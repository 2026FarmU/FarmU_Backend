"""UnionQueryPort DB 구현체."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.adapter.persistence.model.union_model import UnionOrmModel
from src.auth.application.port.required.union_query_port import UnionQueryPort


class UnionQueryImpl(UnionQueryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_id_by_code(self, union_code: str) -> str | None:
        stmt = select(UnionOrmModel.id).where(UnionOrmModel.code == union_code)
        result = await self._session.scalar(stmt)
        return str(result) if result else None
