"""Application 계층 결과 DTO."""
from dataclasses import dataclass

from src.auth.domain.model.role import Role


@dataclass(frozen=True)
class UserInfo:
    user_id: str
    name: str
    role: Role
    union_id: str
    permissions: list[str]


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    refresh_token: str
    expires_in: int
    user: UserInfo


@dataclass(frozen=True)
class RegisterResult:
    user_id: str
