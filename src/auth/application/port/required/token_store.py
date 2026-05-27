from abc import ABC, abstractmethod


class TokenStore(ABC):
    """리프레시 토큰 저장소 + 액세스 토큰 블랙리스트 (Redis)."""

    @abstractmethod
    async def save_refresh_token(
        self, user_id: str, token: str, ttl_seconds: int
    ) -> None: ...

    @abstractmethod
    async def get_refresh_token(self, user_id: str) -> str | None: ...

    @abstractmethod
    async def delete_refresh_token(self, user_id: str) -> None: ...

    @abstractmethod
    async def blacklist_access_token(self, token: str, ttl_seconds: int) -> None: ...

    @abstractmethod
    async def is_blacklisted(self, token: str) -> bool: ...
