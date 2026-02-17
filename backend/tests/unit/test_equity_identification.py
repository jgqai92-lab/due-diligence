"""Unit tests for IST Phase 3: Equity Identification step handlers.

Tests cover:
- Equity scanning handler (mock Claude, verify DB records)
- Tier classification logic (deterministic -- Tier 1, 2, 3 cases)
- Effects analysis handler (mock Claude, verify DB records)
- Invariant checks (all pass + specific failures)
- Research sufficiency gate (pass + various fail scenarios)
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.workflow import WorkflowRun, WorkflowStep
from app.models.ist import (
    ISTBottleneck,
    ISTClaim,
    ISTEffectsChain,
    ISTEquityCandidate,
    ISTScreen,
    ISTValidation,
)
from app.services.ist.equity_identification import (
    EffectItem,
    EffectsResult,
    EquityCandidateItem,
    EquityScanResult,
    ScarcityDimensions,
    handle_effects_analysis,
    handle_equity_scanning,
    handle_invariant_check,
    handle_research_sufficiency_gate,
    handle_tier_classification,
    _get_overall_scarcity_score,
)


# -- Test DB setup ------------------------------------------------------------


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
        status="RUNNING",
        current_phase=2,
    )
    test_db.add(run)
    test_db.commit()
    test_db.refresh(run)
    return run


@pytest.fixture
def ist_screen(test_db, workflow_run):
    """Create an IST screen with source_bias populated."""
    screen = ISTScreen(
        workflow_run_id=workflow_run.id,
        name="Test Screen",
        status="ANALYZING",
        content_type="text",
        raw_content="Test content about GPU scarcity " * 20,
        source_bias=json.dumps({
            "rating": "moderate",
            "notes": "Industry analysis",
            "sourceCredibility": "Medium",
            "potentialBlindSpots": ["Bear case"],
        }),
    )
    test_db.add(screen)
    test_db.commit()
    test_db.refresh(screen)
    return screen


@pytest.fixture
def sample_claims(test_db, ist_screen):
    """Create sample claims for testing."""
    claims_data = [
        {
            "claim_text": "NVIDIA GB300 requires 330,000 units per GW cluster",
            "source_citation": "Section 1",
            "quantitative_anchor": "330,000 units per GW",
            "temporal_marker": "2025-2026",
            "confidence": 0.9,
        },
        {
            "claim_text": "Power infrastructure bottlenecked by 5-year queues",
            "source_citation": "Section 2",
            "quantitative_anchor": "5-year interconnection queues",
            "temporal_marker": "2025-2030",
            "confidence": 0.85,
        },
        {
            "claim_text": "Cooling demand growing 15% CAGR",
            "source_citation": "Section 3",
            "quantitative_anchor": "15% CAGR",
            "temporal_marker": "2025-2028",
            "confidence": 0.8,
        },
        {
            "claim_text": "AI infrastructure spending to reach $500B by 2027",
            "source_citation": "Section 4",
            "quantitative_anchor": "$500B",
            "temporal_marker": "2027",
            "confidence": 0.75,
        },
    ]
    claims = []
    for cd in claims_data:
        claim = ISTClaim(screen_id=ist_screen.id, **cd)
        test_db.add(claim)
        claims.append(claim)
    test_db.commit()
    for c in claims:
        test_db.refresh(c)
    return claims


@pytest.fixture
def sample_bottlenecks(test_db, ist_screen):
    """Create sample bottlenecks for testing."""
    bns = [
        ISTBottleneck(
            screen_id=ist_screen.id,
            name="GPU Supply Scarcity",
            phase=1,
            phase_label="Near-term (0-18 months)",
            description="NVIDIA production capacity constrained",
            quantitative_evidence="330,000 units per GW",
        ),
        ISTBottleneck(
            screen_id=ist_screen.id,
            name="Power Infrastructure Bottleneck",
            phase=2,
            phase_label="Mid-term (18-36 months)",
            description="Grid interconnection queues",
            quantitative_evidence="5-year queues",
        ),
    ]
    for bn in bns:
        test_db.add(bn)
    test_db.commit()
    for bn in bns:
        test_db.refresh(bn)
    return bns


@pytest.fixture
def sample_validations(test_db, ist_screen, sample_claims):
    """Create sample validations for testing."""
    vals = []
    for claim in sample_claims[:2]:
        val = ISTValidation(
            screen_id=ist_screen.id,
            claim_id=claim.id,
            verdict="confirmed",
            confidence=0.9,
            evidence="Confirmed via external source",
            sources=json.dumps([{"url": "https://example.com", "title": "Source"}]),
            search_queries=json.dumps(["test query"]),
        )
        test_db.add(val)
        vals.append(val)
    test_db.commit()
    for v in vals:
        test_db.refresh(v)
    return vals


def _make_scarcity_score(overall: float, dims: dict | None = None) -> str:
    """Helper to create a scarcity_score JSON string."""
    if dims is None:
        dims = {
            "supplyConstraint": overall,
            "demandVisibility": overall,
            "substitutionDifficulty": overall,
            "pricingPower": overall,
            "temporalUrgency": overall,
        }
    return json.dumps({"overall": overall, "dimensions": dims})


def _create_candidate(
    test_db,
    ist_screen,
    sample_bottlenecks,
    ticker="NVDA",
    company_name="NVIDIA Corporation",
    overall_score=4.5,
    tier=3,
    moat_evidence="Scale + IP moat",
    market_cap=2500000000000.0,
    conviction="HIGH",
    bottleneck_idx=0,
):
    """Helper to create a single equity candidate."""
    cand = ISTEquityCandidate(
        screen_id=ist_screen.id,
        ticker=ticker,
        company_name=company_name,
        bottleneck_id=sample_bottlenecks[bottleneck_idx].id if sample_bottlenecks else None,
        scarcity_score=_make_scarcity_score(overall_score),
        moat_type="Scale + IP",
        moat_evidence=moat_evidence,
        catalyst="Data center buildout",
        tier=tier,
        conviction=conviction,
        phase=sample_bottlenecks[bottleneck_idx].phase if sample_bottlenecks else None,
        market_cap=market_cap,
    )
    test_db.add(cand)
    test_db.commit()
    test_db.refresh(cand)
    return cand


# -- Equity Scanning Tests ----------------------------------------------------


class TestEquityScanning:
    """Tests for the equity_scanning step handler."""

    @pytest.mark.asyncio
    async def test_equity_scanning_creates_records(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks, sample_claims
    ):
        """Equity scanning creates ISTEquityCandidate records from Claude output."""
        mock_result = EquityScanResult(
            candidates=[
                EquityCandidateItem(
                    ticker="NVDA",
                    company_name="NVIDIA Corporation",
                    bottleneck_name="GPU Supply Scarcity",
                    scarcity_dimensions=ScarcityDimensions(
                        supply_constraint=5.0,
                        demand_visibility=4.5,
                        substitution_difficulty=4.0,
                        pricing_power=4.5,
                        temporal_urgency=5.0,
                    ),
                    moat_type="Scale + IP",
                    moat_evidence="CUDA ecosystem lock-in, TSMC priority allocation",
                    catalyst="GB300 launch",
                    conviction="HIGH",
                ),
                EquityCandidateItem(
                    ticker="AVGO",
                    company_name="Broadcom Inc.",
                    bottleneck_name="GPU Supply Scarcity",
                    scarcity_dimensions=ScarcityDimensions(
                        supply_constraint=3.5,
                        demand_visibility=4.0,
                        substitution_difficulty=3.0,
                        pricing_power=3.5,
                        temporal_urgency=3.0,
                    ),
                    moat_type="Custom silicon",
                    moat_evidence="Google TPU partnership",
                    catalyst="Custom AI chip ramp",
                    conviction="MEDIUM",
                ),
            ]
        )

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            original_close = test_db.close
            test_db.close = lambda: None
            try:
                result = await handle_equity_scanning(workflow_run.id)
            finally:
                test_db.close = original_close

        assert result is not None
        assert result["candidatesIdentified"] == 2
        assert result["candidatesStored"] == 2

        # Verify DB records
        candidates = (
            test_db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == ist_screen.id)
            .order_by(ISTEquityCandidate.id)
            .all()
        )
        assert len(candidates) == 2
        assert candidates[0].ticker == "NVDA"
        assert candidates[0].company_name == "NVIDIA Corporation"
        assert candidates[0].bottleneck_id == sample_bottlenecks[0].id
        assert candidates[0].conviction == "HIGH"
        assert candidates[0].tier == 3  # Default before classification

        # Verify scarcity score JSON structure
        score = json.loads(candidates[0].scarcity_score)
        assert score["overall"] == 4.6  # mean of 5.0, 4.5, 4.0, 4.5, 5.0
        assert score["dimensions"]["supplyConstraint"] == 5.0
        assert score["dimensions"]["demandVisibility"] == 4.5

        assert candidates[1].ticker == "AVGO"
        assert candidates[1].conviction == "MEDIUM"

    @pytest.mark.asyncio
    async def test_equity_scanning_skips_unknown_bottleneck(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks, sample_claims
    ):
        """Equity scanning skips candidates referencing unknown bottleneck names."""
        mock_result = EquityScanResult(
            candidates=[
                EquityCandidateItem(
                    ticker="FAKE",
                    company_name="Fake Corp",
                    bottleneck_name="Nonexistent Bottleneck",
                    scarcity_dimensions=ScarcityDimensions(
                        supply_constraint=3.0,
                        demand_visibility=3.0,
                        substitution_difficulty=3.0,
                        pricing_power=3.0,
                        temporal_urgency=3.0,
                    ),
                    conviction="LOW",
                ),
            ]
        )

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_equity_scanning(workflow_run.id)

        assert result["candidatesStored"] == 0

        count = (
            test_db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == ist_screen.id)
            .count()
        )
        assert count == 0

    @pytest.mark.asyncio
    async def test_equity_scanning_no_screen_raises(self, test_db):
        """Equity scanning raises if no screen found."""
        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No IST screen found"):
                await handle_equity_scanning(99999)

    @pytest.mark.asyncio
    async def test_equity_scanning_no_bottlenecks_raises(
        self, test_db, workflow_run, ist_screen
    ):
        """Equity scanning raises if no bottlenecks found."""
        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No bottlenecks found"):
                await handle_equity_scanning(workflow_run.id)

    @pytest.mark.asyncio
    async def test_equity_scanning_updates_screen_status(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks, sample_claims
    ):
        """Equity scanning updates screen status to SCANNING."""
        mock_result = EquityScanResult(candidates=[])

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            await handle_equity_scanning(workflow_run.id)

        test_db.refresh(ist_screen)
        assert ist_screen.status == "SCANNING"


# -- Tier Classification Tests ------------------------------------------------


class TestTierClassification:
    """Tests for the tier_classification step handler (deterministic logic)."""

    @pytest.mark.asyncio
    async def test_tier1_classification(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Candidates with scarcity >= 4.0, market_cap, and moat_evidence get Tier 1."""
        _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="NVDA", overall_score=4.5,
            market_cap=2500000000000.0, moat_evidence="CUDA ecosystem",
        )

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_tier_classification(workflow_run.id)

        assert result["tierBreakdown"]["tier1"] == 1
        assert result["tierBreakdown"]["tier2"] == 0
        assert result["tierBreakdown"]["tier3"] == 0

        cand = (
            test_db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == ist_screen.id)
            .first()
        )
        assert cand.tier == 1
        assert "Tier 1" in cand.tier_rationale

    @pytest.mark.asyncio
    async def test_tier2_mid_scarcity(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Candidates with scarcity 3.0-4.0 get Tier 2."""
        _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="AVGO", overall_score=3.5,
            market_cap=800000000000.0, moat_evidence="Custom silicon",
        )

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_tier_classification(workflow_run.id)

        assert result["tierBreakdown"]["tier2"] == 1
        cand = (
            test_db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == ist_screen.id)
            .first()
        )
        assert cand.tier == 2
        assert "Tier 2" in cand.tier_rationale

    @pytest.mark.asyncio
    async def test_tier2_high_scarcity_no_market_cap(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Candidates with scarcity >= 4.0 but no market_cap get Tier 2."""
        _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="SMCI", overall_score=4.2,
            market_cap=None, moat_evidence="Server integration",
        )

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_tier_classification(workflow_run.id)

        assert result["tierBreakdown"]["tier2"] == 1
        cand = (
            test_db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == ist_screen.id)
            .first()
        )
        assert cand.tier == 2
        assert "market cap missing" in cand.tier_rationale

    @pytest.mark.asyncio
    async def test_tier2_high_scarcity_no_moat(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Candidates with scarcity >= 4.0 but no moat_evidence get Tier 2."""
        _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="SMCI", overall_score=4.2,
            market_cap=50000000000.0, moat_evidence=None,
        )

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_tier_classification(workflow_run.id)

        assert result["tierBreakdown"]["tier2"] == 1
        cand = (
            test_db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == ist_screen.id)
            .first()
        )
        assert cand.tier == 2
        assert "moat evidence missing" in cand.tier_rationale

    @pytest.mark.asyncio
    async def test_tier3_low_scarcity(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Candidates with scarcity < 3.0 get Tier 3."""
        _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="INTC", overall_score=2.5,
            market_cap=100000000000.0, moat_evidence="Legacy x86",
        )

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_tier_classification(workflow_run.id)

        assert result["tierBreakdown"]["tier3"] == 1
        cand = (
            test_db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == ist_screen.id)
            .first()
        )
        assert cand.tier == 3
        assert "Tier 3" in cand.tier_rationale

    @pytest.mark.asyncio
    async def test_tier_classification_multiple_candidates(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Tier classification correctly handles a mix of candidates."""
        # Tier 1: high scarcity + market cap + moat
        _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="NVDA", overall_score=4.5,
            market_cap=2500000000000.0, moat_evidence="CUDA",
        )
        # Tier 2: mid scarcity
        _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="AVGO", overall_score=3.5,
            market_cap=800000000000.0, moat_evidence="Custom silicon",
            bottleneck_idx=1,
        )
        # Tier 3: low scarcity
        _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="INTC", overall_score=2.0,
            market_cap=100000000000.0, moat_evidence="x86",
            bottleneck_idx=1,
        )

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_tier_classification(workflow_run.id)

        assert result["candidatesClassified"] == 3
        assert result["tierBreakdown"]["tier1"] == 1
        assert result["tierBreakdown"]["tier2"] == 1
        assert result["tierBreakdown"]["tier3"] == 1

    @pytest.mark.asyncio
    async def test_tier_classification_sets_phase_from_bottleneck(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Tier classification sets candidate.phase from bottleneck.phase."""
        _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="NVDA", overall_score=4.5,
            market_cap=2500000000000.0, moat_evidence="CUDA",
            bottleneck_idx=1,  # phase=2
        )

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            await handle_tier_classification(workflow_run.id)

        cand = (
            test_db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == ist_screen.id)
            .first()
        )
        assert cand.phase == 2  # From bottleneck phase

    @pytest.mark.asyncio
    async def test_tier_classification_no_candidates_raises(
        self, test_db, workflow_run, ist_screen
    ):
        """Tier classification raises if no candidates found."""
        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No equity candidates found"):
                await handle_tier_classification(workflow_run.id)


