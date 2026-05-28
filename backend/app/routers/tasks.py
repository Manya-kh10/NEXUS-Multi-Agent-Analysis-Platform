from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.tasks import run_analysis_task
from app.database import get_db
from app.services.analysis_service import create_analysis, update_analysis, get_analysis_by_task_id
from app.schemas.analysis import AnalysisCreate, AnalysisUpdate
from app.services.cache import clear_cache
from app.services.dependencies import get_current_active_user
from app.models.user import User
from celery.result import AsyncResult
import pandas as pd
import io

router = APIRouter()

@router.post("/analyze")
async def start_analysis(
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    contents = await file.read()
    csv_data = contents.decode("utf-8")

    df = pd.read_csv(io.StringIO(csv_data))

    task = run_analysis_task.delay(csv_data, file.filename)

    analysis = await create_analysis(db, AnalysisCreate(
        filename=file.filename,
        original_rows=len(df),
        original_cols=len(df.columns),
        task_id=task.id,
        user_id=current_user.id
    ))

    return {
        "task_id": task.id,
        "analysis_id": analysis.id,
        "status": "queued",
        "message": "Analysis started. Poll /tasks/status/{task_id} for updates."
    }

@router.get("/status/{task_id}")
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    task = AsyncResult(task_id)

    if task.state == "PENDING":
        return {"task_id": task_id, "status": "pending", "progress": 0}

    elif task.state == "PROGRESS":
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

    elif task.state == "SUCCESS":
        result = task.result

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

    elif task.state == "FAILURE":
        await update_analysis(db, task_id, AnalysisUpdate(status="failed"))
        return {
            "task_id": task_id,
            "status": "failed",
            "progress": 0,
            "error": str(task.info)
        }

    return {"task_id": task_id, "status": task.state}

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