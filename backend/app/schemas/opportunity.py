from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator


class UserBrief(BaseModel):
    """简略用户信息（用于嵌套在商机响应中）"""
    id: int
    real_name: str
    email: str
    role: str

    model_config = {"from_attributes": True}


class OpportunityCreate(BaseModel):
    serial_no: Optional[int] = None
    division_member_id: Optional[int] = None
    customer_type: Optional[str] = None
    opportunity_status: Optional[str] = None
    opportunity_duration: Optional[int] = None
    deal_scale: Optional[str] = None
    branch_office: Optional[str] = None
    group_code: Optional[str] = None
    opportunity_name: str
    customer_name: str
    predicted_amount: Optional[Decimal] = None
    product_category: Optional[str] = None
    product_name: Optional[str] = None
    created_date: Optional[date] = None
    last_push_date: Optional[date] = None
    account_manager_id: Optional[int] = None
    branch_director_id: Optional[int] = None
    leader_name: Optional[str] = None
    requirement_detail: Optional[str] = None
    estimated_sign_date: Optional[date] = None
    is_list_customer: Optional[bool] = False
    is_bid_required: Optional[bool] = False

    @field_validator("created_date", "last_push_date", "estimated_sign_date", mode="before")
    @classmethod
    def coerce_datetime_to_date(cls, v):
        if isinstance(v, datetime):
            return v.date()
        return v


class OpportunityUpdate(BaseModel):
    serial_no: Optional[int] = None
    division_member_id: Optional[int] = None
    customer_type: Optional[str] = None
    opportunity_status: Optional[str] = None
    opportunity_duration: Optional[int] = None
    deal_scale: Optional[str] = None
    branch_office: Optional[str] = None
    group_code: Optional[str] = None
    opportunity_name: Optional[str] = None
    customer_name: Optional[str] = None
    predicted_amount: Optional[Decimal] = None
    product_category: Optional[str] = None
    product_name: Optional[str] = None
    created_date: Optional[date] = None
    last_push_date: Optional[date] = None
    no_push_days: Optional[int] = None
    no_push_flag: Optional[int] = None
    close_flag: Optional[int] = None
    notify_flag: Optional[int] = None
    account_manager_id: Optional[int] = None
    branch_director_id: Optional[int] = None
    leader_name: Optional[str] = None
    requirement_detail: Optional[str] = None
    weekly_progress: Optional[str] = None
    final_amount: Optional[Decimal] = None
    contract_code: Optional[str] = None
    remarks: Optional[str] = None
    estimated_sign_date: Optional[date] = None
    is_list_customer: Optional[bool] = None
    is_bid_required: Optional[bool] = None

    @field_validator("created_date", "last_push_date", "estimated_sign_date", mode="before")
    @classmethod
    def coerce_datetime_to_date(cls, v):
        if isinstance(v, datetime):
            return v.date()
        return v


class OpportunityResponse(BaseModel):
    id: int
    serial_no: Optional[int] = None
    division_member_id: Optional[int] = None
    division_member: Optional[UserBrief] = None
    customer_type: Optional[str] = None
    opportunity_status: Optional[str] = None
    opportunity_duration: Optional[int] = None
    deal_scale: Optional[str] = None
    branch_office: Optional[str] = None
    group_code: Optional[str] = None
    opportunity_name: str
    customer_name: str
    predicted_amount: Optional[Decimal] = None
    product_category: Optional[str] = None
    product_name: Optional[str] = None
    created_date: Optional[date] = None
    last_push_date: Optional[date] = None
    no_push_days: Optional[int] = None
    no_push_flag: Optional[int] = None
    close_flag: Optional[int] = None
    notify_flag: Optional[int] = None
    account_manager_id: Optional[int] = None
    account_manager: Optional[UserBrief] = None
    branch_director_id: Optional[int] = None
    branch_director: Optional[UserBrief] = None
    leader_name: Optional[str] = None
    requirement_detail: Optional[str] = None
    weekly_progress: Optional[str] = None
    final_amount: Optional[Decimal] = None
    contract_code: Optional[str] = None
    remarks: Optional[str] = None
    estimated_sign_date: Optional[date] = None
    is_list_customer: Optional[bool] = False
    priority_level: Optional[int] = 2
    ai_risk_level: Optional[str] = None
    ai_analysis_summary: Optional[str] = None
    last_ai_analysis_at: Optional[datetime] = None
    next_action_required: Optional[str] = None
    competitor_detected: Optional[bool] = False
    bid_date_approaching: Optional[bool] = False
    is_bid_required: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OpportunityListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[OpportunityResponse]


class ProgressBrief(BaseModel):
    """进度记录简要信息"""
    id: int
    updater_role: str
    progress_content: str
    progress_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updater_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AiAnalysisBrief(BaseModel):
    """AI分析结果简要信息"""
    id: int
    analysis_type: str
    risk_signals: Optional[list] = None
    priority_suggestion: Optional[int] = None
    suggested_actions: Optional[list] = None
    confidence_score: Optional[float] = None
    role_conflicts: Optional[list] = None
    timeline_analysis: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OpportunityDetailResponse(OpportunityResponse):
    """商机完整详情（包含进度记录和AI分析历史）"""
    progress_records: list[ProgressBrief] = []
    ai_analysis_history: list[AiAnalysisBrief] = []
    total_progress_count: int = 0
    total_analysis_count: int = 0
