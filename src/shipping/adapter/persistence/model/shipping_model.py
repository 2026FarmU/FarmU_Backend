from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class ShippingRecommendationOrmModel(Base):
    __tablename__ = "shipping_recommendations"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    union_id: Mapped[str] = mapped_column(String(20), ForeignKey("unions.id"), index=True)
    member_id: Mapped[str] = mapped_column(String(20), ForeignKey("members.id"), index=True)
    livestock_id: Mapped[str] = mapped_column(String(30), nullable=False)
    current_weight: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    target_weight: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    recommended_date: Mapped[date] = mapped_column(Date, nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    expected_revenue_min: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_revenue_expected: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_revenue_max: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_type: Mapped[str] = mapped_column(String(40), nullable=False)
    risk_score: Mapped[float] = mapped_column(Numeric(5, 3), nullable=False)
    risk_note: Mapped[str] = mapped_column(String(200), nullable=False)
    rationale: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True, default="PENDING")
    actual_ship_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    decision_memo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ShippingAccuracyOrmModel(Base):
    __tablename__ = "shipping_accuracy_monthly"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    union_id: Mapped[str] = mapped_column(String(20), ForeignKey("unions.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    total_recommendations: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted: Mapped[int] = mapped_column(Integer, nullable=False)
    hit_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
