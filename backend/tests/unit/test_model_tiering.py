"""Unit tests for model tiering infrastructure.

Tests verify:
- MODEL_IDS mapping contains correct model IDs
- resolve_model_id resolves tier names correctly
- resolve_model_id passes through full model IDs
- resolve_model_id falls back to settings.claude_model for unknown values
- IST and HFRT step definitions all have a "model" field
- Step creation stores model_tier in the database
- call_claude and call_claude_raw use resolve_model_id
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel

import app.services.claude_client as claude_client_module
from app.services.claude_client import MODEL_IDS, resolve_model_id


# ── Test response model ──────────────────────────────────────────────────────

class DummyResponse(BaseModel):
    answer: str


def _make_fake_api_response(text: str = '{"answer": "test"}'):
    """Create a mock Anthropic API response object."""
    content_block = MagicMock()
    content_block.text = text
    usage = MagicMock()
    usage.input_tokens = 100
    usage.output_tokens = 50
    response = MagicMock()
    response.content = [content_block]
    response.usage = usage
    return response


@pytest.fixture(autouse=True)
def reset_semaphore():
    """Reset the module-level semaphore before each test."""
    claude_client_module._api_semaphore = None
    yield
    claude_client_module._api_semaphore = None


# ── MODEL_IDS mapping tests ─────────────────────────────────────────────────

class TestModelIDs:
    """Tests for the MODEL_IDS constant."""

    def test_opus_mapping_exists(self):
        assert "opus" in MODEL_IDS

    def test_sonnet_mapping_exists(self):
        assert "sonnet" in MODEL_IDS

    def test_opus_model_id(self):
        assert MODEL_IDS["opus"] == "claude-opus-4-6"

    def test_sonnet_model_id(self):
        assert MODEL_IDS["sonnet"] == "claude-sonnet-4-6"

    def test_only_two_tiers(self):
        """Only opus and sonnet should be in the mapping."""
        assert set(MODEL_IDS.keys()) == {"opus", "sonnet"}


# ── resolve_model_id tests ──────────────────────────────────────────────────

class TestResolveModelId:
    """Tests for the resolve_model_id function."""

    def test_resolves_opus(self):
        assert resolve_model_id("opus") == "claude-opus-4-6"

    def test_resolves_sonnet(self):
        assert resolve_model_id("sonnet") == "claude-sonnet-4-6"

    def test_passes_through_full_model_id(self):
        """Full model IDs with hyphens should pass through unchanged."""
        assert resolve_model_id("claude-sonnet-4-20250514") == "claude-sonnet-4-20250514"

    def test_passes_through_custom_model_id(self):
        """Any string with a hyphen that is not a tier name passes through."""
        assert resolve_model_id("claude-custom-model") == "claude-custom-model"

    def test_none_falls_back_to_settings(self):
        """None should fall back to settings.claude_model."""
        from app.config import settings
        assert resolve_model_id(None) == settings.claude_model

    def test_empty_string_falls_back_to_settings(self):
        """Empty string should fall back to settings.claude_model."""
        from app.config import settings
        assert resolve_model_id("") == settings.claude_model

    def test_unknown_tier_falls_back_to_settings(self):
        """Unknown tier names without hyphens fall back to settings."""
        from app.config import settings
        assert resolve_model_id("haiku") == settings.claude_model

    def test_none_value_does_not_match_model_ids(self):
        """Ensure 'none' (gate steps) falls back to settings, not a model ID."""
        from app.config import settings
        # "none" is not in MODEL_IDS and has no hyphen
        assert resolve_model_id("none") == settings.claude_model


# ── Step definition completeness tests ───────────────────────────────────────

class TestStepDefinitionCompleteness:
    """Verify all workflow step definitions include the model field."""

    def test_ist_steps_all_have_model_field(self):
        from app.routers.ist import IST_WORKFLOW_STEPS
        for step in IST_WORKFLOW_STEPS:
            assert "model" in step, (
                f"IST step '{step['step_name']}' missing 'model' field"
            )

    def test_hfrt_steps_all_have_model_field(self):
        from app.routers.hfrt import HFRT_WORKFLOW_STEPS
        for step in HFRT_WORKFLOW_STEPS:
            assert "model" in step, (
                f"HFRT step '{step['step_name']}' missing 'model' field"
            )

    def test_bridge_hfrt_steps_all_have_model_field(self):
        from app.services.bridge import HFRT_WORKFLOW_STEPS
        for step in HFRT_WORKFLOW_STEPS:
            assert "model" in step, (
                f"Bridge HFRT step '{step['step_name']}' missing 'model' field"
            )

    def test_ist_model_values_are_valid(self):
        """All IST model values must be opus, sonnet, or none."""
        from app.routers.ist import IST_WORKFLOW_STEPS
        valid = {"opus", "sonnet", "none"}
        for step in IST_WORKFLOW_STEPS:
            assert step["model"] in valid, (
                f"IST step '{step['step_name']}' has invalid model: {step['model']}"
            )

    def test_hfrt_model_values_are_valid(self):
        """All HFRT model values must be opus, sonnet, or none."""
        from app.routers.hfrt import HFRT_WORKFLOW_STEPS
        valid = {"opus", "sonnet", "none"}
        for step in HFRT_WORKFLOW_STEPS:
            assert step["model"] in valid, (
                f"HFRT step '{step['step_name']}' has invalid model: {step['model']}"
            )

    def test_ist_gate_steps_are_none(self):
        """Gate steps should use model='none' (they don't call Claude)."""
        from app.routers.ist import IST_WORKFLOW_STEPS
        gate_steps = {s["step_name"] for s in IST_WORKFLOW_STEPS if "gate" in s["step_name"] or s["step_name"] == "invariant_check"}
        for step in IST_WORKFLOW_STEPS:
            if step["step_name"] in gate_steps:
                assert step["model"] == "none", (
                    f"Gate step '{step['step_name']}' should use model='none', "
                    f"got '{step['model']}'"
                )

    def test_hfrt_gate_steps_are_none(self):
        """Gate steps should use model='none' (they don't call Claude)."""
        from app.routers.hfrt import HFRT_WORKFLOW_STEPS
        gate_names = {"research_sufficiency_gate", "dd_sufficiency_gate", "thesis_coherence_gate", "complete"}
        for step in HFRT_WORKFLOW_STEPS:
            if step["step_name"] in gate_names:
                assert step["model"] == "none", (
                    f"Gate step '{step['step_name']}' should use model='none', "
                    f"got '{step['model']}'"
                )

    def test_bridge_and_router_hfrt_steps_match(self):
        """Bridge and router HFRT step definitions must have the same model assignments."""
        from app.routers.hfrt import HFRT_WORKFLOW_STEPS as router_steps
        from app.services.bridge import HFRT_WORKFLOW_STEPS as bridge_steps

        assert len(router_steps) == len(bridge_steps)
        for r, b in zip(router_steps, bridge_steps):
            assert r["step_name"] == b["step_name"]
            assert r["model"] == b["model"], (
                f"Model mismatch for step '{r['step_name']}': "
                f"router={r['model']}, bridge={b['model']}"
            )


# ── Database integration tests ───────────────────────────────────────────────

class TestModelTierInDatabase:
    """Tests for model_tier column in workflow_steps table."""

    def test_step_model_tier_stored_on_create(self, db):
        """Creating a screen stores model_tier on each workflow step."""
        from app.models.workflow import WorkflowRun, WorkflowStep
        from app.routers.ist import IST_WORKFLOW_STEPS
        import json

        run = WorkflowRun(
            workflow_type="IST",
            name="Model Tier Test",
            status="PENDING",
            current_phase=0,
        )
        db.add(run)
        db.flush()

        for step_def in IST_WORKFLOW_STEPS:
            step = WorkflowStep(
                workflow_run_id=run.id,
                step_name=step_def["step_name"],
                phase=step_def["phase"],
                phase_name=step_def["phase_name"],
                step_order=step_def["step_order"],
                status="PENDING",
                depends_on=json.dumps(step_def.get("depends_on", [])),
                model_tier=step_def.get("model", "opus"),
            )
            db.add(step)

        db.commit()

        # Query back and verify
        steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == run.id)
            .order_by(WorkflowStep.step_order)
            .all()
        )

        assert len(steps) == len(IST_WORKFLOW_STEPS)

        # Verify specific known tiers
        step_tiers = {s.step_name: s.model_tier for s in steps}
        assert step_tiers["content_extraction"] == "sonnet"  # data structuring
        assert step_tiers["source_bias_assessment"] == "sonnet"
        assert step_tiers["bottleneck_mapping"] == "opus"  # causal reasoning
        assert step_tiers["demand_modeling"] == "sonnet"  # Perplexity provides TAM data
        assert step_tiers["external_validation"] == "sonnet"  # Perplexity does search
        assert step_tiers["content_sufficiency_gate"] == "none"
        assert step_tiers["effects_analysis"] == "opus"  # 2nd/3rd order reasoning
        assert step_tiers["dialectic_synthesis"] == "opus"  # reconciliation reasoning
        assert step_tiers["master_screen"] == "sonnet"  # ranking from existing data
        assert step_tiers["report_generation"] == "sonnet"  # prose from existing data
        assert step_tiers["hfrt_handoff_generation"] == "sonnet"

    def test_model_tier_nullable(self, db):
        """model_tier can be NULL for backwards compatibility."""
        from app.models.workflow import WorkflowRun, WorkflowStep

        run = WorkflowRun(
            workflow_type="IST",
            name="Nullable Test",
            status="PENDING",
            current_phase=0,
        )
        db.add(run)
        db.flush()

        step = WorkflowStep(
            workflow_run_id=run.id,
            step_name="test_step",
            phase=1,
            phase_name="Test",
            step_order=1,
            status="PENDING",
            # model_tier intentionally omitted -- should be NULL
        )
        db.add(step)
        db.commit()

        result = db.query(WorkflowStep).filter(WorkflowStep.id == step.id).first()
        assert result.model_tier is None


