"""Unit tests for IST Phase 4: Dialectic Scrutiny step handlers.

Tests cover:
- Optimist handler (mock Claude, verify DB record with side='OPTIMIST')
- Pessimist handler (mock Claude, verify side='PESSIMIST', verify it does NOT read optimist)
- Synthesis handler (mock Claude, verify it reads BOTH reviews)
- Data package isolation: optimist and pessimist receive identical data packages
- Edge cases: missing screen, missing reviews for synthesis
- Pydantic model validation
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, call

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.workflow import WorkflowRun, WorkflowStep
from app.models.ist import (
    ISTBottleneck,
    ISTClaim,
    ISTDemandModel,
    ISTDialecticReview,
    ISTEffectsChain,
    ISTEquityCandidate,
    ISTScreen,
    ISTValidation,
)
from app.services.ist.dialectic import (
    DialecticReviewContent,
    Disagreement,
    SynthesisContent,
    TierAdjustment,
    _build_phase_data_package,
    handle_dialectic_optimist,
    handle_dialectic_pessimist,
    handle_dialectic_synthesis,
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
        current_phase=3,
    )
    test_db.add(run)
    test_db.commit()
    test_db.refresh(run)
    return run


@pytest.fixture
def ist_screen(test_db, workflow_run):
    """Create an IST screen with source_bias and screening_brief populated."""
    screen = ISTScreen(
        workflow_run_id=workflow_run.id,
        name="GPU Scarcity Screen",
        status="SCANNING",
        content_type="podcast_transcript",
        raw_content="Transcript about AI infrastructure scarcity " * 20,
        screening_brief=json.dumps({
            "hypothesis": "AI compute demand creates multi-year scarcity",
            "content_type": "podcast_transcript",
        }),
        source_bias=json.dumps({
            "rating": "moderate",
            "notes": "Industry insider perspective",
            "sourceCredibility": "Medium-High",
            "potentialBlindSpots": ["Bear case underweighted", "Substitute technologies"],
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
            "source_citation": "Timestamp 12:30",
            "quantitative_anchor": "330,000 units per GW",
            "temporal_marker": "2025-2026",
            "confidence": 0.9,
            "is_validated": 1,
            "validation_verdict": "confirmed",
        },
        {
            "claim_text": "Power infrastructure bottlenecked by 5-year queues",
            "source_citation": "Timestamp 18:45",
            "quantitative_anchor": "5-year interconnection queues",
            "temporal_marker": "2025-2030",
            "confidence": 0.85,
            "is_validated": 1,
            "validation_verdict": "partially_confirmed",
        },
        {
            "claim_text": "Cooling demand growing 15% CAGR",
            "source_citation": "Timestamp 25:00",
            "quantitative_anchor": "15% CAGR",
            "temporal_marker": "2025-2028",
            "confidence": 0.8,
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
            temporal_marker="2025-2026",
        ),
        ISTBottleneck(
            screen_id=ist_screen.id,
            name="Power Infrastructure Bottleneck",
            phase=2,
            phase_label="Mid-term (18-36 months)",
            description="Grid interconnection queues",
            quantitative_evidence="5-year queues",
            resolution_trigger="Grid modernization policy",
        ),
    ]
    for bn in bns:
        test_db.add(bn)
    test_db.commit()
    for bn in bns:
        test_db.refresh(bn)
    return bns


@pytest.fixture
def sample_demand_models(test_db, ist_screen, sample_bottlenecks):
    """Create sample demand models."""
    dm = ISTDemandModel(
        screen_id=ist_screen.id,
        bottleneck_id=sample_bottlenecks[0].id,
        formula="GPU_demand = clusters * units_per_cluster",
        base_case=json.dumps({"demand": "1M units", "tam": "$50B"}),
        bull_case=json.dumps({"demand": "1.5M units", "tam": "$75B"}),
        bear_case=json.dumps({"demand": "600K units", "tam": "$30B"}),
    )
    test_db.add(dm)
    test_db.commit()
    test_db.refresh(dm)
    return [dm]


@pytest.fixture
def sample_validations(test_db, ist_screen, sample_claims):
    """Create sample validations."""
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


def _make_scarcity_score(overall: float) -> str:
    """Helper to create a scarcity_score JSON string."""
    return json.dumps({
        "overall": overall,
        "dimensions": {
            "supplyConstraint": overall,
            "demandVisibility": overall,
            "substitutionDifficulty": overall,
            "pricingPower": overall,
            "temporalUrgency": overall,
        },
    })


@pytest.fixture
def sample_candidates(test_db, ist_screen, sample_bottlenecks):
    """Create sample equity candidates."""
    cands = [
        ISTEquityCandidate(
            screen_id=ist_screen.id,
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            bottleneck_id=sample_bottlenecks[0].id,
            scarcity_score=_make_scarcity_score(4.6),
            moat_type="Scale + IP",
            moat_evidence="CUDA ecosystem lock-in",
            catalyst="GB300 launch",
            tier=1,
            tier_rationale="Tier 1: Scarcity >= 4.0, market cap, moat evidence",
            phase=1,
            conviction="HIGH",
            market_cap=2500000000000.0,
        ),
        ISTEquityCandidate(
            screen_id=ist_screen.id,
            ticker="EATON",
            company_name="Eaton Corporation",
            bottleneck_id=sample_bottlenecks[1].id,
            scarcity_score=_make_scarcity_score(3.5),
            moat_type="Installed base",
            moat_evidence="Grid infrastructure expertise",
            catalyst="IRA spending acceleration",
            tier=2,
            tier_rationale="Tier 2: Mid-range scarcity score",
            phase=2,
            conviction="MEDIUM",
            market_cap=120000000000.0,
        ),
    ]
    for c in cands:
        test_db.add(c)
    test_db.commit()
    for c in cands:
        test_db.refresh(c)
    return cands


@pytest.fixture
def sample_effects(test_db, ist_screen, sample_candidates):
    """Create sample effects chains."""
    effects = [
        ISTEffectsChain(
            screen_id=ist_screen.id,
            thesis="GPU scarcity drives pricing power",
            effect_order=1,
            effect_description="NVIDIA can charge premium prices",
            equity_candidate_id=sample_candidates[0].id,
        ),
        ISTEffectsChain(
            screen_id=ist_screen.id,
            thesis="Power demand cascades to grid infrastructure",
            effect_order=2,
            effect_description="Electrical equipment makers benefit",
            equity_candidate_id=sample_candidates[1].id,
        ),
    ]
    for e in effects:
        test_db.add(e)
    test_db.commit()
    for e in effects:
        test_db.refresh(e)
    return effects


def _mock_optimist_result():
    """Create a mock DialecticReviewContent for the optimist."""
    return DialecticReviewContent(
        narrative="## Bull Case\nThe scarcity thesis is compelling...",
        key_arguments=[
            "GPU supply constrained through 2026",
            "Power infrastructure creates multi-year tailwind",
            "No viable substitutes for CUDA ecosystem",
        ],
        tier_adjustments=[
            TierAdjustment(
                ticker="EATON",
                current_tier=2,
                proposed_tier=1,
                rationale="Power bottleneck severity underestimated by market",
            ),
        ],
        conviction_level="HIGH",
        risk_discount=0.2,
    )


def _mock_pessimist_result():
    """Create a mock DialecticReviewContent for the pessimist."""
    return DialecticReviewContent(
        narrative="## Bear Case\nSeveral flaws in the thesis...",
        key_arguments=[
            "Demand could decelerate if AI ROI disappoints",
            "Source bias: industry insider may overstate scarcity",
            "Alternative architectures (TPUs, custom silicon) gaining ground",
        ],
        tier_adjustments=[
            TierAdjustment(
                ticker="NVDA",
                current_tier=1,
                proposed_tier=2,
                rationale="Competition from custom silicon could erode monopoly rents",
            ),
        ],
        conviction_level="MEDIUM",
        risk_discount=0.6,
    )


def _mock_synthesis_result():
    """Create a mock SynthesisContent for the synthesis."""
    return SynthesisContent(
        narrative="## Synthesis\nAfter reconciling both perspectives...",
        disagreements=[
            Disagreement(
                topic="NVIDIA competitive moat durability",
                optimist_view="CUDA ecosystem creates multi-year lock-in",
                pessimist_view="Custom silicon erodes NVIDIA monopoly within 2 years",
                resolution="CUDA moat persists for training but inference share will fragment",
                impact_on_tiers="NVDA stays Tier 1 but with reduced conviction",
            ),
            Disagreement(
                topic="Power infrastructure timeline",
                optimist_view="5-year queues create durable bottleneck",
                pessimist_view="Policy changes could accelerate grid buildout",
                resolution="Queues are structural but some acceleration likely",
                impact_on_tiers="EATON stays Tier 2, upgrade not warranted yet",
            ),
        ],
        final_tier_adjustments=[],  # No tier changes after synthesis
        overall_conviction="MEDIUM",
        key_risks=[
            "AI ROI disappointment could reduce hyperscaler capex",
            "Custom silicon adoption faster than expected",
        ],
    )


# -- Optimist Handler Tests ---------------------------------------------------


class TestDialecticOptimist:
    """Tests for the dialectic_optimist step handler."""

    @pytest.mark.asyncio
    async def test_optimist_creates_review_record(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_demand_models,
        sample_validations, sample_candidates, sample_effects,
    ):
        """Optimist handler creates ISTDialecticReview with side='OPTIMIST'."""
        mock_result = _mock_optimist_result()

        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            original_close = test_db.close
            test_db.close = lambda: None
            try:
                result = await handle_dialectic_optimist(workflow_run.id)
            finally:
                test_db.close = original_close

        assert result is not None
        assert result["side"] == "OPTIMIST"
        assert result["convictionLevel"] == "HIGH"
        assert result["riskDiscount"] == 0.2
        assert result["keyArgumentCount"] == 3
        assert result["tierAdjustmentCount"] == 1

        # Verify DB record
        review = (
            test_db.query(ISTDialecticReview)
            .filter(
                ISTDialecticReview.screen_id == ist_screen.id,
                ISTDialecticReview.side == "OPTIMIST",
            )
            .first()
        )
        assert review is not None
        content = json.loads(review.content)
        assert content["conviction_level"] == "HIGH"
        assert len(content["key_arguments"]) == 3
        assert content["tier_adjustments"][0]["ticker"] == "EATON"

    @pytest.mark.asyncio
    async def test_optimist_updates_screen_status(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Optimist handler updates screen status to DIALECTIC."""
        mock_result = _mock_optimist_result()

        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            await handle_dialectic_optimist(workflow_run.id)

        test_db.refresh(ist_screen)
        assert ist_screen.status == "DIALECTIC"

    @pytest.mark.asyncio
    async def test_optimist_no_screen_raises(self, test_db):
        """Optimist handler raises if no screen found."""
        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No IST screen found"):
                await handle_dialectic_optimist(99999)

    @pytest.mark.asyncio
    async def test_optimist_does_not_read_pessimist(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Optimist handler does NOT query ISTDialecticReview table (INV-6)."""
        # Pre-create a pessimist review to ensure it exists
        pessimist_review = ISTDialecticReview(
            screen_id=ist_screen.id,
            side="PESSIMIST",
            content=_mock_pessimist_result().model_dump_json(),
        )
        test_db.add(pessimist_review)
        test_db.commit()

        mock_result = _mock_optimist_result()
        claude_calls = []

        async def capture_claude_call(**kwargs):
            claude_calls.append(kwargs)
            return mock_result

        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.call_claude",
            new_callable=AsyncMock,
            side_effect=capture_claude_call,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            await handle_dialectic_optimist(workflow_run.id)

        # Verify the user prompt sent to Claude does NOT contain pessimist content
        assert len(claude_calls) == 1
        user_prompt = claude_calls[0]["user_prompt"]
        assert "Bear Case" not in user_prompt
        assert "PESSIMIST" not in user_prompt
        assert "pessimist_review" not in user_prompt


# -- Pessimist Handler Tests --------------------------------------------------


class TestDialecticPessimist:
    """Tests for the dialectic_pessimist step handler."""

    @pytest.mark.asyncio
    async def test_pessimist_creates_review_record(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_demand_models,
        sample_validations, sample_candidates, sample_effects,
    ):
        """Pessimist handler creates ISTDialecticReview with side='PESSIMIST'."""
        mock_result = _mock_pessimist_result()

        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            original_close = test_db.close
            test_db.close = lambda: None
            try:
                result = await handle_dialectic_pessimist(workflow_run.id)
            finally:
                test_db.close = original_close

        assert result is not None
        assert result["side"] == "PESSIMIST"
        assert result["convictionLevel"] == "MEDIUM"
        assert result["riskDiscount"] == 0.6
        assert result["keyArgumentCount"] == 3
        assert result["tierAdjustmentCount"] == 1

        # Verify DB record
        review = (
            test_db.query(ISTDialecticReview)
            .filter(
                ISTDialecticReview.screen_id == ist_screen.id,
                ISTDialecticReview.side == "PESSIMIST",
            )
            .first()
        )
        assert review is not None
        content = json.loads(review.content)
        assert content["conviction_level"] == "MEDIUM"
        assert content["tier_adjustments"][0]["ticker"] == "NVDA"
        assert content["tier_adjustments"][0]["proposed_tier"] == 2  # Downgrade

    @pytest.mark.asyncio
    async def test_pessimist_does_not_read_optimist(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Pessimist handler does NOT read optimist output (INV-6)."""
        # Pre-create an optimist review to ensure it exists
        optimist_review = ISTDialecticReview(
            screen_id=ist_screen.id,
            side="OPTIMIST",
            content=_mock_optimist_result().model_dump_json(),
        )
        test_db.add(optimist_review)
        test_db.commit()

        mock_result = _mock_pessimist_result()
        claude_calls = []

        async def capture_claude_call(**kwargs):
            claude_calls.append(kwargs)
            return mock_result

        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.call_claude",
            new_callable=AsyncMock,
            side_effect=capture_claude_call,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            await handle_dialectic_pessimist(workflow_run.id)

        # Verify the user prompt sent to Claude does NOT contain optimist content
        assert len(claude_calls) == 1
        user_prompt = claude_calls[0]["user_prompt"]
        assert "Bull Case" not in user_prompt
        assert "OPTIMIST" not in user_prompt
        assert "optimist_review" not in user_prompt

    @pytest.mark.asyncio
    async def test_pessimist_no_screen_raises(self, test_db):
        """Pessimist handler raises if no screen found."""
        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No IST screen found"):
                await handle_dialectic_pessimist(99999)


# -- Data Package Isolation Tests ---------------------------------------------


class TestDataPackageIsolation:
    """Tests verifying that optimist and pessimist receive identical data packages."""

    @pytest.mark.asyncio
    async def test_identical_data_packages(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_demand_models,
        sample_validations, sample_candidates, sample_effects,
    ):
        """Optimist and pessimist call _build_phase_data_package with same args,
        producing identical data packages (INV-6: Dialectic Isolation)."""
        optimist_calls = []
        pessimist_calls = []

        async def capture_optimist(**kwargs):
            optimist_calls.append(kwargs)
            return _mock_optimist_result()

        async def capture_pessimist(**kwargs):
            pessimist_calls.append(kwargs)
            return _mock_pessimist_result()

        # Run optimist
        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.call_claude",
            new_callable=AsyncMock,
            side_effect=capture_optimist,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            await handle_dialectic_optimist(workflow_run.id)

        # Run pessimist
        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.call_claude",
            new_callable=AsyncMock,
            side_effect=capture_pessimist,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            await handle_dialectic_pessimist(workflow_run.id)

        # Both should have made exactly 1 Claude call each
        assert len(optimist_calls) == 1
        assert len(pessimist_calls) == 1

        # Extract the data package portion from each user_prompt
        # The data package is everything before the final instruction line
        opt_prompt = optimist_calls[0]["user_prompt"]
        pess_prompt = pessimist_calls[0]["user_prompt"]

        # Both contain the same XML-tagged sections
        for tag in [
            "<screen_metadata>", "</screen_metadata>",
            "<claims", "</claims>",
            "<bottlenecks", "</bottlenecks>",
            "<demand_models", "</demand_models>",
            "<validations", "</validations>",
            "<equity_candidates", "</equity_candidates>",
            "<effects_chains", "</effects_chains>",
        ]:
            assert tag in opt_prompt, f"Missing {tag} in optimist prompt"
            assert tag in pess_prompt, f"Missing {tag} in pessimist prompt"

        # Extract just the data package (everything up to the last XML closing tag)
        def extract_data_package(prompt):
            # Find end of </effects_chains> to get consistent data package
            idx = prompt.index("</effects_chains>") + len("</effects_chains>")
            return prompt[:idx]

        opt_data = extract_data_package(opt_prompt)
        pess_data = extract_data_package(pess_prompt)

        # Data packages must be IDENTICAL
        assert opt_data == pess_data, "Optimist and pessimist data packages differ!"

    def test_build_phase_data_package_content(
        self, test_db, ist_screen, workflow_run,
        sample_claims, sample_bottlenecks, sample_demand_models,
        sample_validations, sample_candidates, sample_effects,
    ):
        """Data package contains all Phase 1-3 data elements."""
        data_package = _build_phase_data_package(
            test_db, ist_screen.id, workflow_run.id
        )

        # Verify all sections are present
        assert "<screen_metadata>" in data_package
        assert "GPU Scarcity Screen" in data_package
        assert "podcast_transcript" in data_package
        assert "AI compute demand" in data_package  # hypothesis

        assert "<claims" in data_package
        assert "NVIDIA GB300 requires 330,000 units" in data_package
        assert "330,000 units per GW" in data_package  # quant anchor
        assert "2025-2026" in data_package  # temporal marker

        assert "<bottlenecks" in data_package
        assert "GPU Supply Scarcity" in data_package
        assert "Power Infrastructure Bottleneck" in data_package

        assert "<demand_models" in data_package
        assert "GPU_demand = clusters * units_per_cluster" in data_package

        assert "<validations" in data_package
        assert "confirmed" in data_package

        assert "<equity_candidates" in data_package
        assert "NVDA" in data_package
        assert "EATON" in data_package
        assert "Tier 1" in data_package

        assert "<effects_chains" in data_package
        assert "GPU scarcity drives pricing power" in data_package

    def test_build_phase_data_package_missing_screen_raises(
        self, test_db, workflow_run,
    ):
        """Data package builder raises on missing screen."""
        with pytest.raises(ValueError, match="No IST screen found"):
            _build_phase_data_package(test_db, 99999, workflow_run.id)


# -- Synthesis Handler Tests --------------------------------------------------


class TestDialecticSynthesis:
    """Tests for the dialectic_synthesis step handler."""

    @pytest.mark.asyncio
    async def test_synthesis_creates_review_record(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Synthesis handler creates ISTDialecticReview with side='SYNTHESIS'."""
        # Pre-create both optimist and pessimist reviews
        test_db.add(ISTDialecticReview(
            screen_id=ist_screen.id,
            side="OPTIMIST",
            content=_mock_optimist_result().model_dump_json(),
        ))
        test_db.add(ISTDialecticReview(
            screen_id=ist_screen.id,
            side="PESSIMIST",
            content=_mock_pessimist_result().model_dump_json(),
        ))
        test_db.commit()

        mock_result = _mock_synthesis_result()

        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            original_close = test_db.close
            test_db.close = lambda: None
            try:
                result = await handle_dialectic_synthesis(workflow_run.id)
            finally:
                test_db.close = original_close

        assert result is not None
        assert result["side"] == "SYNTHESIS"
        assert result["overallConviction"] == "MEDIUM"
        assert result["disagreementCount"] == 2
        assert result["finalTierAdjustmentCount"] == 0
        assert result["keyRiskCount"] == 2

        # Verify DB record
        review = (
            test_db.query(ISTDialecticReview)
            .filter(
                ISTDialecticReview.screen_id == ist_screen.id,
                ISTDialecticReview.side == "SYNTHESIS",
            )
            .first()
        )
        assert review is not None
        content = json.loads(review.content)
        assert content["overall_conviction"] == "MEDIUM"
        assert len(content["disagreements"]) == 2
        assert content["disagreements"][0]["topic"] == "NVIDIA competitive moat durability"

    @pytest.mark.asyncio
    async def test_synthesis_reads_both_reviews(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Synthesis handler reads BOTH optimist and pessimist reviews."""
        optimist_content = _mock_optimist_result().model_dump_json()
        pessimist_content = _mock_pessimist_result().model_dump_json()

        test_db.add(ISTDialecticReview(
            screen_id=ist_screen.id,
            side="OPTIMIST",
            content=optimist_content,
        ))
        test_db.add(ISTDialecticReview(
            screen_id=ist_screen.id,
            side="PESSIMIST",
            content=pessimist_content,
        ))
        test_db.commit()

        claude_calls = []

        async def capture_claude(**kwargs):
            claude_calls.append(kwargs)
            return _mock_synthesis_result()

        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.call_claude",
            new_callable=AsyncMock,
            side_effect=capture_claude,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            await handle_dialectic_synthesis(workflow_run.id)

        # Verify the user prompt contains BOTH reviews
        assert len(claude_calls) == 1
        user_prompt = claude_calls[0]["user_prompt"]
        assert "<optimist_review>" in user_prompt
        assert "</optimist_review>" in user_prompt
        assert "<pessimist_review>" in user_prompt
        assert "</pessimist_review>" in user_prompt
        # The actual review content should be embedded
        assert "conviction_level" in user_prompt

    @pytest.mark.asyncio
    async def test_synthesis_missing_optimist_raises(
        self, test_db, workflow_run, ist_screen, sample_claims, sample_bottlenecks,
    ):
        """Synthesis handler raises if optimist review is missing."""
        # Only create pessimist
        test_db.add(ISTDialecticReview(
            screen_id=ist_screen.id,
            side="PESSIMIST",
            content=_mock_pessimist_result().model_dump_json(),
        ))
        test_db.commit()

        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="OPTIMIST"):
                await handle_dialectic_synthesis(workflow_run.id)

    @pytest.mark.asyncio
    async def test_synthesis_missing_pessimist_raises(
        self, test_db, workflow_run, ist_screen, sample_claims, sample_bottlenecks,
    ):
        """Synthesis handler raises if pessimist review is missing."""
        # Only create optimist
        test_db.add(ISTDialecticReview(
            screen_id=ist_screen.id,
            side="OPTIMIST",
            content=_mock_optimist_result().model_dump_json(),
        ))
        test_db.commit()

        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="PESSIMIST"):
                await handle_dialectic_synthesis(workflow_run.id)

    @pytest.mark.asyncio
    async def test_synthesis_missing_both_raises(
        self, test_db, workflow_run, ist_screen, sample_claims, sample_bottlenecks,
    ):
        """Synthesis handler raises if both reviews are missing."""
        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="OPTIMIST"):
                await handle_dialectic_synthesis(workflow_run.id)

    @pytest.mark.asyncio
    async def test_synthesis_no_screen_raises(self, test_db):
        """Synthesis handler raises if no screen found."""
        with patch(
            "app.services.ist.dialectic.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.dialectic.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No IST screen found"):
                await handle_dialectic_synthesis(99999)


