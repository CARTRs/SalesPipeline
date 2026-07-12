"""
AI 分析 API — 对商机进度执行语义分析、风险评估、优先级建议
"""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.ai_analysis_result import AiAnalysisResult
from app.models.opportunity import Opportunity
from app.schemas.ai_analysis import (
    AiAnalysisListResponse,
    AiAnalysisRequest,
    AiAnalysisResponse,
    AiRiskAssessmentResponse,
    RiskSignal,
)
from app.services.ai_service import analyze_progress

router = APIRouter(prefix="/api/ai-analysis", tags=["AI 分析"])


@router.post("/{opportunity_id}", response_model=AiAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def trigger_ai_analysis(
    opportunity_id: int,
    data: AiAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """对指定商机的最新进度执行 AI 分析（风险/优先级/竞对/招标）"""
    # 验证商机存在
    opp_result = await db.execute(select(Opportunity).where(Opportunity.id == opportunity_id))
    opp = opp_result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在")

    result = await analyze_progress(
        opportunity_id=opportunity_id,
        analysis_type=data.analysis_type,
        progress_text=data.progress_text,
        db=db,
    )
    if result is None:
        raise HTTPException(status_code=500, detail="AI 分析失败，请检查 API 配置或稍后重试")

    # 重新从数据库加载完整的分析记录
    record_result = await db.execute(
        select(AiAnalysisResult).where(AiAnalysisResult.id == result["id"])
    )
    record = record_result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=500, detail="分析记录保存失败")

    return AiAnalysisResponse.model_validate(record)


@router.get("/{opportunity_id}/results", response_model=AiAnalysisListResponse)
async def list_analysis_results(
    opportunity_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    analysis_type: Optional[str] = Query(None, alias="analysis_type"),
    db: AsyncSession = Depends(get_db),
):
    """获取商机的 AI 分析历史记录"""
    # 验证商机存在
    opp_result = await db.execute(select(Opportunity).where(Opportunity.id == opportunity_id))
    if not opp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="商机不存在")

    # 查询条件
    filters = [AiAnalysisResult.opportunity_id == opportunity_id]
    if analysis_type:
        filters.append(AiAnalysisResult.analysis_type == analysis_type)

    count_query = select(func.count(AiAnalysisResult.id)).where(*filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = (
        select(AiAnalysisResult)
        .where(*filters)
        .order_by(AiAnalysisResult.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    records_result = await db.execute(query)
    records = records_result.scalars().all()

    return AiAnalysisListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[AiAnalysisResponse.model_validate(r) for r in records],
    )


@router.get("/{opportunity_id}/results/{analysis_id}", response_model=AiAnalysisResponse)
async def get_analysis_result(
    opportunity_id: int,
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取单条 AI 分析详情"""
    result = await db.execute(
        select(AiAnalysisResult).where(
            AiAnalysisResult.id == analysis_id,
            AiAnalysisResult.opportunity_id == opportunity_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="分析记录不存在")

    return AiAnalysisResponse.model_validate(record)


@router.post("/{opportunity_id}/risk-assessment", response_model=AiRiskAssessmentResponse)
async def risk_assessment(
    opportunity_id: int,
    data: AiAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    快速风险评估 — 分析并直接更新商机的风险等级/摘要/建议。
    等价于 analysis_type=progress 的快捷入口，返回结构化评估结果。
    """
    # 验证商机存在
    opp_result = await db.execute(
        select(Opportunity)
        .options(selectinload(Opportunity.ai_analysis_results))
        .where(Opportunity.id == opportunity_id)
    )
    opp = opp_result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在")

    result = await analyze_progress(
        opportunity_id=opportunity_id,
        analysis_type="progress",
        progress_text=data.progress_text,
        db=db,
    )
    if result is None:
        raise HTTPException(status_code=500, detail="AI 分析失败，请检查 API 配置或稍后重试")

    # 构建返回
    risk_signals = [
        RiskSignal(
            type=s.get("type", "其他"),
            description=s.get("description", ""),
            severity=s.get("severity", "medium"),
        )
        for s in (result.get("risk_signals") or [])
    ]

    confidence = (
        Decimal(str(result["confidence_score"]))
        if result.get("confidence_score") is not None
        else None
    )

    return AiRiskAssessmentResponse(
        opportunity_id=opportunity_id,
        ai_risk_level=result.get("risk_level"),
        ai_analysis_summary=result.get("summary"),
        next_action_required=result.get("next_action"),
        competitor_detected=result.get("competitor_detected", False),
        risk_signals=risk_signals,
        priority_suggestion=result.get("priority_suggestion"),
        confidence_score=confidence,
    )
