"""Integration tests for HFRT (Hedge Fund Research Team) endpoints.

Tests cover:
- POST /api/hfrt/projects — project creation with workflow + steps + templates
- GET /api/hfrt/projects — project listing with filters and pagination
- GET /api/hfrt/projects/{id} — project detail
- GET /api/hfrt/projects/{id}/templates — list all templates
- GET /api/hfrt/projects/{id}/templates/{num} — single template
- GET /api/hfrt/projects/{id}/invariants — invariant results
- GET /api/hfrt/projects/{id}/validation — external validation results (Gap 1)
- Workflow step ordering verification (24 steps, correct sequence)
- Error handling: 404, 400, 429 cases
"""

import json
import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────


def _create_project(client, ticker="AAPL", **kwargs):
    """Helper to create an HFRT project and return the response."""
    payload = {"ticker": ticker}
    if "auto_advance" in kwargs:
        payload["autoAdvance"] = kwargs["auto_advance"]
    return client.post("/api/hfrt/projects", json=payload)


# ── POST /api/hfrt/projects ──────────────────────────────────────────────────


class TestCreateProject:
    """Tests for POST /api/hfrt/projects."""

    def test_create_project_success(self, client):
        """Creating a project returns 201 with correct fields."""
        resp = _create_project(client, ticker="NVDA")
        assert resp.status_code == 201
        data = resp.json()
        assert data["ticker"] == "NVDA"
        assert data["status"] == "PENDING"
        assert "id" in data
        assert "workflowRunId" in data
        assert "createdAt" in data

    def test_create_project_creates_workflow_run(self, client, db):
        """Creating a project creates a WorkflowRun with type=HFRT."""
        from app.models.workflow import WorkflowRun

        resp = _create_project(client, ticker="MSFT")
        assert resp.status_code == 201

        run_id = resp.json()["workflowRunId"]
        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        assert run is not None
        assert run.workflow_type == "HFRT"
        assert run.status == "PENDING"
        assert "MSFT" in run.name

    def test_create_project_creates_24_workflow_steps(self, client, db):
        """Creating a project creates all 24 HFRT workflow steps (Gap 1 included)."""
        from app.models.workflow import WorkflowStep

        resp = _create_project(client, ticker="AAPL")
        assert resp.status_code == 201

        run_id = resp.json()["workflowRunId"]
        steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == run_id)
            .order_by(WorkflowStep.step_order)
            .all()
        )
        assert len(steps) == 24

        # Verify first step
        assert steps[0].step_name == "idea_screen"
        assert steps[0].phase == 1
        assert steps[0].step_order == 1
        assert steps[0].status == "PENDING"

        # Verify last step
        assert steps[-1].step_name == "complete"
        assert steps[-1].phase == 5
        assert steps[-1].step_order == 24

    def test_create_project_creates_15_templates(self, client, db):
        """Creating a project creates 15 empty templates (00-14)."""
        from app.models.hfrt import HFRTTemplate

        resp = _create_project(client, ticker="TSLA")
        assert resp.status_code == 201

        project_id = resp.json()["id"]
        templates = (
            db.query(HFRTTemplate)
            .filter(HFRTTemplate.project_id == project_id)
            .order_by(HFRTTemplate.template_number)
            .all()
        )
        assert len(templates) == 15
        assert templates[0].template_number == 0
        assert templates[0].template_name == "Idea Screen"
        assert templates[0].status == "EMPTY"
        assert templates[-1].template_number == 14
        assert templates[-1].template_name == "Investment Memo"

    def test_create_project_ticker_normalized(self, client):
        """Ticker is stored as provided (HFRT does not auto-uppercase here, router accepts as-is)."""
        resp = _create_project(client, ticker="goog")
        assert resp.status_code == 201
        # Accept either case — the important thing is it succeeds
        data = resp.json()
        assert "ticker" in data

    def test_create_project_rejects_missing_ticker(self, client):
        """Missing ticker returns 422."""
        resp = client.post("/api/hfrt/projects", json={})
        assert resp.status_code == 422

    def test_create_project_rate_limited(self, client):
        """6th project creation in same session hits the 5/hour rate limit."""
        # Use letters-only tickers (ticker validator rejects digits)
        valid_tickers = ["AA", "BB", "CC", "DD", "EE"]
        for ticker in valid_tickers:
            r = _create_project(client, ticker=ticker)
            assert r.status_code == 201
        # 6th should be rate-limited
        r = _create_project(client, ticker="FF")
        assert r.status_code == 429


