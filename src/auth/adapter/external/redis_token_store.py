"""Redis 기반 TokenStore."""
import hashlib

from redis.asyncio import Redis

from src.auth.application.port.required.token_store import TokenStore

_REFRESH_PREFIX = "refresh:"
_BLACKLIST_PREFIX = "blacklist:"


def _bl_key(token: str) -> str:
    """토큰 해시를 키로 사용 (토큰 길이 절약)."""
    return _BLACKLIST_PREFIX + hashlib.sha256(token.encode()).hexdigest()


class RedisTokenStore(TokenStore):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def save_refresh_token(
        self, user_id: str, token: str, ttl_seconds: int
    ) -> None:
        await self._redis.setex(_REFRESH_PREFIX + user_id, ttl_seconds, token)

    async def get_refresh_token(self, user_id: str) -> str | None:
        value = await self._redis.get(_REFRESH_PREFIX + user_id)
        return value if isinstance(value, str) else (value.decode() if value else None)

    async def delete_refresh_token(self, user_id: str) -> None:
        await self._redis.delete(_REFRESH_PREFIX + user_id)

    async def blacklist_access_token(self, token: str, ttl_seconds: int) -> None:
        await self._redis.setex(_bl_key(token), ttl_seconds, "1")

    async def is_blacklisted(self, token: str) -> bool:
        return bool(await self._redis.exists(_bl_key(token)))
