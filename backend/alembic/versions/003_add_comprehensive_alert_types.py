"""003 add comprehensive alert types

Revision ID: 003_alert_types
Revises: 002_comprehensive
Create Date: 2026-01-31

Expands the alert_type CHECK constraint to include new alert types from
the comprehensive analysis engine (Wave 5):
- profitability_decline
- leverage_warning
- cash_flow_quality
- valuation_extreme
- short_interest_spike

Also adds enable toggle columns to alert_settings for the new alert types.
"""

from alembic import op
import sqlalchemy as sa


revision = "003_alert_types"
down_revision = "002_comprehensive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Recreate alerts table with expanded CHECK constraint ──
    # SQLite does not support ALTER CONSTRAINT, so we use batch mode
    # which recreates the table under the hood.
    with op.batch_alter_table("alerts") as batch_op:
        # Drop old constraint — wrapped in try/except because the
        # constraint name may differ or may not exist yet (e.g. fresh DB,
        # or SQLite which doesn't always preserve named CHECK constraints).
        try:
            batch_op.drop_constraint("ck_alert_type", type_="check")
        except Exception:
            pass  # Constraint may not exist or have different name

        batch_op.create_check_constraint(
            "ck_alert_type",
            "alert_type IN ('m_score_warning', 'z_score_distress', "
            "'z_score_zone_change', 'rule_of_40_fail', "
            "'magic_number_low', 'sentiment_divergence', "
            "'profitability_decline', 'leverage_warning', "
            "'cash_flow_quality', 'valuation_extreme', "
            "'short_interest_spike')",
        )

    # ── Add new enable columns to alert_settings ──
    with op.batch_alter_table("alert_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "enable_profitability_alerts",
                sa.Integer,
                nullable=False,
                server_default="1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "enable_leverage_alerts",
                sa.Integer,
                nullable=False,
                server_default="1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "enable_cash_flow_alerts",
                sa.Integer,
                nullable=False,
                server_default="1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "enable_valuation_alerts",
                sa.Integer,
                nullable=False,
                server_default="1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "enable_short_interest_alerts",
                sa.Integer,
                nullable=False,
                server_default="1",
            )
        )


def downgrade() -> None:
    # ── Remove new columns from alert_settings ──
    with op.batch_alter_table("alert_settings") as batch_op:
        batch_op.drop_column("enable_short_interest_alerts")
        batch_op.drop_column("enable_valuation_alerts")
        batch_op.drop_column("enable_cash_flow_alerts")
        batch_op.drop_column("enable_leverage_alerts")
        batch_op.drop_column("enable_profitability_alerts")

    # ── Restore original CHECK constraint on alerts ──
    with op.batch_alter_table("alerts") as batch_op:
        try:
            batch_op.drop_constraint("ck_alert_type", type_="check")
        except Exception:
            pass  # Constraint may not exist or have different name

        batch_op.create_check_constraint(
            "ck_alert_type",
            "alert_type IN ('m_score_warning', 'z_score_distress', "
            "'z_score_zone_change', 'rule_of_40_fail', "
            "'magic_number_low', 'sentiment_divergence')",
        )
