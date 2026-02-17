"""Add auto_advance column to workflow_runs for automatic phase progression.

Revision ID: 012
Revises: 011
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column(
            "auto_advance",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("workflow_runs", "auto_advance")
