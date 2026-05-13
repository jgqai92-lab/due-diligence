"""Integration tests for IST-to-HFRT bridge endpoints.

Tests:
  - GET /api/bridge/ist-to-hfrt/candidates/{screen_id}
  - POST /api/bridge/ist-to-hfrt
  - Service layer: get_handoff_candidates, create_hfrt_from_handoff
"""

import json

import pytest

from app.models.ist import ISTScreen
from app.models.hfrt import HFRTProject, HFRTTemplate
from app.models.workflow import WorkflowRun, WorkflowStep


# ── Fixtures ────────────────────────────────────────────────────────────────


SAMPLE_HANDOFF = {
    "screenName": "AI Infrastructure Screen",
    "screenId": 1,
    "certifiedAt": "2026-02-12T10:00:00Z",
    "tier1Count": 2,
    "totalCount": 2,
    "tierBreakdown": {"tier1": 2, "tier2": 0, "tier3": 0},
    "candidates": [
        {
            "ticker": "NVDA",
            "companyName": "NVIDIA Corp",
            "tier": 1,
            "conviction": "HIGH",
            "pillar": "AI Infrastructure",
            "catalyst": "Data center demand surge",
            "scarcityScore": 8.5,
        },
        {
            "ticker": "TSLA",
            "companyName": "Tesla Inc",
            "tier": 1,
            "conviction": "MEDIUM",
            "pillar": "Energy Storage",
            "catalyst": "Battery cost decline",
            "scarcityScore": 7.2,
        },
    ],
}


def _create_certified_screen(db, handoff_data=None) -> ISTScreen:
    """Helper: create a workflow run + certified IST screen with handoff data."""
    run = WorkflowRun(
        workflow_type="IST",
        name="Test IST Run",
        status="COMPLETED",
        current_phase=5,
    )
    db.add(run)
    db.flush()

    screen = ISTScreen(
        workflow_run_id=run.id,
        name="AI Infrastructure Screen",
        status="COMPLETED",
        content_type="text",
        raw_content="Test content for AI infrastructure analysis.",
        is_certified=1,
        hfrt_handoff=json.dumps(handoff_data or SAMPLE_HANDOFF),
    )
    db.add(screen)
    db.commit()
    db.refresh(screen)
    return screen


def _create_uncertified_screen(db) -> ISTScreen:
    """Helper: create a workflow run + uncertified IST screen."""
    run = WorkflowRun(
        workflow_type="IST",
        name="Test IST Run (uncertified)",
        status="RUNNING",
        current_phase=3,
    )
    db.add(run)
    db.flush()

    screen = ISTScreen(
        workflow_run_id=run.id,
        name="Uncertified Screen",
        status="ANALYZING",
        content_type="text",
        raw_content="Test content.",
        is_certified=0,
    )
    db.add(screen)
    db.commit()
    db.refresh(screen)
    return screen


# ── GET /api/bridge/ist-to-hfrt/candidates/{screen_id} ─────────────────────


class TestGetCandidates:
    def test_get_candidates_success(self, client, db):
        screen = _create_certified_screen(db)
        resp = client.get(f"/api/bridge/ist-to-hfrt/candidates/{screen.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenName"] == "AI Infrastructure Screen"
        assert data["tier1Count"] == 2
        assert len(data["candidates"]) == 2
        assert data["candidates"][0]["ticker"] == "NVDA"
        assert data["candidates"][1]["ticker"] == "TSLA"

    def test_get_candidates_screen_not_found(self, client, db):
        resp = client.get("/api/bridge/ist-to-hfrt/candidates/99999")
        assert resp.status_code == 404
        data = resp.json()
        assert data["detail"]["error"]["code"] == "SCREEN_NOT_FOUND"

    def test_get_candidates_not_certified(self, client, db):
        screen = _create_uncertified_screen(db)
        resp = client.get(f"/api/bridge/ist-to-hfrt/candidates/{screen.id}")
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"]["error"]["code"] == "NOT_CERTIFIED"

    def test_get_candidates_no_handoff_data(self, client, db):
        """Screen is certified but has no hfrt_handoff column populated."""
        run = WorkflowRun(
            workflow_type="IST",
            name="Test IST Run",
            status="COMPLETED",
            current_phase=5,
        )
        db.add(run)
        db.flush()

        screen = ISTScreen(
            workflow_run_id=run.id,
            name="Empty Handoff Screen",
            status="COMPLETED",
            content_type="text",
            raw_content="Test content.",
            is_certified=1,
            hfrt_handoff=None,
        )
        db.add(screen)
        db.commit()

        resp = client.get(f"/api/bridge/ist-to-hfrt/candidates/{screen.id}")
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"]["error"]["code"] == "NO_HANDOFF_DATA"


