"""HFRT (Hedge Fund Research Team) endpoints — project CRUD, templates, workflow control.

All endpoints under /api/hfrt prefix (INV-BE-01: /api/ prefix).
Error format: {"error": {"code": "...", "message": "..."}} (INV-BE-02).
Includes Gap B1 (readiness), B3 (invariants), B5 (citations), B6 (isolation audit).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hfrt import (
    HFRTDialecticReview,
    HFRTProject,
    HFRTSECFiling,
    HFRTTemplate,
)
from app.models.workflow import WorkflowRun, WorkflowStep
from app.schemas.hfrt import HFRTProjectCreate
from app.services.hfrt.citation_validator import validate_citations
from app.services.hfrt.invariant_checker import audit_dialectic_isolation, check_all_invariants
from app.services.hfrt.startup_check import verify_hfrt_readiness
from app.services.workflow_engine import cancel_workflow, start_workflow

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# INV-BE-01: Every router MUST use /api/ prefix
router = APIRouter(prefix="/api/hfrt", tags=["hfrt"])


# ── HFRT workflow step definitions (24 steps across 5 phases) ────────────────
# Gap 1: external_validation inserted at step_order 14 (after dd_sufficiency_gate).
# All subsequent steps bumped by 1 (total 23 → 24 steps).

HFRT_WORKFLOW_STEPS = [
    # Phase 1: Screening
    {"step_name": "idea_screen", "phase": 1, "phase_name": "Screening", "step_order": 1, "depends_on": [], "model": "sonnet"},
    # Phase 2: Deep Research
    {"step_name": "company_overview", "phase": 2, "phase_name": "Deep Research", "step_order": 2, "depends_on": ["idea_screen"], "model": "sonnet"},
    {"step_name": "business_model", "phase": 2, "phase_name": "Deep Research", "step_order": 3, "depends_on": ["company_overview"], "model": "opus"},
    {"step_name": "competitive_position", "phase": 2, "phase_name": "Deep Research", "step_order": 4, "depends_on": ["company_overview"], "model": "sonnet"},
    {"step_name": "industry_analysis", "phase": 2, "phase_name": "Deep Research", "step_order": 5, "depends_on": ["company_overview"], "model": "sonnet"},
    {"step_name": "financial_analysis", "phase": 2, "phase_name": "Deep Research", "step_order": 6, "depends_on": ["company_overview"], "model": "sonnet"},
    {"step_name": "valuation", "phase": 2, "phase_name": "Deep Research", "step_order": 7, "depends_on": ["financial_analysis", "industry_analysis"], "model": "sonnet"},
    {"step_name": "research_sufficiency_gate", "phase": 2, "phase_name": "Deep Research", "step_order": 8, "depends_on": ["valuation", "competitive_position", "industry_analysis"], "model": "none", "retry_strategy": "with_parent"},
    # Phase 3: Risk & Due Diligence
    {"step_name": "fetch_sec_filings", "phase": 3, "phase_name": "Risk & Due Diligence", "step_order": 9, "depends_on": ["research_sufficiency_gate"], "model": "none"},
    {"step_name": "management_assessment", "phase": 3, "phase_name": "Risk & Due Diligence", "step_order": 10, "depends_on": ["fetch_sec_filings"], "model": "opus"},
    {"step_name": "risk_analysis", "phase": 3, "phase_name": "Risk & Due Diligence", "step_order": 11, "depends_on": ["fetch_sec_filings"], "model": "opus"},
    {"step_name": "quality_of_earnings", "phase": 3, "phase_name": "Risk & Due Diligence", "step_order": 12, "depends_on": ["fetch_sec_filings"], "model": "opus"},
    {"step_name": "dd_sufficiency_gate", "phase": 3, "phase_name": "Risk & Due Diligence", "step_order": 13, "depends_on": ["management_assessment", "risk_analysis", "quality_of_earnings"], "model": "none", "retry_strategy": "with_parent"},
    # Gap 1: External validation (Perplexity-grounded) — runs in parallel with dialectic
    {"step_name": "external_validation", "phase": 3, "phase_name": "Risk & Due Diligence", "step_order": 14, "depends_on": ["dd_sufficiency_gate"], "model": "sonnet"},
    # Phase 4: Dialectic
    {"step_name": "bull_case", "phase": 4, "phase_name": "Dialectic", "step_order": 15, "depends_on": ["dd_sufficiency_gate"], "model": "opus"},
    {"step_name": "bear_case", "phase": 4, "phase_name": "Dialectic", "step_order": 16, "depends_on": ["dd_sufficiency_gate"], "model": "opus"},
    # Phase 5: Synthesis
    {"step_name": "catalyst_analysis", "phase": 5, "phase_name": "Synthesis", "step_order": 17, "depends_on": ["bull_case", "bear_case"], "model": "sonnet"},
    {"step_name": "investment_thesis", "phase": 5, "phase_name": "Synthesis", "step_order": 18, "depends_on": ["bull_case", "bear_case"], "model": "opus"},
    {"step_name": "bull_synthesis", "phase": 5, "phase_name": "Synthesis", "step_order": 19, "depends_on": ["investment_thesis"], "model": "sonnet"},
    {"step_name": "bear_synthesis", "phase": 5, "phase_name": "Synthesis", "step_order": 20, "depends_on": ["investment_thesis"], "model": "sonnet"},
    {"step_name": "thesis_coherence_gate", "phase": 5, "phase_name": "Synthesis", "step_order": 21, "depends_on": ["bull_synthesis", "bear_synthesis", "catalyst_analysis"], "model": "none", "retry_strategy": "with_parent"},
    {"step_name": "investment_memo", "phase": 5, "phase_name": "Synthesis", "step_order": 22, "depends_on": ["thesis_coherence_gate"], "model": "sonnet"},
    {"step_name": "research_certification", "phase": 5, "phase_name": "Synthesis", "step_order": 23, "depends_on": ["thesis_coherence_gate"], "model": "sonnet"},
    {"step_name": "complete", "phase": 5, "phase_name": "Synthesis", "step_order": 24, "depends_on": ["investment_memo", "research_certification"], "model": "none"},
]

# Template definitions: number -> name
HFRT_TEMPLATES = {
    0: "Idea Screen",
    1: "Company Overview",
    2: "Business Model",
    3: "Competitive Position",
    4: "Industry Analysis",
    5: "Financial Analysis",
    6: "Valuation",
    7: "Management Assessment",
    8: "Risk Analysis",
    9: "Quality of Earnings",
    10: "Catalyst Analysis",
    11: "Investment Thesis",
    12: "Bull Synthesis",
    13: "Bear Synthesis",
    14: "Investment Memo",
}


def _error(code: str, message: str) -> dict:
    """Build a standard error detail dict (INV-BE-02)."""
    return {"error": {"code": code, "message": message}}


# ── POST /api/hfrt/projects — Create HFRT Project ───────────────────────────


@router.post("/projects", status_code=201)
@limiter.limit("5/hour")
def create_project(
    request: Request,
    data: HFRTProjectCreate,
    db: Session = Depends(get_db),
):
    """Create a new HFRT research project for a ticker.

    Creates HFRTProject, WorkflowRun with 24 steps, and 15 empty templates.
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
        workflow_type="HFRT",
        name=f"HFRT Research: {data.ticker}",
        status="PENDING",
        current_phase=0,
        auto_advance=data.auto_advance,
    )
    db.add(run)
    db.flush()

    # 2. Create the HFRTProject
    project = HFRTProject(
        workflow_run_id=run.id,
        ticker=data.ticker,
        status="PENDING",
    )
    db.add(project)
    db.flush()

    # 3. Create all 23 HFRT workflow steps
    for step_def in HFRT_WORKFLOW_STEPS:
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

    # 4. Create all 15 empty templates
    for num, name in HFRT_TEMPLATES.items():
        template = HFRTTemplate(
            project_id=project.id,
            template_number=num,
            template_name=name,
            status="EMPTY",
        )
        db.add(template)

    db.commit()
    db.refresh(project)
    db.refresh(run)

    return {
        "id": project.id,
        "workflowRunId": run.id,
        "ticker": project.ticker,
        "companyName": project.company_name,
        "status": project.status,
        "createdAt": project.created_at.isoformat() if project.created_at else None,
    }


