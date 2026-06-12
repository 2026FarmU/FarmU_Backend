"""FastAPI 의존성 — DB 세션, 서비스 조립, 현재 사용자 추출."""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.adapter.external.jwt_service_impl import JwtServiceImpl
from src.auth.adapter.external.password_hasher_impl import BcryptPasswordHasher
from src.auth.adapter.external.redis_token_store import RedisTokenStore
from src.auth.adapter.persistence.repository.union_query_impl import UnionQueryImpl
from src.auth.adapter.persistence.repository.user_repository_impl import (
    UserRepositoryImpl,
)
from src.auth.application.port.required.jwt_service import TokenPayload
from src.auth.application.service.auth_service import AuthService
from src.infrastructure.cache.redis import get_redis
from src.infrastructure.database.session import get_db_session

_bearer = HTTPBearer(auto_error=False)


# ── DB 세션 ───────────────────────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# ── AuthService 조립 ──────────────────────────────────────────────

def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(
        user_repo=UserRepositoryImpl(session),
        union_query=UnionQueryImpl(session),
        password_hasher=BcryptPasswordHasher(),
        jwt_service=JwtServiceImpl(),
        token_store=RedisTokenStore(get_redis()),
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


# ── JWT 현재 사용자 ────────────────────────────────────────────────

def _extract_bearer(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ],
) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 없습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def get_current_token_payload(
    token: Annotated[str, Depends(_extract_bearer)],
    auth_service: AuthServiceDep,
) -> TokenPayload:
    """액세스 토큰 검증 + 블랙리스트 확인."""
    jwt_svc = JwtServiceImpl()
    payload = jwt_svc.decode_access_token(token)  # 만료·변조 시 DomainException

    if await auth_service._token_store.is_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그아웃된 토큰입니다.",
        )
    return payload


CurrentUser = Annotated[TokenPayload, Depends(get_current_token_payload)]
