"""Integration tests for IST (Investment Screening Team) endpoints.

Tests cover:
- POST /api/ist/screens — screen creation with workflow + steps
- GET /api/ist/screens — screen listing with filters and pagination
- GET /api/ist/screens/{id} — screen detail
- GET /api/ist/screens/{id}/claims — claims list with filters
- PUT /api/ist/screens/{id}/brief — brief update (only when PAUSED)
- Error handling: 404, 400, 409, 429 cases
"""

import json
import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────

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
    if "constraints" in kwargs:
        payload["constraints"] = kwargs["constraints"]
    if "frameworks" in kwargs:
        payload["frameworks"] = kwargs["frameworks"]
    return client.post("/api/ist/screens", json=payload)


# ── POST /api/ist/screens ────────────────────────────────────────────────────


class TestCreateScreen:
    """Tests for POST /api/ist/screens."""

    def test_create_screen_success(self, client):
        """Creating a screen returns 201 with correct fields."""
        resp = _create_screen(
            client,
            name="AI Data Center Scarcity",
            hypothesis="AI buildout creates scarcity",
            content_type="podcast_transcript",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "AI Data Center Scarcity"
        assert data["status"] == "PENDING"
        assert data["contentType"] == "podcast_transcript"
        assert data["hypothesis"] == "AI buildout creates scarcity"
        assert "id" in data
        assert "workflowRunId" in data
        assert "createdAt" in data

    def test_create_screen_creates_workflow_run(self, client, db):
        """Creating a screen also creates a WorkflowRun with type=IST."""
        from app.models.workflow import WorkflowRun

        resp = _create_screen(client, name="Test Screen")
        assert resp.status_code == 201

        run_id = resp.json()["workflowRunId"]
        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        assert run is not None
        assert run.workflow_type == "IST"
        assert run.status == "PENDING"
        assert run.name == "Test Screen"

    def test_create_screen_creates_workflow_steps(self, client, db):
        """Creating a screen creates all 22 IST workflow steps."""
        from app.models.workflow import WorkflowStep

        resp = _create_screen(client, name="Steps Test")
        assert resp.status_code == 201

        run_id = resp.json()["workflowRunId"]
        steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == run_id)
            .order_by(WorkflowStep.step_order)
            .all()
        )
        assert len(steps) == 22

        # Verify first and last steps
        assert steps[0].step_name == "content_extraction"
        assert steps[0].phase == 1
        assert steps[0].phase_name == "Content Extraction"
        assert steps[0].step_order == 1
        assert steps[0].status == "PENDING"
        assert steps[0].model_tier == "opus"

        assert steps[-1].step_name == "hfrt_handoff_generation"
        assert steps[-1].phase == 5
        assert steps[-1].phase_name == "Final Synthesis"
        assert steps[-1].step_order == 22
        assert steps[-1].model_tier == "sonnet"

    def test_create_screen_stores_screening_brief(self, client, db):
        """Screening brief is stored as validated JSON in ISTScreen."""
        from app.models.ist import ISTScreen

        resp = _create_screen(
            client,
            name="Brief Test",
            hypothesis="Test hypothesis",
            constraints={"minMarketCap": 1000000000},
            frameworks=["scarcity_scoring"],
        )
        assert resp.status_code == 201
        screen_id = resp.json()["id"]

        screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
        assert screen is not None
        brief = json.loads(screen.screening_brief)
        assert brief["hypothesis"] == "Test hypothesis"
        assert brief["constraints"]["minMarketCap"] == 1000000000
        assert brief["frameworks"] == ["scarcity_scoring"]

    def test_create_screen_default_content_type(self, client):
        """Content type defaults to 'text' if not provided."""
        resp = _create_screen(client, name="Default Type")
        assert resp.status_code == 201
        assert resp.json()["contentType"] == "text"

    def test_create_screen_rejects_short_content(self, client):
        """Content shorter than 100 characters is rejected."""
        resp = client.post(
            "/api/ist/screens",
            json={"name": "Short", "content": "Too short content."},
        )
        assert resp.status_code == 422

    def test_create_screen_rejects_empty_name(self, client):
        """Empty name is rejected."""
        resp = client.post(
            "/api/ist/screens",
            json={"name": "   ", "content": VALID_CONTENT},
        )
        assert resp.status_code == 422

    def test_create_screen_rejects_invalid_content_type(self, client):
        """Invalid content type is rejected."""
        resp = client.post(
            "/api/ist/screens",
            json={
                "name": "Bad Type",
                "content": VALID_CONTENT,
                "contentType": "invalid_type",
            },
        )
        assert resp.status_code == 422

    def test_create_screen_name_max_length(self, client):
        """Name exceeding 200 chars is rejected."""
        resp = client.post(
            "/api/ist/screens",
            json={"name": "x" * 201, "content": VALID_CONTENT},
        )
        assert resp.status_code == 422


