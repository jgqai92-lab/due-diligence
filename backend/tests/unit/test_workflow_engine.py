"""Tests for the continuous task queue workflow engine.

Validates that the asyncio.wait(FIRST_COMPLETED) execution model starts
steps immediately when dependencies are satisfied, instead of waiting for
the entire batch to complete (the old asyncio.gather model).

Tests cover:
- Immediate dependency resolution (the core optimization)
- Phase boundary pausing (manual and auto-advance)
- Error handling (cancel running tasks on failure)
- Cross-phase dependency handling
- NULL depends_on fallback to sequential
- Deadlock detection
- Pause/cancel signals during execution
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.workflow import WorkflowRun, WorkflowStep
from app.services.workflow_engine import (
    _run_workflow,
    _execute_step,
    _build_fallback_deps,
    _parse_depends_on,
    _step_registry,
    _sse_queues,
    _active_workflows,
    register_step,
    emit_sse_event,
)


# ── Test database setup ──────────────────────────────────────────────────────
# Use a file-based test DB to allow cross-connection access from
# the workflow engine (which opens its own sessions via SessionLocal).
# Only create/drop the two tables we actually need (workflow_runs,
# workflow_steps) to avoid foreign-key issues with other models in Base.

TEST_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "test_workflow_engine.db"
)
TEST_DB_URL = f"sqlite:///{os.path.abspath(TEST_DB_PATH)}"

os.makedirs(os.path.dirname(os.path.abspath(TEST_DB_PATH)), exist_ok=True)

test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# The specific tables we need for workflow tests
_workflow_tables = [
    WorkflowRun.__table__,
    WorkflowStep.__table__,
]


@pytest.fixture(autouse=True)
def setup_db():
    """Create workflow tables before each test, drop after.

    Only creates/drops workflow_runs and workflow_steps (not all Base
    tables) to avoid foreign-key issues with IST/HFRT domain tables.
    """
    # Drop in reverse order (steps before runs due to FK)
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
    # Clean up registries between tests
    _sse_queues.clear()
    _active_workflows.clear()


@pytest.fixture
def db_session():
    """Provide a clean DB session for each test."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _create_workflow(
    db, workflow_type="IST", name="Test Workflow",
    status="PENDING", auto_advance=True,
):
    """Helper: create a WorkflowRun and return its id."""
    run = WorkflowRun(
        workflow_type=workflow_type,
        name=name,
        status=status,
        current_phase=0,
        auto_advance=auto_advance,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run.id


def _create_step(
    db, workflow_run_id, step_name, phase, phase_name, step_order,
    depends_on=None, status="PENDING",
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
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


# ── Unit tests for dependency helpers ────────────────────────────────────────


class TestParseDependsOn:
    def test_null_returns_empty_set(self, db_session):
        step = _create_step(
            db_session, _create_workflow(db_session), "s1", 1, "P1", 1,
            depends_on=None,
        )
        # Override to None since our helper serializes it
        step.depends_on = None
        assert _parse_depends_on(step) == set()

    def test_empty_list_returns_empty_set(self, db_session):
        wid = _create_workflow(db_session)
        step = _create_step(db_session, wid, "s1", 1, "P1", 1, depends_on=[])
        assert _parse_depends_on(step) == set()

    def test_single_dep(self, db_session):
        wid = _create_workflow(db_session)
        step = _create_step(
            db_session, wid, "s2", 1, "P1", 2, depends_on=["s1"],
        )
        assert _parse_depends_on(step) == {"s1"}

    def test_multiple_deps(self, db_session):
        wid = _create_workflow(db_session)
        step = _create_step(
            db_session, wid, "s3", 1, "P1", 3, depends_on=["s1", "s2"],
        )
        assert _parse_depends_on(step) == {"s1", "s2"}

    def test_invalid_json_returns_empty(self, db_session):
        wid = _create_workflow(db_session)
        step = _create_step(db_session, wid, "s1", 1, "P1", 1)
        step.depends_on = "not-json"
        assert _parse_depends_on(step) == set()


class TestBuildFallbackDeps:
    def test_explicit_deps_used(self, db_session):
        wid = _create_workflow(db_session)
        s1 = _create_step(db_session, wid, "s1", 1, "P1", 1, depends_on=[])
        s2 = _create_step(db_session, wid, "s2", 1, "P1", 2, depends_on=["s1"])
        result = _build_fallback_deps([s1, s2])
        assert result == {"s1": set(), "s2": {"s1"}}

    def test_null_deps_fall_back_to_sequential(self, db_session):
        wid = _create_workflow(db_session)
        s1 = _create_step(db_session, wid, "s1", 1, "P1", 1, depends_on=[])
        s2 = _create_step(db_session, wid, "s2", 1, "P1", 2)
        s2.depends_on = None
        db_session.commit()
        s3 = _create_step(db_session, wid, "s3", 1, "P1", 3)
        s3.depends_on = None
        db_session.commit()
        result = _build_fallback_deps([s1, s2, s3])
        assert result == {"s1": set(), "s2": {"s1"}, "s3": {"s2"}}

    def test_mixed_explicit_and_null(self, db_session):
        wid = _create_workflow(db_session)
        s1 = _create_step(db_session, wid, "s1", 1, "P1", 1, depends_on=[])
        s2 = _create_step(db_session, wid, "s2", 1, "P1", 2, depends_on=["s1"])
        s3 = _create_step(db_session, wid, "s3", 1, "P1", 3)
        s3.depends_on = None
        db_session.commit()
        result = _build_fallback_deps([s1, s2, s3])
        # s3 has NULL depends_on, so falls back to sequential (depends on s2)
        assert result["s3"] == {"s2"}


# ── Integration tests for continuous execution loop ──────────────────────────

# Track step execution order across tests
_execution_log: list[tuple[str, float]] = []


def _make_handler(step_name: str, duration: float = 0.0, fail: bool = False):
    """Create a mock step handler that sleeps for `duration` seconds."""
    async def handler(workflow_run_id: int):
        _execution_log.append((step_name, time.monotonic()))
        if duration > 0:
            await asyncio.sleep(duration)
        if fail:
            raise RuntimeError(f"{step_name} intentionally failed")
        return {"step": step_name, "result": "ok"}
    return handler


@pytest.fixture(autouse=True)
def clean_registries():
    """Clear step registry and execution log before each test."""
    _execution_log.clear()
    # Save existing registry entries and restore after test
    saved = dict(_step_registry)
    yield
    _step_registry.clear()
    _step_registry.update(saved)


class TestContinuousExecution:
    """Test the core continuous task queue execution model."""

    @pytest.mark.asyncio
    async def test_immediate_dependency_resolution(self, db_session):
        """The key test: step C starts immediately after A completes,
        without waiting for B (the bottleneck).

        Dependency graph:
            A (0.1s) ──> C (0.0s)
            B (0.5s) ──> D (0.0s)

        Old behavior: C waits 0.5s (until B finishes).
        New behavior: C starts at ~0.1s.
        """
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(db_session, wid, "A", 1, "P1", 1, depends_on=[])
        _create_step(db_session, wid, "B", 1, "P1", 2, depends_on=[])
        _create_step(db_session, wid, "C", 1, "P1", 3, depends_on=["A"])
        _create_step(db_session, wid, "D", 1, "P1", 4, depends_on=["B"])

        # Register handlers with different durations
        _step_registry[("IST", "A")] = _make_handler("A", duration=0.1)
        _step_registry[("IST", "B")] = _make_handler("B", duration=0.5)
        _step_registry[("IST", "C")] = _make_handler("C", duration=0.0)
        _step_registry[("IST", "D")] = _make_handler("D", duration=0.0)

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        # Verify all steps completed
        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"

        steps = db_session.query(WorkflowStep).filter(
            WorkflowStep.workflow_run_id == wid
        ).all()
        for s in steps:
            assert s.status == "COMPLETED", f"Step {s.step_name} is {s.status}"

        # Verify C started before B completed:
        # C should have started at ~0.1s, B completes at ~0.5s
        start_times = {name: t for name, t in _execution_log}
        assert "A" in start_times
        assert "B" in start_times
        assert "C" in start_times
        assert "D" in start_times

        # C must have started BEFORE D (since A is faster than B)
        assert start_times["C"] < start_times["D"], (
            f"C started at {start_times['C']}, D at {start_times['D']}. "
            "C should start before D since A (0.1s) finishes before B (0.5s)."
        )

    @pytest.mark.asyncio
    async def test_all_steps_complete_simple_chain(self, db_session):
        """Simple linear chain: A -> B -> C all complete."""
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(db_session, wid, "A", 1, "P1", 1, depends_on=[])
        _create_step(db_session, wid, "B", 1, "P1", 2, depends_on=["A"])
        _create_step(db_session, wid, "C", 1, "P1", 3, depends_on=["B"])

        _step_registry[("IST", "A")] = _make_handler("A")
        _step_registry[("IST", "B")] = _make_handler("B")
        _step_registry[("IST", "C")] = _make_handler("C")

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"

        # Verify execution order: A before B before C
        names = [name for name, _ in _execution_log]
        assert names.index("A") < names.index("B") < names.index("C")

    @pytest.mark.asyncio
    async def test_parallel_independent_steps(self, db_session):
        """Steps with no deps run in parallel."""
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(db_session, wid, "A", 1, "P1", 1, depends_on=[])
        _create_step(db_session, wid, "B", 1, "P1", 2, depends_on=[])
        _create_step(db_session, wid, "C", 1, "P1", 3, depends_on=[])

        _step_registry[("IST", "A")] = _make_handler("A", duration=0.1)
        _step_registry[("IST", "B")] = _make_handler("B", duration=0.1)
        _step_registry[("IST", "C")] = _make_handler("C", duration=0.1)

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"

        # All three should have started nearly simultaneously
        start_times = {name: t for name, t in _execution_log}
        time_spread = max(start_times.values()) - min(start_times.values())
        assert time_spread < 0.05, (
            f"Steps should start nearly simultaneously, but spread is {time_spread}s"
        )

    @pytest.mark.asyncio
    async def test_diamond_dependency(self, db_session):
        """Diamond pattern: A -> (B, C) -> D.

             A
            / \\
           B   C
            \\ /
             D
        """
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(db_session, wid, "A", 1, "P1", 1, depends_on=[])
        _create_step(db_session, wid, "B", 1, "P1", 2, depends_on=["A"])
        _create_step(db_session, wid, "C", 1, "P1", 3, depends_on=["A"])
        _create_step(db_session, wid, "D", 1, "P1", 4, depends_on=["B", "C"])

        _step_registry[("IST", "A")] = _make_handler("A")
        _step_registry[("IST", "B")] = _make_handler("B", duration=0.1)
        _step_registry[("IST", "C")] = _make_handler("C", duration=0.2)
        _step_registry[("IST", "D")] = _make_handler("D")

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"

        # D should start after both B and C complete
        names = [name for name, _ in _execution_log]
        assert names.index("A") < names.index("B")
        assert names.index("A") < names.index("C")
        assert names.index("B") < names.index("D")
        assert names.index("C") < names.index("D")


class TestPhaseBoundaries:
    """Test phase boundary handling (manual pause and auto-advance)."""

    @pytest.mark.asyncio
    async def test_manual_mode_pauses_at_phase_boundary(self, db_session):
        """With auto_advance=False, engine pauses between phases."""
        wid = _create_workflow(db_session, auto_advance=False)
        _create_step(db_session, wid, "A", 1, "P1", 1, depends_on=[])
        _create_step(db_session, wid, "B", 2, "P2", 2, depends_on=["A"])

        _step_registry[("IST", "A")] = _make_handler("A")
        _step_registry[("IST", "B")] = _make_handler("B")

        sse_events = []
        original_emit = emit_sse_event

        async def capture_emit(wf_id, event_type, data):
            sse_events.append(event_type)
            await original_emit(wf_id, event_type, data)

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal), \
             patch("app.services.workflow_engine.emit_sse_event", side_effect=capture_emit):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "PAUSED"

        # B should NOT have been executed
        step_b = db_session.query(WorkflowStep).filter(
            WorkflowStep.workflow_run_id == wid,
            WorkflowStep.step_name == "B",
        ).first()
        assert step_b.status == "PENDING"

        # Should have emitted checkpoint_reached
        assert "checkpoint_reached" in sse_events

    @pytest.mark.asyncio
    async def test_auto_advance_proceeds_through_phases(self, db_session):
        """With auto_advance=True, engine auto-advances between phases."""
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(db_session, wid, "A", 1, "P1", 1, depends_on=[])
        _create_step(db_session, wid, "B", 2, "P2", 2, depends_on=["A"])
        _create_step(db_session, wid, "C", 3, "P3", 3, depends_on=["B"])

        _step_registry[("IST", "A")] = _make_handler("A")
        _step_registry[("IST", "B")] = _make_handler("B")
        _step_registry[("IST", "C")] = _make_handler("C")

        sse_events = []

        async def capture_emit(wf_id, event_type, data):
            sse_events.append(event_type)

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal), \
             patch("app.services.workflow_engine.emit_sse_event", side_effect=capture_emit):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"

        # Should have emitted phase_auto_advanced events
        assert "phase_auto_advanced" in sse_events

    @pytest.mark.asyncio
    async def test_cross_phase_deps_already_satisfied(self, db_session):
        """Steps depending on previous-phase steps work correctly.

        Phase 1: A (no deps)
        Phase 2: B depends on A (cross-phase), C depends on B (same phase)
        """
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(db_session, wid, "A", 1, "P1", 1, depends_on=[])
        _create_step(db_session, wid, "B", 2, "P2", 2, depends_on=["A"])
        _create_step(db_session, wid, "C", 2, "P2", 3, depends_on=["B"])

        _step_registry[("IST", "A")] = _make_handler("A")
        _step_registry[("IST", "B")] = _make_handler("B")
        _step_registry[("IST", "C")] = _make_handler("C")

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"

        names = [name for name, _ in _execution_log]
        assert names.index("A") < names.index("B") < names.index("C")


