from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.adapter.http.router.deps import CurrentUser
from src.infrastructure.database.session import get_db_session
from src.member.adapter.http.schema.member_schema import (
    AnalysisComponentResponse,
    ExpectedImpactResponse,
    ImprovementTaskResponse,
    MemberAnalysisResponse,
    MemberRankingItemResponse,
    RankingComponentResponse,
    ScoreDetailResponse,
    XaiFactorResponse,
)
from src.member.application.service.member_service import MemberService

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

router = APIRouter(prefix="/api/v1/members", tags=["members"])


@router.get("/ranking", status_code=status.HTTP_200_OK)
async def get_ranking(
    unionId: str,
    period: str = Query(pattern=r"^\d{4}-\d{2}$"),
    group: str = Query(default="ALL", pattern="^(ALL|TOP|MIDDLE|NEEDS_IMPROVEMENT)$"),
    page: int = 0,
    size: int = 20,
    current: CurrentUser = None,
    session: DbSession = None,
) -> ORJSONResponse:
    if current and current.union_id != unionId and current.role != "UNION_ADMIN":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    svc = MemberService(session)
    rows, total = await svc.get_ranking(unionId, period, group, page, size)
    total_pages = 0 if total == 0 else (total + size - 1) // size
    return ORJSONResponse({
        "data": [MemberRankingItemResponse(
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
        ).model_dump() for m, p in rows],
        "page": page,
        "size": size,
        "totalElements": total,
        "totalPages": total_pages,
        "hasNext": (page + 1) < total_pages,
    })


@router.get("/{member_id}/analysis", status_code=status.HTTP_200_OK)
async def get_analysis(member_id: str, period: str = Query(pattern=r"^\d{4}-\d{2}$"), current: CurrentUser = None, session: DbSession = None) -> ORJSONResponse:
    svc = MemberService(session)
    member = await svc.get_member(member_id)
    if current.union_id != member.union_id and current.role != "UNION_ADMIN":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    perf, factors, tasks = await svc.get_analysis(member_id, period)

    return ORJSONResponse({"data": MemberAnalysisResponse(
        memberId=member_id,
        period=period,
        totalScore=float(perf.score),
        components=AnalysisComponentResponse(
            production=ScoreDetailResponse(score=float(perf.production_score), weight=perf.production_weight, percentile=perf.production_percentile),
            shipping=ScoreDetailResponse(score=float(perf.shipping_score), weight=perf.shipping_weight, percentile=perf.shipping_percentile),
            revenue=ScoreDetailResponse(score=float(perf.revenue_score), weight=perf.revenue_weight, percentile=perf.revenue_percentile),
        ),
        xaiFactors=[XaiFactorResponse(factor=f.factor, contribution=float(f.contribution), direction=f.direction, description=f.description) for f in factors],
        improvementTasks=[
            ImprovementTaskResponse(
                taskId=t.id,
                priority=t.priority,
                title=t.title,
                category=t.category,
                expectedImpact=ExpectedImpactResponse(
                    scoreDelta=float(t.expected_score_delta),
                    revenueDelta=t.expected_revenue_delta,
                ),
            )
            for t in tasks
        ],
    ).model_dump()})
