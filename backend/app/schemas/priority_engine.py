from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PriorityEvaluateRequest(BaseModel):
    """单条商机优先级评估请求"""
    opportunity_id: int


class PriorityEvaluateResponse(BaseModel):
    """单条商机优先级评估结果"""
    opportunity_id: int
    opportunity_name: str
    current_priority: int
    suggested_priority: int
    priority_changed: bool
    score_breakdown: dict
    reason: str
    evaluated_at: datetime

    model_config = {"from_attributes": True}


class BatchEvaluateRequest(BaseModel):
    """批量评估请求"""
    opportunity_ids: Optional[list[int]] = None
    filter_no_push_days_gt: Optional[int] = None
    filter_priority_levels: Optional[list[int]] = None
    dry_run: bool = Field(default=True, description="为 true 时不实际写入数据库")


class BatchEvaluateResponse(BaseModel):
    """批量评估结果"""
    total_evaluated: int
    priority_changed: int
    errors: int
    results: list[PriorityEvaluateResponse]


class ManualPriorityAdjustRequest(BaseModel):
    """手动调整优先级请求"""
    opportunity_id: int
    new_priority: int = Field(..., ge=1, le=3, description="1=高 2=中 3=低")
    reason: str = Field(..., min_length=1, max_length=500)


class ManualPriorityAdjustResponse(BaseModel):
    """手动调整优先级结果"""
    opportunity_id: int
    opportunity_name: str
    old_priority: int
    new_priority: int
    reason: str
    changed_by: str
    changed_at: datetime

    model_config = {"from_attributes": True}


class PriorityChangeLogResponse(BaseModel):
    """优先级变更日志"""
    id: int
    opportunity_id: int
    old_priority: int
    new_priority: int
    change_reason: str
    changed_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PriorityChangeLogListResponse(BaseModel):
    """优先级变更日志列表"""
    total: int
    items: list[PriorityChangeLogResponse]


class PriorityDistributionItem(BaseModel):
    """优先级分布统计项"""
    priority_level: int
    priority_label: str
    count: int
    total_amount: Optional[float] = None


class PriorityDistributionResponse(BaseModel):
    """优先级分布统计"""
    distribution: list[PriorityDistributionItem]
    total_opportunities: int
    total_amount: Optional[float] = None
