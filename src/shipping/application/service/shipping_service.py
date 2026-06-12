from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shipping.adapter.persistence.model.shipping_model import (
    ShippingAccuracyOrmModel,
    ShippingRecommendationOrmModel,
)
from src.shipping.domain.exception import (
    RecommendationAlreadyDecidedException,
    RecommendationNotFoundException,
)


class ShippingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_recommendations(
        self,
        union_id: str | None,
        member_id: str | None,
        status: str | None,
    ) -> list[ShippingRecommendationOrmModel]:
        filters = []
        if union_id:
            filters.append(ShippingRecommendationOrmModel.union_id == union_id)
        if member_id:
            filters.append(ShippingRecommendationOrmModel.member_id == member_id)
        if status:
            filters.append(ShippingRecommendationOrmModel.status == status)

        stmt = select(ShippingRecommendationOrmModel)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(ShippingRecommendationOrmModel.created_at.desc())
        return list(await self._session.scalars(stmt))

    async def decide_recommendation(
        self,
        recommendation_id: str,
        decision: str,
        actual_ship_date,
        memo: str | None,
    ) -> None:
        item = await self._session.get(ShippingRecommendationOrmModel, recommendation_id)
        if item is None:
            raise RecommendationNotFoundException(recommendation_id)
        if item.status != "PENDING":
            raise RecommendationAlreadyDecidedException(recommendation_id)

        item.status = decision
        item.actual_ship_date = actual_ship_date
        item.decision_memo = memo
        await self._session.flush()

    async def get_accuracy(
        self,
        union_id: str,
        from_period: str,
        to_period: str,
    ) -> list[ShippingAccuracyOrmModel]:
        return list(
            await self._session.scalars(
                select(ShippingAccuracyOrmModel)
                .where(
                    ShippingAccuracyOrmModel.union_id == union_id,
                    ShippingAccuracyOrmModel.period >= from_period,
                    ShippingAccuracyOrmModel.period <= to_period,
                )
                .order_by(ShippingAccuracyOrmModel.period.asc())
            )
        )
