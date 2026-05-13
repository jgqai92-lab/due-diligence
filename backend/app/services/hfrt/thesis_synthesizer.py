"""HFRT Phase 5: Thesis Synthesis — catalyst, thesis, bull/bear synthesis, memo, certification.

Registered steps:
  - catalyst_analysis (Template 10)
  - investment_thesis (Template 11) — 6-factor conviction scoring
  - bull_synthesis (Template 12) — synthesized bull narrative
  - bear_synthesis (Template 13) — synthesized bear narrative
  - thesis_coherence_gate — validates bull/bear balance
  - investment_memo (Template 14) — full markdown memo
  - research_certification — certifies 8 invariants
  - complete — marks project as COMPLETED
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models.hfrt import HFRTProject, HFRTTemplate, HFRTDialecticReview
from app.services.claude_client import call_claude, call_claude_raw, get_step_model_tier
from app.services.perplexity_client import is_available as perplexity_available, search_and_analyze
from app.services.workflow_engine import register_step, emit_sse_event

logger = logging.getLogger(__name__)


# ── Template context cache (per-project, cleared after workflow completes) ────
_template_context_cache: dict[int, str] = {}


def _get_cached_template_context(db, project_id: int, max_chars_per: int = 3000) -> str:
    """Return cached template context or build and cache it."""
    if project_id in _template_context_cache:
        logger.info("Template context cache HIT for project %d", project_id)
        return _template_context_cache[project_id]
    logger.info("Template context cache MISS for project %d", project_id)
    result = _gather_all_templates(db, project_id, max_chars_per)
    _template_context_cache[project_id] = result
    return result


def clear_template_context_cache(project_id: int | None = None) -> None:
    """Clear cached template context. Call after workflow completes or on rerun."""
    if project_id is not None:
        _template_context_cache.pop(project_id, None)
    else:
        _template_context_cache.clear()


# ── Pydantic models ──────────────────────────────────────────────────────────


class CatalystAnalysisResult(BaseModel):
    catalysts: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    probability_matrix: list[dict[str, Any]] = Field(default_factory=list)
    key_catalyst: str = ""
    expected_timeline: str = ""


class ConvictionFactor(BaseModel):
    score: float = Field(ge=0, le=1)
    rationale: str


class InvestmentThesisResult(BaseModel):
    thesis_statement: str
    conviction_factors: dict[str, ConvictionFactor] = Field(default_factory=dict)
    overall_conviction_score: float = Field(ge=0, le=1)
    recommendation: str = Field(description="BUY, HOLD, SELL, or PASS")
    position_tier: str = Field(description="FULL, HALF, QUARTER, or WATCH")
    price_target: Optional[float] = None
    risk_reward_ratio: Optional[str] = None
    key_assumption: str = ""
    thesis_kill_conditions: list[str] = Field(default_factory=list)


class SynthesisResult(BaseModel):
    narrative: str
    key_points: list[str] = Field(default_factory=list)
    resolution: str = ""


class CoherenceResult(BaseModel):
    passes: bool
    bull_bear_balance: str = ""
    deficiencies: list[str] = Field(default_factory=list)


# ── System prompts ───────────────────────────────────────────────────────────

CATALYST_PROMPT = """You are an equity research analyst identifying catalysts.

Analyze the research data to identify:
1. Near-term catalysts (0-6 months): earnings, product launches, regulatory decisions
2. Medium-term catalysts (6-18 months): market expansion, M&A, restructuring
3. Long-term catalysts (18+ months): secular trends, moat strengthening
4. Probability assessment for each catalyst
5. Timeline visualization

For each catalyst, provide date/timeframe, description, probability, and expected impact.

Every data point MUST come from the provided templates in XML tags above.
NEVER fabricate catalysts, timeline estimates, or probability figures not grounded in the provided data.
Do NOT invent specific earnings dates or event dates unless explicitly mentioned in the provided data.
Return ONLY valid JSON matching the schema."""

THESIS_PROMPT = """You are a senior equity research analyst writing an investment thesis.

Score conviction using 6 factors (each 0-1.0):
1. Catalyst Clarity (20%): Are catalysts identified, specific, and timely?
2. Downside Quantification (20%): Is the downside scenario quantified with specific price levels?
3. Moat Durability (15%): How durable is the competitive advantage over a 5-year horizon?
4. Management Quality (15%): Does management have the track record and incentive alignment to execute?
5. Earnings Quality (15%): Is reported earnings quality high (cash conversion, accruals, revenue recognition)?
6. Valuation Margin (15%): Does the current price offer sufficient margin of safety to intrinsic value?

