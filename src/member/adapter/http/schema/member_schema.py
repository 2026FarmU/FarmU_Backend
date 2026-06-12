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
    weight: int
    percentile: int


class AnalysisComponentResponse(BaseModel):
    production: ScoreDetailResponse
    shipping: ScoreDetailResponse
    revenue: ScoreDetailResponse


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
    category: str
    expectedImpact: ExpectedImpactResponse


class MemberAnalysisResponse(BaseModel):
    memberId: str
    period: str
    totalScore: float
    components: AnalysisComponentResponse
    xaiFactors: list[XaiFactorResponse]
    improvementTasks: list[ImprovementTaskResponse]
