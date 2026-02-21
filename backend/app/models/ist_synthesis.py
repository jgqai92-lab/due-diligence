"""IST synthesis models for cross-screen meta-analysis."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from app.models import Base


class ISTSynthesis(Base):
    """Cross-screen synthesis combining 2+ completed IST screens."""

    __tablename__ = "ist_syntheses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="PENDING")
    workflow_run_id = Column(
        Integer,
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )

    overlap_matrix = Column(Text, nullable=True)
    thesis_interactions = Column(Text, nullable=True)
    tier_changes = Column(Text, nullable=True)
    combined_brief = Column(Text, nullable=True)
    combined_report = Column(Text, nullable=True)
    report_metadata = Column(Text, nullable=True)
    certification = Column(Text, nullable=True)
    hfrt_handoff = Column(Text, nullable=True)

    is_certified = Column(Integer, nullable=False, default=0)
    certified_at = Column(DateTime, nullable=True)
    idempotency_key = Column(Text, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    workflow_run = relationship("WorkflowRun", backref="ist_syntheses")
    source_links = relationship(
        "ISTSynthesisSource",
        back_populates="synthesis",
        cascade="all, delete-orphan",
    )
    equities = relationship(
        "ISTSynthesisEquity",
        back_populates="synthesis",
        cascade="all, delete-orphan",
    )
    dialectic_reviews = relationship(
        "ISTSynthesisDialectic",
        back_populates="synthesis",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'INGESTING', 'ANALYZING', 'DIALECTIC', "
            "'SYNTHESIZING', 'COMPLETED', 'FAILED')",
            name="ck_ist_synthesis_status",
        ),
        Index("ix_ist_syntheses_status", "status", "created_at"),
        Index("ix_ist_syntheses_workflow", "workflow_run_id"),
        Index(
            "ix_ist_syntheses_idempotency_key",
            "idempotency_key",
            unique=True,
        ),
    )


class ISTSynthesisSource(Base):
    """Source screens used as inputs to a synthesis."""

    __tablename__ = "ist_synthesis_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    synthesis_id = Column(
        Integer,
        ForeignKey("ist_syntheses.id", ondelete="CASCADE"),
        nullable=False,
    )
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    screen_name = Column(Text, nullable=False)
    tier1_count = Column(Integer, nullable=False, default=0)
    tier2_count = Column(Integer, nullable=False, default=0)
    tier3_count = Column(Integer, nullable=False, default=0)
    primary_theme = Column(Text, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    synthesis = relationship("ISTSynthesis", back_populates="source_links")
    screen = relationship("ISTScreen")

    __table_args__ = (
        Index("ix_ist_synth_sources_synth", "synthesis_id"),
        Index("ix_ist_synth_sources_screen", "screen_id"),
        Index(
            "ix_ist_synth_sources_unique",
            "synthesis_id",
            "screen_id",
            unique=True,
        ),
    )


class ISTSynthesisEquity(Base):
    """Re-tiered equity candidate within a synthesis output."""

    __tablename__ = "ist_synthesis_equities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    synthesis_id = Column(
        Integer,
        ForeignKey("ist_syntheses.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticker = Column(Text, nullable=False)
    company_name = Column(Text, nullable=False)

    original_tier = Column(Integer, nullable=False)
    new_tier = Column(Integer, nullable=False)
    tier_changed = Column(Integer, nullable=False, default=0)
    tier_change_rationale = Column(Text, nullable=True)

    source_screen_count = Column(Integer, nullable=False, default=1)
    source_screen_ids = Column(Text, nullable=False)
    combined_scarcity_score = Column(Text, nullable=True)
    combined_thesis = Column(Text, nullable=True)
    combined_catalyst = Column(Text, nullable=True)
    conviction = Column(Text, nullable=True)

    price_at_synthesis = Column(Float, nullable=True)
    pe_ratio = Column(Float, nullable=True)
    market_cap = Column(Float, nullable=True)

    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    synthesis = relationship("ISTSynthesis", back_populates="equities")

    __table_args__ = (
        CheckConstraint("original_tier IN (1, 2, 3)", name="ck_synth_eq_orig_tier"),
        CheckConstraint("new_tier IN (1, 2, 3)", name="ck_synth_eq_new_tier"),
        CheckConstraint(
            "conviction IN ('HIGH', 'MEDIUM', 'LOW')",
            name="ck_synth_eq_conviction",
        ),
        Index("ix_ist_synth_eq_synth", "synthesis_id", "new_tier"),
        Index("ix_ist_synth_eq_ticker", "ticker"),
        Index("ix_ist_synth_eq_unique", "synthesis_id", "ticker", unique=True),
    )


class ISTSynthesisDialectic(Base):
    """Dialectic reviews for synthesis outputs."""

    __tablename__ = "ist_synthesis_dialectics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    synthesis_id = Column(
        Integer,
        ForeignKey("ist_syntheses.id", ondelete="CASCADE"),
        nullable=False,
    )
    side = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    synthesis = relationship("ISTSynthesis", back_populates="dialectic_reviews")

    __table_args__ = (
        CheckConstraint(
            "side IN ('OPTIMIST', 'PESSIMIST', 'SYNTHESIS')",
            name="ck_synth_dialectic_side",
        ),
        Index(
            "ix_ist_synth_dialectic_unique",
            "synthesis_id",
            "side",
            unique=True,
        ),
    )