# ── GET /api/ist/screens ─────────────────────────────────────────────────────


class TestListScreens:
    """Tests for GET /api/ist/screens."""

    def test_list_screens_empty(self, client):
        """Empty list returns correctly."""
        resp = client.get("/api/ist/screens")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screens"] == []
        assert data["total"] == 0

    def test_list_screens_with_data(self, client):
        """List returns created screens."""
        _create_screen(client, name="Screen A")
        _create_screen(client, name="Screen B")

        resp = client.get("/api/ist/screens")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["screens"]) == 2
        # Newest first
        assert data["screens"][0]["name"] == "Screen B"
        assert data["screens"][1]["name"] == "Screen A"

    def test_list_screens_status_filter(self, client):
        """Status filter works correctly."""
        _create_screen(client, name="Pending Screen")

        resp = client.get("/api/ist/screens?status=PENDING")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = client.get("/api/ist/screens?status=COMPLETED")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_screens_invalid_status(self, client):
        """Invalid status returns 400."""
        resp = client.get("/api/ist/screens?status=INVALID")
        assert resp.status_code == 400
        assert "INVALID_FILTER" in resp.json()["detail"]["error"]["code"]

    def test_list_screens_pagination(self, client):
        """Pagination (limit/offset) works."""
        for i in range(5):
            _create_screen(client, name=f"Screen {i}")

        resp = client.get("/api/ist/screens?limit=2&offset=0")
        data = resp.json()
        assert data["total"] == 5
        assert len(data["screens"]) == 2

        resp = client.get("/api/ist/screens?limit=2&offset=2")
        data = resp.json()
        assert data["total"] == 5
        assert len(data["screens"]) == 2

    def test_list_screens_summary_fields(self, client):
        """List items include summary fields (counts, phase)."""
        _create_screen(client, name="Summary Test")
        resp = client.get("/api/ist/screens")
        item = resp.json()["screens"][0]
        assert "claimCount" in item
        assert "candidateCount" in item
        assert "tier1Count" in item
        assert "currentPhase" in item
        assert "workflowRunId" in item
        assert item["claimCount"] == 0
        assert item["candidateCount"] == 0
        assert item["currentPhase"] == 0


# ── GET /api/ist/screens/{id} ────────────────────────────────────────────────


class TestGetScreenDetail:
    """Tests for GET /api/ist/screens/{id}."""

    def test_get_screen_detail_success(self, client):
        """Getting screen detail returns all fields."""
        create_resp = _create_screen(
            client,
            name="Detail Test",
            hypothesis="Test hypothesis",
        )
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == screen_id
        assert data["name"] == "Detail Test"
        assert data["status"] == "PENDING"
        assert data["screeningBrief"]["hypothesis"] == "Test hypothesis"
        assert data["contentExtraction"] is None  # Not yet extracted
        assert data["sourceBias"] is None  # Not yet assessed
        assert data["currentPhase"] == 0

    def test_get_screen_detail_not_found(self, client):
        """Getting non-existent screen returns 404."""
        resp = client.get("/api/ist/screens/99999")
        assert resp.status_code == 404
        assert "SCREEN_NOT_FOUND" in resp.json()["detail"]["error"]["code"]


