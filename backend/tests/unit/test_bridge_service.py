"""Unit tests for the IST-to-HFRT bridge service."""

import json

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.ist import ISTScreen, ISTEquityCandidate, ISTBottleneck
from app.models.hfrt import HFRTProject, HFRTTemplate
from app.models.workflow import WorkflowRun, WorkflowStep
from app.services.bridge import (
    get_handoff_candidates,
    create_hfrt_from_handoff,
    HFRT_WORKFLOW_STEPS,
    HFRT_TEMPLATES,
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


SAMPLE_HANDOFF = {
    "screenName": "GPU Supply Screen",
    "screenId": 1,
    "certifiedAt": "2026-02-20T10:00:00Z",
    "tier1Count": 2,
    "totalCount": 3,
    "tierBreakdown": {"tier1": 2, "tier2": 1, "tier3": 0},
    "candidates": [
        {
            "ticker": "NVDA",
            "companyName": "NVIDIA Corporation",
            "tier": 1,
            "conviction": "High",
            "pillar": "GPU Supply Scarcity",
            "catalyst": "H100 ramp",
            "scarcityScore": 8.5,
        },
        {
            "ticker": "AVGO",
            "companyName": "Broadcom Inc.",
            "tier": 1,
            "conviction": "Medium",
            "pillar": "Custom Silicon",
            "catalyst": "TPU partnership",
            "scarcityScore": {"composite": 7.2, "overall": 7.0},
        },
        {
            "ticker": "AMD",
            "companyName": "Advanced Micro Devices",
            "tier": 2,
            "conviction": "Medium",
            "pillar": "GPU Competition",
            "catalyst": "MI300X launch",
            "scarcityScore": 6.0,
        },
    ],
}


@pytest.fixture()
def certified_screen(db):
    """Create a certified IST screen with handoff data."""
    run = WorkflowRun(workflow_type="IST", name="Test", status="COMPLETED")
    db.add(run)
    db.flush()

    screen = ISTScreen(
        workflow_run_id=run.id,
        name="GPU Supply Screen",
        status="COMPLETED",
        content_type="podcast_transcript",
        raw_content="x" * 200,
        is_certified=1,
        hfrt_handoff=json.dumps(SAMPLE_HANDOFF),
    )
    db.add(screen)
    db.flush()
    return screen


# ── get_handoff_candidates ───────────────────────────────────────────────────


class TestGetHandoffCandidates:
    """Tests for get_handoff_candidates()."""

    def test_success(self, db, certified_screen):
        result = get_handoff_candidates(db, certified_screen.id)
        assert result["screenName"] == "GPU Supply Screen"
        assert result["totalCount"] == 3
        assert len(result["candidates"]) == 3

    def test_screen_not_found(self, db):
        with pytest.raises(ValueError, match="not found"):
            get_handoff_candidates(db, 99999)

    def test_screen_not_certified(self, db, certified_screen):
        certified_screen.is_certified = 0
        db.flush()
        with pytest.raises(ValueError, match="not certified"):
            get_handoff_candidates(db, certified_screen.id)

    def test_no_handoff_data(self, db, certified_screen):
        certified_screen.hfrt_handoff = None
        db.flush()
        with pytest.raises(ValueError, match="No handoff data"):
            get_handoff_candidates(db, certified_screen.id)

    def test_empty_handoff_json(self, db, certified_screen):
        certified_screen.hfrt_handoff = json.dumps({})
        db.flush()
        with pytest.raises(ValueError, match="No handoff data"):
            get_handoff_candidates(db, certified_screen.id)

    def test_invalid_json_handoff(self, db, certified_screen):
        certified_screen.hfrt_handoff = "not valid json"
        db.flush()
        with pytest.raises(ValueError, match="No handoff data"):
            get_handoff_candidates(db, certified_screen.id)

    def test_backward_compat_rebuilds_from_db(self, db, certified_screen):
        """Old format (no totalCount) triggers DB query to rebuild."""
        old_handoff = {
            "screenName": "GPU Supply Screen",
            "certifiedAt": "2026-02-20T10:00:00Z",
            "tier1Count": 1,
            "candidates": [{"ticker": "NVDA", "companyName": "NVIDIA"}],
        }
        certified_screen.hfrt_handoff = json.dumps(old_handoff)

        # Add equity candidates in DB for the rebuild
        bn = ISTBottleneck(
            screen_id=certified_screen.id,
            name="GPU Scarcity",
            phase=1,
            phase_label="Current Phase",
            description="GPU supply constraints",
        )
        db.add(bn)
        db.flush()

        cand1 = ISTEquityCandidate(
            screen_id=certified_screen.id,
            bottleneck_id=bn.id,
            ticker="NVDA",
            company_name="NVIDIA Corp",
            tier=1,
            conviction="HIGH",
            catalyst="H100",
            scarcity_score=json.dumps({"overall": 8.5}),
        )
        cand2 = ISTEquityCandidate(
            screen_id=certified_screen.id,
            bottleneck_id=bn.id,
            ticker="AMD",
            company_name="AMD Inc",
            tier=2,
            conviction="MEDIUM",
            catalyst="MI300X",
            scarcity_score=json.dumps({"overall": 5.0}),
        )
        db.add_all([cand1, cand2])
        db.flush()

        result = get_handoff_candidates(db, certified_screen.id)
        assert result["totalCount"] == 2
        assert result["tierBreakdown"]["tier1"] == 1
        assert result["tierBreakdown"]["tier2"] == 1
        assert len(result["candidates"]) == 2

    def test_backward_compat_scarcity_score_parsing(self, db, certified_screen):
        """Backward compat handles dict scarcity_score."""
        old_handoff = {"screenName": "Test", "certifiedAt": "2026-01-01", "tier1Count": 0}
        certified_screen.hfrt_handoff = json.dumps(old_handoff)

        bn = ISTBottleneck(screen_id=certified_screen.id, name="B1", phase=1, phase_label="Current", description="Bottleneck B1")
        db.add(bn)
        db.flush()

        cand = ISTEquityCandidate(
            screen_id=certified_screen.id,
            bottleneck_id=bn.id,
            ticker="TST",
            company_name="Test Corp",
            tier=1,
            conviction="HIGH",
            scarcity_score=json.dumps({"overall": 7.5}),
        )
        db.add(cand)
        db.flush()

        result = get_handoff_candidates(db, certified_screen.id)
        tst = next(c for c in result["candidates"] if c["ticker"] == "TST")
        assert tst["scarcityScore"] == 7.5


# ── create_hfrt_from_handoff ────────────────────────────────────────────────


class TestCreateHFRTFromHandoff:
    """Tests for create_hfrt_from_handoff()."""

    def test_creates_workflow_run(self, db, certified_screen):
        result = create_hfrt_from_handoff(db, certified_screen.id, "NVDA")
        assert result["ticker"] == "NVDA"
        assert result["companyName"] == "NVIDIA Corporation"
        run = db.query(WorkflowRun).filter(WorkflowRun.id == result["workflowRunId"]).first()
        assert run.workflow_type == "HFRT"
        assert "IST Handoff" in run.name

    def test_creates_hfrt_project_with_source(self, db, certified_screen):
        result = create_hfrt_from_handoff(db, certified_screen.id, "NVDA")
        project = db.query(HFRTProject).filter(HFRTProject.id == result["projectId"]).first()
        assert project.source == "IST_HANDOFF"
        assert project.ist_screen_id == certified_screen.id
        assert project.ticker == "NVDA"

    def test_creates_24_workflow_steps(self, db, certified_screen):
        """Gap 1: external_validation added — total steps is now 24."""
        result = create_hfrt_from_handoff(db, certified_screen.id, "NVDA")
        steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == result["workflowRunId"])
            .all()
        )
        assert len(steps) == 24

    def test_creates_15_templates(self, db, certified_screen):
        result = create_hfrt_from_handoff(db, certified_screen.id, "NVDA")
        templates = (
            db.query(HFRTTemplate)
            .filter(HFRTTemplate.project_id == result["projectId"])
            .all()
        )
        assert len(templates) == 15

    def test_idea_screen_template_pre_populated(self, db, certified_screen):
        result = create_hfrt_from_handoff(db, certified_screen.id, "NVDA")
        idea = (
            db.query(HFRTTemplate)
            .filter(
                HFRTTemplate.project_id == result["projectId"],
                HFRTTemplate.template_number == 0,
            )
            .first()
        )
        assert idea.status == "POPULATED"
        data = json.loads(idea.data)
        assert data["ticker"] == "NVDA"
        assert data["prePopulated"] is True
        assert data["istScreenId"] == certified_screen.id
        assert data["scarcityScore"] == 8.5

    def test_other_templates_are_empty(self, db, certified_screen):
        result = create_hfrt_from_handoff(db, certified_screen.id, "NVDA")
        empty = (
            db.query(HFRTTemplate)
            .filter(
                HFRTTemplate.project_id == result["projectId"],
                HFRTTemplate.template_number > 0,
            )
            .all()
        )
        assert all(t.status == "EMPTY" for t in empty)

    def test_ticker_case_insensitive(self, db, certified_screen):
        result = create_hfrt_from_handoff(db, certified_screen.id, "nvda")
        assert result["ticker"] == "NVDA"

    def test_ticker_with_whitespace(self, db, certified_screen):
        result = create_hfrt_from_handoff(db, certified_screen.id, "  nvda  ")
        assert result["ticker"] == "NVDA"

    def test_ticker_not_in_candidates(self, db, certified_screen):
        with pytest.raises(ValueError, match="not found in handoff candidates"):
            create_hfrt_from_handoff(db, certified_screen.id, "INTC")

    def test_screen_not_found(self, db):
        with pytest.raises(ValueError, match="not found"):
            create_hfrt_from_handoff(db, 99999, "NVDA")

    def test_screen_not_certified(self, db, certified_screen):
        certified_screen.is_certified = 0
        db.flush()
        with pytest.raises(ValueError, match="not certified"):
            create_hfrt_from_handoff(db, certified_screen.id, "NVDA")

    def test_no_handoff_data(self, db, certified_screen):
        certified_screen.hfrt_handoff = None
        db.flush()
        with pytest.raises(ValueError, match="No handoff data"):
            create_hfrt_from_handoff(db, certified_screen.id, "NVDA")

    def test_nested_scarcity_score_extracted(self, db, certified_screen):
        """Scarcity score with nested dict extracts composite value."""
        result = create_hfrt_from_handoff(db, certified_screen.id, "AVGO")
        idea = (
            db.query(HFRTTemplate)
            .filter(
                HFRTTemplate.project_id == result["projectId"],
                HFRTTemplate.template_number == 0,
            )
            .first()
        )
        data = json.loads(idea.data)
        assert data["scarcityScore"] == 7.2  # composite, not overall

    def test_returns_link(self, db, certified_screen):
        result = create_hfrt_from_handoff(db, certified_screen.id, "NVDA")
        assert result["link"] == f"/research/{result['projectId']}"

    def test_step_model_tiers_preserved(self, db, certified_screen):
        result = create_hfrt_from_handoff(db, certified_screen.id, "NVDA")
        steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == result["workflowRunId"])
            .order_by(WorkflowStep.step_order)
            .all()
        )
        # idea_screen is sonnet
        assert steps[0].model_tier == "sonnet"
        # business_model is opus
        bm = next(s for s in steps if s.step_name == "business_model")
        assert bm.model_tier == "opus"


# ── Constants Tests ──────────────────────────────────────────────────────────


class TestBridgeConstants:
    """Tests for HFRT_WORKFLOW_STEPS and HFRT_TEMPLATES constants."""

    def test_workflow_steps_count(self):
        """Gap 1: external_validation added — total steps is now 24."""
        assert len(HFRT_WORKFLOW_STEPS) == 24

    def test_templates_count(self):
        assert len(HFRT_TEMPLATES) == 15

    def test_all_steps_have_required_fields(self):
        for step in HFRT_WORKFLOW_STEPS:
            assert "step_name" in step
            assert "phase" in step
            assert "step_order" in step
            assert "model" in step

    def test_step_orders_unique(self):
        orders = [s["step_order"] for s in HFRT_WORKFLOW_STEPS]
        assert len(orders) == len(set(orders))

    def test_step_names_unique(self):
        names = [s["step_name"] for s in HFRT_WORKFLOW_STEPS]
        assert len(names) == len(set(names))

    def test_phases_sequential(self):
        phases = sorted(set(s["phase"] for s in HFRT_WORKFLOW_STEPS))
        assert phases == [1, 2, 3, 4, 5]
