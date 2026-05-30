from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.responses import Response
from app.services.report_service import generate_analysis_report
from app.services.agents import run_eda_agent, run_stats_agent, run_insight_agent
from app.services.ml_agent import run_ml_agent
from app.services import dataset_service, storage_service
from app.services.dependencies import get_current_user_optional
from app.models.user import User
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import pandas as pd
import io
import logging

logger = logging.getLogger("nexus.report_router")
router = APIRouter()

@router.post("/generate")
async def generate_report(
    request: Request,
    dataset_id: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    include_ml: bool = Form(default=True),
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_current_user_optional(request, db)
    guest_session_id = request.headers.get("x-guest-session-id")
    user_id = current_user.id if current_user else None
    
    csv_bytes = None
    filename = "dataset.csv"
    
    if dataset_id:
        logger.info(f"Report generation initiated for dataset ID: {dataset_id}")
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
            
        filename = db_dataset.name
        storage_url = db_dataset.cleaned_storage_url or db_dataset.storage_url
        try:
            csv_bytes = await storage_service.download_file(storage_url)
        except Exception as e:
            logger.error(f"Failed to download dataset {dataset_id} for report: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch dataset from storage.")
            
    elif file:
        logger.info(f"Report generation initiated for uploaded file: {file.filename}")
        csv_bytes = await file.read()
        filename = file.filename
        
    else:
        raise HTTPException(
            status_code=400,
            detail="Failed handoff: must provide either 'dataset_id' or 'file' multipart payload."
        )
        
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes))
        
        eda_result = run_eda_agent(df)
        stats_result = run_stats_agent(df)
        insight_result = run_insight_agent(eda_result, stats_result)

        ml_result = None
        if include_ml:
            ml_result = run_ml_agent(df)

        pdf_bytes = generate_analysis_report(
            filename=filename,
            eda_result=eda_result,
            stats_result=stats_result,
            insight_result=insight_result,
            ml_result=ml_result
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=nexus_report_{filename.replace('.csv', '')}.pdf"
            }
        )
    except Exception as e:
        logger.error(f"PDF report generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

@router.get("/status")
async def report_status():
    return {"status": "ready", "formats": ["pdf"]}