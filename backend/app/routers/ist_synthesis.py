"""IST synthesis endpoints under /api/ist/syntheses."""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ist import ISTEquityCandidate, ISTScreen
from app.models.ist_synthesis import (
    ISTSynthesis,
    ISTSynthesisDialectic,
    ISTSynthesisEquity,
    ISTSynthesisSource,
)
from app.models.workflow import WorkflowRun, WorkflowStep
from app.schemas.ist import ISTSynthesisCreate
from app.services.ist.synthesis import IST_SYNTHESIS_WORKFLOW_STEPS
from app.services.workflow_engine import cancel_workflow

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/ist/syntheses", tags=["ist-synthesis"])


def _error(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def _safe_json(value: Optional[str], fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


@router.post("", status_code=201)
@limiter.limit("5/hour")
def create_synthesis(
    request: Request,
    data: ISTSynthesisCreate,
    db: Session = Depends(get_db),
):
    """Create a new synthesis from 2+ completed certified screens."""
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
                "Maximum of 10 active workflows reached. Complete or cancel existing workflows first.",
            ),
        )

    if data.idempotency_key:
        existing = (
            db.query(ISTSynthesis)
            .filter(ISTSynthesis.idempotency_key == data.idempotency_key)
            .filter(ISTSynthesis.status != "FAILED")
            .first()
        )
        if existing:
            return {
                "id": existing.id,
                "name": existing.name,
                "status": existing.status,
                "workflowRunId": existing.workflow_run_id,
                "createdAt": existing.created_at.isoformat() if existing.created_at else None,
                "idempotent": True,
            }

    requested_ids = list(dict.fromkeys(data.screen_ids))
    screens = db.query(ISTScreen).filter(ISTScreen.id.in_(requested_ids)).all()
    if len(screens) != len(requested_ids):
        raise HTTPException(
            status_code=400,
            detail=_error("INVALID_SCREEN_IDS", "One or more screenIds do not exist."),
        )

    invalid_state = [s.id for s in screens if s.status != "COMPLETED"]
    if invalid_state:
        raise HTTPException(
            status_code=409,
            detail=_error(
                "SCREENS_NOT_COMPLETED",
                f"All source screens must be COMPLETED. Invalid: {invalid_state}",
            ),
        )

    uncertified = [s.id for s in screens if not s.is_certified]
    if uncertified:
        raise HTTPException(
            status_code=409,
            detail=_error(
                "SCREENS_NOT_CERTIFIED",
                f"All source screens must be certified. Invalid: {uncertified}",
            ),
        )

    warning = None
    themes: set[str] = set()
    for screen in screens:
        brief = _safe_json(screen.screening_brief, {})
        extraction = _safe_json(screen.content_extraction, {})
        hypothesis = brief.get("hypothesis") if isinstance(brief, dict) else None
        if hypothesis:
            themes.add(str(hypothesis)[:50])
        extraction_themes = extraction.get("themes") if isinstance(extraction, dict) else None
        if isinstance(extraction_themes, list):
            for theme in extraction_themes:
                if isinstance(theme, str):
                    themes.add(theme)

    if len(themes) < 2:
        warning = (
            "Source screens appear to share similar themes. "
            "Synthesis works best with thematically diverse screens."
        )

    run = WorkflowRun(
        workflow_type="IST_SYNTHESIS",
        name=data.name,
        status="PENDING",
        current_phase=0,
        auto_advance=data.auto_advance,
    )
    db.add(run)
    db.flush()

    synthesis = ISTSynthesis(
        name=data.name,
        status="PENDING",
        workflow_run_id=run.id,
        idempotency_key=data.idempotency_key,
    )
    db.add(synthesis)
    db.flush()

    for screen in screens:
        tier_counts = (
            db.query(
                ISTEquityCandidate.tier,
                func.count(ISTEquityCandidate.id).label("cnt"),
            )
            .filter(ISTEquityCandidate.screen_id == screen.id)
            .group_by(ISTEquityCandidate.tier)
            .all()
        )
        breakdown = {tier: 0 for tier in [1, 2, 3]}
        for row in tier_counts:
            breakdown[row.tier] = row.cnt

        brief = _safe_json(screen.screening_brief, {})
        extraction = _safe_json(screen.content_extraction, {})
        primary_theme = None
        if isinstance(brief, dict):
            primary_theme = brief.get("hypothesis")
        if not primary_theme and isinstance(extraction, dict):
            themes = extraction.get("themes")
            if isinstance(themes, list) and themes:
                primary_theme = themes[0]

        db.add(
            ISTSynthesisSource(
                synthesis_id=synthesis.id,
                screen_id=screen.id,
                screen_name=screen.name,
                tier1_count=breakdown[1],
                tier2_count=breakdown[2],
                tier3_count=breakdown[3],
                primary_theme=primary_theme,
            )
        )

    for step_def in IST_SYNTHESIS_WORKFLOW_STEPS:
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
            )
        )

    db.commit()
    db.refresh(synthesis)

    response = {
        "id": synthesis.id,
        "name": synthesis.name,
        "status": synthesis.status,
        "workflowRunId": synthesis.workflow_run_id,
        "createdAt": synthesis.created_at.isoformat() if synthesis.created_at else None,
    }
    if warning:
        response["warning"] = warning
    return response