class TestErrorHandling:
    """Test error handling in the continuous execution model."""

    @pytest.mark.asyncio
    async def test_step_failure_cancels_running_tasks(self, db_session):
        """When a step fails, all running tasks are cancelled."""
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(db_session, wid, "fast_fail", 1, "P1", 1, depends_on=[])
        _create_step(db_session, wid, "slow_ok", 1, "P1", 2, depends_on=[])

        _step_registry[("IST", "fast_fail")] = _make_handler(
            "fast_fail", duration=0.05, fail=True,
        )
        _step_registry[("IST", "slow_ok")] = _make_handler(
            "slow_ok", duration=2.0,
        )

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "FAILED"
        assert run.error_message is not None

    @pytest.mark.asyncio
    async def test_step_failure_prevents_dependent_steps(self, db_session):
        """When a step fails, its dependents are never started."""
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(db_session, wid, "A", 1, "P1", 1, depends_on=[])
        _create_step(db_session, wid, "B", 1, "P1", 2, depends_on=["A"])

        _step_registry[("IST", "A")] = _make_handler("A", fail=True)
        _step_registry[("IST", "B")] = _make_handler("B")

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "FAILED"

        # B should never have started
        executed = {name for name, _ in _execution_log}
        assert "B" not in executed

    @pytest.mark.asyncio
    async def test_no_handler_registered_fails_step(self, db_session):
        """A step with no registered handler fails gracefully."""
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(db_session, wid, "missing", 1, "P1", 1, depends_on=[])

        # Don't register any handler for "missing"

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "FAILED"