# ── DELETE /api/hfrt/projects/{project_id} — Delete HFRT Project ────────────


@router.delete("/projects/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete an HFRT project and its associated workflow run.

    If the workflow is active, cancels it first. CASCADE handles child records.
    """
    project = db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", f"Project {project_id} not found"),
        )

    # Cancel active workflow if running
    run = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.id == project.workflow_run_id)
        .first()
    )
    if run and run.status in ("RUNNING", "PAUSED", "PENDING"):
        try:
            await cancel_workflow(run.id)
        except Exception:
            pass  # Best-effort cancel before delete

    # Delete child records explicitly (templates, filings, dialectic reviews)
    db.query(HFRTTemplate).filter(HFRTTemplate.project_id == project_id).delete()
    db.query(HFRTSECFiling).filter(HFRTSECFiling.project_id == project_id).delete()
    db.query(HFRTDialecticReview).filter(HFRTDialecticReview.project_id == project_id).delete()

    # Delete workflow steps and run
    if run:
        db.query(WorkflowStep).filter(WorkflowStep.workflow_run_id == run.id).delete()
        db.delete(run)
    db.delete(project)
    db.commit()

    return {"message": f"Project {project_id} deleted"}


# ── GET /api/hfrt/projects/{project_id}/inputs — View Project Inputs ────────


@router.get("/projects/{project_id}/inputs")
def get_project_inputs(project_id: int, db: Session = Depends(get_db)):
    """Get the original user inputs that created this project."""
    project = db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", f"Project {project_id} not found"),
        )

    return {
        "id": project.id,
        "ticker": project.ticker,
        "source": project.source,
        "istScreenId": project.ist_screen_id,
        "createdAt": project.created_at.isoformat() if project.created_at else None,
    }


# ── POST /api/hfrt/projects/{project_id}/rerun — Rerun HFRT Project ────────


@router.post("/projects/{project_id}/rerun")
async def rerun_project(project_id: int, db: Session = Depends(get_db)):
    """Reset and rerun an HFRT project's workflow from scratch.

    Cancels any active workflow, deletes all child data, resets the project
    and workflow run to PENDING, and recreates all 23 steps + 15 templates.
    """
    project = db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", f"Project {project_id} not found"),
        )

    run = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.id == project.workflow_run_id)
        .first()
    )
    if not run:
        raise HTTPException(
            status_code=404,
            detail=_error("WORKFLOW_NOT_FOUND", "No workflow run associated with this project."),
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

    # Delete child records
    db.query(HFRTDialecticReview).filter(HFRTDialecticReview.project_id == project_id).delete()
    db.query(HFRTSECFiling).filter(HFRTSECFiling.project_id == project_id).delete()
    db.query(HFRTTemplate).filter(HFRTTemplate.project_id == project_id).delete()

    # Delete old workflow steps
    db.query(WorkflowStep).filter(WorkflowStep.workflow_run_id == run.id).delete()

    # Reset project fields
    project.status = "PENDING"
    project.company_name = None
    project.sector = None
    project.exchange = None
    project.market_cap = None
    project.investable = False
    project.investable_verdict = None
    project.conviction_score = None
    project.position_tier = None
    project.recommendation = None
    project.is_certified = False
    project.certified_at = None
    project.invariant_results = None
    project.updated_at = datetime.now(timezone.utc)

    # Reset workflow run
    run.status = "PENDING"
    run.current_phase = 0
    run.error_message = None
    run.started_at = None
    run.completed_at = None
    run.updated_at = datetime.now(timezone.utc)

    # Recreate all 24 HFRT workflow steps
    for step_def in HFRT_WORKFLOW_STEPS:
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

    # Recreate all 15 empty templates
    for num, name in HFRT_TEMPLATES.items():
        template = HFRTTemplate(
            project_id=project.id,
            template_number=num,
            template_name=name,
            status="EMPTY",
        )
        db.add(template)

    db.commit()
    db.refresh(project)
    db.refresh(run)

    return {
        "id": project.id,
        "workflowRunId": run.id,
        "ticker": project.ticker,
        "status": project.status,
        "message": "Project reset and ready to rerun",
    }


# ── GET /api/hfrt/projects — List HFRT Projects ─────────────────────────────


@router.get("/projects")
def list_projects(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
):
    """List all HFRT projects with summary info."""
    valid_statuses = (
        "PENDING", "SCREENING", "RESEARCHING", "DUE_DILIGENCE",
        "DIALECTIC", "SYNTHESIZING", "COMPLETED", "FAILED", "NOT_INVESTABLE",
    )

    query = db.query(HFRTProject)

    if status:
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=_error("INVALID_STATUS", f"status must be one of {valid_statuses}"),
            )
        query = query.filter(HFRTProject.status == status)

    total = query.count()

    # Subquery for template count (INV-PE-01: avoid N+1)
    templates_populated_sq = (
        db.query(
            HFRTTemplate.project_id,
            func.count(HFRTTemplate.id).label("populated_count"),
        )
        .filter(HFRTTemplate.status == "POPULATED")
        .group_by(HFRTTemplate.project_id)
        .subquery()
    )

    projects = (
        query
        .outerjoin(
            templates_populated_sq,
            HFRTProject.id == templates_populated_sq.c.project_id,
        )
        .add_columns(
            func.coalesce(templates_populated_sq.c.populated_count, 0).label(
                "templates_populated"
            ),
        )
        .outerjoin(WorkflowRun, HFRTProject.workflow_run_id == WorkflowRun.id)
        .add_columns(
            func.coalesce(WorkflowRun.current_phase, 0).label("current_phase"),
        )
        .order_by(HFRTProject.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for project, templates_populated, current_phase in projects:
        items.append({
            "id": project.id,
            "ticker": project.ticker,
            "companyName": project.company_name,
            "status": project.status,
            "workflowRunId": project.workflow_run_id,
            "sector": project.sector,
            "marketCap": project.market_cap,
            "investable": bool(project.investable),
            "convictionScore": project.conviction_score,
            "recommendation": project.recommendation,
            "currentPhase": current_phase,
            "templatesPopulated": templates_populated,
            "createdAt": project.created_at.isoformat() if project.created_at else None,
            "updatedAt": project.updated_at.isoformat() if project.updated_at else None,
        })

    return {"projects": items, "total": total}


# ── GET /api/hfrt/projects/{project_id} — Get Project Detail ────────────────


@router.get("/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get full HFRT project detail."""
    project = db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", f"Project {project_id} not found"),
        )

    run = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.id == project.workflow_run_id)
        .first()
    )

    # Parse stored invariant results
    invariant_results = None
    if project.invariant_results:
        try:
            invariant_results = json.loads(project.invariant_results)
        except (ValueError, TypeError):
            pass

    return {
        "id": project.id,
        "workflowRunId": project.workflow_run_id,
        "ticker": project.ticker,
        "companyName": project.company_name,
        "status": project.status,
        "sector": project.sector,
        "exchange": project.exchange,
        "marketCap": project.market_cap,
        "investable": bool(project.investable),
        "investableVerdict": project.investable_verdict,
        "convictionScore": project.conviction_score,
        "positionTier": project.position_tier,
        "recommendation": project.recommendation,
        "isCertified": bool(project.is_certified),
        "certifiedAt": project.certified_at.isoformat() if project.certified_at else None,
        "invariantResults": invariant_results,
        "currentPhase": run.current_phase if run else 0,
        "createdAt": project.created_at.isoformat() if project.created_at else None,
        "updatedAt": project.updated_at.isoformat() if project.updated_at else None,
    }


