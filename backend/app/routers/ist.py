"""IST (Investment Screening Team) endpoints -- screen creation, listing, claims,
bottlenecks, demand models, and validation.

All endpoints under /api/ist prefix (INV-BE-01: /api/ prefix).
Error format: {"error": {"code": "...", "message": "..."}} (INV-BE-02).
"""

import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.services.workflow_engine import cancel_workflow, start_workflow

from app.database import get_db
from app.models.ist import (
    ISTBottleneck,
    ISTCatalystCalendar,
    ISTClaim,
    ISTDemandModel,
    ISTDialecticReview,
    ISTEffectsChain,
    ISTEquityCandidate,
    ISTMasterScreen,
    ISTReport,
    ISTRotationStrategy,
    ISTScreen,
    ISTStressTest,
    ISTValidation,
)
from app.models.ist_refresh import ISTScreenRefresh
from app.models.workflow import WorkflowRun, WorkflowStep
from app.schemas.ist import (
    ISTClaimResponse,
    ISTClaimsListResponse,
    ISTScreenRefreshCreate,
    ISTScreenBriefUpdate,
    ISTScreenCreate,
    ISTScreenDetailResponse,
    ISTScreenListItem,
    ISTScreenListResponse,
    ISTScreenResponse,
    ScreeningBrief,
)
from app.services.ist.refresh import IST_REFRESH_WORKFLOW_STEPS

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# INV-BE-01: Every router MUST use /api/ prefix
router = APIRouter(prefix="/api/ist", tags=["ist"])


# ── IST workflow step definitions ───────────────────────────────────────────

IST_WORKFLOW_STEPS = [
    # Phase 1: Content Extraction
    {"step_name": "content_extraction", "phase": 1, "phase_name": "Content Extraction", "step_order": 1, "depends_on": [], "model": "opus"},
    {"step_name": "source_bias_assessment", "phase": 1, "phase_name": "Content Extraction", "step_order": 2, "depends_on": ["content_extraction"], "model": "sonnet"},
    # Phase 2: Thematic Analysis
    {"step_name": "bottleneck_mapping", "phase": 2, "phase_name": "Thematic Analysis", "step_order": 3, "depends_on": ["content_extraction"], "model": "opus"},
    {"step_name": "demand_modeling", "phase": 2, "phase_name": "Thematic Analysis", "step_order": 4, "depends_on": ["bottleneck_mapping"], "model": "opus"},
    {"step_name": "external_validation", "phase": 2, "phase_name": "Thematic Analysis", "step_order": 5, "depends_on": ["content_extraction"], "model": "opus"},
    {"step_name": "content_sufficiency_gate", "phase": 2, "phase_name": "Thematic Analysis", "step_order": 6, "depends_on": ["demand_modeling", "external_validation", "source_bias_assessment"], "model": "none", "retry_strategy": "with_parent"},
    # Phase 3: Equity Identification
    {"step_name": "equity_scanning", "phase": 3, "phase_name": "Equity Identification", "step_order": 7, "depends_on": ["content_sufficiency_gate"], "model": "opus"},
    {"step_name": "tier_classification", "phase": 3, "phase_name": "Equity Identification", "step_order": 8, "depends_on": ["equity_scanning"], "model": "sonnet"},
    {"step_name": "effects_analysis", "phase": 3, "phase_name": "Equity Identification", "step_order": 9, "depends_on": ["equity_scanning"], "model": "opus"},
    {"step_name": "invariant_check", "phase": 3, "phase_name": "Equity Identification", "step_order": 10, "depends_on": ["tier_classification", "effects_analysis"], "model": "none"},
    {"step_name": "research_sufficiency_gate", "phase": 3, "phase_name": "Equity Identification", "step_order": 11, "depends_on": ["invariant_check"], "model": "none", "retry_strategy": "with_parent"},
    # Phase 4: Dialectic Scrutiny
    {"step_name": "dialectic_optimist", "phase": 4, "phase_name": "Dialectic Scrutiny", "step_order": 12, "depends_on": ["research_sufficiency_gate"], "model": "opus"},
    {"step_name": "dialectic_pessimist", "phase": 4, "phase_name": "Dialectic Scrutiny", "step_order": 13, "depends_on": ["research_sufficiency_gate"], "model": "opus"},
    {"step_name": "dialectic_synthesis", "phase": 4, "phase_name": "Dialectic Scrutiny", "step_order": 14, "depends_on": ["dialectic_optimist", "dialectic_pessimist"], "model": "opus"},
    # Phase 5: Final Synthesis (INV-WF-01: ordering is immutable)
    {"step_name": "master_screen", "phase": 5, "phase_name": "Final Synthesis", "step_order": 15, "depends_on": ["dialectic_synthesis"], "model": "opus"},
    {"step_name": "rotation_strategy", "phase": 5, "phase_name": "Final Synthesis", "step_order": 16, "depends_on": ["master_screen"], "model": "sonnet"},
    {"step_name": "catalyst_calendar", "phase": 5, "phase_name": "Final Synthesis", "step_order": 17, "depends_on": ["master_screen"], "model": "sonnet"},
    {"step_name": "stress_tests", "phase": 5, "phase_name": "Final Synthesis", "step_order": 18, "depends_on": ["master_screen"], "model": "sonnet"},
    {"step_name": "report_generation", "phase": 5, "phase_name": "Final Synthesis", "step_order": 19, "depends_on": ["rotation_strategy", "catalyst_calendar", "stress_tests"], "model": "opus"},
    {"step_name": "screen_coherence_gate", "phase": 5, "phase_name": "Final Synthesis", "step_order": 20, "depends_on": ["report_generation"], "model": "none", "retry_strategy": "with_parent"},
    {"step_name": "screen_certification", "phase": 5, "phase_name": "Final Synthesis", "step_order": 21, "depends_on": ["screen_coherence_gate"], "model": "sonnet"},
    {"step_name": "hfrt_handoff_generation", "phase": 5, "phase_name": "Final Synthesis", "step_order": 22, "depends_on": ["screen_certification"], "model": "sonnet"},
]


def _error(code: str, message: str) -> dict:
    """Build a standard error detail dict (INV-BE-02)."""
    return {"error": {"code": code, "message": message}}


# ── POST /api/ist/screens — Create IST Screen ──────────────────────────────


@router.post("/screens", status_code=201)
@limiter.limit("5/hour")
def create_screen(
    request: Request,
    data: ISTScreenCreate,
    db: Session = Depends(get_db),
):
    """Create a new IST investment screen.

    Creates both an ISTScreen record and an associated WorkflowRun
    with all IST workflow steps pre-populated.

    Rate limited to 5 creations per hour.
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

    # 1. Create the WorkflowRun
    run = WorkflowRun(
        workflow_type="IST",
        name=data.name,
        status="PENDING",
        current_phase=0,
        auto_advance=data.auto_advance,
    )
    db.add(run)
    db.flush()  # Get run.id for FK references

    # 2. Build screening brief via Pydantic (INV-BE-06)
    brief = ScreeningBrief(
        hypothesis=data.hypothesis,
        content_type=data.content_type or "text",
        constraints=data.constraints,
        frameworks=data.frameworks,
    )

    # 3. Create the ISTScreen
    screen = ISTScreen(
        workflow_run_id=run.id,
        active_workflow_run_id=run.id,
        name=data.name,
        status="PENDING",
        content_type=data.content_type or "text",
        raw_content=data.content,
        screening_brief=brief.model_dump_json(),
    )
    db.add(screen)
    db.flush()  # Get screen.id

    # 4. Create all IST workflow steps
    for step_def in IST_WORKFLOW_STEPS:
        step = WorkflowStep(
            workflow_run_id=run.id,
            step_name=step_def["step_name"],
            phase=step_def["phase"],
            phase_name=step_def["phase_name"],
            step_order=step_def["step_order"],
            status="PENDING",
            depends_on=json.dumps(step_def.get("depends_on", [])),
            model_tier=step_def.get("model", "opus"),
            retry_strategy=step_def.get("retry_strategy"),
        )
        db.add(step)

    db.commit()
    db.refresh(screen)
    db.refresh(run)

    # Build response
    return {
        "id": screen.id,
        "workflowRunId": run.id,
        "activeWorkflowRunId": screen.active_workflow_run_id,
        "name": screen.name,
        "status": screen.status,
        "contentType": screen.content_type,
        "hypothesis": data.hypothesis,
        "refreshCount": screen.refresh_count,
        "createdAt": screen.created_at.isoformat() if screen.created_at else None,
    }


# ── DELETE /api/ist/screens/{screen_id} — Delete IST Screen ─────────────────


@router.delete("/screens/{screen_id}")
async def delete_screen(screen_id: int, db: Session = Depends(get_db)):
    """Delete an IST screen and its associated workflow run.

    If the workflow is active, cancels it first. CASCADE handles child records.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    # Cancel active workflow if running
    run = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.id == screen.workflow_run_id)
        .first()
    )
    if run and run.status in ("RUNNING", "PAUSED", "PENDING"):
        try:
            await cancel_workflow(run.id)
        except Exception:
            pass  # Best-effort cancel before delete

    # Cancel and delete any refresh workflow runs tied to this screen.
    refresh_run_ids = [
        row.workflow_run_id
        for row in db.query(ISTScreenRefresh.workflow_run_id)
        .filter(ISTScreenRefresh.screen_id == screen_id)
        .all()
    ]
    for refresh_run_id in refresh_run_ids:
        refresh_run = (
            db.query(WorkflowRun)
            .filter(WorkflowRun.id == refresh_run_id)
            .first()
        )
        if refresh_run and refresh_run.status in ("RUNNING", "PAUSED", "PENDING"):
            try:
                await cancel_workflow(refresh_run.id)
            except Exception:
                pass
        if refresh_run:
            db.query(WorkflowStep).filter(WorkflowStep.workflow_run_id == refresh_run.id).delete()
            db.delete(refresh_run)

    # Delete workflow steps, then workflow run, then screen (CASCADE handles IST child tables)
    if run:
        db.query(WorkflowStep).filter(WorkflowStep.workflow_run_id == run.id).delete()
        db.delete(run)
    db.delete(screen)
    db.commit()

    return {"message": f"Screen {screen_id} deleted"}


