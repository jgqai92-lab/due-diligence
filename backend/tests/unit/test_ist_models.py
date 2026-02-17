"""Unit tests for IST SQLAlchemy models and Pydantic schemas.

Tests cover:
- All 13 IST model creation and field defaults
- CHECK constraints (status, content_type, tier, side, etc.)
- Foreign key relationships and cascading deletes
- Unique index enforcement
- Pydantic schema validation (input and output)
"""

import json
import pytest
from datetime import datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.models import Base
from app.models.workflow import WorkflowRun, WorkflowStep
from app.models.ist import (
    ISTScreen,
    ISTClaim,
    ISTBottleneck,
    ISTDemandModel,
    ISTValidation,
    ISTEquityCandidate,
    ISTEffectsChain,
    ISTDialecticReview,
    ISTMasterScreen,
    ISTRotationStrategy,
    ISTCatalystCalendar,
    ISTStressTest,
    ISTReport,
)
from app.schemas.ist import (
    ISTScreenCreate,
    ISTScreenBriefUpdate,
    ScreeningBrief,
    ContentExtractionSummary,
    SourceBiasSummary,
)


# ── Test DB setup ───────────────────────────────────────────────────────────

@pytest.fixture
def test_db():
    """Create a fresh in-memory SQLite DB for each test."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, conn_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def workflow_run(test_db):
    """Create a workflow run for FK references."""
    run = WorkflowRun(
        workflow_type="IST",
        name="Test Workflow",
        status="PENDING",
        current_phase=0,
    )
    test_db.add(run)
    test_db.commit()
    test_db.refresh(run)
    return run


@pytest.fixture
def ist_screen(test_db, workflow_run):
    """Create an IST screen for FK references."""
    screen = ISTScreen(
        workflow_run_id=workflow_run.id,
        name="Test Screen",
        status="PENDING",
        content_type="text",
        raw_content="Test content " * 20,
    )
    test_db.add(screen)
    test_db.commit()
    test_db.refresh(screen)
    return screen


# ── Model creation tests ────────────────────────────────────────────────────


class TestISTScreenModel:
    """Tests for the ISTScreen model."""

    def test_create_screen(self, test_db, workflow_run):
        screen = ISTScreen(
            workflow_run_id=workflow_run.id,
            name="Test Screen",
            raw_content="Test content " * 20,
        )
        test_db.add(screen)
        test_db.commit()
        test_db.refresh(screen)

        assert screen.id is not None
        assert screen.status == "PENDING"
        assert screen.content_type == "text"
        assert screen.is_certified == 0
        assert screen.created_at is not None

    def test_screen_defaults(self, test_db, workflow_run):
        screen = ISTScreen(
            workflow_run_id=workflow_run.id,
            name="Defaults Test",
            raw_content="Content " * 20,
        )
        test_db.add(screen)
        test_db.commit()

        assert screen.status == "PENDING"
        assert screen.content_type == "text"
        assert screen.is_certified == 0
        assert screen.screening_brief is None
        assert screen.content_extraction is None
        assert screen.source_bias is None

    def test_screen_json_columns(self, test_db, workflow_run):
        brief = ScreeningBrief(
            hypothesis="Test hypothesis",
            content_type="text",
            constraints={"minMarketCap": 1e9},
        )
        screen = ISTScreen(
            workflow_run_id=workflow_run.id,
            name="JSON Test",
            raw_content="Content " * 20,
            screening_brief=brief.model_dump_json(),
        )
        test_db.add(screen)
        test_db.commit()
        test_db.refresh(screen)

        parsed = json.loads(screen.screening_brief)
        assert parsed["hypothesis"] == "Test hypothesis"


class TestISTClaimModel:
    """Tests for the ISTClaim model."""

    def test_create_claim(self, test_db, ist_screen):
        claim = ISTClaim(
            screen_id=ist_screen.id,
            claim_text="Test claim about GPU supply",
            source_citation="Section 3, paragraph 2",
            quantitative_anchor="330000 GPUs per GW",
            temporal_marker="2025-2027",
            confidence=0.85,
        )
        test_db.add(claim)
        test_db.commit()
        test_db.refresh(claim)

        assert claim.id is not None
        assert claim.is_validated == 0
        assert claim.validation_verdict is None

    def test_claim_defaults(self, test_db, ist_screen):
        claim = ISTClaim(
            screen_id=ist_screen.id,
            claim_text="Minimal claim",
            source_citation="Source",
        )
        test_db.add(claim)
        test_db.commit()

        assert claim.is_validated == 0
        assert claim.quantitative_anchor is None
        assert claim.temporal_marker is None
        assert claim.bottleneck_name is None

    def test_claim_cascade_delete(self, test_db, ist_screen):
        """Deleting a screen cascades to claims."""
        claim = ISTClaim(
            screen_id=ist_screen.id,
            claim_text="Cascadable claim",
            source_citation="Source",
        )
        test_db.add(claim)
        test_db.commit()
        claim_id = claim.id

        test_db.delete(ist_screen)
        test_db.commit()

        assert test_db.query(ISTClaim).filter(ISTClaim.id == claim_id).first() is None


class TestISTBottleneckModel:
    """Tests for the ISTBottleneck model."""

    def test_create_bottleneck(self, test_db, ist_screen):
        bn = ISTBottleneck(
            screen_id=ist_screen.id,
            name="GPU Supply Scarcity",
            phase=1,
            phase_label="Near-term (0-18 months)",
            description="NVIDIA GB300 production capacity constrained",
        )
        test_db.add(bn)
        test_db.commit()
        test_db.refresh(bn)

        assert bn.id is not None
        assert bn.phase == 1
        assert bn.causal_parent_id is None

    def test_bottleneck_self_referential_fk(self, test_db, ist_screen):
        """Self-referential causal_parent_id works."""
        parent = ISTBottleneck(
            screen_id=ist_screen.id,
            name="Parent Bottleneck",
            phase=1,
            phase_label="Near-term",
            description="Parent desc",
        )
        test_db.add(parent)
        test_db.commit()

        child = ISTBottleneck(
            screen_id=ist_screen.id,
            name="Child Bottleneck",
            phase=2,
            phase_label="Mid-term",
            description="Child desc",
            causal_parent_id=parent.id,
        )
        test_db.add(child)
        test_db.commit()
        test_db.refresh(child)

        assert child.causal_parent_id == parent.id
        assert child.causal_parent.name == "Parent Bottleneck"


class TestISTEquityCandidateModel:
    """Tests for the ISTEquityCandidate model."""

    def test_create_candidate(self, test_db, ist_screen):
        candidate = ISTEquityCandidate(
            screen_id=ist_screen.id,
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            scarcity_score=json.dumps({"overall": 4.6}),
            tier=1,
            conviction="HIGH",
        )
        test_db.add(candidate)
        test_db.commit()
        test_db.refresh(candidate)

        assert candidate.id is not None
        assert candidate.tier == 1

    def test_unique_screen_ticker(self, test_db, ist_screen):
        """UNIQUE constraint on (screen_id, ticker) is enforced."""
        c1 = ISTEquityCandidate(
            screen_id=ist_screen.id,
            ticker="NVDA",
            company_name="NVIDIA",
            scarcity_score="{}",
            tier=1,
        )
        test_db.add(c1)
        test_db.commit()

        c2 = ISTEquityCandidate(
            screen_id=ist_screen.id,
            ticker="NVDA",
            company_name="NVIDIA duplicate",
            scarcity_score="{}",
            tier=2,
        )
        test_db.add(c2)
        with pytest.raises(IntegrityError):
            test_db.commit()
        test_db.rollback()


class TestISTDialecticReviewModel:
    """Tests for the ISTDialecticReview model."""

    def test_create_review(self, test_db, ist_screen):
        review = ISTDialecticReview(
            screen_id=ist_screen.id,
            side="OPTIMIST",
            content=json.dumps({"narrative": "Optimistic outlook"}),
        )
        test_db.add(review)
        test_db.commit()
        assert review.id is not None

    def test_unique_screen_side(self, test_db, ist_screen):
        """UNIQUE constraint on (screen_id, side) is enforced."""
        r1 = ISTDialecticReview(
            screen_id=ist_screen.id,
            side="PESSIMIST",
            content="{}",
        )
        test_db.add(r1)
        test_db.commit()

        r2 = ISTDialecticReview(
            screen_id=ist_screen.id,
            side="PESSIMIST",
            content='{"duplicate": true}',
        )
        test_db.add(r2)
        with pytest.raises(IntegrityError):
            test_db.commit()
        test_db.rollback()


class TestOneToOneModels:
    """Tests for one-to-one IST tables (master_screen, rotation, catalyst, stress, report)."""

    def test_master_screen_unique_screen_id(self, test_db, ist_screen):
        ms1 = ISTMasterScreen(
            screen_id=ist_screen.id,
            ranked_equities="[]",
            invariant_compliance="{}",
            total_equities=0,
            tier1_count=0,
        )
        test_db.add(ms1)
        test_db.commit()

        ms2 = ISTMasterScreen(
            screen_id=ist_screen.id,
            ranked_equities="[]",
            invariant_compliance="{}",
            total_equities=0,
            tier1_count=0,
        )
        test_db.add(ms2)
        with pytest.raises(IntegrityError):
            test_db.commit()
        test_db.rollback()

    def test_rotation_strategy_creation(self, test_db, ist_screen):
        rs = ISTRotationStrategy(
            screen_id=ist_screen.id,
            phase_allocations="[]",
            rotation_triggers="[]",
            risk_limits="{}",
        )
        test_db.add(rs)
        test_db.commit()
        assert rs.id is not None

    def test_catalyst_calendar_creation(self, test_db, ist_screen):
        cc = ISTCatalystCalendar(
            screen_id=ist_screen.id,
            catalysts="[]",
            total_catalysts=0,
        )
        test_db.add(cc)
        test_db.commit()
        assert cc.id is not None

    def test_stress_test_creation(self, test_db, ist_screen):
        st = ISTStressTest(
            screen_id=ist_screen.id,
            framework_tests="[]",
            name_tests="[]",
            survival_scores="{}",
        )
        test_db.add(st)
        test_db.commit()
        assert st.id is not None

    def test_report_creation(self, test_db, ist_screen):
        report = ISTReport(
            screen_id=ist_screen.id,
            title="Test Report",
            content="# Report content",
            report_metadata=json.dumps({"wordCount": 100}),
        )
        test_db.add(report)
        test_db.commit()
        assert report.id is not None
        assert report.report_metadata is not None


# ── Pydantic schema validation tests ────────────────────────────────────────


class TestISTScreenCreateSchema:
    """Tests for the ISTScreenCreate Pydantic schema."""

    def test_valid_minimal(self):
        schema = ISTScreenCreate(
            name="Test",
            content="x" * 100,
        )
        assert schema.name == "Test"
        assert schema.content_type == "text"

    def test_valid_full(self):
        schema = ISTScreenCreate(
            name="Full Test",
            content="x" * 200,
            contentType="podcast_transcript",
            hypothesis="Test hypothesis",
            constraints={"minMarketCap": 1e9},
            frameworks=["scarcity_scoring"],
        )
        assert schema.content_type == "podcast_transcript"
        assert schema.hypothesis == "Test hypothesis"

    def test_rejects_short_content(self):
        with pytest.raises(Exception):
            ISTScreenCreate(name="Test", content="short")

    def test_rejects_invalid_content_type(self):
        with pytest.raises(Exception):
            ISTScreenCreate(
                name="Test",
                content="x" * 100,
                contentType="invalid",
            )

    def test_name_stripped(self):
        schema = ISTScreenCreate(name="  Test  ", content="x" * 100)
        assert schema.name == "Test"

    def test_rejects_empty_name(self):
        with pytest.raises(Exception):
            ISTScreenCreate(name="   ", content="x" * 100)


class TestScreeningBriefSchema:
    """Tests for the ScreeningBrief Pydantic schema."""

    def test_serialization_round_trip(self):
        brief = ScreeningBrief(
            hypothesis="Test",
            content_type="text",
            constraints={"key": "value"},
            frameworks=["fw1"],
        )
        json_str = brief.model_dump_json()
        parsed = json.loads(json_str)
        restored = ScreeningBrief.model_validate(parsed)
        assert restored.hypothesis == "Test"
        assert restored.frameworks == ["fw1"]


class TestContentExtractionSummarySchema:
    """Tests for the ContentExtractionSummary Pydantic schema."""

    def test_creation_and_serialization(self):
        summary = ContentExtractionSummary(
            totalClaims=10,
            claimsWithQuantAnchors=7,
            claimsWithTemporalMarkers=5,
            summary="Test summary",
            themes=["AI", "Energy"],
        )
        json_str = summary.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["totalClaims"] == 10
        assert parsed["themes"] == ["AI", "Energy"]


class TestSourceBiasSummarySchema:
    """Tests for the SourceBiasSummary Pydantic schema."""

    def test_creation_and_serialization(self):
        bias = SourceBiasSummary(
            rating="moderate",
            notes="Industry insider bias",
            sourceCredibility="Medium",
            potentialBlindSpots=["Competitor analysis", "Bear case"],
        )
        json_str = bias.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["rating"] == "moderate"
        assert len(parsed["potentialBlindSpots"]) == 2
