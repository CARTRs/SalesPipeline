from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.opportunity import Opportunity
from app.models.user import User
from app.models.opportunity_progress import OpportunityProgress
from app.models.ai_analysis_result import AiAnalysisResult
from app.models.priority_change_log import PriorityChangeLog
from app.schemas.dashboard import (
    StatsOverview,
    PriorityDistribution,
    PriorityItem,
    StatusDistribution,
    StatusItem,
    RiskOverview,
    RiskItem,
    RecentActivity,
    RecentActivityItem,
    UrgentOverview,
    BranchStats,
    BranchStatsItem,
)

router = APIRouter(prefix="/api/dashboard", tags=["数据看板"])


def _apply_role_opportunity_filter(query, user_role: str, user_id: int):
    """Filter opportunity queries based on user role"""
    if user_role == "项目经理":
        return query.where(Opportunity.division_member_id == user_id)
    elif user_role == "客户经理":
        return query.where(Opportunity.account_manager_id == user_id)
    elif user_role == "责任支局长":
        return query.where(Opportunity.branch_director_id == user_id)
    # Admin sees all
    return query


@router.get("/stats", response_model=StatsOverview)
async def get_stats_overview(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取看板基础统计（按角色过滤）"""
    user_role = current_user.get("role")
    user_id = current_user.get("id")

    # Base opportunity count with role filter
    base_opp_count = _apply_role_opportunity_filter(
        select(func.count(Opportunity.id)), user_role, user_id
    )

    # Total opportunities
    total_opp_result = await db.execute(base_opp_count)
    total_opportunities = total_opp_result.scalar() or 0

    # Total users (no filter - system-wide)
    total_user_result = await db.execute(select(func.count(User.id)))
    total_users = total_user_result.scalar() or 0

    # Total progress records (filtered by accessible opportunities)
    if user_role == "管理员":
        total_prog_result = await db.execute(select(func.count(OpportunityProgress.id)))
    else:
        # Count progress for opportunities the user can access
        subq = _apply_role_opportunity_filter(
            select(Opportunity.id), user_role, user_id
        ).subquery()
        total_prog_result = await db.execute(
            select(func.count(OpportunityProgress.id)).where(
                OpportunityProgress.opportunity_id.in_(select(subq.c.id))
            )
        )
    total_progress_records = total_prog_result.scalar() or 0

    # Open opportunities (not closed)
    open_result = await db.execute(
        _apply_role_opportunity_filter(
            select(func.count(Opportunity.id)).where(
                (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None))
            ),
            user_role,
            user_id,
        )
    )
    open_opportunities = open_result.scalar() or 0

    # Closed opportunities
    closed_result = await db.execute(
        _apply_role_opportunity_filter(
            select(func.count(Opportunity.id)).where(Opportunity.close_flag == 1),
            user_role,
            user_id,
        )
    )
    closed_opportunities = closed_result.scalar() or 0

    # No-push flagged
    no_push_result = await db.execute(
        _apply_role_opportunity_filter(
            select(func.count(Opportunity.id)).where(Opportunity.no_push_flag == 1),
            user_role,
            user_id,
        )
    )
    no_push_count = no_push_result.scalar() or 0

    # Bid approaching
    bid_result = await db.execute(
        _apply_role_opportunity_filter(
            select(func.count(Opportunity.id)).where(Opportunity.bid_date_approaching == True),
            user_role,
            user_id,
        )
    )
    bid_approaching_count = bid_result.scalar() or 0

    # Competitor detected
    comp_result = await db.execute(
        _apply_role_opportunity_filter(
            select(func.count(Opportunity.id)).where(Opportunity.competitor_detected == True),
            user_role,
            user_id,
        )
    )
    competitor_detected_count = comp_result.scalar() or 0

    # Pending amount (sum of predicted_amount for open opportunities)
    pending_amount_result = await db.execute(
        _apply_role_opportunity_filter(
            select(func.coalesce(func.sum(Opportunity.predicted_amount), 0)).where(
                (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None))
            ),
            user_role,
            user_id,
        )
    )
    pending_amount = float(pending_amount_result.scalar() or 0)

    # 本周有进度更新的商机数量
    from datetime import timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # 本周一
    week_end = week_start + timedelta(days=6)  # 本周日

    # 查询本周有进度更新的商机ID（去重）
    weekly_progress_query = (
        select(func.count(func.distinct(OpportunityProgress.opportunity_id)))
        .where(
            OpportunityProgress.progress_date >= week_start,
            OpportunityProgress.progress_date <= week_end
        )
    )
    # 如果不是管理员，需要过滤用户可访问的商机
    if user_role != "管理员":
        subq = _apply_role_opportunity_filter(
            select(Opportunity.id), user_role, user_id
        ).subquery()
        weekly_progress_query = weekly_progress_query.where(
            OpportunityProgress.opportunity_id.in_(select(subq.c.id))
        )
    
    weekly_progress_result = await db.execute(weekly_progress_query)
    weekly_progress_count = weekly_progress_result.scalar() or 0

    # 未推进商机数量（no_push_days > 0 且未关闭的商机）
    no_push_opp_query = _apply_role_opportunity_filter(
        select(func.count(Opportunity.id)).where(
            Opportunity.no_push_days > 0,
            (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None))
        ),
        user_role,
        user_id,
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


@router.get("/priority-distribution", response_model=PriorityDistribution)
async def get_priority_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取商机优先级分布（按角色过滤）"""
    user_role = current_user.get("role")
    user_id = current_user.get("id")

    base = (
        select(
            Opportunity.priority_level,
            func.count(Opportunity.id).label("count"),
        )
        .where(
            (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None))
        )
    )
    base = _apply_role_opportunity_filter(base, user_role, user_id)
    base = base.group_by(Opportunity.priority_level).order_by(Opportunity.priority_level)

    rows = await db.execute(base)
    items = [
        PriorityItem(priority_level=row[0] or 3, count=row[1])
        for row in rows.all()
    ]
    return PriorityDistribution(items=items)