# ── GET /api/hfrt/projects/{project_id}/templates — List All Templates ──────


@router.get("/projects/{project_id}/templates")
def list_templates(project_id: int, db: Session = Depends(get_db)):
    """Get all 15 templates for a project."""
    project = db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", f"Project {project_id} not found"),
        )

    templates = (
        db.query(HFRTTemplate)
        .filter(HFRTTemplate.project_id == project_id)
        .order_by(HFRTTemplate.template_number)
        .all()
    )

    items = []
    for t in templates:
        data = None
        if t.data:
            try:
                data = json.loads(t.data)
            except (ValueError, TypeError):
                data = None
        items.append({
            "templateNumber": t.template_number,
            "templateName": t.template_name,
            "status": t.status,
            "data": data,
            "updatedAt": t.updated_at.isoformat() if t.updated_at else None,
        })

    return {"projectId": project_id, "templates": items}


# ── GET /api/hfrt/projects/{project_id}/templates/{number} — Single Template ─


@router.get("/projects/{project_id}/templates/{template_number}")
def get_template(
    project_id: int, template_number: int, db: Session = Depends(get_db)
):
    """Get a single template by number."""
    if template_number < 0 or template_number > 14:
        raise HTTPException(
            status_code=400,
            detail=_error("INVALID_TEMPLATE", "template_number must be 0-14"),
        )

    template = (
        db.query(HFRTTemplate)
        .filter(
            HFRTTemplate.project_id == project_id,
            HFRTTemplate.template_number == template_number,
        )
        .first()
    )
    if not template:
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", f"Template {template_number} not found"),
        )

    data = None
    if template.data:
        try:
            data = json.loads(template.data)
        except (ValueError, TypeError):
            data = None

    return {
        "templateNumber": template.template_number,
        "templateName": template.template_name,
        "status": template.status,
        "data": data,
        "updatedAt": template.updated_at.isoformat() if template.updated_at else None,
    }


