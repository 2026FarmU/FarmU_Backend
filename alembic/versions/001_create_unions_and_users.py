"""create unions and users tables

Revision ID: 001
Revises:
Create Date: 2026-05-27
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── unions ────────────────────────────────────────────────────
    op.create_table(
        "unions",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
    )
    op.create_index("ix_unions_code", "unions", ["code"], unique=True)

    # ── users ─────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("login_id", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("union_id", sa.String(20), sa.ForeignKey("unions.id"), nullable=False),
        sa.Column("is_withdrawn", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_users_login_id", "users", ["login_id"])
    op.create_index("ix_users_union_id", "users", ["union_id"])
    # (login_id, union_id) 복합 유니크 — 조합마다 동일 ID 허용
    op.create_index(
        "uq_users_login_id_union_id",
        "users",
        ["login_id", "union_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("users")
    op.drop_index("ix_unions_code", table_name="unions")
    op.drop_table("unions")
