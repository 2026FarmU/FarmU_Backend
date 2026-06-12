from abc import ABC, abstractmethod


class UnionQueryPort(ABC):
    """조합 코드 → ID 조회 (auth BC outbound port)."""

    @abstractmethod
    async def find_id_by_code(self, union_code: str) -> str | None: ...
