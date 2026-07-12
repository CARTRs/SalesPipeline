from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class RiskSignal(BaseModel):
    """单个风险信号"""
    type: str
    description: str
    severity: str = "medium"


class AiAnalysisRequest(BaseModel):
    """触发 AI 分析的请求"""
    analysis_type: str = "progress"  # risk / priority / competitor / bid / progress
    progress_text: str
    force_refresh: bool = False


class AiAnalysisResponse(BaseModel):
    """AI 分析记录响应"""
    id: int
    opportunity_id: int
    analysis_type: str
    raw_progress_text: Optional[str] = None
    ai_model: Optional[str] = None
    risk_signals: Optional[list] = None
    priority_suggestion: Optional[int] = None
    suggested_actions: Optional[list] = None
    full_response: Optional[str] = None
    confidence_score: Optional[Decimal] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AiAnalysisListResponse(BaseModel):
    """AI 分析记录列表响应"""
    total: int
    page: int
    page_size: int
    items: list[AiAnalysisResponse]


class AiRiskAssessmentResponse(BaseModel):
    """风险评估结果（直接更新商机后的返回）"""
    opportunity_id: int
    ai_risk_level: Optional[str] = None
    ai_analysis_summary: Optional[str] = None
    next_action_required: Optional[str] = None
    competitor_detected: bool = False
    bid_date_approaching: bool = False
    risk_signals: list[RiskSignal] = []
    priority_suggestion: Optional[int] = None
    confidence_score: Optional[Decimal] = None
