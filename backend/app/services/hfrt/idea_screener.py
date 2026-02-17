"""HFRT Phase 1: Idea Screen — validates ticker investability.

Fetches company data via yfinance, validates liquidity/exchange/sector,
then uses Claude for initial red-flag assessment.

Registered step: idea_screen (Template 00)

Invariants enforced:
  - INV-AI-01: Content/instruction separation
  - INV-AI-03: Pydantic-validated Claude outputs
  - INV-AI-04: Anti-hallucination instructions
  - INV-BE-05: Background tasks own their DB sessions
  - INV-BE-06: JSON stored via Pydantic serialization
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


# ── Pydantic models for Claude structured output (INV-AI-03) ────────────────


class LiquidityCheck(BaseModel):
    """Liquidity assessment details."""

    avg_daily_volume: Optional[float] = Field(default=None, description="Average daily volume")
    market_cap_billions: Optional[float] = Field(default=None, description="Market cap in billions")
    bid_ask_spread: Optional[str] = Field(default=None, description="Typical bid-ask spread")
    passes: bool = Field(description="Whether liquidity check passes")
    notes: str = Field(description="Liquidity assessment notes")


class IdeaScreenOutput(BaseModel):
    """Structured output from the idea screen Claude call."""

    investable: bool = Field(description="Whether the ticker passes initial screen")
    verdict: str = Field(description="PASS, FAIL, or CONDITIONAL")
    company_name: str = Field(description="Full company name")
    sector: str = Field(description="Sector classification")
    exchange: str = Field(description="Stock exchange")
    market_cap_billions: Optional[float] = Field(
        default=None, description="Market cap in billions USD"
    )
    liquidity_check: LiquidityCheck = Field(
        description="Liquidity assessment details"
    )
    red_flags: list[str] = Field(
        default_factory=list, description="Initial red flags identified"
    )
    rationale: str = Field(description="Reasoning for the verdict")
    key_metrics: dict[str, Any] = Field(
        default_factory=dict, description="Key financial metrics snapshot"
    )


# ── System prompt ─────────────────────────────────────────────────────────────

IDEA_SCREEN_SYSTEM_PROMPT = """You are an investment research analyst performing an initial idea screen on a stock ticker.

Your task:
1. Analyze the provided company and financial data
2. Determine if the company is investable based on:
   - Liquidity: sufficient daily volume (>100K shares/day preferred) and market cap (>$500M preferred)
   - Exchange: listed on a major exchange (NYSE, NASDAQ, etc.)
   - Data availability: sufficient financial data for deep research
   - Red flags: any immediate disqualifiers (fraud allegations, delisting risk, etc.)
3. Provide a verdict: PASS, FAIL, or CONDITIONAL
4. List any red flags that warrant attention
5. Provide key financial metrics snapshot

NEVER fabricate financial data. If data is unavailable, note it as null rather than inventing values.
Base your assessment only on the provided data.