# ── GET /api/ist/screens/{screen_id}/inputs — Get Screen Inputs ─────────────


@router.get("/screens/{screen_id}/inputs")
def get_screen_inputs(screen_id: int, db: Session = Depends(get_db)):
    """Get the original user inputs that created this screen."""
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    # Parse screening brief for hypothesis, constraints, frameworks
    brief = _safe_json_parse(screen.screening_brief)

    return {
        "id": screen.id,
        "name": screen.name,
        "contentType": screen.content_type,
        "rawContent": screen.raw_content,
        "hypothesis": brief.get("hypothesis") if brief else None,
        "constraints": brief.get("constraints") if brief else None,
        "frameworks": brief.get("frameworks") if brief else None,
        "createdAt": screen.created_at.isoformat() if screen.created_at else None,
    }


# ── POST /api/ist/screens/{screen_id}/rerun — Rerun Screen ──────────────────


@router.post("/screens/{screen_id}/rerun")
async def rerun_screen(screen_id: int, db: Session = Depends(get_db)):
    """Reset and rerun an IST screen's workflow from scratch.

    Cancels any active workflow, deletes all child data, resets the screen
    and workflow run to PENDING, and recreates all 22 workflow steps.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    run = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.id == screen.workflow_run_id)
        .first()
    )
    if not run:
        raise HTTPException(
            status_code=404,
            detail=_error("WORKFLOW_NOT_FOUND", "No workflow run associated with this screen."),
        )

    # Cancel if currently running
    if run.status in ("RUNNING", "PAUSED"):
        try:
            await cancel_workflow(run.id)
        except Exception:
            pass

    # Check active workflow limit (exclude this run)
    active_count = (
        db.query(WorkflowRun)
        .filter(
            WorkflowRun.status.in_(["PENDING", "RUNNING", "PAUSED"]),
            WorkflowRun.id != run.id,
        )
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

    # Delete refresh workflow runs first to avoid orphans.
    refresh_run_ids = [
        row.workflow_run_id
        for row in db.query(ISTScreenRefresh.workflow_run_id)
        .filter(ISTScreenRefresh.screen_id == screen_id)
        .all()
    ]
    for refresh_run_id in refresh_run_ids:
        refresh_run = (
            db.query(WorkflowRun)
            .filter(WorkflowRun.id == refresh_run_id)
            .first()
        )
        if refresh_run and refresh_run.status in ("RUNNING", "PAUSED", "PENDING"):
            try:
                await cancel_workflow(refresh_run.id)
            except Exception:
                pass
        if refresh_run:
            db.query(WorkflowStep).filter(WorkflowStep.workflow_run_id == refresh_run.id).delete()
            db.delete(refresh_run)

    # Delete child records in dependency order
    db.query(ISTReport).filter(ISTReport.screen_id == screen_id).delete()
    db.query(ISTStressTest).filter(ISTStressTest.screen_id == screen_id).delete()
    db.query(ISTCatalystCalendar).filter(ISTCatalystCalendar.screen_id == screen_id).delete()
    db.query(ISTRotationStrategy).filter(ISTRotationStrategy.screen_id == screen_id).delete()
    db.query(ISTMasterScreen).filter(ISTMasterScreen.screen_id == screen_id).delete()
    db.query(ISTDialecticReview).filter(ISTDialecticReview.screen_id == screen_id).delete()
    db.query(ISTEffectsChain).filter(ISTEffectsChain.screen_id == screen_id).delete()
    db.query(ISTEquityCandidate).filter(ISTEquityCandidate.screen_id == screen_id).delete()
    db.query(ISTValidation).filter(ISTValidation.screen_id == screen_id).delete()
    db.query(ISTDemandModel).filter(ISTDemandModel.screen_id == screen_id).delete()
    db.query(ISTBottleneck).filter(ISTBottleneck.screen_id == screen_id).delete()
    db.query(ISTClaim).filter(ISTClaim.screen_id == screen_id).delete()
    db.query(ISTScreenRefresh).filter(ISTScreenRefresh.screen_id == screen_id).delete()

    # Delete old workflow steps
    db.query(WorkflowStep).filter(WorkflowStep.workflow_run_id == run.id).delete()

    # Reset screen
    screen.status = "PENDING"
    screen.active_workflow_run_id = run.id
    screen.content_extraction = None
    screen.source_bias = None
    screen.is_certified = False
    screen.certified_at = None
    screen.certification = None
    screen.hfrt_handoff = None
    screen.refresh_count = 0
    screen.last_refreshed_at = None
    screen.updated_at = datetime.now(timezone.utc)

    # Reset workflow run
    run.status = "PENDING"
    run.current_phase = 0
    run.error_message = None
    run.started_at = None
    run.completed_at = None
    run.updated_at = datetime.now(timezone.utc)

    # Recreate all 22 IST workflow steps
    for step_def in IST_WORKFLOW_STEPS:
        step = WorkflowStep(
            workflow_run_id=run.id,
            step_name=step_def["step_name"],
            phase=step_def["phase"],
            phase_name=step_def["phase_name"],
            step_order=step_def["step_order"],
            status="PENDING",
            depends_on=json.dumps(step_def.get("depends_on", [])),
            model_tier=step_def.get("model", "opus"),
            retry_strategy=step_def.get("retry_strategy"),
        )
        db.add(step)

    db.commit()
    db.refresh(screen)
    db.refresh(run)

    return {
        "id": screen.id,
        "workflowRunId": run.id,
        "name": screen.name,
        "status": screen.status,
        "message": "Screen reset and ready to rerun",
    }


# ── GET /api/ist/screens — List IST Screens ────────────────────────────────


@router.post("/screens/{screen_id}/refresh", status_code=201)
@limiter.limit("5/hour")
async def create_screen_refresh(
    request: Request,
    screen_id: int,
    data: ISTScreenRefreshCreate,
    db: Session = Depends(get_db),
):
    """Create an IST refresh workflow run for a completed certified screen."""
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    if screen.status != "COMPLETED":
        raise HTTPException(
            status_code=409,
            detail=_error(
                "INVALID_STATE",
                f"Screen {screen_id} must be COMPLETED to refresh.",
            ),
        )

    if not screen.is_certified:
        raise HTTPException(
            status_code=409,
            detail=_error(
                "NOT_CERTIFIED",
                f"Screen {screen_id} must be certified before refresh.",
            ),
        )

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

    if data.idempotency_key:
        existing = (
            db.query(ISTScreenRefresh)
            .filter(ISTScreenRefresh.idempotency_key == data.idempotency_key)
            .filter(ISTScreenRefresh.status != "FAILED")
            .first()
        )
        if existing:
            warning = None
            if int(screen.refresh_count or 0) >= 3:
                warning = (
                    "This screen has been refreshed 3+ times. "
                    "Consider creating a fresh screen."
                )
            response = {
                "id": existing.id,
                "screenId": existing.screen_id,
                "workflowRunId": existing.workflow_run_id,
                "refreshNumber": existing.refresh_number,
                "status": existing.status,
                "createdAt": existing.created_at.isoformat() if existing.created_at else None,
                "idempotent": True,
            }
            if warning:
                response["warning"] = warning
            return response

    next_refresh_number_row = (
        db.query(func.max(ISTScreenRefresh.refresh_number))
        .filter(ISTScreenRefresh.screen_id == screen_id)
        .scalar()
    )
    next_refresh_number = int(next_refresh_number_row or 0) + 1

    run = WorkflowRun(
        workflow_type="IST_REFRESH",
        name=f"{screen.name} Refresh #{next_refresh_number}",
        status="PENDING",
        current_phase=0,
        auto_advance=data.auto_advance,
    )
    db.add(run)
    db.flush()

    refresh = ISTScreenRefresh(
        screen_id=screen.id,
        workflow_run_id=run.id,
        refresh_number=next_refresh_number,
        status="PENDING",
        content_type=data.content_type or "text",
        delta_content=data.content,
        idempotency_key=data.idempotency_key,
    )
    db.add(refresh)
    db.flush()

    for step_def in IST_REFRESH_WORKFLOW_STEPS:
        db.add(
            WorkflowStep(
                workflow_run_id=run.id,
                step_name=step_def["step_name"],
                phase=step_def["phase"],
                phase_name=step_def["phase_name"],
                step_order=step_def["step_order"],
                status="PENDING",
                depends_on=json.dumps(step_def.get("depends_on", [])),
                model_tier=step_def.get("model", "opus"),
                retry_strategy=step_def.get("retry_strategy"),
            )
        )

    screen.active_workflow_run_id = run.id
    screen.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(refresh)

    warning = None
    if int(screen.refresh_count or 0) >= 3:
        warning = (
            "This screen has been refreshed 3+ times. "
            "Consider creating a fresh screen."
        )

    response = {
        "id": refresh.id,
        "screenId": screen.id,
        "workflowRunId": run.id,
        "refreshNumber": refresh.refresh_number,
        "status": refresh.status,
        "createdAt": refresh.created_at.isoformat() if refresh.created_at else None,
    }
    if warning:
        response["warning"] = warning
    return response


@router.get("/screens/{screen_id}/refreshes")
def list_screen_refreshes(screen_id: int, db: Session = Depends(get_db)):
    """List all refresh operations for a screen."""
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    refreshes = (
        db.query(ISTScreenRefresh)
        .filter(ISTScreenRefresh.screen_id == screen_id)
        .order_by(ISTScreenRefresh.refresh_number.desc())
        .all()
    )

    refresh_ids = [r.id for r in refreshes]
    delta_claim_counts = {}
    if refresh_ids:
        rows = (
            db.query(
                ISTClaim.source_refresh_id,
                func.count(ISTClaim.id).label("cnt"),
            )
            .filter(ISTClaim.screen_id == screen_id)
            .filter(ISTClaim.source_refresh_id.in_(refresh_ids))
            .group_by(ISTClaim.source_refresh_id)
            .all()
        )
        delta_claim_counts = {row.source_refresh_id: row.cnt for row in rows}

    return {
        "screenId": screen_id,
        "refreshes": [
            {
                "id": refresh.id,
                "workflowRunId": refresh.workflow_run_id,
                "refreshNumber": refresh.refresh_number,
                "status": refresh.status,
                "contentType": refresh.content_type,
                "deltaClaimCount": int(delta_claim_counts.get(refresh.id, 0)),
                "newClaimsCount": int(refresh.new_claims_count or 0),
                "tierChangeCount": int(refresh.tier_change_count or 0),
                "stepsReexecuted": _deep_camel(_safe_json_parse(refresh.steps_reexecuted)),
                "impactAssessment": _deep_camel(_safe_json_parse(refresh.impact_assessment)),
                "errorMessage": refresh.error_message,
                "isActive": (
                    screen.active_workflow_run_id == refresh.workflow_run_id
                ),
                "startedAt": refresh.started_at.isoformat() if refresh.started_at else None,
                "completedAt": refresh.completed_at.isoformat() if refresh.completed_at else None,
                "createdAt": refresh.created_at.isoformat() if refresh.created_at else None,
            }
            for refresh in refreshes
        ],
        "total": len(refreshes),
    }


@router.get("/screens/{screen_id}/refreshes/{refresh_id}")
def get_screen_refresh_detail(
    screen_id: int,
    refresh_id: int,
    db: Session = Depends(get_db),
):
    """Get detailed metadata for a specific refresh operation."""
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    refresh = (
        db.query(ISTScreenRefresh)
        .filter(
            ISTScreenRefresh.id == refresh_id,
            ISTScreenRefresh.screen_id == screen_id,
        )
        .first()
    )
    if not refresh:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "REFRESH_NOT_FOUND",
                f"No refresh with id {refresh_id} for screen {screen_id}.",
            ),
        )

    delta_claim_count = (
        db.query(func.count(ISTClaim.id))
        .filter(
            ISTClaim.screen_id == screen_id,
            ISTClaim.source_refresh_id == refresh_id,
        )
        .scalar()
    )

    return {
        "id": refresh.id,
        "screenId": screen_id,
        "workflowRunId": refresh.workflow_run_id,
        "refreshNumber": refresh.refresh_number,
        "status": refresh.status,
        "contentType": refresh.content_type,
        "deltaContent": refresh.delta_content,
        "deltaClaimCount": int(delta_claim_count or 0),
        "newClaimsCount": int(refresh.new_claims_count or 0),
        "newClaims": _deep_camel(_safe_json_parse(refresh.new_claims)),
        "newSourceBias": _deep_camel(_safe_json_parse(refresh.new_source_bias)),
        "tierChanges": _deep_camel(_safe_json_parse(refresh.tier_changes)),
        "tierChangeCount": int(refresh.tier_change_count or 0),
        "stepsReexecuted": _deep_camel(_safe_json_parse(refresh.steps_reexecuted)),
        "impactAssessment": _deep_camel(_safe_json_parse(refresh.impact_assessment)),
        "refreshNotes": _deep_camel(_safe_json_parse(refresh.refresh_notes)),
        "errorMessage": refresh.error_message,
        "isActive": (screen.active_workflow_run_id == refresh.workflow_run_id),
        "startedAt": refresh.started_at.isoformat() if refresh.started_at else None,
        "completedAt": refresh.completed_at.isoformat() if refresh.completed_at else None,
        "createdAt": refresh.created_at.isoformat() if refresh.created_at else None,
    }


@router.get("/screens/{screen_id}/refreshes/{refresh_id}/claims")
def get_screen_refresh_claims(
    screen_id: int,
    refresh_id: int,
    db: Session = Depends(get_db),
):
    """Get only the claims added during a specific refresh."""
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    refresh = (
        db.query(ISTScreenRefresh)
        .filter(
            ISTScreenRefresh.id == refresh_id,
            ISTScreenRefresh.screen_id == screen_id,
        )
        .first()
    )
    if not refresh:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "REFRESH_NOT_FOUND",
                f"No refresh with id {refresh_id} for screen {screen_id}.",
            ),
        )

    claims = (
        db.query(ISTClaim)
        .options(joinedload(ISTClaim.source_refresh))
        .filter(
            ISTClaim.screen_id == screen_id,
            ISTClaim.source_refresh_id == refresh_id,
        )
        .order_by(ISTClaim.id)
        .all()
    )

    return {
        "screenId": screen_id,
        "refreshId": refresh_id,
        "claims": [
            {
                "id": claim.id,
                "claimText": claim.claim_text,
                "sourceCitation": claim.source_citation,
                "quantitativeAnchor": claim.quantitative_anchor,
                "temporalMarker": claim.temporal_marker,
                "bottleneckName": claim.bottleneck_name,
                "confidence": claim.confidence,
                "isValidated": bool(claim.is_validated),
                "validationVerdict": claim.validation_verdict,
                "validationSource": claim.validation_source,
                "sourceRefreshId": claim.source_refresh_id,
                "sourceRefreshNumber": (
                    claim.source_refresh.refresh_number if claim.source_refresh else None
                ),
                "createdAt": claim.created_at.isoformat() if claim.created_at else None,
            }
            for claim in claims
        ],
        "totalCount": len(claims),
    }


@router.get("/screens")
def list_screens(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
):
    """List all IST screens with summary info.

    INV-PE-01: Avoids N+1 by using subqueries for counts.
    """
    valid_statuses = (
        "PENDING", "EXTRACTING", "ANALYZING", "SCANNING",
        "DIALECTIC", "SYNTHESIZING", "COMPLETED", "FAILED",
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

    # Base query
    query = db.query(ISTScreen)
    if status:
        query = query.filter(ISTScreen.status == status)

    total = query.count()

    screens = (
        query.order_by(ISTScreen.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Batch-fetch counts to avoid N+1 (INV-PE-01)
    screen_ids = [s.id for s in screens]

    claim_counts = {}
    candidate_counts = {}
    tier1_counts = {}
    phase_map = {}

    if screen_ids:
        # Claim counts per screen
        claim_rows = (
            db.query(
                ISTClaim.screen_id,
                func.count(ISTClaim.id).label("cnt"),
            )
            .filter(ISTClaim.screen_id.in_(screen_ids))
            .group_by(ISTClaim.screen_id)
            .all()
        )
        claim_counts = {row.screen_id: row.cnt for row in claim_rows}

        # Candidate counts per screen
        cand_rows = (
            db.query(
                ISTEquityCandidate.screen_id,
                func.count(ISTEquityCandidate.id).label("cnt"),
            )
            .filter(ISTEquityCandidate.screen_id.in_(screen_ids))
            .group_by(ISTEquityCandidate.screen_id)
            .all()
        )
        candidate_counts = {row.screen_id: row.cnt for row in cand_rows}

        # Tier 1 counts per screen
        tier1_rows = (
            db.query(
                ISTEquityCandidate.screen_id,
                func.count(ISTEquityCandidate.id).label("cnt"),
            )
            .filter(ISTEquityCandidate.screen_id.in_(screen_ids))
            .filter(ISTEquityCandidate.tier == 1)
            .group_by(ISTEquityCandidate.screen_id)
            .all()
        )
        tier1_counts = {row.screen_id: row.cnt for row in tier1_rows}

        # Current phase from workflow_runs
        run_ids = [
            (s.active_workflow_run_id or s.workflow_run_id)
            for s in screens
        ]
        phase_rows = (
            db.query(
                WorkflowRun.id,
                WorkflowRun.current_phase,
            )
            .filter(WorkflowRun.id.in_(run_ids))
            .all()
        )
        run_phase_map = {row.id: row.current_phase for row in phase_rows}
        phase_map = {
            s.id: run_phase_map.get((s.active_workflow_run_id or s.workflow_run_id), 0)
            for s in screens
        }

    items = []
    for s in screens:
        items.append({
            "id": s.id,
            "name": s.name,
            "status": s.status,
            "workflowRunId": s.workflow_run_id,
            "activeWorkflowRunId": s.active_workflow_run_id or s.workflow_run_id,
            "claimCount": claim_counts.get(s.id, 0),
            "candidateCount": candidate_counts.get(s.id, 0),
            "tier1Count": tier1_counts.get(s.id, 0),
            "refreshCount": int(s.refresh_count or 0),
            "isRefreshing": (
                (s.active_workflow_run_id is not None)
                and (s.active_workflow_run_id != s.workflow_run_id)
            ),
            "lastRefreshedAt": (
                s.last_refreshed_at.isoformat() if s.last_refreshed_at else None
            ),
            "currentPhase": phase_map.get(s.id, 0),
            "createdAt": s.created_at.isoformat() if s.created_at else None,
            "updatedAt": s.updated_at.isoformat() if s.updated_at else None,
        })

    return {"screens": items, "total": total}


# ── GET /api/ist/screens/{id} — Get Screen Detail ──────────────────────────


@router.get("/screens/{screen_id}")
def get_screen_detail(screen_id: int, db: Session = Depends(get_db)):
    """Get full screen detail including screening brief, extraction summary, and bias."""
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    active_run_id = screen.active_workflow_run_id or screen.workflow_run_id

    # Get current phase from active workflow run
    run = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.id == active_run_id)
        .first()
    )
    current_phase = run.current_phase if run else 0

    # Parse JSON columns safely and convert nested keys to camelCase
    screening_brief = _deep_camel(_safe_json_parse(screen.screening_brief))
    content_extraction = _deep_camel(_safe_json_parse(screen.content_extraction))
    source_bias = _deep_camel(_safe_json_parse(screen.source_bias))
    certification = _deep_camel(_safe_json_parse(screen.certification))
    hfrt_handoff = _deep_camel(_safe_json_parse(screen.hfrt_handoff))

    return {
        "id": screen.id,
        "workflowRunId": screen.workflow_run_id,
        "activeWorkflowRunId": active_run_id,
        "name": screen.name,
        "status": screen.status,
        "contentType": screen.content_type,
        "screeningBrief": screening_brief,
        "contentExtraction": content_extraction,
        "sourceBias": source_bias,
        "refreshCount": int(screen.refresh_count or 0),
        "isRefreshing": (
            (screen.active_workflow_run_id is not None)
            and (screen.active_workflow_run_id != screen.workflow_run_id)
        ),
        "lastRefreshedAt": (
            screen.last_refreshed_at.isoformat() if screen.last_refreshed_at else None
        ),
        "currentPhase": current_phase,
        "isCertified": bool(screen.is_certified),
        "certifiedAt": screen.certified_at.isoformat() if screen.certified_at else None,
        "certification": certification,
        "hfrtHandoff": hfrt_handoff,
        "createdAt": screen.created_at.isoformat() if screen.created_at else None,
        "updatedAt": screen.updated_at.isoformat() if screen.updated_at else None,
    }


# ── GET /api/ist/screens/{id}/claims — Get Claims List ─────────────────────


@router.get("/screens/{screen_id}/claims")
def get_screen_claims(
    screen_id: int,
    validated: Optional[bool] = Query(
        default=None, description="Filter by validation status"
    ),
    has_quant_anchor: Optional[bool] = Query(
        default=None,
        alias="hasQuantAnchor",
        description="Filter claims with quantitative anchors",
    ),
    db: Session = Depends(get_db),
):
    """Get all extracted claims for this screen."""
    # Verify screen exists
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    query = (
        db.query(ISTClaim)
        .options(joinedload(ISTClaim.source_refresh))
        .filter(ISTClaim.screen_id == screen_id)
    )

    if validated is not None:
        query = query.filter(
            ISTClaim.is_validated == (1 if validated else 0)
        )

    if has_quant_anchor is not None:
        if has_quant_anchor:
            query = query.filter(ISTClaim.quantitative_anchor.isnot(None))
        else:
            query = query.filter(ISTClaim.quantitative_anchor.is_(None))

    claims = query.order_by(ISTClaim.id).all()

    total_count = (
        db.query(func.count(ISTClaim.id))
        .filter(ISTClaim.screen_id == screen_id)
        .scalar()
    )
    validated_count = (
        db.query(func.count(ISTClaim.id))
        .filter(ISTClaim.screen_id == screen_id)
        .filter(ISTClaim.is_validated == 1)
        .scalar()
    )

    claim_items = [
        {
            "id": c.id,
            "claimText": c.claim_text,
            "sourceCitation": c.source_citation,
            "quantitativeAnchor": c.quantitative_anchor,
            "temporalMarker": c.temporal_marker,
            "bottleneckName": c.bottleneck_name,
            "confidence": c.confidence,
            "isValidated": bool(c.is_validated),
            "validationVerdict": c.validation_verdict,
            "validationSource": c.validation_source,
            "sourceRefreshId": c.source_refresh_id,
            "sourceRefreshNumber": (
                c.source_refresh.refresh_number if c.source_refresh else None
            ),
        }
        for c in claims
    ]

    return {
        "screenId": screen_id,
        "claims": claim_items,
        "totalCount": total_count or 0,
        "validatedCount": validated_count or 0,
    }


# ── PUT /api/ist/screens/{id}/brief — Update Screening Brief ───────────────


@router.put("/screens/{screen_id}/brief")
def update_screen_brief(
    screen_id: int,
    data: ISTScreenBriefUpdate,
    db: Session = Depends(get_db),
):
    """Update the screening brief (only when workflow is PAUSED).

    INV-SE-04: Validate workflow state before allowing mutation.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    # Check that the workflow is PAUSED
    run = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.id == screen.workflow_run_id)
        .first()
    )
    if not run or run.status != "PAUSED":
        raise HTTPException(
            status_code=409,
            detail=_error(
                "INVALID_STATE",
                "Screening brief can only be updated when the workflow is PAUSED.",
            ),
        )

    # Parse existing brief or create new
    existing_brief = {}
    if screen.screening_brief:
        try:
            existing_brief = json.loads(screen.screening_brief)
        except (json.JSONDecodeError, TypeError):
            existing_brief = {}

    # Merge updates (only non-None fields)
    if data.hypothesis is not None:
        existing_brief["hypothesis"] = data.hypothesis
    if data.constraints is not None:
        existing_brief["constraints"] = data.constraints
    if data.frameworks is not None:
        existing_brief["frameworks"] = data.frameworks

    # Validate via Pydantic and write (INV-BE-06)
    updated_brief = ScreeningBrief.model_validate(existing_brief)
    screen.screening_brief = updated_brief.model_dump_json()
    screen.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "id": screen.id,
        "screeningBrief": updated_brief.model_dump(),
        "message": "Screening brief updated successfully.",
    }


