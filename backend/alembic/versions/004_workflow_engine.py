"""004 workflow engine

Revision ID: 004_workflow_engine
Revises: 003_alert_types
Create Date: 2026-02-07

Creates the workflow_runs and workflow_steps tables for the
workflow orchestration engine (Wave A1).
"""

from alembic import op
import sqlalchemy as sa


revision = "004_workflow_engine"
down_revision = "003_alert_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── workflow_runs table ──────────────────────────────────────────────
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("workflow_type", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column(
            "status", sa.Text, nullable=False, server_default="PENDING"
        ),
        sa.Column(
            "current_phase", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column("current_phase_name", sa.Text, nullable=True),
        sa.Column("config", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
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
            "workflow_type IN ('IST', 'HFRT')",
            name="ck_workflow_type",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'PAUSED', 'COMPLETED', "
            "'FAILED', 'CANCELLED', 'CANCELLING', 'RETRYING')",
            name="ck_workflow_status",
        ),
    )

    op.create_index("ix_workflow_runs_status", "workflow_runs", ["status"])
    op.create_index(
        "ix_workflow_runs_workflow_type", "workflow_runs", ["workflow_type"]
    )

    # ── workflow_steps table ─────────────────────────────────────────────
    op.create_table(
        "workflow_steps",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "workflow_run_id",
            sa.Integer,
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_name", sa.Text, nullable=False),
        sa.Column("phase", sa.Integer, nullable=False),
        sa.Column("phase_name", sa.Text, nullable=False),
        sa.Column("step_order", sa.Integer, nullable=False),
        sa.Column(
            "status", sa.Text, nullable=False, server_default="PENDING"
        ),
        sa.Column("input_data", sa.Text, nullable=True),
        sa.Column("output_data", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "retry_count", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED')",
            name="ck_step_status",
        ),
    )

    op.create_index(
        "ix_workflow_steps_workflow_run_id",
        "workflow_steps",
        ["workflow_run_id"],
    )
    op.create_index(
        "ix_workflow_steps_status", "workflow_steps", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_steps_status", table_name="workflow_steps")
    op.drop_index(
        "ix_workflow_steps_workflow_run_id", table_name="workflow_steps"
    )
    op.drop_table("workflow_steps")

    op.drop_index(
        "ix_workflow_runs_workflow_type", table_name="workflow_runs"
    )
    op.drop_index("ix_workflow_runs_status", table_name="workflow_runs")
    op.drop_table("workflow_runs")
