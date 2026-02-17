"""005 ist tables

Revision ID: 005_ist_tables
Revises: 004_workflow_engine
Create Date: 2026-02-07

Creates all 13 IST (Investment Screening Team) tables for the
IST screening pipeline (Wave A2).

Tables created in FK dependency order:
    ist_screens, ist_claims, ist_bottlenecks, ist_demand_models,
    ist_validations, ist_equity_candidates, ist_effects_chains,
    ist_dialectic_reviews, ist_master_screens, ist_rotation_strategies,
    ist_catalyst_calendars, ist_stress_tests, ist_reports
"""

from alembic import op
import sqlalchemy as sa


revision = "005_ist_tables"
down_revision = "004_workflow_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ist_screens ─────────────────────────────────────────────────────
    op.create_table(
        "ist_screens",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "workflow_run_id",
            sa.Integer,
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column(
            "status", sa.Text, nullable=False, server_default="PENDING"
        ),
        sa.Column(
            "content_type", sa.Text, nullable=False, server_default="text"
        ),
        sa.Column("raw_content", sa.Text, nullable=False),
        sa.Column("screening_brief", sa.Text, nullable=True),
        sa.Column("content_extraction", sa.Text, nullable=True),
        sa.Column("source_bias", sa.Text, nullable=True),
        sa.Column(
            "is_certified", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column("certified_at", sa.DateTime, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'EXTRACTING', 'ANALYZING', 'SCANNING', "
            "'DIALECTIC', 'SYNTHESIZING', 'COMPLETED', 'FAILED')",
            name="ck_ist_screen_status",
        ),
        sa.CheckConstraint(
            "content_type IN ('podcast_transcript', 'article', 'earnings_call', "
            "'research_note', 'text')",
            name="ck_ist_screen_content_type",
        ),
    )
    op.create_index("ix_ist_screens_workflow", "ist_screens", ["workflow_run_id"])
    op.create_index("ix_ist_screens_status", "ist_screens", ["status", "created_at"])
    op.create_index("ix_ist_screens_created", "ist_screens", ["created_at"])

    # ── ist_claims ──────────────────────────────────────────────────────
    op.create_table(
        "ist_claims",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "screen_id",
            sa.Integer,
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("claim_text", sa.Text, nullable=False),
        sa.Column("source_citation", sa.Text, nullable=False),
        sa.Column("quantitative_anchor", sa.Text, nullable=True),
        sa.Column("temporal_marker", sa.Text, nullable=True),
        sa.Column("bottleneck_name", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column(
            "is_validated", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column("validation_verdict", sa.Text, nullable=True),
        sa.Column("validation_source", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_ist_claim_confidence",
        ),
        sa.CheckConstraint(
            "validation_verdict IN ('confirmed', 'partially_confirmed', "
            "'contradicted', 'unvalidatable')",
            name="ck_ist_claim_validation_verdict",
        ),
    )
    op.create_index("ix_ist_claims_screen", "ist_claims", ["screen_id"])
    op.create_index(
        "ix_ist_claims_bottleneck", "ist_claims", ["screen_id", "bottleneck_name"]
    )
    op.create_index(
        "ix_ist_claims_validated", "ist_claims", ["screen_id", "is_validated"]
    )

    # ── ist_bottlenecks ─────────────────────────────────────────────────
    op.create_table(
        "ist_bottlenecks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "screen_id",
            sa.Integer,
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("phase", sa.Integer, nullable=False),
        sa.Column("phase_label", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("quantitative_evidence", sa.Text, nullable=True),
        sa.Column("temporal_marker", sa.Text, nullable=True),
        sa.Column("resolution_trigger", sa.Text, nullable=True),
        sa.Column(
            "causal_parent_id",
            sa.Integer,
            sa.ForeignKey("ist_bottlenecks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "phase IN (0, 1, 2, 3)",
            name="ck_ist_bottleneck_phase",
        ),
    )
    op.create_index(
        "ix_ist_bottlenecks_screen", "ist_bottlenecks", ["screen_id", "phase"]
    )
    op.create_index(
        "ix_ist_bottlenecks_parent", "ist_bottlenecks", ["causal_parent_id"]
    )

    # ── ist_demand_models ───────────────────────────────────────────────
    op.create_table(
        "ist_demand_models",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "screen_id",
            sa.Integer,
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bottleneck_id",
            sa.Integer,
            sa.ForeignKey("ist_bottlenecks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("formula", sa.Text, nullable=False),
        sa.Column("base_case", sa.Text, nullable=False),
        sa.Column("bull_case", sa.Text, nullable=False),
        sa.Column("bear_case", sa.Text, nullable=False),
        sa.Column("sensitivity_table", sa.Text, nullable=True),
        sa.Column("multiplier_chain", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_ist_demand_models_screen", "ist_demand_models", ["screen_id"]
    )
    op.create_index(
        "ix_ist_demand_models_bottleneck", "ist_demand_models", ["bottleneck_id"]
    )

    # ── ist_validations ─────────────────────────────────────────────────
    op.create_table(
        "ist_validations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "screen_id",
            sa.Integer,
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "claim_id",
            sa.Integer,
            sa.ForeignKey("ist_claims.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("verdict", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("evidence", sa.Text, nullable=False),
        sa.Column("sources", sa.Text, nullable=False),
        sa.Column("search_queries", sa.Text, nullable=True),
        sa.Column(
            "validated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "verdict IN ('confirmed', 'partially_confirmed', "
            "'contradicted', 'unvalidatable')",
            name="ck_ist_validation_verdict",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_ist_validation_confidence",
        ),
    )
    op.create_index(
        "ix_ist_validations_screen", "ist_validations", ["screen_id"]
    )
    op.create_index(
        "ix_ist_validations_claim", "ist_validations", ["claim_id"]
    )
    op.create_index(
        "ix_ist_validations_verdict",
        "ist_validations",
        ["screen_id", "verdict"],
    )

    # ── ist_equity_candidates ───────────────────────────────────────────
    op.create_table(
        "ist_equity_candidates",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "screen_id",
            sa.Integer,
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ticker", sa.Text, nullable=False),
        sa.Column("company_name", sa.Text, nullable=False),
        sa.Column(
            "bottleneck_id",
            sa.Integer,
            sa.ForeignKey("ist_bottlenecks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("scarcity_score", sa.Text, nullable=False),
        sa.Column("moat_type", sa.Text, nullable=True),
        sa.Column("moat_evidence", sa.Text, nullable=True),
        sa.Column("catalyst", sa.Text, nullable=True),
        sa.Column("tier", sa.Integer, nullable=False),
        sa.Column("tier_rationale", sa.Text, nullable=True),
        sa.Column("phase", sa.Integer, nullable=True),
        sa.Column("conviction", sa.Text, nullable=True),
        sa.Column("price_at_screen", sa.Float, nullable=True),
        sa.Column("pe_ratio", sa.Float, nullable=True),
        sa.Column("market_cap", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "tier IN (1, 2, 3)",
            name="ck_ist_equity_tier",
        ),
        sa.CheckConstraint(
            "conviction IN ('HIGH', 'MEDIUM', 'LOW')",
            name="ck_ist_equity_conviction",
        ),
    )
    op.create_index(
        "ix_ist_equity_screen", "ist_equity_candidates", ["screen_id", "tier"]
    )
    op.create_index(
        "ix_ist_equity_ticker", "ist_equity_candidates", ["ticker"]
    )
    op.create_index(
        "ix_ist_equity_bottleneck", "ist_equity_candidates", ["bottleneck_id"]
    )
    op.create_index(
        "ix_ist_equity_unique",
        "ist_equity_candidates",
        ["screen_id", "ticker"],
        unique=True,
    )

    # ── ist_effects_chains ──────────────────────────────────────────────
    op.create_table(
        "ist_effects_chains",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "screen_id",
            sa.Integer,
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("thesis", sa.Text, nullable=False),
        sa.Column("effect_order", sa.Integer, nullable=False),
        sa.Column("effect_description", sa.Text, nullable=False),
        sa.Column(
            "equity_candidate_id",
            sa.Integer,
            sa.ForeignKey("ist_equity_candidates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "effect_order IN (1, 2, 3)",
            name="ck_ist_effects_order",
        ),
    )
    op.create_index(
        "ix_ist_effects_screen",
        "ist_effects_chains",
        ["screen_id", "effect_order"],
    )
    op.create_index(
        "ix_ist_effects_candidate",
        "ist_effects_chains",
        ["equity_candidate_id"],
    )

    # ── ist_dialectic_reviews ───────────────────────────────────────────
    op.create_table(
        "ist_dialectic_reviews",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "screen_id",
            sa.Integer,
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("side", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "side IN ('OPTIMIST', 'PESSIMIST', 'SYNTHESIS')",
            name="ck_ist_dialectic_side",
        ),
    )
    op.create_index(
        "ix_ist_dialectic_screen",
        "ist_dialectic_reviews",
        ["screen_id", "side"],
    )
    op.create_index(
        "ix_ist_dialectic_unique",
        "ist_dialectic_reviews",
        ["screen_id", "side"],
        unique=True,
    )

    # ── ist_master_screens ──────────────────────────────────────────────
    op.create_table(
        "ist_master_screens",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "screen_id",
            sa.Integer,
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ranked_equities", sa.Text, nullable=False),
        sa.Column("invariant_compliance", sa.Text, nullable=False),
        sa.Column("total_equities", sa.Integer, nullable=False),
        sa.Column("tier1_count", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_ist_master_screen",
        "ist_master_screens",
        ["screen_id"],
        unique=True,
    )

    # ── ist_rotation_strategies ─────────────────────────────────────────
    op.create_table(
        "ist_rotation_strategies",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "screen_id",
            sa.Integer,
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phase_allocations", sa.Text, nullable=False),
        sa.Column("rotation_triggers", sa.Text, nullable=False),
        sa.Column("risk_limits", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_ist_rotation_screen",
        "ist_rotation_strategies",
        ["screen_id"],
        unique=True,
    )

    # ── ist_catalyst_calendars ──────────────────────────────────────────
    op.create_table(
        "ist_catalyst_calendars",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "screen_id",
            sa.Integer,
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("catalysts", sa.Text, nullable=False),
        sa.Column("total_catalysts", sa.Integer, nullable=False),
        sa.Column("next_catalyst_date", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_ist_catalyst_screen",
        "ist_catalyst_calendars",
        ["screen_id"],
        unique=True,
    )

    # ── ist_stress_tests ────────────────────────────────────────────────
    op.create_table(
        "ist_stress_tests",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "screen_id",
            sa.Integer,
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("framework_tests", sa.Text, nullable=False),
        sa.Column("name_tests", sa.Text, nullable=False),
        sa.Column("survival_scores", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_ist_stress_screen",
        "ist_stress_tests",
        ["screen_id"],
        unique=True,
    )

    # ── ist_reports ─────────────────────────────────────────────────────
    op.create_table(
        "ist_reports",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "screen_id",
            sa.Integer,
            sa.ForeignKey("ist_screens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("metadata", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_ist_report_screen",
        "ist_reports",
        ["screen_id"],
        unique=True,
    )


def downgrade() -> None:
    # Drop in reverse FK dependency order
    op.drop_index("ix_ist_report_screen", table_name="ist_reports")
    op.drop_table("ist_reports")

    op.drop_index("ix_ist_stress_screen", table_name="ist_stress_tests")
    op.drop_table("ist_stress_tests")

    op.drop_index("ix_ist_catalyst_screen", table_name="ist_catalyst_calendars")
    op.drop_table("ist_catalyst_calendars")

    op.drop_index("ix_ist_rotation_screen", table_name="ist_rotation_strategies")
    op.drop_table("ist_rotation_strategies")

    op.drop_index("ix_ist_master_screen", table_name="ist_master_screens")
    op.drop_table("ist_master_screens")

    op.drop_index("ix_ist_dialectic_unique", table_name="ist_dialectic_reviews")
    op.drop_index("ix_ist_dialectic_screen", table_name="ist_dialectic_reviews")
    op.drop_table("ist_dialectic_reviews")

    op.drop_index("ix_ist_effects_candidate", table_name="ist_effects_chains")
    op.drop_index("ix_ist_effects_screen", table_name="ist_effects_chains")
    op.drop_table("ist_effects_chains")

    op.drop_index("ix_ist_equity_unique", table_name="ist_equity_candidates")
    op.drop_index("ix_ist_equity_bottleneck", table_name="ist_equity_candidates")
    op.drop_index("ix_ist_equity_ticker", table_name="ist_equity_candidates")
    op.drop_index("ix_ist_equity_screen", table_name="ist_equity_candidates")
    op.drop_table("ist_equity_candidates")

    op.drop_index("ix_ist_validations_verdict", table_name="ist_validations")
    op.drop_index("ix_ist_validations_claim", table_name="ist_validations")
    op.drop_index("ix_ist_validations_screen", table_name="ist_validations")
    op.drop_table("ist_validations")

    op.drop_index("ix_ist_demand_models_bottleneck", table_name="ist_demand_models")
    op.drop_index("ix_ist_demand_models_screen", table_name="ist_demand_models")
    op.drop_table("ist_demand_models")

    op.drop_index("ix_ist_bottlenecks_parent", table_name="ist_bottlenecks")
    op.drop_index("ix_ist_bottlenecks_screen", table_name="ist_bottlenecks")
    op.drop_table("ist_bottlenecks")

    op.drop_index("ix_ist_claims_validated", table_name="ist_claims")
    op.drop_index("ix_ist_claims_bottleneck", table_name="ist_claims")
    op.drop_index("ix_ist_claims_screen", table_name="ist_claims")
    op.drop_table("ist_claims")

    op.drop_index("ix_ist_screens_created", table_name="ist_screens")
    op.drop_index("ix_ist_screens_status", table_name="ist_screens")
    op.drop_index("ix_ist_screens_workflow", table_name="ist_screens")
    op.drop_table("ist_screens")
