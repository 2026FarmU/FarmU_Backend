from src.shared.domain.exception import DomainException


class PerformanceNotCalculatedException(DomainException):
    def __init__(self, period: str) -> None:
        super().__init__(
            message=f"해당 기간 성과가 계산되지 않았습니다: {period}",
            code="PERFORMANCE_NOT_CALCULATED",
        )
