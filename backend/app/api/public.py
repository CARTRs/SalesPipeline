"""
公开数据看板 API — 通过 URL 路径区分用户，无需 token
/admin 和 /zw 两个独立入口
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.opportunity import Opportunity
from app.models.user import User
from app.models.opportunity_progress import OpportunityProgress
from app.schemas.dashboard import (
    StatsOverview,
    PriorityDistribution,
    PriorityItem,
    StatusDistribution,
    StatusItem,
    BranchStats,
    BranchStatsItem,
)

router = APIRouter(prefix="/api/public", tags=["公开接口"])


# ---------------------------------------------------------------------------
# 用户映射（URL 路径 → 用户身份）
# ---------------------------------------------------------------------------

USER_INFO = {
    "admin": {"user_id": 1, "role": "管理员", "real_name": "系统管理员"},
    "zw": {"user_id": 13, "role": "责任支局长", "real_name": "政务"},
}


async def get_public_user(
    user_key: str,
) -> dict:
    """根据 URL 路径中的 user_key 返回对应的用户身份"""
    info = USER_INFO.get(user_key)
    if not info:
        raise HTTPException(status_code=404, detail="不存在的用户")
    return {"user_key": user_key, **info}


# ---------------------------------------------------------------------------
# 角色过滤辅助函数
# ---------------------------------------------------------------------------

def _apply_role_opportunity_filter(query, user_role: str, user_id: int):
    if user_role == "项目经理":
        return query.where(Opportunity.division_member_id == user_id)
    elif user_role == "客户经理":
        return query.where(Opportunity.account_manager_id == user_id)
    elif user_role == "责任支局长":
        return query.where(Opportunity.branch_director_id == user_id)
    return query


STATUS_MAPPING = {
    # 需求挖掘
    "需求挖掘": "需求挖掘",
    "需求确认": "需求挖掘",
    "需求分析": "需求挖掘",
    "方案设计": "需求挖掘",
    "长期跟踪": "需求挖掘",
    "需推进": "需求挖掘",
    "暂停": "需求挖掘",
    "签约希望低": "需求挖掘",
    "签约失败": "需求挖掘",
    # 解决方案
    "解决方案": "解决方案",
    "方案设计中": "解决方案",
    "方案报价": "解决方案",
    "方案确认": "解决方案",
    # 商务谈判/招投标
    "商务谈判/招投标": "商务谈判/招投标",
    "商务谈判": "商务谈判/招投标",
    "招投标": "商务谈判/招投标",
    "招标中": "商务谈判/招投标",
    "投标": "商务谈判/招投标",
    "竞标": "商务谈判/招投标",
    "谈判中": "商务谈判/招投标",
    # 签约
    "签约": "签约",
    "已签约": "签约",
    "已中标": "签约",
    "已中标待签约": "签约",
    "签约完成": "签约",
    "已关闭": "签约",
    "其他单位签约": "签约",
}


# ---------------------------------------------------------------------------
# 看板统计
# ---------------------------------------------------------------------------


@router.get("/dashboard/{user_key}/stats", response_model=StatsOverview)
async def public_get_stats_overview(
    current_user: dict = Depends(get_public_user),
    db: AsyncSession = Depends(get_db),
):
    """公开获取看板基础统计"""
    user_role = current_user.get("role")
    user_id = current_user.get("user_id")

    base_opp_count = _apply_role_opportunity_filter(
        select(func.count(Opportunity.id)), user_role, user_id
    )
    total_opp_result = await db.execute(base_opp_count)
    total_opportunities = total_opp_result.scalar() or 0

    total_user_result = await db.execute(select(func.count(User.id)))
    total_users = total_user_result.scalar() or 0

    if user_role == "管理员":
        total_prog_result = await db.execute(select(func.count(OpportunityProgress.id)))
    else:
        subq = _apply_role_opportunity_filter(
            select(Opportunity.id), user_role, user_id
        ).subquery()
        total_prog_result = await db.execute(
            select(func.count(OpportunityProgress.id)).where(
                OpportunityProgress.opportunity_id.in_(select(subq.c.id))
            )
        )
    total_progress_records = total_prog_result.scalar() or 0

    open_result = await db.execute(
        _apply_role_opportunity_filter(
            select(func.count(Opportunity.id)).where(
                (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None))
            ),
            user_role, user_id,
        )
    )
    open_opportunities = open_result.scalar() or 0

    closed_result = await db.execute(
        _apply_role_opportunity_filter(
            select(func.count(Opportunity.id)).where(Opportunity.close_flag == 1),
            user_role, user_id,
        )
    )
    closed_opportunities = closed_result.scalar() or 0

    no_push_result = await db.execute(
        _apply_role_opportunity_filter(
            select(func.count(Opportunity.id)).where(Opportunity.no_push_flag == 1),
            user_role, user_id,
        )
    )
    no_push_count = no_push_result.scalar() or 0

    bid_result = await db.execute(
        _apply_role_opportunity_filter(
            select(func.count(Opportunity.id)).where(Opportunity.bid_date_approaching == True),
            user_role, user_id,
        )
    )
    bid_approaching_count = bid_result.scalar() or 0

    comp_result = await db.execute(
        _apply_role_opportunity_filter(
            select(func.count(Opportunity.id)).where(Opportunity.competitor_detected == True),
            user_role, user_id,
        )
    )
    competitor_detected_count = comp_result.scalar() or 0

    pending_amount_result = await db.execute(
        _apply_role_opportunity_filter(
            select(func.coalesce(func.sum(Opportunity.predicted_amount), 0)).where(
                (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None))
            ),
            user_role, user_id,
        )
    )
    pending_amount = float(pending_amount_result.scalar() or 0)

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    weekly_progress_query = (
        select(func.count(func.distinct(OpportunityProgress.opportunity_id)))
        .where(
            OpportunityProgress.progress_date >= week_start,
            OpportunityProgress.progress_date <= week_end,
        )
    )
    if user_role != "管理员":
        subq = _apply_role_opportunity_filter(
            select(Opportunity.id), user_role, user_id
        ).subquery()
        weekly_progress_query = weekly_progress_query.where(
            OpportunityProgress.opportunity_id.in_(select(subq.c.id))
        )
    weekly_progress_result = await db.execute(weekly_progress_query)
    weekly_progress_count = weekly_progress_result.scalar() or 0

    no_push_opp_query = _apply_role_opportunity_filter(
        select(func.count(Opportunity.id)).where(
            Opportunity.no_push_days > 0,
            (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None)),
        ),
        user_role, user_id,
    )
    no_push_opp_result = await db.execute(no_push_opp_query)
    no_push_opportunity_count = no_push_opp_result.scalar() or 0

    return StatsOverview(
        total_opportunities=total_opportunities,
        total_users=total_users,
        total_progress_records=total_progress_records,
        open_opportunities=open_opportunities,
        closed_opportunities=closed_opportunities,
        no_push_count=no_push_count,
        bid_approaching_count=bid_approaching_count,
        competitor_detected_count=competitor_detected_count,
        pending_amount=round(pending_amount, 2),
        weekly_progress_count=weekly_progress_count,
        no_push_opportunity_count=no_push_opportunity_count,
    )


@router.get("/dashboard/{user_key}/priority-distribution", response_model=PriorityDistribution)
async def public_get_priority_distribution(
    current_user: dict = Depends(get_public_user),
    db: AsyncSession = Depends(get_db),
):
    user_role = current_user.get("role")
    user_id = current_user.get("user_id")
    base = (
        select(Opportunity.priority_level, func.count(Opportunity.id).label("count"))
        .where((Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None)))
    )
    base = _apply_role_opportunity_filter(base, user_role, user_id)
    base = base.group_by(Opportunity.priority_level).order_by(Opportunity.priority_level)
    rows = await db.execute(base)
    items = [PriorityItem(priority_level=row[0] or 3, count=row[1]) for row in rows.all()]
    return PriorityDistribution(items=items)


@router.get("/dashboard/{user_key}/status-distribution", response_model=StatusDistribution)
async def public_get_status_distribution(
    current_user: dict = Depends(get_public_user),
    db: AsyncSession = Depends(get_db),
):
    user_role = current_user.get("role")
    user_id = current_user.get("user_id")
    base = (
        select(Opportunity.opportunity_status, func.count(Opportunity.id).label("count"))
        .where(Opportunity.opportunity_status.isnot(None),
               (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None)))
    )
    base = _apply_role_opportunity_filter(base, user_role, user_id)
    base = base.group_by(Opportunity.opportunity_status)
    rows = await db.execute(base)
    status_counts = {}
    for row in rows.all():
        mapped = STATUS_MAPPING.get(row[0], "需求挖掘")
        status_counts[mapped] = status_counts.get(mapped, 0) + row[1]
    items = [StatusItem(opportunity_status=s, count=status_counts.get(s, 0))
             for s in ["需求挖掘", "解决方案", "商务谈判/招投标", "签约"]]
    items.sort(key=lambda x: x.count, reverse=True)
    return StatusDistribution(items=items)


@router.get("/dashboard/{user_key}/branch-stats", response_model=BranchStats)
async def public_get_branch_stats(
    current_user: dict = Depends(get_public_user),
    db: AsyncSession = Depends(get_db),
):
    user_role = current_user.get("role")
    user_id = current_user.get("user_id")
    base_query = (
        select(Opportunity.branch_office, Opportunity.priority_level, Opportunity.predicted_amount)
        .where(Opportunity.branch_office.isnot(None))
    )
    base_query = _apply_role_opportunity_filter(base_query, user_role, user_id)
    rows = (await db.execute(base_query)).all()
    branch_data = {}
    for row in rows:
        branch = row[0]
        priority = row[1] or 2
        amount = row[2]
        if branch not in branch_data:
            branch_data[branch] = {"branch_office": branch, "opportunity_count": 0,
                                   "total_predicted_amount": 0, "high_count": 0,
                                   "medium_count": 0, "low_count": 0}
        branch_data[branch]["opportunity_count"] += 1
        branch_data[branch]["total_predicted_amount"] = float(branch_data[branch]["total_predicted_amount"] or 0) + float(amount or 0)
        if priority == 1:
            branch_data[branch]["high_count"] += 1
        elif priority == 2:
            branch_data[branch]["medium_count"] += 1
        else:
            branch_data[branch]["low_count"] += 1
    items = sorted(branch_data.values(), key=lambda x: x["opportunity_count"], reverse=True)
    return BranchStats(items=[BranchStatsItem(**item) for item in items])


# ---------------------------------------------------------------------------
# 商机列表
# ---------------------------------------------------------------------------

@router.get("/opportunities/{user_key}")
async def public_list_opportunities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "id",
    sort_order: str = "desc",
    current_user: dict = Depends(get_public_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload
    user_role = current_user.get("role")
    user_id = current_user.get("user_id")
    base_query = select(Opportunity).options(
        selectinload(Opportunity.division_member),
        selectinload(Opportunity.account_manager),
        selectinload(Opportunity.branch_director),
    )
    base_count = select(func.count(Opportunity.id))
    if user_role == "项目经理":
        base_query = base_query.where(Opportunity.division_member_id == user_id)
        base_count = base_count.where(Opportunity.division_member_id == user_id)
    elif user_role == "客户经理":
        base_query = base_query.where(Opportunity.account_manager_id == user_id)
        base_count = base_count.where(Opportunity.account_manager_id == user_id)
    elif user_role == "责任支局长":
        base_query = base_query.where(Opportunity.branch_director_id == user_id)
        base_count = base_count.where(Opportunity.branch_director_id == user_id)
    total = (await db.execute(base_count)).scalar()
    sort_column = getattr(Opportunity, sort_by, Opportunity.id)
    order_fn = getattr(sort_column, sort_order, sort_column.desc)
    result = await db.execute(
        base_query.order_by(order_fn()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().unique().all()
    output = []
    for opp in items:
        output.append({
            "id": opp.id,
            "opportunity_name": opp.opportunity_name,
            "customer_name": opp.customer_name,
            "predicted_amount": float(opp.predicted_amount) if opp.predicted_amount else None,
            "opportunity_status": opp.opportunity_status,
            "branch_office": opp.branch_office,
            "no_push_days": opp.no_push_days or 0,
            "account_manager_name": opp.account_manager.real_name if opp.account_manager else None,
            "division_member_name": opp.division_member.real_name if opp.division_member else None,
            "branch_director_name": opp.branch_director.real_name if opp.branch_director else None,
            "priority_level": opp.priority_level,
        })
    return {"total": total or 0, "page": page, "page_size": page_size, "items": output}
