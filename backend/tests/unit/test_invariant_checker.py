"""Unit tests for the HFRT invariant checker (Gap 3).

Test classes:
    TestMarketCapTier      -- _get_market_cap_tier() tier resolution
    TestDialecticIsolation -- audit_dialectic_isolation() cross-reference detection
    TestInvariants         -- each of 8 invariants: PASS and FAIL paths
"""

import json

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.hfrt import HFRTProject, HFRTTemplate, HFRTDialecticReview
from app.models.workflow import WorkflowRun
from app.services.hfrt.invariant_checker import (
    MARKET_CAP_TIER_THRESHOLDS,
    _get_market_cap_tier,
    _check_invariants,
    audit_dialectic_isolation,
)


# ── In-memory DB setup ────────────────────────────────────────────────────────

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


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def project(db):
    """A minimal HFRT project with no market cap set (defaults to mid_cap)."""
    run = WorkflowRun(workflow_type="HFRT", name="Test HFRT", status="PENDING")
    db.add(run)
    db.flush()
    proj = HFRTProject(
        workflow_run_id=run.id,
        ticker="TST",
        status="PENDING",
    )
    db.add(proj)
    db.flush()
    return proj


def _add_template(db, project_id: int, num: int, data: dict):
    """Helper: create an HFRTTemplate with JSON data."""
    tpl = HFRTTemplate(
        project_id=project_id,
        template_number=num,
        template_name=f"Template {num}",
        data=json.dumps(data),
        status="POPULATED",
    )
    db.add(tpl)
    db.flush()
    return tpl


def _add_dialectic(db, project_id: int, side: str, data: dict):
    """Helper: create an HFRTDialecticReview."""
    review = HFRTDialecticReview(
        project_id=project_id,
        side=side,
        content=json.dumps(data),
    )
    db.add(review)
    db.flush()
    return review


# ── TestMarketCapTier ─────────────────────────────────────────────────────────


class TestMarketCapTier:
    """Tests for _get_market_cap_tier() market-cap tier resolution."""

    def test_mega_cap(self, db, project):
        """Market cap >= 100B returns mega_cap."""
        project.market_cap = 150.0  # 150B
        db.flush()
        assert _get_market_cap_tier(db, project.id) == "mega_cap"

    def test_mega_cap_boundary(self, db, project):
        """Exactly 100B is mega_cap."""
        project.market_cap = 100.0
        db.flush()
        assert _get_market_cap_tier(db, project.id) == "mega_cap"

    def test_mid_cap(self, db, project):
        """Market cap in [2B, 100B) returns mid_cap."""
        project.market_cap = 50.0  # 50B
        db.flush()
        assert _get_market_cap_tier(db, project.id) == "mid_cap"

    def test_mid_cap_boundary(self, db, project):
        """Exactly 2B is mid_cap."""
        project.market_cap = 2.0
        db.flush()
        assert _get_market_cap_tier(db, project.id) == "mid_cap"

    def test_small_cap(self, db, project):
        """Market cap < 2B returns small_cap."""
        project.market_cap = 0.5  # 500M
        db.flush()
        assert _get_market_cap_tier(db, project.id) == "small_cap"

    def test_null_market_cap_defaults_to_mid_cap(self, db, project):
        """Unknown (null) market cap defaults to mid_cap."""
        project.market_cap = None
        db.flush()
        assert _get_market_cap_tier(db, project.id) == "mid_cap"

    def test_project_not_found_defaults_to_mid_cap(self, db):
        """Non-existent project ID defaults to mid_cap."""
        assert _get_market_cap_tier(db, 99999) == "mid_cap"

    def test_thresholds_dict_structure(self):
        """MARKET_CAP_TIER_THRESHOLDS contains all required keys."""
        for tier in ("mega_cap", "mid_cap", "small_cap"):
            assert tier in MARKET_CAP_TIER_THRESHOLDS
            thresholds = MARKET_CAP_TIER_THRESHOLDS[tier]
            assert "min_market_cap_billions" in thresholds
            assert "min_risk_entries" in thresholds
            assert "min_mgmt_categories" in thresholds

    def test_mega_cap_has_higher_thresholds_than_small_cap(self):
        """Mega cap requires more risk entries and mgmt categories than small cap."""
        mega = MARKET_CAP_TIER_THRESHOLDS["mega_cap"]
        small = MARKET_CAP_TIER_THRESHOLDS["small_cap"]
        assert mega["min_risk_entries"] > small["min_risk_entries"]
        assert mega["min_mgmt_categories"] > small["min_mgmt_categories"]