# ── GET /api/hfrt/projects/{project_id}/sec-filings — List SEC Filings ──────


@router.get("/projects/{project_id}/sec-filings")
def list_sec_filings(project_id: int, db: Session = Depends(get_db)):
    """List cached SEC filings for a project."""
    project = db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", f"Project {project_id} not found"),
        )

    filings = (
        db.query(HFRTSECFiling)
        .filter(HFRTSECFiling.project_id == project_id)
        .order_by(HFRTSECFiling.filing_date.desc())
        .all()
    )

    items = []
    for f in filings:
        sections = None
        if f.sections:
            try:
                sections = json.loads(f.sections)
            except (ValueError, TypeError):
                sections = None
        items.append({
            "id": f.id,
            "ticker": f.ticker,
            "filingType": f.filing_type,
            "filingDate": f.filing_date,
            "accessionNumber": f.accession_number,
            "url": f.url,
            "sections": list(sections.keys()) if sections else [],
            "fetchedAt": f.fetched_at.isoformat() if f.fetched_at else None,
        })

    return {"projectId": project_id, "filings": items}


# ── GET /api/hfrt/projects/{project_id}/dialectic/{side} — Get Dialectic ────


@router.get("/projects/{project_id}/dialectic/{side}")
def get_dialectic(
    project_id: int, side: str, db: Session = Depends(get_db)
):
    """Get a dialectic review (BULL or BEAR)."""
    side = side.upper()
    if side not in ("BULL", "BEAR"):
        raise HTTPException(
            status_code=400,
            detail=_error("INVALID_SIDE", "side must be BULL or BEAR"),
        )

    review = (
        db.query(HFRTDialecticReview)
        .filter(
            HFRTDialecticReview.project_id == project_id,
            HFRTDialecticReview.side == side,
        )
        .first()
    )
    if not review:
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", f"{side} review not found for project {project_id}"),
        )

    content = None
    if review.content:
        try:
            content = json.loads(review.content)
        except (ValueError, TypeError):
            content = None

    return {
        "projectId": project_id,
        "side": review.side,
        "content": content,
        "createdAt": review.created_at.isoformat() if review.created_at else None,
    }


