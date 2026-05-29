from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ml_agent import run_ml_agent
from app.services import dataset_service, storage_service
from app.services.dependencies import get_current_user_optional
from app.models.user import User
from app.database import get_db
from typing import Optional
import pandas as pd
import io
import logging

logger = logging.getLogger("nexus.ml_router")
router = APIRouter()

@router.post("/train")
async def train_models(
    request: Request,
    dataset_id: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    guest_session_id = request.headers.get("x-guest-session-id")
    user_id = current_user.id if current_user else None
    
    csv_bytes = None
    
    if dataset_id:
        logger.info(f"ML SWARM training initiated with dataset ID: {dataset_id}")
        db_dataset = await dataset_service.get_dataset_for_user_or_session(
            db=db,
            dataset_id=dataset_id,
            user_id=user_id,
            session_id=guest_session_id
        )
        if not db_dataset:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found or operative session unauthorized."
            )
            
        storage_url = db_dataset.cleaned_storage_url or db_dataset.storage_url
        try:
            csv_bytes = await storage_service.download_file(storage_url)
        except Exception as e:
            logger.error(f"Failed to download dataset {dataset_id} for ML training: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch dataset from storage.")
            
    elif file:
        logger.info(f"ML SWARM training initiated with direct upload of file: {file.filename}")
        csv_bytes = await file.read()
        
    else:
        raise HTTPException(
            status_code=400,
            detail="Failed handoff: must provide either 'dataset_id' or 'file' multipart payload."
        )
        
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes))
        result = run_ml_agent(df)
        return result
    except Exception as e:
        logger.error(f"ML SWARM training pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"ML SWARM training failed: {str(e)}")

@router.get("/status")
async def ml_status():
    return {
        "status": "ready",
        "models": ["Random Forest", "Logistic Regression", "Linear Regression"],
        "tasks": ["classification", "regression"]
    }