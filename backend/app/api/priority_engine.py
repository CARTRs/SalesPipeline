"""
优先级引擎 API 路由

提供商机优先级评估、手动调整、变更历史查询及分布统计等接口。
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.priority_engine import (
    BatchEvaluateRequest,
    BatchEvaluateResponse,
    ManualPriorityAdjustRequest,
    ManualPriorityAdjustResponse,
    PriorityChangeLogListResponse,
    PriorityChangeLogResponse,
    PriorityDistributionResponse,
    PriorityDistributionItem,
    PriorityEvaluateRequest,
    PriorityEvaluateResponse,
)
from app.services.priority_engine import (
    batch_evaluate,
    evaluate_opportunity,
    get_priority_change_logs,
    get_priority_distribution,
    manual_adjust_priority,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/priority", tags=["优先级引擎"])


@router.post("/evaluate/{opportunity_id}", response_model=PriorityEvaluateResponse)
async def evaluate_single(
    opportunity_id: int,
    dry_run: bool = Query(True, description="为 true 时不写入数据库，仅返回评估结果"),
    db: AsyncSession = Depends(get_db),
):
    """评估单个商机的优先级"""
    try:
        result = await evaluate_opportunity(
            opportunity_id=opportunity_id,
            db=db,
            changed_by="AI_SYSTEM",
            dry_run=dry_run,
        )
        return PriorityEvaluateResponse(
            opportunity_id=result["opportunity_id"],
            opportunity_name=result["opportunity_name"],
            current_priority=result["current_priority"],
            suggested_priority=result["suggested_priority"],
            priority_changed=result["priority_changed"],
            score_breakdown=result["score_breakdown"],
            reason=result["reason"],
            evaluated_at=result["evaluated_at"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("评估商机优先级失败")
        raise HTTPException(status_code=500, detail=f"评估失败: {str(e)}")


@router.post("/batch-evaluate", response_model=BatchEvaluateResponse)
async def evaluate_batch(
    request: BatchEvaluateRequest,
    db: AsyncSession = Depends(get_db),
):
    """批量评估商机优先级"""
    try:
        result = await batch_evaluate(
            db=db,
            opportunity_ids=request.opportunity_ids,
            filter_no_push_days_gt=request.filter_no_push_days_gt,
            filter_priority_levels=request.filter_priority_levels,
            dry_run=request.dry_run,
            changed_by="AI_SYSTEM",
        )
        return BatchEvaluateResponse(
            total_evaluated=result["total_evaluated"],
            priority_changed=result["priority_changed"],
            errors=result["errors"],
            results=[
                PriorityEvaluateResponse(
                    opportunity_id=r["opportunity_id"],
                    opportunity_name=r["opportunity_name"],
                    current_priority=r["current_priority"],
                    suggested_priority=r["suggested_priority"],
                    priority_changed=r["priority_changed"],
                    priority_score=r["priority_score"],
                    score_breakdown=r["score_breakdown"],
                    reason=r["reason"],
                    evaluated_at=r["evaluated_at"],
                )
                for r in result["results"]
            ],
        )
    except Exception as e:
        logger.exception("批量评估商机优先级失败")
        raise HTTPException(status_code=500, detail=f"批量评估失败: {str(e)}")


@router.put("/manual-adjust/{opportunity_id}", response_model=ManualPriorityAdjustResponse)
async def adjust_priority(
    opportunity_id: int,
    request: ManualPriorityAdjustRequest,
    db: AsyncSession = Depends(get_db),
):
    """手动调整商机优先级"""
    if opportunity_id != request.opportunity_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="路径参数 opportunity_id 与请求体不一致",
        )
    try:
        result = await manual_adjust_priority(
            opportunity_id=opportunity_id,
            new_priority=request.new_priority,
            reason=request.reason,
            db=db,
            changed_by="USER_MANUAL",
        )
        return ManualPriorityAdjustResponse(
            opportunity_id=result["opportunity_id"],
            opportunity_name=result["opportunity_name"],
            old_priority=result["old_priority"],
            new_priority=result["new_priority"],
            reason=result["reason"],
            changed_by=result["changed_by"],
            changed_at=result["changed_at"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("手动调整优先级失败")
        raise HTTPException(status_code=500, detail=f"调整失败: {str(e)}")


@router.get("/history/{opportunity_id}", response_model=PriorityChangeLogListResponse)
async def list_change_logs(
    opportunity_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取指定商机的优先级变更历史"""
    try:
        result = await get_priority_change_logs(
            opportunity_id=opportunity_id,
            db=db,
            page=page,
            page_size=page_size,
        )
        return PriorityChangeLogListResponse(
            total=result["total"],
            items=[PriorityChangeLogResponse(**item) for item in result["items"]],
        )
    except Exception as e:
        logger.exception("查询优先级变更历史失败")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/distribution", response_model=PriorityDistributionResponse)
async def priority_distribution(db: AsyncSession = Depends(get_db)):
    """获取商机优先级分布统计"""
    try:
        result = await get_priority_distribution(db)
        return PriorityDistributionResponse(
            distribution=[
                PriorityDistributionItem(**item) for item in result["distribution"]
            ],
            total_opportunities=result["total_opportunities"],
            total_amount=result["total_amount"],
        )
    except Exception as e:
        logger.exception("查询优先级分布失败")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
