from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class MentoringMatchOrmModel(Base):
    __tablename__ = "mentoring_matches"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    union_id: Mapped[str] = mapped_column(String(20), ForeignKey("unions.id"), index=True)
    mentee_id: Mapped[str] = mapped_column(String(20), ForeignKey("members.id"), index=True)
    mentor_id: Mapped[str] = mapped_column(String(20), ForeignKey("members.id"), index=True)
    help_areas: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class MentoringTaskOrmModel(Base):
    __tablename__ = "mentoring_tasks"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    match_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("mentoring_matches.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
