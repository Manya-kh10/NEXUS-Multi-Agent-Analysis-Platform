import logging
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, delete
from app.models.dataset import Dataset
from app.services import storage_service

logger = logging.getLogger("nexus.dataset_service")

async def create_dataset(
    db: AsyncSession,
    name: str,
    original_filename: str,
    storage_url: str,
    row_count: int = None,
    column_count: int = None,
    schema_info: dict = None,
    stats: dict = None,
    user_id: int = None,
    session_id: str = None
) -> Dataset:
    """Creates a new Dataset metadata record in the database."""
    dataset_id = str(uuid.uuid4())
    
    # Backward compatible fields are kept
    dataset = Dataset(
        dataset_id=dataset_id,
        name=name,
        source_file=storage_url, # Fallback path
        original_filename=original_filename,
        storage_url=storage_url,
        row_count=row_count,
        column_count=column_count,
        schema_info=schema_info,
        stats=stats,
        status="raw",
        user_id=user_id,
        session_id=session_id
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    logger.info(f"Metadata recorded in DB for dataset {name} (ID: {dataset_id})")
    return dataset

async def get_dataset_by_id(db: AsyncSession, dataset_id: str) -> Dataset:
    """Retrieves a dataset by its unique dataset_id."""
    result = await db.execute(select(Dataset).where(Dataset.dataset_id == dataset_id))
    return result.scalar_one_or_none()

async def get_dataset_for_user_or_session(
    db: AsyncSession,
    dataset_id: str,
    user_id: int = None,
    session_id: str = None
) -> Dataset:
    """
    Retrieves a dataset and verifies ownership/access.
    Guest-mode datasets are isolated and only accessible to the correct session_id.
    """
    dataset = await get_dataset_by_id(db, dataset_id)
    if not dataset:
        return None
        
    # If the dataset has a registered owner:
    if dataset.user_id is not None:
        if user_id is not None and dataset.user_id == user_id:
            return dataset
        # Otherwise access is denied
        return None
        
    # If it is a guest dataset:
    if dataset.session_id is not None:
        if session_id is not None and dataset.session_id == session_id:
            return dataset
        # Also allow if a registered user accesses it during their active login if we want,
        # but strict guest session isolation is preferred:
        return None
        
    # Public/unowned dataset (fallback)
    return dataset

async def update_dataset_cleaned(
    db: AsyncSession,
    dataset_id: str,
    cleaned_filename: str,
    cleaned_storage_url: str,
    row_count: int,
    column_count: int,
    schema_info: dict = None,
    stats: dict = None
) -> Dataset:
    """Updates dataset metadata once it has run through the purification pipeline."""
    dataset = await get_dataset_by_id(db, dataset_id)
    if not dataset:
        return None
        
    dataset.cleaned_filename = cleaned_filename
    dataset.cleaned_storage_url = cleaned_storage_url
    dataset.row_count = row_count
    dataset.column_count = column_count
    if schema_info:
        dataset.schema_info = schema_info
    if stats:
        dataset.stats = stats
    dataset.status = "cleaned"
    
    await db.commit()
    await db.refresh(dataset)
    logger.info(f"Dataset {dataset_id} metadata updated to CLEANED status.")
    return dataset

async def list_datasets(
    db: AsyncSession,
    user_id: int = None,
    session_id: str = None,
    limit: int = 50
) -> list:
    """Lists datasets owned by the user or the active guest session."""
    query = select(Dataset)
    
    if user_id is not None:
        # User sees their own datasets AND any guest datasets uploaded during this session
        if session_id:
            query = query.where(or_(Dataset.user_id == user_id, Dataset.session_id == session_id))
        else:
            query = query.where(Dataset.user_id == user_id)
    elif session_id is not None:
        # Guests only see datasets associated with their specific session
        query = query.where(Dataset.session_id == session_id)
    else:
        # Return empty list if no identifiers provided (anonymous safety check)
        return []
        
    result = await db.execute(
        query.order_by(Dataset.created_at.desc()).limit(limit)
    )
    return result.scalars().all()

async def cleanup_expired_guest_datasets(db: AsyncSession, expiry_hours: int = 24) -> int:
    """
    Cleans up guest datasets that are older than expiry_hours.
    Permanently purges physical files from Supabase/Local storage and removes database records.
    """
    threshold_time = datetime.utcnow() - timedelta(hours=expiry_hours)
    
    # Query guest datasets older than the threshold
    query = select(Dataset).where(
        and_(
            Dataset.user_id == None,
            Dataset.created_at < threshold_time
        )
    )
    result = await db.execute(query)
    expired_datasets = result.scalars().all()
    
    purged_count = 0
    for dataset in expired_datasets:
        logger.info(f"Purging expired guest dataset {dataset.name} (ID: {dataset.dataset_id})...")
        
        # Delete original file
        if dataset.storage_url:
            try:
                await storage_service.delete_file(dataset.storage_url)
            except Exception as e:
                logger.error(f"Failed to delete original file: {e}")
                
        # Delete cleaned file if exists
        if dataset.cleaned_storage_url:
            try:
                await storage_service.delete_file(dataset.cleaned_storage_url)
            except Exception as e:
                logger.error(f"Failed to delete cleaned file: {e}")
                
        # Remove from database
        await db.delete(dataset)
        purged_count += 1
        
    if purged_count > 0:
        await db.commit()
        logger.info(f"Completed expired guest datasets purge. Purged: {purged_count} records.")
        
    return purged_count
