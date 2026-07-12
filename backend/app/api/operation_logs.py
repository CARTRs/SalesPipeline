from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.log_service import get_logs


class LogItem(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    detail: Optional[str] = None
    ip_address: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LogListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[LogItem]


router = APIRouter(prefix="/api/logs", tags=["操作日志"])


@router.get("", response_model=LogListResponse)
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await get_logs(
        db,
        page=page,
        page_size=page_size,
        action=action,
        resource_type=resource_type,
        status_filter=status,
    )
    return LogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[LogItem.model_validate(l) for l in items],
    )
