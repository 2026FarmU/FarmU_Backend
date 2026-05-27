from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TokenPayload:
    user_id: str
    role: str
    union_id: str


class JwtService(ABC):
    """JWT 토큰 생성·검증 인터페이스."""

    @abstractmethod
    def create_access_token(self, payload: TokenPayload) -> tuple[str, int]:
        """(token_string, expires_in_seconds) 반환."""
        ...

    @abstractmethod
    def create_refresh_token(self, payload: TokenPayload) -> str: ...

    @abstractmethod
    def decode_access_token(self, token: str) -> TokenPayload:
        """만료/변조 시 도메인 예외 raise."""
        ...

    @abstractmethod
    def decode_refresh_token(self, token: str) -> TokenPayload: ...
