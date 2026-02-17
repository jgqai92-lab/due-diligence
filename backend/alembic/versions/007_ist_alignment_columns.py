"""007 IST alignment columns

Revision ID: 007_ist_alignment_columns
Revises: 006_hfrt_tables
Create Date: 2026-02-12

Adds columns for IST/HFRT alignment (Mega-Phase D, Wave D1):
    ist_bottlenecks.pillar_name  -- Maps bottleneck to report pillar for Gate 3
    ist_screens.certification    -- JSON certification gate results
    ist_screens.hfrt_handoff     -- JSON Tier 1 candidates for HFRT bridge
"""

from alembic import op
import sqlalchemy as sa


revision = "007_ist_alignment_columns"
down_revision = "006_hfrt_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ist_bottlenecks",
        sa.Column("pillar_name", sa.Text, nullable=True),
    )
    op.add_column(
        "ist_screens",
        sa.Column("certification", sa.Text, nullable=True),
    )
    op.add_column(
        "ist_screens",
        sa.Column("hfrt_handoff", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ist_screens", "hfrt_handoff")
    op.drop_column("ist_screens", "certification")
    op.drop_column("ist_bottlenecks", "pillar_name")
