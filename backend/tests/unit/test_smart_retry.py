"""Tests for the smart retry feature (7E).

Validates that retry_workflow() correctly handles the retry_strategy
field on gate steps, resetting parent steps when a gate fails so that
fresh data is regenerated before the gate re-checks.

Test cases:
1. Non-gate step (no retry_strategy): only resets itself
2. Gate step with retry_strategy="with_parent": resets itself AND parents
3. Parent output_data is cleared during smart retry
4. Mixed steps: only the gate's parents get reset
5. Explicit retry_strategy="self": only resets itself
6. NULL retry_strategy: only resets itself (backward compat)
7. retry_strategy is persisted from step definitions
"""

import json
import os

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, AsyncMock

from app.models.workflow import WorkflowRun, WorkflowStep
from app.services.workflow_engine import retry_workflow


# ── Test database setup ──────────────────────────────────────────────────────

TEST_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "test_smart_retry.db"
)
TEST_DB_URL = f"sqlite:///{os.path.abspath(TEST_DB_PATH)}"

os.makedirs(os.path.dirname(os.path.abspath(TEST_DB_PATH)), exist_ok=True)

test_engine = create_engine(
    TEST_DB_URL, connect_args={"check_same_thread": False}
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine
)

_workflow_tables = [
    WorkflowRun.__table__,
    WorkflowStep.__table__,
]


@pytest.fixture(autouse=True)
def setup_db():
    """Create workflow tables before each test, drop after."""
    for table in reversed(_workflow_tables):
        try:
            table.drop(bind=test_engine, checkfirst=True)
        except Exception:
            pass
    for table in _workflow_tables:
        table.create(bind=test_engine, checkfirst=True)
    yield
    for table in reversed(_workflow_tables):
        try:
            table.drop(bind=test_engine, checkfirst=True)
        except Exception:
            pass


