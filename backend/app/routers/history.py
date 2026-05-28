from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.services.analysis_service import get_all_analyses, delete_analysis
from app.schemas.analysis import AnalysisResponse
from app.services.dependencies import get_current_active_user
from app.models.user import User
from app.models.analysis import Analysis
from typing import List

router = APIRouter()

@router.get("/", response_model=List[AnalysisResponse])
async def get_history(
    limit: int = 20, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    analyses = await get_all_analyses(db, user_id=current_user.id, limit=limit)
    return analyses

@router.delete("/{analysis_id}")
async def delete_analysis_record(
    analysis_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
        
    if analysis.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this record")

    await delete_analysis(db, analysis_id)
    return {"status": "deleted", "id": analysis_id}