# ── GET /api/ist/screens/{id}/claims ─────────────────────────────────────────


class TestGetScreenClaims:
    """Tests for GET /api/ist/screens/{id}/claims."""

    def test_get_claims_empty(self, client):
        """Claims endpoint returns empty list for new screen."""
        create_resp = _create_screen(client, name="Claims Test")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/claims")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["claims"] == []
        assert data["totalCount"] == 0
        assert data["validatedCount"] == 0

    def test_get_claims_with_data(self, client, db):
        """Claims endpoint returns populated claims."""
        from app.models.ist import ISTClaim

        create_resp = _create_screen(client, name="Claims Data")
        screen_id = create_resp.json()["id"]

        # Insert test claims directly into DB
        claim1 = ISTClaim(
            screen_id=screen_id,
            claim_text="Test claim 1",
            source_citation="Section 1",
            quantitative_anchor="100 units",
            confidence=0.9,
        )
        claim2 = ISTClaim(
            screen_id=screen_id,
            claim_text="Test claim 2",
            source_citation="Section 2",
            is_validated=1,
            validation_verdict="confirmed",
            confidence=0.85,
        )
        db.add(claim1)
        db.add(claim2)
        db.commit()

        resp = client.get(f"/api/ist/screens/{screen_id}/claims")
        assert resp.status_code == 200
        data = resp.json()
        assert data["totalCount"] == 2
        assert data["validatedCount"] == 1
        assert len(data["claims"]) == 2

    def test_get_claims_filter_validated(self, client, db):
        """Claims can be filtered by validation status."""
        from app.models.ist import ISTClaim

        create_resp = _create_screen(client, name="Validated Filter")
        screen_id = create_resp.json()["id"]

        db.add(ISTClaim(
            screen_id=screen_id,
            claim_text="Validated claim",
            source_citation="Sec 1",
            is_validated=1,
            validation_verdict="confirmed",
            confidence=0.9,
        ))
        db.add(ISTClaim(
            screen_id=screen_id,
            claim_text="Unvalidated claim",
            source_citation="Sec 2",
            confidence=0.7,
        ))
        db.commit()

        # Only validated
        resp = client.get(f"/api/ist/screens/{screen_id}/claims?validated=true")
        data = resp.json()
        assert len(data["claims"]) == 1
        assert data["claims"][0]["claimText"] == "Validated claim"

        # Only unvalidated
        resp = client.get(f"/api/ist/screens/{screen_id}/claims?validated=false")
        data = resp.json()
        assert len(data["claims"]) == 1
        assert data["claims"][0]["claimText"] == "Unvalidated claim"

    def test_get_claims_filter_quant_anchor(self, client, db):
        """Claims can be filtered by quantitative anchor presence."""
        from app.models.ist import ISTClaim

        create_resp = _create_screen(client, name="Quant Filter")
        screen_id = create_resp.json()["id"]

        db.add(ISTClaim(
            screen_id=screen_id,
            claim_text="With anchor",
            source_citation="Sec 1",
            quantitative_anchor="100 GPUs",
            confidence=0.9,
        ))
        db.add(ISTClaim(
            screen_id=screen_id,
            claim_text="Without anchor",
            source_citation="Sec 2",
            confidence=0.7,
        ))
        db.commit()

        resp = client.get(
            f"/api/ist/screens/{screen_id}/claims?hasQuantAnchor=true"
        )
        assert len(resp.json()["claims"]) == 1
        assert resp.json()["claims"][0]["claimText"] == "With anchor"

    def test_get_claims_not_found(self, client):
        """Claims for non-existent screen returns 404."""
        resp = client.get("/api/ist/screens/99999/claims")
        assert resp.status_code == 404


# ── PUT /api/ist/screens/{id}/brief ──────────────────────────────────────────


