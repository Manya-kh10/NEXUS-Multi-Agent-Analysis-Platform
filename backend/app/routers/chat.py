from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.chat_agent import run_chat_agent
from app.services import dataset_service, storage_service
from app.services.dependencies import get_current_user_optional
from app.models.user import User
from app.database import get_db
from typing import Optional
import pandas as pd
import io
import json
import logging

logger = logging.getLogger("nexus.chat_router")
router = APIRouter()

@router.post("/message")
async def chat_with_agent(
    request: Request,
    message: str = Form(...),
    history: str = Form(default="[]"),
    dataset_id: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    guest_session_id = request.headers.get("x-guest-session-id")
    user_id = current_user.id if current_user else None
    
    csv_bytes = None
    
    if dataset_id:
        logger.info(f"Chat agent session initiated with dataset ID: {dataset_id}")
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
            logger.error(f"Failed to download dataset {dataset_id} for chat: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch dataset from storage.")
            
    elif file:
        logger.info(f"Chat agent session initiated with direct upload file: {file.filename}")
        csv_bytes = await file.read()
        
    else:
        raise HTTPException(
            status_code=400,
            detail="Failed handoff: must provide either 'dataset_id' or 'file' multipart payload."
        )
        
    try:
        chat_history = json.loads(history)
    except Exception:
        chat_history = []

    try:
        df = pd.read_csv(io.BytesIO(csv_bytes))
        result = run_chat_agent(
            user_message=message,
            df=df,
            chat_history=chat_history
        )

        return {
            "role": "assistant",
            "content": result,
            "message": message
        }
    except Exception as e:
        logger.error(f"Chat agent execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat agent failed to process query: {str(e)}")

@router.get("/status")
async def chat_status():
    return {"status": "ready", "model": "llama-3.3-70b-versatile"}