# -- Effects Analysis Tests ---------------------------------------------------


class TestEffectsAnalysis:
    """Tests for the effects_analysis step handler."""

    @pytest.mark.asyncio
    async def test_effects_analysis_creates_records(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Effects analysis creates ISTEffectsChain records from Claude output."""
        # Create a candidate to link to
        cand = _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="NVDA", overall_score=4.5,
        )

        mock_result = EffectsResult(
            effects=[
                EffectItem(
                    thesis="GPU scarcity drives pricing power",
                    order=1,
                    effect_description="NVIDIA can charge premium prices",
                    equity_ticker="NVDA",
                ),
                EffectItem(
                    thesis="GPU scarcity cascades to cloud pricing",
                    order=2,
                    effect_description="Cloud providers pass through GPU costs",
                    equity_ticker=None,
                ),
                EffectItem(
                    thesis="Long-term AI model efficiency drives new architectures",
                    order=3,
                    effect_description="Custom silicon alternatives gain share",
                    equity_ticker=None,
                ),
            ]
        )

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_effects_analysis(workflow_run.id)

        assert result is not None
        assert result["effectsMapped"] == 3
        assert result["orderBreakdown"] == {1: 1, 2: 1, 3: 1}

        # Verify DB records
        effects = (
            test_db.query(ISTEffectsChain)
            .filter(ISTEffectsChain.screen_id == ist_screen.id)
            .order_by(ISTEffectsChain.id)
            .all()
        )
        assert len(effects) == 3
        assert effects[0].thesis == "GPU scarcity drives pricing power"
        assert effects[0].effect_order == 1
        assert effects[0].equity_candidate_id == cand.id  # Linked via ticker
        assert effects[1].equity_candidate_id is None  # Not linked
        assert effects[2].effect_order == 3

    @pytest.mark.asyncio
    async def test_effects_analysis_handles_unknown_ticker(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Effects analysis stores effects even when ticker is unknown (no FK)."""
        mock_result = EffectsResult(
            effects=[
                EffectItem(
                    thesis="Unknown company effect",
                    order=1,
                    effect_description="Some effect",
                    equity_ticker="UNKNOWN",
                ),
            ]
        )

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_effects_analysis(workflow_run.id)

        assert result["effectsMapped"] == 1

        effect = (
            test_db.query(ISTEffectsChain)
            .filter(ISTEffectsChain.screen_id == ist_screen.id)
            .first()
        )
        assert effect.equity_candidate_id is None  # Unknown ticker, no FK

    @pytest.mark.asyncio
    async def test_effects_analysis_no_bottlenecks_raises(
        self, test_db, workflow_run, ist_screen
    ):
        """Effects analysis raises if no bottlenecks found."""
        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No bottlenecks found"):
                await handle_effects_analysis(workflow_run.id)


# -- Invariant Check Tests ----------------------------------------------------


class TestInvariantCheck:
    """Tests for the invariant_check step handler."""

    @pytest.mark.asyncio
    async def test_all_invariants_pass(
        self, test_db, workflow_run, ist_screen, sample_claims, sample_bottlenecks
    ):
        """All invariants pass when data is complete."""
        # Create candidates with tier rationale and bottleneck linkage
        _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="NVDA", overall_score=4.5,
        )
        cand = (
            test_db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == ist_screen.id)
            .first()
        )
        cand.tier_rationale = "Tier 1: High scarcity"
        test_db.commit()

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_invariant_check(workflow_run.id)

        assert result["allPassed"] is True
        assert result["failCount"] == 0
        assert result["passCount"] == 5  # INV-1 through INV-5
        assert result["skipCount"] == 3  # INV-6, 7, 8

        # Verify individual invariants
        invariants = {inv["id"]: inv for inv in result["invariants"]}
        assert invariants["INV-1"]["status"] == "PASS"
        assert invariants["INV-2"]["status"] == "PASS"
        assert invariants["INV-3"]["status"] == "PASS"
        assert invariants["INV-4"]["status"] == "PASS"
        assert invariants["INV-5"]["status"] == "PASS"
        assert invariants["INV-6"]["status"] == "SKIPPED"
        assert invariants["INV-7"]["status"] == "SKIPPED"
        assert invariants["INV-8"]["status"] == "SKIPPED"

    @pytest.mark.asyncio
    async def test_inv2_fails_insufficient_quant_anchors(
        self, test_db, workflow_run, ist_screen
    ):
        """INV-2 fails when < 50% of claims have quantitative anchors."""
        # Create 4 claims, only 1 with quant anchor (25%)
        for i in range(4):
            test_db.add(ISTClaim(
                screen_id=ist_screen.id,
                claim_text=f"Claim {i}",
                source_citation=f"Sec {i}",
                quantitative_anchor=f"100 units" if i == 0 else None,
                temporal_marker="2025" if i == 0 else None,
                confidence=0.8,
            ))
        test_db.commit()

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_invariant_check(workflow_run.id)

        invariants = {inv["id"]: inv for inv in result["invariants"]}
        assert invariants["INV-2"]["status"] == "FAIL"
        assert "25%" in invariants["INV-2"]["details"]

    @pytest.mark.asyncio
    async def test_inv4_fails_orphan_equities(
        self, test_db, workflow_run, ist_screen, sample_claims
    ):
        """INV-4 fails when candidates lack bottleneck linkage."""
        # Create a candidate without bottleneck
        cand = ISTEquityCandidate(
            screen_id=ist_screen.id,
            ticker="ORPHAN",
            company_name="Orphan Corp",
            bottleneck_id=None,  # No bottleneck link
            scarcity_score=_make_scarcity_score(3.0),
            tier=3,
            tier_rationale="Tier 3",
            conviction="LOW",
        )
        test_db.add(cand)
        test_db.commit()

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_invariant_check(workflow_run.id)

        invariants = {inv["id"]: inv for inv in result["invariants"]}
        assert invariants["INV-4"]["status"] == "FAIL"
        assert "1/1" in invariants["INV-4"]["details"]

    @pytest.mark.asyncio
    async def test_inv5_fails_missing_tier_rationale(
        self, test_db, workflow_run, ist_screen, sample_claims, sample_bottlenecks
    ):
        """INV-5 fails when candidates lack tier rationale."""
        cand = _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="NORTNL", overall_score=3.5,
        )
        cand.tier_rationale = None  # Missing rationale
        test_db.commit()

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_invariant_check(workflow_run.id)

        invariants = {inv["id"]: inv for inv in result["invariants"]}
        assert invariants["INV-5"]["status"] == "FAIL"

    @pytest.mark.asyncio
    async def test_invariant_check_does_not_fail_workflow(
        self, test_db, workflow_run, ist_screen
    ):
        """Invariant check does NOT raise -- just records results."""
        # Empty screen with no claims/candidates -- multiple invariants will fail
        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_invariant_check(workflow_run.id)

        # Should NOT raise -- just returns failures
        assert result is not None
        assert result["allPassed"] is False
        assert result["failCount"] > 0


