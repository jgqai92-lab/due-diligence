"""Integration tests for IST Phase 5: Final Synthesis endpoints.

Tests cover:
- GET /api/ist/screens/{id}/master-screen (populated + 404)
- GET /api/ist/screens/{id}/rotation (populated + 404)
- GET /api/ist/screens/{id}/catalysts (populated + 404)
- GET /api/ist/screens/{id}/stress-tests (populated + 404)
- GET /api/ist/screens/{id}/report (populated + 404, verifies markdown content)
- GET /api/ist/screens/{id}/handoff (certified + not certified + 404)
- 404 for non-existent screens on all endpoints
- Error format consistency (INV-BE-02)
"""

import json
import pytest
from datetime import datetime, timezone


# -- Helpers ------------------------------------------------------------------

VALID_CONTENT = (
    "This is a test content that discusses AI infrastructure scarcity. "
    "NVIDIA's GB300 GPU requires 330,000 units per GW cluster. "
    "Power infrastructure is bottlenecked by 5-year interconnection queues. "
    "Cooling demand is growing 15% CAGR. "
) * 5


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


def _create_master_screen(db, screen_id):
    """Create an ISTMasterScreen record directly."""
    from app.models.ist import ISTMasterScreen

    ranked = json.dumps([
        {
            "rank": 1,
            "ticker": "NVDA",
            "company_name": "NVIDIA Corporation",
            "tier": 1,
            "scarcity_score": 4.6,
            "conviction_score": 92,
            "pillar": "GPU Supply Scarcity",
            "catalyst": "GB300 launch",
        },
        {
            "rank": 2,
            "ticker": "EATON",
            "company_name": "Eaton Corporation",
            "tier": 2,
            "scarcity_score": 3.5,
            "conviction_score": 55,
            "pillar": "Power Infrastructure Bottleneck",
            "catalyst": "IRA spending",
        },
    ])
    invariant_compliance = json.dumps([
        {"id": "INV-1", "name": "Source Citation Required", "status": "PASS", "details": "OK"},
    ])
    master = ISTMasterScreen(
        screen_id=screen_id,
        ranked_equities=ranked,
        invariant_compliance=invariant_compliance,
        total_equities=2,
        tier1_count=1,
    )
    db.add(master)
    db.commit()
    return master


def _create_rotation_strategy(db, screen_id):
    """Create an ISTRotationStrategy record directly."""
    from app.models.ist import ISTRotationStrategy

    rotation = ISTRotationStrategy(
        screen_id=screen_id,
        phase_allocations=json.dumps([
            {"phase": 1, "phase_label": "Near-term", "allocation_pct": 60,
             "tickers": ["NVDA"], "rationale": "GPU scarcity immediate"},
        ]),
        rotation_triggers=json.dumps([
            {"trigger_name": "Supply Normalization", "description": "GPU supply catches up",
             "action": "Reduce NVDA", "affected_tickers": ["NVDA"]},
        ]),
        risk_limits=json.dumps([
            {"limit_name": "Single Name Max", "limit_value": "25%",
             "rationale": "Diversification"},
        ]),
    )
    db.add(rotation)
    db.commit()
    return rotation


def _create_catalyst_calendar(db, screen_id):
    """Create an ISTCatalystCalendar record directly."""
    from app.models.ist import ISTCatalystCalendar

    calendar = ISTCatalystCalendar(
        screen_id=screen_id,
        catalysts=json.dumps([
            {"date": "Q2 2025", "ticker": "NVDA", "event": "GB300 ramp",
             "impact": "Positive", "pillar": "GPU Supply Scarcity"},
            {"date": "H2 2025", "ticker": "EATON", "event": "IRA spending",
             "impact": "Positive", "pillar": "Power Infrastructure Bottleneck"},
        ]),
        total_catalysts=2,
        next_catalyst_date="Q2 2025",
    )
    db.add(calendar)
    db.commit()
    return calendar


