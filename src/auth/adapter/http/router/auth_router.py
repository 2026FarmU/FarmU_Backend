"""Auth API 라우터."""
from fastapi import APIRouter, Request, status
from fastapi.responses import ORJSONResponse

from src.auth.adapter.http.router.deps import AuthServiceDep, CurrentUser
from src.auth.adapter.http.schema.auth_schema import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    RefreshRequest,
    RefreshResponse,
    UserResponse,
)
from src.auth.application.dto.commands import LoginCommand, RefreshTokenCommand

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", status_code=status.HTTP_200_OK, summary="로그인")
async def login(body: LoginRequest, svc: AuthServiceDep) -> ORJSONResponse:
    result = await svc.login(
        LoginCommand(
            login_id=body.loginId,
            password=body.password,
            union_code=body.unionCode,
        )
    )
    return ORJSONResponse(
        {
            "data": LoginResponse(
                accessToken=result.access_token,
                refreshToken=result.refresh_token,
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


@router.post("/refresh", status_code=status.HTTP_200_OK, summary="토큰 재발급")
async def refresh(body: RefreshRequest, svc: AuthServiceDep) -> ORJSONResponse:
    result = await svc.refresh(RefreshTokenCommand(refresh_token=body.refreshToken))
    return ORJSONResponse(
        {
            "data": RefreshResponse(
                accessToken=result.access_token,
                refreshToken=result.refresh_token,
            ).model_dump()
        }
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="로그아웃")
async def logout(request: Request, current: CurrentUser, svc: AuthServiceDep) -> None:
    raw_token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    await svc.logout(user_id=current.user_id, access_token=raw_token)


@router.get("/me", status_code=status.HTTP_200_OK, summary="내 정보 조회")
async def get_me(current: CurrentUser, svc: AuthServiceDep) -> ORJSONResponse:
    info = await svc.get_me(current.user_id)
    return ORJSONResponse(
        {
            "data": MeResponse(
                userId=info.user_id,
                name=info.name,
                role=info.role.value,
                unionId=info.union_id,
                permissions=info.permissions,
            ).model_dump()
        }
    )