# ── TestDialecticIsolation ────────────────────────────────────────────────────


class TestDialecticIsolation:
    """Tests for audit_dialectic_isolation() cross-contamination detection."""

    def test_clean_bull_bear_is_isolated(self):
        """Independent bull and bear content with no cross-references is isolated."""
        bull = {"narrative": "Strong revenue growth driven by expanding AI moat."}
        bear = {"narrative": "Valuation is stretched relative to free cash flow yield."}
        result = audit_dialectic_isolation(json.dumps(bull), json.dumps(bear))
        assert result["is_isolated"] is True
        assert result["contamination_evidence"] == []

    def test_bull_references_bear_is_flagged(self):
        """Bull case referencing 'the bear case argues' is flagged."""
        bull = {"narrative": "As the bear case suggests, risks exist, but we believe upside dominates."}
        bear = {"narrative": "Revenue growth will decelerate significantly."}
        result = audit_dialectic_isolation(json.dumps(bull), json.dumps(bear))
        assert result["is_isolated"] is False
        assert len(result["contamination_evidence"]) >= 1

    def test_bear_references_bull_is_flagged(self):
        """Bear case referencing 'contrary to the bull' is flagged."""
        bull = {"narrative": "Margin expansion will continue."}
        bear = {"narrative": "Contrary to the bull thesis, margins are structurally under pressure."}
        result = audit_dialectic_isolation(json.dumps(bull), json.dumps(bear))
        assert result["is_isolated"] is False
        assert len(result["contamination_evidence"]) >= 1

    def test_opposing_analyst_reference_flagged(self):
        """Reference to 'the opposing case' is detected."""
        bull = {"narrative": "The opposing case has overlooked the network effects moat."}
        bear = {"narrative": "Cash flow generation is deteriorating."}
        result = audit_dialectic_isolation(json.dumps(bull), json.dumps(bear))
        assert result["is_isolated"] is False

    def test_shared_phrase_threshold(self):
        """Up to 5 shared 7-word phrases does not flag contamination.

        The checker triggers only when > 5 phrases are shared.  We use
        texts that share exactly one short overlapping phrase to stay
        well under the threshold.
        """
        bull = {"narrative": "Revenue growth driven by cloud expansion and AI adoption."}
        bear = {"narrative": "Revenue growth may slow due to macro headwinds and competition."}
        result = audit_dialectic_isolation(json.dumps(bull), json.dumps(bear))
        # Only a tiny number of shared phrases — should remain isolated
        assert result["is_isolated"] is True

    def test_invalid_json_returns_isolated(self):
        """Malformed JSON gracefully returns is_isolated=True (cannot audit)."""
        result = audit_dialectic_isolation("not valid json {", "also invalid")
        assert result["is_isolated"] is True
        assert result["contamination_evidence"] == []

    def test_empty_dicts_return_isolated(self):
        """Empty dicts have no cross-references and are isolated."""
        result = audit_dialectic_isolation(json.dumps({}), json.dumps({}))
        assert result["is_isolated"] is True

    def test_result_has_required_keys(self):
        """Return value always has is_isolated and contamination_evidence."""
        result = audit_dialectic_isolation("{}", "{}")
        assert "is_isolated" in result
        assert "contamination_evidence" in result
        assert isinstance(result["contamination_evidence"], list)


# ── TestInvariants ────────────────────────────────────────────────────────────


