"""
AI 引擎服务 — Pydantic 请求/响应模型
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class AiAnalysisRequest(BaseModel):
    """单条进度文本分析请求"""
    opportunity_id: int
    progress_text: str


class AiAnalysisResponse(BaseModel):
    """AI 分析结果响应"""
    id: int
    opportunity_id: int
    analysis_type: str
    raw_progress_text: Optional[str] = None
    ai_model: Optional[str] = None
    risk_signals: Optional[list[dict]] = None
    priority_suggestion: Optional[int] = None
    suggested_actions: Optional[list[str]] = None
    full_response: Optional[str] = None
    confidence_score: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AiAnalysisHistoryResponse(BaseModel):
    """分析历史列表"""
    total: int
    items: list[AiAnalysisResponse]


class AiOpportunityAnalysisResult(BaseModel):
    """面向商机的完整分析结果（含商机摘要字段）"""
    opportunity_id: int
    opportunity_name: str
    customer_name: str
    ai_risk_level: Optional[str] = None
    ai_analysis_summary: Optional[str] = None
    next_action_required: Optional[str] = None
    competitor_detected: bool = False
    bid_date_approaching: bool = False
    is_bid_required: bool = False
    priority_suggestion: Optional[int] = None
    risk_signals: Optional[list[dict]] = None
    suggested_actions: Optional[list[str]] = None
    confidence_score: Optional[float] = None
    last_analysis_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BatchAiAnalysisRequest(BaseModel):
    """批量分析请求"""
    opportunity_ids: list[int]


class AiAnalysisCreate(BaseModel):
    """新建分析记录（内部使用）"""
    opportunity_id: int
    analysis_type: str
    raw_progress_text: Optional[str] = None
    ai_model: Optional[str] = None
    risk_signals: Optional[list[dict]] = None
    priority_suggestion: Optional[int] = None
    suggested_actions: Optional[list[str]] = None
    full_response: Optional[str] = None
    confidence_score: Optional[float] = None
