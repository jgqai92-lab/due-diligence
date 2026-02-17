"""Add depends_on column to workflow_steps for dependency-aware parallel execution.

Revision ID: 011
Revises: 010
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_steps",
        sa.Column("depends_on", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_steps", "depends_on")
