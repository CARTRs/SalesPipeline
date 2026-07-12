"""初始化种子数据：默认管理员账号 + 系统配置"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.security import get_password_hash
from app.models.user import User
from app.models.system_config import SystemConfig


async def seed():
    async with async_session() as session:
        # Create default admin user if not exists
        result = await session.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            admin = User(
                username="admin",
                real_name="系统管理员",
                email="admin@company.com",
                role="管理员",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
            )
            session.add(admin)
            print("✅ 默认管理员账号创建成功: admin / admin123")

        # Insert default configs if not exists
        defaults = [
            ("deepseek_api_key", "", "DeepSeek API密钥"),
            ("deepseek_api_url", "https://api.deepseek.com/chat/completions", "DeepSeek API地址"),
            ("deepseek_model", "deepseek-chat", "使用模型"),
            ("email_smtp_host", "smtp.exmail.qq.com", "SMTP服务器"),
            ("email_smtp_port", "465", "SMTP端口"),
            ("email_sender", "noreply@company.com", "发件人地址"),
            ("weekly_remind_day", "1", "每周提醒日（1=周一）"),
            ("weekly_remind_time", "09:00", "每周提醒时间"),
            ("bid_approach_days", "7", "招标临近预警天数"),
            ("no_push_warn_days", "7", "未推进超期预警天数"),
            ("priority_auto_upgrade", "true", "是否允许AI自动提升优先级"),
            ("ai_analysis_trigger", "on_progress_update", "触发时机"),
        ]
        for key, value, desc in defaults:
            result = await session.execute(
                select(SystemConfig).where(SystemConfig.config_key == key)
            )
            if not result.scalar_one_or_none():
                session.add(SystemConfig(config_key=key, config_value=value, description=desc))

        await session.commit()
        print("✅ 系统配置初始化完成")


if __name__ == "__main__":
    asyncio.run(seed())
