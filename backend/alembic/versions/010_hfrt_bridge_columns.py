"""Add source and ist_screen_id columns to hfrt_projects for IST bridge tracking.

Revision ID: 010
Revises: 009
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hfrt_projects",
        sa.Column("source", sa.Text(), nullable=True),
    )
    op.add_column(
        "hfrt_projects",
        sa.Column("ist_screen_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hfrt_projects", "ist_screen_id")
    op.drop_column("hfrt_projects", "source")
