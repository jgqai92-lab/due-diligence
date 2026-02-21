"""Workflow engine endpoints — create, list, advance, pause, cancel, stream."""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workflow import WorkflowRun, WorkflowStep
from app.schemas.workflow import (
    WorkflowAdvanceRequest,
    WorkflowAdvanceResponse,
    WorkflowCreate,
    WorkflowDetailResponse,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowStepResponse,
)
from app.services.workflow_engine import (
    cancel_workflow,
    get_active_workflow_count,
    pause_workflow,
    retry_workflow,
    sse_event_generator,
    start_workflow,
    subscribe_sse,
)

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# INV-BE-01: Every router MUST use /api/ prefix
router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def _error(code: str, message: str) -> dict:
    """Build a standard error detail dict (INV-SE-01)."""
    return {"error": {"code": code, "message": message}}


def _build_workflow_response(run: WorkflowRun) -> dict:
    """Build a WorkflowResponse-compatible dict from a WorkflowRun ORM object."""
    steps = run.steps or []
    completed_count = sum(1 for s in steps if s.status == "COMPLETED")
    total_count = len(steps)
    config_parsed = None
    if run.config:
        try:
            config_parsed = json.loads(run.config)
        except (json.JSONDecodeError, TypeError):
            config_parsed = None

    return {
        "id": run.id,
        "workflowType": run.workflow_type,
        "name": run.name,
        "status": run.status,
        "currentPhase": run.current_phase,
        "currentPhaseName": run.current_phase_name,
        "config": config_parsed,
        "autoAdvance": bool(run.auto_advance),
        "stepsCompleted": completed_count,
        "stepsTotal": total_count,
        "createdAt": run.created_at.isoformat() if run.created_at else None,
        "updatedAt": run.updated_at.isoformat() if run.updated_at else None,
    }


def _build_detail_response(run: WorkflowRun) -> dict:
    """Build a WorkflowDetailResponse-compatible dict with step details."""
    base = _build_workflow_response(run)
    base["errorMessage"] = run.error_message
    base["startedAt"] = run.started_at.isoformat() if run.started_at else None
    base["completedAt"] = run.completed_at.isoformat() if run.completed_at else None
    base["steps"] = [
        {
            "id": s.id,
            "stepName": s.step_name,
            "phase": s.phase,
            "phaseName": s.phase_name,
            "status": s.status,
            "startedAt": s.started_at.isoformat() if s.started_at else None,
            "completedAt": s.completed_at.isoformat() if s.completed_at else None,
            "durationMs": s.duration_ms,
            "errorMessage": s.error_message,
        }
        for s in sorted(run.steps or [], key=lambda s: s.step_order)
    ]
    return base


# ── GET /api/workflows — List workflows ──────────────────────────────────────