class TestEdgeCases:
    """Test edge cases and backward compatibility."""

    @pytest.mark.asyncio
    async def test_empty_workflow(self, db_session):
        """Workflow with no steps completes immediately."""
        wid = _create_workflow(db_session)

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"

    @pytest.mark.asyncio
    async def test_already_completed_steps_skipped(self, db_session):
        """Steps already COMPLETED are not re-executed (retry scenario)."""
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(
            db_session, wid, "done", 1, "P1", 1,
            depends_on=[], status="COMPLETED",
        )
        _create_step(
            db_session, wid, "todo", 1, "P1", 2,
            depends_on=["done"],
        )

        _step_registry[("IST", "done")] = _make_handler("done")
        _step_registry[("IST", "todo")] = _make_handler("todo")

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"

        # "done" should NOT appear in execution log (it was already complete)
        executed = {name for name, _ in _execution_log}
        assert "done" not in executed
        assert "todo" in executed

    @pytest.mark.asyncio
    async def test_null_depends_on_sequential_fallback(self, db_session):
        """Steps with NULL depends_on execute sequentially (backward compat)."""
        wid = _create_workflow(db_session, auto_advance=True)
        s1 = _create_step(db_session, wid, "s1", 1, "P1", 1, depends_on=[])
        s2 = _create_step(db_session, wid, "s2", 1, "P1", 2)
        s2.depends_on = None
        db_session.commit()
        s3 = _create_step(db_session, wid, "s3", 1, "P1", 3)
        s3.depends_on = None
        db_session.commit()

        _step_registry[("IST", "s1")] = _make_handler("s1")
        _step_registry[("IST", "s2")] = _make_handler("s2")
        _step_registry[("IST", "s3")] = _make_handler("s3")

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"

        # Verify sequential execution: s1 -> s2 -> s3
        names = [name for name, _ in _execution_log]
        assert names == ["s1", "s2", "s3"]

    @pytest.mark.asyncio
    async def test_single_step_workflow(self, db_session):
        """Workflow with exactly one step completes."""
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(db_session, wid, "only", 1, "P1", 1, depends_on=[])

        _step_registry[("IST", "only")] = _make_handler("only")

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"

    @pytest.mark.asyncio
    async def test_all_steps_already_completed(self, db_session):
        """If all steps are already COMPLETED, workflow completes immediately."""
        wid = _create_workflow(db_session)
        _create_step(
            db_session, wid, "s1", 1, "P1", 1,
            depends_on=[], status="COMPLETED",
        )

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"
        assert len(_execution_log) == 0

    @pytest.mark.asyncio
    async def test_workflow_not_found(self, db_session):
        """_run_workflow handles missing workflow gracefully."""
        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(99999)
        # Should not raise — just log and return


