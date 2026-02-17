"""Persona Overlay endpoints -- single persona, trio pipeline, and analysis retrieval.

All endpoints under /api/personas prefix (INV-BE-01: /api/ prefix).
Error format: {"error": {"code": "...", "message": "..."}} (INV-BE-02).

POST endpoints use BackgroundTasks -- analysis runs in background, returns 202 with analysis ID.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.persona import PersonaAnalysis
from app.schemas.persona import (
    PersonaAnalysisRequest,
    TrioAnalysisRequest,
)
from app.services.persona.trio_orchestrator import run_single_persona, run_trio_analysis

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# INV-BE-01: Every router MUST use /api/ prefix
router = APIRouter(prefix="/api/personas", tags=["personas"])


def _error(code: str, message: str) -> dict:
    """Build a standard error detail dict (INV-BE-02)."""
    return {"error": {"code": code, "message": message}}


def _safe_json_parse(value: Optional[str]):
    """Safely parse a JSON string, returning None on failure."""
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def _record_to_dict(record: PersonaAnalysis) -> dict:
    """Convert a PersonaAnalysis DB record to a response dict with camelCase keys."""
    return {
        "id": record.id,
        "personaName": record.persona_name,
        "targetType": record.target_type,
        "targetId": record.target_id,
        "analysisResult": _safe_json_parse(record.analysis_result),
        "rawResponse": record.raw_response,
        "modelUsed": record.model_used,
        "tokensUsed": record.tokens_used,
        "createdAt": record.created_at.isoformat() if record.created_at else None,
    }


# ── Background task wrappers ────────────────────────────────────────────────


async def _bg_single_persona(
    persona_name: str,
    target_type: str,
    target_id: Optional[int],
    user_prompt: str,
    additional_context: Optional[str],
    placeholder_id: int,
    mode: str = "structured",
):
    """Background task: run a single persona analysis and update the placeholder record."""
    try:
        result = await run_single_persona(
            persona_name=persona_name,
            target_type=target_type,
            target_id=target_id,
            user_prompt=user_prompt,
            additional_context=additional_context,
            mode=mode,
        )
        # The run_single_persona already stored its own record.
        # Delete the placeholder and log completion.
        db = SessionLocal()
        try:
            placeholder = db.query(PersonaAnalysis).filter(
                PersonaAnalysis.id == placeholder_id
            ).first()
            if placeholder:
                # Update the placeholder with the real result data
                placeholder.analysis_result = json.dumps(result.get("analysisResult"))
                placeholder.raw_response = result.get("rawResponse")
                placeholder.model_used = result.get("modelUsed")
                db.commit()
            logger.info(
                "Single persona analysis completed: persona=%s, placeholder_id=%d, result_id=%s",
                persona_name, placeholder_id, result.get("id"),
            )
        finally:
            db.close()
    except Exception:
        logger.exception(
            "Background single persona analysis failed: persona=%s, placeholder_id=%d",
            persona_name, placeholder_id,
        )
        # Mark the placeholder as failed
        db = SessionLocal()
        try:
            placeholder = db.query(PersonaAnalysis).filter(
                PersonaAnalysis.id == placeholder_id
            ).first()
            if placeholder:
                placeholder.analysis_result = json.dumps({"error": "Analysis failed"})
                db.commit()
        finally:
            db.close()


async def _bg_trio_analysis(
    target_type: str,
    target_id: Optional[int],
    user_prompt: str,
    additional_context: Optional[str],
    placeholder_id: int,
    mode: str = "structured",
):
    """Background task: run the full trio pipeline and update the placeholder record."""
    try:
        result = await run_trio_analysis(
            target_type=target_type,
            target_id=target_id,
            user_prompt=user_prompt,
            additional_context=additional_context,
            mode=mode,
        )
        # Update placeholder with trio summary ID reference
        db = SessionLocal()
        try:
            placeholder = db.query(PersonaAnalysis).filter(
                PersonaAnalysis.id == placeholder_id
            ).first()
            if placeholder:
                summary = result.get("trio_summary", {})
                placeholder.analysis_result = json.dumps({
                    "visser_id": result.get("visser", {}).get("id"),
                    "meldrum_id": result.get("meldrum", {}).get("id"),
                    "wissner_gross_id": result.get("wissner_gross", {}).get("id"),
                    "trio_summary_id": summary.get("id"),
                    "status": "completed",
                })
                placeholder.raw_response = summary.get("rawResponse")
                placeholder.model_used = summary.get("modelUsed")
                db.commit()
            logger.info(
                "Trio analysis completed: placeholder_id=%d", placeholder_id
            )
        finally:
            db.close()
    except Exception:
        logger.exception(
            "Background trio analysis failed: placeholder_id=%d", placeholder_id
        )
        db = SessionLocal()
        try:
            placeholder = db.query(PersonaAnalysis).filter(
                PersonaAnalysis.id == placeholder_id
            ).first()
            if placeholder:
                placeholder.analysis_result = json.dumps({"error": "Trio analysis failed"})
                db.commit()
        finally:
            db.close()


# ── POST /api/personas/analyze -- Run single persona analysis ────────────────


@router.post("/analyze", status_code=202)
@limiter.limit("10/hour")
async def analyze_single_persona(
    request: Request,
    data: PersonaAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Run a single persona analysis (Visser, Meldrum, or Wissner-Gross).

    Analysis runs in the background. Returns 202 Accepted with a placeholder analysis ID
    that can be polled via GET /api/personas/analyses/{id}.

    Rate limited to 10 analyses per hour.
    """
    # Create a placeholder record to return immediately
    placeholder = PersonaAnalysis(
        persona_name=data.persona_name,
        target_type=data.target_type,
        target_id=data.target_id,
        input_context=json.dumps({
            "user_prompt": data.user_prompt,
            "status": "pending",
        }),
        analysis_result=json.dumps({"status": "pending"}),
        raw_response=None,
        model_used=None,
        tokens_used=None,
    )
    db.add(placeholder)
    db.commit()
    db.refresh(placeholder)

    # Schedule the analysis in the background
    background_tasks.add_task(
        _bg_single_persona,
        persona_name=data.persona_name,
        target_type=data.target_type,
        target_id=data.target_id,
        user_prompt=data.user_prompt,
        additional_context=data.additional_context,
        placeholder_id=placeholder.id,
        mode=data.mode,
    )

    return {
        "id": placeholder.id,
        "personaName": placeholder.persona_name,
        "targetType": placeholder.target_type,
        "targetId": placeholder.target_id,
        "status": "pending",
        "message": f"Analysis by {data.persona_name} started. Poll GET /api/personas/analyses/{placeholder.id} for results.",
    }


