"""Unit tests for IST Phase 5: Final Synthesis step handlers.

Tests cover:
- Master screen handler (mock Claude, verify ranked equities + invariant compliance)
- Rotation strategy handler (mock Claude, verify phase allocations)
- Catalyst calendar handler (mock Claude, verify catalyst list)
- Stress tests handler (mock Claude, verify framework + name tests)
- Report generation handler (mock call_claude_raw, verify markdown content)
- Screen coherence gate (pass + fail scenarios: missing report, report too short,
  missing Tier 1 ticker, missing bottleneck name)
- Screen certification (updates screen fields, generates handoff)
- Edge cases: missing screen raises ValueError
- Pydantic model validation for all new models
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
    ISTCatalystCalendar,
    ISTClaim,
    ISTDemandModel,
    ISTDialecticReview,
    ISTEffectsChain,
    ISTEquityCandidate,
    ISTMasterScreen,
    ISTReport,
    ISTRotationStrategy,
    ISTScreen,
    ISTStressTest,
    ISTValidation,
)
from app.services.ist.final_synthesis import (
    CONTENT_TYPE_THRESHOLDS,
    CatalystCalendarResult,
    CatalystEvent,
    FrameworkTest,
    MasterScreenResult,
    NameTest,
    PhaseAllocation,
    RankedEquity,
    RiskLimit,
    RotationStrategyResult,
    RotationTrigger,
    StressTestResult,
    SurvivalScore,
    _bottleneck_name_in_report,
    _build_full_data_package,
    _run_invariant_checks,
    get_thresholds,
    handle_catalyst_calendar,
    handle_hfrt_handoff_generation,
    handle_master_screen,
    handle_report_generation,
    handle_rotation_strategy,
    handle_screen_certification,
    handle_screen_coherence_gate,
    handle_stress_tests,
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
        current_phase=4,
    )
    test_db.add(run)
    test_db.commit()
    test_db.refresh(run)
    return run


@pytest.fixture
def ist_screen(test_db, workflow_run):
    """Create an IST screen with populated fields."""
    screen = ISTScreen(
        workflow_run_id=workflow_run.id,
        name="GPU Scarcity Screen",
        status="DIALECTIC",
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
            "potentialBlindSpots": ["Bear case underweighted"],
        }),
    )
    test_db.add(screen)
    test_db.commit()
    test_db.refresh(screen)
    return screen


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
def sample_claims(test_db, ist_screen):
    """Create sample claims."""
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
    """Create sample bottlenecks."""
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
def sample_dialectic_reviews(test_db, ist_screen):
    """Create sample dialectic reviews."""
    reviews = [
        ISTDialecticReview(
            screen_id=ist_screen.id,
            side="OPTIMIST",
            content=json.dumps({"narrative": "Bull case", "conviction_level": "HIGH"}),
        ),
        ISTDialecticReview(
            screen_id=ist_screen.id,
            side="PESSIMIST",
            content=json.dumps({"narrative": "Bear case", "conviction_level": "MEDIUM"}),
        ),
        ISTDialecticReview(
            screen_id=ist_screen.id,
            side="SYNTHESIS",
            content=json.dumps({
                "narrative": "Synthesis",
                "overall_conviction": "MEDIUM",
                "final_tier_adjustments": [],
            }),
        ),
    ]
    for r in reviews:
        test_db.add(r)
    test_db.commit()
    return reviews


# -- Mock result factories ---------------------------------------------------


def _mock_master_screen_result():
    return MasterScreenResult(
        ranked_equities=[
            RankedEquity(
                rank=1,
                ticker="NVDA",
                company_name="NVIDIA Corporation",
                tier=1,
                scarcity_score=4.6,
                conviction_score=92,
                pillar="GPU Supply Scarcity",
                catalyst="GB300 launch",
            ),
            RankedEquity(
                rank=2,
                ticker="EATON",
                company_name="Eaton Corporation",
                tier=2,
                scarcity_score=3.5,
                conviction_score=55,
                pillar="Power Infrastructure Bottleneck",
                catalyst="IRA spending acceleration",
            ),
        ]
    )


def _mock_rotation_strategy_result():
    return RotationStrategyResult(
        phase_allocations=[
            PhaseAllocation(
                phase=1,
                phase_label="Near-term (0-18 months)",
                allocation_pct=60,
                tickers=["NVDA"],
                rationale="GPU scarcity is immediate and most acute",
            ),
            PhaseAllocation(
                phase=2,
                phase_label="Mid-term (18-36 months)",
                allocation_pct=40,
                tickers=["EATON"],
                rationale="Power bottleneck builds over time",
            ),
        ],
        rotation_triggers=[
            RotationTrigger(
                trigger_name="GPU Supply Normalization",
                description="NVIDIA production catches up with demand",
                action="Rotate out of NVDA, increase EATON allocation",
                affected_tickers=["NVDA", "EATON"],
            ),
        ],
        risk_limits=[
            RiskLimit(
                limit_name="Single Name Concentration",
                limit_value="25% max per name",
                rationale="Prevent over-concentration in any single equity",
            ),
        ],
    )


def _mock_catalyst_calendar_result():
    return CatalystCalendarResult(
        catalysts=[
            CatalystEvent(
                date="Q2 2025",
                ticker="NVDA",
                event="GB300 production ramp",
                impact="Positive",
                pillar="GPU Supply Scarcity",
            ),
            CatalystEvent(
                date="H2 2025",
                ticker="EATON",
                event="IRA infrastructure spending acceleration",
                impact="Positive",
                pillar="Power Infrastructure Bottleneck",
            ),
        ]
    )


def _mock_stress_test_result():
    return StressTestResult(
        framework_tests=[
            FrameworkTest(
                scenario="Demand Collapse",
                description="AI capex falls 40% as ROI disappoints",
                impact_assessment="Thesis fundamentally impaired",
                severity="HIGH",
                affected_pillars=["GPU Supply Scarcity", "Power Infrastructure Bottleneck"],
            ),
        ],
        name_tests=[
            NameTest(
                ticker="NVDA",
                scenario="Custom silicon gains 30% share",
                impact="Revenue growth decelerates to 15%",
                survival_probability=0.65,
            ),
            NameTest(
                ticker="EATON",
                scenario="Grid modernization stalls",
                impact="Order backlog growth flattens",
                survival_probability=0.70,
            ),
        ],
        survival_scores=[
            SurvivalScore(
                ticker="NVDA",
                overall_survival=0.65,
                weakest_scenario="Custom silicon gains 30% share",
            ),
            SurvivalScore(
                ticker="EATON",
                overall_survival=0.70,
                weakest_scenario="Grid modernization stalls",
            ),
        ],
    )


def _mock_report_content():
    """Generate a mock report that passes coherence checks (>= 1000 words)."""
    return (
        "# Investment Thesis Report: GPU Scarcity Screen\n\n"
        "## Executive Summary\n\n"
        "The AI infrastructure buildout creates a multi-year scarcity cycle with "
        "investable opportunities in GPU supply and power infrastructure. "
        "NVDA and EATON represent Tier 1 and Tier 2 opportunities respectively. "
        "The core investment insight centers on a structural supply-demand imbalance "
        "that persists through 2026 for GPU compute and through 2030 for power "
        "infrastructure. Market consensus underestimates the duration and severity "
        "of these bottlenecks, creating a time-arbitrage opportunity for investors "
        "who recognize the multi-year nature of the scarcity cycle. The dialectic "
        "scrutiny process confirmed the thesis with MEDIUM overall conviction after "
        "weighing both bull and bear perspectives. Key risks include AI ROI "
        "disappointment reducing hyperscaler capex and custom silicon adoption "
        "fragmenting NVIDIA's market share faster than expected.\n\n"
        "| Ticker | Company | Tier | Scarcity | Conviction |\n"
        "|--------|---------|------|----------|------------|\n"
        "| NVDA | NVIDIA Corporation | 1 | 4.6 | HIGH |\n"
        "| EATON | Eaton Corporation | 2 | 3.5 | MEDIUM |\n\n"
        "## Pillar-by-Pillar Analysis\n\n"
        "### GPU Supply Scarcity\n\n"
        "NVIDIA's GB300 GPU production capacity remains severely constrained through 2026. "
        "The 330,000 units per GW cluster requirement creates a structural bottleneck that "
        "cannot be resolved quickly. NVDA benefits directly from this scarcity through "
        "exceptional pricing power and market dominance. The CUDA ecosystem creates a "
        "formidable competitive moat that locks in customers for training workloads, though "
        "inference workloads may see more competition from custom silicon alternatives. "
        "The quantitative evidence supporting this bottleneck includes the 330,000 GPU units "
        "required per gigawatt-scale cluster, with demand from major hyperscalers continuing "
        "to accelerate. Production capacity constraints are fundamentally tied to advanced "
        "semiconductor packaging technology, which requires years of investment to scale. "
        "The temporal marker for this bottleneck indicates maximum severity in 2025-2026, "
        "with gradual easing expected only as next-generation production lines come online. "
        "Multiple validated claims support the severity assessment, with confirmed evidence "
        "from industry sources and partially confirmed evidence from supply chain analysis. "
        "The bull case argues that scarcity persists longer than consensus expects due to "
        "compounding demand from AI model scaling, while the bear case notes that custom "
        "silicon alternatives from Google, Amazon, and Microsoft could erode NVIDIA's "
        "monopoly within two to three years. The synthesis concluded that CUDA's moat "
        "persists for training workloads but inference market share will fragment over time.\n\n"
        "> Stress test: Custom silicon scenario shows 65% thesis survival probability. "
        "This represents the weakest scenario for NVDA, as rapid custom silicon adoption "
        "could reduce the company's pricing power and market dominance.\n\n"
        "### Power Infrastructure Bottleneck\n\n"
        "Grid interconnection queues of 5 years create a durable bottleneck for data center "
        "expansion. EATON is positioned to benefit from electrical infrastructure spending "
        "as utilities and data center operators scramble to build out power delivery "
        "infrastructure. The quantitative evidence includes 5-year interconnection queue "
        "data from multiple regional transmission organizations, indicating that the "
        "bottleneck is structural rather than cyclical. Grid modernization policy changes "
        "could accelerate the buildout, but even aggressive policy scenarios suggest "
        "multi-year timelines for meaningful capacity additions. The demand model shows "
        "base case total addressable market of $50 billion for power infrastructure, "
        "with bull case reaching $75 billion if AI capex continues its current trajectory. "
        "Bear case scenarios assume demand deceleration to $30 billion, which still "
        "represents significant growth from current levels. The temporal marker spans "
        "2025-2030, indicating a longer-duration opportunity compared to GPU scarcity. "
        "The resolution trigger identified is grid modernization policy at the federal level, "
        "which would need to dramatically streamline permitting and interconnection processes. "
        "Even optimistic policy scenarios suggest resolution no earlier than 2028-2029. "
        "EATON's installed base and expertise in electrical distribution create a moat "
        "based on customer relationships and technical capability that new entrants cannot "
        "easily replicate. The company's order backlog provides visibility into future "
        "revenue, reducing execution risk relative to pure-play growth stories.\n\n"
        "> Stress test: Grid modernization stall shows 70% thesis survival probability. "
        "Even if grid modernization stalls, the existing backlog provides downside protection.\n\n"
        "## Second & Third-Order Effects\n\n"
        "The effects chain analysis revealed multiple layers of downstream impact from "
        "the primary scarcity bottlenecks:\n\n"
        "- First order: GPU scarcity drives NVIDIA pricing power, enabling premium margins "
        "and exceptional free cash flow generation that funds further R&D investment\n"
        "- Second order: Power demand cascades to grid infrastructure, creating a derived "
        "demand tailwind for electrical equipment manufacturers and utility companies\n"
        "- Third order: Cooling and real estate constraints emerge as data center density "
        "increases, creating potential opportunities in liquid cooling technology and "
        "industrial real estate near power generation facilities\n\n"
        "These multi-order effects suggest that the investment opportunity extends beyond "
        "the two primary pillars identified in this screen. However, third-order effects "
        "carry higher uncertainty and should be treated as speculative add-ons rather than "
        "core portfolio positions.\n\n"
        "## Portfolio Construction Guidance\n\n"
        "Phase 1 allocation favors near-term GPU beneficiaries (NVDA at 60%), with "
        "Phase 2 rotation into power infrastructure (EATON at 40%). The rotation trigger "
        "is GPU supply normalization, which would signal reducing NVDA exposure and "
        "increasing allocation to longer-duration power infrastructure plays. Risk limits "
        "include a 25% maximum single-name concentration to prevent over-exposure to "
        "any individual equity thesis.\n\n"
        "| Catalyst | Date | Ticker | Impact |\n"
        "|----------|------|--------|--------|\n"
        "| GB300 production ramp | Q2 2025 | NVDA | Positive |\n"
        "| IRA infrastructure spending | H2 2025 | EATON | Positive |\n\n"
        "## Disclaimer\n\n"
        "This is AI-assisted investment research, not financial advice. All data comes "
        "from the screened source material. Past performance does not guarantee future results. "
        "Investors should conduct their own due diligence before making investment decisions. "
        "This report was generated by an automated screening process and should be treated "
        "as a starting point for further research rather than a definitive recommendation. "
        "The investment thesis presented here is based on analysis of a single source document "
        "and may not capture all relevant market dynamics. Professional financial advice "
        "should be sought before making any investment decisions based on this report. "
        "All quantitative anchors, temporal markers, and conviction assessments originate "
        "from the screening process and should be independently verified. Market conditions "
        "may have changed since this screen was generated. The tiered classification system "
        "used in this report reflects a structured analytical framework but does not "
        "guarantee investment outcomes. Position sizing, portfolio construction, and risk "
        "management decisions should account for individual investor circumstances, risk "
        "tolerance, and investment objectives that are beyond the scope of this report."
    )


# -- Helper: standard patch context for handlers ----------------------------


def _patch_handler(module_path, test_db, claude_mock=None, claude_raw_mock=None):
    """Returns a context manager that patches SessionLocal, call_claude, emit_sse_event."""
    patches = {
        f"app.services.ist.final_synthesis.SessionLocal": lambda: test_db,
        "app.services.ist.final_synthesis.emit_sse_event": AsyncMock(),
    }
    if claude_mock is not None:
        patches["app.services.ist.final_synthesis.call_claude"] = claude_mock
    if claude_raw_mock is not None:
        patches["app.services.ist.final_synthesis.call_claude_raw"] = claude_raw_mock

    from contextlib import ExitStack
    stack = ExitStack()
    for target, replacement in patches.items():
        if callable(replacement) and not isinstance(replacement, AsyncMock):
            stack.enter_context(patch(target, replacement))
        else:
            stack.enter_context(patch(target, new_callable=lambda r=replacement: lambda: r))
    return stack


# -- Master Screen Handler Tests ---------------------------------------------


class TestMasterScreen:
    """Tests for the master_screen step handler."""

    @pytest.mark.asyncio
    async def test_master_screen_creates_record(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
        sample_dialectic_reviews,
    ):
        """Master screen handler creates ISTMasterScreen record."""
        mock_result = _mock_master_screen_result()

        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_master_screen(workflow_run.id)

        assert result is not None
        assert result["totalEquities"] == 2
        assert result["tier1Count"] == 1

        # Verify DB record
        master = (
            test_db.query(ISTMasterScreen)
            .filter(ISTMasterScreen.screen_id == ist_screen.id)
            .first()
        )
        assert master is not None
        ranked = json.loads(master.ranked_equities)
        assert len(ranked) == 2
        assert ranked[0]["ticker"] == "NVDA"
        assert ranked[0]["conviction_score"] == 92
        assert master.total_equities == 2
        assert master.tier1_count == 1

        # Verify invariant compliance was stored
        inv = json.loads(master.invariant_compliance)
        assert isinstance(inv, list)
        assert any(i["id"] == "INV-1" for i in inv)

    @pytest.mark.asyncio
    async def test_master_screen_updates_status_to_synthesizing(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Master screen handler sets screen status to SYNTHESIZING."""
        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.call_claude",
            new_callable=AsyncMock,
            return_value=_mock_master_screen_result(),
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            await handle_master_screen(workflow_run.id)

        test_db.refresh(ist_screen)
        assert ist_screen.status == "SYNTHESIZING"

    @pytest.mark.asyncio
    async def test_master_screen_no_screen_raises(self, test_db):
        """Master screen raises if no screen found."""
        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No IST screen found"):
                await handle_master_screen(99999)