# ── GET /api/ist/screens/{id}/bottlenecks — Get Bottlenecks ─────────────────


@router.get("/screens/{screen_id}/bottlenecks")
def get_screen_bottlenecks(screen_id: int, db: Session = Depends(get_db)):
    """Get all bottlenecks for a screen with phase breakdown.

    INV-PE-01: Avoids N+1 by loading all bottlenecks in a single query.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    bottlenecks = (
        db.query(ISTBottleneck)
        .filter(ISTBottleneck.screen_id == screen_id)
        .order_by(ISTBottleneck.phase, ISTBottleneck.id)
        .all()
    )

    # Build phase counts
    phase_count = {"phase1": 0, "phase2": 0, "phase3": 0, "crossCutting": 0}
    for bn in bottlenecks:
        if bn.phase == 0:
            phase_count["crossCutting"] += 1
        elif bn.phase == 1:
            phase_count["phase1"] += 1
        elif bn.phase == 2:
            phase_count["phase2"] += 1
        elif bn.phase == 3:
            phase_count["phase3"] += 1

    bottleneck_items = [
        {
            "id": bn.id,
            "name": bn.name,
            "phase": bn.phase,
            "phaseLabel": bn.phase_label,
            "description": bn.description,
            "quantitativeEvidence": bn.quantitative_evidence,
            "temporalMarker": bn.temporal_marker,
            "resolutionTrigger": bn.resolution_trigger,
            "causalParentId": bn.causal_parent_id,
            "createdAt": bn.created_at.isoformat() if bn.created_at else None,
        }
        for bn in bottlenecks
    ]

    return {
        "screenId": screen_id,
        "bottlenecks": bottleneck_items,
        "phaseCount": phase_count,
    }


# ── GET /api/ist/screens/{id}/demand-models — Get Demand Models ─────────────


@router.get("/screens/{screen_id}/demand-models")
def get_screen_demand_models(screen_id: int, db: Session = Depends(get_db)):
    """Get all demand models for a screen.

    INV-PE-01: Single query for all models, with bottleneck name joined.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    # Join to get bottleneck name in one query (INV-PE-01)
    models = (
        db.query(ISTDemandModel, ISTBottleneck.name.label("bottleneck_name"))
        .join(ISTBottleneck, ISTDemandModel.bottleneck_id == ISTBottleneck.id)
        .filter(ISTDemandModel.screen_id == screen_id)
        .order_by(ISTDemandModel.id)
        .all()
    )

    model_items = []
    for dm, bn_name in models:
        # Parse JSON columns safely and convert nested keys to camelCase
        base_case = _deep_camel(_safe_json_parse(dm.base_case))
        bull_case = _deep_camel(_safe_json_parse(dm.bull_case))
        bear_case = _deep_camel(_safe_json_parse(dm.bear_case))
        sensitivity_table = _deep_camel(_safe_json_parse(dm.sensitivity_table))

        model_items.append({
            "id": dm.id,
            "bottleneckId": dm.bottleneck_id,
            "bottleneckName": bn_name,
            "formula": dm.formula,
            "baseCase": base_case,
            "bullCase": bull_case,
            "bearCase": bear_case,
            "sensitivityTable": sensitivity_table,
            "multiplierChain": dm.multiplier_chain,
            "createdAt": dm.created_at.isoformat() if dm.created_at else None,
        })

    return {
        "screenId": screen_id,
        "demandModels": model_items,
    }


