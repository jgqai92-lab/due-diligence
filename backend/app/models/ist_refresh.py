"""IST refresh models for incremental screen updates."""

from datetime import datetime, timezone

from sqlalchemy import (
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


class ISTScreenRefresh(Base):
    """Refresh run metadata for a completed IST screen."""

    __tablename__ = "ist_screen_refreshes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_run_id = Column(
        Integer,
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    refresh_number = Column(Integer, nullable=False)
    status = Column(Text, nullable=False, default="PENDING")

    content_type = Column(Text, nullable=False, default="text")
    delta_content = Column(Text, nullable=False)
    impact_assessment = Column(Text, nullable=True)
    steps_reexecuted = Column(Text, nullable=True)
    new_claims_count = Column(Integer, nullable=False, default=0)
    new_claims = Column(Text, nullable=True)
    new_source_bias = Column(Text, nullable=True)
    tier_changes = Column(Text, nullable=True)
    tier_change_count = Column(Integer, nullable=False, default=0)
    refresh_notes = Column(Text, nullable=True)
    idempotency_key = Column(Text, nullable=True)

    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    screen = relationship("ISTScreen", back_populates="refreshes")
    workflow_run = relationship("WorkflowRun", backref="ist_refreshes")
    claims = relationship("ISTClaim", back_populates="source_refresh")

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'EXTRACTING', 'ASSESSING', 'RE_ANALYZING', "
            "'RE_SYNTHESIZING', 'COMPLETED', 'FAILED')",
            name="ck_ist_refresh_status",
        ),
        CheckConstraint(
            "content_type IN ('podcast_transcript', 'article', 'earnings_call', "
            "'research_note', 'text')",
            name="ck_ist_refresh_content_type",
        ),
        Index("ix_ist_refreshes_screen", "screen_id", "created_at"),
        Index("ix_ist_refreshes_workflow", "workflow_run_id"),
        Index("ix_ist_refreshes_status", "status", "created_at"),
        Index("ix_ist_refreshes_unique", "screen_id", "refresh_number", unique=True),
        Index(
            "ix_ist_refreshes_idempotency_key",
            "idempotency_key",
            unique=True,
        ),
    )
