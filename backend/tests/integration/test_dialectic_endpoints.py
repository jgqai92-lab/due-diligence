"""Integration tests for IST Phase 4: Dialectic Scrutiny endpoints.

Tests cover:
- POST /api/ist/screens/{id}/dialectic (valid + invalid state)
- GET /api/ist/screens/{id}/dialectic/{side} (all 3 sides + 404)
- GET /api/ist/screens/{id}/synthesis (populated + 404)
- 404 for non-existent screens
- Error format consistency (INV-BE-02)
"""

import json
import pytest


# -- Helpers ------------------------------------------------------------------

VALID_CONTENT = (
    "This is a test content that discusses AI infrastructure scarcity. "
    "NVIDIA's GB300 GPU requires 330,000 units per GW cluster. "
    "Power infrastructure is bottlenecked by 5-year interconnection queues. "
    "Cooling demand is growing 15% CAGR. "
) * 5  # Repeat to exceed 100 char minimum


def _create_screen(client, name="Test Screen", content=None, **kwargs):
    """Helper to create a screen and return the response."""
    payload = {
        "name": name,
        "content": content or VALID_CONTENT,
        "contentType": kwargs.get("content_type", "text"),
    }
    if "hypothesis" in kwargs:
        payload["hypothesis"] = kwargs["hypothesis"]
    return client.post("/api/ist/screens", json=payload)


def _create_dialectic_review(db, screen_id, side, content_dict):
    """Helper to create a dialectic review directly in the DB."""
    from app.models.ist import ISTDialecticReview

    review = ISTDialecticReview(
        screen_id=screen_id,
        side=side,
        content=json.dumps(content_dict),
    )
    db.add(review)
    db.commit()
    return review


def _complete_phase3_steps(db, workflow_run_id):
    """Mark all Phase 1-3 workflow steps as COMPLETED."""
    from app.models.workflow import WorkflowStep

    steps = (
        db.query(WorkflowStep)
        .filter(
            WorkflowStep.workflow_run_id == workflow_run_id,
            WorkflowStep.phase <= 3,
        )
        .all()
    )
    for step in steps:
        step.status = "COMPLETED"
    db.commit()


def _pause_workflow(db, workflow_run_id):
    """Set workflow status to PAUSED (simulating phase boundary)."""
    from app.models.workflow import WorkflowRun

    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()
    if run:
        run.status = "PAUSED"
        run.current_phase = 3
        db.commit()


MOCK_OPTIMIST_CONTENT = {
    "narrative": "## Bull Case\nThe scarcity thesis is compelling...",
    "key_arguments": [
        "GPU supply constrained through 2026",
        "Power infrastructure tailwind",
        "CUDA ecosystem lock-in",
    ],
    "tier_adjustments": [
        {
            "ticker": "EATON",
            "current_tier": 2,
            "proposed_tier": 1,
            "rationale": "Power bottleneck severity underestimated",
        },
    ],
    "conviction_level": "HIGH",
    "risk_discount": 0.2,
}

MOCK_PESSIMIST_CONTENT = {
    "narrative": "## Bear Case\nSeveral concerns...",
    "key_arguments": [
        "Demand deceleration risk",
        "Source bias toward bullish narrative",
        "Custom silicon competition",
    ],
    "tier_adjustments": [
        {
            "ticker": "NVDA",
            "current_tier": 1,
            "proposed_tier": 2,
            "rationale": "Competition erodes monopoly rents",
        },
    ],
    "conviction_level": "MEDIUM",
    "risk_discount": 0.6,
}

MOCK_SYNTHESIS_CONTENT = {
    "narrative": "## Synthesis\nAfter reconciling both perspectives...",
    "disagreements": [
        {
            "topic": "NVIDIA moat durability",
            "optimist_view": "CUDA creates multi-year lock-in",
            "pessimist_view": "Custom silicon erodes monopoly",
            "resolution": "Moat persists for training, fragments for inference",
            "impact_on_tiers": "NVDA stays Tier 1 with reduced conviction",
        },
    ],
    "final_tier_adjustments": [],
    "overall_conviction": "MEDIUM",
    "key_risks": [
        "AI ROI disappointment",
        "Custom silicon adoption faster than expected",
    ],
}


