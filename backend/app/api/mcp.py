"""
MCP Agent API — 供外部 Agent 调用的接口
支持用户名密码认证，查询和更新自己相关的商机信息
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.opportunity import Opportunity
from app.models.opportunity_progress import OpportunityProgress
from app.models.user import User
from app.schemas.opportunity import OpportunityResponse, OpportunityListResponse
from app.schemas.progress import ProgressCreate, ProgressResponse
from app.api.progress import _build_weekly_progress, _auto_analyze, _notify_progress_update

router = APIRouter(prefix="/api/mcp", tags=["MCP Agent接口"])


# ---------------------------------------------------------------------------
# 认证
# ---------------------------------------------------------------------------

class AgentLoginRequest(BaseModel):
    username: str
    password: str


class AgentTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    real_name: str
    role: str


@router.post("/auth/login", response_model=AgentTokenResponse)
async def agent_login(request: AgentLoginRequest, db: AsyncSession = Depends(get_db)):
    """Agent 登录认证，返回 JWT token"""
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "real_name": user.real_name}
    )
    return AgentTokenResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        real_name=user.real_name,
        role=user.role,
    )


# ---------------------------------------------------------------------------
# JWT 认证依赖
# ---------------------------------------------------------------------------

from fastapi import Header
from app.core.security import decode_access_token


async def get_agent_user(
    authorization: str = Header(..., description="Bearer <token>"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """从 Authorization header 提取 Agent 用户信息"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的认证格式")

    token = authorization[7:]
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="无效或过期的token")

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(status_code=401, detail="无效的token")

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="无效的token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "role": user.role,
    }


# ---------------------------------------------------------------------------
# 商机查询
# ---------------------------------------------------------------------------

class AgentOpportunityQuery(BaseModel):
    page: int = 1
    page_size: int = 20
    status: Optional[str] = None
    keyword: Optional[str] = None


