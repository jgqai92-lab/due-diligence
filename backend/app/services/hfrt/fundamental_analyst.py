"""HFRT Phase 2: Fundamental Analysis — company overview, business model, competitive position.

Registered steps:
  - company_overview (Template 01)
  - business_model (Template 02)
  - competitive_position (Template 03)

Reuses yfinance_service for financial data.
Porter's Five Forces + Seven Powers scoring for competitive position.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models.hfrt import HFRTProject, HFRTTemplate
from app.services.claude_client import call_claude
from app.services.workflow_engine import register_step, emit_sse_event

logger = logging.getLogger(__name__)


# ── Pydantic models ──────────────────────────────────────────────────────────


class CompanyOverviewResult(BaseModel):
    company_name: str
    ticker: str
    sector: str
    industry: str
    headquarters: Optional[str] = None
    founded: Optional[str] = None
    employees: Optional[int] = None
    description: str
    business_segments: list[dict[str, Any]] = Field(default_factory=list)
    key_products_services: list[str] = Field(default_factory=list)
    geographic_presence: list[str] = Field(default_factory=list)
    recent_developments: list[str] = Field(default_factory=list)
    management_team: list[dict[str, str]] = Field(default_factory=list)


class BusinessModelResult(BaseModel):
    revenue_model: str
    revenue_streams: list[dict[str, Any]] = Field(default_factory=list)
    cost_structure: dict[str, Any] = Field(default_factory=dict)
    unit_economics: dict[str, Any] = Field(default_factory=dict)
    customer_segments: list[str] = Field(default_factory=list)
    value_proposition: str = ""
    distribution_channels: list[str] = Field(default_factory=list)
    key_partnerships: list[str] = Field(default_factory=list)
    scalability_assessment: str = ""
    recurring_revenue_pct: Optional[float] = None


class PorterForce(BaseModel):
    score: int = Field(ge=1, le=5, description="1=weak, 5=strong")
    rationale: str


class SevenPower(BaseModel):
    present: bool
    strength: int = Field(ge=0, le=5, description="0=absent, 5=dominant")
    evidence: str


class CompetitivePositionResult(BaseModel):
    competitive_advantages: list[str] = Field(default_factory=list)
    competitive_disadvantages: list[str] = Field(default_factory=list)
    market_share: Optional[str] = None
    key_competitors: list[dict[str, Any]] = Field(default_factory=list)
    porters_five_forces: dict[str, PorterForce] = Field(default_factory=dict)
    seven_powers: dict[str, SevenPower] = Field(default_factory=dict)
    overall_moat_strength: str = ""
    moat_durability: str = ""


# ── System prompts ───────────────────────────────────────────────────────────

COMPANY_OVERVIEW_PROMPT = """You are an equity research analyst writing a company overview.

Analyze the provided company data and produce a comprehensive overview including:
1. Company description and history
2. Business segments with revenue breakdown
3. Key products/services
4. Geographic presence
5. Recent developments (last 12 months)
6. Management team (top 3-5 executives)

NEVER fabricate data. If information is unavailable, say so explicitly.
Return ONLY valid JSON matching the schema provided."""

BUSINESS_MODEL_PROMPT = """You are an equity research analyst analyzing a company's business model.

Based on the provided data, analyze:
1. Revenue model and streams with breakdown
2. Cost structure (fixed vs variable)
3. Unit economics if applicable
4. Customer segments
5. Value proposition
6. Distribution channels
7. Scalability assessment
8. Recurring revenue percentage estimate

NEVER fabricate financial figures. Use only provided data.
Return ONLY valid JSON matching the schema provided."""

COMPETITIVE_POSITION_PROMPT = """You are an equity research analyst assessing competitive position.

Analyze the company using TWO frameworks:

PORTER'S FIVE FORCES (score each 1-5):
1. Threat of New Entrants
2. Bargaining Power of Suppliers
3. Bargaining Power of Buyers
4. Threat of Substitutes
5. Competitive Rivalry

SEVEN POWERS (assess presence and strength 0-5):
1. Scale Economies
2. Network Effects
3. Counter-Positioning
4. Switching Costs
5. Branding
6. Cornered Resource
7. Process Power

Also identify: competitive advantages, disadvantages, market share, key competitors.

