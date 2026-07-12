import asyncio
import logging
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db, async_session
from app.core.security import get_current_user
from app.models.opportunity import Opportunity
from app.models.opportunity_progress import OpportunityProgress
from app.models.user import User
from app.schemas.progress import ProgressCreate, ProgressResponse, ProgressUpdate, ProgressListResponse

router = APIRouter(prefix="/api/opportunities", tags=["进度协作"])
logger = logging.getLogger(__name__)


def _can_access_opportunity(opp: Opportunity, user_role: str, user_id: int) -> bool:
    """Check if a user can access the given opportunity based on role"""
    if user_role == "管理员":
        return True
    if user_role == "项目经理" and opp.division_member_id == user_id:
        return True
    if user_role == "客户经理" and opp.account_manager_id == user_id:
        return True
    if user_role == "责任支局长" and opp.branch_director_id == user_id:
        return True
    return False


def _calc_week_number(d: date) -> int:
    """计算年度第几周"""
    return int(d.strftime("%Y%U"))


def _build_weekly_progress(opp: Opportunity, new_progress: OpportunityProgress) -> str:
    """拼接最新的 weekly_progress，把新进度按角色时间戳格式追加"""
    ts = new_progress.progress_date.strftime("%Y-%m-%d")
    role = new_progress.updater_role or ""
    name = new_progress.updater.real_name if new_progress.updater else ""
    new_entry = f"[{ts}] {role}-{name}：{new_progress.progress_content}"

    old = opp.weekly_progress or ""
    if old:
        return f"{new_entry}\n{old}"
    return new_entry


