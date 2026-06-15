from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class DataUploadOrmModel(Base):
    __tablename__ = "data_uploads"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    union_id: Mapped[str] = mapped_column(String(20), ForeignKey("unions.id"), index=True)
    uploaded_by: Mapped[str] = mapped_column(String(20), ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    validation: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
