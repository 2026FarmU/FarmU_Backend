"""UserRepository SQLAlchemy 구현체."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.adapter.persistence.model.user_model import UserOrmModel
from src.auth.domain.model.role import Role
from src.auth.domain.model.user import User
from src.auth.domain.model.vo import LoginId, UnionId, UserId
from src.auth.domain.repository.user_repository import UserRepository


class UserRepositoryImpl(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── mapping helpers ───────────────────────────────────────────

    @staticmethod
    def _to_domain(orm: UserOrmModel) -> User:
        return User(
            id=UserId(orm.id),
            login_id=LoginId(orm.login_id),
            hashed_password=orm.hashed_password,
            name=orm.name,
            role=Role(orm.role),
            union_id=UnionId(orm.union_id),
            is_withdrawn=orm.is_withdrawn,
            created_at=orm.created_at,
        )

    @staticmethod
    def _to_orm(user: User) -> UserOrmModel:
        return UserOrmModel(
            id=str(user.id),
            login_id=str(user.login_id),
            hashed_password=user.hashed_password,
            name=user.name,
            role=user.role.value,
            union_id=str(user.union_id),
            is_withdrawn=user.is_withdrawn,
            created_at=user.created_at,
        )

    # ── interface 구현 ────────────────────────────────────────────

    async def find_by_id(self, user_id: UserId) -> User | None:
        result = await self._session.get(UserOrmModel, str(user_id))
        return self._to_domain(result) if result else None

    async def find_by_login_id_and_union(
        self, login_id: LoginId, union_id: UnionId
    ) -> User | None:
        stmt = select(UserOrmModel).where(
            UserOrmModel.login_id == str(login_id),
            UserOrmModel.union_id == str(union_id),
        )
        result = await self._session.scalar(stmt)
        return self._to_domain(result) if result else None

    async def exists_by_login_id_and_union(
        self, login_id: LoginId, union_id: UnionId
    ) -> bool:
        stmt = select(UserOrmModel.id).where(
            UserOrmModel.login_id == str(login_id),
            UserOrmModel.union_id == str(union_id),
        )
        result = await self._session.scalar(stmt)
        return result is not None

    async def save(self, user: User) -> User:
        orm = self._to_orm(user)
        merged = await self._session.merge(orm)
        await self._session.flush()
        return self._to_domain(merged)