class TestInvariants:
    """PASS and FAIL paths for each of the 8 HFRT research invariants."""

    # ── INV-01: Multi-source citations ────────────────────────────────────────

    def test_inv01_pass(self, db, project):
        """INV-01 passes when templates 0, 7, and 8 all have data."""
        _add_template(db, project.id, 0, {"ticker": "TST", "source": "Research"})
        _add_template(db, project.id, 7, {"ceo": "CEO Name", "compensation": "Fair"})
        _add_template(db, project.id, 8, {"risk_register": [{"risk": "competition"}]})
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-01")
        assert inv["status"] == "PASS"

    def test_inv01_fail_missing_template(self, db, project):
        """INV-01 fails when a required template (idea screen) is absent."""
        _add_template(db, project.id, 7, {"ceo": "CEO"})
        # Template 0 and 8 not created
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-01")
        assert inv["status"] == "FAIL"
        assert "missing" in inv["details"].lower()

    # ── INV-02: No forward estimates ─────────────────────────────────────────

    def test_inv02_pass(self, db, project):
        """INV-02 passes when thesis uses company guidance, not analyst estimates."""
        _add_template(db, project.id, 11, {
            "investment_rationale": "Company guided for 20% revenue growth.",
            "overall_conviction_score": 0.75,
            "conviction_factors": ["moat", "management"],
        })
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-02")
        assert inv["status"] == "PASS"

    def test_inv02_fail_analyst_estimate_language(self, db, project):
        """INV-02 fails when thesis contains 'we estimate' language."""
        _add_template(db, project.id, 11, {
            "investment_rationale": "We estimate the company will grow at 25% CAGR.",
            "overall_conviction_score": 0.8,
            "conviction_factors": ["growth"],
        })
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-02")
        assert inv["status"] == "FAIL"
        assert "we estimate" in inv["details"]

    def test_inv02_fail_our_forecast_language(self, db, project):
        """INV-02 fails when thesis contains 'our forecast'."""
        _add_template(db, project.id, 11, {
            "investment_rationale": "Our forecast shows margin expansion of 300bps.",
            "overall_conviction_score": 0.6,
            "conviction_factors": ["margin"],
        })
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-02")
        assert inv["status"] == "FAIL"

    # ── INV-03: DCF terminal linkage ──────────────────────────────────────────

    def test_inv03_pass(self, db, project):
        """INV-03 passes when both valuation (dcf) and competitive position exist."""
        _add_template(db, project.id, 6, {"dcf": {"terminal_growth": 0.03, "wacc": 0.09}})
        _add_template(db, project.id, 3, {"moat": "Network effects", "peers": []})
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-03")
        assert inv["status"] == "PASS"

    def test_inv03_fail_no_dcf(self, db, project):
        """INV-03 fails when valuation template lacks a dcf key."""
        _add_template(db, project.id, 6, {"ev_ebitda": 20})  # no dcf key
        _add_template(db, project.id, 3, {"moat": "Brand"})
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-03")
        assert inv["status"] == "FAIL"

    def test_inv03_fail_no_competitive_position(self, db, project):
        """INV-03 fails when competitive position template is missing."""
        _add_template(db, project.id, 6, {"dcf": {"terminal_growth": 0.03}})
        # Template 3 not created
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-03")
        assert inv["status"] == "FAIL"

    # ── INV-04: Risk register populated (size-aware) ──────────────────────────

    def test_inv04_pass_mid_cap(self, db, project):
        """INV-04 passes for mid-cap with >= 5 risk entries."""
        project.market_cap = 10.0  # 10B mid-cap
        db.flush()
        risks = [{"risk": f"Risk {i}", "probability": "medium", "impact": "high"} for i in range(5)]
        _add_template(db, project.id, 8, {"risk_register": risks})
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-04")
        assert inv["status"] == "PASS"
        assert "mid_cap" in inv["details"]

    def test_inv04_fail_insufficient_mid_cap(self, db, project):
        """INV-04 fails for mid-cap with only 2 risk entries (needs 5)."""
        project.market_cap = 10.0  # mid-cap
        db.flush()
        risks = [{"risk": "Risk A"}, {"risk": "Risk B"}]
        _add_template(db, project.id, 8, {"risk_register": risks})
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-04")
        assert inv["status"] == "FAIL"

    def test_inv04_pass_small_cap_lower_threshold(self, db, project):
        """INV-04 passes for small-cap with only 3 risk entries (small-cap threshold)."""
        project.market_cap = 0.5  # 500M small-cap
        db.flush()
        risks = [{"risk": f"Risk {i}"} for i in range(3)]
        _add_template(db, project.id, 8, {"risk_register": risks})
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-04")
        assert inv["status"] == "PASS"
        assert "small_cap" in inv["details"]

    def test_inv04_fail_mega_cap_needs_more(self, db, project):
        """INV-04 fails for mega-cap with only 5 risk entries (needs 8)."""
        project.market_cap = 200.0  # 200B mega-cap
        db.flush()
        risks = [{"risk": f"Risk {i}"} for i in range(5)]
        _add_template(db, project.id, 8, {"risk_register": risks})
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-04")
        assert inv["status"] == "FAIL"
        assert "mega_cap" in inv["details"]

    # ── INV-05: Management red flags (size-aware) ─────────────────────────────

    def test_inv05_pass_mid_cap(self, db, project):
        """INV-05 passes for mid-cap with 3+ red flag categories covered."""
        project.market_cap = 10.0  # mid-cap, needs 3
        db.flush()
        _add_template(db, project.id, 7, {
            "insider_selling": "No unusual selling",
            "compensation": "Aligned with shareholders",
            "board_composition": "Independent majority",
            "ceo": "Strong track record",
        })
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-05")
        assert inv["status"] == "PASS"

    def test_inv05_fail_insufficient_categories(self, db, project):
        """INV-05 fails for mid-cap with only 1 red flag category covered."""
        project.market_cap = 10.0  # mid-cap, needs 3
        db.flush()
        _add_template(db, project.id, 7, {
            "insider_selling": "No unusual selling",
            # compensation, board_composition, ceo all absent
        })
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-05")
        assert inv["status"] == "FAIL"

    def test_inv05_pass_small_cap_lower_threshold(self, db, project):
        """INV-05 passes for small-cap with 2 categories (small-cap threshold)."""
        project.market_cap = 0.5  # small-cap, needs 2
        db.flush()
        _add_template(db, project.id, 7, {
            "insider_selling": "Minimal selling",
            "ceo": "Founder-led",
        })
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-05")
        assert inv["status"] == "PASS"

    def test_inv05_fail_missing_management_template(self, db, project):
        """INV-05 fails when management assessment template is absent."""
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-05")
        assert inv["status"] == "FAIL"

    # ── INV-06: Earnings quality scored ──────────────────────────────────────

    def test_inv06_pass_quality_score(self, db, project):
        """INV-06 passes with quality_score field present."""
        _add_template(db, project.id, 9, {"quality_score": 7.5, "methodology": "Accruals ratio"})
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-06")
        assert inv["status"] == "PASS"
        assert "quality_score" in inv["details"]

    def test_inv06_pass_cash_flow_quality_score(self, db, project):
        """INV-06 passes with cash_flow_quality_score (Gap 3 addition)."""
        _add_template(db, project.id, 9, {"cash_flow_quality_score": 8.0})
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-06")
        assert inv["status"] == "PASS"
        assert "cash_flow_quality_score" in inv["details"]

    def test_inv06_pass_overall_score(self, db, project):
        """INV-06 passes with overall_score field."""
        _add_template(db, project.id, 9, {"overall_score": 6.0})
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-06")
        assert inv["status"] == "PASS"

    def test_inv06_fail_no_score(self, db, project):
        """INV-06 fails when QoE template is present but has no score field."""
        _add_template(db, project.id, 9, {"narrative": "Earnings appear high quality."})
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-06")
        assert inv["status"] == "FAIL"
        assert "no score" in inv["details"].lower()

    def test_inv06_fail_missing_qoe_template(self, db, project):
        """INV-06 fails when QoE template (9) is absent entirely."""
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-06")
        assert inv["status"] == "FAIL"
        assert "no qoe" in inv["details"].lower()

    # ── INV-07: Dialectic isolation ───────────────────────────────────────────

    def test_inv07_pass(self, db, project):
        """INV-07 passes with independent bull and bear reviews."""
        _add_dialectic(db, project.id, "BULL", {
            "narrative": "Revenue growth from cloud expansion will drive shareholder value.",
        })
        _add_dialectic(db, project.id, "BEAR", {
            "narrative": "Margin compression and debt levels pose significant downside risk.",
        })
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-07")
        assert inv["status"] == "PASS"

    def test_inv07_fail_missing_review(self, db, project):
        """INV-07 fails when bull or bear review is absent."""
        _add_dialectic(db, project.id, "BULL", {"narrative": "Growth story."})
        # Bear review not created
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-07")
        assert inv["status"] == "FAIL"
        assert "missing" in inv["details"].lower()

    def test_inv07_fail_cross_contamination(self, db, project):
        """INV-07 fails when bull case explicitly references the bear case."""
        _add_dialectic(db, project.id, "BULL", {
            "narrative": "As the bear case suggests risks exist, but growth will prevail.",
        })
        _add_dialectic(db, project.id, "BEAR", {
            "narrative": "Valuation is stretched regardless of growth assumptions.",
        })
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-07")
        assert inv["status"] == "FAIL"
        assert "cross" in inv["details"].lower() or "contamination" in inv["details"].lower()

    # ── INV-08: Thesis conviction scored ─────────────────────────────────────

    def test_inv08_pass(self, db, project):
        """INV-08 passes when thesis has conviction factors and overall score."""
        _add_template(db, project.id, 11, {
            "overall_conviction_score": 0.78,
            "conviction_factors": [
                {"factor": "competitive moat", "weight": 0.4},
                {"factor": "management quality", "weight": 0.3},
                {"factor": "valuation discount", "weight": 0.3},
            ],
            "recommendation": "BUY",
        })
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-08")
        assert inv["status"] == "PASS"
        assert "0.78" in inv["details"]

    def test_inv08_fail_no_conviction_score(self, db, project):
        """INV-08 fails when thesis lacks overall_conviction_score."""
        _add_template(db, project.id, 11, {
            "conviction_factors": ["moat"],
            "recommendation": "BUY",
            # No overall_conviction_score
        })
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-08")
        assert inv["status"] == "FAIL"

    def test_inv08_fail_no_conviction_factors(self, db, project):
        """INV-08 fails when thesis has a score but no conviction_factors."""
        _add_template(db, project.id, 11, {
            "overall_conviction_score": 0.7,
            # No conviction_factors
            "recommendation": "BUY",
        })
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-08")
        assert inv["status"] == "FAIL"

    def test_inv08_fail_missing_thesis_template(self, db, project):
        """INV-08 fails when investment thesis template (11) is absent."""
        results = _check_invariants(db, project.id)
        inv = next(r for r in results if r["id"] == "INV-08")
        assert inv["status"] == "FAIL"

    # ── All-invariant structure tests ─────────────────────────────────────────

    def test_returns_all_8_invariants(self, db, project):
        """_check_invariants always returns exactly 8 invariant results."""
        results = _check_invariants(db, project.id)
        assert len(results) == 8

    def test_all_invariant_ids_present(self, db, project):
        """All 8 invariant IDs (INV-01 through INV-08) are present."""
        results = _check_invariants(db, project.id)
        ids = {r["id"] for r in results}
        for i in range(1, 9):
            assert f"INV-0{i}" in ids

    def test_each_result_has_required_fields(self, db, project):
        """Every invariant result has id, name, status, and details."""
        results = _check_invariants(db, project.id)
        for r in results:
            assert "id" in r
            assert "name" in r
            assert "status" in r
            assert r["status"] in ("PASS", "FAIL")
            assert "details" in r

    def test_empty_project_all_fail(self, db, project):
        """A project with no templates or reviews fails most invariants."""
        results = _check_invariants(db, project.id)
        statuses = [r["status"] for r in results]
        # Most will fail without any templates/reviews (INV-02 may pass as no forward estimates)
        fail_count = statuses.count("FAIL")
        assert fail_count >= 5, f"Expected most to FAIL on empty project, got {fail_count} FAIL"
