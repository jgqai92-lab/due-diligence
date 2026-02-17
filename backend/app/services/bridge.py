"""IST-to-HFRT bridge service -- creates HFRT research projects from certified IST screens.

Bridges the IST Investment Screening workflow to the HFRT Hedge Fund Research workflow.
Takes Tier 1 equity candidates from a certified IST screen and creates fully initialized
HFRT deep research projects pre-populated with IST-derived context.
"""

import json
import logging

from sqlalchemy.orm import Session

from app.models.ist import ISTScreen
from app.models.hfrt import HFRTProject, HFRTTemplate
from app.models.workflow import WorkflowRun, WorkflowStep

logger = logging.getLogger(__name__)


# ── HFRT constants (local copy to avoid circular imports from routers) ────────

HFRT_WORKFLOW_STEPS = [
    # Phase 1: Screening
    {"step_name": "idea_screen", "phase": 1, "phase_name": "Screening", "step_order": 1, "depends_on": [], "model": "opus"},
    # Phase 2: Deep Research
    {"step_name": "company_overview", "phase": 2, "phase_name": "Deep Research", "step_order": 2, "depends_on": ["idea_screen"], "model": "opus"},
    {"step_name": "business_model", "phase": 2, "phase_name": "Deep Research", "step_order": 3, "depends_on": ["company_overview"], "model": "opus"},
    {"step_name": "competitive_position", "phase": 2, "phase_name": "Deep Research", "step_order": 4, "depends_on": ["company_overview"], "model": "opus"},
    {"step_name": "industry_analysis", "phase": 2, "phase_name": "Deep Research", "step_order": 5, "depends_on": ["company_overview"], "model": "opus"},
    {"step_name": "financial_analysis", "phase": 2, "phase_name": "Deep Research", "step_order": 6, "depends_on": ["business_model"], "model": "sonnet"},
    {"step_name": "valuation", "phase": 2, "phase_name": "Deep Research", "step_order": 7, "depends_on": ["financial_analysis"], "model": "sonnet"},
    {"step_name": "research_sufficiency_gate", "phase": 2, "phase_name": "Deep Research", "step_order": 8, "depends_on": ["valuation", "competitive_position", "industry_analysis"], "model": "none", "retry_strategy": "with_parent"},
    # Phase 3: Risk & Due Diligence
    {"step_name": "fetch_sec_filings", "phase": 3, "phase_name": "Risk & Due Diligence", "step_order": 9, "depends_on": ["research_sufficiency_gate"], "model": "none"},
    {"step_name": "management_assessment", "phase": 3, "phase_name": "Risk & Due Diligence", "step_order": 10, "depends_on": ["fetch_sec_filings"], "model": "opus"},
    {"step_name": "risk_analysis", "phase": 3, "phase_name": "Risk & Due Diligence", "step_order": 11, "depends_on": ["fetch_sec_filings"], "model": "opus"},
    {"step_name": "quality_of_earnings", "phase": 3, "phase_name": "Risk & Due Diligence", "step_order": 12, "depends_on": ["fetch_sec_filings"], "model": "opus"},
    {"step_name": "dd_sufficiency_gate", "phase": 3, "phase_name": "Risk & Due Diligence", "step_order": 13, "depends_on": ["management_assessment", "risk_analysis", "quality_of_earnings"], "model": "none", "retry_strategy": "with_parent"},
    # Phase 4: Dialectic
    {"step_name": "bull_case", "phase": 4, "phase_name": "Dialectic", "step_order": 14, "depends_on": ["dd_sufficiency_gate"], "model": "opus"},
    {"step_name": "bear_case", "phase": 4, "phase_name": "Dialectic", "step_order": 15, "depends_on": ["dd_sufficiency_gate"], "model": "opus"},
    # Phase 5: Synthesis
    {"step_name": "catalyst_analysis", "phase": 5, "phase_name": "Synthesis", "step_order": 16, "depends_on": ["bull_case", "bear_case"], "model": "sonnet"},
    {"step_name": "investment_thesis", "phase": 5, "phase_name": "Synthesis", "step_order": 17, "depends_on": ["bull_case", "bear_case"], "model": "opus"},
    {"step_name": "bull_synthesis", "phase": 5, "phase_name": "Synthesis", "step_order": 18, "depends_on": ["investment_thesis"], "model": "sonnet"},
    {"step_name": "bear_synthesis", "phase": 5, "phase_name": "Synthesis", "step_order": 19, "depends_on": ["investment_thesis"], "model": "sonnet"},
    {"step_name": "thesis_coherence_gate", "phase": 5, "phase_name": "Synthesis", "step_order": 20, "depends_on": ["bull_synthesis", "bear_synthesis", "catalyst_analysis"], "model": "none", "retry_strategy": "with_parent"},
    {"step_name": "investment_memo", "phase": 5, "phase_name": "Synthesis", "step_order": 21, "depends_on": ["thesis_coherence_gate"], "model": "opus"},
    {"step_name": "research_certification", "phase": 5, "phase_name": "Synthesis", "step_order": 22, "depends_on": ["thesis_coherence_gate"], "model": "sonnet"},
    {"step_name": "complete", "phase": 5, "phase_name": "Synthesis", "step_order": 23, "depends_on": ["investment_memo", "research_certification"], "model": "none"},
]

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


