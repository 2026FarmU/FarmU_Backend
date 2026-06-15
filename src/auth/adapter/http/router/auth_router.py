"""Auth API 라우터."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.account_models import UserMemberLinkOrmModel
from src.auth.adapter.http.router.deps import AuthServiceDep, CurrentUser
from src.infrastructure.database.session import get_db_session
from src.auth.adapter.http.schema.auth_schema import (
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from src.auth.application.dto.commands import (
    CreateUserCommand,
    LoginCommand,
    RefreshTokenCommand,
    RegisterCommand,
)
from src.main.config import get_settings
from src.main.response_schema import DataResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

REFRESH_COOKIE_NAME = "refresh_token"


def _set_refresh_cookie(response: ORJSONResponse, refresh_token: str) -> None:
    settings = get_settings()
    is_development = settings.environment == "development"
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=30 * 24 * 3600,
        httponly=True,
        secure=not is_development,
        samesite="lax" if is_development else "none",
        path="/api/v1/auth",
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
    response_model=DataResponse[RegisterResponse],
)
async def register(
    body: RegisterRequest,
    svc: AuthServiceDep,
) -> ORJSONResponse:
    result = await svc.register(
        RegisterCommand(
            login_id=body.loginId,
            password=body.password,
            name=body.name,
            union_code=body.unionCode,
        )
    )
    return ORJSONResponse({"data": RegisterResponse(userId=result.user_id).model_dump()})


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    summary="사용자 생성(관리자)",
    response_model=DataResponse[RegisterResponse],
)
async def create_user(
    body: CreateUserRequest,
    svc: AuthServiceDep,
    current: CurrentUser,
) -> ORJSONResponse:
    if current.role != "UNION_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNION_ADMIN 권한이 필요합니다.",
        )

    result = await svc.create_user(
        CreateUserCommand(
            login_id=body.loginId,
            password=body.password,
            name=body.name,
            union_id=current.union_id,
            role=body.role,
        )
    )
    return ORJSONResponse({"data": RegisterResponse(userId=result.user_id).model_dump()})


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="로그인",
    response_model=DataResponse[LoginResponse],
)
async def login(body: LoginRequest, svc: AuthServiceDep) -> ORJSONResponse:
    result = await svc.login(
        LoginCommand(
            login_id=body.loginId,
            password=body.password,
            union_code=body.unionCode,
        )
    )
    response = ORJSONResponse(
        {
            "data": LoginResponse(
                accessToken=result.access_token,
                expiresIn=result.expires_in,
                user=UserResponse(
                    userId=result.user.user_id,
                    name=result.user.name,
                    role=result.user.role.value,
                    unionId=result.user.union_id,
                ),
            ).model_dump()
        }
    )
    _set_refresh_cookie(response, result.refresh_token)
    return response


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    summary="토큰 재발급",
    response_model=DataResponse[RefreshResponse],
)
async def refresh(
    request: Request,
    svc: AuthServiceDep,
    body: RefreshRequest | None = None,
) -> ORJSONResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token is None and body is not None:
        refresh_token = body.refreshToken
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="리프레시 토큰이 없습니다.",
        )

    result = await svc.refresh(RefreshTokenCommand(refresh_token=refresh_token))
    response = ORJSONResponse(
        {
            "data": RefreshResponse(
                accessToken=result.access_token,
            ).model_dump()
        }
    )
    _set_refresh_cookie(response, result.refresh_token)
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="로그아웃")
async def logout(
    request: Request,
    current: CurrentUser,
    svc: AuthServiceDep,
) -> Response:
    raw_token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    await svc.logout(user_id=current.user_id, access_token=raw_token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/v1/auth")
    return response


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="내 정보 조회",
    response_model=DataResponse[MeResponse],
)
async def get_me(current: CurrentUser, svc: AuthServiceDep, session: DbSession) -> ORJSONResponse:
    info = await svc.get_me(current.user_id)
    link = await session.get(UserMemberLinkOrmModel, current.user_id)
    return ORJSONResponse(
        {
            "data": MeResponse(
                userId=info.user_id,
                name=info.name,
                role=info.role.value,
                unionId=info.union_id,
                permissions=info.permissions,
                memberId=link.member_id if link else None,
            ).model_dump()
        }
    )
