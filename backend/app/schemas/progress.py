from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class ProgressCreate(BaseModel):
    progress_content: str
    progress_date: date


class ProgressUpdate(BaseModel):
    progress_content: Optional[str] = None


class ProgressResponse(BaseModel):
    id: int
    opportunity_id: int
    updater_id: int
    updater_role: str
    updater_name: Optional[str] = None
    progress_content: str
    progress_date: date
    week_number: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProgressListResponse(BaseModel):
    total: int
    items: list[ProgressResponse]
