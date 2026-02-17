"""IST (Investment Screening Team) models — all 13 IST tables.

Tables:
    ISTScreen, ISTClaim, ISTBottleneck, ISTDemandModel, ISTValidation,
    ISTEquityCandidate, ISTEffectsChain, ISTDialecticReview, ISTMasterScreen,
    ISTRotationStrategy, ISTCatalystCalendar, ISTStressTest, ISTReport
"""

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


class ISTScreen(Base):
    """Screen-level metadata for IST investment screens."""

    __tablename__ = "ist_screens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_run_id = Column(
        Integer,
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="PENDING")
    content_type = Column(Text, nullable=False, default="text")
    raw_content = Column(Text, nullable=False)
    screening_brief = Column(Text, nullable=True)  # JSON
    content_extraction = Column(Text, nullable=True)  # JSON
    source_bias = Column(Text, nullable=True)  # JSON
    is_certified = Column(Integer, nullable=False, default=0)
    certified_at = Column(DateTime, nullable=True)
    certification = Column(Text, nullable=True)  # JSON: certification gate results
    hfrt_handoff = Column(Text, nullable=True)  # JSON: Tier 1 candidates for HFRT bridge
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    workflow_run = relationship("WorkflowRun", backref="ist_screen")
    claims = relationship(
        "ISTClaim",
        back_populates="screen",
        cascade="all, delete-orphan",
        order_by="ISTClaim.id",
    )
    bottlenecks = relationship(
        "ISTBottleneck",
        back_populates="screen",
        cascade="all, delete-orphan",
        order_by="ISTBottleneck.id",
    )
    demand_models = relationship(
        "ISTDemandModel",
        back_populates="screen",
        cascade="all, delete-orphan",
    )
    validations = relationship(
        "ISTValidation",
        back_populates="screen",
        cascade="all, delete-orphan",
    )
    equity_candidates = relationship(
        "ISTEquityCandidate",
        back_populates="screen",
        cascade="all, delete-orphan",
    )
    effects_chains = relationship(
        "ISTEffectsChain",
        back_populates="screen",
        cascade="all, delete-orphan",
    )
    dialectic_reviews = relationship(
        "ISTDialecticReview",
        back_populates="screen",
        cascade="all, delete-orphan",
    )
    master_screen = relationship(
        "ISTMasterScreen",
        back_populates="screen",
        uselist=False,
        cascade="all, delete-orphan",
    )
    rotation_strategy = relationship(
        "ISTRotationStrategy",
        back_populates="screen",
        uselist=False,
        cascade="all, delete-orphan",
    )
    catalyst_calendar = relationship(
        "ISTCatalystCalendar",
        back_populates="screen",
        uselist=False,
        cascade="all, delete-orphan",
    )
    stress_test = relationship(
        "ISTStressTest",
        back_populates="screen",
        uselist=False,
        cascade="all, delete-orphan",
    )
    report = relationship(
        "ISTReport",
        back_populates="screen",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'EXTRACTING', 'ANALYZING', 'SCANNING', "
            "'DIALECTIC', 'SYNTHESIZING', 'COMPLETED', 'FAILED')",
            name="ck_ist_screen_status",
        ),
        CheckConstraint(
            "content_type IN ('podcast_transcript', 'article', 'earnings_call', "
            "'research_note', 'text')",
            name="ck_ist_screen_content_type",
        ),
        Index("ix_ist_screens_workflow", "workflow_run_id"),
        Index("ix_ist_screens_status", "status", "created_at"),
        Index("ix_ist_screens_created", "created_at"),
    )


class ISTClaim(Base):
    """Individual claims extracted from source content."""

    __tablename__ = "ist_claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_text = Column(Text, nullable=False)
    source_citation = Column(Text, nullable=False)
    quantitative_anchor = Column(Text, nullable=True)
    temporal_marker = Column(Text, nullable=True)
    bottleneck_name = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    is_validated = Column(Integer, nullable=False, default=0)
    validation_verdict = Column(Text, nullable=True)
    validation_source = Column(Text, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    screen = relationship("ISTScreen", back_populates="claims")
    validation = relationship(
        "ISTValidation",
        back_populates="claim",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_ist_claim_confidence",
        ),
        CheckConstraint(
            "validation_verdict IN ('confirmed', 'partially_confirmed', "
            "'contradicted', 'unvalidatable')",
            name="ck_ist_claim_validation_verdict",
        ),
        Index("ix_ist_claims_screen", "screen_id"),
        Index("ix_ist_claims_bottleneck", "screen_id", "bottleneck_name"),
        Index("ix_ist_claims_validated", "screen_id", "is_validated"),
    )


