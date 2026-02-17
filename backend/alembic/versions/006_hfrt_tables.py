"""006 hfrt tables

Revision ID: 006_hfrt_tables
Revises: 005_ist_tables
Create Date: 2026-02-07

Creates 4 HFRT (Hedge Fund Research Team) tables:
    hfrt_projects, hfrt_templates, hfrt_sec_filings, hfrt_dialectic_reviews
"""

from alembic import op
import sqlalchemy as sa


revision = "006_hfrt_tables"
down_revision = "005_ist_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── hfrt_projects ────────────────────────────────────────────────────
    op.create_table(
        "hfrt_projects",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "workflow_run_id",
            sa.Integer,
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ticker", sa.Text, nullable=False),
        sa.Column("company_name", sa.Text, nullable=True),
        sa.Column(
            "status", sa.Text, nullable=False, server_default="PENDING"
        ),
        sa.Column("sector", sa.Text, nullable=True),
        sa.Column("exchange", sa.Text, nullable=True),
        sa.Column("market_cap", sa.Float, nullable=True),
        sa.Column(
            "investable", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column("investable_verdict", sa.Text, nullable=True),
        sa.Column("conviction_score", sa.Float, nullable=True),
        sa.Column("position_tier", sa.Text, nullable=True),
        sa.Column("recommendation", sa.Text, nullable=True),
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
            "status IN ('PENDING', 'SCREENING', 'RESEARCHING', 'DUE_DILIGENCE', "
            "'DIALECTIC', 'SYNTHESIZING', 'COMPLETED', 'FAILED', 'NOT_INVESTABLE')",
            name="ck_hfrt_project_status",
        ),
        sa.CheckConstraint(
            "position_tier IS NULL OR position_tier IN ('FULL', 'HALF', 'QUARTER', 'WATCH')",
            name="ck_hfrt_position_tier",
        ),
        sa.CheckConstraint(
            "recommendation IS NULL OR recommendation IN ('BUY', 'HOLD', 'SELL', 'PASS')",
            name="ck_hfrt_recommendation",
        ),
    )
    op.create_index("ix_hfrt_projects_workflow", "hfrt_projects", ["workflow_run_id"])
    op.create_index("ix_hfrt_projects_ticker", "hfrt_projects", ["ticker"])
    op.create_index(
        "ix_hfrt_projects_status", "hfrt_projects", ["status", "created_at"]
    )

    # ── hfrt_templates ───────────────────────────────────────────────────
    op.create_table(
        "hfrt_templates",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "project_id",
            sa.Integer,
            sa.ForeignKey("hfrt_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("template_number", sa.Integer, nullable=False),
        sa.Column("template_name", sa.Text, nullable=False),
        sa.Column("data", sa.Text, nullable=True),
        sa.Column(
            "status", sa.Text, nullable=False, server_default="EMPTY"
        ),
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
            "template_number >= 0 AND template_number <= 14",
            name="ck_hfrt_template_number",
        ),
        sa.CheckConstraint(
            "status IN ('EMPTY', 'POPULATING', 'POPULATED', 'FAILED')",
            name="ck_hfrt_template_status",
        ),
    )
    op.create_index(
        "ix_hfrt_templates_project",
        "hfrt_templates",
        ["project_id", "template_number"],
    )
    op.create_index(
        "ix_hfrt_templates_unique",
        "hfrt_templates",
        ["project_id", "template_number"],
        unique=True,
    )

    # ── hfrt_sec_filings ─────────────────────────────────────────────────
    op.create_table(
        "hfrt_sec_filings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "project_id",
            sa.Integer,
            sa.ForeignKey("hfrt_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ticker", sa.Text, nullable=False),
        sa.Column("filing_type", sa.Text, nullable=False),
        sa.Column("filing_date", sa.Text, nullable=True),
        sa.Column("accession_number", sa.Text, nullable=True),
        sa.Column("content_hash", sa.Text, nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("sections", sa.Text, nullable=True),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "filing_type IN ('10-K', '10-Q', 'DEF_14A', '8-K', 'OTHER')",
            name="ck_hfrt_filing_type",
        ),
    )
    op.create_index(
        "ix_hfrt_sec_filings_project", "hfrt_sec_filings", ["project_id"]
    )
    op.create_index(
        "ix_hfrt_sec_filings_ticker",
        "hfrt_sec_filings",
        ["ticker", "filing_type"],
    )
    op.create_index(
        "ix_hfrt_sec_filings_hash", "hfrt_sec_filings", ["content_hash"]
    )

    # ── hfrt_dialectic_reviews ───────────────────────────────────────────
    op.create_table(
        "hfrt_dialectic_reviews",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "project_id",
            sa.Integer,
            sa.ForeignKey("hfrt_projects.id", ondelete="CASCADE"),
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
            "side IN ('BULL', 'BEAR')",
            name="ck_hfrt_dialectic_side",
        ),
    )
    op.create_index(
        "ix_hfrt_dialectic_project",
        "hfrt_dialectic_reviews",
        ["project_id", "side"],
    )
    op.create_index(
        "ix_hfrt_dialectic_unique",
        "hfrt_dialectic_reviews",
        ["project_id", "side"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("hfrt_dialectic_reviews")
    op.drop_table("hfrt_sec_filings")
    op.drop_table("hfrt_templates")
    op.drop_table("hfrt_projects")