# ── GET /api/ist/screens/{id}/validation — Get Validation Results ───────────


@router.get("/screens/{screen_id}/validation")
def get_screen_validation(screen_id: int, db: Session = Depends(get_db)):
    """Get all claim validation results for a screen with summary.

    INV-PE-01: Avoids N+1 by joining validations with claims in a single query.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    # Join validations with claims to get claim_text (INV-PE-01)
    validations = (
        db.query(ISTValidation, ISTClaim.claim_text)
        .join(ISTClaim, ISTValidation.claim_id == ISTClaim.id)
        .filter(ISTValidation.screen_id == screen_id)
        .order_by(ISTValidation.id)
        .all()
    )

    # Build summary counts
    summary = {
        "confirmed": 0,
        "partiallyConfirmed": 0,
        "contradicted": 0,
        "unvalidatable": 0,
        "total": len(validations),
    }

    validation_items = []
    for val, claim_text in validations:
        # Count by verdict
        if val.verdict == "confirmed":
            summary["confirmed"] += 1
        elif val.verdict == "partially_confirmed":
            summary["partiallyConfirmed"] += 1
        elif val.verdict == "contradicted":
            summary["contradicted"] += 1
        elif val.verdict == "unvalidatable":
            summary["unvalidatable"] += 1

        sources = _deep_camel(_safe_json_parse(val.sources))
        search_queries = _deep_camel(_safe_json_parse(val.search_queries))

        validation_items.append({
            "id": val.id,
            "claimId": val.claim_id,
            "claimText": claim_text,
            "verdict": val.verdict,
            "confidence": val.confidence,
            "evidence": val.evidence,
            "sources": sources,
            "searchQueries": search_queries,
            "validatedAt": val.validated_at.isoformat() if val.validated_at else None,
        })

    return {
        "screenId": screen_id,
        "validations": validation_items,
        "summary": summary,
    }


# ── GET /api/ist/screens/{id}/candidates — Get Equity Candidates ─────────────


@router.get("/screens/{screen_id}/candidates")
def get_screen_candidates(
    screen_id: int,
    tier: Optional[int] = Query(default=None, ge=1, le=3, description="Filter by tier"),
    bottleneck_id: Optional[int] = Query(
        default=None,
        alias="bottleneckId",
        description="Filter by bottleneck ID",
    ),
    db: Session = Depends(get_db),
):
    """Get all equity candidates for a screen with tier breakdown.

    INV-PE-01: Avoids N+1 by joining candidates with bottleneck names in a single query.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    # Base query with outer join for bottleneck name
    query = (
        db.query(
            ISTEquityCandidate,
            ISTBottleneck.name.label("bottleneck_name"),
        )
        .outerjoin(ISTBottleneck, ISTEquityCandidate.bottleneck_id == ISTBottleneck.id)
        .filter(ISTEquityCandidate.screen_id == screen_id)
    )

    if tier is not None:
        query = query.filter(ISTEquityCandidate.tier == tier)

    if bottleneck_id is not None:
        query = query.filter(ISTEquityCandidate.bottleneck_id == bottleneck_id)

    results = query.order_by(ISTEquityCandidate.tier, ISTEquityCandidate.id).all()

    # Build tier breakdown (from unfiltered candidates)
    all_candidates = (
        db.query(ISTEquityCandidate)
        .filter(ISTEquityCandidate.screen_id == screen_id)
        .all()
    )
    tier_breakdown = {"tier1": 0, "tier2": 0, "tier3": 0}
    for c in all_candidates:
        if c.tier == 1:
            tier_breakdown["tier1"] += 1
        elif c.tier == 2:
            tier_breakdown["tier2"] += 1
        elif c.tier == 3:
            tier_breakdown["tier3"] += 1

    candidate_items = []
    for cand, bn_name in results:
        scarcity_score = _deep_camel(_safe_json_parse(cand.scarcity_score))
        candidate_items.append({
            "id": cand.id,
            "ticker": cand.ticker,
            "companyName": cand.company_name,
            "bottleneckId": cand.bottleneck_id,
            "bottleneckName": bn_name,
            "scarcityScore": scarcity_score,
            "moatType": cand.moat_type,
            "moatEvidence": cand.moat_evidence,
            "catalyst": cand.catalyst,
            "tier": cand.tier,
            "tierRationale": cand.tier_rationale,
            "phase": cand.phase,
            "conviction": cand.conviction,
            "priceAtScreen": cand.price_at_screen,
            "peRatio": cand.pe_ratio,
            "marketCap": cand.market_cap,
        })

    return {
        "screenId": screen_id,
        "candidates": candidate_items,
        "tierBreakdown": tier_breakdown,
        "totalCount": len(all_candidates),
    }


