from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class LandOrmModel(Base):
    __tablename__ = "lands"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    union_id: Mapped[str] = mapped_column(String(20), ForeignKey("unions.id"), index=True)
    member_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("members.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    pnu: Mapped[str] = mapped_column(String(19), nullable=False, unique=True)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    area: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    main_crop: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class LandSuitabilityOrmModel(Base):
    __tablename__ = "land_suitabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    land_id: Mapped[str] = mapped_column(String(20), ForeignKey("lands.id"), index=True)
    crop: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
