"""Add IST synthesis and refresh workflow support.

Revision ID: 015
Revises: 014
Create Date: 2026-02-21

Adds:
- Workflow type expansion: IST_SYNTHESIS, IST_REFRESH
- New tables: ist_syntheses, ist_synthesis_sources, ist_synthesis_equities,
  ist_synthesis_dialectics, ist_screen_refreshes
- New columns on ist_screens: refresh_count, last_refreshed_at,
  active_workflow_run_id
- New column on ist_claims: source_refresh_id
- Idempotency keys for synthesis + refresh create endpoints
"""

from alembic import op
import sqlalchemy as sa


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


NEW_WORKFLOW_CHECK = (
    "workflow_type IN ('IST', 'HFRT', 'IST_SYNTHESIS', 'IST_REFRESH')"
)
OLD_WORKFLOW_CHECK = "workflow_type IN ('IST', 'HFRT')"


def upgrade() -> None:
    # Step 0: expand workflow type compatibility before any new workflow rows.
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_constraint("ck_workflow_type", type_="check")
        batch_op.create_check_constraint("ck_workflow_type", NEW_WORKFLOW_CHECK)

    op.create_table(
        "ist_syntheses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column(
            "workflow_run_id",
            sa.Integer(),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("overlap_matrix", sa.Text(), nullable=True),
        sa.Column("thesis_interactions", sa.Text(), nullable=True),
        sa.Column("tier_changes", sa.Text(), nullable=True),
        sa.Column("combined_brief", sa.Text(), nullable=True),
        sa.Column("combined_report", sa.Text(), nullable=True),
        sa.Column("report_metadata", sa.Text(), nullable=True),
        sa.Column("certification", sa.Text(), nullable=True),
        sa.Column("hfrt_handoff", sa.Text(), nullable=True),
        sa.Column("is_certified", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("certified_at", sa.DateTime(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'INGESTING', 'ANALYZING', 'DIALECTIC', "
            "'SYNTHESIZING', 'COMPLETED', 'FAILED')",
            name="ck_ist_synthesis_status",
        ),
    )
    op.create_index(
        "ix_ist_syntheses_status",
        "ist_syntheses",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_ist_syntheses_workflow",
        "ist_syntheses",
        ["workflow_run_id"],
    )
    op.create_index(
        "ix_ist_syntheses_idempotency_key",
        "ist_syntheses",
        ["idempotency_key"],
        unique=True,
    )

    op.create_table(
        "ist_synthesis_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "synthesis_id",
            sa.Integer(),
            sa.ForeignKey("ist_syntheses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "screen_id",
            sa.Integer(),
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("screen_name", sa.Text(), nullable=False),
        sa.Column("tier1_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tier2_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tier3_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("primary_theme", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_ist_synth_sources_synth",
        "ist_synthesis_sources",
        ["synthesis_id"],
    )
    op.create_index(
        "ix_ist_synth_sources_screen",
        "ist_synthesis_sources",
        ["screen_id"],
    )
    op.create_index(
        "ix_ist_synth_sources_unique",
        "ist_synthesis_sources",
        ["synthesis_id", "screen_id"],
        unique=True,
    )

    op.create_table(
        "ist_synthesis_equities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "synthesis_id",
            sa.Integer(),
            sa.ForeignKey("ist_syntheses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("original_tier", sa.Integer(), nullable=False),
        sa.Column("new_tier", sa.Integer(), nullable=False),
        sa.Column("tier_changed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tier_change_rationale", sa.Text(), nullable=True),
        sa.Column("source_screen_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_screen_ids", sa.Text(), nullable=False),
        sa.Column("combined_scarcity_score", sa.Text(), nullable=True),
        sa.Column("combined_thesis", sa.Text(), nullable=True),
        sa.Column("combined_catalyst", sa.Text(), nullable=True),
        sa.Column("conviction", sa.Text(), nullable=True),
        sa.Column("price_at_synthesis", sa.Float(), nullable=True),
        sa.Column("pe_ratio", sa.Float(), nullable=True),
        sa.Column("market_cap", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("original_tier IN (1, 2, 3)", name="ck_synth_eq_orig_tier"),
        sa.CheckConstraint("new_tier IN (1, 2, 3)", name="ck_synth_eq_new_tier"),
        sa.CheckConstraint(
            "conviction IN ('HIGH', 'MEDIUM', 'LOW')",
            name="ck_synth_eq_conviction",
        ),
    )
    op.create_index(
        "ix_ist_synth_eq_synth",
        "ist_synthesis_equities",
        ["synthesis_id", "new_tier"],
    )
    op.create_index(
        "ix_ist_synth_eq_ticker",
        "ist_synthesis_equities",
        ["ticker"],
    )
    op.create_index(
        "ix_ist_synth_eq_unique",
        "ist_synthesis_equities",
        ["synthesis_id", "ticker"],
        unique=True,
    )

    op.create_table(
        "ist_synthesis_dialectics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "synthesis_id",
            sa.Integer(),
            sa.ForeignKey("ist_syntheses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "side IN ('OPTIMIST', 'PESSIMIST', 'SYNTHESIS')",
            name="ck_synth_dialectic_side",
        ),
    )
    op.create_index(
        "ix_ist_synth_dialectic_unique",
        "ist_synthesis_dialectics",
        ["synthesis_id", "side"],
        unique=True,
    )

    op.create_table(
        "ist_screen_refreshes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "screen_id",
            sa.Integer(),
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workflow_run_id",
            sa.Integer(),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("refresh_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("content_type", sa.Text(), nullable=False, server_default="text"),
        sa.Column("delta_content", sa.Text(), nullable=False),
        sa.Column("impact_assessment", sa.Text(), nullable=True),
        sa.Column("steps_reexecuted", sa.Text(), nullable=True),
        sa.Column("new_claims_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_claims", sa.Text(), nullable=True),
        sa.Column("new_source_bias", sa.Text(), nullable=True),
        sa.Column("tier_changes", sa.Text(), nullable=True),
        sa.Column("tier_change_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("refresh_notes", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'EXTRACTING', 'ASSESSING', 'RE_ANALYZING', "
            "'RE_SYNTHESIZING', 'COMPLETED', 'FAILED')",
            name="ck_ist_refresh_status",
        ),
        sa.CheckConstraint(
            "content_type IN ('podcast_transcript', 'article', 'earnings_call', "
            "'research_note', 'text')",
            name="ck_ist_refresh_content_type",
        ),
    )
    op.create_index(
        "ix_ist_refreshes_screen",
        "ist_screen_refreshes",
        ["screen_id", "created_at"],
    )
    op.create_index(
        "ix_ist_refreshes_workflow",
        "ist_screen_refreshes",
        ["workflow_run_id"],
    )
    op.create_index(
        "ix_ist_refreshes_status",
        "ist_screen_refreshes",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_ist_refreshes_unique",
        "ist_screen_refreshes",
        ["screen_id", "refresh_number"],
        unique=True,
    )
    op.create_index(
        "ix_ist_refreshes_idempotency_key",
        "ist_screen_refreshes",
        ["idempotency_key"],
        unique=True,
    )

    with op.batch_alter_table("ist_screens") as batch_op:
        batch_op.add_column(
            sa.Column("refresh_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("last_refreshed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("active_workflow_run_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_ist_screens_active_workflow_run_id",
            "workflow_runs",
            ["active_workflow_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_ist_screens_active_workflow",
            ["active_workflow_run_id"],
            unique=False,
        )

    op.execute(
        sa.text(
            "UPDATE ist_screens SET active_workflow_run_id = workflow_run_id "
            "WHERE active_workflow_run_id IS NULL AND workflow_run_id IS NOT NULL"
        )
    )

    with op.batch_alter_table("ist_claims") as batch_op:
        batch_op.add_column(sa.Column("source_refresh_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_ist_claims_source_refresh_id",
            "ist_screen_refreshes",
            ["source_refresh_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_ist_claims_refresh",
            ["screen_id", "source_refresh_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("ist_claims") as batch_op:
        batch_op.drop_index("ix_ist_claims_refresh")
        batch_op.drop_constraint("fk_ist_claims_source_refresh_id", type_="foreignkey")
        batch_op.drop_column("source_refresh_id")

    with op.batch_alter_table("ist_screens") as batch_op:
        batch_op.drop_index("ix_ist_screens_active_workflow")
        batch_op.drop_constraint("fk_ist_screens_active_workflow_run_id", type_="foreignkey")
        batch_op.drop_column("active_workflow_run_id")
        batch_op.drop_column("last_refreshed_at")
        batch_op.drop_column("refresh_count")

    op.drop_index("ix_ist_refreshes_idempotency_key", table_name="ist_screen_refreshes")
    op.drop_index("ix_ist_refreshes_unique", table_name="ist_screen_refreshes")
    op.drop_index("ix_ist_refreshes_status", table_name="ist_screen_refreshes")
    op.drop_index("ix_ist_refreshes_workflow", table_name="ist_screen_refreshes")
    op.drop_index("ix_ist_refreshes_screen", table_name="ist_screen_refreshes")
    op.drop_table("ist_screen_refreshes")

    op.drop_index("ix_ist_synth_dialectic_unique", table_name="ist_synthesis_dialectics")
    op.drop_table("ist_synthesis_dialectics")

    op.drop_index("ix_ist_synth_eq_unique", table_name="ist_synthesis_equities")
    op.drop_index("ix_ist_synth_eq_ticker", table_name="ist_synthesis_equities")
    op.drop_index("ix_ist_synth_eq_synth", table_name="ist_synthesis_equities")
    op.drop_table("ist_synthesis_equities")

    op.drop_index("ix_ist_synth_sources_unique", table_name="ist_synthesis_sources")
    op.drop_index("ix_ist_synth_sources_screen", table_name="ist_synthesis_sources")
    op.drop_index("ix_ist_synth_sources_synth", table_name="ist_synthesis_sources")
    op.drop_table("ist_synthesis_sources")

    op.drop_index("ix_ist_syntheses_idempotency_key", table_name="ist_syntheses")
    op.drop_index("ix_ist_syntheses_workflow", table_name="ist_syntheses")
    op.drop_index("ix_ist_syntheses_status", table_name="ist_syntheses")
    op.drop_table("ist_syntheses")

    bind = op.get_bind()
    new_type_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM workflow_runs "
            "WHERE workflow_type IN ('IST_SYNTHESIS', 'IST_REFRESH')"
        )
    ).scalar()
    if new_type_count and int(new_type_count) > 0:
        raise RuntimeError(
            "Cannot downgrade: workflow_runs contains IST_SYNTHESIS/IST_REFRESH rows"
        )

    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_constraint("ck_workflow_type", type_="check")
        batch_op.create_check_constraint("ck_workflow_type", OLD_WORKFLOW_CHECK)