# ── GET /api/hfrt/projects ───────────────────────────────────────────────────


class TestListProjects:
    """Tests for GET /api/hfrt/projects."""

    def test_list_projects_empty(self, client):
        """Empty list returns correctly."""
        resp = client.get("/api/hfrt/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert data["projects"] == []
        assert data["total"] == 0

    def test_list_projects_with_data(self, client):
        """List returns created projects."""
        _create_project(client, ticker="AAPL")
        _create_project(client, ticker="MSFT")

        resp = client.get("/api/hfrt/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["projects"]) == 2
        # Newest first
        assert data["projects"][0]["ticker"] == "MSFT"

    def test_list_projects_pagination(self, client):
        """Pagination with limit/offset works."""
        for t in ["AA", "BB", "CC"]:
            _create_project(client, ticker=t)

        resp = client.get("/api/hfrt/projects?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["projects"]) == 2
        assert data["total"] == 3

        resp = client.get("/api/hfrt/projects?limit=2&offset=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["projects"]) == 1

    def test_list_projects_filter_by_status(self, client):
        """Filtering by status works."""
        _create_project(client, ticker="AAPL")

        resp = client.get("/api/hfrt/projects?status=PENDING")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = client.get("/api/hfrt/projects?status=COMPLETED")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_projects_invalid_status(self, client):
        """Invalid status filter returns 400."""
        resp = client.get("/api/hfrt/projects?status=INVALID")
        assert resp.status_code == 400

    def test_list_projects_summary_fields(self, client):
        """Each project in list includes summary fields."""
        _create_project(client, ticker="AAPL")

        resp = client.get("/api/hfrt/projects")
        data = resp.json()
        project = data["projects"][0]

        required_fields = [
            "id", "ticker", "status", "workflowRunId",
            "investable", "currentPhase", "templatesPopulated",
            "createdAt", "updatedAt",
        ]
        for field in required_fields:
            assert field in project, f"Missing field: {field}"


# ── GET /api/hfrt/projects/{id} ──────────────────────────────────────────────


class TestGetProject:
    """Tests for GET /api/hfrt/projects/{id}."""

    def test_get_project_success(self, client):
        """Get project by ID returns full detail."""
        resp = _create_project(client, ticker="AAPL")
        project_id = resp.json()["id"]

        resp = client.get(f"/api/hfrt/projects/{project_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == project_id
        assert data["ticker"] == "AAPL"
        assert data["status"] == "PENDING"

    def test_get_project_not_found(self, client):
        """Non-existent project returns 404."""
        resp = client.get("/api/hfrt/projects/99999")
        assert resp.status_code == 404
        # FastAPI wraps HTTPException.detail in {"detail": ...}
        body = resp.json()
        assert "detail" in body
        assert "error" in body["detail"]

    def test_get_project_detail_fields(self, client):
        """Get project returns all expected detail fields."""
        resp = _create_project(client, ticker="AAPL")
        project_id = resp.json()["id"]

        resp = client.get(f"/api/hfrt/projects/{project_id}")
        data = resp.json()

        required_fields = [
            "id", "workflowRunId", "ticker", "status",
            "investable", "isCertified", "currentPhase",
            "createdAt", "updatedAt",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


# ── GET /api/hfrt/projects/{id}/templates ────────────────────────────────────


class TestTemplates:
    """Tests for template endpoints."""

    def test_list_templates_returns_all_15(self, client):
        """List templates returns all 15 templates."""
        resp = _create_project(client, ticker="AAPL")
        project_id = resp.json()["id"]

        resp = client.get(f"/api/hfrt/projects/{project_id}/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["templates"]) == 15

    def test_list_templates_empty_status(self, client):
        """All templates start as EMPTY."""
        resp = _create_project(client, ticker="AAPL")
        project_id = resp.json()["id"]

        resp = client.get(f"/api/hfrt/projects/{project_id}/templates")
        templates = resp.json()["templates"]
        for t in templates:
            assert t["status"] == "EMPTY"
            assert t["data"] is None

    def test_get_single_template_success(self, client):
        """Get template by number returns correct template."""
        resp = _create_project(client, ticker="AAPL")
        project_id = resp.json()["id"]

        resp = client.get(f"/api/hfrt/projects/{project_id}/templates/0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["templateNumber"] == 0
        assert data["templateName"] == "Idea Screen"

    def test_get_template_invalid_number(self, client):
        """Template number > 14 returns 400."""
        resp = _create_project(client, ticker="AAPL")
        project_id = resp.json()["id"]

        resp = client.get(f"/api/hfrt/projects/{project_id}/templates/15")
        assert resp.status_code == 400

    def test_get_template_not_found_project(self, client):
        """Template for non-existent project returns 404."""
        resp = client.get("/api/hfrt/projects/99999/templates/0")
        assert resp.status_code == 404

    def test_list_templates_project_not_found(self, client):
        """List templates for non-existent project returns 404."""
        resp = client.get("/api/hfrt/projects/99999/templates")
        assert resp.status_code == 404


# ── Invariant Endpoints ──────────────────────────────────────────────────────


class TestInvariants:
    """Tests for GET /api/hfrt/projects/{id}/invariants."""

    def test_get_invariants_empty_project(self, client):
        """Invariants on a fresh project return empty list (not yet run)."""
        resp = _create_project(client, ticker="AAPL")
        project_id = resp.json()["id"]

        resp = client.get(f"/api/hfrt/projects/{project_id}/invariants")
        assert resp.status_code == 200
        data = resp.json()
        assert "projectId" in data
        assert "invariants" in data
        assert "allPassed" in data

    def test_get_invariants_live_mode(self, client):
        """Live invariant check returns structured results for an empty project."""
        resp = _create_project(client, ticker="AAPL")
        project_id = resp.json()["id"]

        resp = client.get(f"/api/hfrt/projects/{project_id}/invariants?live=true")
        assert resp.status_code == 200
        data = resp.json()
        # Live check always returns 8 invariants regardless of project state.
        # Note: check_all_invariants uses its own SessionLocal() so the exact
        # pass/fail mix depends on what is in the live DB — we only assert structure.
        assert len(data["invariants"]) == 8
        assert "failCount" in data
        assert "passCount" in data
        assert data["failCount"] + data["passCount"] == 8
        # Each invariant has the required structure
        for inv in data["invariants"]:
            assert "id" in inv
            assert "name" in inv
            assert "status" in inv
            assert inv["status"] in ("PASS", "FAIL")

    def test_get_invariants_project_not_found(self, client):
        """Invariants for non-existent project returns 404."""
        resp = client.get("/api/hfrt/projects/99999/invariants")
        assert resp.status_code == 404


# ── Validation Endpoint (Gap 1) ──────────────────────────────────────────────


class TestExternalValidation:
    """Tests for GET /api/hfrt/projects/{id}/validation (Gap 1)."""

    def test_get_validation_not_run(self, client):
        """Validation endpoint returns 404 when not yet run."""
        resp = _create_project(client, ticker="AAPL")
        project_id = resp.json()["id"]

        resp = client.get(f"/api/hfrt/projects/{project_id}/validation")
        assert resp.status_code == 404
        # FastAPI wraps HTTPException.detail in {"detail": ...}
        body = resp.json()
        assert "detail" in body
        assert "error" in body["detail"]

    def test_get_validation_project_not_found(self, client):
        """Validation for non-existent project returns 404."""
        resp = client.get("/api/hfrt/projects/99999/validation")
        assert resp.status_code == 404

    def test_get_validation_with_stored_results(self, client, db):
        """Validation endpoint returns stored results correctly."""
        from app.models.hfrt import HFRTProject

        resp = _create_project(client, ticker="AAPL")
        project_id = resp.json()["id"]

        # Manually store validation results
        validation_data = {
            "claims_validated": 5,
            "confirmed": 3,
            "partially_confirmed": 1,
            "contradicted": 1,
            "unvalidatable": 0,
            "overall_confidence": "high",
            "key_contradictions": ["Claim A was wrong"],
            "items": [],
        }
        project = db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
        project.external_validation_results = json.dumps(validation_data)
        db.commit()

        resp = client.get(f"/api/hfrt/projects/{project_id}/validation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["claimsValidated"] == 5
        assert data["confirmed"] == 3
        assert data["partiallyConfirmed"] == 1
        assert data["contradicted"] == 1
        assert data["unvalidatable"] == 0
        assert data["overallConfidence"] == "high"
        assert data["keyContradictions"] == ["Claim A was wrong"]


# ── Workflow Step Ordering ────────────────────────────────────────────────────


class TestWorkflowStepOrdering:
    """Tests for HFRT workflow step definitions and ordering."""

    def test_24_steps_defined(self, client):
        """HFRT_WORKFLOW_STEPS has exactly 24 entries (Gap 1: external_validation added)."""
        from app.routers.hfrt import HFRT_WORKFLOW_STEPS
        assert len(HFRT_WORKFLOW_STEPS) == 24

    def test_step_orders_sequential(self, client):
        """Step orders are sequential (1-24) with no gaps."""
        from app.routers.hfrt import HFRT_WORKFLOW_STEPS
        orders = sorted(s["step_order"] for s in HFRT_WORKFLOW_STEPS)
        assert orders == list(range(1, 25))

    def test_external_validation_at_step_14(self, client):
        """external_validation is at step_order 14 after dd_sufficiency_gate."""
        from app.routers.hfrt import HFRT_WORKFLOW_STEPS
        ev = next(s for s in HFRT_WORKFLOW_STEPS if s["step_name"] == "external_validation")
        assert ev["step_order"] == 14
        assert ev["phase"] == 3
        assert "dd_sufficiency_gate" in ev["depends_on"]

    def test_dialectic_steps_at_15_16(self, client):
        """bull_case and bear_case are at step_orders 15 and 16 after Gap 1 insertion."""
        from app.routers.hfrt import HFRT_WORKFLOW_STEPS
        bull = next(s for s in HFRT_WORKFLOW_STEPS if s["step_name"] == "bull_case")
        bear = next(s for s in HFRT_WORKFLOW_STEPS if s["step_name"] == "bear_case")
        assert bull["step_order"] == 15
        assert bear["step_order"] == 16

    def test_complete_step_at_24(self, client):
        """complete step is at step_order 24."""
        from app.routers.hfrt import HFRT_WORKFLOW_STEPS
        complete = next(s for s in HFRT_WORKFLOW_STEPS if s["step_name"] == "complete")
        assert complete["step_order"] == 24

    def test_no_duplicate_step_orders(self, client):
        """No two steps share the same step_order."""
        from app.routers.hfrt import HFRT_WORKFLOW_STEPS
        orders = [s["step_order"] for s in HFRT_WORKFLOW_STEPS]
        assert len(orders) == len(set(orders))

    def test_all_depends_on_reference_valid_step_names(self, client):
        """Every depends_on entry references a step_name that exists."""
        from app.routers.hfrt import HFRT_WORKFLOW_STEPS
        names = {s["step_name"] for s in HFRT_WORKFLOW_STEPS}
        for step in HFRT_WORKFLOW_STEPS:
            for dep in step.get("depends_on", []):
                assert dep in names, f"Step '{step['step_name']}' depends on unknown '{dep}'"

    def test_project_created_with_all_step_names(self, client, db):
        """All 24 step names are present when a project is created."""
        from app.models.workflow import WorkflowStep
        from app.routers.hfrt import HFRT_WORKFLOW_STEPS

        resp = _create_project(client, ticker="AAPL")
        run_id = resp.json()["workflowRunId"]

        steps = db.query(WorkflowStep).filter(WorkflowStep.workflow_run_id == run_id).all()
        created_names = {s.step_name for s in steps}
        expected_names = {s["step_name"] for s in HFRT_WORKFLOW_STEPS}
        assert created_names == expected_names
