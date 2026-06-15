"""Auth 도메인 예외."""
from src.shared.domain.exception import ConflictException, DomainException


class InvalidCredentialsException(DomainException):
    def __init__(self) -> None:
        super().__init__(
            message="아이디 또는 비밀번호가 일치하지 않습니다.",
            code="INVALID_CREDENTIALS",
        )


class WithdrawnUserException(DomainException):
    def __init__(self) -> None:
        super().__init__(message="탈퇴한 회원입니다.", code="WITHDRAWN_USER")


class DuplicateLoginIdException(ConflictException):
    def __init__(self, login_id: str) -> None:
        super().__init__(
            message=f"이미 사용 중인 로그인 ID입니다: {login_id}",
            code="DUPLICATE_LOGIN_ID",
        )


class UnionNotFoundException(DomainException):
    def __init__(self, union_code: str) -> None:
        super().__init__(
            message=f"조합을 찾을 수 없습니다. code={union_code}",
            code="UNION_NOT_FOUND",
        )


class InvalidPasswordException(DomainException):
    def __init__(self) -> None:
        super().__init__(
            message="기존 비밀번호가 일치하지 않습니다.",
            code="INVALID_PASSWORD",
        )
