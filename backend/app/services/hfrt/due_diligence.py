"""HFRT Phase 3: Risk & Due Diligence — SEC filing fetch, management, risk, earnings quality.

Registered steps:
  - fetch_sec_filings — fetches 10-K, 10-Q, DEF 14A from SEC EDGAR
  - management_assessment (Template 07) — governance, compensation, track record
  - risk_analysis (Template 08) — risk register with probability × impact scoring
  - quality_of_earnings (Template 09) — accrual ratio, cash flow quality
  - dd_sufficiency_gate — validates DD completeness
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models.hfrt import HFRTProject, HFRTTemplate, HFRTSECFiling
from app.services.claude_client import call_claude
from app.services.hfrt.edgar_service import (
    fetch_filing,
    get_filing_content,
    extract_filing_sections,
)
from app.services.workflow_engine import register_step, emit_sse_event

logger = logging.getLogger(__name__)


# ── Pydantic models ──────────────────────────────────────────────────────────


class ManagementAssessmentResult(BaseModel):
    ceo: dict[str, Any] = Field(default_factory=dict)
    cfo: dict[str, Any] = Field(default_factory=dict)
    board_composition: dict[str, Any] = Field(default_factory=dict)
    compensation_analysis: dict[str, Any] = Field(default_factory=dict)
    insider_ownership: Optional[str] = None
    governance_red_flags: list[str] = Field(default_factory=list)
    management_quality_score: Optional[int] = Field(default=None, ge=1, le=10)
    track_record: str = ""
    key_concerns: list[str] = Field(default_factory=list)


class RiskItem(BaseModel):
    risk: str
    category: str
    probability: str
    impact: str
    severity_score: int = Field(ge=1, le=25)
    mitigation: str = ""


class RiskAnalysisResult(BaseModel):
    risk_register: list[RiskItem] = Field(default_factory=list)
    top_risks: list[str] = Field(default_factory=list)
    risk_heat_map: dict[str, Any] = Field(default_factory=dict)
    scenario_analysis: list[dict[str, Any]] = Field(default_factory=list)
    overall_risk_rating: str = ""


class QualityOfEarningsResult(BaseModel):
    accrual_ratio: Optional[float] = None
    operating_cf_to_net_income: Optional[float] = None
    revenue_quality: dict[str, Any] = Field(default_factory=dict)
    expense_quality: dict[str, Any] = Field(default_factory=dict)
    one_time_items: list[str] = Field(default_factory=list)
    accounting_red_flags: list[str] = Field(default_factory=list)
    cash_flow_quality_score: Optional[int] = Field(default=None, ge=1, le=10)
    earnings_sustainability: str = ""
    footnote_concerns: list[str] = Field(default_factory=list)


class DDSufficiencyResult(BaseModel):
    passes: bool
    deficiencies: list[str] = Field(default_factory=list)
    recommendation: str = ""


# ── System prompts ───────────────────────────────────────────────────────────

MANAGEMENT_PROMPT = """You are an equity research analyst performing management due diligence.

Using SEC filing data (especially proxy statement/DEF 14A), analyze:
1. CEO: background, tenure, track record, compensation structure
2. CFO: background, accounting expertise
3. Board: independence, diversity, expertise, potential conflicts
4. Compensation: alignment with shareholder interests, pay-for-performance
5. Insider ownership: management skin in the game
6. Governance red flags: related party transactions, board captured, excessive perks
7. Overall management quality score (1-10)

NEVER fabricate executive names or compensation figures. Use ONLY provided data.
Return ONLY valid JSON matching the schema provided."""

RISK_PROMPT = """You are an equity research analyst building a risk register.

Analyze all research data to identify risks across categories:
- Business risks (competition, disruption, customer concentration)
- Financial risks (leverage, liquidity, currency, interest rate)
- Operational risks (supply chain, key person, execution)
- Regulatory risks (compliance, litigation, policy changes)
- Market risks (valuation, sentiment, macro)

For each risk, assess:
- Probability: Very Low (1), Low (2), Moderate (3), High (4), Very High (5)
- Impact: Minimal (1), Minor (2), Moderate (3), Major (4), Severe (5)
- Severity score = Probability × Impact (1-25)

