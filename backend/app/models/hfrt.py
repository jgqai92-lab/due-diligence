"""HFRT (Hedge Fund Research Team) models — 4 HFRT tables.

Tables:
    HFRTProject — project-level metadata (ticker, status, templates)
    HFRTTemplate — individual research template data (15 templates, JSON data)
    HFRTSECFiling — cached SEC EDGAR filings
    HFRTDialecticReview — isolated bull/bear reviews
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


class HFRTProject(Base):
    """Project-level metadata for HFRT deep equity research."""

    __tablename__ = "hfrt_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_run_id = Column(
        Integer,
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticker = Column(Text, nullable=False)
    company_name = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="PENDING")
    sector = Column(Text, nullable=True)
    exchange = Column(Text, nullable=True)
    market_cap = Column(Float, nullable=True)
    # Idea screen verdict from Phase 1
    investable = Column(Integer, nullable=False, default=0)
    investable_verdict = Column(Text, nullable=True)
    # Conviction scoring from Phase 5
    conviction_score = Column(Float, nullable=True)
    position_tier = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    # Bridge source tracking
    source = Column(Text, nullable=True)  # "IST_HANDOFF" or null for manual
    ist_screen_id = Column(Integer, nullable=True)  # Source IST screen ID (soft FK)
    # External validation results (Gap 1: Perplexity-grounded claim validation)
    external_validation_results = Column(Text, nullable=True)  # JSON: HFRTValidationResult
    # Certification & invariants
    is_certified = Column(Integer, nullable=False, default=0)
    certified_at = Column(DateTime, nullable=True)
    invariant_results = Column(Text, nullable=True)  # JSON: list of invariant check results
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
    workflow_run = relationship("WorkflowRun", backref="hfrt_project")
    templates = relationship(
        "HFRTTemplate",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="HFRTTemplate.template_number",
    )
    sec_filings = relationship(
        "HFRTSECFiling",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    dialectic_reviews = relationship(
        "HFRTDialecticReview",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'SCREENING', 'RESEARCHING', 'DUE_DILIGENCE', "
            "'DIALECTIC', 'SYNTHESIZING', 'COMPLETED', 'FAILED', 'NOT_INVESTABLE')",
            name="ck_hfrt_project_status",
        ),
        CheckConstraint(
            "position_tier IS NULL OR position_tier IN ('FULL', 'HALF', 'QUARTER', 'WATCH')",
            name="ck_hfrt_position_tier",
        ),
        CheckConstraint(
            "recommendation IS NULL OR recommendation IN ('BUY', 'HOLD', 'SELL', 'PASS')",
            name="ck_hfrt_recommendation",
        ),
        Index("ix_hfrt_projects_workflow", "workflow_run_id"),
        Index("ix_hfrt_projects_ticker", "ticker"),
        Index("ix_hfrt_projects_status", "status", "created_at"),
    )


class HFRTTemplate(Base):
    """Individual research template data — 15 templates stored as JSON.

    Templates:
        00: Idea Screen
        01: Company Overview
        02: Business Model
        03: Competitive Position
        04: Industry Analysis
        05: Financial Analysis
        06: Valuation
        07: Management Assessment
        08: Risk Analysis
        09: Quality of Earnings
        10: Catalyst Analysis
        11: Investment Thesis
        12: Bull Synthesis
        13: Bear Synthesis
        14: Investment Memo
    """

    __tablename__ = "hfrt_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer,
        ForeignKey("hfrt_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_number = Column(Integer, nullable=False)
    template_name = Column(Text, nullable=False)
    data = Column(Text, nullable=True)  # JSON
    status = Column(Text, nullable=False, default="EMPTY")
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
    project = relationship("HFRTProject", back_populates="templates")

    __table_args__ = (
        CheckConstraint(
            "template_number >= 0 AND template_number <= 14",
            name="ck_hfrt_template_number",
        ),
        CheckConstraint(
            "status IN ('EMPTY', 'POPULATING', 'POPULATED', 'FAILED')",
            name="ck_hfrt_template_status",
        ),
        Index("ix_hfrt_templates_project", "project_id", "template_number"),
        Index(
            "ix_hfrt_templates_unique",
            "project_id",
            "template_number",
            unique=True,
        ),
    )


class HFRTSECFiling(Base):
    """Cached SEC EDGAR filings with content hash dedup."""

    __tablename__ = "hfrt_sec_filings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer,
        ForeignKey("hfrt_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticker = Column(Text, nullable=False)
    filing_type = Column(Text, nullable=False)
    filing_date = Column(Text, nullable=True)
    accession_number = Column(Text, nullable=True)
    content_hash = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    sections = Column(Text, nullable=True)  # JSON: extracted sections
    url = Column(Text, nullable=True)
    fetched_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("HFRTProject", back_populates="sec_filings")

    __table_args__ = (
        CheckConstraint(
            "filing_type IN ('10-K', '10-Q', 'DEF_14A', '8-K', 'OTHER')",
            name="ck_hfrt_filing_type",
        ),
        Index("ix_hfrt_sec_filings_project", "project_id"),
        Index("ix_hfrt_sec_filings_ticker", "ticker", "filing_type"),
        Index("ix_hfrt_sec_filings_hash", "content_hash"),
    )


class HFRTDialecticReview(Base):
    """Isolated bull/bear dialectic reviews."""

    __tablename__ = "hfrt_dialectic_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer,
        ForeignKey("hfrt_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    side = Column(Text, nullable=False)
    content = Column(Text, nullable=False)  # JSON
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("HFRTProject", back_populates="dialectic_reviews")

    __table_args__ = (
        CheckConstraint(
            "side IN ('BULL', 'BEAR')",
            name="ck_hfrt_dialectic_side",
        ),
        Index("ix_hfrt_dialectic_project", "project_id", "side"),
        Index(
            "ix_hfrt_dialectic_unique",
            "project_id",
            "side",
            unique=True,
        ),
    )
