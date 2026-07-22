"""
AI 引擎 — API 路由：商机分析、文本分析、分析历史
"""
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.models.opportunity import Opportunity
from app.schemas.ai import (
    AiAnalysisHistoryResponse,
    AiAnalysisRequest,
    AiAnalysisResponse,
    AiOpportunityAnalysisResult,
    BatchAiAnalysisRequest,
)
from app.services.ai_engine import (
    analyze_progress_text,
    analyze_opportunity_full,
    get_analysis_history,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI 引擎"])


# ---------------------------------------------------------------------------
# 批量分析任务状态追踪 — 使用 Redis 跨 worker 共享
# ---------------------------------------------------------------------------
def _get_redis():
    """获取 Redis 连接（同步，用于简单 KV 操作）。"""
    import redis
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _set_task(task_id: str, data: dict):
    r = _get_redis()
    r.set(f"ai_task:{task_id}", json.dumps(data, ensure_ascii=False), ex=3600)


def _get_task(task_id: str) -> dict | None:
    r = _get_redis()
    raw = r.get(f"ai_task:{task_id}")
    return json.loads(raw) if raw else None


async def _run_analyze_all_background(task_id: str, opportunity_ids: list[int]):
    """后台执行全量 AI 分析，逐个分析并更新进度。"""
    from app.core.database import async_session

    results = []
    errors = []
    async with async_session() as db:
        for idx, opp_id in enumerate(opportunity_ids):
            try:
                r = await analyze_opportunity_full(opp_id, db)
                results.append({"opportunity_id": opp_id, "success": True, "data": r})
            except Exception as e:
                logger.exception("AI 全量分析商机 %s 失败", opp_id)
                errors.append({"opportunity_id": opp_id, "error": str(e)})

            # 更新 Redis 进度
            _set_task(task_id, {
                "status": "running",
                "total": len(opportunity_ids),
                "analyzed": len(results),
                "failed": len(errors),
                "current_index": idx + 1,
            })

        await db.commit()

    _set_task(task_id, {
        "status": "completed",
        "total": len(opportunity_ids),
        "analyzed": len(results),
        "failed": len(errors),
        "current_index": len(opportunity_ids),
        "results": results,
        "errors": errors,
    })


@router.post("/analyze", response_model=dict)
async def analyze_opportunity(
    opportunity_id: int = Query(..., description="商机 ID"),
    db: AsyncSession = Depends(get_db),
):
    """对指定商机进行全面 AI 分析（聚合所有进度记录）。"""
    try:
        result = await analyze_opportunity_full(opportunity_id, db)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 分析失败: {str(e)}")


@router.post("/analyze-text", response_model=dict)
async def analyze_text(
    request: AiAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """分析单条进度文本并返回 AI 解析结果。"""
    try:
        result = await analyze_progress_text(
            opportunity_id=request.opportunity_id,
            progress_text=request.progress_text,
            db=db,
        )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文本分析失败: {str(e)}")


@router.post("/analyze-batch", response_model=dict)
async def analyze_batch(
    request: BatchAiAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """批量分析多个商机。"""
    results = []
    errors = []

    for opp_id in request.opportunity_ids:
        try:
            result = await analyze_opportunity_full(opp_id, db)
            results.append({"opportunity_id": opp_id, "success": True, "data": result})
        except ValueError as e:
            errors.append({"opportunity_id": opp_id, "error": str(e)})
        except Exception as e:
            errors.append({"opportunity_id": opp_id, "error": str(e)})

    return {
        "success": len(errors) == 0,
        "total": len(request.opportunity_ids),
        "analyzed": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }


@router.post("/analyze-all", response_model=dict)
async def analyze_all(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """对所有活跃商机启动后台 AI 全量分析（立即返回 task_id，前端轮询进度）。"""
    result = await db.execute(
        select(Opportunity.id).where(
            (Opportunity.close_flag == 0) | (Opportunity.close_flag.is_(None))
        )
    )
    all_ids = [row[0] for row in result.all()]

    if not all_ids:
        return {"success": True, "total": 0, "analyzed": 0, "failed": 0, "results": [], "errors": [], "task_id": None}

    task_id = str(uuid.uuid4())[:8]
    _set_task(task_id, {
        "status": "running",
        "total": len(all_ids),
        "analyzed": 0,
        "failed": 0,
        "current_index": 0,
        "results": [],
        "errors": [],
    })

    background_tasks.add_task(_run_analyze_all_background, task_id, all_ids)

    return {
        "success": True,
        "task_id": task_id,
        "total": len(all_ids),
        "message": f"已启动后台分析，共 {len(all_ids)} 条商机",
    }


@router.get("/analyze-all/{task_id}", response_model=dict)
async def get_analyze_all_status(task_id: str):
    """查询后台批量分析任务的进度（通过 Redis 跨 worker 共享状态）。"""
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return {
        "task_id": task_id,
        "status": task["status"],
        "total": task["total"],
        "analyzed": task["analyzed"],
        "failed": task["failed"],
        "current_index": task["current_index"],
        "is_completed": task["status"] == "completed",
        "results": task.get("results", []) if task["status"] == "completed" else [],
        "errors": task.get("errors", []) if task["status"] == "completed" else [],
    }


@router.get("/history/{opportunity_id}", response_model=AiAnalysisHistoryResponse)
async def analysis_history(
    opportunity_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取指定商机的 AI 分析历史记录。"""
    items, total = await get_analysis_history(
        opportunity_id=opportunity_id,
        page=page,
        page_size=page_size,
        db=db,
    )
    return AiAnalysisHistoryResponse(
        total=total,
        items=[AiAnalysisResponse.model_validate(item) for item in items],
    )


@router.get("/result/{opportunity_id}", response_model=AiOpportunityAnalysisResult)
async def get_latest_analysis_result(
    opportunity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取指定商机的最新 AI 分析结果（从 Opportunity 表字段读取）。"""
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在")

    return AiOpportunityAnalysisResult(
        opportunity_id=opp.id,
        opportunity_name=opp.opportunity_name,
        customer_name=opp.customer_name,
        ai_risk_level=opp.ai_risk_level,
        ai_analysis_summary=opp.ai_analysis_summary,
        next_action_required=opp.next_action_required,
        competitor_detected=opp.competitor_detected or False,
        bid_date_approaching=opp.bid_date_approaching or False,
        priority_suggestion=opp.priority_level,
        last_analysis_at=opp.last_ai_analysis_at,
    )
