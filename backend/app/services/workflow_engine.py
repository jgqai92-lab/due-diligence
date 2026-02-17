"""Core workflow engine — background task orchestrator with SSE streaming.

Provides:
- Decorator-based step registration via @register_step
- Continuous dependency-resolution task queue (asyncio.wait FIRST_COMPLETED)
- asyncio.Queue-based SSE event broadcasting
- Phase boundary pausing for user approval (INV-WF-02)
- Per-step DB sessions (INV-WF-01)

Execution model: steps are started immediately when their dependencies are
satisfied, instead of waiting for an entire batch to complete.  This avoids
idle time when batch members have very different durations.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Callable, Optional

from app.database import SessionLocal
from app.models.workflow import WorkflowRun, WorkflowStep
from app.services.claude_client import (
    set_workflow_context,
    clear_workflow_context,
    TokenBudgetExceededError,
)

logger = logging.getLogger(__name__)

# ── In-memory registries ─────────────────────────────────────────────────────

# Active workflow asyncio tasks: workflow_id -> Task
_active_workflows: dict[int, asyncio.Task] = {}

# SSE subscriber queues: workflow_id -> list[Queue]
_sse_queues: dict[int, list[asyncio.Queue]] = {}

# Step handler registry: (workflow_type, step_name) -> async callable
_step_registry: dict[tuple[str, str], Callable] = {}

# Security: max concurrent SSE connections per workflow (SE-01)
MAX_SSE_CONNECTIONS_PER_WORKFLOW = 5

# Security: max active workflows globally
MAX_ACTIVE_WORKFLOWS = 10


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware UTC (handles SQLite round-trip)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ── Step registration decorator ──────────────────────────────────────────────

def register_step(workflow_type: str, step_name: str):
    """Decorator to register a workflow step handler.

    Usage:
        @register_step("IST", "fetch_content")
        async def handle_fetch_content(workflow_run_id: int) -> dict | None:
            ...
    """
    def decorator(func: Callable):
        _step_registry[(workflow_type, step_name)] = func
        return func
    return decorator


# ── SSE event broadcasting ───────────────────────────────────────────────────

async def emit_sse_event(workflow_id: int, event_type: str, data: dict):
    """Send an SSE event to all connected clients for this workflow."""
    event = {
        "type": event_type,
        **data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    queues = _sse_queues.get(workflow_id, [])
    for queue in queues:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(
                "SSE queue full for workflow %d — dropping event %s",
                workflow_id,
                event_type,
            )


def subscribe_sse(workflow_id: int) -> asyncio.Queue:
    """Subscribe to SSE events for a workflow. Returns a Queue to read from.

    Raises ValueError if the per-workflow connection limit is exceeded.
    """
    existing = _sse_queues.get(workflow_id, [])
    if len(existing) >= MAX_SSE_CONNECTIONS_PER_WORKFLOW:
        raise ValueError(
            f"Maximum SSE connections ({MAX_SSE_CONNECTIONS_PER_WORKFLOW}) "
            f"reached for workflow {workflow_id}"
        )
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _sse_queues.setdefault(workflow_id, []).append(queue)
    return queue


def unsubscribe_sse(workflow_id: int, queue: asyncio.Queue):
    """Unsubscribe from SSE events for a workflow."""
    queues = _sse_queues.get(workflow_id, [])
    if queue in queues:
        queues.remove(queue)
    if not queues:
        _sse_queues.pop(workflow_id, None)


# ── Workflow lifecycle ───────────────────────────────────────────────────────

def get_active_workflow_count() -> int:
    """Return the number of currently active workflow tasks."""
    return len(_active_workflows)


async def start_workflow(workflow_id: int):
    """Start executing a workflow in a background asyncio task.

    Raises ValueError if the workflow is already running or if the
    global active-workflow limit has been reached.
    """
    if workflow_id in _active_workflows:
        raise ValueError(f"Workflow {workflow_id} is already running")

    if len(_active_workflows) >= MAX_ACTIVE_WORKFLOWS:
        raise ValueError(
            f"Maximum active workflows ({MAX_ACTIVE_WORKFLOWS}) reached. "
            "Cancel or wait for existing workflows to complete."
        )

    task = asyncio.create_task(_run_workflow(workflow_id))
    _active_workflows[workflow_id] = task

    # Auto-cleanup when the task finishes
    def _cleanup(t: asyncio.Task):
        _active_workflows.pop(workflow_id, None)

    task.add_done_callback(_cleanup)


async def pause_workflow(workflow_id: int):
    """Signal a running workflow to pause after the current step completes."""
    db = SessionLocal()
    try:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()
        if run and run.status == "RUNNING":
            run.status = "PAUSED"
            run.updated_at = datetime.now(timezone.utc)
            db.commit()
            await emit_sse_event(
                workflow_id, "workflow_paused", {"workflowId": workflow_id}
            )
    finally:
        db.close()


async def retry_workflow(workflow_id: int):
    """Retry a failed workflow from the failed step.

    Resets the failed step to PENDING (preserving all completed steps),
    clears the workflow error, and restarts execution.

    Smart retry: gate steps with retry_strategy="with_parent" also reset
    their depends_on parent steps so they regenerate fresh data before
    the gate re-checks.  This prevents the infinite-retry loop where a
    gate keeps validating the same unchanged upstream output.
    """
    db = SessionLocal()
    try:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()
        if not run:
            raise ValueError(f"Workflow {workflow_id} not found")
        if run.status != "FAILED":
            raise ValueError(
                f"Cannot retry workflow in {run.status} state. "
                "Only FAILED workflows can be retried."
            )

        # Reset any FAILED steps back to PENDING
        failed_steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == workflow_id)
            .filter(WorkflowStep.status == "FAILED")
            .all()
        )

        # Capture failed step names before session closes (for SSE event)
        failed_step_names = [step.step_name for step in failed_steps]

        # Collect parent steps that need regeneration (smart retry)
        parent_steps_to_reset: set[str] = set()
        for step in failed_steps:
            if step.retry_strategy == "with_parent" and step.depends_on:
                try:
                    deps = json.loads(step.depends_on)
                    if isinstance(deps, list):
                        parent_steps_to_reset.update(deps)
                except (json.JSONDecodeError, TypeError):
                    pass

        # Reset the failed steps themselves
        for step in failed_steps:
            step.status = "PENDING"
            step.error_message = None
            step.started_at = None
            step.completed_at = None
            step.duration_ms = None

        # Reset parent steps that need regeneration
        if parent_steps_to_reset:
            parent_steps = (
                db.query(WorkflowStep)
                .filter(WorkflowStep.workflow_run_id == workflow_id)
                .filter(WorkflowStep.step_name.in_(parent_steps_to_reset))
                .all()
            )
            for step in parent_steps:
                step.status = "PENDING"
                step.error_message = None
                step.started_at = None
                step.completed_at = None
                step.duration_ms = None
                step.output_data = None  # Clear old output so fresh data is generated

            logger.info(
                "Workflow %d: smart retry — also resetting parent steps: %s",
                workflow_id, sorted(parent_steps_to_reset),
            )

        # Set workflow to RUNNING so _run_workflow picks it up
        run.status = "RUNNING"
        run.error_message = None
        run.updated_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()

    # Emit SSE event for smart retry before restarting
    if parent_steps_to_reset:
        await emit_sse_event(workflow_id, "smart_retry", {
            "workflowId": workflow_id,
            "regeneratingSteps": sorted(parent_steps_to_reset),
            "failedSteps": failed_step_names,
        })

    # Start the workflow — it will skip COMPLETED steps automatically
    await start_workflow(workflow_id)


async def cancel_workflow(workflow_id: int):
    """Cancel a workflow run and its background task."""
    db = SessionLocal()
    try:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()
        if run and run.status in ("RUNNING", "PAUSED", "PENDING"):
            run.status = "CANCELLED"
            run.updated_at = datetime.now(timezone.utc)
            db.commit()
            await emit_sse_event(
                workflow_id, "workflow_cancelled", {"workflowId": workflow_id}
            )
            # Cancel the asyncio task if it exists
            task = _active_workflows.get(workflow_id)
            if task and not task.done():
                task.cancel()
    finally:
        db.close()


# ── Dependency helpers ──────────────────────────────────────────────────────


def _parse_depends_on(step: WorkflowStep) -> set[str]:
    """Parse the depends_on JSON column into a set of step names.

    Returns an empty set if depends_on is NULL or unparseable.
    """
    if step.depends_on:
        try:
            deps = json.loads(step.depends_on)
            if isinstance(deps, list):
                return set(deps)
        except (json.JSONDecodeError, TypeError):
            pass
    return set()


def _build_fallback_deps(all_steps: list[WorkflowStep]) -> dict[str, set[str]]:
    """Build a fallback dependency map for steps with NULL depends_on.

    Steps without explicit depends_on are treated as depending on the
    previous step by step_order — preserving backward-compatible
    sequential execution for workflows created before migration 011.
    """
    sorted_steps = sorted(all_steps, key=lambda s: s.step_order)
    fallback: dict[str, set[str]] = {}
    prev_name: Optional[str] = None
    for step in sorted_steps:
        if step.depends_on is not None:
            # Has explicit deps (even if "[]" meaning no deps)
            fallback[step.step_name] = _parse_depends_on(step)
        else:
            # NULL depends_on — fall back to sequential by step_order
            if prev_name is not None:
                fallback[step.step_name] = {prev_name}
            else:
                fallback[step.step_name] = set()
        prev_name = step.step_name
    return fallback


# ── Core execution loop ─────────────────────────────────────────────────────

async def _run_workflow(workflow_id: int):
    """Execute workflow steps with continuous dependency resolution.

    Uses asyncio.wait(return_when=FIRST_COMPLETED) to start dependent
    steps immediately when their prerequisites finish, instead of the
    previous batch-gather model that waited for all concurrent steps
    to complete before checking for newly-ready steps.

    Phase boundary pausing (INV-WF-02) is preserved: the engine pauses
    before starting steps in a new phase until the user approves
    advancement (or auto-advances if enabled).
    """
    # Set token tracking context for this workflow (D-01, ATLAS-5)
    set_workflow_context(workflow_id)
    db = SessionLocal()
    try:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()
        if not run:
            logger.error("Workflow %d not found", workflow_id)
            return

        run.status = "RUNNING"
        run.started_at = run.started_at or datetime.now(timezone.utc)
        run.updated_at = datetime.now(timezone.utc)
        db.commit()

        await emit_sse_event(workflow_id, "workflow_started", {
            "workflowId": workflow_id,
            "workflowType": run.workflow_type,
        })

        # Load ALL steps (including COMPLETED) for dependency resolution
        all_steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == workflow_id)
            .order_by(WorkflowStep.step_order)
            .all()
        )

        if not all_steps:
            logger.warning("Workflow %d has no steps", workflow_id)
            run.current_phase = 0
            run.status = "COMPLETED"
            run.completed_at = datetime.now(timezone.utc)
            run.updated_at = datetime.now(timezone.utc)
            db.commit()
            await emit_sse_event(workflow_id, "workflow_complete", {
                "workflowId": workflow_id,
            })
            return

        # Build dependency map (handles NULL depends_on via fallback)
        dep_map = _build_fallback_deps(all_steps)

        # Track completed step names
        completed = {s.step_name for s in all_steps if s.status == "COMPLETED"}

        # Determine approved phase.
        # On first start: phase 1 is auto-approved (phase 0 -> 1 is free).
        # On resume from PAUSED: the first pending step's phase is approved.
        first_pending = next(
            (s for s in all_steps if s.status == "PENDING"), None
        )
        if not first_pending:
            # No pending steps — workflow is already complete
            max_phase = max(
                (s.phase for s in all_steps if s.status == "COMPLETED"),
                default=0,
            )
            run.current_phase = max_phase
            run.status = "COMPLETED"
            run.completed_at = datetime.now(timezone.utc)
            run.updated_at = datetime.now(timezone.utc)
            db.commit()
            await emit_sse_event(workflow_id, "workflow_complete", {
                "workflowId": workflow_id,
            })
            return

        approved_phase = first_pending.phase if first_pending.phase > 0 else 1

        # ── Continuous task queue execution loop ──────────────────────
        # Instead of batch-gather (which wastes time waiting for the
        # slowest step in each batch), this uses asyncio.wait with
        # FIRST_COMPLETED to start dependent steps immediately when
        # their prerequisites finish.
        #
        # Example savings: if step A (26s) and step B (92s) run in
        # parallel, and step C depends only on A, the old model makes
        # C wait 92s.  The continuous model starts C after 26s.

        # running: step_name -> (asyncio.Task, step_id)
        running: dict[str, tuple[asyncio.Task, int]] = {}
        failed_steps: set[str] = set()

        # Index steps by name for fast lookup
        step_by_name = {s.step_name: s for s in all_steps}

        def _get_ready_steps() -> list[WorkflowStep]:
            """Find PENDING steps whose deps are all completed and that
            aren't already running, failed, or outside the approved phase."""
            ready = []
            for s in all_steps:
                if s.step_name in completed or s.step_name in failed_steps:
                    continue
                if s.step_name in running:
                    continue
                if s.status != "PENDING":
                    continue
                deps = dep_map.get(s.step_name, set())
                if deps.issubset(completed):
                    ready.append(s)
            return ready

        async def _step_wrapper(step_name: str, step_id: int, step_phase: int):
            """Execute a step and return (step_name, success)."""
            try:
                await _execute_step(
                    workflow_id=workflow_id,
                    workflow_type=run.workflow_type,
                    step_id=step_id,
                    step_name=step_name,
                    step_phase=step_phase,
                )
                return (step_name, True)
            except Exception as e:
                logger.error(
                    "Workflow %d: step '%s' raised unhandled exception: %s",
                    workflow_id, step_name, e,
                )
                return (step_name, False)

        def _launch_step(step: WorkflowStep, reason: str):
            """Create an asyncio task for a step and register it."""
            task = asyncio.create_task(
                _step_wrapper(step.step_name, step.id, step.phase)
            )
            running[step.step_name] = (task, step.id)
            logger.info(
                "Workflow %d: started step '%s' (%s)",
                workflow_id, step.step_name, reason,
            )

        def _cancel_all_running():
            """Cancel all currently running asyncio tasks."""
            for name, (task, _sid) in running.items():
                if not task.done():
                    task.cancel()
                    logger.info(
                        "Workflow %d: cancelled running step '%s'",
                        workflow_id, name,
                    )

        # Outer loop handles phase boundary transitions.
        # Inner loop handles continuous dependency resolution within a phase.
        execution_aborted = False
        while not execution_aborted:
            # Check for pause/cancel signals
            db.refresh(run)
            if run.status in ("PAUSED", "CANCELLED", "CANCELLING"):
                break

            # Find all ready steps (deps satisfied, PENDING)
            ready = _get_ready_steps()

            if not ready and not running:
                # Check for pending steps that couldn't be resolved
                remaining = [s for s in all_steps if s.status == "PENDING"
                             and s.step_name not in failed_steps]
                if remaining:
                    logger.error(
                        "Workflow %d: no ready steps but %d pending — "
                        "possible dependency deadlock",
                        workflow_id, len(remaining),
                    )
                break  # All done or deadlocked

            # Phase boundary check: filter ready steps to approved phase
            ready_in_phase = [s for s in ready if s.phase <= approved_phase]

            if not ready_in_phase and not running:
                # All ready steps are in a future phase and nothing
                # is still running in the current phase
                next_phase = min(s.phase for s in ready)

                if run.auto_advance:
                    await emit_sse_event(workflow_id, "phase_auto_advanced", {
                        "phase": approved_phase,
                        "nextPhase": next_phase,
                    })
                    approved_phase = next_phase
                    continue  # Re-evaluate with new approved phase
                else:
                    # Manual mode: pause for user approval
                    run.status = "PAUSED"
                    run.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    await emit_sse_event(workflow_id, "checkpoint_reached", {
                        "phase": approved_phase,
                        "nextPhase": next_phase,
                        "requiresApproval": True,
                    })
                    break

            # Seed initial ready steps for this iteration
            for step in ready_in_phase:
                _launch_step(step, "batch seed")

            # ── Inner continuous resolution loop ──────────────────
            # Runs until no tasks are active.  After each task
            # completes, immediately checks for newly-unblocked steps.
            while running:
                # Check for pause/cancel signals before waiting
                db.refresh(run)
                if run.status in ("PAUSED", "CANCELLED", "CANCELLING"):
                    _cancel_all_running()
                    execution_aborted = True
                    break

                # Wait for ANY running task to complete
                tasks = [t for (t, _sid) in running.values()]
                done, _pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # Process completed tasks
                for finished_task in done:
                    try:
                        step_name, success = finished_task.result()
                    except asyncio.CancelledError:
                        # Find which step this task belonged to
                        step_name = None
                        for sn, (t, _sid) in list(running.items()):
                            if t is finished_task:
                                step_name = sn
                                break
                        if step_name:
                            del running[step_name]
                        continue

                    del running[step_name]

                    if success:
                        completed.add(step_name)
                    else:
                        failed_steps.add(step_name)

                # Refresh step statuses from the DB after completions
                db.expire_all()
                all_steps = (
                    db.query(WorkflowStep)
                    .filter(WorkflowStep.workflow_run_id == workflow_id)
                    .order_by(WorkflowStep.step_order)
                    .all()
                )
                step_by_name = {s.step_name: s for s in all_steps}

                # Also rebuild completed from DB (authoritative source)
                completed = {s.step_name for s in all_steps
                             if s.status == "COMPLETED"}

                # Check for failures (both from wrapper and from DB)
                db_failed = [s for s in all_steps if s.status == "FAILED"]
                if failed_steps or db_failed:
                    # Determine error message
                    failed_step_error = None
                    for s in db_failed:
                        failed_step_error = s.error_message
                        break
                    if not failed_step_error and failed_steps:
                        failed_step_error = (
                            f"Steps failed: {', '.join(sorted(failed_steps))}"
                        )

                    # Cancel all still-running tasks
                    _cancel_all_running()
                    # Wait briefly for cancellations to propagate
                    if running:
                        cancel_tasks = [t for (t, _) in running.values()]
                        await asyncio.gather(
                            *cancel_tasks, return_exceptions=True
                        )
                        running.clear()

                    db.refresh(run)
                    run.status = "FAILED"
                    run.error_message = (
                        failed_step_error or "Unknown error"
                    )[:1000]
                    run.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    await emit_sse_event(workflow_id, "workflow_failed", {
                        "workflowId": workflow_id,
                        "error": (
                            failed_step_error or "Unknown error"
                        )[:500],
                    })
                    return

                # Update current phase tracking
                max_completed_phase = max(
                    (s.phase for s in all_steps if s.status == "COMPLETED"),
                    default=0,
                )
                highest_phase_step = next(
                    (
                        s for s in reversed(all_steps)
                        if s.status == "COMPLETED"
                        and s.phase == max_completed_phase
                    ),
                    None,
                )
                db.refresh(run)
                run.current_phase = max_completed_phase
                if highest_phase_step:
                    run.current_phase_name = highest_phase_step.phase_name
                run.updated_at = datetime.now(timezone.utc)
                db.commit()

                # Check for newly unblocked steps (the key optimization)
                newly_ready = _get_ready_steps()
                newly_ready_in_phase = [
                    s for s in newly_ready if s.phase <= approved_phase
                ]
                for step in newly_ready_in_phase:
                    # Determine which dependency just unblocked this step
                    deps = dep_map.get(step.step_name, set())
                    # Find most-recently-completed dep for the log message
                    unblocked_by = ", ".join(sorted(deps)) if deps else "none"
                    _launch_step(
                        step,
                        f"unblocked by: {unblocked_by}",
                    )

                # If nothing is running and no newly-ready steps exist,
                # break to re-evaluate phase boundaries in the outer loop
                if not running:
                    break

        # ── After loop: check if workflow is complete ─────────────────
        db.refresh(run)
        if run.status == "RUNNING":
            remaining_pending = (
                db.query(WorkflowStep)
                .filter(WorkflowStep.workflow_run_id == workflow_id)
                .filter(WorkflowStep.status == "PENDING")
                .count()
            )
            if remaining_pending == 0:
                # Final phase update before marking complete
                final_steps = (
                    db.query(WorkflowStep)
                    .filter(WorkflowStep.workflow_run_id == workflow_id)
                    .filter(WorkflowStep.status == "COMPLETED")
                    .all()
                )
                if final_steps:
                    max_phase = max(s.phase for s in final_steps)
                    run.current_phase = max_phase
                run.status = "COMPLETED"
                run.completed_at = datetime.now(timezone.utc)
                run.updated_at = datetime.now(timezone.utc)
                db.commit()
                await emit_sse_event(workflow_id, "workflow_complete", {
                    "workflowId": workflow_id,
                })

    except asyncio.CancelledError:
        logger.info("Workflow %d cancelled via asyncio", workflow_id)
    except Exception as e:
        logger.error("Workflow %d failed: %s", workflow_id, e, exc_info=True)
        try:
            run = db.query(WorkflowRun).filter(
                WorkflowRun.id == workflow_id
            ).first()
            if run:
                run.status = "FAILED"
                # Use specific error code for token budget exceeded
                if isinstance(e, TokenBudgetExceededError):
                    run.error_message = "TOKEN_BUDGET_EXCEEDED"
                else:
                    run.error_message = str(e)[:1000]
                run.updated_at = datetime.now(timezone.utc)
                db.commit()
            error_code = (
                "TOKEN_BUDGET_EXCEEDED"
                if isinstance(e, TokenBudgetExceededError)
                else str(e)[:500]
            )
            await emit_sse_event(workflow_id, "workflow_failed", {
                "workflowId": workflow_id,
                "error": error_code,
            })
        except Exception:
            logger.error(
                "Failed to update workflow %d status after error",
                workflow_id,
                exc_info=True,
            )
    finally:
        clear_workflow_context(workflow_id)
        db.close()


