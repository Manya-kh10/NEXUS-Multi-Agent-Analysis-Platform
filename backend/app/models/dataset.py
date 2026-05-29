from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    source_file = Column(String, nullable=True) # Kept for backward compatibility
    original_filename = Column(String, nullable=False)
    cleaned_filename = Column(String, nullable=True)
    storage_url = Column(String, nullable=False)
    cleaned_storage_url = Column(String, nullable=True)
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    schema_info = Column(JSON, nullable=True)
    stats = Column(JSON, nullable=True)
    status = Column(String, default="raw") # raw, cleaned, analyzing, error
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String, nullable=True) # guest session isolation
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())