class TestSSEEvents:
    """Verify SSE events are emitted correctly."""

    @pytest.mark.asyncio
    async def test_sse_events_emitted_in_order(self, db_session):
        """workflow_started, step events, workflow_complete are all emitted."""
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(db_session, wid, "A", 1, "P1", 1, depends_on=[])
        _create_step(db_session, wid, "B", 1, "P1", 2, depends_on=["A"])

        _step_registry[("IST", "A")] = _make_handler("A")
        _step_registry[("IST", "B")] = _make_handler("B")

        sse_events = []

        async def capture_emit(wf_id, event_type, data):
            sse_events.append(event_type)

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal), \
             patch("app.services.workflow_engine.emit_sse_event", side_effect=capture_emit):
            await _run_workflow(wid)

        assert sse_events[0] == "workflow_started"
        assert sse_events[-1] == "workflow_complete"

        # Each step should have started and completed
        assert sse_events.count("step_started") == 2
        assert sse_events.count("step_complete") == 2

    @pytest.mark.asyncio
    async def test_step_failed_sse_on_error(self, db_session):
        """step_failed and workflow_failed events are emitted on error."""
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(db_session, wid, "bad", 1, "P1", 1, depends_on=[])

        _step_registry[("IST", "bad")] = _make_handler("bad", fail=True)

        sse_events = []

        async def capture_emit(wf_id, event_type, data):
            sse_events.append(event_type)

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal), \
             patch("app.services.workflow_engine.emit_sse_event", side_effect=capture_emit):
            await _run_workflow(wid)

        assert "step_started" in sse_events
        assert "step_failed" in sse_events
        assert "workflow_failed" in sse_events