# ── GET /api/ist/screens/{id}/effects — Get Effects Chains ──────────────────


@router.get("/screens/{screen_id}/effects")
def get_screen_effects(screen_id: int, db: Session = Depends(get_db)):
    """Get all effects chains for a screen.

    INV-PE-01: Joins effects with equity candidates to get ticker in one query.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    # Join to get equity candidate ticker (INV-PE-01)
    effects = (
        db.query(
            ISTEffectsChain,
            ISTEquityCandidate.ticker.label("equity_ticker"),
        )
        .outerjoin(
            ISTEquityCandidate,
            ISTEffectsChain.equity_candidate_id == ISTEquityCandidate.id,
        )
        .filter(ISTEffectsChain.screen_id == screen_id)
        .order_by(ISTEffectsChain.effect_order, ISTEffectsChain.id)
        .all()
    )

    effect_items = [
        {
            "id": effect.id,
            "thesis": effect.thesis,
            "order": effect.effect_order,
            "effectDescription": effect.effect_description,
            "equityCandidateId": effect.equity_candidate_id,
            "equityTicker": ticker,
        }
        for effect, ticker in effects
    ]

    return {
        "screenId": screen_id,
        "effectsChains": effect_items,
    }


# ── GET /api/ist/screens/{id}/tiers — Get Tier Breakdown ────────────────────


@router.get("/screens/{screen_id}/tiers")
def get_screen_tiers(screen_id: int, db: Session = Depends(get_db)):
    """Get equity candidates organized by tier with labels and criteria.

    INV-PE-01: Single query for all candidates.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    candidates = (
        db.query(ISTEquityCandidate)
        .filter(ISTEquityCandidate.screen_id == screen_id)
        .order_by(ISTEquityCandidate.tier, ISTEquityCandidate.id)
        .all()
    )

    def _candidate_to_dict(c: ISTEquityCandidate) -> dict:
        return {
            "id": c.id,
            "ticker": c.ticker,
            "companyName": c.company_name,
            "scarcityScore": _deep_camel(_safe_json_parse(c.scarcity_score)),
            "moatType": c.moat_type,
            "conviction": c.conviction,
            "tier": c.tier,
            "tierRationale": c.tier_rationale,
        }

    tier1_cands = [c for c in candidates if c.tier == 1]
    tier2_cands = [c for c in candidates if c.tier == 2]
    tier3_cands = [c for c in candidates if c.tier == 3]

    return {
        "screenId": screen_id,
        "tiers": {
            "tier1": {
                "label": "High Conviction",
                "criteria": "Scarcity score >= 4.0, market cap present, moat evidence documented",
                "candidates": [_candidate_to_dict(c) for c in tier1_cands],
                "count": len(tier1_cands),
            },
            "tier2": {
                "label": "Watchlist",
                "criteria": "Scarcity score >= 3.0, or high scarcity with missing data",
                "candidates": [_candidate_to_dict(c) for c in tier2_cands],
                "count": len(tier2_cands),
            },
            "tier3": {
                "label": "Speculative",
                "criteria": "Scarcity score below 3.0",
                "candidates": [_candidate_to_dict(c) for c in tier3_cands],
                "count": len(tier3_cands),
            },
        },
    }