Overall = weighted average using the weights above.

Recommend: BUY (>0.7), HOLD (0.4-0.7), SELL (<0.4 with deterioration), PASS (<0.4 without position)
Position: FULL (>0.8), HALF (0.6-0.8), QUARTER (0.4-0.6), WATCH (<0.4)

Include thesis kill conditions — specific events that would invalidate the thesis.

Every data point MUST come from the provided templates in XML tags above.
NEVER fabricate price targets, conviction factors, or kill conditions not grounded in the provided data.
Return ONLY valid JSON matching the schema."""

SYNTHESIS_PROMPT = """You are a synthesis analyst combining multiple perspectives into a coherent narrative.

Review the provided case and research data, then produce:
1. A coherent synthesis narrative
2. Key points extracted
3. Resolution of any tensions or contradictions

Every data point MUST come from the provided templates in XML tags above.
NEVER fabricate synthesis conclusions, price targets, or investment arguments not grounded in the provided case data.
Return ONLY valid JSON matching the schema."""

MEMO_PROMPT = """You are a senior equity research analyst writing the FINAL investment memo.

This memo synthesizes ALL research into a single deliverable. Structure:

1. EXECUTIVE SUMMARY (1 paragraph)
2. INVESTMENT THESIS
3. COMPANY OVERVIEW
4. COMPETITIVE POSITION
5. FINANCIAL ANALYSIS
6. VALUATION
7. RISK ANALYSIS
8. CATALYSTS
9. BULL/BEAR SYNTHESIS
10. RECOMMENDATION & POSITION SIZING
11. KEY MONITORING METRICS

Write in clear, professional prose. Include specific data points with citations.

