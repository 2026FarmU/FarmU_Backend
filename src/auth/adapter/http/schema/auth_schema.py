"""Auth HTTP 요청/응답 Pydantic 스키마."""
from typing import Literal

from pydantic import BaseModel, Field


# ── 요청 ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    loginId: str = Field(..., min_length=3, description="로그인 ID")
    password: str = Field(..., min_length=1, description="비밀번호")
    unionCode: str = Field(..., description="조합 코드")


class RegisterRequest(BaseModel):
    loginId: str = Field(..., min_length=3, description="로그인 ID")
    password: str = Field(..., min_length=1, description="비밀번호")
    name: str = Field(..., min_length=1, description="이름")
    unionCode: str = Field(..., description="조합 코드")


class CreateUserRequest(BaseModel):
    loginId: str = Field(..., min_length=3, description="로그인 ID")
    password: str = Field(..., min_length=1, description="비밀번호")
    name: str = Field(..., min_length=1, description="이름")
    role: Literal["MEMBER", "UNION_ADMIN"] = Field(default="MEMBER", description="권한")


class RefreshRequest(BaseModel):
    refreshToken: str = Field(..., description="리프레시 토큰")


# ── 응답 ──────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    userId: str
    name: str
    role: str
    unionId: str


class LoginResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int
    user: UserResponse


class RegisterResponse(BaseModel):
    userId: str


class RefreshResponse(BaseModel):
    accessToken: str
    refreshToken: str


class MeResponse(BaseModel):
    userId: str
    name: str
    role: str
    unionId: str
    permissions: list[str]
