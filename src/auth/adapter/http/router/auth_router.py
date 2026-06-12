"""Auth API 라우터."""
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import ORJSONResponse

from src.auth.adapter.http.router.deps import AuthServiceDep, CurrentUser
from src.auth.adapter.http.schema.auth_schema import (
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
    RefreshRequest,
    RefreshResponse,
    UserResponse,
)
from src.auth.application.dto.commands import (
    CreateUserCommand,
    LoginCommand,
    RefreshTokenCommand,
    RegisterCommand,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="회원가입")
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


@router.post("/users", status_code=status.HTTP_201_CREATED, summary="사용자 생성(관리자)")
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