# ── GET /api/ist/screens/{id}/invariants — Get Invariant Check Results ───────


@router.get("/screens/{screen_id}/invariants")
def get_screen_invariants(screen_id: int, db: Session = Depends(get_db)):
    """Get invariant check results for a screen.

    Runs the invariant checks live (they are cheap, deterministic queries).
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    # Run all invariant checks inline (same logic as the step handler)
    invariants = []

    # INV-1: Source Citation Required
    claims = (
        db.query(ISTClaim)
        .filter(ISTClaim.screen_id == screen_id)
        .all()
    )
    total_claims = len(claims)
    claims_with_citation = sum(
        1 for c in claims
        if c.source_citation is not None and c.source_citation.strip() != ""
    )
    inv1_pass = total_claims > 0 and claims_with_citation == total_claims
    invariants.append({
        "id": "INV-1",
        "name": "Source Citation Required",
        "status": "PASS" if inv1_pass else "FAIL",
        "details": (
            f"All {total_claims} claims have source citations."
            if inv1_pass
            else f"{claims_with_citation}/{total_claims} claims have source citations."
        ),
    })

    # INV-2: Quantitative Anchor Required (>= 50%)
    claims_with_quant = sum(
        1 for c in claims
        if c.quantitative_anchor is not None and c.quantitative_anchor.strip() != ""
    )
    quant_pct = (claims_with_quant / total_claims * 100) if total_claims > 0 else 0
    inv2_pass = total_claims > 0 and quant_pct >= 50
    invariants.append({
        "id": "INV-2",
        "name": "Quantitative Anchor Required",
        "status": "PASS" if inv2_pass else "FAIL",
        "details": (
            f"{claims_with_quant}/{total_claims} claims ({quant_pct:.0f}%) have "
            f"quantitative anchors (>= 50% required)."
        ),
    })

    # INV-3: Temporal Marker Required
    claims_with_temporal = sum(
        1 for c in claims
        if c.temporal_marker is not None and c.temporal_marker.strip() != ""
    )
    inv3_pass = claims_with_temporal >= 1
    invariants.append({
        "id": "INV-3",
        "name": "Temporal Marker Required",
        "status": "PASS" if inv3_pass else "FAIL",
        "details": f"{claims_with_temporal} claims have temporal markers (>= 1 required).",
    })

    # INV-4: No Orphan Equities
    candidates = (
        db.query(ISTEquityCandidate)
        .filter(ISTEquityCandidate.screen_id == screen_id)
        .all()
    )
    total_candidates = len(candidates)
    orphan_candidates = sum(1 for c in candidates if c.bottleneck_id is None)
    inv4_pass = total_candidates == 0 or orphan_candidates == 0
    invariants.append({
        "id": "INV-4",
        "name": "No Orphan Equities",
        "status": "PASS" if inv4_pass else "FAIL",
        "details": (
            f"All {total_candidates} candidates linked to bottlenecks."
            if inv4_pass
            else f"{orphan_candidates}/{total_candidates} candidates lack bottleneck linkage."
        ),
    })

    # INV-5: Tier Justification Required
    candidates_with_rationale = sum(
        1 for c in candidates
        if c.tier_rationale is not None and c.tier_rationale.strip() != ""
    )
    inv5_pass = total_candidates == 0 or candidates_with_rationale == total_candidates
    invariants.append({
        "id": "INV-5",
        "name": "Tier Justification Required",
        "status": "PASS" if inv5_pass else "FAIL",
        "details": (
            f"All {total_candidates} candidates have tier rationale."
            if inv5_pass
            else f"{candidates_with_rationale}/{total_candidates} candidates have tier rationale."
        ),
    })

    # INV-6, 7, 8: Skipped (checked in later phases)
    invariants.append({
        "id": "INV-6",
        "name": "Dialectic Isolation",
        "status": "SKIPPED",
        "details": "Checked in Phase 4 (Dialectic Scrutiny).",
    })
    invariants.append({
        "id": "INV-7",
        "name": "Anti-Hallucination",
        "status": "SKIPPED",
        "details": "Checked in Phase 5 (Final Synthesis).",
    })
    invariants.append({
        "id": "INV-8",
        "name": "Report Completeness",
        "status": "SKIPPED",
        "details": "Checked in Phase 5 (Final Synthesis).",
    })

    pass_count = sum(1 for inv in invariants if inv["status"] == "PASS")
    fail_count = sum(1 for inv in invariants if inv["status"] == "FAIL")
    all_passed = fail_count == 0

    return {
        "screenId": screen_id,
        "invariants": invariants,
        "allPassed": all_passed,
        "passCount": pass_count,
        "failCount": fail_count,
    }


# ── Utility ─────────────────────────────────────────────────────────────────


def _safe_json_parse(value: Optional[str]) -> any:
    """Safely parse a JSON string, returning None on failure."""
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def _snake_to_camel(s: str) -> str:
    """Convert a snake_case string to camelCase.

    Already-camelCase or single-word strings pass through unchanged.
    Examples:
        "key_arguments"   -> "keyArguments"
        "conviction_level" -> "convictionLevel"
        "screenId"        -> "screenId"   (no underscore, unchanged)
        "name"            -> "name"       (single word, unchanged)
    """
    if "_" not in s:
        return s
    components = s.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def _deep_camel(obj):
    """Recursively convert all dict keys from snake_case to camelCase.

    Handles nested dicts, lists of dicts, and passes primitives through.
    Already-camelCase keys are preserved (no underscore means no change).
    """
    if isinstance(obj, dict):
        return {_snake_to_camel(k): _deep_camel(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_camel(item) for item in obj]
    return obj


def _normalize_catalyst(catalyst: dict) -> dict:
    """Normalize a catalyst dict to match the frontend's expected shape.

    After _deep_camel has already been applied:
    - If `ticker` exists but not `tickers`, wrap as [ticker]
    - If `impact` exists but not `expectedImpact`, copy it
    - Default `importance` to "MEDIUM" if missing
    - Default `dateType` to "estimated" if missing
    """
    # ticker (string) -> tickers (array)
    if "ticker" in catalyst and "tickers" not in catalyst:
        ticker_val = catalyst.pop("ticker")
        catalyst["tickers"] = [ticker_val] if ticker_val else []
    # impact -> expectedImpact
    if "impact" in catalyst and "expectedImpact" not in catalyst:
        catalyst["expectedImpact"] = catalyst.pop("impact")
    # Defaults
    if "importance" not in catalyst:
        catalyst["importance"] = "MEDIUM"
    if "dateType" not in catalyst:
        catalyst["dateType"] = "estimated"
    return catalyst


def _normalize_stress_test(test: dict) -> dict:
    """Normalize a stress test dict to match the frontend's expected shape.

    After _deep_camel has already been applied:
    - If `impactAssessment` or `description` exists but not `impact`, set it
    - Default `survivorTickers` and `casualtyTickers` to [] if missing
    - Default `framework` to `scenario` value if missing
    """
    # impactAssessment/description -> impact
    if "impact" not in test:
        if "impactAssessment" in test:
            test["impact"] = test["impactAssessment"]
        elif "description" in test:
            test["impact"] = test["description"]
    # Default empty arrays for tickers
    if "survivorTickers" not in test:
        test["survivorTickers"] = []
    if "casualtyTickers" not in test:
        test["casualtyTickers"] = []
    # framework fallback
    if "framework" not in test:
        test["framework"] = test.get("scenario", "")
    return test


# ── POST /api/ist/screens/{id}/dialectic — Trigger Dialectic Analysis ────────


@router.post("/screens/{screen_id}/dialectic", status_code=202)
async def trigger_dialectic(
    screen_id: int,
    db: Session = Depends(get_db),
):
    """Trigger dialectic analysis (Phase 4) for a screen.

    Pre-check: Screen must have completed Phase 3 (all Phase 3 steps COMPLETED).
    Returns 202 Accepted and starts the workflow for Phase 4 steps.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    # Verify workflow exists
    run = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.id == screen.workflow_run_id)
        .first()
    )
    if not run:
        raise HTTPException(
            status_code=404,
            detail=_error("WORKFLOW_NOT_FOUND", "No workflow run associated with this screen."),
        )

    # Pre-check: Verify Phase 3 is complete (all steps with phase <= 3 are COMPLETED)
    phase3_incomplete = (
        db.query(WorkflowStep)
        .filter(
            WorkflowStep.workflow_run_id == run.id,
            WorkflowStep.phase <= 3,
            WorkflowStep.status != "COMPLETED",
        )
        .count()
    )
    if phase3_incomplete > 0:
        raise HTTPException(
            status_code=409,
            detail=_error(
                "PHASE_NOT_COMPLETE",
                "Phase 3 (Equity Identification) must be completed before "
                "starting dialectic analysis. "
                f"{phase3_incomplete} step(s) still pending.",
            ),
        )

    # Check that dialectic steps are still PENDING (not already run)
    dialectic_steps = (
        db.query(WorkflowStep)
        .filter(
            WorkflowStep.workflow_run_id == run.id,
            WorkflowStep.step_name.in_(
                ["dialectic_optimist", "dialectic_pessimist", "dialectic_synthesis"]
            ),
        )
        .all()
    )

    already_running = any(s.status in ("RUNNING", "COMPLETED") for s in dialectic_steps)
    if already_running:
        raise HTTPException(
            status_code=409,
            detail=_error(
                "ALREADY_STARTED",
                "Dialectic analysis has already been started or completed.",
            ),
        )

    # Resume the workflow — it was PAUSED at the Phase 3->4 boundary
    if run.status == "PAUSED":
        run.status = "RUNNING"
        run.updated_at = datetime.now(timezone.utc)
        db.commit()
        # Start the workflow engine to continue from where it paused
        try:
            await start_workflow(run.id)
        except ValueError:
            # Already running — that's fine
            pass

    return {
        "screenId": screen_id,
        "message": "Dialectic analysis started",
        "status": "RUNNING",
    }


