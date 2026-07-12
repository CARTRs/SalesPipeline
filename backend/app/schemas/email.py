from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class EmailLogResponse(BaseModel):
    id: int
    opportunity_id: Optional[int] = None
    recipient_id: Optional[int] = None
    recipient_email: str
    email_type: str
    subject: str
    content: Optional[str] = None
    status: str
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailLogListResponse(BaseModel):
    total: int
    items: list[EmailLogResponse]


class EmailTemplateResponse(BaseModel):
    template_key: str
    subject_template: str
    body_html: str