# -- Rotation Strategy Handler Tests -----------------------------------------


class TestRotationStrategy:
    """Tests for the rotation_strategy step handler."""

    @pytest.mark.asyncio
    async def test_rotation_strategy_creates_record(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Rotation strategy handler creates ISTRotationStrategy record."""
        mock_result = _mock_rotation_strategy_result()

        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_rotation_strategy(workflow_run.id)

        assert result is not None
        assert result["phaseCount"] == 2
        assert result["triggerCount"] == 1
        assert result["riskLimitCount"] == 1

        # Verify DB record
        rotation = (
            test_db.query(ISTRotationStrategy)
            .filter(ISTRotationStrategy.screen_id == ist_screen.id)
            .first()
        )
        assert rotation is not None
        allocations = json.loads(rotation.phase_allocations)
        assert len(allocations) == 2
        triggers = json.loads(rotation.rotation_triggers)
        assert len(triggers) == 1
        limits = json.loads(rotation.risk_limits)
        assert len(limits) == 1

    @pytest.mark.asyncio
    async def test_rotation_strategy_no_screen_raises(self, test_db):
        """Rotation strategy raises if no screen found."""
        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No IST screen found"):
                await handle_rotation_strategy(99999)


# -- Catalyst Calendar Handler Tests -----------------------------------------


class TestCatalystCalendar:
    """Tests for the catalyst_calendar step handler."""

    @pytest.mark.asyncio
    async def test_catalyst_calendar_creates_record(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Catalyst calendar handler creates ISTCatalystCalendar record."""
        mock_result = _mock_catalyst_calendar_result()

        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_catalyst_calendar(workflow_run.id)

        assert result is not None
        assert result["totalCatalysts"] == 2
        assert result["nextCatalystDate"] is not None

        # Verify DB record
        calendar = (
            test_db.query(ISTCatalystCalendar)
            .filter(ISTCatalystCalendar.screen_id == ist_screen.id)
            .first()
        )
        assert calendar is not None
        catalysts = json.loads(calendar.catalysts)
        assert len(catalysts) == 2
        assert calendar.total_catalysts == 2

    @pytest.mark.asyncio
    async def test_catalyst_calendar_no_screen_raises(self, test_db):
        """Catalyst calendar raises if no screen found."""
        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No IST screen found"):
                await handle_catalyst_calendar(99999)


# -- Stress Tests Handler Tests ----------------------------------------------


class TestStressTests:
    """Tests for the stress_tests step handler."""

    @pytest.mark.asyncio
    async def test_stress_tests_creates_record(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Stress tests handler creates ISTStressTest record."""
        mock_result = _mock_stress_test_result()

        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_stress_tests(workflow_run.id)

        assert result is not None
        assert result["frameworkTestCount"] == 1
        assert result["nameTestCount"] == 2
        assert result["survivalScoreCount"] == 2

        # Verify DB record
        stress = (
            test_db.query(ISTStressTest)
            .filter(ISTStressTest.screen_id == ist_screen.id)
            .first()
        )
        assert stress is not None
        fw_tests = json.loads(stress.framework_tests)
        assert len(fw_tests) == 1
        name_tests = json.loads(stress.name_tests)
        assert len(name_tests) == 2
        survival = json.loads(stress.survival_scores)
        assert len(survival) == 2

    @pytest.mark.asyncio
    async def test_stress_tests_no_screen_raises(self, test_db):
        """Stress tests raises if no screen found."""
        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No IST screen found"):
                await handle_stress_tests(99999)


# -- Report Generation Handler Tests ----------------------------------------


class TestReportGeneration:
    """Tests for the report_generation step handler."""

    @pytest.mark.asyncio
    async def test_report_generation_creates_record(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Report generation handler creates ISTReport record with markdown."""
        mock_report = _mock_report_content()

        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.call_claude_raw",
            new_callable=AsyncMock,
            return_value=mock_report,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_report_generation(workflow_run.id)

        assert result is not None
        assert "GPU Scarcity Screen" in result["title"]
        assert result["wordCount"] > 0
        assert result["pillarCount"] == 2
        assert result["equityCount"] == 2

        # Verify DB record
        report = (
            test_db.query(ISTReport)
            .filter(ISTReport.screen_id == ist_screen.id)
            .first()
        )
        assert report is not None
        assert "## Executive Summary" in report.content
        assert "NVDA" in report.content
        assert report.title == "Investment Thesis Report: GPU Scarcity Screen"

        # Verify metadata
        metadata = json.loads(report.report_metadata)
        assert metadata["pillarCount"] == 2
        assert metadata["equityCount"] == 2
        assert metadata["tier1Count"] == 1
        assert metadata["wordCount"] > 0
        assert "model" in metadata

    @pytest.mark.asyncio
    async def test_report_generation_uses_raw_call(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Report generation uses call_claude_raw (NOT structured output)."""
        raw_calls = []

        async def capture_raw(**kwargs):
            raw_calls.append(kwargs)
            return _mock_report_content()

        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.call_claude_raw",
            new_callable=AsyncMock,
            side_effect=capture_raw,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            await handle_report_generation(workflow_run.id)

        assert len(raw_calls) == 1
        # Verify anti-hallucination instruction is in the system prompt
        system_prompt = raw_calls[0]["system_prompt"]
        assert "No new numbers" in system_prompt
        assert "synthesis only" in system_prompt

    @pytest.mark.asyncio
    async def test_report_generation_no_screen_raises(self, test_db):
        """Report generation raises if no screen found."""
        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No IST screen found"):
                await handle_report_generation(99999)


# -- Screen Coherence Gate Tests ---------------------------------------------


class TestScreenCoherenceGate:
    """Tests for the screen_coherence_gate step handler."""

    @pytest.fixture
    def populated_screen(
        self, test_db, ist_screen, sample_claims, sample_bottlenecks,
        sample_candidates, sample_dialectic_reviews,
    ):
        """Create a screen with all artifacts for passing coherence gate."""
        # Create master screen
        ranked_equities = json.dumps([
            {"rank": 1, "ticker": "NVDA", "tier": 1, "conviction_score": 92},
            {"rank": 2, "ticker": "EATON", "tier": 2, "conviction_score": 55},
        ])
        master = ISTMasterScreen(
            screen_id=ist_screen.id,
            ranked_equities=ranked_equities,
            invariant_compliance=json.dumps([]),
            total_equities=2,
            tier1_count=1,
        )
        test_db.add(master)

        # Create report with content that passes coherence (>= 1000 words, contains tickers and bottlenecks)
        report = ISTReport(
            screen_id=ist_screen.id,
            title="Investment Thesis Report: GPU Scarcity Screen",
            content=_mock_report_content(),
            report_metadata=json.dumps({
                "wordCount": 1500,
                "pillarCount": 2,
                "equityCount": 2,
                "tier1Count": 1,
                "tier2Count": 1,
                "tier3Count": 0,
            }),
        )
        test_db.add(report)

        # Create rotation strategy (required by coherence gate check 6)
        rotation = ISTRotationStrategy(
            screen_id=ist_screen.id,
            phase_allocations=json.dumps([]),
            rotation_triggers=json.dumps([]),
            risk_limits=json.dumps([]),
        )
        test_db.add(rotation)

        # Create catalyst calendar (required by coherence gate check 7)
        catalyst = ISTCatalystCalendar(
            screen_id=ist_screen.id,
            catalysts=json.dumps([]),
            total_catalysts=0,
        )
        test_db.add(catalyst)

        # Create stress tests (required by coherence gate check 8)
        stress = ISTStressTest(
            screen_id=ist_screen.id,
            framework_tests=json.dumps([]),
            name_tests=json.dumps([]),
            survival_scores=json.dumps([]),
        )
        test_db.add(stress)

        test_db.commit()

        return ist_screen

    @pytest.mark.asyncio
    async def test_coherence_gate_passes(
        self, test_db, workflow_run, populated_screen,
    ):
        """Coherence gate passes when all checks succeed."""
        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ) as mock_sse:
            test_db.close = lambda: None
            result = await handle_screen_coherence_gate(workflow_run.id)

        assert result is not None
        assert result["gateResult"] == "PASSED"
        assert result["reportExists"] is True
        assert result["masterScreenExists"] is True

        # Verify gate_passed SSE was emitted
        sse_calls = [
            c for c in mock_sse.call_args_list
            if c[0][1] == "gate_passed"
        ]
        assert len(sse_calls) == 1

    @pytest.mark.asyncio
    async def test_coherence_gate_fails_missing_report(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Coherence gate fails when report is missing."""
        # Create master screen but NO report
        master = ISTMasterScreen(
            screen_id=ist_screen.id,
            ranked_equities=json.dumps([]),
            invariant_compliance=json.dumps([]),
            total_equities=0,
            tier1_count=0,
        )
        test_db.add(master)
        test_db.commit()

        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="Report does not exist"):
                await handle_screen_coherence_gate(workflow_run.id)

    @pytest.mark.asyncio
    async def test_coherence_gate_fails_short_report(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Coherence gate fails when report is too short (< 1000 words)."""
        master = ISTMasterScreen(
            screen_id=ist_screen.id,
            ranked_equities=json.dumps([]),
            invariant_compliance=json.dumps([]),
            total_equities=0,
            tier1_count=0,
        )
        test_db.add(master)

        report = ISTReport(
            screen_id=ist_screen.id,
            title="Short Report",
            content="This is a very short report. " * 10,  # ~70 words
            report_metadata=json.dumps({}),
        )
        test_db.add(report)
        test_db.commit()

        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="word count.*below minimum 1000"):
                await handle_screen_coherence_gate(workflow_run.id)

    @pytest.mark.asyncio
    async def test_coherence_gate_fails_missing_tier1_ticker(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Coherence gate fails when a Tier 1 ticker is missing from report."""
        master = ISTMasterScreen(
            screen_id=ist_screen.id,
            ranked_equities=json.dumps([]),
            invariant_compliance=json.dumps([]),
            total_equities=0,
            tier1_count=0,
        )
        test_db.add(master)

        # Report that does NOT contain "NVDA" (which is Tier 1)
        long_text = ("The power infrastructure thesis shows strong fundamentals. "
                     "Eaton Corporation benefits from grid modernization spending. "
                     "GPU Supply Scarcity is a key pillar. "
                     "Power Infrastructure Bottleneck drives infrastructure spending. ") * 50
        report = ISTReport(
            screen_id=ist_screen.id,
            title="Missing NVDA Report",
            content=long_text,
            report_metadata=json.dumps({}),
        )
        test_db.add(report)
        test_db.commit()

        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="Tier 1 ticker NVDA not found"):
                await handle_screen_coherence_gate(workflow_run.id)

    @pytest.mark.asyncio
    async def test_coherence_gate_fails_missing_bottleneck(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Coherence gate fails when a bottleneck name is missing from report."""
        master = ISTMasterScreen(
            screen_id=ist_screen.id,
            ranked_equities=json.dumps([]),
            invariant_compliance=json.dumps([]),
            total_equities=0,
            tier1_count=0,
        )
        test_db.add(master)

        # Report that contains NVDA but NOT "GPU Supply Scarcity"
        long_text = (
            "NVDA benefits from strong demand tailwinds. "
            "Power Infrastructure Bottleneck is a structural driver. "
        ) * 100
        report = ISTReport(
            screen_id=ist_screen.id,
            title="Missing Bottleneck Report",
            content=long_text,
            report_metadata=json.dumps({}),
        )
        test_db.add(report)
        test_db.commit()

        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="GPU Supply Scarcity.*not sufficiently covered"):
                await handle_screen_coherence_gate(workflow_run.id)

    @pytest.mark.asyncio
    async def test_coherence_gate_fails_missing_master_screen(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Coherence gate fails when master screen is missing."""
        # Create report but NO master screen
        report = ISTReport(
            screen_id=ist_screen.id,
            title="Report Without Master",
            content=_mock_report_content(),
            report_metadata=json.dumps({}),
        )
        test_db.add(report)
        test_db.commit()

        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="Master screen does not exist"):
                await handle_screen_coherence_gate(workflow_run.id)

    @pytest.mark.asyncio
    async def test_coherence_gate_emits_gate_failed_sse(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Coherence gate emits gate_failed SSE event on failure."""
        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ) as mock_sse:
            test_db.close = lambda: None
            with pytest.raises(ValueError):
                await handle_screen_coherence_gate(workflow_run.id)

        sse_calls = [
            c for c in mock_sse.call_args_list
            if c[0][1] == "gate_failed"
        ]
        assert len(sse_calls) == 1


# -- Screen Certification Tests ----------------------------------------------


class TestScreenCertification:
    """Tests for the screen_certification step handler."""

    @pytest.mark.asyncio
    async def test_certification_updates_screen(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """Certification sets is_certified, certified_at, and status."""
        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_screen_certification(workflow_run.id)

        assert result is not None
        assert result["certified"] is True
        assert result["status"] == "COMPLETED"

        # Verify screen fields
        test_db.refresh(ist_screen)
        assert ist_screen.is_certified == 1
        assert ist_screen.certified_at is not None
        assert ist_screen.status == "COMPLETED"

    @pytest.mark.asyncio
    async def test_handoff_generation_produces_candidates(
        self, test_db, workflow_run, ist_screen,
        sample_claims, sample_bottlenecks, sample_candidates,
    ):
        """HFRT handoff generation produces candidates from certified screen."""
        # First certify the screen
        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            await handle_screen_certification(workflow_run.id)

        # Now generate handoff
        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_hfrt_handoff_generation(workflow_run.id)

        assert result is not None
        assert result["screenName"] == "GPU Scarcity Screen"
        # All candidates (both tiers) included in handoff
        assert result["tier1Count"] == 2  # Both NVDA and EATON
        assert "NVDA" in result["candidates"]

        # Verify handoff stored on screen
        test_db.refresh(ist_screen)
        import json as _json
        handoff_data = _json.loads(ist_screen.hfrt_handoff)
        assert handoff_data["screenName"] == "GPU Scarcity Screen"
        assert len(handoff_data["candidates"]) == 2

    @pytest.mark.asyncio
    async def test_certification_no_screen_raises(self, test_db):
        """Certification raises if no screen found."""
        with patch(
            "app.services.ist.final_synthesis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.final_synthesis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No IST screen found"):
                await handle_screen_certification(99999)


# -- Data Package Tests ------------------------------------------------------


class TestBuildFullDataPackage:
    """Tests for the _build_full_data_package helper."""

    def test_package_contains_all_sections(
        self, test_db, ist_screen, workflow_run,
        sample_claims, sample_bottlenecks, sample_candidates,
        sample_dialectic_reviews,
    ):
        """Full data package contains all Phase 1-5 data sections."""
        data_package = _build_full_data_package(test_db, ist_screen.id)

        # Check all XML sections
        assert "<screen_metadata>" in data_package
        assert "<claims" in data_package
        assert "<bottlenecks" in data_package
        assert "<demand_models" in data_package
        assert "<validations" in data_package
        assert "<equity_candidates" in data_package
        assert "<effects_chains" in data_package
        assert "<dialectic_reviews" in data_package

        # Check specific content
        assert "GPU Scarcity Screen" in data_package
        assert "NVDA" in data_package
        assert "EATON" in data_package
        assert "GPU Supply Scarcity" in data_package
        assert "OPTIMIST" in data_package
        assert "PESSIMIST" in data_package
        assert "SYNTHESIS" in data_package

    def test_package_missing_screen_raises(self, test_db):
        """Data package builder raises on missing screen."""
        with pytest.raises(ValueError, match="No IST screen found"):
            _build_full_data_package(test_db, 99999)


# -- Invariant Check Tests ---------------------------------------------------


class TestRunInvariantChecks:
    """Tests for the _run_invariant_checks helper."""

    def test_invariant_checks_pass(
        self, test_db, ist_screen, sample_claims, sample_candidates,
    ):
        """Invariant checks pass when data is clean."""
        invariants = _run_invariant_checks(test_db, ist_screen.id)

        assert len(invariants) == 5
        assert invariants[0]["id"] == "INV-1"
        # INV-1: Both claims have citations
        assert invariants[0]["status"] == "PASS"
        # INV-2: Both claims have quant anchors (100%)
        assert invariants[1]["status"] == "PASS"
        # INV-3: Both claims have temporal markers
        assert invariants[2]["status"] == "PASS"
        # INV-4: No orphan equities
        assert invariants[3]["status"] == "PASS"
        # INV-5: All candidates have tier rationale
        assert invariants[4]["status"] == "PASS"

    def test_invariant_checks_fail_orphan_equity(
        self, test_db, ist_screen, sample_claims,
    ):
        """INV-4 fails when a candidate has no bottleneck."""
        orphan = ISTEquityCandidate(
            screen_id=ist_screen.id,
            ticker="ORPHAN",
            company_name="Orphan Inc",
            bottleneck_id=None,
            scarcity_score=json.dumps({"overall": 3.0}),
            tier=3,
            tier_rationale="Speculative",
            conviction="LOW",
        )
        test_db.add(orphan)
        test_db.commit()

        invariants = _run_invariant_checks(test_db, ist_screen.id)
        inv4 = next(i for i in invariants if i["id"] == "INV-4")
        assert inv4["status"] == "FAIL"


# -- Pydantic Model Tests ---------------------------------------------------


class TestPydanticModels:
    """Tests for the Pydantic response models."""

    def test_ranked_equity_valid(self):
        eq = RankedEquity(
            rank=1, ticker="NVDA", company_name="NVIDIA",
            tier=1, scarcity_score=4.5, conviction_score=90,
            pillar="GPU Supply", catalyst="GB300 launch",
        )
        assert eq.ticker == "NVDA"
        assert eq.conviction_score == 90

    def test_ranked_equity_rejects_invalid_score(self):
        with pytest.raises(Exception):
            RankedEquity(
                rank=1, ticker="NVDA", company_name="NVIDIA",
                tier=1, scarcity_score=4.5, conviction_score=150,  # > 100
                pillar="GPU Supply",
            )

    def test_master_screen_result_roundtrip(self):
        result = _mock_master_screen_result()
        json_str = json.dumps([eq.model_dump() for eq in result.ranked_equities])
        parsed = json.loads(json_str)
        for item in parsed:
            RankedEquity.model_validate(item)

    def test_catalyst_event_valid(self):
        cat = CatalystEvent(
            date="Q2 2025", ticker="NVDA", event="GB300 launch",
            impact="Positive", pillar="GPU Supply",
        )
        assert cat.date == "Q2 2025"

    def test_stress_test_survival_bounds(self):
        """SurvivalScore rejects out-of-range probabilities."""
        with pytest.raises(Exception):
            SurvivalScore(
                ticker="NVDA", overall_survival=1.5,  # > 1.0
                weakest_scenario="Test",
            )

    def test_name_test_survival_bounds(self):
        """NameTest rejects out-of-range survival probability."""
        with pytest.raises(Exception):
            NameTest(
                ticker="NVDA", scenario="Test",
                impact="Test", survival_probability=-0.1,  # < 0.0
            )

    def test_phase_allocation_valid(self):
        pa = PhaseAllocation(
            phase=1, phase_label="Near-term",
            allocation_pct=60, tickers=["NVDA"],
            rationale="Immediate scarcity",
        )
        assert pa.allocation_pct == 60.0

    def test_rotation_strategy_result_roundtrip(self):
        result = _mock_rotation_strategy_result()
        pa_json = json.dumps([pa.model_dump() for pa in result.phase_allocations])
        parsed = json.loads(pa_json)
        for item in parsed:
            PhaseAllocation.model_validate(item)


# -- Content-Type-Aware Threshold Tests -------------------------------------


class TestContentTypeThresholds:
    """Tests for CONTENT_TYPE_THRESHOLDS and get_thresholds()."""

    def test_all_five_content_types_defined(self):
        expected = {"earnings_call", "research_note", "article", "podcast_transcript", "text"}
        assert set(CONTENT_TYPE_THRESHOLDS.keys()) == expected

    def test_earnings_call_strictest_inv2(self):
        t = get_thresholds("earnings_call")
        assert t["inv2_quant_pct"] == 50

    def test_text_lowest_inv2(self):
        t = get_thresholds("text")
        assert t["inv2_quant_pct"] == 20

    def test_podcast_inv2_below_article(self):
        podcast = get_thresholds("podcast_transcript")["inv2_quant_pct"]
        article = get_thresholds("article")["inv2_quant_pct"]
        assert podcast < article

    def test_fallback_for_unknown_type(self):
        t = get_thresholds("unknown_type")
        assert t["inv2_quant_pct"] == 40
        assert t["bottleneck_kw"] == 0.60

    def test_fallback_for_none(self):
        t = get_thresholds(None)
        assert t["inv2_quant_pct"] == 40

    def test_bottleneck_kw_decreases_for_qualitative_types(self):
        ec = get_thresholds("earnings_call")["bottleneck_kw"]
        txt = get_thresholds("text")["bottleneck_kw"]
        assert ec > txt

    def test_all_thresholds_have_required_keys(self):
        for ct, t in CONTENT_TYPE_THRESHOLDS.items():
            assert "inv2_quant_pct" in t, f"{ct} missing inv2_quant_pct"
            assert "bottleneck_kw" in t, f"{ct} missing bottleneck_kw"


class TestInvariantChecksContentTypeAware:
    """Tests that _run_invariant_checks uses content-type thresholds for INV-2."""

    def test_inv2_passes_with_text_content_type(
        self, test_db, ist_screen,
    ):
        """33% quant anchors should PASS for 'text' (threshold 20%)."""
        ist_screen.content_type = "text"
        test_db.flush()

        # Add 3 claims: 1 with quant anchor, 2 without = 33%
        for i in range(3):
            test_db.add(ISTClaim(
                screen_id=ist_screen.id,
                claim_text=f"Claim {i}",
                source_citation=f"Source {i}",
                quantitative_anchor=f"$100M" if i == 0 else None,
                temporal_marker="2025" if i == 0 else None,
                confidence=0.8,
            ))
        test_db.commit()

        invariants = _run_invariant_checks(
            test_db, ist_screen.id, content_type="text"
        )
        inv2 = next(i for i in invariants if i["id"] == "INV-2")
        assert inv2["status"] == "PASS"
        assert "[text]" in inv2["details"]

    def test_inv2_fails_with_earnings_call_content_type(
        self, test_db, ist_screen,
    ):
        """33% quant anchors should FAIL for 'earnings_call' (threshold 50%)."""
        ist_screen.content_type = "earnings_call"
        test_db.flush()

        for i in range(3):
            test_db.add(ISTClaim(
                screen_id=ist_screen.id,
                claim_text=f"Claim {i}",
                source_citation=f"Source {i}",
                quantitative_anchor=f"$100M" if i == 0 else None,
                temporal_marker="2025" if i == 0 else None,
                confidence=0.8,
            ))
        test_db.commit()

        invariants = _run_invariant_checks(
            test_db, ist_screen.id, content_type="earnings_call"
        )
        inv2 = next(i for i in invariants if i["id"] == "INV-2")
        assert inv2["status"] == "FAIL"
        assert "[earnings_call]" in inv2["details"]

    def test_inv2_without_content_type_uses_default(
        self, test_db, ist_screen, sample_claims,
    ):
        """Without content_type, uses default 40% threshold."""
        invariants = _run_invariant_checks(test_db, ist_screen.id)
        inv2 = next(i for i in invariants if i["id"] == "INV-2")
        # sample_claims has 2/2 quant anchors = 100%, passes regardless
        assert inv2["status"] == "PASS"
        # No content type label in details
        assert "[" not in inv2["details"]

    def test_inv2_detail_shows_threshold(
        self, test_db, ist_screen,
    ):
        """Detail message should reflect the content-type-specific threshold."""
        test_db.add(ISTClaim(
            screen_id=ist_screen.id,
            claim_text="Claim",
            source_citation="Source",
            quantitative_anchor="$1B",
            confidence=0.8,
        ))
        test_db.commit()

        invariants = _run_invariant_checks(
            test_db, ist_screen.id, content_type="podcast_transcript"
        )
        inv2 = next(i for i in invariants if i["id"] == "INV-2")
        assert ">= 25%" in inv2["details"]


class TestBottleneckNameInReport:
    """Tests for _bottleneck_name_in_report with configurable threshold."""

    def test_default_threshold_60_pct(self):
        """Default 60% threshold: 3/5 key words needed."""
        name = "Advanced GPU Supply Chain Bottleneck"
        content = "The advanced GPU supply issues are growing."
        passed, missing = _bottleneck_name_in_report(name, content)
        # key words (>=4 chars): advanced, supply, chain, bottleneck = 4
        # found: advanced, supply = 2, need ceil(4*0.6) = 3, so FAIL
        assert passed is False
        assert "chain" in missing
        assert "bottleneck" in missing

    def test_lower_threshold_40_pct(self):
        """With 40% threshold: 2/4 key words needed for same name."""
        name = "Advanced GPU Supply Chain Bottleneck"
        content = "The advanced GPU supply issues are growing."
        passed, missing = _bottleneck_name_in_report(
            name, content, coverage_threshold=0.4
        )
        # key words: advanced, supply, chain, bottleneck = 4
        # found: advanced, supply = 2, need ceil(4*0.4) = 2, so PASS
        assert passed is True

    def test_abstract_name_fails_at_60_passes_at_40(self):
        """Ontological name (like AWG Ted Talk) fails strict, passes lenient."""
        name = "Ontological Civilizational Adaptation Bottleneck"
        content = "civilization must adapt through ontological transformation"
        # key words: ontological, civilizational, adaptation, bottleneck = 4
        # found in content (case-insensitive): ontological = yes,
        # civilizational (NOT civilization) = no, adaptation = no (adapt != adaptation),
        # bottleneck = no
        # Actually let me check: "adaptation" not in content, "civilizational" not in content
        # So found=1, need ceil(4*0.6)=3 -> FAIL
        passed_strict, _ = _bottleneck_name_in_report(name, content)
        assert passed_strict is False

        # With 0.25 threshold: need ceil(4*0.25)=1 -> PASS
        passed_lenient, _ = _bottleneck_name_in_report(
            name, content, coverage_threshold=0.25
        )
        assert passed_lenient is True

    def test_short_name_fallback_ignores_threshold(self):
        """Names with no key words (all < 4 chars) use substring match."""
        name = "AI GPU"
        content = "The AI GPU market is booming."
        passed, missing = _bottleneck_name_in_report(name, content)
        assert passed is True
        assert missing == []

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        name = "Power Infrastructure Constraint"
        content = "the POWER INFRASTRUCTURE constraint is binding"
        passed, _ = _bottleneck_name_in_report(name, content)
        assert passed is True