async def _execute_step(
    workflow_id: int,
    workflow_type: str,
    step_id: int,
    step_name: str,
    step_phase: int,
):
    """Execute a single workflow step via its registered handler.

    Uses its own DB session for all status bookkeeping so that multiple
    steps can safely run in parallel without sharing a session.

    INV-WF-01: Step handlers use their own DB sessions (not this one).
    """
    step_db = SessionLocal()
    try:
        step = step_db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
        if not step:
            logger.error(
                "Workflow %d: step %d not found during execution", workflow_id, step_id
            )
            return

        step.status = "RUNNING"
        step.started_at = datetime.now(timezone.utc)
        step_db.commit()

        await emit_sse_event(workflow_id, "step_started", {
            "stepName": step_name,
            "phase": step_phase,
        })

        handler = _step_registry.get((workflow_type, step_name))
        if not handler:
            step.status = "FAILED"
            step.error_message = (
                f"No handler registered for {workflow_type}:{step_name}"
            )
            step.completed_at = datetime.now(timezone.utc)
            step_db.commit()
            await emit_sse_event(workflow_id, "step_failed", {
                "stepName": step_name,
                "phase": step_phase,
                "error": step.error_message,
            })
            return

        try:
            # Step handlers receive workflow_run_id and manage their own DB sessions
            result = await handler(workflow_id)

            step_db.refresh(step)
            step.status = "COMPLETED"
            step.output_data = json.dumps(result) if result else None
            step.completed_at = datetime.now(timezone.utc)
            if step.started_at:
                delta = step.completed_at - _ensure_utc(step.started_at)
                step.duration_ms = int(delta.total_seconds() * 1000)
            step_db.commit()

            await emit_sse_event(workflow_id, "step_complete", {
                "stepName": step_name,
                "phase": step_phase,
                "durationMs": step.duration_ms,
            })

        except Exception as e:
            logger.error("Step %s failed: %s", step_name, e, exc_info=True)
            step_db.refresh(step)
            step.status = "FAILED"
            step.error_message = str(e)[:1000]
            step.completed_at = datetime.now(timezone.utc)
            if step.started_at:
                delta = step.completed_at - _ensure_utc(step.started_at)
                step.duration_ms = int(delta.total_seconds() * 1000)
            step.retry_count += 1
            step_db.commit()

            await emit_sse_event(workflow_id, "step_failed", {
                "stepName": step_name,
                "phase": step_phase,
                "error": str(e)[:500],
            })
    finally:
        step_db.close()


