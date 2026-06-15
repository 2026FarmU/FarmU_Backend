"""JWT 서비스 python-jose 구현체."""
from datetime import UTC, datetime, timedelta

from jose import ExpiredSignatureError, JWTError, jwt

from src.auth.application.port.required.jwt_service import JwtService, TokenPayload
from src.main.config import get_settings
from src.shared.domain.exception import DomainException

settings = get_settings()

_ACCESS = "access"
_REFRESH = "refresh"


def _make_expired_exc(token_type: str) -> DomainException:
    if token_type == _REFRESH:
        return DomainException(
            message="만료된 리프레시 토큰입니다.", code="EXPIRED_REFRESH_TOKEN"
        )
    return DomainException(
        message="만료된 액세스 토큰입니다.", code="EXPIRED_ACCESS_TOKEN"
    )


def _make_invalid_exc(token_type: str) -> DomainException:
    if token_type == _REFRESH:
        return DomainException(
            message="유효하지 않은 리프레시 토큰입니다.", code="INVALID_REFRESH_TOKEN"
        )
    return DomainException(
        message="유효하지 않은 액세스 토큰입니다.", code="INVALID_ACCESS_TOKEN"
    )


class JwtServiceImpl(JwtService):
    def _encode(self, payload: TokenPayload, token_type: str, delta: timedelta) -> str:
        now = datetime.now(UTC)
        data = {
            "sub": payload.user_id,
            "role": payload.role,
            "union_id": payload.union_id,
            "type": token_type,
            "iat": now,
            "exp": now + delta,
        }
        return str(
            jwt.encode(data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        )

    def _decode(self, token: str, token_type: str) -> TokenPayload:
        try:
            claims = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
        except ExpiredSignatureError:
            raise _make_expired_exc(token_type) from None
        except JWTError:
            raise _make_invalid_exc(token_type) from None

        if claims.get("type") != token_type:
            raise _make_invalid_exc(token_type)

        return TokenPayload(
            user_id=claims["sub"],
            role=claims["role"],
            union_id=claims["union_id"],
        )

    def create_access_token(self, payload: TokenPayload) -> tuple[str, int]:
        expires_minutes = settings.jwt_access_token_expire_minutes
        token = self._encode(payload, _ACCESS, timedelta(minutes=expires_minutes))
        return token, expires_minutes * 60

    def create_refresh_token(self, payload: TokenPayload) -> str:
        return self._encode(
            payload,
            _REFRESH,
            timedelta(days=settings.jwt_refresh_token_expire_days),
        )

    def decode_access_token(self, token: str) -> TokenPayload:
        return self._decode(token, _ACCESS)

    def decode_refresh_token(self, token: str) -> TokenPayload:
        return self._decode(token, _REFRESH)
