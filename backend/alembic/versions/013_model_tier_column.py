"""Add model_tier column to workflow_steps for per-step model tiering.

Allows each workflow step to specify which Claude model to use:
- "opus" for complex reasoning steps
- "sonnet" for mechanical/template-following steps
- "none" for server-side-only steps (gates, invariant checks)

Revision ID: 013
Revises: 012
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_steps",
        sa.Column("model_tier", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_steps", "model_tier")
