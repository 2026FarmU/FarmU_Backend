from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import ORJSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account_models import UserMemberLinkOrmModel
from src.auth.adapter.http.router.deps import CurrentUser
from src.infrastructure.database.session import get_db_session
from src.land.adapter.persistence.model.land_model import LandOrmModel, LandSuitabilityOrmModel
from src.main.response_schema import DataResponse
from src.member.adapter.http.schema.member_schema import (
    AnalysisComponentResponse,
    CropSuitabilityItem,
    ExpectedImpactResponse,
    ImprovementTaskResponse,
    MemberAnalysisResponse,
    MemberRankingItemResponse,
    MemberRankingPageResponse,
    RankingComponentResponse,
    ScoreDetailResponse,
    ScoreHistoryItem,
    XaiFactorResponse,
)
from src.member.adapter.persistence.model.member_model import MemberPerformanceOrmModel
from src.member.application.service.member_service import MemberService

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

router = APIRouter(prefix="/api/v1/members", tags=["members"])


async def _latest_period(session: AsyncSession, union_id: str) -> str:
    period = await session.scalar(
        select(func.max(MemberPerformanceOrmModel.period)).where(
            MemberPerformanceOrmModel.union_id == union_id
        )
    )
    if period is None:
        raise HTTPException(status_code=404, detail="성과 데이터가 없습니다.")
    return period


async def _available_periods(session: AsyncSession, union_id: str) -> list[str]:
    return list(
        (
            await session.scalars(
                select(MemberPerformanceOrmModel.period)
                .where(MemberPerformanceOrmModel.union_id == union_id)
                .distinct()
                .order_by(MemberPerformanceOrmModel.period.desc())
            )
        ).all()
    )


@router.get(
    "/ranking", status_code=status.HTTP_200_OK, response_model=MemberRankingPageResponse
)
async def get_ranking(
    unionId: str,
    period: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    group: str = Query(default="ALL", pattern="^(ALL|TOP|MID|LOW)$"),
    page: int = 0,
    size: int = 20,
    current: CurrentUser = None,
    session: DbSession = None,
) -> ORJSONResponse:
    if current and current.union_id != unionId and current.role != "UNION_ADMIN":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    period = period or await _latest_period(session, unionId)
    svc = MemberService(session)
    rows, total = await svc.get_ranking(unionId, period, group, page, size)
    total_pages = 0 if total == 0 else (total + size - 1) // size
    return ORJSONResponse(
        {
            "data": [
                MemberRankingItemResponse(
                    memberId=m.id,
                    rank=p.rank,
                    name=m.name,
                    group=m.group_name,
                    score=float(p.score),
                    scoreDelta=float(p.score_delta),
                    components=RankingComponentResponse(
                        production=float(p.production_score),
                        shipping=float(p.shipping_score),
                        revenue=float(p.revenue_score),
                    ),
                    mainCrop=m.main_crop,
                    region=m.region,
                ).model_dump()
                for m, p in rows
            ],
            "page": page,
            "size": size,
            "totalElements": total,
            "totalPages": total_pages,
            "hasNext": (page + 1) < total_pages,
            "availablePeriods": await _available_periods(session, unionId),
        }
    )


@router.get(
    "/me/analysis",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[MemberAnalysisResponse],
)
async def get_my_analysis(
    current: CurrentUser,
    session: DbSession,
    period: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
) -> ORJSONResponse:
    link = await session.get(UserMemberLinkOrmModel, current.user_id)
    if link is None:
        raise HTTPException(status_code=404, detail="사용자와 연결된 조합원이 없습니다.")
    return await get_analysis(link.member_id, period, current, session)


