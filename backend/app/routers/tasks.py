from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.tasks import run_analysis_task
from app.database import get_db
from app.services.analysis_service import create_analysis, update_analysis, get_analysis_by_task_id
from app.schemas.analysis import AnalysisCreate, AnalysisUpdate
from app.services.cache import clear_cache
from app.services.dependencies import get_current_user_optional
from app.services import dataset_service, storage_service
from app.models.user import User
from celery.result import AsyncResult
from typing import Optional
import pandas as pd
import io
import uuid
import logging
import celery.exceptions
import kombu.exceptions
import redis

logger = logging.getLogger("nexus.tasks_router")
router = APIRouter()

@router.post("/analyze")
async def start_analysis(
    request: Request,
    dataset_id: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    try:
        guest_session_id = request.headers.get("x-guest-session-id")
        user_id = current_user.id if current_user else None
        
        filename = ""
        row_count = 0
        col_count = 0
        task_param = ""
        
        if dataset_id:
            logger.info(f"Triggering agent swarm analysis on pre-existing dataset ID: {dataset_id}")
            # Verify access/ownership for this user/guest session
            db_dataset = await dataset_service.get_dataset_for_user_or_session(
                db=db,
                dataset_id=dataset_id,
                user_id=user_id,
                session_id=guest_session_id
            )
            if not db_dataset:
                raise HTTPException(
                    status_code=404,
                    detail="Dataset not found or operative session not authorized."
                )
                
            filename = db_dataset.name
            row_count = db_dataset.row_count or 0
            col_count = db_dataset.column_count or 0
            task_param = db_dataset.dataset_id
            
        elif file:
            logger.info(f"Direct upload swarm analysis initiated for file: {file.filename}")
            contents = await file.read()
            filename = file.filename
            
            try:
                df = pd.read_csv(io.BytesIO(contents))
                row_count = len(df)
                col_count = len(df.columns)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid CSV structure: {e}")
                
            # Create persistent dataset automatically for the user
            generated_id = str(uuid.uuid4())
            try:
                # Upload raw file
                storage_url = await storage_service.upload_file(
                    filename=filename,
                    file_bytes=contents,
                    dataset_id=generated_id
                )
                # Create DB metadata
                db_dataset = await dataset_service.create_dataset(
                    db=db,
                    name=filename,
                    original_filename=filename,
                    storage_url=storage_url,
                    row_count=row_count,
                    column_count=col_count,
                    user_id=user_id,
                    session_id=guest_session_id
                )
                task_param = db_dataset.dataset_id
            except Exception as e:
                logger.error(f"Failed to record upload in storage/DB: {e}")
                # Fall back to passing raw CSV data in celery parameters for resilience
                task_param = contents.decode("utf-8")
                
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed handoff: must provide either 'dataset_id' or 'file' multipart payload."
            )

        # Queue Celery analysis task
        try:
            task = run_analysis_task.delay(task_param, filename)
        except (celery.exceptions.OperationalError, kombu.exceptions.OperationalError, redis.RedisError) as e:
            logger.error(f"Failed to queue Celery analysis task: {e}")
            raise HTTPException(
                status_code=503,
                detail="Task queue service is temporarily unavailable."
            )
        except Exception as e:
            err_msg = str(e)
            if "celery" in err_msg.lower() or "redis" in err_msg.lower() or "connection" in err_msg.lower() or "retry" in err_msg.lower():
                logger.error(f"Celery result store or broker connection error: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Task queue service is temporarily unavailable. Please verify task queue service connectivity."
                )
            raise e

        # Create analysis run record
        analysis = await create_analysis(db, AnalysisCreate(
            filename=filename,
            original_rows=row_count,
            original_cols=col_count,
            task_id=task.id,
            user_id=user_id
        ))

        return {
            "task_id": task.id,
            "analysis_id": analysis.id,
            "status": "queued",
            "message": "Analysis started. Poll /tasks/status/{task_id} for updates."
        }
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.exception(f"Unhandled exception in start_analysis endpoint: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis initiation failed: {str(exc)}"
        )

@router.get("/status/{task_id}")
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    try:
        task = AsyncResult(task_id)
        state = task.state
    except Exception as e:
        logger.error(f"Failed to fetch Celery task state for {task_id}: {e}")
        await update_analysis(db, task_id, AnalysisUpdate(status="failed"))
        return {
            "task_id": task_id,
            "status": "failed",
            "progress": 0,
            "error": "Task execution failed or results state was corrupted."
        }

    try:
        if state == "PENDING":
            return {"task_id": task_id, "status": "pending", "progress": 0}

        elif state == "PROGRESS":
            meta = task.info or {}
            return {
                "task_id": task_id,
                "status": "progress",
                "progress": meta.get("progress", 0),
                "message": meta.get("status", ""),
                "eda": meta.get("eda"),
                "stats": meta.get("stats"),
                "insights": meta.get("insights")
            }

        elif state == "SUCCESS":
            result = task.result

            if isinstance(result, dict) and result.get("status") == "failed":
                await update_analysis(db, task_id, AnalysisUpdate(status="failed"))
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "progress": 0,
                    "error": result.get("error", "Task execution failed.")
                }

            await update_analysis(db, task_id, AnalysisUpdate(
                status="complete",
                cached=result.get("cached", False),
                eda_result=result.get("eda"),
                stats_result=result.get("stats"),
                insight_result=result.get("insights"),
            ))

            return {
                "task_id": task_id,
                "status": "complete",
                "progress": 100,
                "result": result
            }

        elif state == "FAILURE":
            await update_analysis(db, task_id, AnalysisUpdate(status="failed"))
            error_msg = "Celery worker task execution failure."
            try:
                error_msg = str(task.info)
            except Exception:
                pass
            return {
                "task_id": task_id,
                "status": "failed",
                "progress": 0,
                "error": error_msg
            }

        return {"task_id": task_id, "status": state}

    except Exception as e:
        logger.exception(f"Exception raised in get_task_status endpoint for {task_id}: {e}")
        return {
            "task_id": task_id,
            "status": "failed",
            "progress": 0,
            "error": f"Failed to retrieve task status details: {str(e)}"
        }

@router.delete("/cancel/{task_id}")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    task = AsyncResult(task_id)
    task.revoke(terminate=True)
    await update_analysis(db, task_id, AnalysisUpdate(status="cancelled"))
    return {"task_id": task_id, "status": "cancelled"}

@router.delete("/cache/clear")
async def clear_analysis_cache():
    count = clear_cache()
    return {"status": "cleared", "keys_deleted": count}

@router.get("/health")
async def tasks_health():
    return {
        "status": "ready",
        "workers": "active",
        "cache": "redis"
    }