# 状态映射：将数据库状态归类为4种标准状态
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


@router.get("/status-distribution", response_model=StatusDistribution)
async def get_status_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取商机状态分布（按角色过滤，归类为4种标准状态）"""
    user_role = current_user.get("role")
    user_id = current_user.get("id")

    base = (
        select(
            Opportunity.opportunity_status,
            func.count(Opportunity.id).label("count"),
        )
        .where(
            Opportunity.opportunity_status.isnot(None),
            (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None)),
        )
    )
    base = _apply_role_opportunity_filter(base, user_role, user_id)
    base = base.group_by(Opportunity.opportunity_status)

    rows = await db.execute(base)
    
    # 将原始状态归类为4种标准状态
    status_counts = {}
    for row in rows.all():
        raw_status = row[0]
        count = row[1]
        # 使用映射表将原始状态转换为标准状态
        mapped_status = STATUS_MAPPING.get(raw_status, "需求挖掘")
        status_counts[mapped_status] = status_counts.get(mapped_status, 0) + count
    
    # 确保4种状态都有数据（即使为0）
    standard_statuses = ["需求挖掘", "解决方案", "商务谈判/招投标", "签约"]
    items = [
        StatusItem(opportunity_status=status, count=status_counts.get(status, 0))
        for status in standard_statuses
    ]
    
    # 按数量降序排列
    items.sort(key=lambda x: x.count, reverse=True)
    
    return StatusDistribution(items=items)


@router.get("/risk-overview", response_model=RiskOverview)
async def get_risk_overview(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取AI风险等级分布（按角色过滤）"""
    user_role = current_user.get("role")
    user_id = current_user.get("id")

    base = (
        select(
            Opportunity.ai_risk_level,
            func.count(Opportunity.id).label("count"),
        )
        .where(
            Opportunity.ai_risk_level.isnot(None),
            (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None)),
        )
    )
    base = _apply_role_opportunity_filter(base, user_role, user_id)
    base = base.group_by(Opportunity.ai_risk_level).order_by(func.count(Opportunity.id).desc())

    rows = await db.execute(base)
    items = [
        RiskItem(risk_level=row[0], count=row[1])
        for row in rows.all()
    ]
    return RiskOverview(items=items)