@router.get("")
def list_syntheses(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List synthesis runs."""
    valid_status = ("PENDING", "INGESTING", "ANALYZING", "DIALECTIC", "SYNTHESIZING", "COMPLETED", "FAILED")
    query = db.query(ISTSynthesis)

    if status:
        if status not in valid_status:
            raise HTTPException(
                status_code=400,
                detail=_error("INVALID_FILTER", f"status must be one of {valid_status}"),
            )
        query = query.filter(ISTSynthesis.status == status)

    total = query.count()
    rows = (
        query.order_by(ISTSynthesis.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    synthesis_ids = [row.id for row in rows]
    source_counts = {}
    if synthesis_ids:
        source_rows = (
            db.query(ISTSynthesisSource.synthesis_id, func.count(ISTSynthesisSource.id).label("cnt"))
            .filter(ISTSynthesisSource.synthesis_id.in_(synthesis_ids))
            .group_by(ISTSynthesisSource.synthesis_id)
            .all()
        )
        source_counts = {row.synthesis_id: row.cnt for row in source_rows}

    items = []
    for row in rows:
        tier_changes = _safe_json(row.tier_changes, [])
        items.append(
            {
                "id": row.id,
                "name": row.name,
                "status": row.status,
                "workflowRunId": row.workflow_run_id,
                "sourceScreenCount": source_counts.get(row.id, 0),
                "tierChangeCount": len(tier_changes) if isinstance(tier_changes, list) else 0,
                "createdAt": row.created_at.isoformat() if row.created_at else None,
                "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
            }
        )

    return {"syntheses": items, "total": total}


@router.get("/{synthesis_id}")
def get_synthesis(synthesis_id: int, db: Session = Depends(get_db)):
    """Get synthesis detail."""
    synthesis = db.query(ISTSynthesis).filter(ISTSynthesis.id == synthesis_id).first()
    if not synthesis:
        raise HTTPException(
            status_code=404,
            detail=_error("SYNTHESIS_NOT_FOUND", f"No synthesis with id {synthesis_id}"),
        )

    return {
        "id": synthesis.id,
        "name": synthesis.name,
        "status": synthesis.status,
        "workflowRunId": synthesis.workflow_run_id,
        "overlapMatrix": _safe_json(synthesis.overlap_matrix, []),
        "thesisInteractions": _safe_json(synthesis.thesis_interactions, []),
        "tierChanges": _safe_json(synthesis.tier_changes, []),
        "combinedBrief": _safe_json(synthesis.combined_brief, {}),
        "report": synthesis.combined_report,
        "reportMetadata": _safe_json(synthesis.report_metadata, {}),
        "certification": _safe_json(synthesis.certification, {}),
        "hfrtHandoff": _safe_json(synthesis.hfrt_handoff, {}),
        "isCertified": bool(synthesis.is_certified),
        "certifiedAt": synthesis.certified_at.isoformat() if synthesis.certified_at else None,
        "createdAt": synthesis.created_at.isoformat() if synthesis.created_at else None,
        "updatedAt": synthesis.updated_at.isoformat() if synthesis.updated_at else None,
    }


@router.delete("/{synthesis_id}")
async def delete_synthesis(synthesis_id: int, db: Session = Depends(get_db)):
    """Delete synthesis and associated workflow."""
    synthesis = db.query(ISTSynthesis).filter(ISTSynthesis.id == synthesis_id).first()
    if not synthesis:
        raise HTTPException(
            status_code=404,
            detail=_error("SYNTHESIS_NOT_FOUND", f"No synthesis with id {synthesis_id}"),
        )

    run = db.query(WorkflowRun).filter(WorkflowRun.id == synthesis.workflow_run_id).first()
    if run and run.status in ("RUNNING", "PAUSED", "PENDING"):
        try:
            await cancel_workflow(run.id)
        except Exception:
            pass

    if run:
        db.query(WorkflowStep).filter(WorkflowStep.workflow_run_id == run.id).delete()
        db.delete(run)

    db.delete(synthesis)
    db.commit()

    return {"message": f"Synthesis {synthesis_id} deleted"}


@router.get("/{synthesis_id}/sources")
def get_synthesis_sources(synthesis_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(ISTSynthesisSource)
        .filter(ISTSynthesisSource.synthesis_id == synthesis_id)
        .order_by(ISTSynthesisSource.id)
        .all()
    )
    return {
        "synthesisId": synthesis_id,
        "sources": [
            {
                "id": row.id,
                "screenId": row.screen_id,
                "screenName": row.screen_name,
                "tier1Count": row.tier1_count,
                "tier2Count": row.tier2_count,
                "tier3Count": row.tier3_count,
                "primaryTheme": row.primary_theme,
            }
            for row in rows
        ],
    }


@router.get("/{synthesis_id}/overlap")
def get_synthesis_overlap(synthesis_id: int, db: Session = Depends(get_db)):
    synthesis = db.query(ISTSynthesis).filter(ISTSynthesis.id == synthesis_id).first()
    if not synthesis:
        raise HTTPException(status_code=404, detail=_error("SYNTHESIS_NOT_FOUND", "Not found"))
    return {"synthesisId": synthesis_id, "overlap": _safe_json(synthesis.overlap_matrix, [])}


@router.get("/{synthesis_id}/interactions")
def get_synthesis_interactions(synthesis_id: int, db: Session = Depends(get_db)):
    synthesis = db.query(ISTSynthesis).filter(ISTSynthesis.id == synthesis_id).first()
    if not synthesis:
        raise HTTPException(status_code=404, detail=_error("SYNTHESIS_NOT_FOUND", "Not found"))
    return {"synthesisId": synthesis_id, "interactions": _safe_json(synthesis.thesis_interactions, [])}


@router.get("/{synthesis_id}/tier-changes")
def get_synthesis_tier_changes(synthesis_id: int, db: Session = Depends(get_db)):
    synthesis = db.query(ISTSynthesis).filter(ISTSynthesis.id == synthesis_id).first()
    if not synthesis:
        raise HTTPException(status_code=404, detail=_error("SYNTHESIS_NOT_FOUND", "Not found"))
    return {"synthesisId": synthesis_id, "tierChanges": _safe_json(synthesis.tier_changes, [])}


@router.get("/{synthesis_id}/equities")
def get_synthesis_equities(synthesis_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(ISTSynthesisEquity)
        .filter(ISTSynthesisEquity.synthesis_id == synthesis_id)
        .order_by(ISTSynthesisEquity.new_tier, ISTSynthesisEquity.ticker)
        .all()
    )
    return {
        "synthesisId": synthesis_id,
        "equities": [
            {
                "id": row.id,
                "ticker": row.ticker,
                "companyName": row.company_name,
                "originalTier": row.original_tier,
                "newTier": row.new_tier,
                "tierChanged": bool(row.tier_changed),
                "tierChangeRationale": row.tier_change_rationale,
                "sourceScreenCount": row.source_screen_count,
                "sourceScreenIds": _safe_json(row.source_screen_ids, []),
                "combinedScarcityScore": _safe_json(row.combined_scarcity_score, {}),
                "combinedThesis": row.combined_thesis,
                "combinedCatalyst": row.combined_catalyst,
                "conviction": row.conviction,
            }
            for row in rows
        ],
    }


@router.get("/{synthesis_id}/dialectic/{side}")
def get_synthesis_dialectic(synthesis_id: int, side: str, db: Session = Depends(get_db)):
    normalized = side.upper()
    if normalized not in ("OPTIMIST", "PESSIMIST", "SYNTHESIS"):
        raise HTTPException(
            status_code=400,
            detail=_error("INVALID_SIDE", "side must be OPTIMIST, PESSIMIST, or SYNTHESIS"),
        )

    review = (
        db.query(ISTSynthesisDialectic)
        .filter(
            ISTSynthesisDialectic.synthesis_id == synthesis_id,
            ISTSynthesisDialectic.side == normalized,
        )
        .first()
    )
    if not review:
        raise HTTPException(
            status_code=404,
            detail=_error("DIALECTIC_NOT_FOUND", f"No {normalized} dialectic found"),
        )

    return {
        "synthesisId": synthesis_id,
        "side": normalized,
        "content": _safe_json(review.content, {}),
        "createdAt": review.created_at.isoformat() if review.created_at else None,
    }


@router.get("/{synthesis_id}/report")
def get_synthesis_report(synthesis_id: int, db: Session = Depends(get_db)):
    synthesis = db.query(ISTSynthesis).filter(ISTSynthesis.id == synthesis_id).first()
    if not synthesis:
        raise HTTPException(status_code=404, detail=_error("SYNTHESIS_NOT_FOUND", "Not found"))

    if not synthesis.combined_report:
        raise HTTPException(
            status_code=404,
            detail=_error("REPORT_NOT_FOUND", "Synthesis report not generated yet."),
        )

    return {
        "synthesisId": synthesis_id,
        "report": synthesis.combined_report,
        "metadata": _safe_json(synthesis.report_metadata, {}),
    }


@router.get("/{synthesis_id}/handoff")
def get_synthesis_handoff(synthesis_id: int, db: Session = Depends(get_db)):
    synthesis = db.query(ISTSynthesis).filter(ISTSynthesis.id == synthesis_id).first()
    if not synthesis:
        raise HTTPException(status_code=404, detail=_error("SYNTHESIS_NOT_FOUND", "Not found"))

    if not synthesis.hfrt_handoff:
        raise HTTPException(
            status_code=404,
            detail=_error("HANDOFF_NOT_FOUND", "Synthesis handoff not generated yet."),
        )

    return {
        "synthesisId": synthesis_id,
        "handoff": _safe_json(synthesis.hfrt_handoff, {}),
    }
