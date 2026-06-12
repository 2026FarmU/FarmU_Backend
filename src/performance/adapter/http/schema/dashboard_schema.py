from datetime import datetime
from pydantic import BaseModel


class GroupDistributionResponse(BaseModel):
    top: int
    middle: int
    needsImprovement: int


class KpiResponse(BaseModel):
    shippingHitRate: float
    avgRevenue: int
    reportTimeReduced: float


class DashboardSummaryResponse(BaseModel):
    unionId: str
    period: str
    avgScore: float
    scoreDelta: float
    memberCount: int
    groupDistribution: GroupDistributionResponse
    kpi: KpiResponse
    lastUpdated: datetime


class TrendPointResponse(BaseModel):
    period: str
    value: float


class DashboardTrendResponse(BaseModel):
    metric: str
    series: list[TrendPointResponse]


class AlertItemResponse(BaseModel):
    id: str
    level: str
    type: str
    title: str
    message: str
    affectedMembers: int
    createdAt: datetime
    actionUrl: str | None


class AlertDismissRequest(BaseModel):
    status: str