# -- POST /api/ist/screens/{id}/dialectic ------------------------------------


class TestTriggerDialectic:
    """Tests for POST /api/ist/screens/{id}/dialectic."""

    def test_trigger_dialectic_phase3_incomplete(self, client, db):
        """Trigger fails when Phase 3 is not complete (409)."""
        create_resp = _create_screen(client, name="Dialectic Incomplete")
        screen_id = create_resp.json()["id"]

        resp = client.post(f"/api/ist/screens/{screen_id}/dialectic")
        assert resp.status_code == 409
        data = resp.json()
        assert data["detail"]["error"]["code"] == "PHASE_NOT_COMPLETE"

    def test_trigger_dialectic_phase3_complete(self, client, db):
        """Trigger returns 202 when Phase 3 is complete and workflow is PAUSED."""
        create_resp = _create_screen(client, name="Dialectic Valid")
        screen_id = create_resp.json()["id"]
        workflow_run_id = create_resp.json()["workflowRunId"]

        # Complete all Phase 1-3 steps
        _complete_phase3_steps(db, workflow_run_id)
        # Set workflow to PAUSED at phase boundary
        _pause_workflow(db, workflow_run_id)

        resp = client.post(f"/api/ist/screens/{screen_id}/dialectic")
        assert resp.status_code == 202
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["message"] == "Dialectic analysis started"
        assert data["status"] == "RUNNING"

    def test_trigger_dialectic_nonexistent_screen(self, client):
        """Trigger returns 404 for nonexistent screen."""
        resp = client.post("/api/ist/screens/99999/dialectic")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "SCREEN_NOT_FOUND"

    def test_trigger_dialectic_already_started(self, client, db):
        """Trigger returns 409 when dialectic steps are already running."""
        from app.models.workflow import WorkflowStep

        create_resp = _create_screen(client, name="Dialectic Already")
        screen_id = create_resp.json()["id"]
        workflow_run_id = create_resp.json()["workflowRunId"]

        _complete_phase3_steps(db, workflow_run_id)
        _pause_workflow(db, workflow_run_id)

        # Mark optimist step as COMPLETED to simulate already started
        optimist_step = (
            db.query(WorkflowStep)
            .filter(
                WorkflowStep.workflow_run_id == workflow_run_id,
                WorkflowStep.step_name == "dialectic_optimist",
            )
            .first()
        )
        optimist_step.status = "COMPLETED"
        db.commit()

        resp = client.post(f"/api/ist/screens/{screen_id}/dialectic")
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"]["code"] == "ALREADY_STARTED"


# -- GET /api/ist/screens/{id}/dialectic/{side} ------------------------------


