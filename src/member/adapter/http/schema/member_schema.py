from typing import Literal

from pydantic import BaseModel


class RankingComponentResponse(BaseModel):
    production: float
    shipping: float
    revenue: float


class MemberRankingItemResponse(BaseModel):
    memberId: str
    rank: int
    name: str
    group: str
    score: float
    scoreDelta: float
    components: RankingComponentResponse
    mainCrop: str
    region: str


class ScoreDetailResponse(BaseModel):
    score: float
    value: float
    weight: int
    percentile: int


class AnalysisComponentResponse(BaseModel):
    production: ScoreDetailResponse
    shipping: ScoreDetailResponse
    revenue: ScoreDetailResponse
    quality: ScoreDetailResponse
    costEfficiency: ScoreDetailResponse


class XaiFactorResponse(BaseModel):
    factor: str
    contribution: float
    direction: str
    description: str


class ExpectedImpactResponse(BaseModel):
    scoreDelta: float
    revenueDelta: int


class ImprovementTaskResponse(BaseModel):
    taskId: str
    priority: int
    title: str
    description: str
    category: str
    expectedImpact: ExpectedImpactResponse


class ScoreHistoryItem(BaseModel):
    period: str
    score: float


class CropSuitabilityItem(BaseModel):
    crop: str
    fitScore: float
    current: bool


class MemberAnalysisResponse(BaseModel):
    memberId: str
    name: str
    crop: str
    region: str
    years: int
    period: str
    totalScore: float
    scoreDelta: float
    rank: int
    rankTotal: int
    group: Literal["TOP", "MID", "LOW"]
    shippingHitRate: float
    components: AnalysisComponentResponse
    scoreHistory: list[ScoreHistoryItem]
    cropSuitability: list[CropSuitabilityItem]
    baseline: float
    xaiFactors: list[XaiFactorResponse]
    improvementTasks: list[ImprovementTaskResponse]
    availablePeriods: list[str]


class MemberRankingPageResponse(BaseModel):
    data: list[MemberRankingItemResponse]
    page: int
    size: int
    totalElements: int
    totalPages: int
    hasNext: bool
    availablePeriods: list[str]