@router.get("/recent-activity", response_model=RecentActivity)
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取最近的进度推进记录（按角色过滤）"""
    user_role = current_user.get("role")
    user_id = current_user.get("id")

    base_query = (
        select(
            OpportunityProgress.id,
            OpportunityProgress.opportunity_id,
            Opportunity.opportunity_name,
            OpportunityProgress.progress_content,
            User.real_name.label("updater_name"),
            OpportunityProgress.updater_role,
            OpportunityProgress.progress_date,
            OpportunityProgress.created_at,
        )
        .join(Opportunity, OpportunityProgress.opportunity_id == Opportunity.id)
        .join(User, OpportunityProgress.updater_id == User.id)
    )

    # Filter by accessible opportunities based on role
    if user_role != "管理员":
        if user_role == "项目经理":
            base_query = base_query.where(Opportunity.division_member_id == user_id)
        elif user_role == "客户经理":
            base_query = base_query.where(Opportunity.account_manager_id == user_id)
        elif user_role == "责任支局长":
            base_query = base_query.where(Opportunity.branch_director_id == user_id)

    base_query = base_query.order_by(OpportunityProgress.created_at.desc()).limit(limit)

    rows = await db.execute(base_query)
    items = [
        RecentActivityItem(
            id=row[0],
            opportunity_id=row[1],
            opportunity_name=row[2],
            progress_content=row[3],
            updater_name=row[4],
            updater_role=row[5],
            progress_date=row[6],
            created_at=row[7],
        )
        for row in rows.all()
    ]
    return RecentActivity(items=items)


@router.get("/urgent-overview", response_model=UrgentOverview)
async def get_urgent_overview(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取需关注的紧急商机（按角色过滤）"""
    user_role = current_user.get("role")
    user_id = current_user.get("id")

    # No-push opportunities
    no_push_base = (
        select(
            Opportunity.id,
            Opportunity.opportunity_name,
            Opportunity.customer_name,
            Opportunity.no_push_days,
            Opportunity.priority_level,
            Opportunity.last_push_date,
        )
        .where(
            Opportunity.no_push_flag == 1,
            (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None)),
        )
    )
    no_push_base = _apply_role_opportunity_filter(no_push_base, user_role, user_id)
    no_push_base = no_push_base.order_by(Opportunity.no_push_days.desc().nullslast()).limit(20)

    no_push_rows = await db.execute(no_push_base)
    no_push_opportunities = [
        {
            "id": row[0],
            "opportunity_name": row[1],
            "customer_name": row[2],
            "no_push_days": row[3],
            "priority_level": row[4],
            "last_push_date": row[5].isoformat() if row[5] else None,
        }
        for row in no_push_rows.all()
    ]

    # Bid approaching opportunities
    bid_base = (
        select(
            Opportunity.id,
            Opportunity.opportunity_name,
            Opportunity.customer_name,
            Opportunity.estimated_sign_date,
            Opportunity.priority_level,
            Opportunity.product_category,
        )
        .where(
            Opportunity.bid_date_approaching == True,
            (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None)),
        )
    )
    bid_base = _apply_role_opportunity_filter(bid_base, user_role, user_id)
    bid_base = bid_base.order_by(Opportunity.estimated_sign_date.asc().nullslast()).limit(20)

    bid_rows = await db.execute(bid_base)
    bid_approaching_opportunities = [
        {
            "id": row[0],
            "opportunity_name": row[1],
            "customer_name": row[2],
            "estimated_sign_date": row[3].isoformat() if row[3] else None,
            "priority_level": row[4],
            "product_category": row[5],
        }
        for row in bid_rows.all()
    ]

    # Competitor detected opportunities
    comp_base = (
        select(
            Opportunity.id,
            Opportunity.opportunity_name,
            Opportunity.customer_name,
            Opportunity.priority_level,
            Opportunity.ai_risk_level,
        )
        .where(
            Opportunity.competitor_detected == True,
            (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None)),
        )
    )
    comp_base = _apply_role_opportunity_filter(comp_base, user_role, user_id)
    comp_base = comp_base.order_by(Opportunity.priority_level.asc().nullslast()).limit(20)

    comp_rows = await db.execute(comp_base)
    competitor_detected_opportunities = [
        {
            "id": row[0],
            "opportunity_name": row[1],
            "customer_name": row[2],
            "priority_level": row[3],
            "ai_risk_level": row[4],
        }
        for row in comp_rows.all()
    ]

    return UrgentOverview(
        no_push_opportunities=no_push_opportunities,
        bid_approaching_opportunities=bid_approaching_opportunities,
        competitor_detected_opportunities=competitor_detected_opportunities,
    )


@router.get("/branch-stats", response_model=BranchStats)
async def get_branch_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取各支局商机统计（按角色过滤，包含优先级分布）"""
    user_role = current_user.get("role")
    user_id = current_user.get("id")

    # 查询所有符合条件的商机
    base_query = (
        select(
            Opportunity.branch_office,
            Opportunity.priority_level,
            Opportunity.predicted_amount,
        )
        .where(
            Opportunity.branch_office.isnot(None),
        )
    )
    base_query = _apply_role_opportunity_filter(base_query, user_role, user_id)

    result = await db.execute(base_query)
    rows = result.all()

    # 在Python中汇总
    branch_data = {}
    for row in rows:
        branch = row[0]
        priority = row[1] or 2  # 默认为中
        amount = row[2]

        if branch not in branch_data:
            branch_data[branch] = {
                "branch_office": branch,
                "opportunity_count": 0,
                "total_predicted_amount": 0,
                "high_count": 0,    # 高
                "medium_count": 0,  # 中
                "low_count": 0,     # 低
            }

        branch_data[branch]["opportunity_count"] += 1
        branch_data[branch]["total_predicted_amount"] = float(branch_data[branch]["total_predicted_amount"] or 0) + float(amount or 0)

        # 按优先级分类
        if priority == 1:
            branch_data[branch]["high_count"] += 1
        elif priority == 2:
            branch_data[branch]["medium_count"] += 1
        else:
            branch_data[branch]["low_count"] += 1

    # 按商机数量排序
    items = sorted(branch_data.values(), key=lambda x: x["opportunity_count"], reverse=True)

    return BranchStats(items=[
        BranchStatsItem(
            branch_office=item["branch_office"],
            opportunity_count=item["opportunity_count"],
            total_predicted_amount=item["total_predicted_amount"],
            high_count=item["high_count"],
            medium_count=item["medium_count"],
            low_count=item["low_count"],
        )
        for item in items
    ])
