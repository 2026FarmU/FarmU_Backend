from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.member.adapter.persistence.model.member_model import (
    MemberImprovementTaskOrmModel,
    MemberOrmModel,
    MemberPerformanceOrmModel,
    MemberXaiFactorOrmModel,
)
from src.shared.domain.exception import EntityNotFoundException


class MemberService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_ranking(self, union_id: str, period: str, group: str, page: int, size: int) -> tuple[list[tuple[MemberOrmModel, MemberPerformanceOrmModel]], int]:
        filters = [
            MemberPerformanceOrmModel.union_id == union_id,
            MemberPerformanceOrmModel.period == period,
            MemberPerformanceOrmModel.member_id == MemberOrmModel.id,
        ]
        if group != "ALL":
            filters.append(MemberOrmModel.group_name == group)

        total = await self._session.scalar(select(func.count(MemberPerformanceOrmModel.id)).select_from(MemberPerformanceOrmModel, MemberOrmModel).where(*filters))
        rows = await self._session.execute(
            select(MemberOrmModel, MemberPerformanceOrmModel)
            .where(*filters)
            .order_by(MemberPerformanceOrmModel.rank.asc())
            .offset(page * size)
            .limit(size)
        )
        return list(rows.all()), int(total or 0)

    async def get_analysis(self, member_id: str, period: str) -> tuple[MemberPerformanceOrmModel, list[MemberXaiFactorOrmModel], list[MemberImprovementTaskOrmModel]]:
        perf = await self._session.scalar(
            select(MemberPerformanceOrmModel).where(
                MemberPerformanceOrmModel.member_id == member_id,
                MemberPerformanceOrmModel.period == period,
            )
        )
        if perf is None:
            raise EntityNotFoundException("Member", member_id)

        factors = list(await self._session.scalars(
            select(MemberXaiFactorOrmModel)
            .where(MemberXaiFactorOrmModel.member_id == member_id, MemberXaiFactorOrmModel.period == period)
            .order_by(MemberXaiFactorOrmModel.id.asc())
        ))
        tasks = list(await self._session.scalars(
            select(MemberImprovementTaskOrmModel)
            .where(MemberImprovementTaskOrmModel.member_id == member_id, MemberImprovementTaskOrmModel.period == period)
            .order_by(MemberImprovementTaskOrmModel.priority.asc())
        ))
        return perf, factors, tasks

    async def get_member(self, member_id: str) -> MemberOrmModel:
        m = await self._session.get(MemberOrmModel, member_id)
        if m is None:
            raise EntityNotFoundException("Member", member_id)
        return m