# ── GET /api/ist/screens/{id}/dialectic/{side} — Get Dialectic Review ────────


@router.get("/screens/{screen_id}/dialectic/{side}")
def get_dialectic_review(
    screen_id: int,
    side: str,
    db: Session = Depends(get_db),
):
    """Get a specific dialectic review (optimist, pessimist, or synthesis).

    INV-PE-01: Single query for the review record.
    """
    # Validate side parameter
    valid_sides = {"optimist": "OPTIMIST", "pessimist": "PESSIMIST", "synthesis": "SYNTHESIS"}
    side_upper = valid_sides.get(side.lower())
    if side_upper is None:
        raise HTTPException(
            status_code=400,
            detail=_error(
                "INVALID_SIDE",
                f"side must be one of: optimist, pessimist, synthesis. Got: {side}",
            ),
        )

    # Verify screen exists
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    # Load the review
    review = (
        db.query(ISTDialecticReview)
        .filter(
            ISTDialecticReview.screen_id == screen_id,
            ISTDialecticReview.side == side_upper,
        )
        .first()
    )
    if not review:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "REVIEW_NOT_FOUND",
                f"No {side} review found for screen {screen_id}.",
            ),
        )

    # Parse the JSON content column and convert nested keys to camelCase
    content = _safe_json_parse(review.content)
    if content is not None:
        content = _deep_camel(content)

    return {
        "screenId": screen_id,
        "side": review.side,
        "content": content,
        "createdAt": review.created_at.isoformat() if review.created_at else None,
    }


# ── GET /api/ist/screens/{id}/synthesis — Get Synthesis (shortcut) ───────────


@router.get("/screens/{screen_id}/synthesis")
def get_synthesis(
    screen_id: int,
    db: Session = Depends(get_db),
):
    """Shortcut endpoint for getting the synthesis review.

    Returns the synthesis in the synthesis-specific format with
    disagreements, final tier adjustments, overall conviction, and key risks.

    INV-PE-01: Single query for the review record.
    """
    # Verify screen exists
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    # Load the synthesis review
    review = (
        db.query(ISTDialecticReview)
        .filter(
            ISTDialecticReview.screen_id == screen_id,
            ISTDialecticReview.side == "SYNTHESIS",
        )
        .first()
    )
    if not review:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "SYNTHESIS_NOT_FOUND",
                f"No synthesis review found for screen {screen_id}. "
                "Dialectic analysis may not have completed yet.",
            ),
        )

    # Parse and convert nested keys to camelCase
    content = _safe_json_parse(review.content)
    if content is None:
        raise HTTPException(
            status_code=500,
            detail=_error(
                "PARSE_ERROR",
                "Failed to parse synthesis content.",
            ),
        )

    # Convert all nested keys first, then extract with camelCase names
    content = _deep_camel(content)
    synthesis_payload = {
        "narrative": content.get("narrative"),
        "disagreements": content.get("disagreements", []),
        "finalTierAdjustments": content.get("finalTierAdjustments", []),
        "overallConviction": content.get("overallConviction"),
        "keyRisks": content.get("keyRisks", []),
    }

    return {
        "screenId": screen_id,
        # Backward-compatible top-level shape.
        "narrative": synthesis_payload["narrative"],
        "disagreements": synthesis_payload["disagreements"],
        "finalTierAdjustments": synthesis_payload["finalTierAdjustments"],
        "overallConviction": synthesis_payload["overallConviction"],
        "keyRisks": synthesis_payload["keyRisks"],
        # New nested shape used by the frontend.
        "synthesis": synthesis_payload,
        "createdAt": review.created_at.isoformat() if review.created_at else None,
    }


# ── GET /api/ist/screens/{id}/master-screen — Get Master Screen ──────────────


@router.get("/screens/{screen_id}/master-screen")
def get_master_screen(screen_id: int, db: Session = Depends(get_db)):
    """Get the master screen (final ranked equity list) for a screen.

    INV-PE-01: Single query for the master screen record.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    master = (
        db.query(ISTMasterScreen)
        .filter(ISTMasterScreen.screen_id == screen_id)
        .first()
    )
    if not master:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "MASTER_SCREEN_NOT_FOUND",
                f"No master screen found for screen {screen_id}. "
                "Phase 5 may not have started yet.",
            ),
        )

    ranked_equities = _deep_camel(_safe_json_parse(master.ranked_equities))
    raw_invariant_compliance = _safe_json_parse(master.invariant_compliance)

    # Transform invariant array into summary object for frontend
    # Frontend expects: { allPassed: bool, checkedAt: string }
    if isinstance(raw_invariant_compliance, list):
        all_passed = all(
            inv.get("status") == "PASS"
            for inv in raw_invariant_compliance
            if isinstance(inv, dict)
        )
        invariant_compliance = {
            "allPassed": all_passed,
            "checkedAt": screen.updated_at.isoformat() if screen.updated_at else None,
        }
    elif isinstance(raw_invariant_compliance, dict):
        # Already in the right shape or close to it
        invariant_compliance = {
            "allPassed": raw_invariant_compliance.get("all_passed", raw_invariant_compliance.get("allPassed", False)),
            "checkedAt": raw_invariant_compliance.get("checked_at", raw_invariant_compliance.get("checkedAt",
                screen.updated_at.isoformat() if screen.updated_at else None)),
        }
    else:
        invariant_compliance = {
            "allPassed": False,
            "checkedAt": screen.updated_at.isoformat() if screen.updated_at else None,
        }

    return {
        "screenId": screen_id,
        "rankedEquities": ranked_equities,
        "invariantCompliance": invariant_compliance,
        "totalEquities": master.total_equities,
        "tier1Count": master.tier1_count,
        "createdAt": master.created_at.isoformat() if master.created_at else None,
    }


# ── GET /api/ist/screens/{id}/rotation — Get Rotation Strategy ───────────────


@router.get("/screens/{screen_id}/rotation")
def get_rotation_strategy(screen_id: int, db: Session = Depends(get_db)):
    """Get the rotation strategy for a screen.

    INV-PE-01: Single query for the rotation strategy record.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    rotation = (
        db.query(ISTRotationStrategy)
        .filter(ISTRotationStrategy.screen_id == screen_id)
        .first()
    )
    if not rotation:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "ROTATION_NOT_FOUND",
                f"No rotation strategy found for screen {screen_id}.",
            ),
        )

    return {
        "screenId": screen_id,
        "phaseAllocations": _deep_camel(_safe_json_parse(rotation.phase_allocations)),
        "rotationTriggers": _deep_camel(_safe_json_parse(rotation.rotation_triggers)),
        "riskLimits": _deep_camel(_safe_json_parse(rotation.risk_limits)),
        "createdAt": rotation.created_at.isoformat() if rotation.created_at else None,
    }


# ── GET /api/ist/screens/{id}/catalysts — Get Catalyst Calendar ──────────────


