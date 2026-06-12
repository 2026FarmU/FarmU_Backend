from src.shared.domain.exception import ConflictException, EntityNotFoundException


class RecommendationNotFoundException(EntityNotFoundException):
    def __init__(self, recommendation_id: str) -> None:
        super().__init__("Recommendation", recommendation_id)
        self.code = "RECOMMENDATION_NOT_FOUND"


class RecommendationAlreadyDecidedException(ConflictException):
    def __init__(self, recommendation_id: str) -> None:
        super().__init__(
            message=f"이미 결정된 추천입니다: {recommendation_id}",
            code="RECOMMENDATION_ALREADY_DECIDED",
        )
