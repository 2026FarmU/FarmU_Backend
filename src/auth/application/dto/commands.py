"""Application 계층 커맨드 DTO."""
from dataclasses import dataclass


@dataclass(frozen=True)
class LoginCommand:
    login_id: str
    password: str
    union_code: str


@dataclass(frozen=True)
class RefreshTokenCommand:
    refresh_token: str