@router.get("/{opportunity_id}/progress", response_model=ProgressListResponse)
async def list_progress(
    opportunity_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取商机的进度历史（需认证，按角色过滤访问权限）"""
    # Verify opportunity exists and user has access
    opp_result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opp = opp_result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在")

    # Check role-based access
    user_role = current_user.get("role")
    user_id = current_user.get("id")
    if not _can_access_opportunity(opp, user_role, user_id):
        raise HTTPException(status_code=403, detail="无权访问此商机的进度记录")

    count_query = select(func.count(OpportunityProgress.id)).where(
        OpportunityProgress.opportunity_id == opportunity_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = (
        select(OpportunityProgress)
        .options(selectinload(OpportunityProgress.updater))
        .where(OpportunityProgress.opportunity_id == opportunity_id)
        .order_by(OpportunityProgress.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return ProgressListResponse(
        total=total,
        items=[ProgressResponse.model_validate(p) for p in items],
    )


@router.post("/{opportunity_id}/progress", response_model=ProgressResponse, status_code=status.HTTP_201_CREATED)
async def create_progress(
    opportunity_id: int,
    data: ProgressCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交新的进度记录"""
    current_user_id = current_user["id"]
    # Load opportunity + user
    opp_result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opp = opp_result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在")

    user_result = await db.execute(select(User).where(User.id == current_user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # Create progress record
    prog = OpportunityProgress(
        opportunity_id=opportunity_id,
        updater_id=current_user_id,
        updater_role=user.role or "",
        progress_content=data.progress_content,
        progress_date=data.progress_date,
        week_number=_calc_week_number(data.progress_date or date.today()),
    )
    db.add(prog)
    await db.flush()
    await db.refresh(prog)

    # Reload with updater
    await db.refresh(prog, ["updater"])

    # Auto-update weekly_progress in opportunities table
    opp.weekly_progress = _build_weekly_progress(opp, prog)
    opp.last_push_date = date.today()
    opp.no_push_days = 0
    opp.no_push_flag = 0

    await db.flush()
    await db.refresh(opp)

    # 异步触发 AI 分析（不阻塞用户）
    logger.info(f"进度提交: 商机 {opportunity_id} 提交成功，准备触发 AI 分析")
    background_tasks.add_task(_auto_analyze, opportunity_id)
    logger.info(f"进度提交: 商机 {opportunity_id} AI 分析任务已添加到后台")

    # Step 4：异步通知相关人员（排除提交者自己）
    background_tasks.add_task(
        _notify_progress_update, opportunity_id, current_user_id, data.progress_content
    )

    return ProgressResponse.model_validate(prog)


async def _auto_analyze(opportunity_id: int):
    """后台自动执行 AI 分析（聚合最近进度含角色信息，供 AI 检测说法冲突）"""
    try:
        async with async_session() as session:
            from app.services.ai_engine import analyze_progress_text
            from app.models.opportunity_progress import OpportunityProgress

            # 加载最近 10 条进度记录（含更新人信息）
            result = await session.execute(
                select(OpportunityProgress)
                .options(selectinload(OpportunityProgress.updater))
                .where(OpportunityProgress.opportunity_id == opportunity_id)
                .order_by(OpportunityProgress.created_at.asc())  # 正序：旧→新
                .limit(10)
            )
            records = result.scalars().all()
            if not records:
                logger.info(f"AI 自动分析: 商机 {opportunity_id} 无进度记录，跳过")
                return

            # 拼接多行文本，每行带角色和日期
            lines = []
            for pr in records:
                date_str = pr.progress_date.isoformat() if pr.progress_date else ""
                role = pr.updater_role or ""
                name = pr.updater.real_name if pr.updater else ""
                line = f"[{date_str}] {role}-{name}: {pr.progress_content}"
                lines.append(line)

            combined_text = "\n".join(lines)
            logger.info(f"AI 自动分析: 商机 {opportunity_id} 开始分析")
            analysis_result = await analyze_progress_text(opportunity_id, combined_text, session)
            logger.info(f"AI 自动分析: 商机 {opportunity_id} 完成，风险等级={analysis_result.get('risk_level')}")

            # Step 3：AI 检测到高风险时发送预警邮件
            risk_level = analysis_result.get("risk_level") or ""
            if risk_level in ("critical", "high"):
                logger.info(f"AI 自动分析: 商机 {opportunity_id} 检测到高风险，准备发送邮件")
                await _send_risk_alert(opportunity_id, analysis_result, session)
            else:
                logger.info(f"AI 自动分析: 商机 {opportunity_id} 风险等级={risk_level}，无需发送邮件")

    except Exception as e:
        logger.exception(f"AI 自动分析失败 (opportunity={opportunity_id}): {e}")


async def _send_risk_alert(opportunity_id: int, analysis_result: dict, db: AsyncSession):
    """AI 检测到高风险时，向项目经理、客户经理和责任支局长发送预警邮件"""
    try:
        from app.services.email_service import send_email, render_template
        from app.models.email_log import EmailLog

        # 加载商机及相关人员
        row = await db.execute(
            select(Opportunity)
            .options(
                selectinload(Opportunity.division_member),
                selectinload(Opportunity.account_manager),
                selectinload(Opportunity.branch_director),
            )
            .where(Opportunity.id == opportunity_id)
        )
        opp = row.scalar_one_or_none()
        if not opp:
            logger.warning(f"邮件发送: 商机 {opportunity_id} 不存在")
            return

        recipients = []
        # 项目经理
        if opp.division_member and opp.division_member.email:
            recipients.append(opp.division_member)
            logger.info(f"邮件发送: 收件人-项目经理 {opp.division_member.real_name} ({opp.division_member.email})")
        # 客户经理
        if opp.account_manager and opp.account_manager.email:
            recipients.append(opp.account_manager)
            logger.info(f"邮件发送: 收件人-客户经理 {opp.account_manager.real_name} ({opp.account_manager.email})")
        # 责任支局长
        if opp.branch_director and opp.branch_director.email:
            recipients.append(opp.branch_director)
            logger.info(f"邮件发送: 收件人-责任支局长 {opp.branch_director.real_name} ({opp.branch_director.email})")
        if not recipients:
            logger.warning(f"邮件发送: 商机 {opportunity_id} 无收件人")
            return

        subject, body = render_template(
            "ai_alert",
            opportunity_name=opp.opportunity_name,
            customer_name=opp.customer_name,
            predicted_amount=opp.predicted_amount or "未知",
            risk_signals=analysis_result.get("risk_signals", []),
            suggested_actions=analysis_result.get("suggested_actions", []),
            system_link="",
        )

        for user in recipients:
            logger.info(f"邮件发送: 向 {user.email} 发送 AI 风险预警邮件")
            success = await send_email(user.email, subject, body, db)
            logger.info(f"邮件发送: {user.email} 发送结果={'成功' if success else '失败'}")
            log = EmailLog(
                opportunity_id=opportunity_id,
                recipient_id=user.id,
                recipient_email=user.email,
                email_type="ai_alert",
                subject=subject,
                content=body,
                status="sent" if success else "failed",
                sent_at=datetime.utcnow() if success else None,
                error_message=None if success else "发送失败",
            )
            db.add(log)

        await db.flush()
        logger.info(f"邮件发送: 商机 {opportunity_id} 邮件日志已保存")

        # 钉钉通知
        from app.services.dingtalk_service import notify_ai_alert
        await notify_ai_alert(opportunity_id, analysis_result, db)
    except Exception as e:
        logger.exception(f"AI 风险预警邮件发送失败 (opportunity={opportunity_id}): {e}")


async def _notify_progress_update(
    opportunity_id: int,
    current_user_id: int,
    progress_content: str,
):
    """提交进度后，通知相关角色（排除提交者本人）"""
    try:
        async with async_session() as db:
            from app.services.email_service import send_email, render_template
            from app.models.email_log import EmailLog

            # 加载商机及相关人员
            row = await db.execute(
                select(Opportunity)
                .options(
                    selectinload(Opportunity.division_member),
                    selectinload(Opportunity.account_manager),
                    selectinload(Opportunity.branch_director),
                )
                .where(Opportunity.id == opportunity_id)
            )
            opp = row.scalar_one_or_none()
            if not opp:
                return

            # 加载提交者信息
            user_row = await db.execute(select(User).where(User.id == current_user_id))
            updater = user_row.scalar_one_or_none()
            updater_name = updater.real_name if updater else "未知"
            updater_role = updater.role if updater else ""

            recipients = []
            # 项目经理
            if opp.division_member and opp.division_member.email and opp.division_member.id != current_user_id:
                recipients.append(opp.division_member)
            # 客户经理
            if opp.account_manager and opp.account_manager.email and opp.account_manager.id != current_user_id:
                recipients.append(opp.account_manager)
            # 责任支局长
            if opp.branch_director and opp.branch_director.email and opp.branch_director.id != current_user_id:
                recipients.append(opp.branch_director)
            if not recipients:
                return

            subject, body = render_template(
                "progress_update",
                opportunity_name=opp.opportunity_name,
                updater_name=updater_name,
                updater_role=updater_role,
                update_time=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                progress_content=progress_content,
                system_link="",
            )

            for user in recipients:
                success = await send_email(user.email, subject, body, db)
                log = EmailLog(
                    opportunity_id=opportunity_id,
                    recipient_id=user.id,
                    recipient_email=user.email,
                    email_type="progress_update",
                    subject=subject,
                    content=body,
                    status="sent" if success else "failed",
                    sent_at=datetime.utcnow() if success else None,
                    error_message=None if success else "发送失败",
                )
                db.add(log)

            await db.flush()

            # 钉钉通知
            from app.services.dingtalk_service import notify_progress_update
            await notify_progress_update(opportunity_id, current_user_id, progress_content, db)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"进度通知邮件发送失败 (opportunity={opportunity_id}): {e}"
        )


@router.put("/{opportunity_id}/progress/{progress_id}", response_model=ProgressResponse)
async def update_progress(
    opportunity_id: int,
    progress_id: int,
    data: ProgressUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改进度记录（仅限本人，24h内）"""
    current_user_id = current_user["id"]
    result = await db.execute(
        select(OpportunityProgress)
        .options(selectinload(OpportunityProgress.updater))
        .where(
            OpportunityProgress.id == progress_id,
            OpportunityProgress.opportunity_id == opportunity_id,
        )
    )
    prog = result.scalar_one_or_none()
    if not prog:
        raise HTTPException(status_code=404, detail="进度记录不存在")

    if prog.updater_id != current_user_id:
        raise HTTPException(status_code=403, detail="仅可修改自己的进度记录")

    # 24h check - normalize both to naive UTC for safe comparison
    if prog.created_at:
        now = datetime.utcnow()
        created = prog.created_at.replace(tzinfo=None) if prog.created_at.tzinfo else prog.created_at
        delta = now - created
        if delta.total_seconds() > 86400:
            raise HTTPException(status_code=400, detail="已超过24小时修改时限")

    if data.progress_content is not None:
        prog.progress_content = data.progress_content

    await db.flush()
    return ProgressResponse.model_validate(prog)
