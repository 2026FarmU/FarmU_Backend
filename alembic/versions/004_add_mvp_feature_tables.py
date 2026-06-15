"""add MVP feature tables and normalize member groups

Revision ID: 004
Revises: 003
Create Date: 2026-06-12
"""

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE members SET group_name='MID' WHERE group_name='MIDDLE'")
    op.execute("UPDATE members SET group_name='LOW' WHERE group_name='NEEDS_IMPROVEMENT'")

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(20), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("phone", sa.String(30)),
        sa.Column("email", sa.String(200)),
        sa.Column("bio", sa.String(500)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("banner_url", sa.String(500)),
    )
    op.create_table(
        "user_member_links",
        sa.Column("user_id", sa.String(20), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column(
            "member_id", sa.String(20), sa.ForeignKey("members.id"), nullable=False, unique=True
        ),
    )
    op.create_table(
        "notification_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.String(20), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("key", sa.String(50), nullable=False),
        sa.Column("channels", sa.String(100), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_notification_settings_user_id", "notification_settings", ["user_id"])
    op.create_table(
        "union_weights",
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), primary_key=True),
        sa.Column("production", sa.Integer, nullable=False, server_default="35"),
        sa.Column("shipping", sa.Integer, nullable=False, server_default="35"),
        sa.Column("revenue", sa.Integer, nullable=False, server_default="30"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_table(
        "lands",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), nullable=False),
        sa.Column("member_id", sa.String(20), sa.ForeignKey("members.id")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("pnu", sa.String(19), nullable=False, unique=True),
        sa.Column("address", sa.String(300), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("area", sa.Numeric(12, 2), nullable=False),
        sa.Column("main_crop", sa.String(100)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_lands_union_id", "lands", ["union_id"])
    op.create_index("ix_lands_member_id", "lands", ["member_id"])
    op.create_table(
        "land_suitabilities",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("land_id", sa.String(20), sa.ForeignKey("lands.id"), nullable=False),
        sa.Column("crop", sa.String(100), nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("reasons", sa.JSON, nullable=False),
    )
    op.create_index("ix_land_suitabilities_land_id", "land_suitabilities", ["land_id"])

    op.create_table(
        "scenarios",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), nullable=False),
        sa.Column("member_id", sa.String(20), sa.ForeignKey("members.id")),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("base_crop", sa.String(100), nullable=False),
        sa.Column("target_crop", sa.String(100), nullable=False),
        sa.Column("apply_area_ratio", sa.Float, nullable=False),
        sa.Column("result", sa.JSON, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_scenarios_union_id", "scenarios", ["union_id"])
    op.create_table(
        "mentoring_matches",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), nullable=False),
        sa.Column("mentee_id", sa.String(20), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("mentor_id", sa.String(20), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("help_areas", sa.JSON, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_mentoring_matches_union_id", "mentoring_matches", ["union_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), nullable=False),
        sa.Column("member_id", sa.String(20), sa.ForeignKey("members.id")),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("report_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("file_key", sa.String(300), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_reports_union_id", "reports", ["union_id"])
    op.create_index("ix_reports_period", "reports", ["period"])
    op.create_table(
        "data_uploads",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), nullable=False),
        sa.Column("uploaded_by", sa.String(20), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("validation", sa.JSON, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_data_uploads_union_id", "data_uploads", ["union_id"])
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("user_id", sa.String(20), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("level", sa.String(10), nullable=False),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("action_url", sa.String(255)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])


def downgrade() -> None:
    for table in [
        "notifications",
        "data_uploads",
        "reports",
        "mentoring_matches",
        "scenarios",
        "land_suitabilities",
        "lands",
        "union_weights",
        "notification_settings",
        "user_member_links",
        "user_profiles",
    ]:
        op.drop_table(table)
    op.execute("UPDATE members SET group_name='MIDDLE' WHERE group_name='MID'")
    op.execute("UPDATE members SET group_name='NEEDS_IMPROVEMENT' WHERE group_name='LOW'")