# -- Pydantic Model Tests -----------------------------------------------------


class TestPydanticModels:
    """Tests for the Pydantic response models used in dialectic analysis."""

    def test_tier_adjustment_valid(self):
        """TierAdjustment accepts valid tier values."""
        adj = TierAdjustment(
            ticker="NVDA",
            current_tier=2,
            proposed_tier=1,
            rationale="Strong bull case",
        )
        assert adj.ticker == "NVDA"
        assert adj.proposed_tier == 1

    def test_tier_adjustment_rejects_invalid_tier(self):
        """TierAdjustment rejects tier values outside 1-3."""
        with pytest.raises(Exception):
            TierAdjustment(
                ticker="NVDA",
                current_tier=1,
                proposed_tier=4,  # Invalid
                rationale="Bad",
            )

    def test_dialectic_review_content_valid(self):
        """DialecticReviewContent accepts valid data."""
        content = DialecticReviewContent(
            narrative="Analysis text",
            key_arguments=["Arg1", "Arg2", "Arg3"],
            tier_adjustments=[],
            conviction_level="HIGH",
            risk_discount=0.3,
        )
        assert content.conviction_level == "HIGH"
        assert content.risk_discount == 0.3

    def test_dialectic_review_content_rejects_invalid_discount(self):
        """DialecticReviewContent rejects risk_discount outside 0-1."""
        with pytest.raises(Exception):
            DialecticReviewContent(
                narrative="Analysis",
                key_arguments=["Arg1"],
                tier_adjustments=[],
                conviction_level="HIGH",
                risk_discount=1.5,  # Invalid
            )

    def test_synthesis_content_valid(self):
        """SynthesisContent accepts valid synthesis data."""
        content = SynthesisContent(
            narrative="Synthesis text",
            disagreements=[
                Disagreement(
                    topic="Test",
                    optimist_view="Bull",
                    pessimist_view="Bear",
                    resolution="Resolved",
                    impact_on_tiers="No change",
                ),
            ],
            final_tier_adjustments=[],
            overall_conviction="MEDIUM",
            key_risks=["Risk 1", "Risk 2"],
        )
        assert content.overall_conviction == "MEDIUM"
        assert len(content.disagreements) == 1
        assert len(content.key_risks) == 2

    def test_synthesis_content_serialization_roundtrip(self):
        """SynthesisContent serializes and deserializes correctly."""
        content = _mock_synthesis_result()
        json_str = content.model_dump_json()
        parsed = json.loads(json_str)
        restored = SynthesisContent.model_validate(parsed)
        assert restored.overall_conviction == content.overall_conviction
        assert len(restored.disagreements) == len(content.disagreements)
        assert restored.disagreements[0].topic == content.disagreements[0].topic

    def test_dialectic_review_content_serialization_roundtrip(self):
        """DialecticReviewContent serializes and deserializes correctly."""
        content = _mock_optimist_result()
        json_str = content.model_dump_json()
        parsed = json.loads(json_str)
        restored = DialecticReviewContent.model_validate(parsed)
        assert restored.conviction_level == content.conviction_level
        assert len(restored.key_arguments) == len(content.key_arguments)
        assert restored.tier_adjustments[0].ticker == content.tier_adjustments[0].ticker
