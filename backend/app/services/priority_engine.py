"""
优先级引擎服务

提供商机优先级的自动计算、评估、变更记录以及批量评估功能。

优先级规则（3档）：
  - 高：有竞争对手（移动、联通、华数、广电等）或招标7天以内
  - 低：无进展/无推进（no_push_days > 0）
  - 中：其余所有情况
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.opportunity import Opportunity
from app.models.priority_change_log import PriorityChangeLog

logger = logging.getLogger(__name__)

# ── 常量 ──────────────────────────────────────────────
PRIORITY_LABELS = {1: "高", 2: "中", 3: "低"}

def _is_high_priority(opp: Opportunity) -> tuple[bool, str]:
    """判断是否为高优先级：有竞争对手或招标7天以内"""
    # 竞争对手检测
    if opp.competitor_detected:
        return True, "检测到竞争对手介入"

    # 招标7天以内
    if opp.estimated_sign_date:
        days_until_bid = (opp.estimated_sign_date - date.today()).days
        if 0 <= days_until_bid <= 7:
            return True, f"招标临近（{days_until_bid}天内）"

    return False, ""


def _is_low_priority(opp: Opportunity) -> tuple[bool, str]:
    """判断是否为低优先级：无进展/无推进"""
    if opp.no_push_days and opp.no_push_days > 0:
        return True, f"无进展（{opp.no_push_days}天未推进）"
    return False, ""


def _score_to_priority(opp: Opportunity, current_priority: int) -> tuple[int, str]:
    """
    根据规则判断优先级（3档）：
      - 高(1)：有竞争对手或招标7天以内
      - 低(3)：无进展/无推进
      - 中(2)：其他所有情况
    """
    is_high, high_reason = _is_high_priority(opp)
    is_low, low_reason = _is_low_priority(opp)

    if is_high:
        suggested = 1
        reason = high_reason
    elif is_low:
        suggested = 3
        reason = low_reason
    else:
        suggested = 2
        reason = "常规状态"

    if suggested == current_priority:
        return suggested, "优先级无需变更（当前一致）"
    return suggested, f"建议由「{PRIORITY_LABELS.get(current_priority, str(current_priority))}」调整为「{PRIORITY_LABELS.get(suggested, str(suggested))}」（{reason}）"


# ── 公开接口 ──────────────────────────────────────────


def compute_priority_score(opp: Opportunity) -> dict:
    """
    根据规则判断商机优先级，返回评分和推荐结果。

    返回字段：
      - score_breakdown: dict[str, dict]  # 各维度状态
      - suggested_priority: int
      - score_description: str
    """
    breakdown = {}

    # 竞争对手状态
    if opp.competitor_detected:
        breakdown["competitor"] = {"status": "detected", "reason": "检测到竞争对手介入"}
    else:
        breakdown["competitor"] = {"status": "none", "reason": "未检测到竞争对手"}

    # 招标时间状态
    if opp.estimated_sign_date:
        days_until_bid = (opp.estimated_sign_date - date.today()).days
        if 0 <= days_until_bid <= 7:
            breakdown["bid_date"] = {"status": "urgent", "reason": f"招标临近（{days_until_bid}天内）"}
        elif days_until_bid > 7:
            breakdown["bid_date"] = {"status": "normal", "reason": f"招标在{days_until_bid}天后"}
        else:
            breakdown["bid_date"] = {"status": "expired", "reason": "招标日期已过"}
    else:
        breakdown["bid_date"] = {"status": "none", "reason": "无招标日期"}

    # 未推进状态
    if opp.no_push_days and opp.no_push_days > 0:
        breakdown["push_status"] = {"status": "stale", "reason": f"{opp.no_push_days}天未推进"}
    else:
        breakdown["push_status"] = {"status": "active", "reason": "有推进"}

    suggested_priority, desc = _score_to_priority(opp, opp.priority_level)

    return {
        "score_breakdown": breakdown,
        "suggested_priority": suggested_priority,
        "score_description": desc,
    }


async def evaluate_opportunity(
    opportunity_id: int,
    db: AsyncSession,
    changed_by: str = "AI_SYSTEM",
    dry_run: bool = False,
) -> dict:
    """
    评估单个商机的优先级，必要时记录变更日志。

    参数:
      - opportunity_id: 商机 ID
      - db: 数据库会话
      - changed_by: 变更来源标识
      - dry_run: 为 True 时不实际写入数据库

    返回:
      与 compute_priority_score 字段一致，额外增加:
        - opportunity_id / opportunity_name
        - priority_changed: bool
        - change_log_id: Optional[int]
    """
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opp: Optional[Opportunity] = result.scalar_one_or_none()
    if not opp:
        raise ValueError(f"商机不存在: opportunity_id={opportunity_id}")

    score_result = compute_priority_score(opp)
    old_priority = opp.priority_level
    new_priority = score_result["suggested_priority"]
    priority_changed = old_priority != new_priority

    change_log_id = None
    if priority_changed and not dry_run:
        opp.priority_level = new_priority
        # 记录变更日志
        log_entry = PriorityChangeLog(
            opportunity_id=opportunity_id,
            old_priority=old_priority,
            new_priority=new_priority,
            change_reason=score_result["score_description"],
            changed_by=changed_by,
        )
        db.add(log_entry)
        await db.flush()
        await db.refresh(opp)
        change_log_id = log_entry.id
        logger.info(
            "优先级变更: opp_id=%s %s→%s reason=%s",
            opportunity_id, old_priority, new_priority,
            score_result["score_description"],
        )
    elif priority_changed and dry_run:
        logger.info(
            "[dry-run] 优先级将变更: opp_id=%s %s→%s reason=%s",
            opportunity_id, old_priority, new_priority,
            score_result["score_description"],
        )

    return {
        "opportunity_id": opportunity_id,
        "opportunity_name": opp.opportunity_name,
        "current_priority": old_priority,
        "suggested_priority": new_priority,
        "priority_changed": priority_changed,
        "score_breakdown": score_result["score_breakdown"],
        "reason": score_result["score_description"],
        "change_log_id": change_log_id,
        "evaluated_at": datetime.utcnow(),
    }


async def batch_evaluate(
    db: AsyncSession,
    opportunity_ids: Optional[list[int]] = None,
    filter_no_push_days_gt: Optional[int] = None,
    filter_priority_levels: Optional[list[int]] = None,
    dry_run: bool = True,
    changed_by: str = "AI_SYSTEM",
) -> dict:
    """
    批量评估商机优先级。

    参数与 evaluate_opportunity 类似，extra:
      - filter_no_push_days_gt: 只评估未推进天数大于此值的商机
      - filter_priority_levels: 只评估指定优先级的商机
    """
    query = select(Opportunity).options(
        selectinload(Opportunity.priority_change_logs),
    )

    if opportunity_ids:
        query = query.where(Opportunity.id.in_(opportunity_ids))
    if filter_no_push_days_gt is not None:
        query = query.where(
            (Opportunity.no_push_days > filter_no_push_days_gt)
            | (Opportunity.no_push_days.is_(None)),
        )
    if filter_priority_levels:
        query = query.where(Opportunity.priority_level.in_(filter_priority_levels))

    query = query.order_by(Opportunity.id)

    result = await db.execute(query)
    opportunities = result.scalars().unique().all()

    total = len(opportunities)
    changed = 0
    errors = 0
    results_list = []

    for opp in opportunities:
        try:
            eval_result = await evaluate_opportunity(
                opportunity_id=opp.id,
                db=db,
                changed_by=changed_by,
                dry_run=dry_run,
            )
            if eval_result["priority_changed"]:
                changed += 1
            results_list.append(eval_result)
        except Exception as exc:
            errors += 1
            logger.error("评估商机 %s 出错: %s", opp.id, exc)

    return {
        "total_evaluated": total,
        "priority_changed": changed,
        "errors": errors,
        "results": results_list,
    }


async def manual_adjust_priority(
    opportunity_id: int,
    new_priority: int,
    reason: str,
    db: AsyncSession,
    changed_by: str = "USER_MANUAL",
) -> dict:
    """
    手动调整商机优先级 —— 覆盖 AI 推荐结果，直接写入并记录日志。
    """
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Opportunity)
        .options(
            selectinload(Opportunity.account_manager),
            selectinload(Opportunity.branch_director),
        )
        .where(Opportunity.id == opportunity_id)
    )
    opp: Optional[Opportunity] = result.scalar_one_or_none()
    if not opp:
        raise ValueError(f"商机不存在: opportunity_id={opportunity_id}")

    old_priority = opp.priority_level
    opp.priority_level = new_priority

    log_entry = PriorityChangeLog(
        opportunity_id=opportunity_id,
        old_priority=old_priority,
        new_priority=new_priority,
        change_reason=reason,
        changed_by=changed_by,
    )
    db.add(log_entry)
    await db.flush()
    await db.refresh(opp)

    # 发送优先级变更通知邮件
    await _send_priority_change_email(opp, old_priority, new_priority, reason, db)

    return {
        "opportunity_id": opportunity_id,
        "opportunity_name": opp.opportunity_name,
        "old_priority": old_priority,
        "new_priority": new_priority,
        "reason": reason,
        "changed_by": changed_by,
        "changed_at": datetime.utcnow(),
    }


async def _send_priority_change_email(
    opp: Opportunity,
    old_priority: int,
    new_priority: int,
    reason: str,
    db: AsyncSession,
):
    """优先级变更时向相关人员发送通知邮件"""
    try:
        from app.services.email_service import send_email, render_template
        from app.models.email_log import EmailLog

        recipients = []
        if opp.account_manager and opp.account_manager.email:
            recipients.append(opp.account_manager)
        if opp.branch_director and opp.branch_director.email:
            recipients.append(opp.branch_director)
        if not recipients:
            return

        _PRIORITY_NAMES = {1: "高", 2: "中", 3: "低"}
        old_label = _PRIORITY_NAMES.get(old_priority, str(old_priority))
        new_label = _PRIORITY_NAMES.get(new_priority, str(new_priority))

        subject, body = render_template(
            "priority_change",
            opportunity_name=opp.opportunity_name,
            customer_name=opp.customer_name,
            old_priority=old_label,
            new_priority=new_label,
            reason=reason,
            system_link="",
        )

        for user in recipients:
            success = await send_email(user.email, subject, body, db)
            log = EmailLog(
                opportunity_id=opp.id,
                recipient_id=user.id,
                recipient_email=user.email,
                email_type="priority_change",
                subject=subject,
                content=body,
                status="sent" if success else "failed",
                sent_at=datetime.utcnow() if success else None,
                error_message=None if success else "发送失败",
            )
            db.add(log)

        await db.flush()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"优先级变更邮件发送失败 (opportunity={opp.id}): {e}"
        )


async def get_priority_change_logs(
    opportunity_id: int,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """获取某个商机的优先级变更历史"""
    query = (
        select(PriorityChangeLog)
        .where(PriorityChangeLog.opportunity_id == opportunity_id)
        .order_by(PriorityChangeLog.created_at.desc())
    )
    count_query = select(func.count(PriorityChangeLog.id)).where(
        PriorityChangeLog.opportunity_id == opportunity_id,
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    result = await db.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )
    logs = result.scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": log.id,
                "opportunity_id": log.opportunity_id,
                "old_priority": log.old_priority,
                "new_priority": log.new_priority,
                "change_reason": log.change_reason,
                "changed_by": log.changed_by,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }


async def get_priority_distribution(db: AsyncSession) -> dict:
    """获取当前所有商机的优先级分布统计"""
    query = select(
        Opportunity.priority_level,
        func.count(Opportunity.id).label("cnt"),
        func.sum(Opportunity.predicted_amount).label("total_amount"),
    ).group_by(Opportunity.priority_level).order_by(Opportunity.priority_level)

    result = await db.execute(query)
    rows = result.all()

    distribution = []
    total_opps = 0
    total_amount = Decimal(0)
    for row in rows:
        count = row.cnt
        amt = row.total_amount if row.total_amount else Decimal(0)
        total_opps += count
        total_amount += amt
        distribution.append({
            "priority_level": row.priority_level,
            "priority_label": PRIORITY_LABELS.get(row.priority_level, "未知"),
            "count": count,
            "total_amount": float(amt) if amt else None,
        })

    return {
        "distribution": distribution,
        "total_opportunities": total_opps,
        "total_amount": float(total_amount) if total_amount else None,
    }
