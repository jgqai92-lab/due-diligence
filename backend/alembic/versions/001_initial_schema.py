"""001 initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-01-30

Creates all 6 tables for The Skeptical Analyst:
- cached_financials
- analysis_reports
- holdings
- alerts
- watchlist
- alert_settings
"""

from alembic import op
import sqlalchemy as sa


revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── cached_financials ──
    op.create_table(
        "cached_financials",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.Text, nullable=False),
        sa.Column(
            "data_type",
            sa.Text,
            nullable=False,
        ),
        sa.Column("raw_json", sa.Text, nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("ticker", "data_type", name="uq_cache_ticker_type"),
        sa.CheckConstraint(
            "data_type IN ('financials', 'balance_sheet', 'cashflow', "
            "'quarterly_financials', 'quarterly_balance_sheet', "
            "'quarterly_cashflow', 'info')",
            name="ck_cache_data_type",
        ),
    )
    op.create_index(
        "idx_cache_lookup",
        "cached_financials",
        ["ticker", "data_type", "expires_at"],
    )
    op.create_index(
        "idx_cache_expiry",
        "cached_financials",
        ["expires_at"],
    )

    # ── analysis_reports ──
    op.create_table(
        "analysis_reports",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.Text, nullable=False),
        sa.Column("company_name", sa.Text),
        sa.Column("sector", sa.Text),
        sa.Column("beneish_m_score", sa.Text),
        sa.Column("altman_z_score", sa.Text),
        sa.Column("altman_z_score_saas", sa.Text),
        sa.Column("rule_of_40", sa.Text),
        sa.Column("magic_number", sa.Text),
        sa.Column("llm_report", sa.Text),
        sa.Column("bear_case", sa.Text),
        sa.Column("red_flags", sa.Text),
        sa.Column("data_sources", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )
    op.create_index(
        "idx_reports_ticker",
        "analysis_reports",
        ["ticker", sa.text("created_at DESC")],
    )

    # ── holdings ──
    op.create_table(
        "holdings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.Text, nullable=False),
        sa.Column("shares", sa.Float, nullable=False),
        sa.Column("cost_basis", sa.Float, nullable=False),
        sa.Column("purchase_date", sa.Text, nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.CheckConstraint("shares > 0", name="ck_holdings_shares_positive"),
        sa.CheckConstraint("cost_basis > 0", name="ck_holdings_cost_positive"),
    )
    op.create_index("idx_holdings_ticker", "holdings", ["ticker"])

    # ── alerts ──
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "holding_id",
            sa.Integer,
            sa.ForeignKey("holdings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("ticker", sa.Text, nullable=False),
        sa.Column("alert_type", sa.Text, nullable=False),
        sa.Column("severity", sa.Text, nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("previous_value", sa.Float),
        sa.Column("current_value", sa.Float),
        sa.Column("details", sa.Text),
        sa.Column("is_dismissed", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.CheckConstraint(
            "alert_type IN ('m_score_warning', 'z_score_distress', "
            "'z_score_zone_change', 'rule_of_40_fail', "
            "'magic_number_low', 'sentiment_divergence')",
            name="ck_alert_type",
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="ck_alert_severity",
        ),
    )
    op.create_index(
        "idx_alerts_active",
        "alerts",
        ["is_dismissed", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_alerts_ticker",
        "alerts",
        ["ticker", sa.text("created_at DESC")],
    )

    # ── watchlist ──
    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.Text, nullable=False, unique=True),
        sa.Column(
            "added_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )

    # ── alert_settings ──
    op.create_table(
        "alert_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "enable_z_score_alerts", sa.Integer, nullable=False, server_default="1"
        ),
        sa.Column(
            "enable_m_score_alerts", sa.Integer, nullable=False, server_default="1"
        ),
        sa.Column(
            "enable_rule_of_40_alerts", sa.Integer, nullable=False, server_default="1"
        ),
        sa.Column(
            "enable_magic_number_alerts",
            sa.Integer,
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "z_score_threshold", sa.Float, nullable=False, server_default="2.99"
        ),
        sa.Column(
            "m_score_threshold", sa.Float, nullable=False, server_default="-1.78"
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.CheckConstraint("id = 1", name="ck_alert_settings_single_row"),
    )

    # Insert default settings row
    op.execute("INSERT INTO alert_settings (id) VALUES (1)")


def downgrade() -> None:
    op.drop_table("alert_settings")
    op.drop_table("watchlist")
    op.drop_table("alerts")
    op.drop_table("holdings")
    op.drop_table("analysis_reports")
    op.drop_table("cached_financials")
