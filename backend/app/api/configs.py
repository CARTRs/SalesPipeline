from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.system_config import SystemConfig


class ConfigItem(BaseModel):
    config_key: str
    config_value: Optional[str] = None
    description: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    configs: list[ConfigItem]


router = APIRouter(prefix="/api/configs", tags=["系统配置"])


@router.get("")
async def get_configs(db: AsyncSession = Depends(get_db)):
    """获取所有系统配置"""
    result = await db.execute(select(SystemConfig))
    items = result.scalars().all()
    return {item.config_key: item.config_value for item in items}


@router.put("")
async def update_configs(data: ConfigUpdateRequest, db: AsyncSession = Depends(get_db)):
    """批量更新系统配置"""
    updated = []
    for item in data.configs:
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.config_key == item.config_key)
        )
        config = result.scalar_one_or_none()
        if config:
            config.config_value = item.config_value
        else:
            config = SystemConfig(
                config_key=item.config_key,
                config_value=item.config_value,
                description=item.description or "",
            )
            db.add(config)
        updated.append(item.config_key)

    await db.flush()
    return {"message": f"已更新 {len(updated)} 项配置", "updated": updated}


class EmailTemplatesResponse(BaseModel):
    templates: dict


@router.get("/email-templates")
async def get_email_templates(db: AsyncSession = Depends(get_db)):
    """获取邮件模板（DB 覆盖默认值）"""
    from app.services.email_service import load_email_templates

    templates = await load_email_templates(db)
    return {"templates": templates}


@router.put("/email-templates")
async def update_email_templates(
    data: EmailTemplatesResponse, db: AsyncSession = Depends(get_db)
):
    """保存邮件模板到数据库"""
    from app.services.email_service import save_email_templates_to_db

    await save_email_templates_to_db(db, data.templates)
    return {"message": "邮件模板已更新"}


@router.get("/email-template-blueprints")
async def get_email_template_blueprints():
    """获取邮件模板字段蓝图（供前端表单渲染使用）"""
    from app.services.email_service import TEMPLATE_BLUEPRINTS

    return {"blueprints": TEMPLATE_BLUEPRINTS}


@router.post("/dingtalk/test")
async def test_dingtalk(db: AsyncSession = Depends(get_db)):
    """测试钉钉机器人连接"""
    from app.services.dingtalk_service import test_dingtalk_connection

    result = await test_dingtalk_connection(db)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return {"message": result["message"]}
