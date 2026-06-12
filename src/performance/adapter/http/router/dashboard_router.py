from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.adapter.http.router.deps import CurrentUser
from src.infrastructure.database.session import get_db_session
from src.performance.adapter.http.schema.dashboard_schema import (
    AlertDismissRequest,
    AlertItemResponse,
    DashboardSummaryResponse,
    DashboardTrendResponse,
    GroupDistributionResponse,
    KpiResponse,
    TrendPointResponse,
)
from src.performance.application.service.dashboard_service import DashboardService

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary", status_code=status.HTTP_200_OK)
async def get_summary(unionId: str, period: str = Query(pattern=r"^\d{4}-\d{2}$"), current: CurrentUser = None, session: DbSession = None) -> ORJSONResponse:
    if current.union_id != unionId and current.role != "UNION_ADMIN":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    svc = DashboardService(session)
    item = await svc.get_summary(unionId, period)
    return ORJSONResponse({"data": DashboardSummaryResponse(
        unionId=item.union_id,
        period=item.period,
        avgScore=float(item.avg_score),
        scoreDelta=float(item.score_delta),
        memberCount=item.member_count,
        groupDistribution=GroupDistributionResponse(
            top=item.group_top,
            middle=item.group_middle,
            needsImprovement=item.group_needs_improvement,
        ),
        kpi=KpiResponse(
            shippingHitRate=float(item.shipping_hit_rate),
            avgRevenue=item.avg_revenue,
            reportTimeReduced=float(item.report_time_reduced),
        ),
        lastUpdated=item.last_updated,
    ).model_dump()})


@router.get("/trends", status_code=status.HTTP_200_OK)
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
    svc = DashboardService(session)
    rows = await svc.get_trends(unionId, from_, to, metric)
    return ORJSONResponse({"data": DashboardTrendResponse(metric=metric, series=[TrendPointResponse(period=r.period, value=float(r.value)) for r in rows]).model_dump()})


@router.get("/alerts", status_code=status.HTTP_200_OK)
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
    return ORJSONResponse({
        "data": [AlertItemResponse(
            id=r.id,
            level=r.level,
            type=r.type,
            title=r.title,
            message=r.message,
            affectedMembers=r.affected_members,
            createdAt=r.created_at,
            actionUrl=r.action_url,
        ).model_dump() for r in rows],
        "page": page,
        "size": size,
        "totalElements": total,
        "totalPages": total_pages,
        "hasNext": (page + 1) < total_pages,
    })


@router.patch("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_alert(alert_id: str, body: AlertDismissRequest, current: CurrentUser, session: DbSession) -> None:
    if current.role not in ("UNION_ADMIN", "CONSULTANT"):
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    svc = DashboardService(session)
    await svc.dismiss_alert(alert_id, body.status)
    return None
