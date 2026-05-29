from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, Query
from fastapi.responses import StreamingResponse
from app.services.cleaning_pipeline import CleaningPipeline
from app.services import storage_service, dataset_service
from app.services.dependencies import get_current_user_optional
from app.models.user import User
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
import io
import os
import asyncio
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

logger = logging.getLogger("nexus.pipeline_router")
router = APIRouter()

# Thread pool for CPU-bound cleaning pipeline execution
_cleaning_pool = ThreadPoolExecutor(max_workers=2)

def _run_cleaning_pipeline(contents: bytes) -> dict:
    """Synchronous CPU-bound helper executed in thread executor."""
    df = pd.read_csv(io.BytesIO(contents), low_memory=True)
    original_rows = len(df)
    original_cols = len(df.columns)

    pipeline = CleaningPipeline(df)
    pipeline.run_all()

    # Save cleaned dataframe to bytes
    out_buffer = io.BytesIO()
    pipeline.df.to_csv(out_buffer, index=False)
    cleaned_bytes = out_buffer.getvalue()

    return {
        "bytes": cleaned_bytes,
        "original_shape": {"rows": original_rows, "cols": original_cols},
        "cleaned_shape": {"rows": len(pipeline.df), "cols": len(pipeline.df.columns)},
        "report": pipeline.report
    }

@router.post("/clean")
async def clean_dataset(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    # Parse guest session ID header
    guest_session_id = request.headers.get("x-guest-session-id")
    user_id = current_user.id if current_user else None
    
    contents = await file.read()
    filename = file.filename
    dataset_id = str(uuid.uuid4())
    
    try:
        # Step 1: Upload raw file to persistent storage
        raw_storage_url = await storage_service.upload_file(
            filename=filename,
            file_bytes=contents,
            dataset_id=dataset_id
        )
        
        # Step 2: Record raw metadata in DB
        # To avoid schema parsing overhead, we do this first
        db_dataset = await dataset_service.create_dataset(
            db=db,
            name=filename,
            original_filename=filename,
            storage_url=raw_storage_url,
            user_id=user_id,
            session_id=guest_session_id
        )
        
        # Step 3: Run cleaning pipeline in executor thread pool
        loop = asyncio.get_running_loop()
        cleaning_result = await loop.run_in_executor(
            _cleaning_pool,
            _run_cleaning_pipeline,
            contents
        )
        
        # Step 4: Upload cleaned file to persistent storage
        cleaned_filename = f"cleaned_{filename}"
        cleaned_storage_url = await storage_service.upload_file(
            filename=cleaned_filename,
            file_bytes=cleaning_result["bytes"],
            dataset_id=dataset_id
        )
        
        # Step 5: Update DB metadata with cleaned info
        await dataset_service.update_dataset_cleaned(
            db=db,
            dataset_id=db_dataset.dataset_id,
            cleaned_filename=cleaned_filename,
            cleaned_storage_url=cleaned_storage_url,
            row_count=cleaning_result["cleaned_shape"]["rows"],
            column_count=cleaning_result["cleaned_shape"]["cols"],
            schema_info={"columns": list(pd.read_csv(io.BytesIO(cleaning_result["bytes"]), nrows=2).columns)},
            stats={}
        )
        
        return {
            "dataset_id": db_dataset.dataset_id,
            "filename": cleaned_filename,
            "original_shape": cleaning_result["original_shape"],
            "cleaned_shape": cleaning_result["cleaned_shape"],
            "cleaning_report": cleaning_result["report"],
            "download_path": f"/api/pipeline/download/{db_dataset.dataset_id}"
        }
        
    except Exception as exc:
        logger.error(f"Pipeline error for file {filename}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Purification pipeline error: {str(exc)}")

@router.get("/download/{dataset_id}")
async def download_cleaned(
    dataset_id: str,
    request: Request,
    version: str = Query("cleaned", regex="^(cleaned|original)$"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    guest_session_id = request.headers.get("x-guest-session-id") or request.query_params.get("guest_session_id")
    user_id = current_user.id if current_user else None
    
    # 1. Fetch metadata and verify user/session ownership
    dataset = await dataset_service.get_dataset_for_user_or_session(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        session_id=guest_session_id
    )
    
    if not dataset:
        # Check backward compatibility fallback: if dataset_id matches an actual local file, download it
        # (This preserves compatibility with older files in standard local folders during transition)
        local_dir = "/app/data/cleaned"
        local_path = os.path.join(local_dir, dataset_id)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                data_bytes = f.read()
            return StreamingResponse(
                io.BytesIO(data_bytes),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=cleaned_{dataset_id}"}
            )
        raise HTTPException(status_code=404, detail="Dataset not found or access unauthorized.")
        
    # 2. Get storage URL based on requested version
    storage_url = dataset.cleaned_storage_url if version == "cleaned" else dataset.storage_url
    filename = dataset.cleaned_filename if version == "cleaned" else dataset.original_filename
    
    if not storage_url:
        # If cleaned version is requested but doesn't exist, fall back to original
        storage_url = dataset.storage_url
        filename = dataset.original_filename
        
    try:
        # 3. Stream from Supabase/Local storage to client
        file_bytes = await storage_service.download_file(storage_url)
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as exc:
        logger.error(f"Download storage error for dataset {dataset_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch dataset from storage.")

@router.get("/datasets")
async def list_user_datasets(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Lists all datasets owned by the logged-in user or the active guest session."""
    guest_session_id = request.headers.get("x-guest-session-id")
    user_id = current_user.id if current_user else None
    
    datasets = await dataset_service.list_datasets(
        db=db,
        user_id=user_id,
        session_id=guest_session_id,
        limit=limit
    )
    
    return [
        {
            "dataset_id": d.dataset_id,
            "name": d.name,
            "original_filename": d.original_filename,
            "cleaned_filename": d.cleaned_filename,
            "status": d.status,
            "row_count": d.row_count,
            "column_count": d.column_count,
            "created_at": d.created_at
        }
        for d in datasets
    ]

@router.post("/cleanup")
async def purge_guest_datasets(
    db: AsyncSession = Depends(get_db),
    expiry_hours: int = Query(24, ge=1)
):
    """Admin/System endpoint to trigger garbage collection of expired guest datasets."""
    count = await dataset_service.cleanup_expired_guest_datasets(db, expiry_hours=expiry_hours)
    return {"status": "success", "purged_count": count}

@router.get("/status")
async def pipeline_status():
    return {
        "status": "ready",
        "storage": "supabase" if storage_service.is_supabase_enabled() else "local_fallback"
    }