from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    source_file = Column(String)
    row_count = Column(Integer)
    column_count = Column(Integer)
    schema_info = Column(JSON)
    stats = Column(JSON)
    status = Column(String, default="raw")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())