@pytest.fixture
def db_session():
    """Provide a clean DB session for each test."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _create_workflow(db, status="FAILED"):
    """Helper: create a WorkflowRun in FAILED state (ready for retry)."""
    run = WorkflowRun(
        workflow_type="IST",
        name="Test Workflow",
        status=status,
        current_phase=1,
        auto_advance=True,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run.id


def _create_step(
    db,
    workflow_run_id,
    step_name,
    phase=1,
    phase_name="Test Phase",
    step_order=1,
    depends_on=None,
    status="PENDING",
    retry_strategy=None,
    output_data=None,
):
    """Helper: create a WorkflowStep."""
    step = WorkflowStep(
        workflow_run_id=workflow_run_id,
        step_name=step_name,
        phase=phase,
        phase_name=phase_name,
        step_order=step_order,
        status=status,
        depends_on=json.dumps(depends_on) if depends_on is not None else None,
        retry_strategy=retry_strategy,
        output_data=output_data,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


# ── Tests ────────────────────────────────────────────────────────────────────


class TestSmartRetry:
    """Tests for the smart retry logic in retry_workflow()."""

    @pytest.mark.asyncio
    async def test_retry_non_gate_step_resets_only_self(self, db_session):
        """A FAILED non-gate step (no retry_strategy) only resets itself."""
        wid = _create_workflow(db_session)

        # Parent step is COMPLETED
        parent = _create_step(
            db_session, wid, "parent_step",
            step_order=1, depends_on=[], status="COMPLETED",
            output_data='{"result": "old data"}',
        )

        # Child step FAILED (no retry_strategy)
        child = _create_step(
            db_session, wid, "child_step",
            step_order=2, depends_on=["parent_step"], status="FAILED",
            retry_strategy=None,
        )

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal), \
             patch("app.services.workflow_engine.start_workflow", new_callable=AsyncMock):
            await retry_workflow(wid)

        db_session.expire_all()
        parent = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "parent_step",
            WorkflowStep.workflow_run_id == wid,
        ).first()
        child = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "child_step",
            WorkflowStep.workflow_run_id == wid,
        ).first()

        # Child should be reset to PENDING
        assert child.status == "PENDING"
        assert child.error_message is None

        # Parent should remain COMPLETED with output_data intact
        assert parent.status == "COMPLETED"
        assert parent.output_data == '{"result": "old data"}'

    @pytest.mark.asyncio
    async def test_retry_gate_step_with_parent_resets_parents(self, db_session):
        """A FAILED gate step with retry_strategy='with_parent' resets
        itself AND its depends_on parents to PENDING."""
        wid = _create_workflow(db_session)

        # Two parent steps (COMPLETED)
        _create_step(
            db_session, wid, "report_generation",
            step_order=1, depends_on=[], status="COMPLETED",
            output_data='{"report": "old report"}',
        )
        _create_step(
            db_session, wid, "stress_tests",
            step_order=2, depends_on=[], status="COMPLETED",
            output_data='{"tests": "old tests"}',
        )

        # Gate step FAILED with retry_strategy="with_parent"
        _create_step(
            db_session, wid, "screen_coherence_gate",
            step_order=3, depends_on=["report_generation", "stress_tests"],
            status="FAILED", retry_strategy="with_parent",
        )

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal), \
             patch("app.services.workflow_engine.start_workflow", new_callable=AsyncMock), \
             patch("app.services.workflow_engine.emit_sse_event", new_callable=AsyncMock):
            await retry_workflow(wid)

        db_session.expire_all()

        gate = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "screen_coherence_gate",
            WorkflowStep.workflow_run_id == wid,
        ).first()
        report = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "report_generation",
            WorkflowStep.workflow_run_id == wid,
        ).first()
        stress = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "stress_tests",
            WorkflowStep.workflow_run_id == wid,
        ).first()

        # Gate should be reset
        assert gate.status == "PENDING"
        assert gate.error_message is None

        # Both parents should be reset
        assert report.status == "PENDING"
        assert stress.status == "PENDING"

    @pytest.mark.asyncio
    async def test_retry_gate_clears_parent_output_data(self, db_session):
        """Parent steps have their output_data set to None during smart retry."""
        wid = _create_workflow(db_session)

        _create_step(
            db_session, wid, "report_generation",
            step_order=1, depends_on=[], status="COMPLETED",
            output_data='{"report": "stale data that should be cleared"}',
        )
        _create_step(
            db_session, wid, "screen_coherence_gate",
            step_order=2, depends_on=["report_generation"],
            status="FAILED", retry_strategy="with_parent",
        )

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal), \
             patch("app.services.workflow_engine.start_workflow", new_callable=AsyncMock), \
             patch("app.services.workflow_engine.emit_sse_event", new_callable=AsyncMock):
            await retry_workflow(wid)

        db_session.expire_all()

        report = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "report_generation",
            WorkflowStep.workflow_run_id == wid,
        ).first()

        # output_data must be cleared
        assert report.output_data is None
        assert report.status == "PENDING"
        assert report.started_at is None
        assert report.completed_at is None
        assert report.duration_ms is None

    @pytest.mark.asyncio
    async def test_retry_mixed_steps(self, db_session):
        """If both a gate (with_parent) and a non-gate step fail,
        only the gate's parents get reset."""
        wid = _create_workflow(db_session)

        # Parent of the gate (COMPLETED)
        _create_step(
            db_session, wid, "report_generation",
            step_order=1, depends_on=[], status="COMPLETED",
            output_data='{"report": "data"}',
        )

        # Parent of the non-gate (COMPLETED)
        _create_step(
            db_session, wid, "unrelated_parent",
            step_order=2, depends_on=[], status="COMPLETED",
            output_data='{"other": "data"}',
        )

        # Gate step FAILED (with_parent)
        _create_step(
            db_session, wid, "screen_coherence_gate",
            step_order=3, depends_on=["report_generation"],
            status="FAILED", retry_strategy="with_parent",
        )

        # Non-gate step FAILED (no retry_strategy)
        _create_step(
            db_session, wid, "regular_step",
            step_order=4, depends_on=["unrelated_parent"],
            status="FAILED", retry_strategy=None,
        )

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal), \
             patch("app.services.workflow_engine.start_workflow", new_callable=AsyncMock), \
             patch("app.services.workflow_engine.emit_sse_event", new_callable=AsyncMock):
            await retry_workflow(wid)

        db_session.expire_all()

        # Gate's parent should be reset (smart retry)
        report = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "report_generation",
            WorkflowStep.workflow_run_id == wid,
        ).first()
        assert report.status == "PENDING"
        assert report.output_data is None

        # Non-gate's parent should remain COMPLETED
        unrelated = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "unrelated_parent",
            WorkflowStep.workflow_run_id == wid,
        ).first()
        assert unrelated.status == "COMPLETED"
        assert unrelated.output_data == '{"other": "data"}'

        # Both failed steps should be reset
        gate = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "screen_coherence_gate",
            WorkflowStep.workflow_run_id == wid,
        ).first()
        regular = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "regular_step",
            WorkflowStep.workflow_run_id == wid,
        ).first()
        assert gate.status == "PENDING"
        assert regular.status == "PENDING"

    @pytest.mark.asyncio
    async def test_retry_strategy_self_only_resets_self(self, db_session):
        """A step with retry_strategy='self' only resets itself (not parents)."""
        wid = _create_workflow(db_session)

        _create_step(
            db_session, wid, "parent_step",
            step_order=1, depends_on=[], status="COMPLETED",
            output_data='{"data": "preserved"}',
        )
        _create_step(
            db_session, wid, "gate_with_self",
            step_order=2, depends_on=["parent_step"],
            status="FAILED", retry_strategy="self",
        )

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal), \
             patch("app.services.workflow_engine.start_workflow", new_callable=AsyncMock):
            await retry_workflow(wid)

        db_session.expire_all()

        parent = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "parent_step",
            WorkflowStep.workflow_run_id == wid,
        ).first()
        gate = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "gate_with_self",
            WorkflowStep.workflow_run_id == wid,
        ).first()

        # Gate reset to PENDING
        assert gate.status == "PENDING"

        # Parent should remain COMPLETED with data intact
        assert parent.status == "COMPLETED"
        assert parent.output_data == '{"data": "preserved"}'

    @pytest.mark.asyncio
    async def test_retry_no_retry_strategy_only_resets_self(self, db_session):
        """A step with NULL retry_strategy only resets itself (backward compat)."""
        wid = _create_workflow(db_session)

        _create_step(
            db_session, wid, "parent_step",
            step_order=1, depends_on=[], status="COMPLETED",
            output_data='{"data": "kept"}',
        )
        _create_step(
            db_session, wid, "failed_step",
            step_order=2, depends_on=["parent_step"],
            status="FAILED",
            # retry_strategy is None (NULL) -- backward compat default
        )

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal), \
             patch("app.services.workflow_engine.start_workflow", new_callable=AsyncMock):
            await retry_workflow(wid)

        db_session.expire_all()

        parent = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "parent_step",
            WorkflowStep.workflow_run_id == wid,
        ).first()
        failed = db_session.query(WorkflowStep).filter(
            WorkflowStep.step_name == "failed_step",
            WorkflowStep.workflow_run_id == wid,
        ).first()

        assert failed.status == "PENDING"
        assert parent.status == "COMPLETED"
        assert parent.output_data == '{"data": "kept"}'

    @pytest.mark.asyncio
    async def test_retry_strategy_persisted_from_step_def(self, db_session):
        """Verify IST_WORKFLOW_STEPS gate entries have retry_strategy and
        it is stored in the DB when steps are created."""
        from app.routers.ist import IST_WORKFLOW_STEPS

        wid = _create_workflow(db_session, status="PENDING")

        # Simulate step creation (same logic as create_screen)
        for step_def in IST_WORKFLOW_STEPS:
            step = WorkflowStep(
                workflow_run_id=wid,
                step_name=step_def["step_name"],
                phase=step_def["phase"],
                phase_name=step_def["phase_name"],
                step_order=step_def["step_order"],
                status="PENDING",
                depends_on=json.dumps(step_def.get("depends_on", [])),
                model_tier=step_def.get("model", "opus"),
                retry_strategy=step_def.get("retry_strategy"),
            )
            db_session.add(step)
        db_session.commit()

        # Verify the gate steps have retry_strategy="with_parent" in DB
        gate_names = [
            "content_sufficiency_gate",
            "research_sufficiency_gate",
            "screen_coherence_gate",
        ]
        for gate_name in gate_names:
            step = db_session.query(WorkflowStep).filter(
                WorkflowStep.workflow_run_id == wid,
                WorkflowStep.step_name == gate_name,
            ).first()
            assert step is not None, f"Gate step {gate_name} not found"
            assert step.retry_strategy == "with_parent", (
                f"Gate step {gate_name} should have retry_strategy='with_parent', "
                f"got {step.retry_strategy!r}"
            )

        # Verify non-gate steps have retry_strategy=None
        non_gate = db_session.query(WorkflowStep).filter(
            WorkflowStep.workflow_run_id == wid,
            WorkflowStep.step_name == "content_extraction",
        ).first()
        assert non_gate.retry_strategy is None


