"""Workflow engine models — WorkflowRun and WorkflowStep."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from app.models import Base


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_type = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="PENDING")
    current_phase = Column(Integer, nullable=False, default=0)
    current_phase_name = Column(Text, nullable=True)
    config = Column(Text, nullable=True)  # JSON string
    auto_advance = Column(Boolean, default=False, nullable=False, server_default="0")
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    steps = relationship(
        "WorkflowStep",
        back_populates="workflow_run",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.step_order",
    )

    __table_args__ = (
        CheckConstraint(
            "workflow_type IN ('IST', 'HFRT', 'IST_SYNTHESIS', 'IST_REFRESH')",
            name="ck_workflow_type",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'PAUSED', 'COMPLETED', "
            "'FAILED', 'CANCELLED', 'CANCELLING', 'RETRYING')",
            name="ck_workflow_status",
        ),
        Index("ix_workflow_runs_status", "status"),
        Index("ix_workflow_runs_workflow_type", "workflow_type"),
    )


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_run_id = Column(
        Integer,
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_name = Column(Text, nullable=False)
    phase = Column(Integer, nullable=False)
    phase_name = Column(Text, nullable=False)
    step_order = Column(Integer, nullable=False)
    status = Column(Text, nullable=False, default="PENDING")
    input_data = Column(Text, nullable=True)
    output_data = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    depends_on = Column(Text, nullable=True)  # JSON list of step names, e.g. '["content_extraction"]'
    model_tier = Column(Text, nullable=True)  # "opus", "sonnet", or "none"
    retry_strategy = Column(Text, nullable=True)  # "self" or "with_parent"; NULL = "self"
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    workflow_run = relationship("WorkflowRun", back_populates="steps")

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED')",
            name="ck_step_status",
        ),
        Index("ix_workflow_steps_workflow_run_id", "workflow_run_id"),
        Index("ix_workflow_steps_status", "status"),
    )