@router.get(
    "/{member_id}/analysis",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[MemberAnalysisResponse],
)
async def get_analysis(
    member_id: str,
    period: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    current: CurrentUser = None,
    session: DbSession = None,
) -> ORJSONResponse:
    svc = MemberService(session)
    member = await svc.get_member(member_id)
    if current.union_id != member.union_id and current.role != "UNION_ADMIN":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    period = period or await _latest_period(session, member.union_id)
    perf, factors, tasks = await svc.get_analysis(member_id, period)
    rank_total = int(
        await session.scalar(
            select(func.count(MemberPerformanceOrmModel.id)).where(
                MemberPerformanceOrmModel.union_id == member.union_id,
                MemberPerformanceOrmModel.period == period,
            )
        )
        or 0
    )
    history = list(
        (
            await session.scalars(
                select(MemberPerformanceOrmModel)
                .where(MemberPerformanceOrmModel.member_id == member_id)
                .order_by(MemberPerformanceOrmModel.period)
            )
        ).all()
    )
    suitability_rows = (
        await session.execute(
            select(LandSuitabilityOrmModel, LandOrmModel)
            .where(
                LandSuitabilityOrmModel.land_id == LandOrmModel.id,
                LandOrmModel.member_id == member_id,
            )
            .order_by(LandSuitabilityOrmModel.score.desc())
        )
    ).all()
    production_value = min(100.0, float(perf.production_score) / perf.production_weight * 100)
    shipping_value = min(100.0, float(perf.shipping_score) / perf.shipping_weight * 100)
    revenue_value = min(100.0, float(perf.revenue_score) / perf.revenue_weight * 100)
    quality_value = round((production_value * 0.7) + (shipping_value * 0.3), 1)
    cost_value = round((revenue_value * 0.7) + (production_value * 0.3), 1)
    baseline = round(float(perf.score) - sum(float(f.contribution) for f in factors), 2)
    years = max(1, datetime.now(UTC).year - member.created_at.year + 1)

    return ORJSONResponse(
        {
            "data": MemberAnalysisResponse(
                memberId=member_id,
                name=member.name,
                crop=member.main_crop,
                region=member.region,
                years=years,
                period=period,
                totalScore=float(perf.score),
                scoreDelta=float(perf.score_delta),
                rank=perf.rank,
                rankTotal=rank_total,
                group=member.group_name,
                shippingHitRate=round(shipping_value, 1),
                components=AnalysisComponentResponse(
                    production=ScoreDetailResponse(
                        score=float(perf.production_score),
                        value=round(production_value, 1),
                        weight=perf.production_weight,
                        percentile=perf.production_percentile,
                    ),
                    shipping=ScoreDetailResponse(
                        score=float(perf.shipping_score),
                        value=round(shipping_value, 1),
                        weight=perf.shipping_weight,
                        percentile=perf.shipping_percentile,
                    ),
                    revenue=ScoreDetailResponse(
                        score=float(perf.revenue_score),
                        value=round(revenue_value, 1),
                        weight=perf.revenue_weight,
                        percentile=perf.revenue_percentile,
                    ),
                    quality=ScoreDetailResponse(
                        score=round(quality_value * 0.1, 2),
                        value=quality_value,
                        weight=10,
                        percentile=round((perf.production_percentile + perf.shipping_percentile) / 2),
                    ),
                    costEfficiency=ScoreDetailResponse(
                        score=round(cost_value * 0.1, 2),
                        value=cost_value,
                        weight=10,
                        percentile=round((perf.revenue_percentile + perf.production_percentile) / 2),
                    ),
                ),
                scoreHistory=[
                    ScoreHistoryItem(period=item.period, score=float(item.score)) for item in history
                ],
                cropSuitability=[
                    CropSuitabilityItem(
                        crop=item.crop,
                        fitScore=float(item.score),
                        current=item.crop == member.main_crop,
                    )
                    for item, _land in suitability_rows
                ],
                baseline=baseline,
                xaiFactors=[
                    XaiFactorResponse(
                        factor=f.factor,
                        contribution=float(f.contribution),
                        direction=f.direction,
                        description=f.description,
                    )
                    for f in factors
                ],
                improvementTasks=[
                    ImprovementTaskResponse(
                        taskId=t.id,
                        priority=t.priority,
                        title=t.title,
                        description=(
                            f"{t.title} 실행 시 점수 {float(t.expected_score_delta):g}점, "
                            f"수익 {t.expected_revenue_delta:,}원 개선이 예상됩니다."
                        ),
                        category=t.category,
                        expectedImpact=ExpectedImpactResponse(
                            scoreDelta=float(t.expected_score_delta),
                            revenueDelta=t.expected_revenue_delta,
                        ),
                    )
                    for t in tasks
                ],
                availablePeriods=await _available_periods(session, member.union_id),
            ).model_dump()
        }
    )
