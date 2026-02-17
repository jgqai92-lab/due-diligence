"""Integration tests for IST Phase 2: Thematic Analysis endpoints.

Tests cover:
- GET /api/ist/screens/{id}/bottlenecks (empty + populated)
- GET /api/ist/screens/{id}/demand-models (empty + populated)
- GET /api/ist/screens/{id}/validation (empty + populated)
- 404 for non-existent screen on all 3 endpoints
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
    return client.post("/api/ist/screens", json=payload)


# ── GET /api/ist/screens/{id}/bottlenecks ──────────────────────────────────


class TestGetBottlenecks:
    """Tests for GET /api/ist/screens/{id}/bottlenecks."""

    def test_bottlenecks_empty(self, client):
        """Bottlenecks endpoint returns empty list for new screen."""
        create_resp = _create_screen(client, name="BN Empty Test")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/bottlenecks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["bottlenecks"] == []
        assert data["phaseCount"] == {
            "phase1": 0,
            "phase2": 0,
            "phase3": 0,
            "crossCutting": 0,
        }

    def test_bottlenecks_populated(self, client, db):
        """Bottlenecks endpoint returns populated data with correct structure."""
        from app.models.ist import ISTBottleneck

        create_resp = _create_screen(client, name="BN Populated")
        screen_id = create_resp.json()["id"]

        # Insert test bottlenecks directly
        parent = ISTBottleneck(
            screen_id=screen_id,
            name="GPU Supply Scarcity",
            phase=1,
            phase_label="Near-term (0-18 months)",
            description="NVIDIA production constrained",
            quantitative_evidence="330,000 units per GW",
            temporal_marker="2025-2026",
            resolution_trigger="TSMC expansion",
        )
        db.add(parent)
        db.flush()

        child = ISTBottleneck(
            screen_id=screen_id,
            name="Data Center Power",
            phase=2,
            phase_label="Mid-term (18-36 months)",
            description="Grid interconnection queues",
            quantitative_evidence="5-year queues",
            causal_parent_id=parent.id,
        )
        db.add(child)

        cross = ISTBottleneck(
            screen_id=screen_id,
            name="Talent Scarcity",
            phase=0,
            phase_label="Cross-cutting",
            description="AI engineer shortage",
        )
        db.add(cross)
        db.commit()

        resp = client.get(f"/api/ist/screens/{screen_id}/bottlenecks")
        assert resp.status_code == 200
        data = resp.json()

        assert data["screenId"] == screen_id
        assert len(data["bottlenecks"]) == 3
        assert data["phaseCount"] == {
            "phase1": 1,
            "phase2": 1,
            "phase3": 0,
            "crossCutting": 1,
        }

        # Verify bottleneck structure
        bn0 = data["bottlenecks"][0]  # phase 0 comes first due to ordering
        assert "id" in bn0
        assert "name" in bn0
        assert "phase" in bn0
        assert "phaseLabel" in bn0
        assert "description" in bn0
        assert "quantitativeEvidence" in bn0
        assert "temporalMarker" in bn0
        assert "resolutionTrigger" in bn0
        assert "causalParentId" in bn0
        assert "createdAt" in bn0

    def test_bottlenecks_causal_parent_linked(self, client, db):
        """Bottlenecks with causal parent show correct causalParentId."""
        from app.models.ist import ISTBottleneck

        create_resp = _create_screen(client, name="BN Causal")
        screen_id = create_resp.json()["id"]

        parent = ISTBottleneck(
            screen_id=screen_id,
            name="Parent BN",
            phase=1,
            phase_label="Near-term",
            description="Parent",
        )
        db.add(parent)
        db.flush()

        child = ISTBottleneck(
            screen_id=screen_id,
            name="Child BN",
            phase=2,
            phase_label="Mid-term",
            description="Child",
            causal_parent_id=parent.id,
        )
        db.add(child)
        db.commit()

        resp = client.get(f"/api/ist/screens/{screen_id}/bottlenecks")
        data = resp.json()

        # Find the child bottleneck
        child_bn = next(b for b in data["bottlenecks"] if b["name"] == "Child BN")
        assert child_bn["causalParentId"] == parent.id

    def test_bottlenecks_not_found(self, client):
        """Bottlenecks for non-existent screen returns 404."""
        resp = client.get("/api/ist/screens/99999/bottlenecks")
        assert resp.status_code == 404
        assert "SCREEN_NOT_FOUND" in resp.json()["detail"]["error"]["code"]


# ── GET /api/ist/screens/{id}/demand-models ────────────────────────────────


class TestGetDemandModels:
    """Tests for GET /api/ist/screens/{id}/demand-models."""

    def test_demand_models_empty(self, client):
        """Demand models endpoint returns empty list for new screen."""
        create_resp = _create_screen(client, name="DM Empty Test")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/demand-models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["demandModels"] == []

    def test_demand_models_populated(self, client, db):
        """Demand models endpoint returns populated data with parsed JSON fields."""
        from app.models.ist import ISTBottleneck, ISTDemandModel

        create_resp = _create_screen(client, name="DM Populated")
        screen_id = create_resp.json()["id"]

        # Create bottleneck first
        bn = ISTBottleneck(
            screen_id=screen_id,
            name="GPU Scarcity",
            phase=1,
            phase_label="Near-term",
            description="Test bottleneck",
        )
        db.add(bn)
        db.flush()

        # Create demand model
        dm = ISTDemandModel(
            screen_id=screen_id,
            bottleneck_id=bn.id,
            formula="TAM = Units * ASP",
            base_case=json.dumps({"demand": 1000, "tam": 50000000}),
            bull_case=json.dumps({"demand": 2000, "tam": 100000000}),
            bear_case=json.dumps({"demand": 500, "tam": 25000000}),
            sensitivity_table=json.dumps([
                {"variable": "ASP", "low": 20000, "base": 30000, "high": 40000, "tamImpact": "30%"}
            ]),
            multiplier_chain="GPU -> Cluster -> Revenue",
        )
        db.add(dm)
        db.commit()

        resp = client.get(f"/api/ist/screens/{screen_id}/demand-models")
        assert resp.status_code == 200
        data = resp.json()

        assert data["screenId"] == screen_id
        assert len(data["demandModels"]) == 1

        model = data["demandModels"][0]
        assert model["bottleneckName"] == "GPU Scarcity"
        assert model["formula"] == "TAM = Units * ASP"
        assert model["baseCase"]["demand"] == 1000
        assert model["bullCase"]["demand"] == 2000
        assert model["bearCase"]["demand"] == 500
        assert len(model["sensitivityTable"]) == 1
        assert model["sensitivityTable"][0]["variable"] == "ASP"
        assert model["multiplierChain"] == "GPU -> Cluster -> Revenue"
        assert "createdAt" in model

    def test_demand_models_not_found(self, client):
        """Demand models for non-existent screen returns 404."""
        resp = client.get("/api/ist/screens/99999/demand-models")
        assert resp.status_code == 404
        assert "SCREEN_NOT_FOUND" in resp.json()["detail"]["error"]["code"]


# ── GET /api/ist/screens/{id}/validation ───────────────────────────────────


class TestGetValidation:
    """Tests for GET /api/ist/screens/{id}/validation."""

    def test_validation_empty(self, client):
        """Validation endpoint returns empty list with zeroed summary."""
        create_resp = _create_screen(client, name="Val Empty Test")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/validation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["validations"] == []
        assert data["summary"] == {
            "confirmed": 0,
            "partiallyConfirmed": 0,
            "contradicted": 0,
            "unvalidatable": 0,
            "total": 0,
        }

    def test_validation_populated(self, client, db):
        """Validation endpoint returns populated data with correct summary."""
        from app.models.ist import ISTClaim, ISTValidation

        create_resp = _create_screen(client, name="Val Populated")
        screen_id = create_resp.json()["id"]

        # Create claims
        claim1 = ISTClaim(
            screen_id=screen_id,
            claim_text="GPU demand is growing",
            source_citation="Section 1",
            confidence=0.9,
        )
        claim2 = ISTClaim(
            screen_id=screen_id,
            claim_text="Power costs are declining",
            source_citation="Section 2",
            confidence=0.8,
        )
        db.add(claim1)
        db.add(claim2)
        db.flush()

        # Create validations
        val1 = ISTValidation(
            screen_id=screen_id,
            claim_id=claim1.id,
            verdict="confirmed",
            confidence=0.9,
            evidence="Widely reported GPU demand surge",
            sources=json.dumps([{"url": "https://example.com", "title": "Report"}]),
            search_queries=json.dumps(["GPU demand growth"]),
        )
        val2 = ISTValidation(
            screen_id=screen_id,
            claim_id=claim2.id,
            verdict="contradicted",
            confidence=0.7,
            evidence="Power costs are actually increasing",
            sources=json.dumps([]),
            search_queries=json.dumps(["power costs trend"]),
        )
        db.add(val1)
        db.add(val2)
        db.commit()

        resp = client.get(f"/api/ist/screens/{screen_id}/validation")
        assert resp.status_code == 200
        data = resp.json()

        assert data["screenId"] == screen_id
        assert len(data["validations"]) == 2
        assert data["summary"]["confirmed"] == 1
        assert data["summary"]["contradicted"] == 1
        assert data["summary"]["partiallyConfirmed"] == 0
        assert data["summary"]["unvalidatable"] == 0
        assert data["summary"]["total"] == 2

        # Verify validation item structure
        v0 = data["validations"][0]
        assert "id" in v0
        assert "claimId" in v0
        assert "claimText" in v0
        assert "verdict" in v0
        assert "confidence" in v0
        assert "evidence" in v0
        assert "sources" in v0
        assert "searchQueries" in v0
        assert "validatedAt" in v0

    def test_validation_summary_all_verdicts(self, client, db):
        """Validation summary counts all verdict types correctly."""
        from app.models.ist import ISTClaim, ISTValidation

        create_resp = _create_screen(client, name="Val Summary")
        screen_id = create_resp.json()["id"]

        claims = []
        for i in range(4):
            claim = ISTClaim(
                screen_id=screen_id,
                claim_text=f"Claim {i}",
                source_citation=f"Sec {i}",
                confidence=0.8,
            )
            db.add(claim)
            claims.append(claim)
        db.flush()

        verdicts = ["confirmed", "partially_confirmed", "contradicted", "unvalidatable"]
        for i, verdict in enumerate(verdicts):
            val = ISTValidation(
                screen_id=screen_id,
                claim_id=claims[i].id,
                verdict=verdict,
                confidence=0.8,
                evidence=f"Evidence for {verdict}",
                sources=json.dumps([]),
                search_queries=json.dumps([]),
            )
            db.add(val)
        db.commit()

        resp = client.get(f"/api/ist/screens/{screen_id}/validation")
        data = resp.json()

        assert data["summary"]["confirmed"] == 1
        assert data["summary"]["partiallyConfirmed"] == 1
        assert data["summary"]["contradicted"] == 1
        assert data["summary"]["unvalidatable"] == 1
        assert data["summary"]["total"] == 4

    def test_validation_not_found(self, client):
        """Validation for non-existent screen returns 404."""
        resp = client.get("/api/ist/screens/99999/validation")
        assert resp.status_code == 404
        assert "SCREEN_NOT_FOUND" in resp.json()["detail"]["error"]["code"]


# ── Cross-endpoint 404 consistency ─────────────────────────────────────────


class TestNotFoundConsistency:
    """Verify all 3 new endpoints return consistent 404 format (INV-BE-02)."""

    @pytest.mark.parametrize("endpoint", [
        "/api/ist/screens/99999/bottlenecks",
        "/api/ist/screens/99999/demand-models",
        "/api/ist/screens/99999/validation",
    ])
    def test_404_error_format(self, client, endpoint):
        """All endpoints use standard error format for 404."""
        resp = client.get(endpoint)
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert "error" in data["detail"]
        assert "code" in data["detail"]["error"]
        assert "message" in data["detail"]["error"]
        assert data["detail"]["error"]["code"] == "SCREEN_NOT_FOUND"
