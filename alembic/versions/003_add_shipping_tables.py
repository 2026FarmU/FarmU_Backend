"""add shipping tables

Revision ID: 003
Revises: 002
Create Date: 2026-06-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: str | None = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shipping_recommendations",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), nullable=False),
        sa.Column("member_id", sa.String(20), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("livestock_id", sa.String(30), nullable=False),
        sa.Column("current_weight", sa.Numeric(8, 2), nullable=False),
        sa.Column("target_weight", sa.Numeric(8, 2), nullable=False),
        sa.Column("recommended_date", sa.Date, nullable=False),
        sa.Column("recommended_action", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("expected_revenue_min", sa.Integer, nullable=False),
        sa.Column("expected_revenue_expected", sa.Integer, nullable=False),
        sa.Column("expected_revenue_max", sa.Integer, nullable=False),
        sa.Column("risk_type", sa.String(40), nullable=False),
        sa.Column("risk_score", sa.Numeric(5, 3), nullable=False),
        sa.Column("risk_note", sa.String(200), nullable=False),
        sa.Column("rationale", sa.String(300), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("actual_ship_date", sa.Date, nullable=True),
        sa.Column("decision_memo", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_shipping_recommendations_union_id", "shipping_recommendations", ["union_id"])
    op.create_index("ix_shipping_recommendations_member_id", "shipping_recommendations", ["member_id"])
    op.create_index("ix_shipping_recommendations_status", "shipping_recommendations", ["status"])

    op.create_table(
        "shipping_accuracy_monthly",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("total_recommendations", sa.Integer, nullable=False),
        sa.Column("accepted", sa.Integer, nullable=False),
        sa.Column("hit_rate", sa.Numeric(5, 4), nullable=False),
    )
    op.create_index("ix_shipping_accuracy_monthly_union_id", "shipping_accuracy_monthly", ["union_id"])
    op.create_index("ix_shipping_accuracy_monthly_period", "shipping_accuracy_monthly", ["period"])


def downgrade() -> None:
    op.drop_table("shipping_accuracy_monthly")
    op.drop_table("shipping_recommendations")