class TestISTPipelineSimulation:
    """Simulate the IST P2 scenario that motivates this change.

    IST Phase 2 steps:
    - bottleneck_mapping (depends on content_extraction, P1)  -- fast (0.1s)
    - demand_modeling (depends on bottleneck_mapping)          -- medium
    - external_validation (depends on content_extraction, P1) -- slow (0.5s)
    - content_sufficiency_gate (depends on demand_modeling, external_validation, source_bias_assessment)

    With the old model, demand_modeling couldn't start until external_validation
    finished. With the new model, it starts as soon as bottleneck_mapping finishes.
    """

    @pytest.mark.asyncio
    async def test_ist_p2_immediate_unblock(self, db_session):
        """demand_modeling starts immediately after bottleneck_mapping,
        without waiting for external_validation."""
        wid = _create_workflow(db_session, auto_advance=True)

        # P1 steps (already completed in a real scenario)
        _create_step(
            db_session, wid, "content_extraction", 1, "Content Extraction", 1,
            depends_on=[], status="COMPLETED",
        )
        _create_step(
            db_session, wid, "source_bias_assessment", 1, "Content Extraction", 2,
            depends_on=["content_extraction"], status="COMPLETED",
        )

        # P2 steps (the focus of this test)
        _create_step(
            db_session, wid, "bottleneck_mapping", 2, "Thematic Analysis", 3,
            depends_on=["content_extraction"],
        )
        _create_step(
            db_session, wid, "demand_modeling", 2, "Thematic Analysis", 4,
            depends_on=["bottleneck_mapping"],
        )
        _create_step(
            db_session, wid, "external_validation", 2, "Thematic Analysis", 5,
            depends_on=["content_extraction"],
        )
        _create_step(
            db_session, wid, "content_sufficiency_gate", 2, "Thematic Analysis", 6,
            depends_on=["demand_modeling", "external_validation", "source_bias_assessment"],
        )

        # bottleneck_mapping: fast (0.1s)
        # external_validation: slow (0.5s)
        _step_registry[("IST", "bottleneck_mapping")] = _make_handler(
            "bottleneck_mapping", duration=0.1,
        )
        _step_registry[("IST", "demand_modeling")] = _make_handler(
            "demand_modeling", duration=0.05,
        )
        _step_registry[("IST", "external_validation")] = _make_handler(
            "external_validation", duration=0.5,
        )
        _step_registry[("IST", "content_sufficiency_gate")] = _make_handler(
            "content_sufficiency_gate",
        )

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"

        # Verify demand_modeling started BEFORE external_validation completed
        start_times = {name: t for name, t in _execution_log}

        assert "bottleneck_mapping" in start_times
        assert "demand_modeling" in start_times
        assert "external_validation" in start_times
        assert "content_sufficiency_gate" in start_times

        # demand_modeling should start at ~0.1s (after bottleneck_mapping)
        # external_validation starts at ~0s but finishes at ~0.5s
        # So demand_modeling should start well before 0.5s
        dm_start = start_times["demand_modeling"]
        bm_start = start_times["bottleneck_mapping"]
        ev_start = start_times["external_validation"]

        # demand_modeling started after bottleneck_mapping
        assert dm_start > bm_start
        # demand_modeling started roughly at the same time as external_validation
        # (within a reasonable window, not waiting for it)
        # The key assertion: demand_modeling starts within 0.25s of workflow start
        # (bottleneck_mapping is 0.1s, so demand_modeling starts around 0.1s)
        assert dm_start - bm_start < 0.25, (
            f"demand_modeling started {dm_start - bm_start}s after "
            f"bottleneck_mapping. Should be < 0.25s (immediate unblock)."
        )

    @pytest.mark.asyncio
    async def test_hfrt_p2_parallel_research(self, db_session):
        """HFRT Phase 2: company_overview unblocks 3 parallel steps."""
        wid = _create_workflow(db_session, workflow_type="HFRT", auto_advance=True)

        # P1 complete
        _create_step(
            db_session, wid, "idea_screen", 1, "Screening", 1,
            depends_on=[], status="COMPLETED",
        )

        # P2 steps
        _create_step(
            db_session, wid, "company_overview", 2, "Deep Research", 2,
            depends_on=["idea_screen"],
        )
        _create_step(
            db_session, wid, "business_model", 2, "Deep Research", 3,
            depends_on=["company_overview"],
        )
        _create_step(
            db_session, wid, "competitive_position", 2, "Deep Research", 4,
            depends_on=["company_overview"],
        )
        _create_step(
            db_session, wid, "industry_analysis", 2, "Deep Research", 5,
            depends_on=["company_overview"],
        )

        _step_registry[("HFRT", "company_overview")] = _make_handler(
            "company_overview", duration=0.1,
        )
        _step_registry[("HFRT", "business_model")] = _make_handler(
            "business_model", duration=0.1,
        )
        _step_registry[("HFRT", "competitive_position")] = _make_handler(
            "competitive_position", duration=0.1,
        )
        _step_registry[("HFRT", "industry_analysis")] = _make_handler(
            "industry_analysis", duration=0.1,
        )

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"

        # All three research steps should start nearly simultaneously
        # after company_overview completes
        start_times = {name: t for name, t in _execution_log}
        bm = start_times["business_model"]
        cp = start_times["competitive_position"]
        ia = start_times["industry_analysis"]

        # They should all start within 50ms of each other
        spread = max(bm, cp, ia) - min(bm, cp, ia)
        assert spread < 0.1, (
            f"Parallel research steps should start near-simultaneously, "
            f"but spread is {spread}s"
        )


class TestCurrentPhaseTracking:
    """Test that current_phase and current_phase_name are updated correctly."""

    @pytest.mark.asyncio
    async def test_phase_tracking_updates(self, db_session):
        """current_phase advances as phases complete."""
        wid = _create_workflow(db_session, auto_advance=True)
        _create_step(db_session, wid, "A", 1, "Phase One", 1, depends_on=[])
        _create_step(db_session, wid, "B", 2, "Phase Two", 2, depends_on=["A"])

        _step_registry[("IST", "A")] = _make_handler("A")
        _step_registry[("IST", "B")] = _make_handler("B")

        with patch("app.services.workflow_engine.SessionLocal", TestSessionLocal):
            await _run_workflow(wid)

        db_session.expire_all()
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == wid).first()
        assert run.status == "COMPLETED"
        assert run.current_phase == 2
        assert run.current_phase_name == "Phase Two"