NEVER fabricate data. Base analysis on provided financial data and public information.
Return ONLY valid JSON matching the schema provided."""


# ── Helper ───────────────────────────────────────────────────────────────────

def _fetch_company_data(ticker: str) -> dict[str, Any]:
    """Fetch comprehensive company data from yfinance (cached)."""
    from app.services.hfrt.data_cache import get_yfinance_info, get_yfinance_financials

    info = get_yfinance_info(ticker)
    financials = get_yfinance_financials(ticker)

    # Extract most recent year only (matches original iloc[:, 0] behavior)
    def _most_recent(stmt_dict: dict) -> dict:
        if not stmt_dict:
            return {}
        # Keys are date strings like "2024-06-30"; sort descending to get most recent
        most_recent_key = sorted(stmt_dict.keys(), reverse=True)[0]
        return stmt_dict[most_recent_key]

    return {
        "ticker": ticker,
        "info": {
            k: v for k, v in info.items()
            if k not in ("companyOfficers",)  # Exclude large nested objects
        },
        "income_statement": _most_recent(financials.get("income_statement", {})),
        "balance_sheet": _most_recent(financials.get("balance_sheet", {})),
        "cash_flow": _most_recent(financials.get("cash_flow", {})),
    }


def _get_template_data(db, project_id: int, template_number: int) -> dict | None:
    """Get populated template data for building context."""
    template = (
        db.query(HFRTTemplate)
        .filter(
            HFRTTemplate.project_id == project_id,
            HFRTTemplate.template_number == template_number,
        )
        .first()
    )
    if template and template.data:
        try:
            return json.loads(template.data)
        except (ValueError, TypeError):
            return None
    return None


def _save_template(db, project_id: int, template_number: int, data: dict) -> None:
    """Save data to a template."""
    template = (
        db.query(HFRTTemplate)
        .filter(
            HFRTTemplate.project_id == project_id,
            HFRTTemplate.template_number == template_number,
        )
        .first()
    )
    if template:
        template.data = json.dumps(data, default=str)
        template.status = "POPULATED"
        template.updated_at = datetime.now(timezone.utc)


# ── Step handlers ────────────────────────────────────────────────────────────


@register_step("HFRT", "company_overview")
async def handle_company_overview(workflow_run_id: int) -> dict | None:
    """Generate Template 01: Company Overview."""
    db = SessionLocal()
    try:
        project = (
            db.query(HFRTProject)
            .filter(HFRTProject.workflow_run_id == workflow_run_id)
            .first()
        )
        if not project:
            raise ValueError(f"No HFRT project for workflow {workflow_run_id}")

        project.status = "RESEARCHING"
        project.updated_at = datetime.now(timezone.utc)
        db.commit()

        await emit_sse_event(workflow_run_id, "step_progress", {
            "stepName": "company_overview", "message": "Fetching company data...", "percent": 10,
        })

        company_data = _fetch_company_data(project.ticker)
        idea_screen = _get_template_data(db, project.id, 0)

        user_prompt = (
            f"<company_data>\n{json.dumps(company_data, indent=2, default=str)[:15000]}\n</company_data>\n\n"
            f"<idea_screen>\n{json.dumps(idea_screen, indent=2, default=str)[:3000]}\n</idea_screen>\n\n"
            f"Write a comprehensive company overview for {project.ticker} ({project.company_name}).\n"
            f"Return JSON matching this schema: {CompanyOverviewResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=COMPANY_OVERVIEW_PROMPT,
            user_prompt=user_prompt,
            response_model=CompanyOverviewResult,
        )

        _save_template(db, project.id, 1, result.model_dump())
        db.commit()

        return {"template": 1, "status": "POPULATED"}
    finally:
        db.close()


@register_step("HFRT", "business_model")
async def handle_business_model(workflow_run_id: int) -> dict | None:
    """Generate Template 02: Business Model."""
    db = SessionLocal()
    try:
        project = (
            db.query(HFRTProject)
            .filter(HFRTProject.workflow_run_id == workflow_run_id)
            .first()
        )
        if not project:
            raise ValueError(f"No HFRT project for workflow {workflow_run_id}")

        await emit_sse_event(workflow_run_id, "step_progress", {
            "stepName": "business_model", "message": "Analyzing business model...", "percent": 10,
        })

        company_data = _fetch_company_data(project.ticker)
        overview = _get_template_data(db, project.id, 1)

        user_prompt = (
            f"<company_data>\n{json.dumps(company_data, indent=2, default=str)[:15000]}\n</company_data>\n\n"
            f"<company_overview>\n{json.dumps(overview, indent=2, default=str)[:5000]}\n</company_overview>\n\n"
            f"Analyze the business model of {project.ticker} ({project.company_name}).\n"
            f"Return JSON matching this schema: {BusinessModelResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=BUSINESS_MODEL_PROMPT,
            user_prompt=user_prompt,
            response_model=BusinessModelResult,
        )

        _save_template(db, project.id, 2, result.model_dump())
        db.commit()

        return {"template": 2, "status": "POPULATED"}
    finally:
        db.close()


@register_step("HFRT", "competitive_position")
async def handle_competitive_position(workflow_run_id: int) -> dict | None:
    """Generate Template 03: Competitive Position with Porter's 5 + Seven Powers."""
    db = SessionLocal()
    try:
        project = (
            db.query(HFRTProject)
            .filter(HFRTProject.workflow_run_id == workflow_run_id)
            .first()
        )
        if not project:
            raise ValueError(f"No HFRT project for workflow {workflow_run_id}")

        await emit_sse_event(workflow_run_id, "step_progress", {
            "stepName": "competitive_position", "message": "Assessing competitive position...", "percent": 10,
        })

        company_data = _fetch_company_data(project.ticker)
        overview = _get_template_data(db, project.id, 1)
        biz_model = _get_template_data(db, project.id, 2)

        user_prompt = (
            f"<company_data>\n{json.dumps(company_data, indent=2, default=str)[:12000]}\n</company_data>\n\n"
            f"<company_overview>\n{json.dumps(overview, indent=2, default=str)[:4000]}\n</company_overview>\n\n"
            f"<business_model>\n{json.dumps(biz_model, indent=2, default=str)[:4000]}\n</business_model>\n\n"
            f"Assess the competitive position of {project.ticker} ({project.company_name}) "
            f"using Porter's Five Forces and Seven Powers frameworks.\n"
            f"Return JSON matching this schema: {CompetitivePositionResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=COMPETITIVE_POSITION_PROMPT,
            user_prompt=user_prompt,
            response_model=CompetitivePositionResult,
        )

        _save_template(db, project.id, 3, result.model_dump())
        db.commit()

        return {"template": 3, "status": "POPULATED"}
    finally:
        db.close()
