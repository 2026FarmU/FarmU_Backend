"""공통 도메인 예외 클래스."""


class DomainException(Exception):
    """도메인 레이어 기본 예외."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class EntityNotFoundException(DomainException):
    """엔티티 미조회 예외."""

    def __init__(self, entity: str, entity_id: str) -> None:
        super().__init__(
            message=f"{entity}을(를) 찾을 수 없습니다. id={entity_id}",
            code=f"{entity.upper()}_NOT_FOUND",
        )


class BusinessRuleViolationException(DomainException):
    """비즈니스 규칙 위반 예외."""


class ConflictException(DomainException):
    """중복 또는 충돌 예외."""


class InsufficientDataException(DomainException):
    """데이터 부족 예외."""

    def __init__(self, detail: str = "분석에 필요한 데이터가 부족합니다.") -> None:
        super().__init__(message=detail, code="INSUFFICIENT_DATA")
