"""Add invariant_results column to hfrt_projects.

Revision ID: 008
Revises: 007
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "008"
down_revision = "007_ist_alignment_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hfrt_projects",
        sa.Column("invariant_results", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hfrt_projects", "invariant_results")
