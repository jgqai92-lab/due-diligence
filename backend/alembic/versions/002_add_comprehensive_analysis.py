"""002 add comprehensive analysis columns

Revision ID: 002_comprehensive
Revises: 001_initial
Create Date: 2026-01-31

Adds comprehensive_analysis (Text) and sector_category (String) columns
to the analysis_reports table for the general-purpose hedge fund screener.
"""

from alembic import op
import sqlalchemy as sa


revision = "002_comprehensive"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("analysis_reports") as batch_op:
        batch_op.add_column(sa.Column("comprehensive_analysis", sa.Text, nullable=True))
        batch_op.add_column(sa.Column("sector_category", sa.String, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("analysis_reports") as batch_op:
        batch_op.drop_column("sector_category")
        batch_op.drop_column("comprehensive_analysis")
