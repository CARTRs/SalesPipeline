"""
调度中心服务 — 基于 APScheduler 的定时任务管理
提供定时任务注册、触发、状态查询，以及各业务任务实现
"""
import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import async_session
from app.models.opportunity import Opportunity
from app.models.priority_change_log import PriorityChangeLog
from app.models.email_log import EmailLog
from app.models.user import User

logger = logging.getLogger(__name__)


class SchedulerService:
    """定时任务调度服务 — 管理 APScheduler 生命周期与业务任务"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._task_registry: dict[str, dict] = {}

    # ────────────────────── 生命周期 ──────────────────────

    async def start(self):
        """启动调度器并注册所有内置定时任务"""
        if self.scheduler.running:
            logger.warning("调度器已在运行中，跳过 start()")
            return

        self._register_jobs()
        self.scheduler.start()
        logger.info("调度器已启动")

    async def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("调度器已停止")

    # ────────────────────── 任务注册 ──────────────────────

    def _register_jobs(self):
        """向调度器注册所有内置定时任务"""

        # 0. 未推进天数自动递增 — 每天 01:00（在优先级升级之前）
        self._add_job(
            "daily_no_push_increment",
            self.daily_no_push_increment_task,
            CronTrigger(hour=1, minute=0),
            "未关闭商机未推进天数 +1",
        )

        # 1. 每周待更新提醒 — 配置的周几与时间
        weekday = settings.WEEKLY_REMIND_DAY  # 0=Monday .. 6=Sunday
        hour, minute = self._parse_time_setting(settings.WEEKLY_REMIND_TIME, 9, 0)
        self._add_job(
            "weekly_remind",
            self.weekly_remind_task,
            CronTrigger(day_of_week=weekday, hour=hour, minute=minute),
            "每周待更新商机提醒邮件",
        )

        # 2. 招标临近检查 — 每天 08:00
        self._add_job(
            "bid_approach_check",
            self.bid_approach_check_task,
            CronTrigger(hour=8, minute=0),
            "招标临近提醒检查",
        )

        # 3. 超期未推进预警 — 每天 09:00
        self._add_job(
            "no_push_warn",
            self.no_push_warn_task,
            CronTrigger(hour=9, minute=0),
            "超期未推进预警检查",
        )

        # 4. 优先级自动升级 — 每天 02:00（仅在配置开启时注册）
        if settings.PRIORITY_AUTO_UPGRADE:
            self._add_job(
                "auto_priority_upgrade",
                self.auto_priority_upgrade_task,
                CronTrigger(hour=2, minute=0),
                "商机优先级自动升级（按未推进时长）",
            )

        # 5. 过期记录清理 — 每周日 03:00
        self._add_job(
            "cleanup_expired",
            self.cleanup_expired_task,
            CronTrigger(day_of_week=6, hour=3, minute=0),
            "清理 30 天前的已发送/失败邮件日志",
        )

    def _add_job(self, task_id: str, func: Any, trigger: Any, description: str = ""):
        """向调度器注册一个任务并记入注册表"""
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=task_id,
            name=task_id,
            replace_existing=True,
        )
        self._task_registry[task_id] = {
            "id": task_id,
            "description": description,
            "trigger": str(trigger),
            "next_run_time": None,
        }
        logger.info("定时任务已注册: %s — %s", task_id, description)

    @staticmethod
    def _parse_time_setting(raw: str, default_hour: int, default_minute: int) -> tuple[int, int]:
        """解析配置中的时间字符串（HH:MM），失败时返回默认值"""
        try:
            parts = raw.strip().split(":")
            return int(parts[0]), int(parts[1])
        except (ValueError, IndexError, AttributeError):
            return default_hour, default_minute

    # ────────────────────── 业务任务实现 ──────────────────────

    async def daily_no_push_increment_task(self) -> dict:
        """每天凌晨对未关闭商机 no_push_days += 1"""
        logger.info("[定时任务] daily_no_push_increment — 开始执行")
        async with async_session() as db:
            try:
                rows = await db.execute(
                    select(Opportunity).where(Opportunity.close_flag == 0)
                )
                count = 0
                for opp in rows.scalars().all():
                    opp.no_push_days = (opp.no_push_days or 0) + 1
                    count += 1
                if count:
                    await db.flush()
                logger.info("未推进天数已递增: %d 个商机", count)
                return {
                    "task": "daily_no_push_increment",
                    "count": count,
                    "detail": f"已为 {count} 个未关闭商机增加未推进天数",
                }
            except Exception as e:
                logger.exception("daily_no_push_increment 执行失败")
                return {"task": "daily_no_push_increment", "error": str(e)}

    async def weekly_remind_task(self) -> dict:
        """每周待更新商机提醒：
        筛选未推进天数 >= 阈值的活跃商机，按责任支局长汇总，发送提醒邮件
        """
        logger.info("[定时任务] weekly_remind — 开始执行")
        threshold = settings.NO_PUSH_WARN_DAYS or 7

        async with async_session() as db:
            try:
                rows = await db.execute(
                    select(Opportunity)
                    .options(
                        selectinload(Opportunity.account_manager),
                        selectinload(Opportunity.branch_director),
                    )
                    .where(
                        Opportunity.close_flag == 0,
                        Opportunity.no_push_days >= threshold,
                    )
                    .order_by(Opportunity.no_push_days.desc())
                )
                opportunities = rows.scalars().all()
                logger.info("待提醒商机数: %d (阈值=%d天)", len(opportunities), threshold)

                if not opportunities:
                    return {"task": "weekly_remind", "count": 0, "detail": "无待提醒商机"}

                # 按责任支局长分组
                director_map: dict[int, dict[str, Any]] = {}
                for opp in opportunities:
                    uid = opp.branch_director_id
                    if uid is None:
                        continue
                    if uid not in director_map:
                        director_map[uid] = {"user": opp.branch_director, "opportunities": []}
                    director_map[uid]["opportunities"].append(opp)

                from app.services.email_service import send_email, render_template

                sent_count = 0
                today_str = date.today().isoformat()
                for uid, info in director_map.items():
                    user: Optional[User] = info["user"]
                    if not user or not user.email:
                        continue
                    opp_list = [
                        {
                            "name": opp.opportunity_name,
                            "customer": opp.customer_name,
                            "no_push_days": opp.no_push_days or 0,
                        }
                        for opp in info["opportunities"]
                    ]
                    subject, body = render_template(
                        "weekly_remind",
                        date=today_str,
                        real_name=user.real_name,
                        opportunities=opp_list,
                        system_link="",
                    )
                    if await send_email(user.email, subject, body, db):
                        sent_count += 1

                logger.info("周提醒邮件已发送: %d 人", sent_count)
                return {
                    "task": "weekly_remind",
                    "count": sent_count,
                    "detail": f"发现 {len(opportunities)} 个待提醒商机，已向 {sent_count} 人发送邮件",
                }
            except Exception as e:
                logger.exception("weekly_remind 执行失败")
                return {"task": "weekly_remind", "error": str(e)}

    async def bid_approach_check_task(self) -> dict:
        """招标临近检查：
        筛选预计签约日期在 (今天, 今天+配置天数] 范围内的商机，通知相关人员
        """
        logger.info("[定时任务] bid_approach_check — 开始执行")
        approach_days = settings.BID_APPROACH_DAYS or 7
        today = date.today()
        target = today + timedelta(days=approach_days)

        async with async_session() as db:
            try:
                rows = await db.execute(
                    select(Opportunity)
                    .options(
                        selectinload(Opportunity.account_manager),
                        selectinload(Opportunity.branch_director),
                    )
                    .where(
                        Opportunity.close_flag == 0,
                        Opportunity.is_bid_required == True,
                        Opportunity.estimated_sign_date.isnot(None),
                        Opportunity.estimated_sign_date <= target,
                        Opportunity.estimated_sign_date >= today,
                    )
                )
                opportunities = rows.scalars().all()
                logger.info("招标临近商机数: %d", len(opportunities))

                if not opportunities:
                    return {"task": "bid_approach_check", "count": 0, "detail": "无临近招标商机"}

                from app.services.email_service import send_email, render_template

                sent_count = 0
                for opp in opportunities:
                    recipients = []
                    if opp.account_manager and opp.account_manager.email:
                        recipients.append(opp.account_manager)
                    if opp.branch_director and opp.branch_director.email:
                        recipients.append(opp.branch_director)

                    remaining_days = (opp.estimated_sign_date - today).days
                    for user in recipients:
                        subject, body = render_template(
                            "bid_approach",
                            opportunity_name=opp.opportunity_name,
                            days=remaining_days,
                            estimated_sign_date=opp.estimated_sign_date.isoformat(),
                            system_link="",
                        )
                        if await send_email(user.email, subject, body, db):
                            sent_count += 1

                return {
                    "task": "bid_approach_check",
                    "count": sent_count,
                    "detail": f"发现 {len(opportunities)} 个招标临近商机，已发送 {sent_count} 封邮件",
                }
            except Exception as e:
                logger.exception("bid_approach_check 执行失败")
                return {"task": "bid_approach_check", "error": str(e)}

    async def no_push_warn_task(self) -> dict:
        """超期未推进预警：
        对未推进天数 >= 阈值 且 尚未标记预警的活跃商机发送预警邮件，并标记 no_push_flag=1
        """
        logger.info("[定时任务] no_push_warn — 开始执行")
        threshold = settings.NO_PUSH_WARN_DAYS or 7

        async with async_session() as db:
            try:
                rows = await db.execute(
                    select(Opportunity)
                    .options(
                        selectinload(Opportunity.account_manager),
                        selectinload(Opportunity.branch_director),
                    )
                    .where(
                        Opportunity.close_flag == 0,
                        Opportunity.no_push_days >= threshold,
                        Opportunity.no_push_flag == 0,
                    )
                )
                opportunities = rows.scalars().all()
                logger.info("新超期未推进商机数: %d", len(opportunities))

                if not opportunities:
                    return {"task": "no_push_warn", "count": 0, "detail": "无新的超期未推进商机"}

                from app.services.email_service import send_email, render_template

                sent_count = 0
                for opp in opportunities:
                    recipients = []
                    if opp.account_manager and opp.account_manager.email:
                        recipients.append(opp.account_manager)
                    if opp.branch_director and opp.branch_director.email:
                        recipients.append(opp.branch_director)

                    for user in recipients:
                        subject, body = render_template(
                            "no_push_warn",
                            opportunity_name=opp.opportunity_name,
                            customer_name=opp.customer_name,
                            days=opp.no_push_days or 0,
                            system_link="",
                        )
                        if await send_email(user.email, subject, body, db):
                            sent_count += 1

                    # 标记已预警，避免重复发送
                    opp.no_push_flag = 1

                await db.flush()
                logger.info("未推进预警已发送: %d 封邮件", sent_count)
                return {
                    "task": "no_push_warn",
                    "count": sent_count,
                    "detail": f"发现 {len(opportunities)} 个超期商机，已发送 {sent_count} 封预警邮件",
                }
            except Exception as e:
                logger.exception("no_push_warn 执行失败")
                return {"task": "no_push_warn", "error": str(e)}

    @staticmethod
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

            _PRIORITY_NAMES = {1: "紧急", 2: "高", 3: "中", 4: "低"}
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

    async def auto_priority_upgrade_task(self) -> dict:
        """优先级自动升级：
        根据未推进时长自动提升优先级（数字越小优先级越高）
          - 未推进 >= 30 天 → 优先级 1（紧急）
          - 未推进 >= 14 天 → 优先级 2（高）
        同时记录 PriorityChangeLog 并发送通知邮件
        """
        logger.info("[定时任务] auto_priority_upgrade — 开始执行")

        # (最小未推进天数, 目标优先级)
        rules = [
            (30, 1),
            (14, 2),
        ]

        async with async_session() as db:
            try:
                total = 0
                for min_days, target_priority in rules:
                    rows = await db.execute(
                        select(Opportunity)
                        .options(
                            selectinload(Opportunity.account_manager),
                            selectinload(Opportunity.branch_director),
                        )
                        .where(
                            Opportunity.close_flag == 0,
                            Opportunity.no_push_days >= min_days,
                            Opportunity.priority_level > target_priority,
                        )
                    )
                    for opp in rows.scalars().all():
                        old = opp.priority_level
                        opp.priority_level = target_priority
                        db.add(
                            PriorityChangeLog(
                                opportunity_id=opp.id,
                                old_priority=old,
                                new_priority=target_priority,
                                change_reason=f"未推进 ≥ {min_days} 天自动升级",
                                changed_by="AI_SYSTEM",
                            )
                        )
                        total += 1

                        # 发送优先级变更通知邮件
                        await self._send_priority_change_email(
                            opp, old, target_priority,
                            f"未推进 ≥ {min_days} 天自动升级", db,
                        )

                if total:
                    await db.flush()

                logger.info("优先级自动升级完成: %d 个商机", total)
                return {
                    "task": "auto_priority_upgrade",
                    "count": total,
                    "detail": f"已升级 {total} 个商机的优先级",
                }
            except Exception as e:
                logger.exception("auto_priority_upgrade 执行失败")
                return {"task": "auto_priority_upgrade", "error": str(e)}

    async def cleanup_expired_task(self) -> dict:
        """清理过期记录：删除 30 天前的已发送/失败邮件日志"""
        logger.info("[定时任务] cleanup_expired — 开始执行")
        cutoff = datetime.utcnow() - timedelta(days=30)

        async with async_session() as db:
            try:
                # 先计数
                count_row = await db.execute(
                    select(func.count(EmailLog.id)).where(
                        EmailLog.created_at < cutoff,
                        EmailLog.status.in_(["sent", "failed"]),
                    )
                )
                count = count_row.scalar() or 0

                if count:
                    stmt = sa_delete(EmailLog).where(
                        EmailLog.created_at < cutoff,
                        EmailLog.status.in_(["sent", "failed"]),
                    )
                    await db.execute(stmt)
                    await db.flush()

                logger.info("过期记录清理完成: 删除 %d 条", count)
                return {
                    "task": "cleanup_expired",
                    "count": count,
                    "detail": f"已清理 {count} 条过期日志",
                }
            except Exception as e:
                logger.exception("cleanup_expired 执行失败")
                return {"task": "cleanup_expired", "error": str(e)}

    # ────────────────────── 手动触发 ──────────────────────

    async def trigger_task(self, task_id: str) -> dict:
        """手动触发指定任务并返回执行结果"""
        if task_id not in self._task_registry:
            return {"error": f"任务不存在: {task_id}"}

        logger.info("手动触发任务: %s", task_id)
        task_map = {
            "daily_no_push_increment": self.daily_no_push_increment_task,
            "weekly_remind": self.weekly_remind_task,
            "bid_approach_check": self.bid_approach_check_task,
            "no_push_warn": self.no_push_warn_task,
            "auto_priority_upgrade": self.auto_priority_upgrade_task,
            "cleanup_expired": self.cleanup_expired_task,
        }
        task_fn = task_map.get(task_id)
        if task_fn is None:
            return {"error": f"未实现任务处理函数: {task_id}"}
        return await task_fn()

    # ────────────────────── 状态查询 ──────────────────────

    def get_scheduler_info(self) -> dict:
        """获取调度器当前状态及任务列表"""
        if not self.scheduler.running:
            return {"status": "stopped", "tasks": []}

        jobs = self.scheduler.get_jobs()
        tasks = []
        for job in jobs:
            info = self._task_registry.get(job.id, {})
            tasks.append({
                "id": job.id,
                "description": info.get("description", ""),
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            })

        return {"status": "running", "tasks": tasks}

    def get_task_registry(self) -> list[dict]:
        """获取所有已注册任务的元信息"""
        return list(self._task_registry.values())


# 全局单例
scheduler_service = SchedulerService()
