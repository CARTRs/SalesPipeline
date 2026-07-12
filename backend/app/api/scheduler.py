"""
调度管理 API — 查看调度器状态、手动触发定时任务
"""
import logging

from fastapi import APIRouter, HTTPException

from app.services.scheduler_service import scheduler_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scheduler", tags=["调度管理"])


@router.get("/status")
async def get_scheduler_status():
    """获取调度器运行状态及所有定时任务的下次执行时间"""
    return scheduler_service.get_scheduler_info()


@router.get("/tasks")
async def list_scheduler_tasks():
    """获取所有已注册定时任务的元信息"""
    return {
        "status": "running" if scheduler_service.scheduler.running else "stopped",
        "tasks": scheduler_service.get_task_registry(),
    }


@router.post("/trigger/{task_id}")
async def trigger_scheduler_task(task_id: str):
    """手动触发指定定时任务立即执行"""
    result = await scheduler_service.trigger_task(task_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