@router.get("")
def list_workflows(
    workflow_type: Optional[str] = Query(
        default=None,
        alias="workflowType",
        description="Filter by type: IST, HFRT, IST_SYNTHESIS, or IST_REFRESH",
    ),
    status: Optional[str] = Query(
        default=None, description="Filter by status"
    ),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """List workflow runs with optional filters and pagination."""
    query = db.query(WorkflowRun)

    if workflow_type:
        allowed_types = ("IST", "HFRT", "IST_SYNTHESIS", "IST_REFRESH")
        if workflow_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=_error(
                    "INVALID_FILTER",
                    f"workflowType must be one of {allowed_types}",
                ),
            )
        query = query.filter(WorkflowRun.workflow_type == workflow_type)

    valid_statuses = (
        "PENDING", "RUNNING", "PAUSED", "COMPLETED",
        "FAILED", "CANCELLED", "CANCELLING", "RETRYING",
    )
    if status:
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=_error(
                    "INVALID_FILTER",
                    f"status must be one of {valid_statuses}",
                ),
            )
        query = query.filter(WorkflowRun.status == status)

    total = query.count()
    runs = (
        query.order_by(WorkflowRun.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "workflows": [_build_workflow_response(r) for r in runs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ── POST /api/workflows — Create workflow ────────────────────────────────────

@router.post("", status_code=201)
@limiter.limit("5/hour")
def create_workflow(
    request: Request,
    data: WorkflowCreate,
    db: Session = Depends(get_db),
):
    """Create a new workflow run.

    Rate limited to 5 creations per hour per client.
    """
    # Security: enforce global active workflow limit
    active_count = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.status.in_(["PENDING", "RUNNING", "PAUSED"]))
        .count()
    )
    if active_count >= 10:
        raise HTTPException(
            status_code=429,
            detail=_error(
                "TOO_MANY_WORKFLOWS",
                "Maximum of 10 active workflows reached. "
                "Complete or cancel existing workflows first.",
            ),
        )

    run = WorkflowRun(
        workflow_type=data.workflow_type,
        name=data.name,
        status="PENDING",
        current_phase=0,
        config=json.dumps(data.config) if data.config else None,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return _build_workflow_response(run)


# ── GET /api/workflows/{id} — Get workflow detail ────────────────────────────

@router.get("/{workflow_id}")
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Get a single workflow run with all step details."""
    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()
    if not run:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "WORKFLOW_NOT_FOUND",
                f"No workflow with id {workflow_id}",
            ),
        )
    return _build_detail_response(run)


# ── POST /api/workflows/{id}/advance — Start or resume workflow ──────────────

@router.post("/{workflow_id}/advance", status_code=202)
async def advance_workflow(
    workflow_id: int,
    body: Optional[WorkflowAdvanceRequest] = None,
    db: Session = Depends(get_db),
):
    """Start a PENDING workflow or resume a PAUSED workflow.

    Returns 202 Accepted — execution happens in the background.
    """
    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()
    if not run:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "WORKFLOW_NOT_FOUND",
                f"No workflow with id {workflow_id}",
            ),
        )

    if run.status not in ("PENDING", "PAUSED"):
        raise HTTPException(
            status_code=409,
            detail=_error(
                "INVALID_STATE",
                f"Cannot advance workflow in {run.status} state. "
                "Only PENDING or PAUSED workflows can be advanced.",
            ),
        )

    # Determine next phase
    if run.status == "PAUSED":
        # Find the next pending step's phase
        next_step = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == workflow_id)
            .filter(WorkflowStep.status == "PENDING")
            .order_by(WorkflowStep.step_order)
            .first()
        )
        advancing_to = next_step.phase if next_step else run.current_phase + 1
    else:
        # PENDING — starting from phase 1 (or 0)
        advancing_to = 1

    try:
        await start_workflow(workflow_id)
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=_error("WORKFLOW_START_FAILED", str(e)[:500]),
        )

    message = (
        f"Workflow resumed, advancing to phase {advancing_to}"
        if run.status == "PAUSED"
        else "Workflow started"
    )

    return {
        "id": workflow_id,
        "status": "RUNNING",
        "advancingToPhase": advancing_to,
        "message": message,
    }


# ── POST /api/workflows/{id}/pause — Pause workflow ─────────────────────────

@router.post("/{workflow_id}/pause")
async def pause_workflow_endpoint(
    workflow_id: int, db: Session = Depends(get_db)
):
    """Pause a running workflow after the current step completes."""
    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()
    if not run:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "WORKFLOW_NOT_FOUND",
                f"No workflow with id {workflow_id}",
            ),
        )

    if run.status != "RUNNING":
        raise HTTPException(
            status_code=409,
            detail=_error(
                "INVALID_STATE",
                f"Cannot pause workflow in {run.status} state. "
                "Only RUNNING workflows can be paused.",
            ),
        )

    await pause_workflow(workflow_id)
    return {"id": workflow_id, "status": "PAUSED", "message": "Workflow pausing after current step"}


# ── POST /api/workflows/{id}/cancel — Cancel workflow ────────────────────────

@router.post("/{workflow_id}/cancel")
async def cancel_workflow_endpoint(
    workflow_id: int, db: Session = Depends(get_db)
):
    """Cancel a workflow run."""
    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()
    if not run:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "WORKFLOW_NOT_FOUND",
                f"No workflow with id {workflow_id}",
            ),
        )

    if run.status in ("COMPLETED", "CANCELLED", "FAILED"):
        raise HTTPException(
            status_code=409,
            detail=_error(
                "INVALID_STATE",
                f"Cannot cancel workflow in {run.status} state.",
            ),
        )

    await cancel_workflow(workflow_id)
    return {"id": workflow_id, "status": "CANCELLED", "message": "Workflow cancelled"}


# ── POST /api/workflows/{id}/retry — Retry failed workflow ──────────────────

@router.post("/{workflow_id}/retry", status_code=202)
async def retry_workflow_endpoint(
    workflow_id: int, db: Session = Depends(get_db)
):
    """Retry a failed workflow from the failed step.

    Resets the failed step to PENDING, preserving all completed steps
    and their outputs. Returns 202 Accepted — execution resumes in the background.
    """
    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()
    if not run:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "WORKFLOW_NOT_FOUND",
                f"No workflow with id {workflow_id}",
            ),
        )

    if run.status != "FAILED":
        raise HTTPException(
            status_code=409,
            detail=_error(
                "INVALID_STATE",
                f"Cannot retry workflow in {run.status} state. "
                "Only FAILED workflows can be retried.",
            ),
        )

    # Find which step failed for the response message
    failed_step = (
        db.query(WorkflowStep)
        .filter(WorkflowStep.workflow_run_id == workflow_id)
        .filter(WorkflowStep.status == "FAILED")
        .order_by(WorkflowStep.step_order)
        .first()
    )
    retry_from = failed_step.step_name if failed_step else "unknown"

    try:
        await retry_workflow(workflow_id)
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=_error("RETRY_FAILED", str(e)[:500]),
        )

    return {
        "id": workflow_id,
        "status": "RUNNING",
        "retryFromStep": retry_from,
        "message": f"Workflow retrying from step: {retry_from}",
    }


# ── PATCH /api/workflows/{id}/auto-advance — Toggle auto-advance ─────────────

@router.patch("/{workflow_id}/auto-advance")
def toggle_auto_advance(
    workflow_id: int,
    enabled: bool = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Toggle auto-advance mode for a workflow run.

    When enabled, the workflow will automatically proceed to the next phase
    after all steps in the current phase complete, without waiting for user
    approval. Quality gates still halt the pipeline on failure.
    """
    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()
    if not run:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "WORKFLOW_NOT_FOUND",
                f"No workflow with id {workflow_id}",
            ),
        )

    if run.status in ("COMPLETED", "CANCELLED", "FAILED"):
        raise HTTPException(
            status_code=409,
            detail=_error(
                "INVALID_STATE",
                f"Cannot toggle auto-advance for workflow in {run.status} state.",
            ),
        )

    run.auto_advance = enabled
    run.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "id": workflow_id,
        "autoAdvance": run.auto_advance,
        "message": f"Auto-advance {'enabled' if enabled else 'disabled'}",
    }


