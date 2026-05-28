from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class AnalysisCreate(BaseModel):
    filename: str
    original_rows: int
    original_cols: int
    task_id: str
    user_id: Optional[int] = None

class AnalysisUpdate(BaseModel):
    status: Optional[str] = None
    cleaned_rows: Optional[int] = None
    cleaned_cols: Optional[int] = None
    cached: Optional[bool] = None
    eda_result: Optional[Any] = None
    stats_result: Optional[Any] = None
    insight_result: Optional[Any] = None
    cleaning_report: Optional[Any] = None
    completed_at: Optional[datetime] = None

class AnalysisResponse(BaseModel):
    id: int
    filename: str
    original_rows: Optional[int]
    original_cols: Optional[int]
    cleaned_rows: Optional[int]
    cleaned_cols: Optional[int]
    task_id: Optional[str]
    status: str
    cached: bool
    created_at: datetime

    class Config:
        from_attributes = True