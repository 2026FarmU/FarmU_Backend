from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alert.adapter.persistence.model.alert_model import AlertOrmModel
from src.performance.adapter.persistence.model.dashboard_model import UnionKpiOrmModel, UnionTrendOrmModel
from src.performance.domain.exception import PerformanceNotCalculatedException
from src.shared.domain.exception import DomainException, EntityNotFoundException


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_summary(self, union_id: str, period: str) -> UnionKpiOrmModel:
        row = await self._session.scalar(
            select(UnionKpiOrmModel).where(
                UnionKpiOrmModel.union_id == union_id,
                UnionKpiOrmModel.period == period,
            )
        )
        if row is None:
            raise PerformanceNotCalculatedException(period)
        return row

    async def get_trends(self, union_id: str, from_period: str, to_period: str, metric: str) -> list[UnionTrendOrmModel]:
        rows = await self._session.scalars(
            select(UnionTrendOrmModel)
            .where(
                UnionTrendOrmModel.union_id == union_id,
                UnionTrendOrmModel.metric == metric,
                UnionTrendOrmModel.period >= from_period,
                UnionTrendOrmModel.period <= to_period,
            )
            .order_by(UnionTrendOrmModel.period.asc())
        )
        data = list(rows)
        if not data:
            raise PerformanceNotCalculatedException(from_period)
        return data

    async def get_alerts(self, union_id: str, level: str | None, status: str | None, page: int, size: int) -> tuple[list[AlertOrmModel], int]:
        filters = [AlertOrmModel.union_id == union_id]
        if level:
            filters.append(AlertOrmModel.level == level)
        if status:
            filters.append(AlertOrmModel.status == status)

        total = await self._session.scalar(select(func.count(AlertOrmModel.id)).where(*filters))
        rows = await self._session.scalars(
            select(AlertOrmModel)
            .where(*filters)
            .order_by(AlertOrmModel.created_at.desc())
            .offset(page * size)
            .limit(size)
        )
        return list(rows), int(total or 0)

    async def dismiss_alert(self, alert_id: str, status: str) -> None:
        row = await self._session.get(AlertOrmModel, alert_id)
        if row is None:
            raise EntityNotFoundException("Alert", alert_id)
        if status != "DISMISSED":
            raise DomainException("status는 DISMISSED만 허용됩니다.", "INVALID_REQUEST")
        row.status = status
        await self._session.flush()
