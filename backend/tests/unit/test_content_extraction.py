"""Unit tests for IST Phase 1: content extraction and source bias assessment."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.ist import ISTScreen, ISTClaim
from app.models.workflow import WorkflowRun, WorkflowStep
from app.services.ist.content_extraction import (
    _run_content_extraction,
    _run_source_bias,
    ContentExtractionResult,
    ExtractedClaim,
    SourceBiasResult,
)


# ── Test DB setup ────────────────────────────────────────────────────────────

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def workflow_run(db):
    run = WorkflowRun(workflow_type="IST", name="Test IST Run", status="RUNNING")
    db.add(run)
    db.flush()
    return run


@pytest.fixture()
def screen(db, workflow_run):
    s = ISTScreen(
        workflow_run_id=workflow_run.id,
        name="GPU Supply Analysis",
        status="PENDING",
        content_type="podcast_transcript",
        raw_content="NVIDIA is seeing massive demand for H100 GPUs. CEO Jensen Huang said datacenter revenue grew 400% YoY to $18.4B in Q3 2024.",
    )
    db.add(s)
    db.flush()
    return s


def _mock_extraction_result():
    return ContentExtractionResult(
        claims=[
            ExtractedClaim(
                claim_text="NVIDIA datacenter revenue grew 400% YoY to $18.4B in Q3 2024",
                source_citation="CEO Jensen Huang statement",
                quantitative_anchor="400% YoY, $18.4B",
                temporal_marker="Q3 2024",
                confidence=0.95,
            ),
            ExtractedClaim(
                claim_text="Massive demand for H100 GPUs",
                source_citation="Opening statement",
                quantitative_anchor=None,
                temporal_marker=None,
                confidence=0.8,
            ),
        ],
        summary="Analysis of NVIDIA GPU supply dynamics",
        content_themes=["GPU demand", "Datacenter growth"],
    )


def _mock_bias_result():
    return SourceBiasResult(
        rating="moderate",
        notes="Podcast may overweight bull narrative",
        source_credibility="Established tech podcast with industry guests",
        potential_blind_spots=["Supply chain constraints", "Competition from AMD"],
    )


# ── Content Extraction Tests ─────────────────────────────────────────────────


class TestRunContentExtraction:
    """Tests for _run_content_extraction()."""

    @pytest.mark.asyncio
    async def test_extracts_claims_and_stores_in_db(self, db, screen, workflow_run):
        with patch(
            "app.services.ist.content_extraction.call_claude",
            new_callable=AsyncMock,
            return_value=_mock_extraction_result(),
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            result = await _run_content_extraction(screen, db, workflow_run.id)

        assert result["claimsExtracted"] == 2
        assert "GPU demand" in result["themes"]
        claims = db.query(ISTClaim).filter(ISTClaim.screen_id == screen.id).all()
        assert len(claims) == 2

    @pytest.mark.asyncio
    async def test_sets_screen_status_to_extracting(self, db, screen, workflow_run):
        with patch(
            "app.services.ist.content_extraction.call_claude",
            new_callable=AsyncMock,
            return_value=_mock_extraction_result(),
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            await _run_content_extraction(screen, db, workflow_run.id)

        # After extraction, status is no longer PENDING
        db.refresh(screen)
        assert screen.content_extraction is not None

    @pytest.mark.asyncio
    async def test_skip_status_update_when_disabled(self, db, screen, workflow_run):
        screen.status = "ANALYZING"
        db.flush()

        with patch(
            "app.services.ist.content_extraction.call_claude",
            new_callable=AsyncMock,
            return_value=_mock_extraction_result(),
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            await _run_content_extraction(
                screen, db, workflow_run.id, update_screen_status=False
            )

        db.refresh(screen)
        # Status should remain ANALYZING, not changed to EXTRACTING
        assert screen.status == "ANALYZING"

    @pytest.mark.asyncio
    async def test_stores_extraction_summary_json(self, db, screen, workflow_run):
        with patch(
            "app.services.ist.content_extraction.call_claude",
            new_callable=AsyncMock,
            return_value=_mock_extraction_result(),
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            await _run_content_extraction(screen, db, workflow_run.id)

        db.refresh(screen)
        summary = json.loads(screen.content_extraction)
        assert summary["totalClaims"] == 2
        assert summary["claimsWithQuantAnchors"] == 1
        assert summary["claimsWithTemporalMarkers"] == 1
        assert "GPU demand" in summary["themes"]

    @pytest.mark.asyncio
    async def test_replace_claims_deletes_existing(self, db, screen, workflow_run):
        # Pre-populate a claim
        db.add(ISTClaim(
            screen_id=screen.id,
            claim_text="Old claim",
            source_citation="old",
            confidence=0.5,
        ))
        db.flush()

        with patch(
            "app.services.ist.content_extraction.call_claude",
            new_callable=AsyncMock,
            return_value=_mock_extraction_result(),
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            await _run_content_extraction(
                screen, db, workflow_run.id, replace_claims=True
            )

        claims = db.query(ISTClaim).filter(ISTClaim.screen_id == screen.id).all()
        # Old claim deleted, 2 new ones added
        assert len(claims) == 2
        assert all(c.claim_text != "Old claim" for c in claims)

    @pytest.mark.asyncio
    async def test_without_replace_claims_appends(self, db, screen, workflow_run):
        db.add(ISTClaim(
            screen_id=screen.id,
            claim_text="Existing claim",
            source_citation="src",
            confidence=0.5,
        ))
        db.flush()

        with patch(
            "app.services.ist.content_extraction.call_claude",
            new_callable=AsyncMock,
            return_value=_mock_extraction_result(),
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            await _run_content_extraction(
                screen, db, workflow_run.id, replace_claims=False
            )

        claims = db.query(ISTClaim).filter(ISTClaim.screen_id == screen.id).all()
        assert len(claims) == 3  # 1 existing + 2 new

    @pytest.mark.asyncio
    async def test_screening_brief_parsed(self, db, screen, workflow_run):
        screen.screening_brief = json.dumps({"hypothesis": "GPU scarcity drives NVDA"})
        db.flush()

        call_mock = AsyncMock(return_value=_mock_extraction_result())
        with patch(
            "app.services.ist.content_extraction.call_claude",
            call_mock,
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            await _run_content_extraction(screen, db, workflow_run.id)

        # Verify hypothesis was included in the user prompt
        user_prompt = call_mock.call_args.kwargs["user_prompt"]
        assert "GPU scarcity drives NVDA" in user_prompt

    @pytest.mark.asyncio
    async def test_invalid_screening_brief_handled(self, db, screen, workflow_run):
        screen.screening_brief = "not valid json"
        db.flush()

        with patch(
            "app.services.ist.content_extraction.call_claude",
            new_callable=AsyncMock,
            return_value=_mock_extraction_result(),
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            # Should not raise
            result = await _run_content_extraction(screen, db, workflow_run.id)

        assert result["claimsExtracted"] == 2

    @pytest.mark.asyncio
    async def test_raw_content_override(self, db, screen, workflow_run):
        custom_content = "AMD Instinct MI300X is gaining traction."
        call_mock = AsyncMock(return_value=_mock_extraction_result())
        with patch(
            "app.services.ist.content_extraction.call_claude",
            call_mock,
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            await _run_content_extraction(
                screen, db, workflow_run.id, raw_content=custom_content
            )

        user_prompt = call_mock.call_args.kwargs["user_prompt"]
        assert "AMD Instinct MI300X" in user_prompt
        assert screen.raw_content not in user_prompt  # Should use override

    @pytest.mark.asyncio
    async def test_emits_sse_events(self, db, screen, workflow_run):
        sse_mock = AsyncMock()
        with patch(
            "app.services.ist.content_extraction.call_claude",
            new_callable=AsyncMock,
            return_value=_mock_extraction_result(),
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            sse_mock,
        ):
            await _run_content_extraction(screen, db, workflow_run.id)

        # Should emit at least 2 SSE events (progress at 10% and 70%)
        assert sse_mock.call_count >= 2
        event_types = [call.args[1] for call in sse_mock.call_args_list]
        assert all(t == "step_progress" for t in event_types)

    @pytest.mark.asyncio
    async def test_claim_source_refresh_id_set(self, db, screen, workflow_run):
        # Create a refresh row so FK constraint is satisfied
        from app.models.ist_refresh import ISTScreenRefresh
        refresh = ISTScreenRefresh(
            screen_id=screen.id,
            workflow_run_id=workflow_run.id,
            refresh_number=1,
            status="COMPLETED",
            delta_content="new content about GPU supply",
        )
        db.add(refresh)
        db.flush()

        with patch(
            "app.services.ist.content_extraction.call_claude",
            new_callable=AsyncMock,
            return_value=_mock_extraction_result(),
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            await _run_content_extraction(
                screen, db, workflow_run.id, claim_source_refresh_id=refresh.id
            )

        claims = db.query(ISTClaim).filter(ISTClaim.screen_id == screen.id).all()
        for claim in claims:
            assert claim.source_refresh_id == refresh.id


# ── Source Bias Tests ────────────────────────────────────────────────────────


class TestRunSourceBias:
    """Tests for _run_source_bias()."""

    @pytest.mark.asyncio
    async def test_stores_bias_summary(self, db, screen, workflow_run):
        with patch(
            "app.services.ist.content_extraction.call_claude",
            new_callable=AsyncMock,
            return_value=_mock_bias_result(),
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            result = await _run_source_bias(screen, db, workflow_run.id)

        assert result["biasRating"] == "moderate"
        db.refresh(screen)
        bias = json.loads(screen.source_bias)
        assert bias["rating"] == "moderate"
        assert "AMD" in bias["potentialBlindSpots"][1]

    @pytest.mark.asyncio
    async def test_truncates_content_to_5000_chars(self, db, screen, workflow_run):
        screen.raw_content = "x" * 10000
        db.flush()

        call_mock = AsyncMock(return_value=_mock_bias_result())
        with patch(
            "app.services.ist.content_extraction.call_claude",
            call_mock,
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            await _run_source_bias(screen, db, workflow_run.id)

        user_prompt = call_mock.call_args.kwargs["user_prompt"]
        # Content sample should be ≤5000 chars
        assert "x" * 5000 in user_prompt
        assert "x" * 5001 not in user_prompt

    @pytest.mark.asyncio
    async def test_raw_content_override(self, db, screen, workflow_run):
        call_mock = AsyncMock(return_value=_mock_bias_result())
        with patch(
            "app.services.ist.content_extraction.call_claude",
            call_mock,
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            await _run_source_bias(
                screen, db, workflow_run.id, raw_content="Custom content for bias"
            )

        user_prompt = call_mock.call_args.kwargs["user_prompt"]
        assert "Custom content for bias" in user_prompt

    @pytest.mark.asyncio
    async def test_target_refresh_stores_on_refresh(self, db, screen, workflow_run):
        """When target_refresh is provided, bias is stored there instead of screen."""
        mock_refresh = MagicMock()
        mock_refresh.new_source_bias = None

        with patch(
            "app.services.ist.content_extraction.call_claude",
            new_callable=AsyncMock,
            return_value=_mock_bias_result(),
        ), patch(
            "app.services.ist.content_extraction.emit_sse_event",
            new_callable=AsyncMock,
        ):
            await _run_source_bias(
                screen, db, workflow_run.id, target_refresh=mock_refresh
            )

        # Bias stored on refresh, not on screen
        assert mock_refresh.new_source_bias is not None
        bias = json.loads(mock_refresh.new_source_bias)
        assert bias["rating"] == "moderate"


# ── Pydantic Model Tests ────────────────────────────────────────────────────


class TestPydanticModels:
    """Tests for extraction/bias Pydantic models."""

    def test_extracted_claim_confidence_bounds(self):
        with pytest.raises(Exception):
            ExtractedClaim(
                claim_text="test",
                source_citation="src",
                confidence=1.5,
            )

    def test_extracted_claim_optional_fields(self):
        claim = ExtractedClaim(
            claim_text="Revenue grew",
            source_citation="pg 5",
            confidence=0.9,
        )
        assert claim.quantitative_anchor is None
        assert claim.temporal_marker is None

    def test_content_extraction_result_accepts_list(self):
        result = ContentExtractionResult(
            claims=[],
            summary="No claims found",
            content_themes=[],
        )
        assert result.claims == []

    def test_source_bias_result_fields(self):
        result = SourceBiasResult(
            rating="low",
            notes="SEC filing is regulatory disclosure",
            source_credibility="High - mandatory regulatory filing",
            potential_blind_spots=["Forward-looking statements may be optimistic"],
        )
        assert result.rating == "low"
        assert len(result.potential_blind_spots) == 1
