from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class UnionKpiOrmModel(Base):
    __tablename__ = "union_kpis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    union_id: Mapped[str] = mapped_column(String(20), ForeignKey("unions.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    avg_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    score_delta: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False)
    group_top: Mapped[int] = mapped_column(Integer, nullable=False)
    group_middle: Mapped[int] = mapped_column(Integer, nullable=False)
    group_needs_improvement: Mapped[int] = mapped_column(Integer, nullable=False)
    shipping_hit_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    avg_revenue: Mapped[int] = mapped_column(Integer, nullable=False)
    report_time_reduced: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class UnionTrendOrmModel(Base):
    __tablename__ = "union_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    union_id: Mapped[str] = mapped_column(String(20), ForeignKey("unions.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    metric: Mapped[str] = mapped_column(String(30), index=True)
    value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
