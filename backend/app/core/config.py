from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "商机智能跟踪与预警系统"
    APP_PORT: int = 8000
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://sjxt:sjxt@localhost:5432/opportunity_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "change-me-to-a-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # AI API（兼容 OpenAI 格式，支持旧名 DEEPSEEK_*）
    AI_API_KEY: Optional[str] = Field(None, validation_alias="DEEPSEEK_API_KEY")
    AI_API_URL: str = Field("https://api.deepseek.com/chat/completions", validation_alias="DEEPSEEK_API_URL")
    AI_MODEL: str = Field("deepseek-chat", validation_alias="DEEPSEEK_MODEL")

    # Email (SMTP)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 465
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    EMAIL_SENDER: Optional[str] = None

    # System config defaults
    WEEKLY_REMIND_DAY: int = 1
    WEEKLY_REMIND_TIME: str = "09:00"
    BID_APPROACH_DAYS: int = 7
    NO_PUSH_WARN_DAYS: int = 7
    PRIORITY_AUTO_UPGRADE: bool = True
    AI_ANALYSIS_TRIGGER: str = "on_progress_update"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
    }


settings = Settings()
