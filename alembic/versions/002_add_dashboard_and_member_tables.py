"""add dashboard and member tables

Revision ID: 002
Revises: 001
Create Date: 2026-06-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: str | None = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "members",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("group_name", sa.String(30), nullable=False),
        sa.Column("main_crop", sa.String(100), nullable=False),
        sa.Column("region", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_members_union_id", "members", ["union_id"])
    op.create_index("ix_members_group_name", "members", ["group_name"])

    op.create_table(
        "member_performances",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("member_id", sa.String(20), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("score_delta", sa.Numeric(5, 2), nullable=False),
        sa.Column("production_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("shipping_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("revenue_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("production_weight", sa.Integer, nullable=False, server_default="35"),
        sa.Column("shipping_weight", sa.Integer, nullable=False, server_default="35"),
        sa.Column("revenue_weight", sa.Integer, nullable=False, server_default="30"),
        sa.Column("production_percentile", sa.Integer, nullable=False, server_default="50"),
        sa.Column("shipping_percentile", sa.Integer, nullable=False, server_default="50"),
        sa.Column("revenue_percentile", sa.Integer, nullable=False, server_default="50"),
    )
    op.create_index("ix_member_performances_member_id", "member_performances", ["member_id"])
    op.create_index("ix_member_performances_union_id", "member_performances", ["union_id"])
    op.create_index("ix_member_performances_period", "member_performances", ["period"])

    op.create_table(
        "member_xai_factors",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("member_id", sa.String(20), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("factor", sa.String(100), nullable=False),
        sa.Column("contribution", sa.Numeric(6, 2), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
    )
    op.create_index("ix_member_xai_factors_member_id", "member_xai_factors", ["member_id"])
    op.create_index("ix_member_xai_factors_period", "member_xai_factors", ["period"])

    op.create_table(
        "member_improvement_tasks",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("member_id", sa.String(20), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("expected_score_delta", sa.Numeric(6, 2), nullable=False),
        sa.Column("expected_revenue_delta", sa.Integer, nullable=False),
    )
    op.create_index("ix_member_improvement_tasks_member_id", "member_improvement_tasks", ["member_id"])
    op.create_index("ix_member_improvement_tasks_period", "member_improvement_tasks", ["period"])

    op.create_table(
        "union_kpis",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("avg_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("score_delta", sa.Numeric(5, 2), nullable=False),
        sa.Column("member_count", sa.Integer, nullable=False),
        sa.Column("group_top", sa.Integer, nullable=False),
        sa.Column("group_middle", sa.Integer, nullable=False),
        sa.Column("group_needs_improvement", sa.Integer, nullable=False),
        sa.Column("shipping_hit_rate", sa.Numeric(5, 4), nullable=False),
        sa.Column("avg_revenue", sa.Integer, nullable=False),
        sa.Column("report_time_reduced", sa.Numeric(5, 4), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_union_kpis_union_id", "union_kpis", ["union_id"])
    op.create_index("ix_union_kpis_period", "union_kpis", ["period"])

    op.create_table(
        "union_trends",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("metric", sa.String(30), nullable=False),
        sa.Column("value", sa.Numeric(12, 4), nullable=False),
    )
    op.create_index("ix_union_trends_union_id", "union_trends", ["union_id"])
    op.create_index("ix_union_trends_period", "union_trends", ["period"])
    op.create_index("ix_union_trends_metric", "union_trends", ["metric"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), nullable=False),
        sa.Column("level", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("affected_members", sa.Integer, nullable=False),
        sa.Column("action_url", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_alerts_union_id", "alerts", ["union_id"])
    op.create_index("ix_alerts_level", "alerts", ["level"])
    op.create_index("ix_alerts_status", "alerts", ["status"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("union_trends")
    op.drop_table("union_kpis")
    op.drop_table("member_improvement_tasks")
    op.drop_table("member_xai_factors")
    op.drop_table("member_performances")
    op.drop_table("members")
