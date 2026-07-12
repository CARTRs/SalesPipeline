"""
钉钉群聊机器人服务 — 异步Webhook发送、签名验证、Markdown消息构建、日志记录
"""
import hashlib
import hmac
import base64
import json
import logging
import time
import urllib.parse
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.system_config import SystemConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

async def _load_dingtalk_config(db_session=None) -> dict:
    """从 system_configs 加载钉钉配置，回退到环境变量"""
    config = {
        "webhook_url": "",
        "secret": "",
        "enabled": "false",
        "notify_types": json.dumps([
            "progress_update", "ai_alert", "priority_change",
            "bid_approach", "no_push_warn", "weekly_remind",
        ]),
    }

    keys = [
        "dingtalk_webhook_url", "dingtalk_secret",
        "dingtalk_enabled", "dingtalk_notify_types",
    ]

    if db_session is not None:
        try:
            result = await db_session.execute(
                select(SystemConfig).where(SystemConfig.config_key.in_(keys))
            )
            for item in result.scalars().all():
                if item.config_key == "dingtalk_webhook_url":
                    config["webhook_url"] = item.config_value or ""
                elif item.config_key == "dingtalk_secret":
                    config["secret"] = item.config_value or ""
                elif item.config_key == "dingtalk_enabled":
                    config["enabled"] = item.config_value or "false"
                elif item.config_key == "dingtalk_notify_types":
                    config["notify_types"] = item.config_value or config["notify_types"]
        except Exception as e:
            logger.warning(f"从数据库加载钉钉配置失败: {e}")

    return config


def _is_notify_type_enabled(config: dict, notify_type: str) -> bool:
    """检查指定通知类型是否启用"""
    try:
        types = json.loads(config.get("notify_types", "[]"))
        return notify_type in types
    except (json.JSONDecodeError, TypeError):
        return True  # 解析失败时默认启用


# ---------------------------------------------------------------------------
# 签名生成
# ---------------------------------------------------------------------------

def _sign_request(secret: str, timestamp: int) -> str:
    """HMAC-SHA256 签名，返回 URL 查询参数"""
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode("utf-8"))
    return f"&timestamp={timestamp}&sign={sign}"


# ---------------------------------------------------------------------------
# 消息构建 — Markdown 格式
# ---------------------------------------------------------------------------

def _build_at_suffix(mobiles: list[str]) -> str:
    """构建 @手机号 的文本后缀"""
    if not mobiles:
        return ""
    return "\n\n" + " ".join(f"@{m}" for m in mobiles if m)


def build_progress_update_msg(
    opportunity_name: str,
    customer_name: str,
    updater_name: str,
    updater_role: str,
    update_time: str,
    progress_content: str,
    system_link: str = "",
    at_mobiles: list[str] = None,
) -> tuple[str, str]:
    """构建进度更新通知消息，返回 (title, markdown_content)"""
    title = f"📝 进度更新 — {opportunity_name}"
    content = (
        f"### 📝 进度更新通知\n"
        f"**商机**: {opportunity_name}\n"
        f"**客户**: {customer_name}\n"
        f"**更新人**: {updater_name}（{updater_role}）\n"
        f"**时间**: {update_time}\n\n"
        f"> {progress_content}\n"
    )
    if system_link:
        content += f"\n[查看系统详情]({system_link})"
    content += _build_at_suffix(at_mobiles or [])
    return title, content


def build_ai_alert_msg(
    opportunity_name: str,
    customer_name: str,
    predicted_amount,
    risk_level: str,
    risk_signals: list[dict],
    suggested_actions: list[str],
    system_link: str = "",
    at_mobiles: list[str] = None,
) -> tuple[str, str]:
    """构建AI风险预警消息"""
    level_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    emoji = level_emoji.get(risk_level, "⚠️")

    title = f"{emoji} AI风险预警 — {opportunity_name}"
    content = (
        f"### {emoji} AI 风险预警\n"
        f"**商机**: {opportunity_name}\n"
        f"**客户**: {customer_name}\n"
        f"**金额**: {predicted_amount}万元\n"
        f"**风险等级**: {risk_level.upper()}\n\n"
    )

    if risk_signals:
        content += "**风险信号**:\n"
        for sig in risk_signals:
            sig_type = sig.get("type", "")
            sig_desc = sig.get("description", "")
            content += f"- **[{sig_type}]** {sig_desc}\n"
        content += "\n"

    if suggested_actions:
        content += "**建议行动**:\n"
        for i, action in enumerate(suggested_actions, 1):
            content += f"{i}. {action}\n"

    if system_link:
        content += f"\n[查看系统详情]({system_link})"
    content += _build_at_suffix(at_mobiles or [])
    return title, content