class ISTBottleneck(Base):
    """Temporal bottleneck records from thematic analysis."""

    __tablename__ = "ist_bottlenecks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(Text, nullable=False)
    phase = Column(Integer, nullable=False)
    phase_label = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    quantitative_evidence = Column(Text, nullable=True)
    temporal_marker = Column(Text, nullable=True)
    resolution_trigger = Column(Text, nullable=True)
    pillar_name = Column(Text, nullable=True)  # Maps bottleneck to report pillar for Gate 3
    causal_parent_id = Column(
        Integer,
        ForeignKey("ist_bottlenecks.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    screen = relationship("ISTScreen", back_populates="bottlenecks")
    causal_parent = relationship(
        "ISTBottleneck",
        remote_side=[id],
        backref="causal_children",
    )
    demand_models = relationship(
        "ISTDemandModel",
        back_populates="bottleneck",
        cascade="all, delete-orphan",
    )
    equity_candidates = relationship(
        "ISTEquityCandidate",
        back_populates="bottleneck",
    )

    __table_args__ = (
        CheckConstraint(
            "phase IN (0, 1, 2, 3)",
            name="ck_ist_bottleneck_phase",
        ),
        Index("ix_ist_bottlenecks_screen", "screen_id", "phase"),
        Index("ix_ist_bottlenecks_parent", "causal_parent_id"),
    )


class ISTDemandModel(Base):
    """Quantitative demand models derived from bottleneck analysis."""

    __tablename__ = "ist_demand_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    bottleneck_id = Column(
        Integer,
        ForeignKey("ist_bottlenecks.id", ondelete="CASCADE"),
        nullable=False,
    )
    formula = Column(Text, nullable=False)
    base_case = Column(Text, nullable=False)  # JSON
    bull_case = Column(Text, nullable=False)  # JSON
    bear_case = Column(Text, nullable=False)  # JSON
    sensitivity_table = Column(Text, nullable=True)  # JSON
    multiplier_chain = Column(Text, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    screen = relationship("ISTScreen", back_populates="demand_models")
    bottleneck = relationship("ISTBottleneck", back_populates="demand_models")

    __table_args__ = (
        Index("ix_ist_demand_models_screen", "screen_id"),
        Index("ix_ist_demand_models_bottleneck", "bottleneck_id"),
    )


class ISTValidation(Base):
    """External validation records for claims."""

    __tablename__ = "ist_validations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_id = Column(
        Integer,
        ForeignKey("ist_claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    verdict = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    evidence = Column(Text, nullable=False)
    sources = Column(Text, nullable=False)  # JSON
    search_queries = Column(Text, nullable=True)  # JSON
    validated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    screen = relationship("ISTScreen", back_populates="validations")
    claim = relationship("ISTClaim", back_populates="validation")

    __table_args__ = (
        CheckConstraint(
            "verdict IN ('confirmed', 'partially_confirmed', "
            "'contradicted', 'unvalidatable')",
            name="ck_ist_validation_verdict",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_ist_validation_confidence",
        ),
        Index("ix_ist_validations_screen", "screen_id"),
        Index("ix_ist_validations_claim", "claim_id"),
        Index("ix_ist_validations_verdict", "screen_id", "verdict"),
    )


class ISTEquityCandidate(Base):
    """Company candidates identified during equity scanning."""

    __tablename__ = "ist_equity_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticker = Column(Text, nullable=False)
    company_name = Column(Text, nullable=False)
    bottleneck_id = Column(
        Integer,
        ForeignKey("ist_bottlenecks.id", ondelete="SET NULL"),
        nullable=True,
    )
    scarcity_score = Column(Text, nullable=False)  # JSON
    moat_type = Column(Text, nullable=True)
    moat_evidence = Column(Text, nullable=True)
    catalyst = Column(Text, nullable=True)
    tier = Column(Integer, nullable=False)
    tier_rationale = Column(Text, nullable=True)
    phase = Column(Integer, nullable=True)
    conviction = Column(Text, nullable=True)
    price_at_screen = Column(Float, nullable=True)
    pe_ratio = Column(Float, nullable=True)
    market_cap = Column(Float, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    screen = relationship("ISTScreen", back_populates="equity_candidates")
    bottleneck = relationship("ISTBottleneck", back_populates="equity_candidates")
    effects_chains = relationship(
        "ISTEffectsChain",
        back_populates="equity_candidate",
    )

    __table_args__ = (
        CheckConstraint(
            "tier IN (1, 2, 3)",
            name="ck_ist_equity_tier",
        ),
        CheckConstraint(
            "conviction IN ('HIGH', 'MEDIUM', 'LOW')",
            name="ck_ist_equity_conviction",
        ),
        Index("ix_ist_equity_screen", "screen_id", "tier"),
        Index("ix_ist_equity_ticker", "ticker"),
        Index("ix_ist_equity_bottleneck", "bottleneck_id"),
        Index(
            "ix_ist_equity_unique",
            "screen_id",
            "ticker",
            unique=True,
        ),
    )


class ISTEffectsChain(Base):
    """Multi-order effects chains mapping downstream impacts."""

    __tablename__ = "ist_effects_chains"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    thesis = Column(Text, nullable=False)
    effect_order = Column(Integer, nullable=False)
    effect_description = Column(Text, nullable=False)
    equity_candidate_id = Column(
        Integer,
        ForeignKey("ist_equity_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    screen = relationship("ISTScreen", back_populates="effects_chains")
    equity_candidate = relationship(
        "ISTEquityCandidate", back_populates="effects_chains"
    )

    __table_args__ = (
        CheckConstraint(
            "effect_order IN (1, 2, 3)",
            name="ck_ist_effects_order",
        ),
        Index("ix_ist_effects_screen", "screen_id", "effect_order"),
        Index("ix_ist_effects_candidate", "equity_candidate_id"),
    )


class ISTDialecticReview(Base):
    """Dialectic review records (optimist, pessimist, synthesis)."""

    __tablename__ = "ist_dialectic_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    side = Column(Text, nullable=False)
    content = Column(Text, nullable=False)  # JSON
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    screen = relationship("ISTScreen", back_populates="dialectic_reviews")

    __table_args__ = (
        CheckConstraint(
            "side IN ('OPTIMIST', 'PESSIMIST', 'SYNTHESIS')",
            name="ck_ist_dialectic_side",
        ),
        Index("ix_ist_dialectic_screen", "screen_id", "side"),
        Index(
            "ix_ist_dialectic_unique",
            "screen_id",
            "side",
            unique=True,
        ),
    )


class ISTMasterScreen(Base):
    """Final ranked equity output after all phases complete."""

    __tablename__ = "ist_master_screens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    ranked_equities = Column(Text, nullable=False)  # JSON
    invariant_compliance = Column(Text, nullable=False)  # JSON
    total_equities = Column(Integer, nullable=False)
    tier1_count = Column(Integer, nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    screen = relationship("ISTScreen", back_populates="master_screen")

    __table_args__ = (
        Index(
            "ix_ist_master_screen",
            "screen_id",
            unique=True,
        ),
    )


class ISTRotationStrategy(Base):
    """Phase-based portfolio allocation strategies."""

    __tablename__ = "ist_rotation_strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    phase_allocations = Column(Text, nullable=False)  # JSON
    rotation_triggers = Column(Text, nullable=False)  # JSON
    risk_limits = Column(Text, nullable=False)  # JSON
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    screen = relationship("ISTScreen", back_populates="rotation_strategy")

    __table_args__ = (
        Index(
            "ix_ist_rotation_screen",
            "screen_id",
            unique=True,
        ),
    )


class ISTCatalystCalendar(Base):
    """Dated catalyst events for equity candidates."""

    __tablename__ = "ist_catalyst_calendars"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    catalysts = Column(Text, nullable=False)  # JSON
    total_catalysts = Column(Integer, nullable=False)
    next_catalyst_date = Column(Text, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    screen = relationship("ISTScreen", back_populates="catalyst_calendar")

    __table_args__ = (
        Index(
            "ix_ist_catalyst_screen",
            "screen_id",
            unique=True,
        ),
    )


class ISTStressTest(Base):
    """Stress test results at framework and equity level."""

    __tablename__ = "ist_stress_tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    framework_tests = Column(Text, nullable=False)  # JSON
    name_tests = Column(Text, nullable=False)  # JSON
    survival_scores = Column(Text, nullable=False)  # JSON
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    screen = relationship("ISTScreen", back_populates="stress_test")

    __table_args__ = (
        Index(
            "ix_ist_stress_screen",
            "screen_id",
            unique=True,
        ),
    )


class ISTReport(Base):
    """Investment Thesis Report -- primary IST deliverable."""

    __tablename__ = "ist_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(
        Integer,
        ForeignKey("ist_screens.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    # JSON — "metadata" is reserved in SQLAlchemy. Expected keys for Gate 3:
    # pillar_count (int), equity_count (int), tier_breakdown (dict: tier1/tier2/tier3 counts)
    report_metadata = Column("metadata", Text, nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    screen = relationship("ISTScreen", back_populates="report")

    __table_args__ = (
        Index(
            "ix_ist_report_screen",
            "screen_id",
            unique=True,
        ),
    )
