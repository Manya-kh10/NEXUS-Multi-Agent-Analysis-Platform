from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisCreate, AnalysisUpdate
from datetime import datetime

async def create_analysis(db: AsyncSession, data: AnalysisCreate) -> Analysis:
    analysis = Analysis(
        user_id=data.user_id,
        filename=data.filename,
        original_rows=data.original_rows,
        original_cols=data.original_cols,
        task_id=data.task_id,
        status="pending"
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis

async def update_analysis(db: AsyncSession, task_id: str, data: AnalysisUpdate) -> Analysis:
    result = await db.execute(select(Analysis).where(Analysis.task_id == task_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        return None
    for key, value in data.dict(exclude_none=True).items():
        setattr(analysis, key, value)
    await db.commit()
    await db.refresh(analysis)
    return analysis

async def get_analysis_by_task_id(db: AsyncSession, task_id: str) -> Analysis:
    result = await db.execute(select(Analysis).where(Analysis.task_id == task_id))
    return result.scalar_one_or_none()

async def get_all_analyses(db: AsyncSession, user_id: int = None, limit: int = 20) -> list:
    query = select(Analysis)
    if user_id is not None:
        query = query.where(Analysis.user_id == user_id)
    result = await db.execute(
        query.order_by(desc(Analysis.created_at)).limit(limit)
    )
    return result.scalars().all()

async def delete_analysis(db: AsyncSession, analysis_id: int) -> bool:
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        return False
    await db.delete(analysis)
    await db.commit()
    return True