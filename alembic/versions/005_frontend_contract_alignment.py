"""align scenario, report, mentoring and upload contracts

Revision ID: 005
Revises: 004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scenarios", sa.Column("land_id", sa.String(length=20), nullable=True))
    op.create_index("ix_scenarios_land_id", "scenarios", ["land_id"])
    op.create_foreign_key(
        "fk_scenarios_land_id_lands", "scenarios", "lands", ["land_id"], ["id"]
    )

    op.add_column(
        "reports", sa.Column("format", sa.String(length=10), nullable=False, server_default="PDF")
    )
    op.add_column(
        "reports",
        sa.Column("sections", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column("mentoring_matches", sa.Column("goal", sa.Text(), nullable=True))

    op.create_table(
        "mentoring_tasks",
        sa.Column("id", sa.String(length=20), primary_key=True),
        sa.Column(
            "match_id",
            sa.String(length=20),
            sa.ForeignKey("mentoring_matches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.String(length=10), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mentoring_tasks_match_id", "mentoring_tasks", ["match_id"])


def downgrade() -> None:
    op.drop_index("ix_mentoring_tasks_match_id", table_name="mentoring_tasks")
    op.drop_table("mentoring_tasks")
    op.drop_column("mentoring_matches", "goal")
    op.drop_column("reports", "sections")
    op.drop_column("reports", "format")
    op.drop_constraint("fk_scenarios_land_id_lands", "scenarios", type_="foreignkey")
    op.drop_index("ix_scenarios_land_id", table_name="scenarios")
    op.drop_column("scenarios", "land_id")
