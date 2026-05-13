"""HFRT Phase 3: Risk & Due Diligence — SEC filing fetch, management, risk, earnings quality.

Registered steps:
  - fetch_sec_filings — fetches 10-K, 10-Q, DEF 14A from SEC EDGAR
  - management_assessment (Template 07) — governance, compensation, track record
  - risk_analysis (Template 08) — risk register with probability × impact scoring
  - quality_of_earnings (Template 09) — accrual ratio, cash flow quality
  - dd_sufficiency_gate — validates DD completeness
  - external_validation (Gap 1) — Perplexity-grounded factual claim verification
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models.hfrt import HFRTProject, HFRTTemplate, HFRTSECFiling
from app.services.claude_client import call_claude, get_step_model_tier
from app.services.hfrt.edgar_service import (
    fetch_filing,
    get_filing_content,
    extract_filing_sections,
)
from app.services.perplexity_client import is_available as perplexity_available, search_and_analyze
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

Use ONLY SEC filing data provided in XML tags above.
NEVER fabricate management names, compensation figures, tenure dates, or governance details.
If a specific executive is not mentioned in the provided filing data, do not invent their details.
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

Use ONLY SEC filing data provided in XML tags above.
NEVER fabricate risk factors, litigation details, or regulatory actions not present in the provided data.
Do NOT invent specific dollar amounts for risk impacts unless supported by the provided data.
Return ONLY valid JSON matching the schema provided."""

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

