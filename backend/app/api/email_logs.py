import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.email_log import EmailLog
from app.models.opportunity import Opportunity
from app.schemas.email import EmailLogResponse, EmailLogListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email-logs", tags=["邮件日志"])


@router.get("", response_model=EmailLogListResponse)
async def list_email_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    email_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(EmailLog).options(selectinload(EmailLog.opportunity))
    count_query = select(func.count(EmailLog.id))

    if status_filter:
        query = query.where(EmailLog.status == status_filter)
        count_query = count_query.where(EmailLog.status == status_filter)
    if email_type:
        query = query.where(EmailLog.email_type == email_type)
        count_query = count_query.where(EmailLog.email_type == email_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(EmailLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return EmailLogListResponse(
        total=total,
        items=[EmailLogResponse.model_validate(l) for l in items],
    )


@router.get("/by-opportunity/{opportunity_id}")
async def get_email_logs_by_opportunity(
    opportunity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取某个商机的邮件发送记录"""
    query = (
        select(EmailLog)
        .where(EmailLog.opportunity_id == opportunity_id)
        .order_by(EmailLog.created_at.desc())
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "total": len(logs),
        "items": [EmailLogResponse.model_validate(l) for l in logs],
        "has_sent": any(l.status == "sent" for l in logs),
        "last_sent_at": next((l.sent_at for l in logs if l.status == "sent"), None),
    }


@router.post("/{log_id}/resend", response_model=EmailLogResponse)
async def resend_email(log_id: int, db: AsyncSession = Depends(get_db)):
    """重发失败邮件"""
    result = await db.execute(
        select(EmailLog).where(EmailLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="邮件记录不存在")

    log.status = "pending"
    await db.flush()
    await db.refresh(log)
    return EmailLogResponse.model_validate(log)
