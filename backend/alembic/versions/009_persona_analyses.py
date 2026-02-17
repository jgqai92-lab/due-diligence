"""Create persona_analyses table for Persona Overlay.

Revision ID: 009
Revises: 008
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "persona_analyses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("persona_name", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("input_context", sa.Text(), nullable=False),
        sa.Column("analysis_result", sa.Text(), nullable=True),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column("model_used", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(datetime('now'))"),
        ),
    )

    # Indexes
    op.create_index(
        "ix_persona_analyses_persona_name",
        "persona_analyses",
        ["persona_name"],
    )
    op.create_index(
        "ix_persona_target",
        "persona_analyses",
        ["target_type", "target_id"],
    )
    op.create_index(
        "ix_persona_name_created",
        "persona_analyses",
        ["persona_name", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_persona_name_created", table_name="persona_analyses")
    op.drop_index("ix_persona_target", table_name="persona_analyses")
    op.drop_index("ix_persona_analyses_persona_name", table_name="persona_analyses")
    op.drop_table("persona_analyses")