# ── SSE event generator ─────────────────────────────────────────────────────

async def sse_event_generator(workflow_id: int) -> AsyncGenerator[str, None]:
    """Generate SSE events for a workflow. Used by the streaming endpoint.

    Sends a catch-up snapshot first, then streams live events.
    Sends heartbeats every 15 seconds to keep the connection alive.
    Terminates on workflow_complete, workflow_failed, or workflow_cancelled.
    """
    queue = subscribe_sse(workflow_id)
    try:
        # Send catch-up state so late joiners know the current status
        db = SessionLocal()
        try:
            run = db.query(WorkflowRun).filter(
                WorkflowRun.id == workflow_id
            ).first()
            if run:
                steps = (
                    db.query(WorkflowStep)
                    .filter(WorkflowStep.workflow_run_id == workflow_id)
                    .order_by(WorkflowStep.step_order)
                    .all()
                )
                catch_up = {
                    "type": "catch_up",
                    "workflowId": run.id,
                    "status": run.status,
                    "currentPhase": run.current_phase,
                    "steps": [
                        {
                            "stepName": s.step_name,
                            "phase": s.phase,
                            "status": s.status,
                            "durationMs": s.duration_ms,
                        }
                        for s in steps
                    ],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"event: catch_up\ndata: {json.dumps(catch_up)}\n\n"

                # If workflow is already in a terminal state, send synthetic
                # terminal event and close immediately — no point entering the
                # heartbeat loop since no new events will ever arrive.
                if run.status in ("COMPLETED", "FAILED", "CANCELLED"):
                    terminal_event = {
                        "type": f"workflow_{run.status.lower()}",
                        "workflowId": run.id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    yield f"event: {terminal_event['type']}\ndata: {json.dumps(terminal_event)}\n\n"
                    return
        finally:
            db.close()

        # Stream live events
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                event_type = event.get("type", "message")
                yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"

                # Stop streaming on terminal workflow events
                if event_type in (
                    "workflow_complete",
                    "workflow_failed",
                    "workflow_cancelled",
                ):
                    break
            except asyncio.TimeoutError:
                # Send heartbeat to keep the connection alive
                heartbeat = {
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"event: heartbeat\ndata: {json.dumps(heartbeat)}\n\n"
    finally:
        unsubscribe_sse(workflow_id, queue)