# ── call_claude model resolution tests ───────────────────────────────────────

class TestCallClaudeModelResolution:
    """Tests that call_claude and call_claude_raw resolve model tiers."""

    @pytest.mark.asyncio
    async def test_call_claude_uses_opus_tier(self):
        """Passing model='opus' should resolve to the opus model ID."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_fake_api_response()
        )

        with patch("app.services.claude_client.get_client", return_value=mock_client):
            await claude_client_module.call_claude(
                system_prompt="test",
                user_prompt="test",
                response_model=DummyResponse,
                model="opus",
            )

        # Verify the model ID passed to the API
        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-opus-4-6"

    @pytest.mark.asyncio
    async def test_call_claude_uses_sonnet_tier(self):
        """Passing model='sonnet' should resolve to the sonnet model ID."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_fake_api_response()
        )

        with patch("app.services.claude_client.get_client", return_value=mock_client):
            await claude_client_module.call_claude(
                system_prompt="test",
                user_prompt="test",
                response_model=DummyResponse,
                model="sonnet",
            )

        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_call_claude_raw_uses_tier(self):
        """call_claude_raw also resolves tier names."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_fake_api_response(text="raw text")
        )

        with patch("app.services.claude_client.get_client", return_value=mock_client):
            await claude_client_module.call_claude_raw(
                system_prompt="test",
                user_prompt="test",
                model="opus",
            )

        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-opus-4-6"

    @pytest.mark.asyncio
    async def test_call_claude_default_model(self):
        """Passing model=None should use settings.claude_model."""
        from app.config import settings

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_fake_api_response()
        )

        with patch("app.services.claude_client.get_client", return_value=mock_client):
            await claude_client_module.call_claude(
                system_prompt="test",
                user_prompt="test",
                response_model=DummyResponse,
                # model not specified -- should use default
            )

        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == settings.claude_model


# ── get_step_model_tier tests ─────────────────────────────────────────────


class TestGetStepModelTier:
    """Tests for get_step_model_tier lookup function."""

    @pytest.mark.asyncio
    async def test_returns_model_tier_from_db(self, db):
        """Should return the model_tier stored on the workflow step."""
        from app.models.workflow import WorkflowRun, WorkflowStep
        from app.services.claude_client import get_step_model_tier

        run = WorkflowRun(
            workflow_type="IST",
            name="Tier Lookup Test",
            status="RUNNING",
            current_phase=1,
        )
        db.add(run)
        db.flush()

        step = WorkflowStep(
            workflow_run_id=run.id,
            step_name="bottleneck_mapping",
            phase=1,
            phase_name="Test",
            step_order=1,
            status="RUNNING",
            model_tier="opus",
        )
        db.add(step)
        db.commit()

        # Patch SessionLocal so get_step_model_tier uses the test session
        with patch("app.database.SessionLocal", return_value=db):
            result = await get_step_model_tier(run.id, "bottleneck_mapping")
        assert result == "opus"

    @pytest.mark.asyncio
    async def test_returns_none_when_step_not_found(self):
        """Should return None if no matching step exists."""
        from app.services.claude_client import get_step_model_tier

        result = await get_step_model_tier(999999, "nonexistent_step")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_model_tier_is_null(self, db):
        """Should return None if model_tier column is NULL."""
        from app.models.workflow import WorkflowRun, WorkflowStep
        from app.services.claude_client import get_step_model_tier

        run = WorkflowRun(
            workflow_type="IST",
            name="Null Tier Test",
            status="RUNNING",
            current_phase=1,
        )
        db.add(run)
        db.flush()

        step = WorkflowStep(
            workflow_run_id=run.id,
            step_name="test_step",
            phase=1,
            phase_name="Test",
            step_order=1,
            status="RUNNING",
            # model_tier intentionally omitted
        )
        db.add(step)
        db.commit()

        result = await get_step_model_tier(run.id, "test_step")
        assert result is None


# ── Perplexity client tests ───────────────────────────────────────────────


class TestPerplexityClient:
    """Tests for the Perplexity client module."""

    def test_is_available_without_key(self):
        """Should return False when no API key is configured."""
        from app.services.perplexity_client import is_available
        with patch("app.services.perplexity_client.settings") as mock_settings:
            mock_settings.perplexity_api_key = ""
            assert is_available() is False

    def test_is_available_with_key(self):
        """Should return True when API key is configured."""
        from app.services.perplexity_client import is_available
        with patch("app.services.perplexity_client.settings") as mock_settings:
            mock_settings.perplexity_api_key = "pplx-test-key"
            assert is_available() is True

    def test_token_tracking(self):
        """Per-workflow token tracking should work correctly."""
        from app.services.perplexity_client import (
            get_workflow_perplexity_usage,
            clear_workflow_perplexity_usage,
            _workflow_perplexity_usage,
        )

        # Clean state
        _workflow_perplexity_usage.clear()

        assert get_workflow_perplexity_usage(1) == 0

        _workflow_perplexity_usage[1] = 500
        assert get_workflow_perplexity_usage(1) == 500

        clear_workflow_perplexity_usage(1)
        assert get_workflow_perplexity_usage(1) == 0

    @pytest.mark.asyncio
    async def test_search_and_analyze_raises_without_key(self):
        """Should raise RuntimeError when Perplexity is not configured."""
        from app.services.perplexity_client import search_and_analyze
        with patch("app.services.perplexity_client.settings") as mock_settings:
            mock_settings.perplexity_api_key = ""
            with pytest.raises(RuntimeError, match="not configured"):
                await search_and_analyze(
                    system_prompt="test",
                    user_prompt="test",
                )