@router.get("/screens/{screen_id}/catalysts")
def get_catalyst_calendar(screen_id: int, db: Session = Depends(get_db)):
    """Get the catalyst calendar for a screen.

    INV-PE-01: Single query for the catalyst calendar record.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    calendar = (
        db.query(ISTCatalystCalendar)
        .filter(ISTCatalystCalendar.screen_id == screen_id)
        .first()
    )
    if not calendar:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "CATALYSTS_NOT_FOUND",
                f"No catalyst calendar found for screen {screen_id}.",
            ),
        )

    # Parse catalysts JSON and normalize each entry for the frontend
    raw_catalysts = _safe_json_parse(calendar.catalysts)
    if isinstance(raw_catalysts, list):
        catalysts = [
            _normalize_catalyst(_deep_camel(cat)) if isinstance(cat, dict) else cat
            for cat in raw_catalysts
        ]
    else:
        catalysts = _deep_camel(raw_catalysts) if raw_catalysts is not None else None

    # Compute nextCatalyst as object with { date, event, daysUntil } or null
    # Frontend expects: { date: string, event: string, daysUntil: number } | null
    next_catalyst = None
    if isinstance(catalysts, list) and len(catalysts) > 0:
        first_cat = catalysts[0]
        if isinstance(first_cat, dict):
            next_catalyst = {
                "date": first_cat.get("date", calendar.next_catalyst_date or ""),
                "event": first_cat.get("event", first_cat.get("description", "")),
                "daysUntil": 0,  # Quarter labels like "Q1 2025" lack exact dates
            }

    return {
        "screenId": screen_id,
        "catalysts": catalysts,
        "totalCatalysts": calendar.total_catalysts,
        # Backward-compatible legacy field.
        "nextCatalyst": calendar.next_catalyst_date,
        # Richer field for the frontend.
        "nextCatalystDetails": next_catalyst,
        "createdAt": calendar.created_at.isoformat() if calendar.created_at else None,
    }


# ── GET /api/ist/screens/{id}/stress-tests — Get Stress Tests ────────────────


@router.get("/screens/{screen_id}/stress-tests")
def get_stress_tests(screen_id: int, db: Session = Depends(get_db)):
    """Get the stress test results for a screen.

    INV-PE-01: Single query for the stress test record.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    stress = (
        db.query(ISTStressTest)
        .filter(ISTStressTest.screen_id == screen_id)
        .first()
    )
    if not stress:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "STRESS_TESTS_NOT_FOUND",
                f"No stress tests found for screen {screen_id}.",
            ),
        )

    # Parse and normalize stress test data for the frontend
    raw_framework_tests = _safe_json_parse(stress.framework_tests)
    if isinstance(raw_framework_tests, list):
        framework_tests = [
            _normalize_stress_test(_deep_camel(t)) if isinstance(t, dict) else t
            for t in raw_framework_tests
        ]
    else:
        framework_tests = _deep_camel(raw_framework_tests) if raw_framework_tests is not None else None

    # ── nameTests: group flat items by ticker for frontend ──────────
    # Frontend expects: [{ ticker, companyName, overallSurvivalScore, scenarios: [...] }]
    raw_name_tests = _safe_json_parse(stress.name_tests)
    if isinstance(raw_name_tests, list):
        # Normalize each item first
        normalized_name_tests = [
            _normalize_stress_test(_deep_camel(t)) if isinstance(t, dict) else t
            for t in raw_name_tests
        ]
        # Group by ticker
        grouped = defaultdict(list)
        for item in normalized_name_tests:
            if isinstance(item, dict):
                grouped[item.get("ticker", "UNKNOWN")].append(item)
        name_tests = []
        for ticker, scenarios in grouped.items():
            avg_survival = (
                sum(s.get("survivalProbability", 0) for s in scenarios) / len(scenarios)
                if scenarios
                else 0
            )
            name_tests.append({
                "ticker": ticker,
                "companyName": scenarios[0].get("companyName", ticker) if scenarios else ticker,
                "overallSurvivalScore": round(avg_survival * 100),
                "scenarios": [
                    {
                        "scenario": s.get("scenario", ""),
                        "impactSeverity": s.get("severity", s.get("impactSeverity", "MEDIUM")),
                        "survivalScore": round(s.get("survivalProbability", 0) * 100),
                    }
                    for s in scenarios
                ],
            })
    else:
        name_tests = _deep_camel(raw_name_tests) if raw_name_tests is not None else []

    # ── survivalScores: compute tier-averaged summary ────────────
    # Frontend expects: { averageTier1, averageTier2, lowestSurvivor: { ticker, score } }
    raw_survival = _safe_json_parse(stress.survival_scores)

    # Get tier mapping from equity candidates for this screen
    candidates = (
        db.query(ISTEquityCandidate)
        .filter(ISTEquityCandidate.screen_id == screen_id)
        .all()
    )
    tier_map = {c.ticker: c.tier for c in candidates}

    if isinstance(raw_survival, list) and len(raw_survival) > 0:
        tier1_scores = [
            s.get("overallSurvival", s.get("overall_survival", 0)) * 100
            for s in raw_survival
            if isinstance(s, dict) and tier_map.get(s.get("ticker")) == 1
        ]
        tier2_scores = [
            s.get("overallSurvival", s.get("overall_survival", 0)) * 100
            for s in raw_survival
            if isinstance(s, dict) and tier_map.get(s.get("ticker")) == 2
        ]
        lowest = min(
            (s for s in raw_survival if isinstance(s, dict)),
            key=lambda s: s.get("overallSurvival", s.get("overall_survival", 1)),
            default=None,
        )
        survival_scores = {
            "averageTier1": round(sum(tier1_scores) / len(tier1_scores)) if tier1_scores else 0,
            "averageTier2": round(sum(tier2_scores) / len(tier2_scores)) if tier2_scores else 0,
            "lowestSurvivor": {
                "ticker": lowest.get("ticker", ""),
                "score": round(lowest.get("overallSurvival", lowest.get("overall_survival", 0)) * 100),
            } if lowest else None,
        }
    else:
        survival_scores = {
            "averageTier1": 0,
            "averageTier2": 0,
            "lowestSurvivor": None,
        }

    return {
        "screenId": screen_id,
        "frameworkTests": framework_tests,
        "nameTests": name_tests,
        # Backward-compatible legacy shape.
        "survivalScores": _deep_camel(raw_survival) if raw_survival is not None else [],
        # New summary shape used by the frontend.
        "survivalSummary": survival_scores,
        "createdAt": stress.created_at.isoformat() if stress.created_at else None,
    }


# ── GET /api/ist/screens/{id}/report — Get Investment Thesis Report ──────────


@router.get("/screens/{screen_id}/report")
def get_report(screen_id: int, db: Session = Depends(get_db)):
    """Get the Investment Thesis Report for a screen.

    INV-PE-01: Single query for the report record.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    report = (
        db.query(ISTReport)
        .filter(ISTReport.screen_id == screen_id)
        .first()
    )
    if not report:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "REPORT_NOT_FOUND",
                f"No report found for screen {screen_id}. "
                "Report generation may not have completed yet.",
            ),
        )

    metadata = _deep_camel(_safe_json_parse(report.report_metadata))
    return {
        "screenId": screen_id,
        # Backward-compatible legacy fields.
        "title": report.title,
        "content": report.content,
        "metadata": metadata,
        # New nested shape used by the frontend.
        "report": {
            "id": report.id,
            "title": report.title,
            "content": report.content,
            "metadata": metadata,
        },
        "createdAt": report.created_at.isoformat() if report.created_at else None,
    }


# ── GET /api/ist/screens/{id}/handoff — Get HFRT Handoff Data ───────────────


@router.get("/screens/{screen_id}/handoff")
def get_handoff(screen_id: int, db: Session = Depends(get_db)):
    """Get the HFRT handoff data for a certified screen.

    Returns Tier 1 candidates formatted for HFRT workflow bridge.

    INV-PE-01: Batch query for candidates + bottleneck names.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    if not screen.is_certified:
        raise HTTPException(
            status_code=409,
            detail=_error(
                "NOT_CERTIFIED",
                f"Screen {screen_id} is not yet certified. "
                "Complete the full IST workflow before requesting handoff data.",
            ),
        )

    # Load Tier 1 candidates with bottleneck names (INV-PE-01)
    tier1_candidates = (
        db.query(
            ISTEquityCandidate,
            ISTBottleneck.name.label("bottleneck_name"),
        )
        .outerjoin(ISTBottleneck, ISTEquityCandidate.bottleneck_id == ISTBottleneck.id)
        .filter(
            ISTEquityCandidate.screen_id == screen_id,
            ISTEquityCandidate.tier == 1,
        )
        .order_by(ISTEquityCandidate.id)
        .all()
    )

    candidates = []
    for cand, bn_name in tier1_candidates:
        candidates.append({
            "ticker": cand.ticker,
            "companyName": cand.company_name,
            "tier": cand.tier,
            "conviction": cand.conviction,
            "pillar": bn_name or "Unknown",
            "catalyst": cand.catalyst,
            "scarcityScore": _deep_camel(_safe_json_parse(cand.scarcity_score)),
        })

    return {
        "screenId": screen_id,
        "screenName": screen.name,
        "certified": True,
        "certifiedAt": screen.certified_at.isoformat() if screen.certified_at else None,
        "tier1Count": len(candidates),
        "candidates": candidates,
    }


# ── GET /api/ist/screens/{id}/certification — Get Certification Details ──────


@router.get("/screens/{screen_id}/certification")
def get_certification(screen_id: int, db: Session = Depends(get_db)):
    """Get certification gate results for a screen.

    Returns the full certification metadata written during screen_certification step,
    including Gate 3 results, invariant compliance, report metrics, and tier breakdown.

    INV-PE-01: Single query for the screen record.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise HTTPException(
            status_code=404,
            detail=_error("SCREEN_NOT_FOUND", f"No screen with id {screen_id}"),
        )

    if not screen.is_certified:
        raise HTTPException(
            status_code=409,
            detail=_error(
                "NOT_CERTIFIED",
                f"Screen {screen_id} is not yet certified. "
                "Complete the full IST workflow before requesting certification data.",
            ),
        )

    certification_raw = _safe_json_parse(screen.certification)
    if certification_raw is None:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "CERTIFICATION_NOT_FOUND",
                f"Screen {screen_id} is certified but certification data is missing.",
            ),
        )
    certification = _deep_camel(certification_raw)

    return {
        "screenId": screen_id,
        "screenName": screen.name,
        "certified": True,
        "certification": certification,
    }