Return ONLY valid JSON matching the schema provided."""


# ── Helper: Fetch yfinance data ──────────────────────────────────────────────


def _fetch_yfinance_data(ticker: str) -> dict[str, Any]:
    """Fetch company info and key metrics from yfinance (cached)."""
    from app.services.hfrt.data_cache import get_yfinance_info

    info = get_yfinance_info(ticker)

    return {
        "ticker": ticker,
        "company_name": info.get("longName") or info.get("shortName") or ticker,
        "sector": info.get("sector", "Unknown"),
        "industry": info.get("industry", "Unknown"),
        "exchange": info.get("exchange", "Unknown"),
        "market_cap": info.get("marketCap"),
        "enterprise_value": info.get("enterpriseValue"),
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "price_to_book": info.get("priceToBook"),
        "revenue": info.get("totalRevenue"),
        "ebitda": info.get("ebitda"),
        "net_income": info.get("netIncomeToCommon"),
        "free_cash_flow": info.get("freeCashflow"),
        "total_debt": info.get("totalDebt"),
        "total_cash": info.get("totalCash"),
        "avg_volume": info.get("averageVolume"),
        "avg_volume_10d": info.get("averageDailyVolume10Day"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "dividend_yield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "currency": info.get("currency", "USD"),
        "country": info.get("country", "Unknown"),
        "full_time_employees": info.get("fullTimeEmployees"),
        "website": info.get("website"),
        "description": (info.get("longBusinessSummary") or "")[:2000],
    }


# ── Registered step handler ──────────────────────────────────────────────────


@register_step("HFRT", "idea_screen")
async def handle_idea_screen(workflow_run_id: int) -> dict | None:
    """Screen a ticker for investability and populate Template 00.

    INV-BE-05: Creates its own SessionLocal, closed in finally block.
    INV-BE-06: JSON columns written via Pydantic serialization.
    """
    db = SessionLocal()
    try:
        # Find the HFRT project linked to this workflow
        project = (
            db.query(HFRTProject)
            .filter(HFRTProject.workflow_run_id == workflow_run_id)
            .first()
        )
        if not project:
            raise ValueError(
                f"No HFRT project found for workflow {workflow_run_id}"
            )

        # Update project status
        project.status = "SCREENING"
        project.updated_at = datetime.now(timezone.utc)
        db.commit()

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "idea_screen",
                "message": f"Fetching market data for {project.ticker}...",
                "percent": 10,
            },
        )

        # Fetch yfinance data
        yf_data = _fetch_yfinance_data(project.ticker)

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "idea_screen",
                "message": "Running investability assessment...",
                "percent": 40,
            },
        )

        # Build Claude prompt (INV-AI-01: data in XML tags)
        user_prompt = (
            f"<company_data>\n{json.dumps(yf_data, indent=2, default=str)}\n</company_data>\n\n"
            f"Perform an idea screen on {project.ticker}. "
            f"Assess investability, liquidity, and identify any red flags.\n"
            f"Return JSON matching this schema: {IdeaScreenOutput.model_json_schema()}"
        )

        # Call Claude (INV-AI-03: Pydantic-validated)
        result = await call_claude(
            system_prompt=IDEA_SCREEN_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=IdeaScreenOutput,
        )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "idea_screen",
                "message": f"Verdict: {result.verdict}",
                "percent": 80,
            },
        )

        # Update project with screening results
        project.company_name = result.company_name
        project.sector = result.sector
        project.exchange = result.exchange
        project.market_cap = result.market_cap_billions
        project.investable = 1 if result.investable else 0
        project.investable_verdict = result.verdict

        if not result.investable:
            project.status = "NOT_INVESTABLE"
        else:
            project.status = "SCREENING"  # Will progress to RESEARCHING

        project.updated_at = datetime.now(timezone.utc)

        # Populate Template 00: Idea Screen
        template_data = {
            "ticker": project.ticker,
            "companyName": result.company_name,
            "verdict": result.verdict,
            "investable": result.investable,
            "sector": result.sector,
            "exchange": result.exchange,
            "marketCapBillions": result.market_cap_billions,
            "liquidityCheck": result.liquidity_check.model_dump(),
            "redFlags": result.red_flags,
            "rationale": result.rationale,
            "keyMetrics": result.key_metrics,
            "yfinanceData": {
                k: v for k, v in yf_data.items()
                if k not in ("description",)  # Exclude long text from template
            },
        }

        template = (
            db.query(HFRTTemplate)
            .filter(
                HFRTTemplate.project_id == project.id,
                HFRTTemplate.template_number == 0,
            )
            .first()
        )
        if template:
            template.data = json.dumps(template_data, default=str)
            template.status = "POPULATED"
            template.updated_at = datetime.now(timezone.utc)

        db.commit()

        return {
            "ticker": project.ticker,
            "verdict": result.verdict,
            "investable": result.investable,
            "redFlags": result.red_flags,
        }
    finally:
        db.close()
