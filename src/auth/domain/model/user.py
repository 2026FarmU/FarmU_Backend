"""User 애그리게이트 루트."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.auth.domain.model.role import Role
from src.auth.domain.model.vo import LoginId, UnionId, UserId


@dataclass
class User:
    id: UserId
    login_id: LoginId
    hashed_password: str
    name: str
    role: Role
    union_id: UnionId
    is_withdrawn: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # ── 비즈니스 규칙 ──────────────────────────────────────────────

    def verify_not_withdrawn(self) -> None:
        from src.auth.domain.exception import WithdrawnUserException

        if self.is_withdrawn:
            raise WithdrawnUserException()

    @property
    def permissions(self) -> list[str]:
        """역할별 기본 권한 목록."""
        base = ["dashboard.read"]
        if self.role == Role.UNION_ADMIN:
            return base + ["member.write", "report.export", "weight.write", "data.upload"]
        if self.role == Role.CONSULTANT:
            return base + ["member.read", "report.read", "mentoring.manage"]
        # MEMBER
        return base + ["member.read.self", "scenario.read", "mentoring.request"]