# ── POST /api/bridge/ist-to-hfrt ───────────────────────────────────────────


class TestCreateHFRTProjects:
    def test_create_single_ticker(self, client, db):
        screen = _create_certified_screen(db)
        resp = client.post(
            "/api/bridge/ist-to-hfrt",
            json={"screenId": screen.id, "tickers": ["NVDA"]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total"] == 1
        assert len(data["created"]) == 1
        assert data["failed"] == []

        created = data["created"][0]
        assert created["ticker"] == "NVDA"
        assert created["companyName"] == "NVIDIA Corp"
        assert created["status"] == "PENDING"
        assert created["link"] == f"/research/{created['projectId']}"

        # Verify database state
        project = db.query(HFRTProject).filter(HFRTProject.id == created["projectId"]).first()
        assert project is not None
        assert project.ticker == "NVDA"
        assert project.company_name == "NVIDIA Corp"
        assert project.source == "IST_HANDOFF"
        assert project.ist_screen_id == screen.id

        # Verify workflow run
        run = db.query(WorkflowRun).filter(WorkflowRun.id == project.workflow_run_id).first()
        assert run is not None
        assert run.workflow_type == "HFRT"
        assert "IST Handoff" in run.name

        # Verify 24 workflow steps created (Gap 1: external_validation added)
        steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == run.id)
            .all()
        )
        assert len(steps) == 24

        # Verify 15 templates created
        templates = (
            db.query(HFRTTemplate)
            .filter(HFRTTemplate.project_id == project.id)
            .order_by(HFRTTemplate.template_number)
            .all()
        )
        assert len(templates) == 15

        # Verify template 00 (Idea Screen) is pre-populated
        idea_screen = templates[0]
        assert idea_screen.template_number == 0
        assert idea_screen.status == "POPULATED"
        idea_data = json.loads(idea_screen.data)
        assert idea_data["ticker"] == "NVDA"
        assert idea_data["companyName"] == "NVIDIA Corp"
        assert idea_data["source"] == "IST Handoff"
        assert idea_data["istScreenId"] == screen.id
        assert idea_data["istScreenName"] == "AI Infrastructure Screen"
        assert idea_data["prePopulated"] is True
        assert idea_data["scarcityScore"] == 8.5
        assert idea_data["catalyst"] == "Data center demand surge"
        assert "AI Infrastructure" in idea_data["thesis"]
        assert "HIGH" in idea_data["thesis"]

        # Verify other templates are EMPTY
        for t in templates[1:]:
            assert t.status == "EMPTY"
            assert t.data is None

    def test_create_multiple_tickers(self, client, db):
        screen = _create_certified_screen(db)
        resp = client.post(
            "/api/bridge/ist-to-hfrt",
            json={"screenId": screen.id, "tickers": ["NVDA", "TSLA"]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total"] == 2
        assert len(data["created"]) == 2
        assert data["failed"] == []

        tickers = [c["ticker"] for c in data["created"]]
        assert "NVDA" in tickers
        assert "TSLA" in tickers

        # Verify each project has separate workflow run
        project_ids = [c["projectId"] for c in data["created"]]
        run_ids = [c["workflowRunId"] for c in data["created"]]
        assert len(set(project_ids)) == 2
        assert len(set(run_ids)) == 2

    def test_create_with_invalid_ticker_not_in_candidates(self, client, db):
        screen = _create_certified_screen(db)
        resp = client.post(
            "/api/bridge/ist-to-hfrt",
            json={"screenId": screen.id, "tickers": ["AAPL"]},
        )
        # AAPL is not in the handoff candidates -- partial failure
        assert resp.status_code == 201
        data = resp.json()
        assert data["total"] == 0
        assert len(data["created"]) == 0
        assert len(data["failed"]) == 1
        assert data["failed"][0]["ticker"] == "AAPL"
        assert "not found" in data["failed"][0]["error"].lower()

    def test_create_mixed_success_and_failure(self, client, db):
        screen = _create_certified_screen(db)
        resp = client.post(
            "/api/bridge/ist-to-hfrt",
            json={"screenId": screen.id, "tickers": ["NVDA", "AAPL", "TSLA"]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total"] == 2  # NVDA and TSLA succeed
        assert len(data["failed"]) == 1  # AAPL fails
        assert data["failed"][0]["ticker"] == "AAPL"

    def test_create_screen_not_found(self, client, db):
        resp = client.post(
            "/api/bridge/ist-to-hfrt",
            json={"screenId": 99999, "tickers": ["NVDA"]},
        )
        assert resp.status_code == 404

    def test_create_screen_not_certified(self, client, db):
        screen = _create_uncertified_screen(db)
        resp = client.post(
            "/api/bridge/ist-to-hfrt",
            json={"screenId": screen.id, "tickers": ["NVDA"]},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"]["error"]["code"] == "NOT_CERTIFIED"

    def test_create_empty_tickers_list_rejected(self, client, db):
        screen = _create_certified_screen(db)
        resp = client.post(
            "/api/bridge/ist-to-hfrt",
            json={"screenId": screen.id, "tickers": []},
        )
        assert resp.status_code == 422  # Pydantic validation error

    def test_create_invalid_ticker_format_rejected(self, client, db):
        screen = _create_certified_screen(db)
        resp = client.post(
            "/api/bridge/ist-to-hfrt",
            json={"screenId": screen.id, "tickers": ["123"]},
        )
        assert resp.status_code == 422  # Pydantic validation error

    def test_create_duplicate_tickers_rejected(self, client, db):
        screen = _create_certified_screen(db)
        resp = client.post(
            "/api/bridge/ist-to-hfrt",
            json={"screenId": screen.id, "tickers": ["NVDA", "NVDA"]},
        )
        assert resp.status_code == 422  # Pydantic validation error

    def test_create_case_insensitive_ticker(self, client, db):
        screen = _create_certified_screen(db)
        resp = client.post(
            "/api/bridge/ist-to-hfrt",
            json={"screenId": screen.id, "tickers": ["nvda"]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total"] == 1
        assert data["created"][0]["ticker"] == "NVDA"

    def test_create_with_nested_scarcity_score(self, client, db):
        """Verify bridge handles nested scarcityScore dicts (from real IST data)."""
        handoff_with_nested = {
            "screenName": "Nested Score Screen",
            "screenId": 1,
            "certifiedAt": "2026-02-12T10:00:00Z",
            "tier1Count": 1,
            "totalCount": 1,
            "tierBreakdown": {"tier1": 1, "tier2": 0, "tier3": 0},
            "candidates": [
                {
                    "ticker": "AMD",
                    "companyName": "Advanced Micro Devices",
                    "tier": 1,
                    "conviction": "HIGH",
                    "pillar": "Semiconductors",
                    "catalyst": "AI chip demand",
                    "scarcityScore": {
                        "composite": 7.8,
                        "supply": 8.0,
                        "demand": 7.5,
                    },
                },
            ],
        }
        screen = _create_certified_screen(db, handoff_data=handoff_with_nested)
        resp = client.post(
            "/api/bridge/ist-to-hfrt",
            json={"screenId": screen.id, "tickers": ["AMD"]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total"] == 1

        project = db.query(HFRTProject).filter(HFRTProject.id == data["created"][0]["projectId"]).first()
        template = (
            db.query(HFRTTemplate)
            .filter(
                HFRTTemplate.project_id == project.id,
                HFRTTemplate.template_number == 0,
            )
            .first()
        )
        idea_data = json.loads(template.data)
        # The bridge should extract the composite score
        assert idea_data["scarcityScore"] == 7.8


# ── Service layer unit tests ───────────────────────────────────────────────


class TestBridgeServiceUnit:
    def test_get_handoff_candidates_success(self, db):
        from app.services.bridge import get_handoff_candidates

        screen = _create_certified_screen(db)
        result = get_handoff_candidates(db, screen.id)
        assert result["screenName"] == "AI Infrastructure Screen"
        assert len(result["candidates"]) == 2

    def test_get_handoff_candidates_not_found(self, db):
        from app.services.bridge import get_handoff_candidates

        with pytest.raises(ValueError, match="not found"):
            get_handoff_candidates(db, 99999)

    def test_get_handoff_candidates_not_certified(self, db):
        from app.services.bridge import get_handoff_candidates

        screen = _create_uncertified_screen(db)
        with pytest.raises(ValueError, match="not certified"):
            get_handoff_candidates(db, screen.id)

    def test_create_hfrt_from_handoff_success(self, db):
        from app.services.bridge import create_hfrt_from_handoff

        screen = _create_certified_screen(db)
        result = create_hfrt_from_handoff(db, screen.id, "NVDA")
        assert result["ticker"] == "NVDA"
        assert result["companyName"] == "NVIDIA Corp"
        assert result["status"] == "PENDING"

    def test_create_hfrt_from_handoff_ticker_not_in_candidates(self, db):
        from app.services.bridge import create_hfrt_from_handoff

        screen = _create_certified_screen(db)
        with pytest.raises(ValueError, match="not found in handoff"):
            create_hfrt_from_handoff(db, screen.id, "AAPL")

    def test_create_hfrt_from_handoff_sets_source_columns(self, db):
        from app.services.bridge import create_hfrt_from_handoff

        screen = _create_certified_screen(db)
        result = create_hfrt_from_handoff(db, screen.id, "TSLA")

        project = db.query(HFRTProject).filter(HFRTProject.id == result["projectId"]).first()
        assert project.source == "IST_HANDOFF"
        assert project.ist_screen_id == screen.id

    def test_create_hfrt_workflow_run_name(self, db):
        from app.services.bridge import create_hfrt_from_handoff

        screen = _create_certified_screen(db)
        result = create_hfrt_from_handoff(db, screen.id, "NVDA")

        run = db.query(WorkflowRun).filter(WorkflowRun.id == result["workflowRunId"]).first()
        assert run.name == "HFRT Research: NVDA (IST Handoff)"
        assert run.workflow_type == "HFRT"
        assert run.status == "PENDING"

    def test_create_hfrt_template_count(self, db):
        from app.services.bridge import create_hfrt_from_handoff

        screen = _create_certified_screen(db)
        result = create_hfrt_from_handoff(db, screen.id, "NVDA")

        templates = (
            db.query(HFRTTemplate)
            .filter(HFRTTemplate.project_id == result["projectId"])
            .all()
        )
        assert len(templates) == 15

    def test_create_hfrt_step_count(self, db):
        from app.services.bridge import create_hfrt_from_handoff

        screen = _create_certified_screen(db)
        result = create_hfrt_from_handoff(db, screen.id, "NVDA")

        steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == result["workflowRunId"])
            .all()
        )
        assert len(steps) == 24  # Gap 1: external_validation added