def get_handoff_candidates(db: Session, screen_id: int) -> dict:
    """Load and return HFRT handoff data from a certified IST screen.

    Args:
        db: SQLAlchemy session.
        screen_id: ID of the IST screen.

    Returns:
        Parsed handoff data dict containing screenName, screenId, certifiedAt,
        tier1Count, and candidates list.

    Raises:
        ValueError: If screen not found, not certified, or no handoff data.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise ValueError(f"Screen {screen_id} not found")

    if not screen.is_certified:
        raise ValueError("Screen is not certified")

    if not screen.hfrt_handoff:
        raise ValueError("No handoff data available")

    try:
        handoff_data = json.loads(screen.hfrt_handoff)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.error("Failed to parse hfrt_handoff JSON for screen %d: %s", screen_id, exc)
        raise ValueError("No handoff data available") from exc

    if not handoff_data:
        raise ValueError("No handoff data available")

    return handoff_data


def create_hfrt_from_handoff(db: Session, screen_id: int, ticker: str) -> dict:
    """Create an HFRT research project from an IST handoff candidate.

    Creates a full HFRT project (WorkflowRun, HFRTProject, 23 WorkflowSteps,
    15 HFRTTemplates) with the Idea Screen template (00) pre-populated from
    IST handoff data.

    Args:
        db: SQLAlchemy session.
        screen_id: ID of the certified IST screen.
        ticker: Ticker symbol of the candidate to create a project for.

    Returns:
        Dict with projectId, workflowRunId, ticker, companyName, status, and link.

    Raises:
        ValueError: If screen not found, not certified, no handoff data,
                     or ticker not in handoff candidates.
    """
    # Load and validate screen
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise ValueError(f"Screen {screen_id} not found")

    if not screen.is_certified:
        raise ValueError("Screen is not certified")

    if not screen.hfrt_handoff:
        raise ValueError("No handoff data available")

    try:
        handoff_data = json.loads(screen.hfrt_handoff)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.error("Failed to parse hfrt_handoff JSON for screen %d: %s", screen_id, exc)
        raise ValueError("No handoff data available") from exc

    # Find the candidate matching the requested ticker (case-insensitive)
    candidates = handoff_data.get("candidates", [])
    candidate = None
    ticker_upper = ticker.strip().upper()
    for c in candidates:
        if c.get("ticker", "").strip().upper() == ticker_upper:
            candidate = c
            break

    if candidate is None:
        raise ValueError(
            f"Ticker {ticker_upper} not found in handoff candidates for screen {screen_id}"
        )

    # 1. Create the WorkflowRun
    run = WorkflowRun(
        workflow_type="HFRT",
        name=f"HFRT Research: {ticker_upper} (IST Handoff)",
        status="PENDING",
        current_phase=0,
    )
    db.add(run)
    db.flush()

    # 2. Create the HFRTProject with bridge source tracking
    project = HFRTProject(
        workflow_run_id=run.id,
        ticker=ticker_upper,
        company_name=candidate.get("companyName"),
        status="PENDING",
        source="IST_HANDOFF",
        ist_screen_id=screen_id,
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

    # 4. Create all 15 templates; pre-populate template 00 (Idea Screen)
    screen_name = handoff_data.get("screenName", screen.name)

    # Build the scarcity score -- may be a number or a nested structure
    scarcity_score = candidate.get("scarcityScore")
    if isinstance(scarcity_score, dict):
        # Extract composite score if available
        scarcity_score = scarcity_score.get("composite", scarcity_score.get("overall", scarcity_score))

    idea_screen_data = {
        "ticker": ticker_upper,
        "companyName": candidate.get("companyName", ""),
        "source": "IST Handoff",
        "istScreenId": screen_id,
        "istScreenName": screen_name,
        "thesis": f"Pillar: {candidate.get('pillar', 'Unknown')}. Conviction: {candidate.get('conviction', 'Unknown')}.",
        "scarcityScore": scarcity_score,
        "catalyst": candidate.get("catalyst", ""),
        "bottleneckExposure": candidate.get("pillar", ""),
        "prePopulated": True,
    }

    for num, name in HFRT_TEMPLATES.items():
        if num == 0:
            template = HFRTTemplate(
                project_id=project.id,
                template_number=num,
                template_name=name,
                data=json.dumps(idea_screen_data),
                status="POPULATED",
            )
        else:
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

    logger.info(
        "Created HFRT project %d for ticker %s from IST screen %d",
        project.id,
        ticker_upper,
        screen_id,
    )

    return {
        "ticker": ticker_upper,
        "projectId": project.id,
        "workflowRunId": run.id,
        "companyName": candidate.get("companyName"),
        "status": project.status,
        "link": f"/research/{project.id}",
    }
