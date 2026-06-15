from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.adapter.http.router.deps import CurrentUser
from src.infrastructure.database.session import get_db_session
from src.main.response_schema import DataResponse, ListResponse
from src.shipping.adapter.http.schema.shipping_schema import (
    AccuracyResponse,
    DecisionRequest,
    ExpectedRevenueResponse,
    MonthlyAccuracyResponse,
    RecommendationItemResponse,
    RiskFactorResponse,
)
from src.shipping.application.service.shipping_service import ShippingService

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

router = APIRouter(prefix="/api/v1/shipping", tags=["shipping"])


@router.get(
    "/recommendations",
    status_code=status.HTTP_200_OK,
    response_model=ListResponse[RecommendationItemResponse],
)
async def get_recommendations(
    unionId: str | None = None,
    memberId: str | None = None,
    status_: str | None = Query(default=None, alias="status", pattern="^(PENDING|ACCEPTED|REJECTED)$"),
    current: CurrentUser = None,
    session: DbSession = None,
) -> ORJSONResponse:
    if unionId and current and current.union_id != unionId and current.role != "UNION_ADMIN":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    svc = ShippingService(session)
    rows = await svc.get_recommendations(unionId, memberId, status_)

    return ORJSONResponse({
        "data": [
            RecommendationItemResponse(
                id=r.id,
                memberId=r.member_id,
                livestockId=r.livestock_id,
                currentWeight=float(r.current_weight),
                targetWeight=float(r.target_weight),
                recommendedDate=r.recommended_date,
                recommendedAction=r.recommended_action,
                confidence=float(r.confidence),
                expectedRevenue=ExpectedRevenueResponse(
                    min=r.expected_revenue_min,
                    expected=r.expected_revenue_expected,
                    max=r.expected_revenue_max,
                ),
                riskFactors=[
                    RiskFactorResponse(type=r.risk_type, score=float(r.risk_score), note=r.risk_note)
                ],
                rationale=r.rationale,
            ).model_dump()
            for r in rows
        ]
    })


@router.post("/recommendations/{recommendation_id}/decision", status_code=status.HTTP_204_NO_CONTENT)
async def decide_recommendation(
    recommendation_id: str,
    body: DecisionRequest,
    current: CurrentUser,
    session: DbSession,
) -> None:
    if body.decision not in ("ACCEPTED", "REJECTED"):
        raise HTTPException(status_code=400, detail="INVALID_REQUEST")
    svc = ShippingService(session)
    await svc.decide_recommendation(recommendation_id, body.decision, body.actualShipDate, body.memo)


@router.get(
    "/accuracy", status_code=status.HTTP_200_OK, response_model=DataResponse[AccuracyResponse]
)
async def get_accuracy(
    unionId: str,
    from_: str = Query(alias="from", pattern=r"^\d{4}-\d{2}$"),
    to: str = Query(pattern=r"^\d{4}-\d{2}$"),
    current: CurrentUser = None,
    session: DbSession = None,
) -> ORJSONResponse:
    if current and current.union_id != unionId and current.role != "UNION_ADMIN":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    svc = ShippingService(session)
    rows = await svc.get_accuracy(unionId, from_, to)
    overall = 0.0
    if rows:
        overall = sum(float(x.hit_rate) for x in rows) / len(rows) * 100

    return ORJSONResponse({"data": AccuracyResponse(
        overallHitRate=overall,
        monthly=[
            MonthlyAccuracyResponse(
                period=r.period,
                totalRecommendations=r.total_recommendations,
                accepted=r.accepted,
                hitRate=round(float(r.hit_rate) * 100),
            )
            for r in rows
        ],
    ).model_dump()})
