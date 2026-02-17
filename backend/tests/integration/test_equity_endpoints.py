"""Integration tests for IST Phase 3: Equity Identification endpoints.

Tests cover:
- GET /api/ist/screens/{id}/candidates (empty + populated + tier filter + bottleneckId filter)
- GET /api/ist/screens/{id}/effects (empty + populated)
- GET /api/ist/screens/{id}/tiers (empty + populated)
- GET /api/ist/screens/{id}/invariants (empty + populated)
- 404 for non-existent screen on all 4 endpoints
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


def _make_scarcity_score(overall, dims=None):
    """Helper to create scarcity score JSON string."""
    if dims is None:
        dims = {
            "supplyConstraint": overall,
            "demandVisibility": overall,
            "substitutionDifficulty": overall,
            "pricingPower": overall,
            "temporalUrgency": overall,
        }
    return json.dumps({"overall": overall, "dimensions": dims})


# -- GET /api/ist/screens/{id}/candidates ------------------------------------


class TestGetCandidates:
    """Tests for GET /api/ist/screens/{id}/candidates."""

    def test_candidates_empty(self, client):
        """Candidates endpoint returns empty list for new screen."""
        create_resp = _create_screen(client, name="Cand Empty Test")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/candidates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["candidates"] == []
        assert data["tierBreakdown"] == {"tier1": 0, "tier2": 0, "tier3": 0}
        assert data["totalCount"] == 0

    def test_candidates_populated(self, client, db):
        """Candidates endpoint returns populated data with correct structure."""
        from app.models.ist import ISTBottleneck, ISTEquityCandidate

        create_resp = _create_screen(client, name="Cand Populated")
        screen_id = create_resp.json()["id"]

        # Create bottleneck first
        bn = ISTBottleneck(
            screen_id=screen_id,
            name="GPU Supply Scarcity",
            phase=1,
            phase_label="Near-term (0-18 months)",
            description="NVIDIA production constrained",
        )
        db.add(bn)
        db.flush()

        # Create equity candidate
        cand = ISTEquityCandidate(
            screen_id=screen_id,
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            bottleneck_id=bn.id,
            scarcity_score=_make_scarcity_score(4.6),
            moat_type="Scale + IP",
            moat_evidence="CUDA ecosystem lock-in",
            catalyst="GB300 launch",
            tier=1,
            tier_rationale="High scarcity score with moat",
            phase=1,
            conviction="HIGH",
            market_cap=2500000000000.0,
        )
        db.add(cand)
        db.commit()

        resp = client.get(f"/api/ist/screens/{screen_id}/candidates")
        assert resp.status_code == 200
        data = resp.json()

        assert data["screenId"] == screen_id
        assert data["totalCount"] == 1
        assert len(data["candidates"]) == 1
        assert data["tierBreakdown"]["tier1"] == 1

        c = data["candidates"][0]
        assert c["ticker"] == "NVDA"
        assert c["companyName"] == "NVIDIA Corporation"
        assert c["bottleneckId"] == bn.id
        assert c["bottleneckName"] == "GPU Supply Scarcity"
        assert c["scarcityScore"]["overall"] == 4.6
        assert c["moatType"] == "Scale + IP"
        assert c["moatEvidence"] == "CUDA ecosystem lock-in"
        assert c["catalyst"] == "GB300 launch"
        assert c["tier"] == 1
        assert c["tierRationale"] == "High scarcity score with moat"
        assert c["phase"] == 1
        assert c["conviction"] == "HIGH"
        assert c["marketCap"] == 2500000000000.0

    def test_candidates_tier_filter(self, client, db):
        """Candidates can be filtered by tier."""
        from app.models.ist import ISTBottleneck, ISTEquityCandidate

        create_resp = _create_screen(client, name="Tier Filter")
        screen_id = create_resp.json()["id"]

        bn = ISTBottleneck(
            screen_id=screen_id,
            name="Test BN",
            phase=1,
            phase_label="Near-term",
            description="Test",
        )
        db.add(bn)
        db.flush()

        # Tier 1 candidate
        db.add(ISTEquityCandidate(
            screen_id=screen_id,
            ticker="NVDA",
            company_name="NVIDIA",
            bottleneck_id=bn.id,
            scarcity_score=_make_scarcity_score(4.5),
            tier=1,
            conviction="HIGH",
        ))
        # Tier 2 candidate
        db.add(ISTEquityCandidate(
            screen_id=screen_id,
            ticker="AVGO",
            company_name="Broadcom",
            bottleneck_id=bn.id,
            scarcity_score=_make_scarcity_score(3.5),
            tier=2,
            conviction="MEDIUM",
        ))
        # Tier 3 candidate
        db.add(ISTEquityCandidate(
            screen_id=screen_id,
            ticker="INTC",
            company_name="Intel",
            bottleneck_id=bn.id,
            scarcity_score=_make_scarcity_score(2.0),
            tier=3,
            conviction="LOW",
        ))
        db.commit()

        # Filter tier 1 only
        resp = client.get(f"/api/ist/screens/{screen_id}/candidates?tier=1")
        data = resp.json()
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["ticker"] == "NVDA"
        # tierBreakdown should show all candidates (unfiltered)
        assert data["totalCount"] == 3
        assert data["tierBreakdown"]["tier1"] == 1
        assert data["tierBreakdown"]["tier2"] == 1
        assert data["tierBreakdown"]["tier3"] == 1

        # Filter tier 2
        resp = client.get(f"/api/ist/screens/{screen_id}/candidates?tier=2")
        assert len(resp.json()["candidates"]) == 1
        assert resp.json()["candidates"][0]["ticker"] == "AVGO"

    def test_candidates_bottleneck_filter(self, client, db):
        """Candidates can be filtered by bottleneckId."""
        from app.models.ist import ISTBottleneck, ISTEquityCandidate

        create_resp = _create_screen(client, name="BN Filter")
        screen_id = create_resp.json()["id"]

        bn1 = ISTBottleneck(
            screen_id=screen_id,
            name="GPU Scarcity",
            phase=1,
            phase_label="Near-term",
            description="GPU",
        )
        bn2 = ISTBottleneck(
            screen_id=screen_id,
            name="Power Scarcity",
            phase=2,
            phase_label="Mid-term",
            description="Power",
        )
        db.add(bn1)
        db.add(bn2)
        db.flush()

        db.add(ISTEquityCandidate(
            screen_id=screen_id,
            ticker="NVDA",
            company_name="NVIDIA",
            bottleneck_id=bn1.id,
            scarcity_score=_make_scarcity_score(4.5),
            tier=1,
            conviction="HIGH",
        ))
        db.add(ISTEquityCandidate(
            screen_id=screen_id,
            ticker="EATON",
            company_name="Eaton Corp",
            bottleneck_id=bn2.id,
            scarcity_score=_make_scarcity_score(3.5),
            tier=2,
            conviction="MEDIUM",
        ))
        db.commit()

        # Filter by bn1
        resp = client.get(f"/api/ist/screens/{screen_id}/candidates?bottleneckId={bn1.id}")
        data = resp.json()
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["ticker"] == "NVDA"

        # Filter by bn2
        resp = client.get(f"/api/ist/screens/{screen_id}/candidates?bottleneckId={bn2.id}")
        data = resp.json()
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["ticker"] == "EATON"

    def test_candidates_not_found(self, client):
        """Candidates for non-existent screen returns 404."""
        resp = client.get("/api/ist/screens/99999/candidates")
        assert resp.status_code == 404
        assert "SCREEN_NOT_FOUND" in resp.json()["detail"]["error"]["code"]


# -- GET /api/ist/screens/{id}/effects ----------------------------------------


class TestGetEffects:
    """Tests for GET /api/ist/screens/{id}/effects."""

    def test_effects_empty(self, client):
        """Effects endpoint returns empty list for new screen."""
        create_resp = _create_screen(client, name="Effects Empty")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/effects")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["effectsChains"] == []

    def test_effects_populated(self, client, db):
        """Effects endpoint returns populated data with correct structure."""
        from app.models.ist import ISTBottleneck, ISTEffectsChain, ISTEquityCandidate

        create_resp = _create_screen(client, name="Effects Populated")
        screen_id = create_resp.json()["id"]

        bn = ISTBottleneck(
            screen_id=screen_id,
            name="GPU Scarcity",
            phase=1,
            phase_label="Near-term",
            description="GPU",
        )
        db.add(bn)
        db.flush()

        cand = ISTEquityCandidate(
            screen_id=screen_id,
            ticker="NVDA",
            company_name="NVIDIA",
            bottleneck_id=bn.id,
            scarcity_score=_make_scarcity_score(4.5),
            tier=1,
            conviction="HIGH",
        )
        db.add(cand)
        db.flush()

        effect = ISTEffectsChain(
            screen_id=screen_id,
            thesis="GPU scarcity drives pricing power",
            effect_order=1,
            effect_description="Premium pricing maintained",
            equity_candidate_id=cand.id,
        )
        db.add(effect)
        db.commit()

        resp = client.get(f"/api/ist/screens/{screen_id}/effects")
        assert resp.status_code == 200
        data = resp.json()

        assert data["screenId"] == screen_id
        assert len(data["effectsChains"]) == 1

        e = data["effectsChains"][0]
        assert e["thesis"] == "GPU scarcity drives pricing power"
        assert e["order"] == 1
        assert e["effectDescription"] == "Premium pricing maintained"
        assert e["equityCandidateId"] == cand.id
        assert e["equityTicker"] == "NVDA"

    def test_effects_without_candidate(self, client, db):
        """Effects without equity candidate show null ticker."""
        from app.models.ist import ISTEffectsChain

        create_resp = _create_screen(client, name="Effects No Cand")
        screen_id = create_resp.json()["id"]

        effect = ISTEffectsChain(
            screen_id=screen_id,
            thesis="Broad market effect",
            effect_order=2,
            effect_description="Industry-wide impact",
            equity_candidate_id=None,
        )
        db.add(effect)
        db.commit()

        resp = client.get(f"/api/ist/screens/{screen_id}/effects")
        data = resp.json()
        assert len(data["effectsChains"]) == 1
        assert data["effectsChains"][0]["equityCandidateId"] is None
        assert data["effectsChains"][0]["equityTicker"] is None

    def test_effects_not_found(self, client):
        """Effects for non-existent screen returns 404."""
        resp = client.get("/api/ist/screens/99999/effects")
        assert resp.status_code == 404
        assert "SCREEN_NOT_FOUND" in resp.json()["detail"]["error"]["code"]


# -- GET /api/ist/screens/{id}/tiers ------------------------------------------


class TestGetTiers:
    """Tests for GET /api/ist/screens/{id}/tiers."""

    def test_tiers_empty(self, client):
        """Tiers endpoint returns empty tier structure for new screen."""
        create_resp = _create_screen(client, name="Tiers Empty")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/tiers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert data["tiers"]["tier1"]["count"] == 0
        assert data["tiers"]["tier2"]["count"] == 0
        assert data["tiers"]["tier3"]["count"] == 0
        assert data["tiers"]["tier1"]["label"] == "High Conviction"
        assert data["tiers"]["tier2"]["label"] == "Watchlist"
        assert data["tiers"]["tier3"]["label"] == "Speculative"
        assert data["tiers"]["tier1"]["candidates"] == []

    def test_tiers_populated(self, client, db):
        """Tiers endpoint organizes candidates by tier correctly."""
        from app.models.ist import ISTBottleneck, ISTEquityCandidate

        create_resp = _create_screen(client, name="Tiers Populated")
        screen_id = create_resp.json()["id"]

        bn = ISTBottleneck(
            screen_id=screen_id,
            name="GPU Scarcity",
            phase=1,
            phase_label="Near-term",
            description="GPU",
        )
        db.add(bn)
        db.flush()

        # Tier 1
        db.add(ISTEquityCandidate(
            screen_id=screen_id,
            ticker="NVDA",
            company_name="NVIDIA",
            bottleneck_id=bn.id,
            scarcity_score=_make_scarcity_score(4.5),
            moat_type="Scale",
            tier=1,
            tier_rationale="Tier 1",
            conviction="HIGH",
        ))
        # Tier 2
        db.add(ISTEquityCandidate(
            screen_id=screen_id,
            ticker="AVGO",
            company_name="Broadcom",
            bottleneck_id=bn.id,
            scarcity_score=_make_scarcity_score(3.5),
            moat_type="Custom",
            tier=2,
            tier_rationale="Tier 2",
            conviction="MEDIUM",
        ))
        db.commit()

        resp = client.get(f"/api/ist/screens/{screen_id}/tiers")
        assert resp.status_code == 200
        data = resp.json()

        assert data["tiers"]["tier1"]["count"] == 1
        assert data["tiers"]["tier2"]["count"] == 1
        assert data["tiers"]["tier3"]["count"] == 0

        t1_cand = data["tiers"]["tier1"]["candidates"][0]
        assert t1_cand["ticker"] == "NVDA"
        assert t1_cand["scarcityScore"]["overall"] == 4.5
        assert t1_cand["conviction"] == "HIGH"
        assert t1_cand["tierRationale"] == "Tier 1"

        t2_cand = data["tiers"]["tier2"]["candidates"][0]
        assert t2_cand["ticker"] == "AVGO"

    def test_tiers_not_found(self, client):
        """Tiers for non-existent screen returns 404."""
        resp = client.get("/api/ist/screens/99999/tiers")
        assert resp.status_code == 404
        assert "SCREEN_NOT_FOUND" in resp.json()["detail"]["error"]["code"]


# -- GET /api/ist/screens/{id}/invariants -------------------------------------


class TestGetInvariants:
    """Tests for GET /api/ist/screens/{id}/invariants."""

    def test_invariants_empty_screen(self, client):
        """Invariants endpoint returns results for empty screen (mostly FAIL)."""
        create_resp = _create_screen(client, name="Inv Empty")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/invariants")
        assert resp.status_code == 200
        data = resp.json()
        assert data["screenId"] == screen_id
        assert len(data["invariants"]) == 8
        # INV-1 should fail (no claims)
        inv1 = next(i for i in data["invariants"] if i["id"] == "INV-1")
        assert inv1["status"] == "FAIL"

    def test_invariants_populated_all_pass(self, client, db):
        """Invariants pass when data is complete."""
        from app.models.ist import ISTBottleneck, ISTClaim, ISTEquityCandidate

        create_resp = _create_screen(client, name="Inv Pass")
        screen_id = create_resp.json()["id"]

        # Add claims with citations, quant anchors, temporal markers
        for i in range(4):
            db.add(ISTClaim(
                screen_id=screen_id,
                claim_text=f"Claim {i}",
                source_citation=f"Section {i}",
                quantitative_anchor=f"{i * 100} units",
                temporal_marker=f"202{i}",
                confidence=0.9,
            ))

        bn = ISTBottleneck(
            screen_id=screen_id,
            name="Test BN",
            phase=1,
            phase_label="Near-term",
            description="Test",
        )
        db.add(bn)
        db.flush()

        cand = ISTEquityCandidate(
            screen_id=screen_id,
            ticker="NVDA",
            company_name="NVIDIA",
            bottleneck_id=bn.id,
            scarcity_score=_make_scarcity_score(4.5),
            tier=1,
            tier_rationale="Tier 1: High scarcity with moat",
            conviction="HIGH",
        )
        db.add(cand)
        db.commit()

        resp = client.get(f"/api/ist/screens/{screen_id}/invariants")
        assert resp.status_code == 200
        data = resp.json()
        assert data["allPassed"] is True
        assert data["failCount"] == 0
        assert data["passCount"] == 5

        # Check each invariant
        inv_map = {i["id"]: i for i in data["invariants"]}
        assert inv_map["INV-1"]["status"] == "PASS"
        assert inv_map["INV-2"]["status"] == "PASS"
        assert inv_map["INV-3"]["status"] == "PASS"
        assert inv_map["INV-4"]["status"] == "PASS"
        assert inv_map["INV-5"]["status"] == "PASS"
        assert inv_map["INV-6"]["status"] == "SKIPPED"
        assert inv_map["INV-7"]["status"] == "SKIPPED"
        assert inv_map["INV-8"]["status"] == "SKIPPED"

    def test_invariants_structure(self, client):
        """Each invariant has id, name, status, and details."""
        create_resp = _create_screen(client, name="Inv Structure")
        screen_id = create_resp.json()["id"]

        resp = client.get(f"/api/ist/screens/{screen_id}/invariants")
        data = resp.json()

        for inv in data["invariants"]:
            assert "id" in inv
            assert "name" in inv
            assert "status" in inv
            assert inv["status"] in ("PASS", "FAIL", "SKIPPED")
            assert "details" in inv

    def test_invariants_not_found(self, client):
        """Invariants for non-existent screen returns 404."""
        resp = client.get("/api/ist/screens/99999/invariants")
        assert resp.status_code == 404
        assert "SCREEN_NOT_FOUND" in resp.json()["detail"]["error"]["code"]


# -- Cross-endpoint 404 consistency -------------------------------------------


class TestNotFoundConsistency:
    """Verify all 4 new endpoints return consistent 404 format (INV-BE-02)."""

    @pytest.mark.parametrize("endpoint", [
        "/api/ist/screens/99999/candidates",
        "/api/ist/screens/99999/effects",
        "/api/ist/screens/99999/tiers",
        "/api/ist/screens/99999/invariants",
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