# ── GET /api/hfrt/projects/{project_id}/invariants — Invariant Check ────────


@router.get("/projects/{project_id}/invariants")
def get_invariants(
    project_id: int,
    live: bool = Query(default=False, description="Run live check instead of using stored results"),
    db: Session = Depends(get_db),
):
    """Get HFRT invariant check results (Gap B3).

    By default returns stored results from research_certification step.
    Pass ?live=true to run a fresh check via the centralized invariant checker.
    """
    project = db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", f"Project {project_id} not found"),
        )

    invariants: list[dict] = []

    if live:
        # Run live invariant check
        invariants = check_all_invariants(project_id)
    elif project.invariant_results:
        # Use stored results from project column
        try:
            invariants = json.loads(project.invariant_results)
        except (ValueError, TypeError):
            invariants = []

    if not invariants:
        # Fallback: check memo template for legacy stored results
        memo_template = (
            db.query(HFRTTemplate)
            .filter(
                HFRTTemplate.project_id == project_id,
                HFRTTemplate.template_number == 14,
            )
            .first()
        )
        if memo_template and memo_template.data:
            try:
                data = json.loads(memo_template.data)
                invariants = data.get("invariants", [])
            except (ValueError, TypeError):
                pass

    all_passed = all(inv.get("status") == "PASS" for inv in invariants) if invariants else True
    pass_count = sum(1 for inv in invariants if inv.get("status") == "PASS")
    fail_count = sum(1 for inv in invariants if inv.get("status") == "FAIL")

    return {
        "projectId": project_id,
        "invariants": invariants,
        "allPassed": all_passed,
        "passCount": pass_count,
        "failCount": fail_count,
    }


# ── GET /api/hfrt/readiness — Startup Readiness Check (Gap B1) ──────────────


