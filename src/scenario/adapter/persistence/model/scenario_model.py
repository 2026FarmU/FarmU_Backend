from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class ScenarioOrmModel(Base):
    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    union_id: Mapped[str] = mapped_column(String(20), ForeignKey("unions.id"), index=True)
    member_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("members.id"), index=True)
    land_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("lands.id"), index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    base_crop: Mapped[str] = mapped_column(String(100), nullable=False)
    target_crop: Mapped[str] = mapped_column(String(100), nullable=False)
    apply_area_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    result: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
