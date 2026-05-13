"""Unit tests for IST Phase 2: Thematic Analysis step handlers and endpoints.

Tests cover:
- Bottleneck mapping step handler (mock Claude, verify DB records)
- Demand modeling step handler (mock Claude, verify DB records)
- External validation step handler (mock Claude, verify DB + claim updates)
- Content sufficiency gate (pass case + multiple fail cases)
- GET /api/ist/screens/{id}/bottlenecks endpoint
- GET /api/ist/screens/{id}/demand-models endpoint
- GET /api/ist/screens/{id}/validation endpoint
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
    ISTDemandModel,
    ISTScreen,
    ISTValidation,
)
from app.services.ist.thematic_analysis import (
    BottleneckItem,
    BottleneckResult,
    DemandModelItem,
    DemandModelResult,
    ValidationItem,
    ValidationResult,
    handle_bottleneck_mapping,
    handle_content_sufficiency_gate,
    handle_demand_modeling,
    handle_external_validation,
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
        status="RUNNING",
        current_phase=1,
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
        status="EXTRACTING",
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
    """Create sample bottlenecks for demand modeling tests."""
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


# ── Bottleneck Mapping Tests ───────────────────────────────────────────────


class TestBottleneckMapping:
    """Tests for the bottleneck_mapping step handler."""

    @pytest.mark.asyncio
    async def test_bottleneck_mapping_creates_records(
        self, test_db, workflow_run, ist_screen, sample_claims
    ):
        """Bottleneck mapping creates ISTBottleneck records from Claude output."""
        mock_result = BottleneckResult(
            bottlenecks=[
                BottleneckItem(
                    name="GPU Supply Scarcity",
                    phase=1,
                    phase_label="Near-term (0-18 months)",
                    description="NVIDIA GB300 production constrained",
                    quantitative_evidence="330,000 units per GW",
                    temporal_marker="2025-2026",
                    resolution_trigger="TSMC capacity expansion",
                    claim_indices=[0],
                    causal_parent_name=None,
                ),
                BottleneckItem(
                    name="Power Infrastructure",
                    phase=2,
                    phase_label="Mid-term (18-36 months)",
                    description="Grid interconnection queues",
                    quantitative_evidence="5-year queues",
                    temporal_marker="2025-2030",
                    resolution_trigger="Grid modernization",
                    claim_indices=[1],
                    causal_parent_name="GPU Supply Scarcity",
                ),
            ]
        )

        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            # Override db.close to no-op since we need the session alive
            original_close = test_db.close
            test_db.close = lambda: None
            try:
                result = await handle_bottleneck_mapping(workflow_run.id)
            finally:
                test_db.close = original_close

        assert result is not None
        assert result["bottlenecksIdentified"] == 2

        # Verify DB records
        bns = (
            test_db.query(ISTBottleneck)
            .filter(ISTBottleneck.screen_id == ist_screen.id)
            .order_by(ISTBottleneck.id)
            .all()
        )
        assert len(bns) == 2
        assert bns[0].name == "GPU Supply Scarcity"
        assert bns[0].phase == 1
        assert bns[0].causal_parent_id is None

        assert bns[1].name == "Power Infrastructure"
        assert bns[1].phase == 2
        assert bns[1].causal_parent_id == bns[0].id  # causal parent linked

    @pytest.mark.asyncio
    async def test_bottleneck_mapping_updates_claims(
        self, test_db, workflow_run, ist_screen, sample_claims
    ):
        """Bottleneck mapping updates claim.bottleneck_name for mapped claims."""
        mock_result = BottleneckResult(
            bottlenecks=[
                BottleneckItem(
                    name="GPU Scarcity",
                    phase=1,
                    phase_label="Near-term",
                    description="GPU supply",
                    claim_indices=[0, 1],
                ),
            ]
        )

        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            try:
                await handle_bottleneck_mapping(workflow_run.id)
            finally:
                pass  # close already no-op'd

        # Verify claims updated
        claims = (
            test_db.query(ISTClaim)
            .filter(ISTClaim.screen_id == ist_screen.id)
            .order_by(ISTClaim.id)
            .all()
        )
        assert claims[0].bottleneck_name == "GPU Scarcity"
        assert claims[1].bottleneck_name == "GPU Scarcity"
        assert claims[2].bottleneck_name is None  # Not mapped
        assert claims[3].bottleneck_name is None

    @pytest.mark.asyncio
    async def test_bottleneck_mapping_no_screen_raises(self, test_db):
        """Bottleneck mapping raises if no screen found."""
        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No IST screen found"):
                await handle_bottleneck_mapping(99999)

    @pytest.mark.asyncio
    async def test_bottleneck_mapping_no_claims_raises(
        self, test_db, workflow_run, ist_screen
    ):
        """Bottleneck mapping raises if no claims found."""
        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No claims found"):
                await handle_bottleneck_mapping(workflow_run.id)


# ── Demand Modeling Tests ──────────────────────────────────────────────────


class TestDemandModeling:
    """Tests for the demand_modeling step handler."""

    @pytest.mark.asyncio
    async def test_demand_modeling_creates_records(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Demand modeling creates ISTDemandModel records."""
        mock_result = DemandModelResult(
            models=[
                DemandModelItem(
                    bottleneck_name="GPU Supply Scarcity",
                    formula="TAM = Units * ASP * Growth_Rate",
                    base_case={"demand": 1000000, "tam": 50000000000, "assumptions": "moderate growth"},
                    bull_case={"demand": 1500000, "tam": 75000000000, "assumptions": "aggressive adoption"},
                    bear_case={"demand": 500000, "tam": 25000000000, "assumptions": "slow rollout"},
                    sensitivity_table=[
                        {"variable": "ASP", "low": 20000, "base": 30000, "high": 40000, "tamImpact": "30%"},
                    ],
                    multiplier_chain="GPU -> Cluster -> Data Center -> Cloud Revenue",
                ),
                DemandModelItem(
                    bottleneck_name="Power Infrastructure Bottleneck",
                    formula="TAM = GW_Capacity * $/GW",
                    base_case={"demand": 50, "tam": 10000000000, "assumptions": "steady build"},
                    bull_case={"demand": 80, "tam": 16000000000, "assumptions": "accelerated grid"},
                    bear_case={"demand": 30, "tam": 6000000000, "assumptions": "regulatory delays"},
                    sensitivity_table=[
                        {"variable": "GW_capacity", "low": 30, "base": 50, "high": 80, "tamImpact": "60%"},
                    ],
                ),
            ]
        )

        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_demand_modeling(workflow_run.id)

        assert result is not None
        assert result["modelsCreated"] == 2

        # Verify DB records
        models = (
            test_db.query(ISTDemandModel)
            .filter(ISTDemandModel.screen_id == ist_screen.id)
            .order_by(ISTDemandModel.id)
            .all()
        )
        assert len(models) == 2
        assert models[0].bottleneck_id == sample_bottlenecks[0].id
        assert models[0].formula == "TAM = Units * ASP * Growth_Rate"

        # Verify JSON columns are valid JSON (INV-BE-06)
        base = json.loads(models[0].base_case)
        assert base["tam"] == 50000000000
        sensitivity = json.loads(models[0].sensitivity_table)
        assert len(sensitivity) == 1
        assert sensitivity[0]["variable"] == "ASP"

    @pytest.mark.asyncio
    async def test_demand_modeling_no_bottlenecks_raises(
        self, test_db, workflow_run, ist_screen
    ):
        """Demand modeling raises if no bottlenecks found."""
        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No bottlenecks found"):
                await handle_demand_modeling(workflow_run.id)

    @pytest.mark.asyncio
    async def test_demand_modeling_skips_unknown_bottleneck(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Demand modeling skips models referencing unknown bottleneck names."""
        mock_result = DemandModelResult(
            models=[
                DemandModelItem(
                    bottleneck_name="Nonexistent Bottleneck",
                    formula="N/A",
                    base_case={"demand": 0},
                    bull_case={"demand": 0},
                    bear_case={"demand": 0},
                    sensitivity_table=[],
                ),
            ]
        )

        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_demand_modeling(workflow_run.id)

        # Model should be skipped, not stored
        models = (
            test_db.query(ISTDemandModel)
            .filter(ISTDemandModel.screen_id == ist_screen.id)
            .all()
        )
        assert len(models) == 0


# ── External Validation Tests ──────────────────────────────────────────────


class TestExternalValidation:
    """Tests for the external_validation step handler."""

    @pytest.mark.asyncio
    async def test_validation_creates_records_and_updates_claims(
        self, test_db, workflow_run, ist_screen, sample_claims
    ):
        """Validation creates ISTValidation records and updates claims."""
        mock_result = ValidationResult(
            validations=[
                ValidationItem(
                    claim_index=0,
                    verdict="confirmed",
                    confidence=0.9,
                    evidence="NVIDIA confirmed GB300 specs at GTC 2025",
                    sources=[{"url": "https://nvidia.com/gtc", "title": "NVIDIA GTC 2025"}],
                    search_queries=["NVIDIA GB300 specs"],
                ),
                ValidationItem(
                    claim_index=1,
                    verdict="partially_confirmed",
                    confidence=0.7,
                    evidence="Interconnection queues vary by region, 3-7 year range",
                    sources=[{"url": "https://example.com/grid-report", "title": "Grid Report"}],
                    search_queries=["interconnection queue times US"],
                ),
                ValidationItem(
                    claim_index=2,
                    verdict="contradicted",
                    confidence=0.6,
                    evidence="Cooling demand CAGR is closer to 10% per recent studies",
                    sources=[],
                    search_queries=["data center cooling demand CAGR"],
                ),
                ValidationItem(
                    claim_index=3,
                    verdict="unvalidatable",
                    confidence=0.3,
                    evidence="Future spending projections vary widely",
                    sources=[],
                    search_queries=["AI infrastructure spending 2027"],
                ),
            ]
        )

        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.perplexity_available",
            return_value=False,
        ), patch(
            "app.services.ist.thematic_analysis.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_external_validation(workflow_run.id)

        assert result is not None
        assert result["claimsValidated"] == 4
        assert result["verdictBreakdown"]["confirmed"] == 1
        assert result["verdictBreakdown"]["partially_confirmed"] == 1
        assert result["verdictBreakdown"]["contradicted"] == 1
        assert result["verdictBreakdown"]["unvalidatable"] == 1

        # Verify ISTValidation records
        validations = (
            test_db.query(ISTValidation)
            .filter(ISTValidation.screen_id == ist_screen.id)
            .order_by(ISTValidation.id)
            .all()
        )
        assert len(validations) == 4
        assert validations[0].verdict == "confirmed"
        assert validations[0].confidence == 0.9

        # Verify claims updated
        claims = (
            test_db.query(ISTClaim)
            .filter(ISTClaim.screen_id == ist_screen.id)
            .order_by(ISTClaim.id)
            .all()
        )
        assert claims[0].is_validated == 1
        assert claims[0].validation_verdict == "confirmed"
        assert claims[1].validation_verdict == "partially_confirmed"
        assert claims[2].validation_verdict == "contradicted"
        assert claims[3].validation_verdict == "unvalidatable"

    @pytest.mark.asyncio
    async def test_validation_no_claims_raises(
        self, test_db, workflow_run, ist_screen
    ):
        """Validation raises if no claims found."""
        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No claims found"):
                await handle_external_validation(workflow_run.id)

    @pytest.mark.asyncio
    async def test_validation_skips_out_of_range_index(
        self, test_db, workflow_run, ist_screen, sample_claims
    ):
        """Validation skips claims with out-of-range indices."""
        mock_result = ValidationResult(
            validations=[
                ValidationItem(
                    claim_index=999,  # Out of range
                    verdict="confirmed",
                    confidence=0.9,
                    evidence="Should be skipped",
                    sources=[],
                    search_queries=[],
                ),
            ]
        )

        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.perplexity_available",
            return_value=False,
        ), patch(
            "app.services.ist.thematic_analysis.call_claude",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            result = await handle_external_validation(workflow_run.id)

        # No validation records should be stored
        count = (
            test_db.query(ISTValidation)
            .filter(ISTValidation.screen_id == ist_screen.id)
            .count()
        )
        assert count == 0


# ── Content Sufficiency Gate Tests ─────────────────────────────────────────


class TestContentSufficiencyGate:
    """Tests for the content_sufficiency_gate step handler."""

    @pytest.mark.asyncio
    async def test_gate_passes_when_all_criteria_met(
        self, test_db, workflow_run, ist_screen, sample_claims, sample_bottlenecks
    ):
        """Gate passes when all 4 criteria are met."""
        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ) as mock_sse:
            test_db.close = lambda: None
            result = await handle_content_sufficiency_gate(workflow_run.id)

        assert result is not None
        assert result["gateResult"] == "PASSED"
        assert result["quantitativeAnchors"] >= 3
        assert result["temporalMarkers"] >= 1
        assert result["sourceBiasAssessed"] is True
        assert result["bottleneckCount"] >= 1

        # Verify gate_passed SSE event was emitted
        sse_calls = [call for call in mock_sse.call_args_list if call[0][1] == "gate_passed"]
        assert len(sse_calls) == 1

    @pytest.mark.asyncio
    async def test_gate_fails_insufficient_quant_anchors(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Gate fails when fewer than 3 claims have quantitative anchors."""
        # Create claims with only 2 quant anchors
        test_db.add(ISTClaim(
            screen_id=ist_screen.id,
            claim_text="Claim with anchor",
            source_citation="Sec 1",
            quantitative_anchor="100 units",
            temporal_marker="2025",
            confidence=0.9,
        ))
        test_db.add(ISTClaim(
            screen_id=ist_screen.id,
            claim_text="Claim with anchor 2",
            source_citation="Sec 2",
            quantitative_anchor="200 units",
            temporal_marker="2026",
            confidence=0.8,
        ))
        test_db.add(ISTClaim(
            screen_id=ist_screen.id,
            claim_text="Claim without anchor",
            source_citation="Sec 3",
            confidence=0.7,
        ))
        test_db.commit()

        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ) as mock_sse:
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="Content sufficiency gate FAILED"):
                await handle_content_sufficiency_gate(workflow_run.id)

        # Verify gate_failed SSE event
        sse_calls = [call for call in mock_sse.call_args_list if call[0][1] == "gate_failed"]
        assert len(sse_calls) == 1

    @pytest.mark.asyncio
    async def test_gate_fails_no_temporal_markers(
        self, test_db, workflow_run, ist_screen, sample_bottlenecks
    ):
        """Gate fails when no claims have temporal markers."""
        for i in range(4):
            test_db.add(ISTClaim(
                screen_id=ist_screen.id,
                claim_text=f"Claim {i}",
                source_citation=f"Sec {i}",
                quantitative_anchor=f"{i * 100} units",
                confidence=0.9,
            ))
        test_db.commit()

        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No temporal markers"):
                await handle_content_sufficiency_gate(workflow_run.id)

    @pytest.mark.asyncio
    async def test_gate_fails_no_source_bias(
        self, test_db, workflow_run, sample_claims
    ):
        """Gate fails when source bias has not been assessed."""
        # Create a screen without source_bias
        screen_no_bias = ISTScreen(
            workflow_run_id=workflow_run.id,
            name="No Bias Screen",
            status="ANALYZING",
            content_type="text",
            raw_content="Test " * 50,
            source_bias=None,
        )
        test_db.add(screen_no_bias)
        test_db.commit()

        # Add claims and bottlenecks for this screen
        for i in range(4):
            test_db.add(ISTClaim(
                screen_id=screen_no_bias.id,
                claim_text=f"Claim {i}",
                source_citation=f"Sec {i}",
                quantitative_anchor=f"{i * 100} units",
                temporal_marker=f"202{i}",
                confidence=0.9,
            ))
        test_db.add(ISTBottleneck(
            screen_id=screen_no_bias.id,
            name="Test BN",
            phase=1,
            phase_label="Near-term",
            description="Test",
        ))
        test_db.commit()

        # We need a separate workflow run that points to this screen
        run2 = WorkflowRun(
            workflow_type="IST",
            name="No Bias Run",
            status="RUNNING",
            current_phase=2,
        )
        test_db.add(run2)
        test_db.commit()
        screen_no_bias.workflow_run_id = run2.id
        test_db.commit()

        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="Source bias assessment"):
                await handle_content_sufficiency_gate(run2.id)

    @pytest.mark.asyncio
    async def test_gate_fails_no_bottlenecks(
        self, test_db, workflow_run, ist_screen, sample_claims
    ):
        """Gate fails when no bottlenecks have been identified."""
        # sample_claims has quant anchors and temporal markers,
        # ist_screen has source_bias, but no bottlenecks
        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError, match="No bottlenecks identified"):
                await handle_content_sufficiency_gate(workflow_run.id)

    @pytest.mark.asyncio
    async def test_gate_fails_with_multiple_deficiencies(
        self, test_db, workflow_run
    ):
        """Gate failure message includes all deficiencies."""
        # Screen with no source_bias, no claims, no bottlenecks
        screen = ISTScreen(
            workflow_run_id=workflow_run.id,
            name="Empty Screen",
            status="ANALYZING",
            content_type="text",
            raw_content="Test " * 50,
        )
        test_db.add(screen)
        test_db.commit()

        with patch(
            "app.services.ist.thematic_analysis.SessionLocal",
            return_value=test_db,
        ), patch(
            "app.services.ist.thematic_analysis.emit_sse_event",
            new_callable=AsyncMock,
        ):
            test_db.close = lambda: None
            with pytest.raises(ValueError) as exc_info:
                await handle_content_sufficiency_gate(workflow_run.id)

            error_msg = str(exc_info.value)
            assert "quantitative anchors" in error_msg.lower() or "Insufficient" in error_msg
            assert "Source bias" in error_msg
            assert "bottleneck" in error_msg.lower()