@router.get("/readiness")
def get_readiness(
    force: bool = Query(default=False, description="Force re-check (bypass cache)"),
):
    """Check HFRT startup readiness (Gap B1).

    Verifies database, API keys, SEC agent, and framework files are available.
    Result is cached until app restart unless ?force=true.
    """
    result = verify_hfrt_readiness(force=force)
    return {
        "ready": result.ready,
        "issues": result.issues,
        "checks": result.checks,
    }


# ── GET /api/hfrt/projects/{id}/citations/{template_num} — Citation Validation (Gap B5) ─


@router.get("/projects/{project_id}/citations/{template_number}")
def get_citations(
    project_id: int,
    template_number: int,
    db: Session = Depends(get_db),
):
    """Validate citations for a specific template (Gap B5).

    Scans template content for quantitative claims and checks for nearby citations.
    """
    project = db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", f"Project {project_id} not found"),
        )

    if template_number < 0 or template_number > 14:
        raise HTTPException(
            status_code=400,
            detail=_error("INVALID_TEMPLATE", "template_number must be 0-14"),
        )

    result = validate_citations(project_id, template_number)
    return {
        "projectId": project_id,
        "templateNumber": template_number,
        **result,
    }


# ── GET /api/hfrt/projects/{id}/dialectic/audit — Isolation Audit (Gap B6) ──


@router.get("/projects/{project_id}/dialectic/audit")
def get_dialectic_audit(project_id: int, db: Session = Depends(get_db)):
    """Audit dialectic isolation between bull and bear cases (Gap B6).

    Checks for cross-references and shared unique phrases that indicate
    the bull and bear analysts saw each other's work.
    """
    project = db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", f"Project {project_id} not found"),
        )

    bull = (
        db.query(HFRTDialecticReview)
        .filter(
            HFRTDialecticReview.project_id == project_id,
            HFRTDialecticReview.side == "BULL",
        )
        .first()
    )
    bear = (
        db.query(HFRTDialecticReview)
        .filter(
            HFRTDialecticReview.project_id == project_id,
            HFRTDialecticReview.side == "BEAR",
        )
        .first()
    )

    if not bull or not bear:
        raise HTTPException(
            status_code=404,
            detail=_error(
                "INCOMPLETE_DIALECTIC",
                "Both bull and bear reviews must exist before auditing isolation",
            ),
        )

    result = audit_dialectic_isolation(bull.content, bear.content)
    return {
        "projectId": project_id,
        "isIsolated": result["is_isolated"],
        "contaminationEvidence": result["contamination_evidence"],
    }


# ── GET /api/hfrt/projects/{id}/validation — External Validation (Gap 1) ────


@router.get("/projects/{project_id}/validation")
def get_validation(project_id: int, db: Session = Depends(get_db)):
    """Get external validation results for a project (Gap 1).

    Returns Perplexity-grounded fact-checking results with verdict breakdown:
      confirmed, partially_confirmed, contradicted, unvalidatable.
    """
    project = db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", f"Project {project_id} not found"),
        )

    if not project.external_validation_results:
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", "External validation has not been run for this project"),
        )

    try:
        results = json.loads(project.external_validation_results)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=500,
            detail=_error("PARSE_ERROR", "Could not parse stored validation results"),
        )

    return {
        "projectId": project_id,
        "claimsValidated": results.get("claims_validated", 0),
        "confirmed": results.get("confirmed", 0),
        "partiallyConfirmed": results.get("partially_confirmed", 0),
        "contradicted": results.get("contradicted", 0),
        "unvalidatable": results.get("unvalidatable", 0),
        "overallConfidence": results.get("overall_confidence", ""),
        "keyContradictions": results.get("key_contradictions", []),
        "items": results.get("items", []),
    }


# ── GET /api/hfrt/projects/{project_id}/memo — Investment Memo ──────────────


@router.get("/projects/{project_id}/memo")
def get_memo(project_id: int, db: Session = Depends(get_db)):
    """Get the final investment memo (Template 14)."""
    template = (
        db.query(HFRTTemplate)
        .filter(
            HFRTTemplate.project_id == project_id,
            HFRTTemplate.template_number == 14,
        )
        .first()
    )
    if not template or template.status != "POPULATED":
        raise HTTPException(
            status_code=404,
            detail=_error("NOT_FOUND", "Investment memo not yet generated"),
        )

    data = None
    if template.data:
        try:
            data = json.loads(template.data)
        except (ValueError, TypeError):
            data = None

    return {
        "projectId": project_id,
        "memo": data,
        "createdAt": template.updated_at.isoformat() if template.updated_at else None,
    }