def build_priority_change_msg(
    opportunity_name: str,
    customer_name: str,
    old_priority: str,
    new_priority: str,
    reason: str,
    system_link: str = "",
    at_mobiles: list[str] = None,
) -> tuple[str, str]:
    """构建优先级变更通知消息"""
    title = f"🔔 优先级变更 — {opportunity_name}"
    content = (
        f"### 🔔 优先级变更通知\n"
        f"**商机**: {opportunity_name}\n"
        f"**客户**: {customer_name}\n"
        f"**变更**: {old_priority} → **{new_priority}**\n"
        f"**原因**: {reason}\n"
    )
    if system_link:
        content += f"\n[查看系统详情]({system_link})"
    content += _build_at_suffix(at_mobiles or [])
    return title, content


def build_bid_approach_msg(
    opportunity_name: str,
    customer_name: str,
    estimated_sign_date: str,
    days: int,
    system_link: str = "",
    at_mobiles: list[str] = None,
) -> tuple[str, str]:
    """构建招标临近提醒消息"""
    title = f"⏰ 招标临近 — {opportunity_name}"
    content = (
        f"### ⏰ 招标临近提醒\n"
        f"**商机**: {opportunity_name}\n"
        f"**客户**: {customer_name}\n"
        f"**预计签约日期**: {estimated_sign_date}\n"
        f"**剩余天数**: **{days}** 天\n\n"
        f"请尽快确认投标方案并准备相关材料。\n"
    )
    if system_link:
        content += f"\n[查看系统详情]({system_link})"
    content += _build_at_suffix(at_mobiles or [])
    return title, content


def build_no_push_warn_msg(
    opportunity_name: str,
    customer_name: str,
    no_push_days: int,
    system_link: str = "",
    at_mobiles: list[str] = None,
) -> tuple[str, str]:
    """构建超期未推进预警消息"""
    title = f"⚠️ 超期未推进 — {opportunity_name}"
    content = (
        f"### ⚠️ 未推进超期预警\n"
        f"**商机**: {opportunity_name}\n"
        f"**客户**: {customer_name}\n"
        f"**未推进天数**: **{no_push_days}** 天\n\n"
        f"请尽快更新商机进展情况，避免商机流失。\n"
    )
    if system_link:
        content += f"\n[查看系统详情]({system_link})"
    content += _build_at_suffix(at_mobiles or [])
    return title, content


def build_weekly_remind_msg(
    director_name: str,
    opportunities: list[dict],
    system_link: str = "",
    at_mobiles: list[str] = None,
) -> tuple[str, str]:
    """构建周度待更新提醒消息"""
    title = "📋 本周待更新商机提醒"
    content = f"### 📋 本周待更新商机提醒\n**{director_name}**，以下是本周待更新进度的商机：\n\n"

    for opp in opportunities:
        content += (
            f"- **{opp['name']}**（{opp['customer']}）"
            f" — 未推进 **{opp['no_push_days']}** 天\n"
        )

    content += "\n请尽快更新商机进展情况。"
    if system_link:
        content += f"\n\n[前往系统更新]({system_link})"
    content += _build_at_suffix(at_mobiles or [])
    return title, content


# ---------------------------------------------------------------------------
# 底层发送
# ---------------------------------------------------------------------------

