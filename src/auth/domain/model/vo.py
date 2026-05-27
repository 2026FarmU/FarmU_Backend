"""Auth 도메인 값 객체."""
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class UserId:
    value: str

    @classmethod
    def generate(cls) -> UserId:
        return cls(value=f"usr_{uuid.uuid4().hex[:4]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class LoginId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) < 3:
            raise ValueError("LoginId는 3자 이상이어야 합니다.")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class UnionId:
    value: str

    def __str__(self) -> str:
        return self.value
