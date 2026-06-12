from datetime import date

from pydantic import BaseModel


class ExpectedRevenueResponse(BaseModel):
    min: int
    expected: int
    max: int


class RiskFactorResponse(BaseModel):
    type: str
    score: float
    note: str


class RecommendationItemResponse(BaseModel):
    id: str
    memberId: str
    livestockId: str
    currentWeight: float
    targetWeight: float
    recommendedDate: date
    recommendedAction: str
    confidence: float
    expectedRevenue: ExpectedRevenueResponse
    riskFactors: list[RiskFactorResponse]
    rationale: str


class DecisionRequest(BaseModel):
    decision: str
    actualShipDate: date | None = None
    memo: str | None = None


class MonthlyAccuracyResponse(BaseModel):
    period: str
    totalRecommendations: int
    accepted: int
    hitRate: float


class AccuracyResponse(BaseModel):
    overallHitRate: float
    monthly: list[MonthlyAccuracyResponse]