async def send_dingtalk_message(
    title: str,
    content: str,
    at_mobiles: list[str] = None,
    at_all: bool = False,
    db_session=None,
) -> bool:
    """
    发送钉钉群机器人消息（Markdown 格式）
    返回 True 表示成功，False 表示失败
    """
    config = await _load_dingtalk_config(db_session)

    if config["enabled"].lower() != "true":
        logger.debug("钉钉通知未启用，跳过发送")
        return False

    webhook_url = config["webhook_url"]
    if not webhook_url:
        logger.warning("钉钉 Webhook URL 未配置，跳过发送")
        return False

    # 构建请求URL（含签名）
    url = webhook_url
    secret = config.get("secret", "")
    if secret:
        timestamp = int(round(time.time() * 1000))
        sign_suffix = _sign_request(secret, timestamp)
        url = f"{webhook_url}{sign_suffix}"

    # 构建请求体
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": content,
        },
        "at": {
            "atMobiles": at_mobiles or [],
            "isAtAll": at_all,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            result = resp.json()

            if result.get("errcode") == 0:
                logger.info(f"钉钉消息发送成功: {title}")
                return True
            else:
                logger.warning(
                    f"钉钉消息发送失败: errcode={result.get('errcode')}, "
                    f"errmsg={result.get('errmsg')}"
                )
                return False
    except Exception as e:
        logger.error(f"钉钉消息发送异常: {e}")
        return False


# ---------------------------------------------------------------------------
# 日志记录
# ---------------------------------------------------------------------------

async def _save_dingtalk_log(
    db: AsyncSession,
    opportunity_id: int = None,
    recipient_ids: str = "",
    msg_type: str = "",
    title: str = "",
    content: str = "",
    at_mobiles: list[str] = None,
    status: str = "pending",
    error_message: str = None,
):
    """保存钉钉发送日志"""
    from app.models.dingtalk_log import DingtalkLog

    log = DingtalkLog(
        opportunity_id=opportunity_id,
        recipient_ids=recipient_ids,
        msg_type=msg_type,
        title=title,
        content=content,
        at_mobiles=json.dumps(at_mobiles or []),
        status=status,
        sent_at=datetime.utcnow() if status == "sent" else None,
        error_message=error_message,
    )
    db.add(log)
    await db.flush()


# ---------------------------------------------------------------------------
# 业务通知入口 — 6 个场景
# ---------------------------------------------------------------------------

async def notify_progress_update(
    opportunity_id: int,
    current_user_id: int,
    progress_content: str,
    db_session=None,
):
    """进度更新通知：@其他三角色成员"""
    try:
        async with (db_session or _get_session()) as db:
            from app.models.opportunity import Opportunity
            from app.models.user import User
            from sqlalchemy.orm import selectinload

            config = await _load_dingtalk_config(db)
            if not _is_notify_type_enabled(config, "progress_update"):
                return

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

            user_row = await db.execute(select(User).where(User.id == current_user_id))
            updater = user_row.scalar_one_or_none()
            updater_name = updater.real_name if updater else "未知"
            updater_role = updater.role if updater else ""

            # 收集通知对象（排除提交者）
            recipients = []
            mobiles = []
            for role_user in [opp.division_member, opp.account_manager, opp.branch_director]:
                if role_user and role_user.id != current_user_id and role_user.phone:
                    recipients.append(role_user)
                    mobiles.append(role_user.phone)

            if not recipients:
                return

            title, content = build_progress_update_msg(
                opportunity_name=opp.opportunity_name,
                customer_name=opp.customer_name,
                updater_name=updater_name,
                updater_role=updater_role,
                update_time=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                progress_content=progress_content,
                at_mobiles=mobiles,
            )

            success = await send_dingtalk_message(title, content, mobiles, db_session=db)
            await _save_dingtalk_log(
                db, opportunity_id,
                recipient_ids=",".join(str(r.id) for r in recipients),
                msg_type="progress_update",
                title=title, content=content, at_mobiles=mobiles,
                status="sent" if success else "failed",
            )
    except Exception as e:
        logger.exception(f"钉钉进度更新通知失败 (opportunity={opportunity_id}): {e}")


async def notify_ai_alert(
    opportunity_id: int,
    analysis_result: dict,
    db_session=None,
):
    """AI风险预警通知：@全部三角色成员"""
    try:
        async with (db_session or _get_session()) as db:
            from app.models.opportunity import Opportunity
            from sqlalchemy.orm import selectinload

            config = await _load_dingtalk_config(db)
            if not _is_notify_type_enabled(config, "ai_alert"):
                return

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
            mobiles = []
            for role_user in [opp.division_member, opp.account_manager, opp.branch_director]:
                if role_user and role_user.phone:
                    recipients.append(role_user)
                    mobiles.append(role_user.phone)

            if not recipients:
                return

            risk_level = analysis_result.get("risk_level") or analysis_result.get("ai_risk_level") or "medium"
            title, content = build_ai_alert_msg(
                opportunity_name=opp.opportunity_name,
                customer_name=opp.customer_name,
                predicted_amount=opp.predicted_amount or "未知",
                risk_level=risk_level,
                risk_signals=analysis_result.get("risk_signals", []),
                suggested_actions=analysis_result.get("suggested_actions", []),
                at_mobiles=mobiles,
            )

            success = await send_dingtalk_message(title, content, mobiles, db_session=db)
            await _save_dingtalk_log(
                db, opportunity_id,
                recipient_ids=",".join(str(r.id) for r in recipients),
                msg_type="ai_alert",
                title=title, content=content, at_mobiles=mobiles,
                status="sent" if success else "failed",
            )
    except Exception as e:
        logger.exception(f"钉钉AI风险预警通知失败 (opportunity={opportunity_id}): {e}")


async def notify_priority_change(
    opportunity_id: int,
    old_priority: int,
    new_priority: int,
    reason: str,
    db_session=None,
):
    """优先级变更通知：@客户经理+责任支局长"""
    _PRIORITY_NAMES = {1: "紧急", 2: "高", 3: "中", 4: "低"}
    try:
        async with (db_session or _get_session()) as db:
            from app.models.opportunity import Opportunity
            from sqlalchemy.orm import selectinload

            config = await _load_dingtalk_config(db)
            if not _is_notify_type_enabled(config, "priority_change"):
                return

            row = await db.execute(
                select(Opportunity)
                .options(
                    selectinload(Opportunity.account_manager),
                    selectinload(Opportunity.branch_director),
                )
                .where(Opportunity.id == opportunity_id)
            )
            opp = row.scalar_one_or_none()
            if not opp:
                return

            recipients = []
            mobiles = []
            for role_user in [opp.account_manager, opp.branch_director]:
                if role_user and role_user.phone:
                    recipients.append(role_user)
                    mobiles.append(role_user.phone)

            if not recipients:
                return

            title, content = build_priority_change_msg(
                opportunity_name=opp.opportunity_name,
                customer_name=opp.customer_name,
                old_priority=_PRIORITY_NAMES.get(old_priority, str(old_priority)),
                new_priority=_PRIORITY_NAMES.get(new_priority, str(new_priority)),
                reason=reason,
                at_mobiles=mobiles,
            )

            success = await send_dingtalk_message(title, content, mobiles, db_session=db)
            await _save_dingtalk_log(
                db, opportunity_id,
                recipient_ids=",".join(str(r.id) for r in recipients),
                msg_type="priority_change",
                title=title, content=content, at_mobiles=mobiles,
                status="sent" if success else "failed",
            )
    except Exception as e:
        logger.exception(f"钉钉优先级变更通知失败 (opportunity={opportunity_id}): {e}")


async def notify_bid_approach(
    opportunity_id: int,
    days: int,
    db_session=None,
):
    """招标临近通知：@客户经理+责任支局长"""
    try:
        async with (db_session or _get_session()) as db:
            from app.models.opportunity import Opportunity
            from sqlalchemy.orm import selectinload

            config = await _load_dingtalk_config(db)
            if not _is_notify_type_enabled(config, "bid_approach"):
                return

            row = await db.execute(
                select(Opportunity)
                .options(
                    selectinload(Opportunity.account_manager),
                    selectinload(Opportunity.branch_director),
                )
                .where(Opportunity.id == opportunity_id)
            )
            opp = row.scalar_one_or_none()
            if not opp:
                return

            recipients = []
            mobiles = []
            for role_user in [opp.account_manager, opp.branch_director]:
                if role_user and role_user.phone:
                    recipients.append(role_user)
                    mobiles.append(role_user.phone)

            if not recipients:
                return

            title, content = build_bid_approach_msg(
                opportunity_name=opp.opportunity_name,
                customer_name=opp.customer_name,
                estimated_sign_date=opp.estimated_sign_date.isoformat() if opp.estimated_sign_date else "未知",
                days=days,
                at_mobiles=mobiles,
            )

            success = await send_dingtalk_message(title, content, mobiles, db_session=db)
            await _save_dingtalk_log(
                db, opportunity_id,
                recipient_ids=",".join(str(r.id) for r in recipients),
                msg_type="bid_approach",
                title=title, content=content, at_mobiles=mobiles,
                status="sent" if success else "failed",
            )
    except Exception as e:
        logger.exception(f"钉钉招标临近通知失败 (opportunity={opportunity_id}): {e}")


async def notify_no_push_warn(
    opportunity_id: int,
    no_push_days: int,
    db_session=None,
):
    """超期未推进预警通知：@客户经理+责任支局长"""
    try:
        async with (db_session or _get_session()) as db:
            from app.models.opportunity import Opportunity
            from sqlalchemy.orm import selectinload

            config = await _load_dingtalk_config(db)
            if not _is_notify_type_enabled(config, "no_push_warn"):
                return

            row = await db.execute(
                select(Opportunity)
                .options(
                    selectinload(Opportunity.account_manager),
                    selectinload(Opportunity.branch_director),
                )
                .where(Opportunity.id == opportunity_id)
            )
            opp = row.scalar_one_or_none()
            if not opp:
                return

            recipients = []
            mobiles = []
            for role_user in [opp.account_manager, opp.branch_director]:
                if role_user and role_user.phone:
                    recipients.append(role_user)
                    mobiles.append(role_user.phone)

            if not recipients:
                return

            title, content = build_no_push_warn_msg(
                opportunity_name=opp.opportunity_name,
                customer_name=opp.customer_name,
                no_push_days=no_push_days,
                at_mobiles=mobiles,
            )

            success = await send_dingtalk_message(title, content, mobiles, db_session=db)
            await _save_dingtalk_log(
                db, opportunity_id,
                recipient_ids=",".join(str(r.id) for r in recipients),
                msg_type="no_push_warn",
                title=title, content=content, at_mobiles=mobiles,
                status="sent" if success else "failed",
            )
    except Exception as e:
        logger.exception(f"钉钉超期未推进通知失败 (opportunity={opportunity_id}): {e}")


async def notify_weekly_remind(
    director_id: int,
    opportunities: list[dict],
    db_session=None,
):
    """周度待更新提醒：@责任支局长"""
    try:
        async with (db_session or _get_session()) as db:
            from app.models.user import User

            config = await _load_dingtalk_config(db)
            if not _is_notify_type_enabled(config, "weekly_remind"):
                return

            user_row = await db.execute(select(User).where(User.id == director_id))
            user = user_row.scalar_one_or_none()
            if not user or not user.phone:
                return

            mobiles = [user.phone]
            title, content = build_weekly_remind_msg(
                director_name=user.real_name,
                opportunities=opportunities,
                at_mobiles=mobiles,
            )

            success = await send_dingtalk_message(title, content, mobiles, db_session=db)
            await _save_dingtalk_log(
                db,
                recipient_ids=str(director_id),
                msg_type="weekly_remind",
                title=title, content=content, at_mobiles=mobiles,
                status="sent" if success else "failed",
            )
    except Exception as e:
        logger.exception(f"钉钉周度提醒通知失败 (director={director_id}): {e}")


# ---------------------------------------------------------------------------
# 测试发送
# ---------------------------------------------------------------------------

async def test_dingtalk_connection(db_session=None) -> dict:
    """测试钉钉机器人连接，返回结果字典"""
    config = await _load_dingtalk_config(db_session)

    if config["enabled"].lower() != "true":
        return {"success": False, "message": "钉钉通知未启用"}

    if not config["webhook_url"]:
        return {"success": False, "message": "Webhook URL 未配置"}

    title = "🧪 连接测试"
    content = (
        "### 🧪 钉钉机器人连接测试\n"
        "**状态**: 连接成功 ✅\n"
        f"**时间**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "商机智能跟踪与预警系统已成功连接到此群。"
    )

    success = await send_dingtalk_message(title, content, db_session=db_session)
    return {
        "success": success,
        "message": "连接测试成功" if success else "连接测试失败，请检查 Webhook URL 和签名配置",
    }


# ---------------------------------------------------------------------------
# 辅助：获取数据库会话
# ---------------------------------------------------------------------------

async def _get_session():
    """获取独立的数据库会话（用于后台任务）"""
    from app.core.database import async_session
    return async_session()
