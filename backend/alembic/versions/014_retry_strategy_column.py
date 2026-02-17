"""Add retry_strategy column to workflow_steps for smart retry behavior.

Allows gate steps to specify how retries should behave:
- NULL or "self": only reset the failed step itself (default, backward compat)
- "with_parent": also reset the step's depends_on parents so they
  regenerate fresh data before the gate re-checks

Revision ID: 014
Revises: 013
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_steps",
        sa.Column("retry_strategy", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_steps", "retry_strategy")
