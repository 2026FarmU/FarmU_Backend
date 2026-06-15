from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class ReportOrmModel(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    union_id: Mapped[str] = mapped_column(String(20), ForeignKey("unions.id"), index=True)
    member_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("members.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    report_type: Mapped[str] = mapped_column(String(30), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False, default="PDF")
    sections: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="READY")
    file_key: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
