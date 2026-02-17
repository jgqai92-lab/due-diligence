"""HFRT Phase 2: Quantitative Analysis — financial analysis, valuation, sufficiency gate.

Registered steps:
  - financial_analysis (Template 05) — DuPont decomposition, ratio analysis, M-Score/Z-Score
  - valuation (Template 06) — DCF, comps, sensitivity analysis
  - research_sufficiency_gate — validates Templates 01-06 completeness

Reuses forensic_engine (M-Score, Z-Score) and general_metrics_engine.
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


class DuPontDecomposition(BaseModel):
    """3-factor and 5-factor DuPont decomposition."""
    roe: Optional[float] = None
    # 3-factor
    net_margin: Optional[float] = None
    asset_turnover: Optional[float] = None
    equity_multiplier: Optional[float] = None
    # 5-factor
    tax_burden: Optional[float] = None
    interest_burden: Optional[float] = None
    operating_margin: Optional[float] = None
    interpretation: str = ""


class FinancialAnalysisResult(BaseModel):
    dupont: DuPontDecomposition
    profitability: dict[str, Any] = Field(default_factory=dict)
    leverage: dict[str, Any] = Field(default_factory=dict)
    liquidity: dict[str, Any] = Field(default_factory=dict)
    efficiency: dict[str, Any] = Field(default_factory=dict)
    cash_flow_quality: dict[str, Any] = Field(default_factory=dict)
    growth_metrics: dict[str, Any] = Field(default_factory=dict)
    altman_z_score: Optional[dict[str, Any]] = None
    beneish_m_score: Optional[dict[str, Any]] = None
    key_trends: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)


class DCFValuation(BaseModel):
    wacc: Optional[float] = None
    wacc_components: dict[str, Any] = Field(default_factory=dict)
    projected_fcf: list[dict[str, Any]] = Field(default_factory=list)
    terminal_value: Optional[float] = None
    terminal_growth_rate: Optional[float] = None
    enterprise_value: Optional[float] = None
    equity_value: Optional[float] = None
    implied_share_price: Optional[float] = None
    current_price: Optional[float] = None
    upside_downside_pct: Optional[float] = None


class ValuationResult(BaseModel):
    dcf: DCFValuation
    relative_valuation: dict[str, Any] = Field(default_factory=dict)
    sensitivity_table: list[dict[str, Any]] = Field(default_factory=list)
    peer_comparison: list[dict[str, Any]] = Field(default_factory=list)
    valuation_summary: str = ""
    fair_value_range: dict[str, Any] = Field(default_factory=dict)


class SufficiencyResult(BaseModel):
    passes: bool
    deficiencies: list[str] = Field(default_factory=list)
    template_status: dict[str, str] = Field(default_factory=dict)
    recommendation: str = ""


# ── System prompts ───────────────────────────────────────────────────────────

FINANCIAL_ANALYSIS_PROMPT = """You are a quantitative equity research analyst performing financial analysis.

Analyze the provided financial data to produce:

1. DUPONT DECOMPOSITION (both 3-factor and 5-factor):
   - 3-factor: ROE = Net Margin × Asset Turnover × Equity Multiplier
   - 5-factor: ROE = Tax Burden × Interest Burden × Operating Margin × Asset Turnover × Equity Multiplier

2. RATIO ANALYSIS:
   - Profitability: Gross margin, operating margin, net margin, ROE, ROA, ROIC
   - Leverage: D/E ratio, interest coverage, debt/EBITDA
   - Liquidity: Current ratio, quick ratio
   - Efficiency: Asset turnover, inventory turnover, receivables turnover
   - Cash flow quality: Operating CF/Net Income, FCF yield, CapEx/Revenue

3. GROWTH METRICS: Revenue, earnings, FCF growth rates (YoY)

4. FORENSIC FLAGS:
   - Altman Z-Score components if calculable
   - Beneish M-Score components if calculable

5. KEY TRENDS and RED FLAGS

Calculate from actual data where possible. NEVER fabricate financial figures.
If data is insufficient for a calculation, return null.
Return ONLY valid JSON matching the schema provided."""

VALUATION_PROMPT = """You are a quantitative equity research analyst performing valuation analysis.

Build a comprehensive valuation including:

1. DCF VALUATION:
   - WACC calculation (risk-free rate ~4.5%, ERP ~5.5%, use company beta)
   - 5-year projected FCF based on historical growth + analyst consensus
   - Terminal value using perpetuity growth method (2-3% terminal growth)
   - Enterprise value → Equity value → Implied share price

2. RELATIVE VALUATION:
   - P/E, EV/EBITDA, P/S, P/FCF multiples vs peers
   - Historical valuation range

3. SENSITIVITY TABLE:
   - Vary WACC (±1%) and terminal growth (±0.5%)
   - Show implied price for each combination

4. PEER COMPARISON:
   - 3-5 closest peers with comparable metrics