class TestGetDialecticReview:
    """Tests for GET /api/ist/screens/{id}/dialectic/{side}."""

    def test_get_optimist_review(self, client, db):
        """Successfully get optimist review."""
        create_resp = _create_screen(client, name="Get Optimist")
        screen_id = create_resp.json()["id"]

        _create_dialectic_review(db, screen_id, "OPTIMIST", MOCK_OPTIMIST_CONTENT)

        resp = client.get(f"/api/ist/screens/{screen_id}/dialectic/optimist")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["side"] == "OPTIMIST"
        assert data["content"]["convictionLevel"] == "HIGH"
        assert len(data["content"]["keyArguments"]) == 3
        assert data["content"]["riskDiscount"] == 0.2
        assert data["createdAt"] is not None

    def test_get_pessimist_review(self, client, db):
        """Successfully get pessimist review."""
        create_resp = _create_screen(client, name="Get Pessimist")
        screen_id = create_resp.json()["id"]

        _create_dialectic_review(db, screen_id, "PESSIMIST", MOCK_PESSIMIST_CONTENT)

        resp = client.get(f"/api/ist/screens/{screen_id}/dialectic/pessimist")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["side"] == "PESSIMIST"
        assert data["content"]["convictionLevel"] == "MEDIUM"
        assert data["content"]["riskDiscount"] == 0.6

    def test_get_synthesis_review(self, client, db):
        """Successfully get synthesis review via dialectic endpoint."""
        create_resp = _create_screen(client, name="Get Synthesis")
        screen_id = create_resp.json()["id"]

        _create_dialectic_review(db, screen_id, "SYNTHESIS", MOCK_SYNTHESIS_CONTENT)

        resp = client.get(f"/api/ist/screens/{screen_id}/dialectic/synthesis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["side"] == "SYNTHESIS"
        assert data["content"]["overallConviction"] == "MEDIUM"
        assert len(data["content"]["disagreements"]) == 1

    def test_get_review_not_found(self, client):
        """Returns 404 when review does not exist."""
        create_resp = _create_screen(client, name="No Review")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/dialectic/optimist")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "REVIEW_NOT_FOUND"

    def test_get_review_invalid_side(self, client):
        """Returns 400 for invalid side parameter."""
        create_resp = _create_screen(client, name="Bad Side")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/dialectic/neutral")
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"]["code"] == "INVALID_SIDE"

    def test_get_review_nonexistent_screen(self, client):
        """Returns 404 for nonexistent screen."""
        resp = client.get("/api/ist/screens/99999/dialectic/optimist")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "SCREEN_NOT_FOUND"

    def test_get_review_case_insensitive(self, client, db):
        """Side parameter is case-insensitive."""
        create_resp = _create_screen(client, name="Case Test")
        screen_id = create_resp.json()["id"]

        _create_dialectic_review(db, screen_id, "OPTIMIST", MOCK_OPTIMIST_CONTENT)

        # Uppercase should work
        resp = client.get(f"/api/ist/screens/{screen_id}/dialectic/OPTIMIST")
        assert resp.status_code == 200

        # Mixed case should work
        resp = client.get(f"/api/ist/screens/{screen_id}/dialectic/Optimist")
        assert resp.status_code == 200


# -- GET /api/ist/screens/{id}/synthesis -------------------------------------


class TestGetSynthesis:
    """Tests for GET /api/ist/screens/{id}/synthesis."""

    def test_get_synthesis_format(self, client, db):
        """Synthesis endpoint returns synthesis-specific format."""
        create_resp = _create_screen(client, name="Synthesis Format")
        screen_id = create_resp.json()["id"]

        _create_dialectic_review(db, screen_id, "SYNTHESIS", MOCK_SYNTHESIS_CONTENT)

        resp = client.get(f"/api/ist/screens/{screen_id}/synthesis")
        assert resp.status_code == 200
        data = resp.json()

        # Verify synthesis-specific format (different from generic dialectic endpoint)
        assert data["screenId"] == screen_id
        assert data["narrative"] == MOCK_SYNTHESIS_CONTENT["narrative"]
        assert len(data["disagreements"]) == 1
        assert data["disagreements"][0]["topic"] == "NVIDIA moat durability"
        assert data["finalTierAdjustments"] == []
        assert data["overallConviction"] == "MEDIUM"
        assert len(data["keyRisks"]) == 2
        assert data["createdAt"] is not None

    def test_get_synthesis_not_found(self, client):
        """Returns 404 when synthesis review does not exist."""
        create_resp = _create_screen(client, name="No Synthesis")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/synthesis")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "SYNTHESIS_NOT_FOUND"

    def test_get_synthesis_nonexistent_screen(self, client):
        """Returns 404 for nonexistent screen."""
        resp = client.get("/api/ist/screens/99999/synthesis")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "SCREEN_NOT_FOUND"


# -- Error format consistency -------------------------------------------------


class TestErrorFormatConsistency:
    """Verify all new endpoints return consistent error format (INV-BE-02)."""

    @pytest.mark.parametrize("endpoint", [
        "/api/ist/screens/99999/dialectic/optimist",
        "/api/ist/screens/99999/dialectic/pessimist",
        "/api/ist/screens/99999/dialectic/synthesis",
        "/api/ist/screens/99999/synthesis",
    ])
    def test_404_error_format(self, client, endpoint):
        """All GET endpoints use standard error format for 404."""
        resp = client.get(endpoint)
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert "error" in data["detail"]
        assert "code" in data["detail"]["error"]
        assert "message" in data["detail"]["error"]

    def test_post_dialectic_404_format(self, client):
        """POST dialectic uses standard error format for 404."""
        resp = client.post("/api/ist/screens/99999/dialectic")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert "error" in data["detail"]
        assert "code" in data["detail"]["error"]
