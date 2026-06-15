from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import ORJSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.adapter.http.router.deps import CurrentUser
from src.infrastructure.database.session import get_db_session
from src.main.response_schema import DataResponse
from src.member.adapter.persistence.model.member_model import (
    MemberOrmModel,
    MemberPerformanceOrmModel,
)
from src.performance.adapter.http.schema.dashboard_schema import (
    AlertDismissRequest,
    AlertItemResponse,
    AlertPageResponse,
    DashboardSummaryResponse,
    DashboardTrendResponse,
    GroupDistributionResponse,
    KpiResponse,
    TrendPointResponse,
    TrendSeriesResponse,
)
from src.performance.adapter.persistence.model.dashboard_model import UnionKpiOrmModel
from src.performance.application.service.dashboard_service import DashboardService

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


async def _periods(session: AsyncSession, union_id: str) -> list[str]:
    return list(
        (
            await session.scalars(
                select(UnionKpiOrmModel.period)
                .where(UnionKpiOrmModel.union_id == union_id)
                .distinct()
                .order_by(UnionKpiOrmModel.period.desc())
            )
        ).all()
    )


@router.get(
    "/summary",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[DashboardSummaryResponse],
)
async def get_summary(
    unionId: str,
    period: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    current: CurrentUser = None,
    session: DbSession = None,
) -> ORJSONResponse:
    if current.union_id != unionId and current.role != "UNION_ADMIN":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    available_periods = await _periods(session, unionId)
    period = period or (available_periods[0] if available_periods else None)
    if period is None:
        raise HTTPException(status_code=404, detail="성과 데이터가 없습니다.")
    svc = DashboardService(session)
    item = await svc.get_summary(unionId, period)
    return ORJSONResponse(
        {
            "data": DashboardSummaryResponse(
                unionId=item.union_id,
                period=item.period,
                avgScore=float(item.avg_score),
                scoreDelta=float(item.score_delta),
                memberCount=item.member_count,
                groupDistribution=GroupDistributionResponse(
                    top=item.group_top,
                    mid=item.group_middle,
                    low=item.group_needs_improvement,
                ),
                kpi=KpiResponse(
                    shippingHitRate=round(float(item.shipping_hit_rate) * 100),
                    avgRevenue=item.avg_revenue,
                    reportTimeReduced=round(float(item.report_time_reduced) * 100),
                ),
                lastUpdated=item.last_updated,
                availablePeriods=available_periods,
            ).model_dump()
        }
    )


@router.get(
    "/trends",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[DashboardTrendResponse],
)
async def get_trends(
    unionId: str,
    from_: str = Query(alias="from", pattern=r"^\d{4}-\d{2}$"),
    to: str = Query(pattern=r"^\d{4}-\d{2}$"),
    metric: str = Query(pattern="^(score|revenue|shippingHitRate|production)$"),
    current: CurrentUser = None,
    session: DbSession = None,
) -> ORJSONResponse:
    if current and current.union_id != unionId and current.role != "UNION_ADMIN":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    score_column = {
        "score": MemberPerformanceOrmModel.score,
        "revenue": MemberPerformanceOrmModel.revenue_score,
        "shippingHitRate": MemberPerformanceOrmModel.shipping_score,
        "production": MemberPerformanceOrmModel.production_score,
    }[metric]
    query_rows = (
        await session.execute(
            select(
                MemberPerformanceOrmModel.period,
                MemberOrmModel.group_name,
                func.avg(score_column),
                func.count(MemberPerformanceOrmModel.id),
            )
            .where(
                MemberPerformanceOrmModel.member_id == MemberOrmModel.id,
                MemberPerformanceOrmModel.union_id == unionId,
                MemberPerformanceOrmModel.period >= from_,
                MemberPerformanceOrmModel.period <= to,
            )
            .group_by(MemberPerformanceOrmModel.period, MemberOrmModel.group_name)
            .order_by(MemberPerformanceOrmModel.period)
        )
    ).all()
    normalized_rows: list[tuple[str, str, float, int]] = [
        (str(item_period), str(group), float(value), int(count))
        for item_period, group, value, count in query_rows
    ]
    if not normalized_rows:
        svc = DashboardService(session)
        legacy_rows = await svc.get_trends(unionId, from_, to, metric)
        normalized_rows = [(row.period, "ALL", float(row.value), 1) for row in legacy_rows]
    periods = sorted({row[0] for row in normalized_rows})
    grouped = {(period, group): (value, count) for period, group, value, count in normalized_rows}

    def points(group: str) -> list[TrendPointResponse]:
        result = []
        for item_period in periods:
            if group == "ALL":
                values = [item for (p, _g), item in grouped.items() if p == item_period]
                value = sum(score * count for score, count in values) / sum(
                    count for _score, count in values
                )
            else:
                value = grouped.get(
                    (item_period, group), grouped.get((item_period, "ALL"), (0.0, 1))
                )[0]
            if metric == "shippingHitRate":
                value = min(100.0, value / 35 * 100)
            result.append(TrendPointResponse(period=item_period, value=round(value, 1)))
        return result
    return ORJSONResponse(
        {
            "data": DashboardTrendResponse(
                metric=metric,
                series=[
                    TrendSeriesResponse(name="AVERAGE", points=points("ALL")),
                    TrendSeriesResponse(name="TOP", points=points("TOP")),
                    TrendSeriesResponse(name="LOW", points=points("LOW")),
                ],
            ).model_dump()
        }
    )


@router.get("/alerts", status_code=status.HTTP_200_OK, response_model=AlertPageResponse)
async def get_alerts(
    unionId: str,
    level: str | None = Query(default=None, pattern="^(HIGH|MEDIUM|LOW)$"),
    status_: str | None = Query(default=None, alias="status", pattern="^(ACTIVE|DISMISSED)$"),
    page: int = 0,
    size: int = 10,
    current: CurrentUser = None,
    session: DbSession = None,
) -> ORJSONResponse:
    if current and current.union_id != unionId and current.role != "UNION_ADMIN":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    svc = DashboardService(session)
    rows, total = await svc.get_alerts(unionId, level, status_, page, size)
    total_pages = 0 if total == 0 else (total + size - 1) // size
    return ORJSONResponse(
        {
            "data": [
                AlertItemResponse(
                    id=r.id,
                    level=r.level,
                    type=r.type,
                    title=r.title,
                    message=r.message,
                    affectedMembers=r.affected_members,
                    createdAt=r.created_at,
                    actionUrl=r.action_url,
                ).model_dump()
                for r in rows
            ],
            "page": page,
            "size": size,
            "totalElements": total,
            "totalPages": total_pages,
            "hasNext": (page + 1) < total_pages,
        }
    )


@router.patch("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_alert(
    alert_id: str, body: AlertDismissRequest, current: CurrentUser, session: DbSession
) -> None:
    if current.role not in ("UNION_ADMIN", "CONSULTANT"):
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    svc = DashboardService(session)
    await svc.dismiss_alert(alert_id, body.status)
    return None