def _create_stress_test(db, screen_id):
    """Create an ISTStressTest record directly."""
    from app.models.ist import ISTStressTest

    stress = ISTStressTest(
        screen_id=screen_id,
        framework_tests=json.dumps([
            {"scenario": "Demand Collapse", "description": "AI capex falls 40%",
             "impact_assessment": "Thesis impaired", "severity": "HIGH",
             "affected_pillars": ["GPU Supply Scarcity"]},
        ]),
        name_tests=json.dumps([
            {"ticker": "NVDA", "scenario": "Custom silicon", "impact": "Revenue slows",
             "survival_probability": 0.65},
        ]),
        survival_scores=json.dumps([
            {"ticker": "NVDA", "overall_survival": 0.65,
             "weakest_scenario": "Custom silicon"},
        ]),
    )
    db.add(stress)
    db.commit()
    return stress


def _create_report(db, screen_id):
    """Create an ISTReport record directly."""
    from app.models.ist import ISTReport

    content = (
        "# Investment Thesis Report\n\n"
        "## Executive Summary\n\n"
        "This report analyzes AI infrastructure scarcity.\n\n"
        "## Pillar-by-Pillar Analysis\n\n"
        "### GPU Supply Scarcity\n\n"
        "NVIDIA dominates the GPU market.\n\n"
        "## Disclaimer\n\n"
        "This is not financial advice."
    )
    metadata = json.dumps({
        "pillarCount": 2,
        "equityCount": 2,
        "tier1Count": 1,
        "tier2Count": 1,
        "tier3Count": 0,
        "wordCount": 40,
        "model": "claude-sonnet-4-20250514",
    })
    report = ISTReport(
        screen_id=screen_id,
        title="Investment Thesis Report: Test Screen",
        content=content,
        report_metadata=metadata,
    )
    db.add(report)
    db.commit()
    return report


def _certify_screen(db, screen_id):
    """Mark a screen as certified."""
    from app.models.ist import ISTScreen

    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if screen:
        screen.is_certified = 1
        screen.certified_at = datetime.now(timezone.utc)
        screen.status = "COMPLETED"
        db.commit()


def _create_tier1_candidate(db, screen_id):
    """Create a Tier 1 equity candidate."""
    from app.models.ist import ISTEquityCandidate

    cand = ISTEquityCandidate(
        screen_id=screen_id,
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        scarcity_score=json.dumps({"overall": 4.6}),
        tier=1,
        tier_rationale="High scarcity",
        conviction="HIGH",
        catalyst="GB300 launch",
    )
    db.add(cand)
    db.commit()
    return cand


# -- GET /api/ist/screens/{id}/master-screen --------------------------------


class TestGetMasterScreen:
    """Tests for GET /api/ist/screens/{id}/master-screen."""

    def test_get_master_screen_populated(self, client, db):
        """Successfully get master screen with ranked equities."""
        create_resp = _create_screen(client, name="Master Screen Test")
        screen_id = create_resp.json()["id"]
        _create_master_screen(db, screen_id)

        resp = client.get(f"/api/ist/screens/{screen_id}/master-screen")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["totalEquities"] == 2
        assert data["tier1Count"] == 1
        assert isinstance(data["rankedEquities"], list)
        assert len(data["rankedEquities"]) == 2
        assert data["rankedEquities"][0]["ticker"] == "NVDA"
        assert data["rankedEquities"][0]["convictionScore"] == 92
        assert data["invariantCompliance"] is not None
        assert data["createdAt"] is not None

    def test_get_master_screen_not_found(self, client):
        """Returns 404 when master screen does not exist."""
        create_resp = _create_screen(client, name="No Master")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/master-screen")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "MASTER_SCREEN_NOT_FOUND"

    def test_get_master_screen_nonexistent_screen(self, client):
        """Returns 404 for nonexistent screen."""
        resp = client.get("/api/ist/screens/99999/master-screen")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "SCREEN_NOT_FOUND"


