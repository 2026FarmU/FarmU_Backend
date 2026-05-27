"""User ORM 모델."""
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class UserOrmModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    login_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    union_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    is_withdrawn: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} login_id={self.login_id}>"