@router.post("/opportunities/query", response_model=OpportunityListResponse)
async def agent_query_opportunities(
    query: AgentOpportunityQuery,
    current_user: dict = Depends(get_agent_user),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户相关的商机列表"""
    base_query = select(Opportunity).options(
        selectinload(Opportunity.division_member),
        selectinload(Opportunity.account_manager),
        selectinload(Opportunity.branch_director),
    )
    base_count = select(func.count(Opportunity.id))

    # 按角色过滤
    user_role = current_user["role"]
    user_id = current_user["id"]
    if user_role == "项目经理":
        base_query = base_query.where(Opportunity.division_member_id == user_id)
        base_count = base_count.where(Opportunity.division_member_id == user_id)
    elif user_role == "客户经理":
        base_query = base_query.where(Opportunity.account_manager_id == user_id)
        base_count = base_count.where(Opportunity.account_manager_id == user_id)
    elif user_role == "责任支局长":
        base_query = base_query.where(Opportunity.branch_director_id == user_id)
        base_count = base_count.where(Opportunity.branch_director_id == user_id)
    # 管理员可看所有

    if query.status:
        base_query = base_query.where(Opportunity.opportunity_status == query.status)
        base_count = base_count.where(Opportunity.opportunity_status == query.status)
    if query.keyword:
        from sqlalchemy import or_
        kw_filter = or_(
            Opportunity.opportunity_name.ilike(f"%{query.keyword}%"),
            Opportunity.customer_name.ilike(f"%{query.keyword}%"),
        )
        base_query = base_query.where(kw_filter)
        base_count = base_count.where(kw_filter)

    total_result = await db.execute(base_count)
    total = total_result.scalar()

    query_sql = base_query.order_by(Opportunity.id.desc()).offset(
        (query.page - 1) * query.page_size
    ).limit(query.page_size)
    result = await db.execute(query_sql)
    items = result.scalars().unique().all()

    return OpportunityListResponse(
        total=total,
        page=query.page,
        page_size=query.page_size,
        items=[OpportunityResponse.model_validate(o) for o in items],
    )


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
async def agent_get_opportunity(
    opportunity_id: int,
    current_user: dict = Depends(get_agent_user),
    db: AsyncSession = Depends(get_db),
):
    """获取商机详情"""
    query = (
        select(Opportunity)
        .options(
            selectinload(Opportunity.division_member),
            selectinload(Opportunity.account_manager),
            selectinload(Opportunity.branch_director),
        )
        .where(Opportunity.id == opportunity_id)
    )

    user_role = current_user["role"]
    user_id = current_user["id"]
    if user_role == "项目经理":
        query = query.where(Opportunity.division_member_id == user_id)
    elif user_role == "客户经理":
        query = query.where(Opportunity.account_manager_id == user_id)
    elif user_role == "责任支局长":
        query = query.where(Opportunity.branch_director_id == user_id)

    result = await db.execute(query)
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在或无权访问")
    return OpportunityResponse.model_validate(opp)


# ---------------------------------------------------------------------------
# 商机更新（有限字段）
# ---------------------------------------------------------------------------

class AgentOpportunityUpdate(BaseModel):
    """Agent 可更新的商机字段（受限子集）"""
    opportunity_status: Optional[str] = None
    requirement_detail: Optional[str] = None
    remarks: Optional[str] = None
    estimated_sign_date: Optional[date] = None
    final_amount: Optional[float] = None
    contract_code: Optional[str] = None


@router.put("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
async def agent_update_opportunity(
    opportunity_id: int,
    data: AgentOpportunityUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_agent_user),
    db: AsyncSession = Depends(get_db),
):
    """更新商机信息（仅允许部分字段）"""
    query = select(Opportunity).where(Opportunity.id == opportunity_id)

    user_role = current_user["role"]
    user_id = current_user["id"]
    if user_role == "项目经理":
        query = query.where(Opportunity.division_member_id == user_id)
    elif user_role == "客户经理":
        query = query.where(Opportunity.account_manager_id == user_id)
    elif user_role == "责任支局长":
        query = query.where(Opportunity.branch_director_id == user_id)

    result = await db.execute(query)
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在或无权更新")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(opp, field, value)

    opp.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(opp)

    # Reload with relationships
    reload = await db.execute(
        select(Opportunity)
        .options(
            selectinload(Opportunity.division_member),
            selectinload(Opportunity.account_manager),
            selectinload(Opportunity.branch_director),
        )
        .where(Opportunity.id == opportunity_id)
    )
    opp = reload.scalar_one()

    # 异步触发 AI 分析
    background_tasks.add_task(_auto_analyze_on_update, opportunity_id)

    return OpportunityResponse.model_validate(opp)


async def _auto_analyze_on_update(opportunity_id: int):
    """商机更新后自动触发 AI 分析（后台任务）"""
    try:
        from app.core.database import async_session
        from app.services.ai_engine import analyze_opportunity_full
        async with async_session() as session:
            await analyze_opportunity_full(opportunity_id, session)
            await session.commit()
            import logging
            logging.getLogger(__name__).info(f"MCP商机更新AI分析完成: opportunity_id={opportunity_id}")
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(f"MCP商机更新AI分析失败 (opportunity={opportunity_id}): {e}")


async def _send_risk_alert_sync(opportunity_id: int, analysis_result: dict):
    """高风险时异步发送预警邮件（MCP 进度同步分析后调用）"""
    try:
        from app.core.database import async_session
        async with async_session() as db:
            from app.services.email_service import send_email, render_template
            from app.models.email_log import EmailLog

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

            recipients = []
            if opp.division_member and opp.division_member.email:
                recipients.append(opp.division_member)
            if opp.account_manager and opp.account_manager.email:
                recipients.append(opp.account_manager)
            if opp.branch_director and opp.branch_director.email:
                recipients.append(opp.branch_director)
            if not recipients:
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

            from datetime import datetime
            for user in recipients:
                success = await send_email(user.email, subject, body, db)
                log = EmailLog(
                    opportunity_id=opportunity_id,
                    recipient_id=user.id,
                    recipient_email=user.email,
                    email_type="ai_alert",
                    subject=subject,
                    content=body,
                    status="sent" if success else "failed",
                    sent_at=datetime.utcnow() if success else None,
                )
                db.add(log)
            await db.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(f"MCP高风险预警邮件发送失败 (opportunity={opportunity_id}): {e}")


# ---------------------------------------------------------------------------
# 进度提交
# ---------------------------------------------------------------------------

class AgentProgressCreate(BaseModel):
    progress_content: str
    progress_date: Optional[date] = None


class AgentProgressWithAIResponse(BaseModel):
    """进度创建结果（含 AI 分析建议）"""
    progress: ProgressResponse
    ai_analysis: Optional[dict] = None
    ai_analysis_error: Optional[str] = None


@router.post("/opportunities/{opportunity_id}/progress", response_model=AgentProgressWithAIResponse, status_code=status.HTTP_201_CREATED)
async def agent_create_progress(
    opportunity_id: int,
    data: AgentProgressCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_agent_user),
    db: AsyncSession = Depends(get_db),
):
    """为商机添加进度记录，并同步返回 AI 分析建议"""
    query = select(Opportunity).where(Opportunity.id == opportunity_id)

    user_role = current_user["role"]
    user_id = current_user["id"]
    if user_role == "项目经理":
        query = query.where(Opportunity.division_member_id == user_id)
    elif user_role == "客户经理":
        query = query.where(Opportunity.account_manager_id == user_id)
    elif user_role == "责任支局长":
        query = query.where(Opportunity.branch_director_id == user_id)

    result = await db.execute(query)
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在或无权操作")

    progress_date = data.progress_date or date.today()

    prog = OpportunityProgress(
        opportunity_id=opportunity_id,
        updater_id=user_id,
        updater_role=user_role,
        progress_content=data.progress_content,
        progress_date=progress_date,
        week_number=int(progress_date.strftime("%Y%U")),
    )
    db.add(prog)
    await db.flush()
    await db.refresh(prog)
    await db.refresh(prog, ["updater"])

    # Update opportunity fields
    opp.weekly_progress = _build_weekly_progress(opp, prog)
    opp.last_push_date = progress_date
    opp.no_push_days = 0
    opp.no_push_flag = 0
    await db.flush()

    # 同步执行 AI 分析，将结果返回给 Agent
    ai_result = None
    ai_error = None
    try:
        from app.services.ai_engine import analyze_progress_text
        # 加载最近进度文本供 AI 分析
        recent_progress = await db.execute(
            select(OpportunityProgress)
            .options(selectinload(OpportunityProgress.updater))
            .where(OpportunityProgress.opportunity_id == opportunity_id)
            .order_by(OpportunityProgress.created_at.asc())
            .limit(10)
        )
        records = recent_progress.scalars().all()
        if records:
            lines = []
            for pr in records:
                date_str = pr.progress_date.isoformat() if pr.progress_date else ""
                role = pr.updater_role or ""
                name = pr.updater.real_name if pr.updater else ""
                lines.append(f"[{date_str}] {role}-{name}: {pr.progress_content}")
            combined_text = "\n".join(lines)
            ai_result = await analyze_progress_text(opportunity_id, combined_text, db)

            # 高风险时发送预警邮件（异步）
            risk_level = ai_result.get("risk_level") or ""
            if risk_level in ("critical", "high"):
                background_tasks.add_task(_send_risk_alert_sync, opportunity_id, ai_result)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(f"MCP同步AI分析失败 (opportunity={opportunity_id}): {e}")
        ai_error = str(e)

    # Notify related people (exclude the submitter)
    background_tasks.add_task(
        _notify_progress_update, opportunity_id, user_id, data.progress_content
    )

    return AgentProgressWithAIResponse(
        progress=ProgressResponse.model_validate(prog),
        ai_analysis=ai_result,
        ai_analysis_error=ai_error,
    )


@router.get("/opportunities/{opportunity_id}/progress")
async def agent_list_progress(
    opportunity_id: int,
    current_user: dict = Depends(get_agent_user),
    db: AsyncSession = Depends(get_db),
):
    """获取商机的进度历史"""
    query = select(Opportunity).where(Opportunity.id == opportunity_id)

    user_role = current_user["role"]
    user_id = current_user["id"]
    if user_role == "项目经理":
        query = query.where(Opportunity.division_member_id == user_id)
    elif user_role == "客户经理":
        query = query.where(Opportunity.account_manager_id == user_id)
    elif user_role == "责任支局长":
        query = query.where(Opportunity.branch_director_id == user_id)

    result = await db.execute(query)
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在或无权访问")

    count_query = select(func.count(OpportunityProgress.id)).where(
        OpportunityProgress.opportunity_id == opportunity_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    progress_query = (
        select(OpportunityProgress)
        .options(selectinload(OpportunityProgress.updater))
        .where(OpportunityProgress.opportunity_id == opportunity_id)
        .order_by(OpportunityProgress.created_at.desc())
    )
    result = await db.execute(progress_query)
    items = result.scalars().all()

    return {
        "total": total,
        "items": [ProgressResponse.model_validate(p) for p in items],
    }


# ---------------------------------------------------------------------------
# Agent 信息
# ---------------------------------------------------------------------------

@router.get("/me")
async def agent_get_me(current_user: dict = Depends(get_agent_user)):
    """获取当前 Agent 用户信息"""
    return current_user


# ---------------------------------------------------------------------------
# 钉钉直接推送
# ---------------------------------------------------------------------------

class AgentDingtalkSend(BaseModel):
    title: str
    content: str
    at_mobiles: Optional[list[str]] = None
    at_all: bool = False


@router.post("/dingtalk/send")
async def agent_send_dingtalk(
    data: AgentDingtalkSend,
    current_user: dict = Depends(get_agent_user),
    db: AsyncSession = Depends(get_db),
):
    """直接发送钉钉群机器人消息"""
    from app.services.dingtalk_service import send_dingtalk_message, _save_dingtalk_log

    success = await send_dingtalk_message(
        title=data.title,
        content=data.content,
        at_mobiles=data.at_mobiles,
        at_all=data.at_all,
        db_session=db,
    )

    await _save_dingtalk_log(
        db=db,
        title=data.title,
        content=data.content,
        status="sent" if success else "failed",
        msg_type="agent_direct",
        opportunity_id=None,
        at_mobiles=data.at_mobiles,
    )

    if not success:
        raise HTTPException(status_code=502, detail="钉钉消息发送失败，请检查 Webhook 配置")

    return {"success": True, "message": "钉钉消息发送成功"}
