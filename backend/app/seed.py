"""初始化种子数据：默认管理员账号 + 系统配置 + 公开看板 token"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.security import get_password_hash, generate_public_token
from app.models.user import User
from app.models.system_config import SystemConfig


async def seed():
    async with async_session() as session:
        # Create default admin user if not exists
        result = await session.execute(select(User).where(User.username == "admin"))
        admin_user = result.scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                username="admin",
                real_name="系统管理员",
                email="admin@company.com",
                role="管理员",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
            )
            session.add(admin_user)
            await session.flush()
            await session.refresh(admin_user)
            print("✅ 默认管理员账号创建成功: admin / admin123")

        # Create zw user if not exists
        result = await session.execute(select(User).where(User.username == "zw"))
        zw_user = result.scalar_one_or_none()
        if not zw_user:
            zw_user = User(
                username="zw",
                real_name="政务",
                email="zw@company.com",
                role="责任支局长",
                hashed_password=get_password_hash("zw1234"),
                is_active=True,
            )
            session.add(zw_user)
            await session.flush()
            await session.refresh(zw_user)
            print("✅ zw账号创建成功: zw / zw1234")

        # Insert default configs if not exists
        defaults = [
            ("deepseek_api_key", "", "DeepSeek API密钥"),
            ("deepseek_api_url", "https://api.deepseek.com/chat/completions", "DeepSeek API地址"),
            ("deepseek_model", "deepseek-chat", "使用模型"),
            ("email_smtp_host", "smtp.exmail.qq.com", "SMTP服务器"),
            ("email_smtp_port", "465", "SMTP端口"),
            ("email_sender", "noreply@company.com", "发件人地址"),
            ("email_smtp_password", "", "SMTP密码"),
            ("weekly_remind_day", "1", "每周提醒日（1=周一）"),
            ("weekly_remind_time", "09:00", "每周提醒时间"),
            ("bid_approach_days", "7", "招标临近预警天数"),
            ("no_push_warn_days", "7", "未推进超期预警天数"),
            ("priority_auto_upgrade", "true", "是否允许AI自动提升优先级"),
            ("ai_analysis_trigger", "on_progress_update", "触发时机"),
            # 钉钉配置
            ("dingtalk_enabled", "true", "是否启用钉钉通知"),
            ("dingtalk_webhook_url", "", "钉钉机器人Webhook地址"),
            ("dingtalk_secret", "", "钉钉机器人签名密钥"),
            ("dingtalk_notify_types", '["progress_update","ai_alert","priority_change","bid_approach","no_push_warn","weekly_remind"]', "钉钉通知类型"),
        ]
        for key, value, desc in defaults:
            result = await session.execute(
                select(SystemConfig).where(SystemConfig.config_key == key)
            )
            if not result.scalar_one_or_none():
                session.add(SystemConfig(config_key=key, config_value=value, description=desc))

        # Generate public tokens for admin and zw (always regenerate to ensure freshness)
        admin_token = generate_public_token("admin", admin_user.id, admin_user.role, admin_user.real_name)
        result = await session.execute(
            select(SystemConfig).where(SystemConfig.config_key == "public_token_admin")
        )
        config = result.scalar_one_or_none()
        if config:
            config.config_value = admin_token
        else:
            session.add(SystemConfig(config_key="public_token_admin", config_value=admin_token, description="admin公开看板token"))

        if zw_user:
            zw_token = generate_public_token("zw", zw_user.id, zw_user.role, zw_user.real_name)
            result = await session.execute(
                select(SystemConfig).where(SystemConfig.config_key == "public_token_zw")
            )
            config = result.scalar_one_or_none()
            if config:
                config.config_value = zw_token
            else:
                session.add(SystemConfig(config_key="public_token_zw", config_value=zw_token, description="zw公开看板token"))

        await session.commit()
        print("✅ 系统配置初始化完成")
        print(f"✅ admin 公开看板 token 已生成")
        if zw_user:
            print(f"✅ zw 公开看板 token 已生成")


if __name__ == "__main__":
    asyncio.run(seed())
