from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class UserProfileOrmModel(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(20), ForeignKey("users.id"), primary_key=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(200))
    bio: Mapped[str | None] = mapped_column(String(500))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    banner_url: Mapped[str | None] = mapped_column(String(500))


class UserMemberLinkOrmModel(Base):
    __tablename__ = "user_member_links"

    user_id: Mapped[str] = mapped_column(String(20), ForeignKey("users.id"), primary_key=True)
    member_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("members.id"), unique=True, nullable=False
    )


class NotificationSettingOrmModel(Base):
    __tablename__ = "notification_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(20), ForeignKey("users.id"), index=True)
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    channels: Mapped[str] = mapped_column(String(100), nullable=False, default="PUSH")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class UnionWeightOrmModel(Base):
    __tablename__ = "union_weights"

    union_id: Mapped[str] = mapped_column(String(20), ForeignKey("unions.id"), primary_key=True)
    production: Mapped[int] = mapped_column(Integer, nullable=False, default=35)
    shipping: Mapped[int] = mapped_column(Integer, nullable=False, default=35)
    revenue: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