# ── Pydantic Model Tests ──────────────────────────────────────────────────


class TestPydanticModels:
    """Tests for the Pydantic response models used in thematic analysis."""

    def test_bottleneck_result_serialization(self):
        """BottleneckResult serializes and deserializes correctly."""
        result = BottleneckResult(
            bottlenecks=[
                BottleneckItem(
                    name="Test BN",
                    phase=1,
                    phase_label="Near-term",
                    description="Test description",
                    claim_indices=[0, 1],
                ),
            ]
        )
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        assert len(parsed["bottlenecks"]) == 1
        restored = BottleneckResult.model_validate(parsed)
        assert restored.bottlenecks[0].name == "Test BN"

    def test_demand_model_result_serialization(self):
        """DemandModelResult serializes and deserializes correctly."""
        result = DemandModelResult(
            models=[
                DemandModelItem(
                    bottleneck_name="Test BN",
                    formula="TAM = X * Y",
                    base_case={"demand": 100, "tam": 1000},
                    bull_case={"demand": 200, "tam": 2000},
                    bear_case={"demand": 50, "tam": 500},
                    sensitivity_table=[{"variable": "X", "low": 10, "base": 50, "high": 100, "tamImpact": "50%"}],
                ),
            ]
        )
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["models"][0]["formula"] == "TAM = X * Y"

    def test_validation_result_serialization(self):
        """ValidationResult serializes and deserializes correctly."""
        result = ValidationResult(
            validations=[
                ValidationItem(
                    claim_index=0,
                    verdict="confirmed",
                    confidence=0.9,
                    evidence="Test evidence",
                    sources=[{"url": "https://example.com", "title": "Example"}],
                    search_queries=["test query"],
                ),
            ]
        )
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["validations"][0]["verdict"] == "confirmed"

    def test_bottleneck_phase_validation(self):
        """BottleneckItem rejects invalid phase values."""
        with pytest.raises(Exception):
            BottleneckItem(
                name="Bad Phase",
                phase=5,  # Invalid: must be 0-3
                phase_label="Invalid",
                description="Test",
                claim_indices=[0],
            )

    def test_validation_confidence_range(self):
        """ValidationItem rejects confidence outside 0-1."""
        with pytest.raises(Exception):
            ValidationItem(
                claim_index=0,
                verdict="confirmed",
                confidence=1.5,  # Invalid: must be 0-1
                evidence="Test",
                sources=[],
                search_queries=[],
            )