Every data point MUST come from the provided templates in XML tags above.
NEVER fabricate financial figures, price targets, executive names, or investment conclusions not present in the provided templates.
Return ONLY the memo text with no additional commentary."""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_template_data(db, project_id: int, template_number: int) -> dict | None:
    template = (
        db.query(HFRTTemplate)
        .filter(HFRTTemplate.project_id == project_id, HFRTTemplate.template_number == template_number)
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
        .filter(HFRTTemplate.project_id == project_id, HFRTTemplate.template_number == template_number)
        .first()
    )
    if template:
        template.data = json.dumps(data, default=str)
        template.status = "POPULATED"
        template.updated_at = datetime.now(timezone.utc)


def _get_dialectic(db, project_id: int, side: str) -> dict | None:
    review = (
        db.query(HFRTDialecticReview)
        .filter(HFRTDialecticReview.project_id == project_id, HFRTDialecticReview.side == side)
        .first()
    )
    if review and review.content:
        try:
            return json.loads(review.content)
        except (ValueError, TypeError):
            return None
    return None


def _gather_all_templates(db, project_id: int, max_chars_per: int = 3000) -> str:
    """Gather all populated templates as context (Gap 4: + SEC filing sections + yfinance snapshot)."""
    parts = []

    # Templates 00-14
    for num in range(15):
        data = _get_template_data(db, project_id, num)
        if data:
            data_str = json.dumps(data, indent=2, default=str)[:max_chars_per]
            parts.append(f"<template_{num:02d}>\n{data_str}\n</template_{num:02d}>")

    # SEC filing key sections (Gap 4)
    try:
        from app.models.hfrt import HFRTProject, HFRTSECFiling
        from app.services.hfrt.edgar_service import extract_filing_sections

        project = db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
        if project:
            sec_parts = []
            for filing_type in ("10-K", "10-Q", "DEF 14A"):
                filing = (
                    db.query(HFRTSECFiling)
                    .filter(
                        HFRTSECFiling.project_id == project_id,
                        HFRTSECFiling.filing_type == filing_type,
                    )
                    .order_by(HFRTSECFiling.fetched_at.desc())
                    .first()
                )
                if filing and filing.content:
                    sections = extract_filing_sections(filing.content)
                    for section_key in ("business", "risk_factors", "md_and_a"):
                        section_text = sections.get(section_key, "")
                        if section_text:
                            sec_parts.append(
                                f"<{section_key} filing_type=\"{filing_type}\">\n"
                                f"{section_text[:2000]}\n"
                                f"</{section_key}>"
                            )
            if sec_parts:
                parts.append(
                    "<sec_filing>\n" + "\n\n".join(sec_parts) + "\n</sec_filing>"
                )
    except Exception as exc:
        logger.warning("Gap 4: SEC filing section enrichment failed: %s", exc)

    # yfinance snapshot (Gap 4)
    try:
        from app.models.hfrt import HFRTProject
        from app.services.hfrt.data_cache import get_yfinance_info

        project = db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
        if project:
            info = get_yfinance_info(project.ticker)
            snapshot_keys = (
                "marketCap", "trailingPE", "forwardPE", "priceToBook",
                "enterpriseToEbitda", "beta", "dividendYield",
                "totalRevenue", "ebitda", "freeCashflow",
                "totalDebt", "totalCash", "currentPrice",
            )
            snapshot = {k: info.get(k) for k in snapshot_keys if info.get(k) is not None}
            if snapshot:
                parts.append(
                    f"<yfinance_snapshot>\n"
                    f"{json.dumps(snapshot, indent=2, default=str)}\n"
                    f"</yfinance_snapshot>"
                )
    except Exception as exc:
        logger.warning("Gap 4: yfinance snapshot enrichment failed: %s", exc)

    return "\n\n".join(parts)


# ── Step handlers ────────────────────────────────────────────────────────────


@register_step("HFRT", "catalyst_analysis")
async def handle_catalyst_analysis(workflow_run_id: int) -> dict | None:
    """Generate Template 10: Catalyst Analysis."""
    db = SessionLocal()
    try:
        project = (
            db.query(HFRTProject)
            .filter(HFRTProject.workflow_run_id == workflow_run_id)
            .first()
        )
        if not project:
            raise ValueError(f"No HFRT project for workflow {workflow_run_id}")

        project.status = "SYNTHESIZING"
        project.updated_at = datetime.now(timezone.utc)
        db.commit()

        await emit_sse_event(workflow_run_id, "step_progress", {
            "stepName": "catalyst_analysis", "message": "Identifying catalysts...", "percent": 10,
        })

        context = _get_cached_template_context(db, project.id, max_chars_per=2500)
        bull = _get_dialectic(db, project.id, "BULL")
        bear = _get_dialectic(db, project.id, "BEAR")

        # Optionally enrich with real upcoming events from Perplexity
        catalyst_data_block = ""
        if perplexity_available():
            try:
                pplx = await search_and_analyze(
                    system_prompt=(
                        "You are a financial events researcher. Find upcoming "
                        "earnings dates, product launches, regulatory decisions, "
                        "analyst days, and other material events for this company. "
                        "Provide specific dates where available."
                    ),
                    user_prompt=(
                        f"Upcoming catalysts and events for "
                        f"{project.ticker} ({project.company_name})"
                    ),
                    model="sonar",
                    max_tokens=4096,
                    workflow_run_id=workflow_run_id,
                )
                catalyst_data_block = (
                    f"<verified_upcoming_events>\n{pplx.content}\n</verified_upcoming_events>\n\n"
                )
                logger.info("Perplexity catalyst enrichment: %d citations", len(pplx.citations))
            except Exception:
                logger.warning("Perplexity catalyst enrichment failed, continuing without", exc_info=True)

        user_prompt = (
            f"{catalyst_data_block}"
            f"<research_data>\n{context}\n</research_data>\n\n"
            f"<bull_case>\n{json.dumps(bull, indent=2, default=str)[:3000]}\n</bull_case>\n\n"
            f"<bear_case>\n{json.dumps(bear, indent=2, default=str)[:3000]}\n</bear_case>\n\n"
            f"Identify and analyze catalysts for {project.ticker} ({project.company_name}).\n"
            f"Return JSON matching this schema: {CatalystAnalysisResult.model_json_schema()}"
        )

        model = await get_step_model_tier(workflow_run_id, "catalyst_analysis")
        result = await call_claude(
            system_prompt=CATALYST_PROMPT,
            user_prompt=user_prompt,
            response_model=CatalystAnalysisResult,
            model=model,
        )

        _save_template(db, project.id, 10, result.model_dump())
        db.commit()
        return {"template": 10, "catalysts": len(result.catalysts)}
    finally:
        db.close()


@register_step("HFRT", "investment_thesis")
async def handle_investment_thesis(workflow_run_id: int) -> dict | None:
    """Generate Template 11: Investment Thesis with 6-factor conviction scoring."""
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
            "stepName": "investment_thesis", "message": "Scoring conviction...", "percent": 10,
        })

        context = _get_cached_template_context(db, project.id, max_chars_per=2000)
        bull = _get_dialectic(db, project.id, "BULL")
        bear = _get_dialectic(db, project.id, "BEAR")

        user_prompt = (
            f"<research_data>\n{context}\n</research_data>\n\n"
            f"<bull_case>\n{json.dumps(bull, indent=2, default=str)[:3000]}\n</bull_case>\n\n"
            f"<bear_case>\n{json.dumps(bear, indent=2, default=str)[:3000]}\n</bear_case>\n\n"
            f"Write the investment thesis and score conviction for {project.ticker} ({project.company_name}).\n"
            f"Return JSON matching this schema: {InvestmentThesisResult.model_json_schema()}"
        )

        model = await get_step_model_tier(workflow_run_id, "investment_thesis")
        result = await call_claude(
            system_prompt=THESIS_PROMPT,
            user_prompt=user_prompt,
            response_model=InvestmentThesisResult,
            model=model,
        )

        # Update project with thesis results
        project.conviction_score = result.overall_conviction_score
        project.position_tier = result.position_tier
        project.recommendation = result.recommendation
        project.updated_at = datetime.now(timezone.utc)

        _save_template(db, project.id, 11, result.model_dump())
        db.commit()

        return {
            "template": 11,
            "conviction": result.overall_conviction_score,
            "recommendation": result.recommendation,
        }
    finally:
        db.close()


@register_step("HFRT", "bull_synthesis")
async def handle_bull_synthesis(workflow_run_id: int) -> dict | None:
    """Generate Template 12: Bull Synthesis."""
    db = SessionLocal()
    try:
        project = (
            db.query(HFRTProject)
            .filter(HFRTProject.workflow_run_id == workflow_run_id)
            .first()
        )
        if not project:
            raise ValueError(f"No HFRT project for workflow {workflow_run_id}")

        bull = _get_dialectic(db, project.id, "BULL")
        thesis = _get_template_data(db, project.id, 11)
        catalysts = _get_template_data(db, project.id, 10)

        user_prompt = (
            f"<bull_case>\n{json.dumps(bull, indent=2, default=str)[:5000]}\n</bull_case>\n\n"
            f"<investment_thesis>\n{json.dumps(thesis, indent=2, default=str)[:3000]}\n</investment_thesis>\n\n"
            f"<catalysts>\n{json.dumps(catalysts, indent=2, default=str)[:2000]}\n</catalysts>\n\n"
            f"Synthesize the bull case for {project.ticker} into a coherent narrative.\n"
            f"Return JSON matching this schema: {SynthesisResult.model_json_schema()}"
        )

        model = await get_step_model_tier(workflow_run_id, "bull_synthesis")
        result = await call_claude(
            system_prompt=SYNTHESIS_PROMPT,
            user_prompt=user_prompt,
            response_model=SynthesisResult,
            model=model,
        )

        _save_template(db, project.id, 12, result.model_dump())
        db.commit()
        return {"template": 12}
    finally:
        db.close()


@register_step("HFRT", "bear_synthesis")
async def handle_bear_synthesis(workflow_run_id: int) -> dict | None:
    """Generate Template 13: Bear Synthesis."""
    db = SessionLocal()
    try:
        project = (
            db.query(HFRTProject)
            .filter(HFRTProject.workflow_run_id == workflow_run_id)
            .first()
        )
        if not project:
            raise ValueError(f"No HFRT project for workflow {workflow_run_id}")

        bear = _get_dialectic(db, project.id, "BEAR")
        thesis = _get_template_data(db, project.id, 11)

        user_prompt = (
            f"<bear_case>\n{json.dumps(bear, indent=2, default=str)[:5000]}\n</bear_case>\n\n"
            f"<investment_thesis>\n{json.dumps(thesis, indent=2, default=str)[:3000]}\n</investment_thesis>\n\n"
            f"Synthesize the bear case for {project.ticker} into a coherent narrative.\n"
            f"Return JSON matching this schema: {SynthesisResult.model_json_schema()}"
        )

        model = await get_step_model_tier(workflow_run_id, "bear_synthesis")
        result = await call_claude(
            system_prompt=SYNTHESIS_PROMPT,
            user_prompt=user_prompt,
            response_model=SynthesisResult,
            model=model,
        )

        _save_template(db, project.id, 13, result.model_dump())
        db.commit()
        return {"template": 13}
    finally:
        db.close()


@register_step("HFRT", "thesis_coherence_gate")
async def handle_thesis_coherence_gate(workflow_run_id: int) -> dict | None:
    """Validate bull/bear synthesis balance (Gap 5: server-side pre-checks + Claude balance check)."""
    db = SessionLocal()
    try:
        project = (
            db.query(HFRTProject)
            .filter(HFRTProject.workflow_run_id == workflow_run_id)
            .first()
        )
        if not project:
            raise ValueError(f"No HFRT project for workflow {workflow_run_id}")

        bull_syn = _get_template_data(db, project.id, 12)
        bear_syn = _get_template_data(db, project.id, 13)
        thesis = _get_template_data(db, project.id, 11)

        # Gap 5: Server-side pre-checks BEFORE the Claude call
        server_deficiencies: list[str] = []

        # 1. Bull/bear syntheses both exist with non-empty narratives
        if not bull_syn or not bull_syn.get("narrative", "").strip():
            server_deficiencies.append("Bull synthesis is missing or has an empty narrative")
        if not bear_syn or not bear_syn.get("narrative", "").strip():
            server_deficiencies.append("Bear synthesis is missing or has an empty narrative")

        # 2. Conviction score in valid range [0, 1]
        conviction = (thesis or {}).get("overall_conviction_score")
        if conviction is None:
            server_deficiencies.append("Investment thesis is missing overall_conviction_score")
        elif not (0.0 <= float(conviction) <= 1.0):
            server_deficiencies.append(
                f"Conviction score {conviction} is out of valid range [0, 1]"
            )

        # 3. At least 2 kill conditions defined
        kill_conditions = (thesis or {}).get("thesis_kill_conditions", [])
        if len(kill_conditions) < 2:
            server_deficiencies.append(
                f"Only {len(kill_conditions)} kill condition(s) defined; at least 2 required"
            )

        # 4. Valid recommendation
        recommendation = (thesis or {}).get("recommendation", "")
        if recommendation not in ("BUY", "HOLD", "SELL", "PASS"):
            server_deficiencies.append(
                f"Invalid recommendation '{recommendation}'; must be BUY, HOLD, SELL, or PASS"
            )

        # 5. Key templates (01, 05, 06, 08) are populated
        required_templates = {1: "Company Overview", 5: "Financial Analysis", 6: "Valuation", 8: "Risk Analysis"}
        for tpl_num, tpl_name in required_templates.items():
            tpl_data = _get_template_data(db, project.id, tpl_num)
            if not tpl_data:
                server_deficiencies.append(f"Template {tpl_num:02d} ({tpl_name}) is not populated")

        # If server pre-checks catch hard failures, skip Claude call and fail immediately
        if server_deficiencies:
            all_deficiencies = server_deficiencies
            await emit_sse_event(workflow_run_id, "gate_failed", {
                "gateName": "thesis_coherence_gate",
                "deficiencies": all_deficiencies,
                "source": "server_pre_check",
            })
            return {
                "gate": "thesis_coherence",
                "passes": False,
                "deficiencies": all_deficiencies,
                "source": "server_pre_check",
            }

        # Server pre-checks passed — run Claude balance assessment
        user_prompt = (
            f"<bull_synthesis>\n{json.dumps(bull_syn, indent=2, default=str)[:4000]}\n</bull_synthesis>\n\n"
            f"<bear_synthesis>\n{json.dumps(bear_syn, indent=2, default=str)[:4000]}\n</bear_synthesis>\n\n"
            f"<investment_thesis>\n{json.dumps(thesis, indent=2, default=str)[:3000]}\n</investment_thesis>\n\n"
            f"Check if the bull and bear cases are balanced and coherent for {project.ticker}.\n"
            f"Return JSON matching this schema: {CoherenceResult.model_json_schema()}"
        )

        model = await get_step_model_tier(workflow_run_id, "thesis_coherence_gate")
        result = await call_claude(
            system_prompt="You are a quality assurance analyst checking thesis coherence. Return ONLY valid JSON.",
            user_prompt=user_prompt,
            response_model=CoherenceResult,
            model=model,
        )

        # Gap 5: Merge server-side deficiencies (empty here) with Claude's findings
        # Gate fails if EITHER set has issues
        all_deficiencies = server_deficiencies + result.deficiencies
        passes = len(all_deficiencies) == 0

        if not passes:
            await emit_sse_event(workflow_run_id, "gate_failed", {
                "gateName": "thesis_coherence_gate",
                "deficiencies": all_deficiencies,
            })

        return {
            "gate": "thesis_coherence",
            "passes": passes,
            "deficiencies": all_deficiencies,
        }
    finally:
        db.close()


@register_step("HFRT", "investment_memo")
async def handle_investment_memo(workflow_run_id: int) -> dict | None:
    """Generate Template 14: Full Investment Memo (markdown)."""
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
            "stepName": "investment_memo", "message": "Writing investment memo...", "percent": 10,
        })

        context = _get_cached_template_context(db, project.id, max_chars_per=2500)
        bull = _get_dialectic(db, project.id, "BULL")
        bear = _get_dialectic(db, project.id, "BEAR")

        user_prompt = (
            f"<all_templates>\n{context}\n</all_templates>\n\n"
            f"<bull_case>\n{json.dumps(bull, indent=2, default=str)[:3000]}\n</bull_case>\n\n"
            f"<bear_case>\n{json.dumps(bear, indent=2, default=str)[:3000]}\n</bear_case>\n\n"
            f"Write a comprehensive investment memo for {project.ticker} ({project.company_name}).\n"
            f"Structure with: Executive Summary, Investment Thesis, Company Overview, "
            f"Competitive Position, Financial Analysis, Valuation, Risk Analysis, "
            f"Catalysts, Bull/Bear Synthesis, Recommendation & Position Sizing, "
            f"Key Monitoring Metrics."
        )

        model = await get_step_model_tier(workflow_run_id, "investment_memo")
        memo_content = await call_claude_raw(
            system_prompt=MEMO_PROMPT,
            user_prompt=user_prompt,
            model=model,
            max_tokens=16384,
        )

        memo_data = {
            "title": f"Investment Memo: {project.ticker} ({project.company_name})",
            "content": memo_content,
            "convictionScore": project.conviction_score,
            "recommendation": project.recommendation,
            "positionTier": project.position_tier,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }

        _save_template(db, project.id, 14, memo_data)
        db.commit()

        return {"template": 14, "wordCount": len(memo_content.split())}
    finally:
        db.close()


@register_step("HFRT", "research_certification")
async def handle_research_certification(workflow_run_id: int) -> dict | None:
    """Run 8 HFRT invariant checks via centralized checker and store results."""
    from app.services.hfrt.invariant_checker import check_all_invariants

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
            "stepName": "research_certification", "message": "Running invariant checks...", "percent": 30,
        })

        # Delegate to centralized invariant checker (Gap B3)
        invariants = check_all_invariants(project.id)

        all_passed = all(inv["status"] == "PASS" for inv in invariants)

        # Store invariant results on project
        project.invariant_results = json.dumps(invariants, default=str)

        # Update memo template with invariant results
        memo_template = (
            db.query(HFRTTemplate)
            .filter(HFRTTemplate.project_id == project.id, HFRTTemplate.template_number == 14)
            .first()
        )
        if memo_template and memo_template.data:
            try:
                memo_data = json.loads(memo_template.data)
                memo_data["invariants"] = invariants
                memo_data["allInvariantsPassed"] = all_passed
                memo_template.data = json.dumps(memo_data, default=str)
                memo_template.updated_at = datetime.now(timezone.utc)
            except (ValueError, TypeError):
                pass

        # Certify project if all passed
        if all_passed:
            project.is_certified = 1
            project.certified_at = datetime.now(timezone.utc)

        project.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "invariants_checked": len(invariants),
            "all_passed": all_passed,
            "certified": all_passed,
        }
    finally:
        db.close()


@register_step("HFRT", "complete")
async def handle_complete(workflow_run_id: int) -> dict | None:
    """Mark the project as COMPLETED."""
    db = SessionLocal()
    try:
        project = (
            db.query(HFRTProject)
            .filter(HFRTProject.workflow_run_id == workflow_run_id)
            .first()
        )
        if not project:
            raise ValueError(f"No HFRT project for workflow {workflow_run_id}")

        project.status = "COMPLETED"
        project.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {"status": "COMPLETED", "ticker": project.ticker}
    finally:
        db.close()