Also provide scenario analysis (bull/base/bear) with quantified impacts.

NEVER fabricate risk data. Return ONLY valid JSON matching the schema provided."""

EARNINGS_QUALITY_PROMPT = """You are a forensic accountant reviewing earnings quality.

Analyze the financial data to assess:
1. Accrual ratio: (Net Income - Operating CF) / Total Assets
2. Operating CF / Net Income ratio (should be >1.0 for high quality)
3. Revenue quality: organic vs acquired, recurring vs one-time
4. Expense quality: normal vs aggressive capitalization
5. One-time items that inflate/deflate earnings
6. Accounting red flags from financial statement analysis
7. Cash flow quality score (1-10)
8. Footnote concerns (if filing data available)

NEVER fabricate financial figures. Calculate from provided data.
Return ONLY valid JSON matching the schema provided."""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_template_data(db, project_id: int, template_number: int) -> dict | None:
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


@register_step("HFRT", "fetch_sec_filings")
async def handle_fetch_sec_filings(workflow_run_id: int) -> dict | None:
    """Fetch 10-K, 10-Q, and DEF 14A from SEC EDGAR."""
    db = SessionLocal()
    try:
        project = (
            db.query(HFRTProject)
            .filter(HFRTProject.workflow_run_id == workflow_run_id)
            .first()
        )
        if not project:
            raise ValueError(f"No HFRT project for workflow {workflow_run_id}")

        project.status = "DUE_DILIGENCE"
        project.updated_at = datetime.now(timezone.utc)
        db.commit()

        results = {}
        filing_types = ["10-K", "10-Q", "DEF_14A"]

        for i, filing_type in enumerate(filing_types):
            await emit_sse_event(workflow_run_id, "step_progress", {
                "stepName": "fetch_sec_filings",
                "message": f"Fetching {filing_type}...",
                "percent": int((i + 1) / len(filing_types) * 80),
            })

            result = fetch_filing(
                ticker=project.ticker,
                filing_type=filing_type.replace("_", " "),
                project_id=project.id,
            )
            results[filing_type] = result

        return {
            "filings_fetched": sum(1 for r in results.values() if r.get("success")),
            "filings_failed": sum(1 for r in results.values() if not r.get("success")),
            "details": results,
        }
    finally:
        db.close()


@register_step("HFRT", "management_assessment")
async def handle_management_assessment(workflow_run_id: int) -> dict | None:
    """Generate Template 07: Management Assessment."""
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
            "stepName": "management_assessment", "message": "Assessing management...", "percent": 10,
        })

        # Get proxy statement content
        proxy_content = get_filing_content(project.id, "DEF 14A", max_chars=30000) or ""
        ten_k_content = get_filing_content(project.id, "10-K", max_chars=10000) or ""
        overview = _get_template_data(db, project.id, 1)

        user_prompt = (
            f"<proxy_statement>\n{proxy_content[:25000]}\n</proxy_statement>\n\n"
            f"<annual_report_excerpt>\n{ten_k_content[:8000]}\n</annual_report_excerpt>\n\n"
            f"<company_overview>\n{json.dumps(overview, indent=2, default=str)[:3000]}\n</company_overview>\n\n"
            f"Perform a management assessment for {project.ticker} ({project.company_name}).\n"
            f"Return JSON matching this schema: {ManagementAssessmentResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=MANAGEMENT_PROMPT,
            user_prompt=user_prompt,
            response_model=ManagementAssessmentResult,
        )

        _save_template(db, project.id, 7, result.model_dump())
        db.commit()

        return {"template": 7, "status": "POPULATED"}
    finally:
        db.close()


@register_step("HFRT", "risk_analysis")
async def handle_risk_analysis(workflow_run_id: int) -> dict | None:
    """Generate Template 08: Risk Analysis with heat map."""
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
            "stepName": "risk_analysis", "message": "Building risk register...", "percent": 10,
        })

        # Get 10-K risk factors
        ten_k_content = get_filing_content(project.id, "10-K", max_chars=40000) or ""
        sections = extract_filing_sections(ten_k_content) if ten_k_content else {}
        risk_factors = sections.get("risk_factors", "")[:15000]

        # Get prior templates for context
        overview = _get_template_data(db, project.id, 1)
        competitive = _get_template_data(db, project.id, 3)
        financials = _get_template_data(db, project.id, 5)

        user_prompt = (
            f"<risk_factors_10k>\n{risk_factors}\n</risk_factors_10k>\n\n"
            f"<company_overview>\n{json.dumps(overview, indent=2, default=str)[:3000]}\n</company_overview>\n\n"
            f"<competitive_position>\n{json.dumps(competitive, indent=2, default=str)[:3000]}\n</competitive_position>\n\n"
            f"<financial_analysis>\n{json.dumps(financials, indent=2, default=str)[:3000]}\n</financial_analysis>\n\n"
            f"Build a comprehensive risk analysis for {project.ticker} ({project.company_name}).\n"
            f"Return JSON matching this schema: {RiskAnalysisResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=RISK_PROMPT,
            user_prompt=user_prompt,
            response_model=RiskAnalysisResult,
        )

        _save_template(db, project.id, 8, result.model_dump())
        db.commit()

        return {"template": 8, "status": "POPULATED", "risks": len(result.risk_register)}
    finally:
        db.close()


@register_step("HFRT", "quality_of_earnings")
async def handle_quality_of_earnings(workflow_run_id: int) -> dict | None:
    """Generate Template 09: Quality of Earnings."""
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
            "stepName": "quality_of_earnings", "message": "Analyzing earnings quality...", "percent": 10,
        })

        ten_k_content = get_filing_content(project.id, "10-K", max_chars=30000) or ""
        financials = _get_template_data(db, project.id, 5)

        # Get raw financial data (cached)
        from app.services.hfrt.data_cache import get_yfinance_financials
        cached_fins = get_yfinance_financials(project.ticker)
        raw_financials = {}
        for year, data in cached_fins.get("income_statement", {}).items():
            raw_financials[f"income_{year}"] = data
        for year, data in cached_fins.get("cash_flow", {}).items():
            raw_financials[f"cashflow_{year}"] = data

        user_prompt = (
            f"<annual_report_excerpt>\n{ten_k_content[:20000]}\n</annual_report_excerpt>\n\n"
            f"<financial_analysis>\n{json.dumps(financials, indent=2, default=str)[:5000]}\n</financial_analysis>\n\n"
            f"<raw_financials>\n{json.dumps(raw_financials, indent=2, default=str)[:10000]}\n</raw_financials>\n\n"
            f"Perform a quality of earnings analysis for {project.ticker} ({project.company_name}).\n"
            f"Return JSON matching this schema: {QualityOfEarningsResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=EARNINGS_QUALITY_PROMPT,
            user_prompt=user_prompt,
            response_model=QualityOfEarningsResult,
        )

        _save_template(db, project.id, 9, result.model_dump())
        db.commit()

        return {"template": 9, "status": "POPULATED"}
    finally:
        db.close()


@register_step("HFRT", "dd_sufficiency_gate")
async def handle_dd_sufficiency_gate(workflow_run_id: int) -> dict | None:
    """Validate DD completeness (Templates 07-09) before dialectic."""
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
            "stepName": "dd_sufficiency_gate", "message": "Checking DD completeness...", "percent": 50,
        })

        # Check templates 07-09
        deficiencies = []
        for num, name in [(7, "Management Assessment"), (8, "Risk Analysis"), (9, "Quality of Earnings")]:
            data = _get_template_data(db, project.id, num)
            if not data:
                deficiencies.append(f"Template {num:02d} ({name}) is empty")

        passes = len(deficiencies) == 0

        if not passes:
            await emit_sse_event(workflow_run_id, "gate_failed", {
                "gateName": "dd_sufficiency_gate",
                "deficiencies": deficiencies,
            })

        return {
            "gate": "dd_sufficiency",
            "passes": passes,
            "deficiencies": deficiencies,
        }
    finally:
        db.close()
