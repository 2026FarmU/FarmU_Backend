"""User 리포지토리 인터페이스 (outbound port)."""
from abc import ABC, abstractmethod

from src.auth.domain.model.user import User
from src.auth.domain.model.vo import LoginId, UnionId, UserId


class UserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: UserId) -> User | None: ...

    @abstractmethod
    async def find_by_login_id_and_union(
        self, login_id: LoginId, union_id: UnionId
    ) -> User | None: ...

    @abstractmethod
    async def exists_by_login_id_and_union(
        self, login_id: LoginId, union_id: UnionId
    ) -> bool: ...

    @abstractmethod
    async def save(self, user: User) -> User: ...
