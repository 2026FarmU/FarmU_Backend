from datetime import datetime

from pydantic import BaseModel


class GroupDistributionResponse(BaseModel):
    top: int
    mid: int
    low: int


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
    availablePeriods: list[str]


class TrendPointResponse(BaseModel):
    period: str
    value: float


class TrendSeriesResponse(BaseModel):
    name: str
    points: list[TrendPointResponse]


class DashboardTrendResponse(BaseModel):
    metric: str
    series: list[TrendSeriesResponse]


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


class AlertPageResponse(BaseModel):
    data: list[AlertItemResponse]
    page: int
    size: int
    totalElements: int
    totalPages: int
    hasNext: bool
