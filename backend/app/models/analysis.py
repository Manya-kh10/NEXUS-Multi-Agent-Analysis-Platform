from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String, nullable=False)
    original_rows = Column(Integer)
    original_cols = Column(Integer)
    cleaned_rows = Column(Integer)
    cleaned_cols = Column(Integer)
    task_id = Column(String, index=True)
    status = Column(String, default="pending")
    cached = Column(Boolean, default=False)
    eda_result = Column(JSON)
    stats_result = Column(JSON)
    insight_result = Column(JSON)
    cleaning_report = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, onupdate=func.now())