5. FAIR VALUE RANGE: bull/base/bear scenarios

Use provided financial data. NEVER fabricate numbers.
Return ONLY valid JSON matching the schema provided."""

SUFFICIENCY_PROMPT = """You are a research quality gate checking whether Templates 01-06 are sufficiently complete.

Review the provided template data and check:
1. Each template has been populated (not empty)
2. Key sections have substantive content
3. Financial data is present and reasonable
4. No critical gaps that would prevent due diligence

Return a pass/fail verdict with specific deficiencies listed.
Return ONLY valid JSON matching the schema provided."""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fetch_financial_data(ticker: str) -> dict[str, Any]:
    """Fetch comprehensive financial data from yfinance (cached)."""
    from app.services.hfrt.data_cache import get_yfinance_info, get_yfinance_financials

    info = get_yfinance_info(ticker)
    financials = get_yfinance_financials(ticker)

    return {
        "ticker": ticker,
        "info": {k: v for k, v in info.items() if k not in ("companyOfficers",)},
        "income_statement": financials.get("income_statement", {}),
        "balance_sheet": financials.get("balance_sheet", {}),
        "cash_flow": financials.get("cash_flow", {}),
    }


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


@register_step("HFRT", "financial_analysis")
async def handle_financial_analysis(workflow_run_id: int) -> dict | None:
    """Generate Template 05: Financial Analysis with DuPont decomposition."""
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
            "stepName": "financial_analysis", "message": "Running financial analysis...", "percent": 10,
        })

        financial_data = _fetch_financial_data(project.ticker)
        overview = _get_template_data(db, project.id, 1)

        user_prompt = (
            f"<financial_data>\n{json.dumps(financial_data, indent=2, default=str)[:20000]}\n</financial_data>\n\n"
            f"<company_overview>\n{json.dumps(overview, indent=2, default=str)[:3000]}\n</company_overview>\n\n"
            f"Perform comprehensive financial analysis for {project.ticker} ({project.company_name}).\n"
            f"Return JSON matching this schema: {FinancialAnalysisResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=FINANCIAL_ANALYSIS_PROMPT,
            user_prompt=user_prompt,
            response_model=FinancialAnalysisResult,
        )

        _save_template(db, project.id, 5, result.model_dump())
        db.commit()

        return {"template": 5, "status": "POPULATED"}
    finally:
        db.close()


@register_step("HFRT", "valuation")
async def handle_valuation(workflow_run_id: int) -> dict | None:
    """Generate Template 06: Valuation with DCF and comps."""
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
            "stepName": "valuation", "message": "Building valuation model...", "percent": 10,
        })

        financial_data = _fetch_financial_data(project.ticker)
        financials = _get_template_data(db, project.id, 5)
        industry = _get_template_data(db, project.id, 4)

        user_prompt = (
            f"<financial_data>\n{json.dumps(financial_data, indent=2, default=str)[:15000]}\n</financial_data>\n\n"
            f"<financial_analysis>\n{json.dumps(financials, indent=2, default=str)[:5000]}\n</financial_analysis>\n\n"
            f"<industry_analysis>\n{json.dumps(industry, indent=2, default=str)[:3000]}\n</industry_analysis>\n\n"
            f"Build a comprehensive valuation for {project.ticker} ({project.company_name}).\n"
            f"Return JSON matching this schema: {ValuationResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=VALUATION_PROMPT,
            user_prompt=user_prompt,
            response_model=ValuationResult,
            max_tokens=12288,
        )

        _save_template(db, project.id, 6, result.model_dump())
        db.commit()

        return {"template": 6, "status": "POPULATED"}
    finally:
        db.close()


@register_step("HFRT", "research_sufficiency_gate")
async def handle_research_sufficiency_gate(workflow_run_id: int) -> dict | None:
    """Validate that Templates 01-06 are complete before proceeding to DD."""
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
            "stepName": "research_sufficiency_gate",
            "message": "Checking research completeness...",
            "percent": 50,
        })

        # Gather templates 01-06
        templates_data = {}
        for num in range(1, 7):
            data = _get_template_data(db, project.id, num)
            templates_data[f"template_{num:02d}"] = data

        user_prompt = (
            f"<templates>\n{json.dumps(templates_data, indent=2, default=str)[:20000]}\n</templates>\n\n"
            f"Check if Templates 01-06 for {project.ticker} are sufficiently complete "
            f"to proceed to due diligence.\n"
            f"Return JSON matching this schema: {SufficiencyResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=SUFFICIENCY_PROMPT,
            user_prompt=user_prompt,
            response_model=SufficiencyResult,
        )

        if not result.passes:
            await emit_sse_event(workflow_run_id, "gate_failed", {
                "gateName": "research_sufficiency_gate",
                "deficiencies": result.deficiencies,
            })

        return {
            "gate": "research_sufficiency",
            "passes": result.passes,
            "deficiencies": result.deficiencies,
        }
    finally:
        db.close()