# -- GET /api/ist/screens/{id}/rotation -------------------------------------


class TestGetRotationStrategy:
    """Tests for GET /api/ist/screens/{id}/rotation."""

    def test_get_rotation_populated(self, client, db):
        """Successfully get rotation strategy."""
        create_resp = _create_screen(client, name="Rotation Test")
        screen_id = create_resp.json()["id"]
        _create_rotation_strategy(db, screen_id)

        resp = client.get(f"/api/ist/screens/{screen_id}/rotation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert isinstance(data["phaseAllocations"], list)
        assert len(data["phaseAllocations"]) == 1
        assert isinstance(data["rotationTriggers"], list)
        assert len(data["rotationTriggers"]) == 1
        assert isinstance(data["riskLimits"], list)
        assert len(data["riskLimits"]) == 1
        assert data["createdAt"] is not None

    def test_get_rotation_not_found(self, client):
        """Returns 404 when rotation strategy does not exist."""
        create_resp = _create_screen(client, name="No Rotation")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/rotation")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "ROTATION_NOT_FOUND"

    def test_get_rotation_nonexistent_screen(self, client):
        """Returns 404 for nonexistent screen."""
        resp = client.get("/api/ist/screens/99999/rotation")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "SCREEN_NOT_FOUND"


# -- GET /api/ist/screens/{id}/catalysts ------------------------------------


class TestGetCatalystCalendar:
    """Tests for GET /api/ist/screens/{id}/catalysts."""

    def test_get_catalysts_populated(self, client, db):
        """Successfully get catalyst calendar."""
        create_resp = _create_screen(client, name="Catalyst Test")
        screen_id = create_resp.json()["id"]
        _create_catalyst_calendar(db, screen_id)

        resp = client.get(f"/api/ist/screens/{screen_id}/catalysts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert isinstance(data["catalysts"], list)
        assert len(data["catalysts"]) == 2
        assert data["totalCatalysts"] == 2
        assert data["nextCatalyst"] == "Q2 2025"
        assert data["createdAt"] is not None

    def test_get_catalysts_not_found(self, client):
        """Returns 404 when catalyst calendar does not exist."""
        create_resp = _create_screen(client, name="No Catalysts")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/catalysts")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "CATALYSTS_NOT_FOUND"

    def test_get_catalysts_nonexistent_screen(self, client):
        """Returns 404 for nonexistent screen."""
        resp = client.get("/api/ist/screens/99999/catalysts")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "SCREEN_NOT_FOUND"


# -- GET /api/ist/screens/{id}/stress-tests ---------------------------------


class TestGetStressTests:
    """Tests for GET /api/ist/screens/{id}/stress-tests."""

    def test_get_stress_tests_populated(self, client, db):
        """Successfully get stress test results."""
        create_resp = _create_screen(client, name="Stress Test")
        screen_id = create_resp.json()["id"]
        _create_stress_test(db, screen_id)

        resp = client.get(f"/api/ist/screens/{screen_id}/stress-tests")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert isinstance(data["frameworkTests"], list)
        assert len(data["frameworkTests"]) == 1
        assert data["frameworkTests"][0]["scenario"] == "Demand Collapse"
        assert isinstance(data["nameTests"], list)
        assert len(data["nameTests"]) == 1
        assert isinstance(data["survivalScores"], list)
        assert len(data["survivalScores"]) == 1
        assert data["createdAt"] is not None

    def test_get_stress_tests_not_found(self, client):
        """Returns 404 when stress tests do not exist."""
        create_resp = _create_screen(client, name="No Stress")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/stress-tests")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "STRESS_TESTS_NOT_FOUND"

    def test_get_stress_tests_nonexistent_screen(self, client):
        """Returns 404 for nonexistent screen."""
        resp = client.get("/api/ist/screens/99999/stress-tests")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "SCREEN_NOT_FOUND"


# -- GET /api/ist/screens/{id}/report ---------------------------------------


class TestGetReport:
    """Tests for GET /api/ist/screens/{id}/report."""

    def test_get_report_populated(self, client, db):
        """Successfully get investment thesis report with markdown."""
        create_resp = _create_screen(client, name="Report Test")
        screen_id = create_resp.json()["id"]
        _create_report(db, screen_id)

        resp = client.get(f"/api/ist/screens/{screen_id}/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["title"] == "Investment Thesis Report: Test Screen"
        assert "## Executive Summary" in data["content"]
        assert "## Pillar-by-Pillar Analysis" in data["content"]
        assert data["metadata"] is not None
        assert data["metadata"]["pillarCount"] == 2
        assert data["metadata"]["equityCount"] == 2
        assert data["createdAt"] is not None

    def test_get_report_returns_markdown_content(self, client, db):
        """Report content is raw markdown (not JSON-encoded)."""
        create_resp = _create_screen(client, name="Markdown Test")
        screen_id = create_resp.json()["id"]
        _create_report(db, screen_id)

        resp = client.get(f"/api/ist/screens/{screen_id}/report")
        assert resp.status_code == 200
        content = resp.json()["content"]
        assert content.startswith("# ")  # Markdown heading
        assert "##" in content  # Sub-headings

    def test_get_report_not_found(self, client):
        """Returns 404 when report does not exist."""
        create_resp = _create_screen(client, name="No Report")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/report")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "REPORT_NOT_FOUND"

    def test_get_report_nonexistent_screen(self, client):
        """Returns 404 for nonexistent screen."""
        resp = client.get("/api/ist/screens/99999/report")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "SCREEN_NOT_FOUND"


# -- GET /api/ist/screens/{id}/handoff --------------------------------------


class TestGetHandoff:
    """Tests for GET /api/ist/screens/{id}/handoff."""

    def test_get_handoff_certified(self, client, db):
        """Successfully get handoff data from a certified screen."""
        create_resp = _create_screen(client, name="Handoff Test")
        screen_id = create_resp.json()["id"]
        _create_tier1_candidate(db, screen_id)
        _certify_screen(db, screen_id)

        resp = client.get(f"/api/ist/screens/{screen_id}/handoff")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["screenName"] == "Handoff Test"
        assert data["certified"] is True
        assert data["certifiedAt"] is not None
        assert data["tier1Count"] == 1
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["ticker"] == "NVDA"
        assert data["candidates"][0]["tier"] == 1
        assert data["candidates"][0]["conviction"] == "HIGH"

    def test_get_handoff_not_certified(self, client, db):
        """Returns 409 when screen is not yet certified."""
        create_resp = _create_screen(client, name="Not Certified")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/handoff")
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"]["code"] == "NOT_CERTIFIED"

    def test_get_handoff_nonexistent_screen(self, client):
        """Returns 404 for nonexistent screen."""
        resp = client.get("/api/ist/screens/99999/handoff")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "SCREEN_NOT_FOUND"

    def test_get_handoff_no_tier1_candidates(self, client, db):
        """Handoff returns empty candidates list when no Tier 1 candidates exist."""
        create_resp = _create_screen(client, name="No Tier 1")
        screen_id = create_resp.json()["id"]
        _certify_screen(db, screen_id)

        resp = client.get(f"/api/ist/screens/{screen_id}/handoff")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier1Count"] == 0
        assert data["candidates"] == []


# -- Error format consistency ------------------------------------------------


class TestErrorFormatConsistency:
    """Verify all new endpoints return consistent error format (INV-BE-02)."""

    @pytest.mark.parametrize("endpoint", [
        "/api/ist/screens/99999/master-screen",
        "/api/ist/screens/99999/rotation",
        "/api/ist/screens/99999/catalysts",
        "/api/ist/screens/99999/stress-tests",
        "/api/ist/screens/99999/report",
        "/api/ist/screens/99999/handoff",
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
