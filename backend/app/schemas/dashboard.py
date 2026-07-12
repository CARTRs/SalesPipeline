from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class StatsOverview(BaseModel):
    total_opportunities: int
    total_users: int
    total_progress_records: int
    open_opportunities: int
    closed_opportunities: int
    no_push_count: int
    bid_approaching_count: int
    competitor_detected_count: int
    pending_amount: Optional[float] = None


class PriorityItem(BaseModel):
    priority_level: int
    count: int


class PriorityDistribution(BaseModel):
    items: list[PriorityItem]


class StatusItem(BaseModel):
    opportunity_status: str
    count: int


class StatusDistribution(BaseModel):
    items: list[StatusItem]


class RiskItem(BaseModel):
    risk_level: str
    count: int


class RiskOverview(BaseModel):
    items: list[RiskItem]


class RecentActivityItem(BaseModel):
    id: int
    opportunity_id: int
    opportunity_name: str
    progress_content: str
    updater_name: str
    updater_role: str
    progress_date: date
    created_at: datetime


class RecentActivity(BaseModel):
    items: list[RecentActivityItem]


class UrgentOverview(BaseModel):
    no_push_opportunities: list[dict]
    bid_approaching_opportunities: list[dict]
    competitor_detected_opportunities: list[dict]


class BranchStatsItem(BaseModel):
    branch_office: str
    opportunity_count: int
    total_predicted_amount: Optional[Decimal] = None


class BranchStats(BaseModel):
    items: list[BranchStatsItem]
