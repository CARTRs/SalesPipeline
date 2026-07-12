"""
操作日志服务 — 记录用户操作到数据库
"""
import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.operation_log import OperationLog


async def log_operation(
    action: str,
    detail: Optional[dict] = None,
    *,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    db: Optional[AsyncSession] = None,
):
    """记录操作日志"""
    log = OperationLog(
        user_id=user_id,
        user_name=user_name,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
        ip_address=ip_address,
        status=status,
        error_message=error_message,
    )

    if db:
        db.add(log)
    else:
        # 独立会话（用于没有 db session 的场景）
        async with async_session() as session:
            session.add(log)
            await session.commit()


async def get_logs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> tuple[list[OperationLog], int]:
    """查询操作日志"""
    from sqlalchemy import func

    query = select(OperationLog)
    count_query = select(func.count(OperationLog.id))

    if action:
        query = query.where(OperationLog.action == action)
        count_query = count_query.where(OperationLog.action == action)
    if resource_type:
        query = query.where(OperationLog.resource_type == resource_type)
        count_query = count_query.where(OperationLog.resource_type == resource_type)
    if status_filter:
        query = query.where(OperationLog.status == status_filter)
        count_query = count_query.where(OperationLog.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(OperationLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return items, total
