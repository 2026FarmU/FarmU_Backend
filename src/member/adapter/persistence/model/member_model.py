from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class MemberOrmModel(Base):
    __tablename__ = "members"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    union_id: Mapped[str] = mapped_column(String(20), ForeignKey("unions.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    group_name: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    main_crop: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class MemberPerformanceOrmModel(Base):
    __tablename__ = "member_performances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[str] = mapped_column(String(20), ForeignKey("members.id"), index=True)
    union_id: Mapped[str] = mapped_column(String(20), ForeignKey("unions.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    score_delta: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    production_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    shipping_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    revenue_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    production_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=35)
    shipping_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=35)
    revenue_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    production_percentile: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    shipping_percentile: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    revenue_percentile: Mapped[int] = mapped_column(Integer, nullable=False, default=50)


class MemberXaiFactorOrmModel(Base):
    __tablename__ = "member_xai_factors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[str] = mapped_column(String(20), ForeignKey("members.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    factor: Mapped[str] = mapped_column(String(100), nullable=False)
    contribution: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)


class MemberImprovementTaskOrmModel(Base):
    __tablename__ = "member_improvement_tasks"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    member_id: Mapped[str] = mapped_column(String(20), ForeignKey("members.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    expected_score_delta: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    expected_revenue_delta: Mapped[int] = mapped_column(Integer, nullable=False)