# -- Research Sufficiency Gate Tests ------------------------------------------


class TestResearchSufficiencyGate:
    """Tests for the research_sufficiency_gate step handler."""

    @pytest.mark.asyncio
    async def test_gate_passes_when_all_criteria_met(
        self, test_db, workflow_run, ist_screen, sample_claims,
        sample_bottlenecks, sample_validations
    ):
        """Gate passes when all 4 criteria are met."""
        _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="NVDA", overall_score=4.5,
        )

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ) as mock_sse:
            test_db.close = lambda: None
            result = await handle_research_sufficiency_gate(workflow_run.id)

        assert result is not None
        assert result["gateResult"] == "PASSED"
        assert result["candidateCount"] == 1
        assert result["allHaveScarcityScores"] is True
        assert result["allHaveTiers"] is True
        assert result["validationCount"] >= 1

        # Verify gate_passed SSE event
        sse_calls = [
            call for call in mock_sse.call_args_list
            if call[0][1] == "gate_passed"
        ]
        assert len(sse_calls) == 1

    @pytest.mark.asyncio
    async def test_gate_fails_no_candidates(
        self, test_db, workflow_run, ist_screen, sample_validations
    ):
        """Gate fails when no equity candidates identified."""
        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No equity candidates"):
                await handle_research_sufficiency_gate(workflow_run.id)

    @pytest.mark.asyncio
    async def test_gate_fails_missing_scarcity_scores(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks,
        sample_claims, sample_validations
    ):
        """Gate fails when candidates lack scarcity scores."""
        cand = _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="NVDA", overall_score=4.5,
        )
        cand.scarcity_score = ""  # Empty
        test_db.commit()

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="missing scarcity scores"):
                await handle_research_sufficiency_gate(workflow_run.id)

    @pytest.mark.asyncio
    async def test_gate_fails_no_validations(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Gate fails when no bottleneck validations found."""
        _create_candidate(
            test_db, ist_screen, sample_bottlenecks,
            ticker="NVDA", overall_score=4.5,
        )

        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No bottleneck validations"):
                await handle_research_sufficiency_gate(workflow_run.id)

    @pytest.mark.asyncio
    async def test_gate_fails_with_multiple_deficiencies(
        self, test_db, workflow_run, ist_screen
    ):
        """Gate failure message includes all deficiencies."""
        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError) as exc_info:
                await handle_research_sufficiency_gate(workflow_run.id)

            error_msg = str(exc_info.value)
            assert "No equity candidates" in error_msg
            assert "No bottleneck validations" in error_msg

    @pytest.mark.asyncio
    async def test_gate_emits_gate_failed_event(
        self, test_db, workflow_run, ist_screen
    ):
        """Gate emits gate_failed SSE event on failure."""
        with patch(
            "app.services.ist.equity_identification.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.equity_identification.emit_sse_event",
            new_callable=AsyncMock,
        ) as mock_sse:
            test_db.close = lambda: None
            with pytest.raises(ValueError):
                await handle_research_sufficiency_gate(workflow_run.id)

        sse_calls = [
            call for call in mock_sse.call_args_list
            if call[0][1] == "gate_failed"
        ]
        assert len(sse_calls) == 1


# -- Utility Function Tests ---------------------------------------------------


class TestUtilityFunctions:
    """Tests for internal utility functions."""

    def test_get_overall_scarcity_score_valid(self):
        """Parses valid scarcity score JSON."""
        score_json = json.dumps({"overall": 4.5, "dimensions": {}})
        assert _get_overall_scarcity_score(score_json) == 4.5

    def test_get_overall_scarcity_score_none(self):
        """Returns 0.0 for None input."""
        assert _get_overall_scarcity_score(None) == 0.0

    def test_get_overall_scarcity_score_empty(self):
        """Returns 0.0 for empty string."""
        assert _get_overall_scarcity_score("") == 0.0

    def test_get_overall_scarcity_score_invalid_json(self):
        """Returns 0.0 for invalid JSON."""
        assert _get_overall_scarcity_score("not json") == 0.0

    def test_get_overall_scarcity_score_missing_overall(self):
        """Returns 0.0 when 'overall' key is missing."""
        score_json = json.dumps({"dimensions": {}})
        assert _get_overall_scarcity_score(score_json) == 0.0


# -- Pydantic Model Tests -----------------------------------------------------


class TestPydanticModels:
    """Tests for the Pydantic response models used in equity identification."""

    def test_scarcity_dimensions_valid(self):
        """ScarcityDimensions accepts valid scores."""
        dims = ScarcityDimensions(
            supply_constraint=5.0,
            demand_visibility=4.0,
            substitution_difficulty=3.0,
            pricing_power=2.0,
            temporal_urgency=1.0,
        )
        assert dims.supply_constraint == 5.0
        assert dims.temporal_urgency == 1.0

    def test_scarcity_dimensions_rejects_out_of_range(self):
        """ScarcityDimensions rejects scores outside 1-5."""
        with pytest.raises(Exception):
            ScarcityDimensions(
                supply_constraint=6.0,  # Invalid
                demand_visibility=4.0,
                substitution_difficulty=3.0,
                pricing_power=2.0,
                temporal_urgency=1.0,
            )

    def test_scarcity_dimensions_rejects_zero(self):
        """ScarcityDimensions rejects scores below 1."""
        with pytest.raises(Exception):
            ScarcityDimensions(
                supply_constraint=0.0,  # Invalid
                demand_visibility=4.0,
                substitution_difficulty=3.0,
                pricing_power=2.0,
                temporal_urgency=1.0,
            )

    def test_equity_scan_result_serialization(self):
        """EquityScanResult serializes and deserializes correctly."""
        result = EquityScanResult(
            candidates=[
                EquityCandidateItem(
                    ticker="NVDA",
                    company_name="NVIDIA Corporation",
                    bottleneck_name="GPU Scarcity",
                    scarcity_dimensions=ScarcityDimensions(
                        supply_constraint=5.0,
                        demand_visibility=4.5,
                        substitution_difficulty=4.0,
                        pricing_power=4.5,
                        temporal_urgency=5.0,
                    ),
                    moat_type="Scale + IP",
                    moat_evidence="CUDA ecosystem",
                    catalyst="GB300 launch",
                    conviction="HIGH",
                ),
            ]
        )
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        assert len(parsed["candidates"]) == 1
        assert parsed["candidates"][0]["ticker"] == "NVDA"

        restored = EquityScanResult.model_validate(parsed)
        assert restored.candidates[0].ticker == "NVDA"

    def test_effects_result_serialization(self):
        """EffectsResult serializes and deserializes correctly."""
        result = EffectsResult(
            effects=[
                EffectItem(
                    thesis="Test thesis",
                    order=1,
                    effect_description="Test effect",
                    equity_ticker="NVDA",
                ),
            ]
        )
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["effects"][0]["order"] == 1

    def test_effect_item_rejects_invalid_order(self):
        """EffectItem rejects order outside 1-3."""
        with pytest.raises(Exception):
            EffectItem(
                thesis="Bad order",
                order=4,  # Invalid
                effect_description="Test",
            )