Use ONLY SEC filing data provided in XML tags above.
NEVER fabricate financial figures, accounting judgments, or footnote citations.
Return null for any ratio that cannot be computed from the provided data — do NOT estimate.
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

        # Gap 4: Invalidate template context cache so Phase 5 picks up fresh SEC data
        from app.services.hfrt.thesis_synthesizer import clear_template_context_cache
        clear_template_context_cache(project.id)
        logger.info("Cleared template context cache for project %d after SEC filing fetch", project.id)

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

        model = await get_step_model_tier(workflow_run_id, "management_assessment")
        result = await call_claude(
            system_prompt=MANAGEMENT_PROMPT,
            user_prompt=user_prompt,
            response_model=ManagementAssessmentResult,
            model=model,
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

        # Optionally enrich with current regulatory/litigation risks from Perplexity
        risk_data_block = ""
        if perplexity_available():
            try:
                pplx = await search_and_analyze(
                    system_prompt=(
                        "You are a risk analyst. Identify current regulatory threats, "
                        "pending litigation, enforcement actions, and other material "
                        "risks for the given company. Focus on recent developments."
                    ),
                    user_prompt=(
                        f"Current regulatory threats, pending litigation, and material "
                        f"risk developments for {project.ticker} ({project.company_name})"
                    ),
                    model="sonar-pro",
                    max_tokens=4096,
                    workflow_run_id=workflow_run_id,
                )
                risk_data_block = (
                    f"<current_risk_data>\n{pplx.content}\n</current_risk_data>\n\n"
                )
                logger.info("Perplexity risk enrichment: %d citations", len(pplx.citations))
            except Exception:
                logger.warning("Perplexity risk enrichment failed, continuing without", exc_info=True)

        user_prompt = (
            f"{risk_data_block}"
            f"<risk_factors_10k>\n{risk_factors}\n</risk_factors_10k>\n\n"
            f"<company_overview>\n{json.dumps(overview, indent=2, default=str)[:3000]}\n</company_overview>\n\n"
            f"<competitive_position>\n{json.dumps(competitive, indent=2, default=str)[:3000]}\n</competitive_position>\n\n"
            f"<financial_analysis>\n{json.dumps(financials, indent=2, default=str)[:3000]}\n</financial_analysis>\n\n"
            f"Build a comprehensive risk analysis for {project.ticker} ({project.company_name}).\n"
            f"Return JSON matching this schema: {RiskAnalysisResult.model_json_schema()}"
        )

        model = await get_step_model_tier(workflow_run_id, "risk_analysis")
        result = await call_claude(
            system_prompt=RISK_PROMPT,
            user_prompt=user_prompt,
            response_model=RiskAnalysisResult,
            model=model,
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

        model = await get_step_model_tier(workflow_run_id, "quality_of_earnings")
        result = await call_claude(
            system_prompt=EARNINGS_QUALITY_PROMPT,
            user_prompt=user_prompt,
            response_model=QualityOfEarningsResult,
            model=model,
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


# ── Gap 1: External Validation Pydantic models ───────────────────────────────


class HFRTClaimForValidation(BaseModel):
    """A single factual claim extracted from research templates for validation."""
    claim_id: str
    claim_text: str
    template_source: str = ""
    claim_type: str = Field(description="quantitative or qualitative")


class HFRTClaimExtractionResult(BaseModel):
    """Claims extracted from research templates ready for Perplexity search."""
    claims: list[HFRTClaimForValidation] = Field(default_factory=list)


class HFRTValidationItem(BaseModel):
    """Verdict for a single claim after Perplexity search + Claude verification."""
    claim_id: str
    claim_text: str
    verdict: str = Field(description="confirmed, partially_confirmed, contradicted, or unvalidatable")
    evidence: str = ""
    confidence: str = Field(description="high, medium, low")
    source_url: Optional[str] = None


class HFRTValidationResult(BaseModel):
    """Aggregate external validation result for a project."""
    claims_validated: int = 0
    confirmed: int = 0
    partially_confirmed: int = 0
    contradicted: int = 0
    unvalidatable: int = 0
    items: list[HFRTValidationItem] = Field(default_factory=list)
    overall_confidence: str = ""
    key_contradictions: list[str] = Field(default_factory=list)


# ── Gap 1: External Validation Step Handler ───────────────────────────────────


CLAIM_EXTRACTION_PROMPT = """You are a research analyst extracting verifiable factual claims.

Review the provided research templates and extract up to 20 key factual claims that can be
verified against external sources. Focus on:
- Specific financial metrics (revenue, margins, growth rates, market share)
- Management facts (tenure, compensation, track record)
- Competitive positions (market share, rankings, comparisons)
- Industry facts (market size, growth rates, regulatory actions)

For each claim, label it as 'quantitative' (has specific numbers) or 'qualitative' (descriptive).

Return ONLY valid JSON matching the schema."""

CLAIM_VERIFICATION_PROMPT = """You are a fact-checking analyst verifying research claims against search results.

For each claim, review the Perplexity search result and determine:
- confirmed: search clearly supports the claim
- partially_confirmed: search broadly supports but with qualifications
- contradicted: search contradicts the claim with evidence
- unvalidatable: search result insufficient to verify the claim

Return ONLY valid JSON matching the schema."""


@register_step("HFRT", "external_validation")
async def handle_external_validation(workflow_run_id: int) -> dict | None:
    """Perplexity-grounded external validation of key research claims (Gap 1).

    Steps:
      1. Claude extracts up to 20 verifiable claims from Templates 01-09
      2. Perplexity (sonar-pro for quant, sonar for qual) searches each claim
      3. Claude verifies each claim against search results → verdict
      4. Results stored in project.external_validation_results as JSON
    """
    from app.services.perplexity_client import is_available as perplexity_available
    from app.services.perplexity_client import search_and_analyze

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
            "stepName": "external_validation",
            "message": "Extracting claims for validation...",
            "percent": 10,
        })

        # Gather Templates 01-09 as context
        context_parts = []
        for num in range(1, 10):
            data = _get_template_data(db, project.id, num)
            if data:
                data_str = json.dumps(data, indent=2, default=str)[:2000]
                context_parts.append(f"<template_{num:02d}>\n{data_str}\n</template_{num:02d}>")
        context = "\n\n".join(context_parts)

        if not context.strip():
            logger.warning("No template data available for external validation — skipping")
            return {"skipped": True, "reason": "No template data to validate"}

        # Step 1: Extract claims via Claude
        from app.services.claude_client import call_claude, get_step_model_tier
        model = await get_step_model_tier(workflow_run_id, "external_validation")

        extraction_prompt = (
            f"<research_templates>\n{context}\n</research_templates>\n\n"
            f"Extract up to 20 verifiable factual claims from the above research "
            f"for {project.ticker} ({project.company_name or ''}).\n"
            f"Return JSON matching this schema: {HFRTClaimExtractionResult.model_json_schema()}"
        )

        extracted = await call_claude(
            system_prompt=CLAIM_EXTRACTION_PROMPT,
            user_prompt=extraction_prompt,
            response_model=HFRTClaimExtractionResult,
            model=model,
        )
        claims = extracted.claims[:20]

        await emit_sse_event(workflow_run_id, "step_progress", {
            "stepName": "external_validation",
            "message": f"Validating {len(claims)} claims via Perplexity...",
            "percent": 25,
        })

        # Derive source date for temporal context
        source_date = project.created_at.strftime("%Y-%m-%d") if project.created_at else None

        # Step 2: Perplexity search for each claim
        validation_items: list[HFRTValidationItem] = []

        if perplexity_available() and claims:
            for i, claim in enumerate(claims):
                try:
                    # Use sonar-pro for quantitative, sonar for qualitative
                    pplx_model = "sonar-pro" if claim.claim_type == "quantitative" else "sonar"
                    temporal_hint = ""
                    if source_date:
                        temporal_hint = (
                            f" This research was conducted on {source_date} "
                            f"(current year: {source_date[:4]}). Interpret any "
                            f"ambiguous dates relative to this date."
                        )
                    search_result = await search_and_analyze(
                        system_prompt=(
                            "You are a financial fact-checker. Search for information "
                            "to verify or refute the given claim. Provide specific evidence."
                            + temporal_hint
                        ),
                        user_prompt=(
                            f"Verify this claim about {project.ticker}: {claim.claim_text}"
                        ),
                        model=pplx_model,
                        max_tokens=1024,
                        workflow_run_id=workflow_run_id,
                    )

                    # Step 3: Claude verification against search result
                    temporal_block = ""
                    if source_date:
                        temporal_block = (
                            f"<temporal_context>\n"
                            f"This research was conducted on {source_date}. "
                            f"The current year is {source_date[:4]}. Interpret ambiguous "
                            f"dates relative to this date.\n"
                            f"</temporal_context>\n\n"
                        )
                    verify_prompt = (
                        f"{temporal_block}"
                        f"<claim>\n{claim.claim_text}\n</claim>\n\n"
                        f"<search_result>\n{search_result.content[:3000]}\n</search_result>\n\n"
                        f"Verify this claim against the search result.\n"
                        f"Return JSON matching this schema: {HFRTValidationItem.model_json_schema()}"
                    )
                    # Fill required fields in case Claude omits them
                    verify_item_schema = HFRTValidationItem.model_json_schema()

                    verdict_result = await call_claude(
                        system_prompt=CLAIM_VERIFICATION_PROMPT,
                        user_prompt=verify_prompt,
                        response_model=HFRTValidationItem,
                        model=model,
                    )
                    # Ensure claim_id matches
                    verdict_result.claim_id = claim.claim_id
                    verdict_result.claim_text = claim.claim_text
                    validation_items.append(verdict_result)

                    percent = 25 + int((i + 1) / len(claims) * 60)
                    await emit_sse_event(workflow_run_id, "step_progress", {
                        "stepName": "external_validation",
                        "message": f"Validated {i+1}/{len(claims)} claims...",
                        "percent": percent,
                    })

                except Exception as exc:
                    logger.warning("Perplexity validation failed for claim %s: %s", claim.claim_id, exc)
                    validation_items.append(HFRTValidationItem(
                        claim_id=claim.claim_id,
                        claim_text=claim.claim_text,
                        verdict="unvalidatable",
                        evidence=f"Search failed: {str(exc)[:200]}",
                        confidence="low",
                    ))
        else:
            # Perplexity not available — mark all as unvalidatable
            for claim in claims:
                validation_items.append(HFRTValidationItem(
                    claim_id=claim.claim_id,
                    claim_text=claim.claim_text,
                    verdict="unvalidatable",
                    evidence="Perplexity not available",
                    confidence="low",
                ))

        # Aggregate results
        confirmed = sum(1 for v in validation_items if v.verdict == "confirmed")
        partially = sum(1 for v in validation_items if v.verdict == "partially_confirmed")
        contradicted = sum(1 for v in validation_items if v.verdict == "contradicted")
        unvalidatable = sum(1 for v in validation_items if v.verdict == "unvalidatable")

        total = len(validation_items)
        if total > 0:
            confirm_rate = (confirmed + partially) / total
            if confirm_rate >= 0.8:
                overall_confidence = "high"
            elif confirm_rate >= 0.5:
                overall_confidence = "medium"
            else:
                overall_confidence = "low"
        else:
            overall_confidence = "low"

        contradictions = [v.claim_text for v in validation_items if v.verdict == "contradicted"]

        validation_result = HFRTValidationResult(
            claims_validated=total,
            confirmed=confirmed,
            partially_confirmed=partially,
            contradicted=contradicted,
            unvalidatable=unvalidatable,
            items=validation_items,
            overall_confidence=overall_confidence,
            key_contradictions=contradictions[:5],
        )

        # Step 4: Store results in project
        project.external_validation_results = json.dumps(
            validation_result.model_dump(), default=str
        )
        project.updated_at = datetime.now(timezone.utc)
        db.commit()

        await emit_sse_event(workflow_run_id, "step_progress", {
            "stepName": "external_validation",
            "message": f"Validation complete: {confirmed} confirmed, {contradicted} contradicted",
            "percent": 100,
        })

        return {
            "claims_validated": total,
            "confirmed": confirmed,
            "partially_confirmed": partially,
            "contradicted": contradicted,
            "unvalidatable": unvalidatable,
            "overall_confidence": overall_confidence,
        }
    finally:
        db.close()