# ── POST /api/personas/trio -- Run trio pipeline ────────────────────────────


@router.post("/trio", status_code=202)
@limiter.limit("5/hour")
async def analyze_trio(
    request: Request,
    data: TrioAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Run the full trio pipeline (Visser | Meldrum | Wissner-Gross in parallel -> Moderator).

    Analysis runs in the background. Returns 202 Accepted with a placeholder analysis ID
    that can be polled via GET /api/personas/analyses/{id}.

    Rate limited to 5 trio analyses per hour.
    """
    # Create a placeholder record for the trio run
    placeholder = PersonaAnalysis(
        persona_name="trio_summary",
        target_type=data.target_type,
        target_id=data.target_id,
        input_context=json.dumps({
            "user_prompt": data.user_prompt,
            "status": "pending",
        }),
        analysis_result=json.dumps({"status": "pending"}),
        raw_response=None,
        model_used=None,
        tokens_used=None,
    )
    db.add(placeholder)
    db.commit()
    db.refresh(placeholder)

    # Schedule the trio analysis in the background
    background_tasks.add_task(
        _bg_trio_analysis,
        target_type=data.target_type,
        target_id=data.target_id,
        user_prompt=data.user_prompt,
        additional_context=data.additional_context,
        placeholder_id=placeholder.id,
        mode=data.mode,
    )

    return {
        "id": placeholder.id,
        "personaName": "trio_summary",
        "targetType": placeholder.target_type,
        "targetId": placeholder.target_id,
        "status": "pending",
        "message": f"Trio analysis started. Poll GET /api/personas/analyses/{placeholder.id} for results.",
    }


# ── GET /api/personas/analyses -- List analyses ─────────────────────────────


@router.get("/analyses")
def list_analyses(
    persona_name: Optional[str] = Query(
        default=None,
        alias="personaName",
        description="Filter by persona name",
    ),
    target_type: Optional[str] = Query(
        default=None,
        alias="targetType",
        description="Filter by target type",
    ),
    target_id: Optional[int] = Query(
        default=None,
        alias="targetId",
        description="Filter by target ID",
    ),
    skip: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    db: Session = Depends(get_db),
):
    """List persona analyses with optional filters.

    Supports filtering by persona_name, target_type, and target_id.
    """
    valid_personas = ("visser", "meldrum", "wissner_gross", "trio_summary")
    valid_target_types = ("ist_screen", "hfrt_project", "standalone")

    if persona_name and persona_name not in valid_personas:
        raise HTTPException(
            status_code=400,
            detail=_error(
                "INVALID_FILTER",
                f"personaName must be one of {valid_personas}",
            ),
        )

    if target_type and target_type not in valid_target_types:
        raise HTTPException(
            status_code=400,
            detail=_error(
                "INVALID_FILTER",
                f"targetType must be one of {valid_target_types}",
            ),
        )

    query = db.query(PersonaAnalysis)

    if persona_name:
        query = query.filter(PersonaAnalysis.persona_name == persona_name)
    if target_type:
        query = query.filter(PersonaAnalysis.target_type == target_type)
    if target_id is not None:
        query = query.filter(PersonaAnalysis.target_id == target_id)

    total = query.count()

    analyses = (
        query.order_by(PersonaAnalysis.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    items = [_record_to_dict(a) for a in analyses]

    return {"analyses": items, "total": total}


# ── GET /api/personas/analyses/{id} -- Get specific analysis ─────────────────


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Get a specific persona analysis by ID."""
    record = (
        db.query(PersonaAnalysis)
        .filter(PersonaAnalysis.id == analysis_id)
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "ANALYSIS_NOT_FOUND",
                f"No persona analysis with id {analysis_id}",
            ),
        )

    return _record_to_dict(record)


# ── GET /api/personas/analyses/by-target/{target_type}/{target_id} ───────────


@router.get("/analyses/by-target/{target_type}/{target_id}")
def get_analyses_by_target(
    target_type: str,
    target_id: int,
    db: Session = Depends(get_db),
):
    """Get all persona analyses for a specific target (IST screen or HFRT project).

    Returns all analyses (individual personas + trio summaries) associated
    with the given target.
    """
    valid_target_types = ("ist_screen", "hfrt_project", "standalone")
    if target_type not in valid_target_types:
        raise HTTPException(
            status_code=400,
            detail=_error(
                "INVALID_TARGET_TYPE",
                f"target_type must be one of {valid_target_types}",
            ),
        )

    analyses = (
        db.query(PersonaAnalysis)
        .filter(
            PersonaAnalysis.target_type == target_type,
            PersonaAnalysis.target_id == target_id,
        )
        .order_by(PersonaAnalysis.created_at.desc())
        .all()
    )

    items = [_record_to_dict(a) for a in analyses]

    return {
        "targetType": target_type,
        "targetId": target_id,
        "analyses": items,
        "total": len(items),
    }