# ── GET /api/workflows/{id}/stream — SSE stream ─────────────────────────────

@router.get("/{workflow_id}/stream")
async def stream_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Stream workflow events via Server-Sent Events.

    Sends:
    - catch_up: initial state snapshot on connect
    - heartbeat: every 15 seconds if no events
    - step_started, step_complete, step_failed: per-step events
    - checkpoint_reached: phase boundary pause
    - workflow_started, workflow_paused, workflow_complete, workflow_failed, workflow_cancelled
    """
    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()
    if not run:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "WORKFLOW_NOT_FOUND",
                f"No workflow with id {workflow_id}",
            ),
        )

    # Security: SSE connection limit is enforced inside subscribe_sse
    # but we check here to return a proper HTTP error
    from app.services.workflow_engine import _sse_queues, MAX_SSE_CONNECTIONS_PER_WORKFLOW
    current_connections = len(_sse_queues.get(workflow_id, []))
    if current_connections >= MAX_SSE_CONNECTIONS_PER_WORKFLOW:
        raise HTTPException(
            status_code=429,
            detail=_error(
                "TOO_MANY_CONNECTIONS",
                f"Maximum SSE connections ({MAX_SSE_CONNECTIONS_PER_WORKFLOW}) "
                f"reached for this workflow.",
            ),
        )

    return StreamingResponse(
        sse_event_generator(workflow_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