class TestUpdateScreenBrief:
    """Tests for PUT /api/ist/screens/{id}/brief."""

    def test_update_brief_when_paused(self, client, db):
        """Brief can be updated when workflow is PAUSED."""
        from app.models.workflow import WorkflowRun

        create_resp = _create_screen(
            client,
            name="Brief Update",
            hypothesis="Original hypothesis",
        )
        screen_id = create_resp.json()["id"]
        run_id = create_resp.json()["workflowRunId"]

        # Set workflow to PAUSED
        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        run.status = "PAUSED"
        db.commit()

        resp = client.put(
            f"/api/ist/screens/{screen_id}/brief",
            json={"hypothesis": "Updated hypothesis"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["screeningBrief"]["hypothesis"] == "Updated hypothesis"

    def test_update_brief_rejects_when_not_paused(self, client):
        """Brief update is rejected when workflow is not PAUSED."""
        create_resp = _create_screen(client, name="Not Paused")
        screen_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/ist/screens/{screen_id}/brief",
            json={"hypothesis": "New hypothesis"},
        )
        assert resp.status_code == 409
        assert "INVALID_STATE" in resp.json()["detail"]["error"]["code"]

    def test_update_brief_not_found(self, client):
        """Brief update for non-existent screen returns 404."""
        resp = client.put(
            "/api/ist/screens/99999/brief",
            json={"hypothesis": "Test"},
        )
        assert resp.status_code == 404

    def test_update_brief_partial_merge(self, client, db):
        """Brief update merges with existing data, not replaces."""
        from app.models.workflow import WorkflowRun

        create_resp = _create_screen(
            client,
            name="Merge Test",
            hypothesis="Original",
            constraints={"minMarketCap": 1000000000},
        )
        screen_id = create_resp.json()["id"]
        run_id = create_resp.json()["workflowRunId"]

        # Set PAUSED
        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        run.status = "PAUSED"
        db.commit()

        # Update only hypothesis, constraints should remain
        resp = client.put(
            f"/api/ist/screens/{screen_id}/brief",
            json={"hypothesis": "Updated"},
        )
        assert resp.status_code == 200
        brief = resp.json()["screeningBrief"]
        assert brief["hypothesis"] == "Updated"
        assert brief["constraints"]["minMarketCap"] == 1000000000


# ── Workflow step ordering verification ──────────────────────────────────────


class TestWorkflowStepOrdering:
    """Verify INV-WF-01: Phase 5 step ordering is immutable."""

    def test_phase5_step_ordering(self, client, db):
        """Phase 5 steps must be in the exact required order."""
        from app.models.workflow import WorkflowStep

        create_resp = _create_screen(client, name="Step Order Test")
        run_id = create_resp.json()["workflowRunId"]

        phase5_steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == run_id)
            .filter(WorkflowStep.phase == 5)
            .order_by(WorkflowStep.step_order)
            .all()
        )

        expected_order = [
            "master_screen",
            "rotation_strategy",
            "catalyst_calendar",
            "stress_tests",
            "report_generation",
            "screen_coherence_gate",
            "screen_certification",
            "hfrt_handoff_generation",
        ]
        actual_order = [s.step_name for s in phase5_steps]
        assert actual_order == expected_order, (
            f"Phase 5 step ordering violated INV-WF-01. "
            f"Expected {expected_order}, got {actual_order}"
        )

    def test_report_generation_before_coherence_gate(self, client, db):
        """report_generation must come before screen_coherence_gate (INV-WF-01)."""
        from app.models.workflow import WorkflowStep

        create_resp = _create_screen(client, name="Order Check")
        run_id = create_resp.json()["workflowRunId"]

        report_step = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == run_id)
            .filter(WorkflowStep.step_name == "report_generation")
            .first()
        )
        gate_step = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == run_id)
            .filter(WorkflowStep.step_name == "screen_coherence_gate")
            .first()
        )

        assert report_step.step_order < gate_step.step_order