class TestSmartRetrySSE:
    """Tests for SSE event emission during smart retry."""

    @pytest.mark.asyncio
    async def test_smart_retry_emits_sse_event(self, db_session):
        """When parent steps are reset, a smart_retry SSE event is emitted."""
        wid = _create_workflow(db_session)

        _create_step(
            db_session, wid, "report_generation",
            step_order=1, depends_on=[], status="COMPLETED",
            output_data='{"report": "data"}',
        )
        _create_step(
            db_session, wid, "screen_coherence_gate",
            step_order=2, depends_on=["report_generation"],
            status="FAILED", retry_strategy="with_parent",
        )

        sse_calls = []

        async def capture_sse(wf_id, event_type, data):
            sse_calls.append((wf_id, event_type, data))

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal), \
             patch("app.services.workflow_engine.start_workflow", new_callable=AsyncMock), \
             patch("app.services.workflow_engine.emit_sse_event", side_effect=capture_sse):
            await retry_workflow(wid)

        # Should have emitted exactly one smart_retry event
        smart_retry_events = [
            (wf_id, et, d) for wf_id, et, d in sse_calls if et == "smart_retry"
        ]
        assert len(smart_retry_events) == 1

        _, _, data = smart_retry_events[0]
        assert data["workflowId"] == wid
        assert "report_generation" in data["regeneratingSteps"]
        assert "screen_coherence_gate" in data["failedSteps"]

    @pytest.mark.asyncio
    async def test_no_sse_event_for_self_retry(self, db_session):
        """No smart_retry SSE event when retry_strategy is not 'with_parent'."""
        wid = _create_workflow(db_session)

        _create_step(
            db_session, wid, "parent_step",
            step_order=1, depends_on=[], status="COMPLETED",
        )
        _create_step(
            db_session, wid, "failed_step",
            step_order=2, depends_on=["parent_step"],
            status="FAILED", retry_strategy=None,
        )

        sse_calls = []

        async def capture_sse(wf_id, event_type, data):
            sse_calls.append((wf_id, event_type, data))

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal), \
             patch("app.services.workflow_engine.start_workflow", new_callable=AsyncMock), \
             patch("app.services.workflow_engine.emit_sse_event", side_effect=capture_sse):
            await retry_workflow(wid)

        smart_retry_events = [
            (wf_id, et, d) for wf_id, et, d in sse_calls if et == "smart_retry"
        ]
        assert len(smart_retry_events) == 0
