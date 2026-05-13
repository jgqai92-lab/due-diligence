"""IST Phase 3: equity identification, invariant checks, and gate."""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.ist import (
    ISTBottleneck,
    ISTClaim,
    ISTEffectsChain,
    ISTEquityCandidate,
    ISTScreen,
    ISTValidation,
)
from app.services.ist.claude_client import call_claude, get_step_model_tier
from app.services.perplexity_client import is_available as perplexity_available, search_and_analyze
from app.services.workflow_engine import emit_sse_event, register_step

logger = logging.getLogger(__name__)


class ScarcityDimensions(BaseModel):
    """Five-dimensional scarcity scoring rubric."""

    supply_constraint: float = Field(ge=1.0, le=5.0)
    demand_visibility: float = Field(ge=1.0, le=5.0)
    substitution_difficulty: float = Field(ge=1.0, le=5.0)
    pricing_power: float = Field(ge=1.0, le=5.0)
    temporal_urgency: float = Field(ge=1.0, le=5.0)


class EquityCandidateItem(BaseModel):
    """A single equity candidate identified for a bottleneck."""

    ticker: str
    company_name: str
    bottleneck_name: str
    scarcity_dimensions: ScarcityDimensions
    moat_type: Optional[str] = None
    moat_evidence: Optional[str] = None
    catalyst: Optional[str] = None
    conviction: str


class EquityScanResult(BaseModel):
    """Structured output from equity scanning."""

    candidates: list[EquityCandidateItem]


class EffectItem(BaseModel):
    """A single effects-chain entry."""

    thesis: str
    order: int = Field(ge=1, le=3)
    effect_description: str
    equity_ticker: Optional[str] = None


class EffectsResult(BaseModel):
    """Structured output from effects analysis."""

    effects: list[EffectItem]


EQUITY_SCANNING_SYSTEM_PROMPT = """You are an investment research analyst identifying equity candidates that benefit from temporal scarcity bottlenecks.

Your task:
1. For each bottleneck provided, identify 2-4 publicly-traded companies that benefit
2. For each company, assess the five scarcity dimensions on a 1-5 scale:
   - supply_constraint: How constrained is the supply chain? (5 = severely constrained)
   - demand_visibility: How visible/certain is the demand? (5 = highly visible)
   - substitution_difficulty: How hard is it to substitute? (5 = no substitutes)
   - pricing_power: How much pricing power does the company have? (5 = monopoly-like)
   - temporal_urgency: How time-sensitive is the opportunity? (5 = urgent window)
3. Identify the moat type and evidence (1-2 sentences max) for each candidate
4. Identify near-term catalysts (1 sentence max)
5. Assign conviction (HIGH, MEDIUM, or LOW)

IMPORTANT: Keep output CONCISE. Limit to 15 candidates total across all bottlenecks.
Use short strings for thesis (1 sentence), moat_evidence (1-2 sentences), and catalysts (1 sentence).

NEVER fabricate ticker symbols or company names. Only identify real, publicly-traded companies. If you cannot identify companies for a bottleneck, return an empty list for that bottleneck. Use only information derivable from the bottleneck and claim data provided.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""

EFFECTS_ANALYSIS_SYSTEM_PROMPT = """You are an investment research analyst mapping multi-order downstream effects from temporal scarcity bottlenecks.

Your task:
1. For each bottleneck and its equity candidates, map downstream effects:
   - 1st order: Direct, immediate effects of the bottleneck
   - 2nd order: Secondary effects that cascade from 1st order
   - 3rd order: Tertiary, often non-obvious effects
2. Link effects to specific equity candidates where applicable (via ticker)
3. Each effect should have a clear thesis and description

NEVER fabricate data or invent effects without basis in the provided bottleneck and candidate data. If an effect cannot be clearly linked to a candidate, leave equity_ticker as null.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""


async def _run_equity_scanning(
    screen: ISTScreen,
    bottlenecks: list[ISTBottleneck],
    claims: list[ISTClaim],
    db: Session,
    workflow_run_id: int,
    *,
    update_screen_status: bool = True,
    replace_artifact: bool = False,
    model: str | None = None,
) -> dict | None:
    """Core equity-scanning logic for IST and IST_REFRESH."""
    if update_screen_status:
        screen.status = "SCANNING"
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "equity_scanning",
            "message": "Scanning for equity candidates...",
            "percent": 10,
        },
    )

    if not bottlenecks:
        raise ValueError("No bottlenecks found for equity scanning. Run bottleneck_mapping first.")

    if replace_artifact:
        db.query(ISTEquityCandidate).filter(ISTEquityCandidate.screen_id == screen.id).delete()

    bottleneck_text = "\n".join(
        f"- {bn.name} (Phase {bn.phase}: {bn.phase_label}): {bn.description}"
        + (f" | Evidence: {bn.quantitative_evidence}" if bn.quantitative_evidence else "")
        + (f" | Temporal: {bn.temporal_marker}" if bn.temporal_marker else "")
        for bn in bottlenecks
    )

    claims_text = "\n".join(
        f"- {c.claim_text}"
        + (f" | Quant: {c.quantitative_anchor}" if c.quantitative_anchor else "")
        for c in claims
    )

    # Optionally enrich with current market data from Perplexity
    market_verification_block = ""
    if perplexity_available():
        try:
            bn_names = ", ".join(bn.name for bn in bottlenecks[:5])
            pplx = await search_and_analyze(
                system_prompt=(
                    "You are a market research analyst. For the given bottleneck themes, "
                    "identify publicly traded companies that are key beneficiaries. "
                    "For each company, provide: ticker symbol, current market cap, "
                    "and one sentence on why they benefit. Verify tickers are real "
                    "and currently trading on major US exchanges."
                ),
                user_prompt=(
                    f"Find publicly traded companies that benefit from these "
                    f"investment themes: {bn_names}"
                ),
                model="sonar",
                max_tokens=4096,
                workflow_run_id=workflow_run_id,
            )
            market_verification_block = (
                f"<verified_market_data>\n{pplx.content}\n</verified_market_data>\n\n"
            )
            logger.info("Perplexity equity verification: %d citations", len(pplx.citations))
        except Exception:
            logger.warning("Perplexity equity verification failed, continuing without", exc_info=True)

    user_prompt = (
        f"{market_verification_block}"
        f"<bottlenecks>\n{bottleneck_text}\n</bottlenecks>\n\n"
        f"<claims>\n{claims_text}\n</claims>\n\n"
        f"Identify equity candidates that benefit from these {len(bottlenecks)} bottlenecks.\n"
        f"Return JSON matching this schema: {EquityScanResult.model_json_schema()}"
    )

    result = await call_claude(
        system_prompt=EQUITY_SCANNING_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=EquityScanResult,
        model=model,
        max_tokens=16384,
    )

    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "equity_scanning",
            "message": f"Identified {len(result.candidates)} candidates, storing...",
            "percent": 70,
        },
    )

    name_to_bottleneck: dict[str, ISTBottleneck] = {bn.name: bn for bn in bottlenecks}

    stored_count = 0
    seen_tickers: set[str] = set()
    for cand_data in result.candidates:
        # Deduplicate: UNIQUE constraint on (screen_id, ticker)
        ticker_upper = cand_data.ticker.strip().upper()
        if ticker_upper in seen_tickers:
            logger.info("Skipping duplicate ticker '%s'", ticker_upper)
            continue
        seen_tickers.add(ticker_upper)

        matched_bn = name_to_bottleneck.get(cand_data.bottleneck_name)
        if matched_bn is None:
            logger.warning(
                "Equity candidate '%s' references unknown bottleneck '%s', skipping",
                cand_data.ticker,
                cand_data.bottleneck_name,
            )
            continue

        dims = cand_data.scarcity_dimensions
        overall = round(
            (
                dims.supply_constraint
                + dims.demand_visibility
                + dims.substitution_difficulty
                + dims.pricing_power
                + dims.temporal_urgency
            )
            / 5.0,
            2,
        )

        scarcity_score_json = json.dumps(
            {
                "overall": overall,
                "dimensions": {
                    "supplyConstraint": dims.supply_constraint,
                    "demandVisibility": dims.demand_visibility,
                    "substitutionDifficulty": dims.substitution_difficulty,
                    "pricingPower": dims.pricing_power,
                    "temporalUrgency": dims.temporal_urgency,
                },
            }
        )

        db.add(
            ISTEquityCandidate(
                screen_id=screen.id,
                ticker=cand_data.ticker,
                company_name=cand_data.company_name,
                bottleneck_id=matched_bn.id,
                scarcity_score=scarcity_score_json,
                moat_type=cand_data.moat_type,
                moat_evidence=cand_data.moat_evidence,
                catalyst=cand_data.catalyst,
                tier=3,
                conviction=cand_data.conviction,
                phase=matched_bn.phase,
            )
        )
        stored_count += 1

    screen.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "candidatesIdentified": len(result.candidates),
        "candidatesStored": stored_count,
    }


async def _run_tier_classification(
    screen: ISTScreen,
    candidates: list[ISTEquityCandidate],
    db: Session,
    workflow_run_id: int,
) -> dict | None:
    """Core deterministic tiering logic for IST and IST_REFRESH."""
    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "tier_classification",
            "message": "Classifying equity candidates into tiers...",
            "percent": 20,
        },
    )

    if not candidates:
        raise ValueError("No equity candidates found for tier classification. Run equity_scanning first.")

    bottleneck_ids = {c.bottleneck_id for c in candidates if c.bottleneck_id}
    if bottleneck_ids:
        bottlenecks = db.query(ISTBottleneck).filter(ISTBottleneck.id.in_(bottleneck_ids)).all()
        bn_phase_map = {bn.id: bn.phase for bn in bottlenecks}
    else:
        bn_phase_map = {}

    tier_counts = {1: 0, 2: 0, 3: 0}

    for candidate in candidates:
        overall_score = _get_overall_scarcity_score(candidate.scarcity_score)

        has_high_scarcity = overall_score >= 4.0
        has_mid_scarcity = overall_score >= 3.0
        has_market_cap = candidate.market_cap is not None
        has_moat_evidence = candidate.moat_evidence is not None and candidate.moat_evidence != ""

        if has_high_scarcity and has_market_cap and has_moat_evidence:
            candidate.tier = 1
            candidate.tier_rationale = (
                f"Tier 1: Scarcity score {overall_score:.1f} >= 4.0, "
                "market cap present, moat evidence documented."
            )
        elif has_mid_scarcity or (has_high_scarcity and (not has_market_cap or not has_moat_evidence)):
            candidate.tier = 2
            missing_parts: list[str] = []
            if has_high_scarcity and not has_market_cap:
                missing_parts.append("market cap missing")
            if has_high_scarcity and not has_moat_evidence:
                missing_parts.append("moat evidence missing")
            if not has_high_scarcity:
                missing_parts.append(f"scarcity score {overall_score:.1f} between 3.0-4.0")
            candidate.tier_rationale = (
                "Tier 2: Watchlist candidate. "
                f"{' ; '.join(missing_parts) if missing_parts else 'Mid-range scarcity score.'}."
            )
        else:
            candidate.tier = 3
            candidate.tier_rationale = (
                f"Tier 3: Speculative. Scarcity score {overall_score:.1f} below 3.0."
            )

        if candidate.bottleneck_id and candidate.bottleneck_id in bn_phase_map:
            candidate.phase = bn_phase_map[candidate.bottleneck_id]

        candidate.updated_at = datetime.now(timezone.utc)
        tier_counts[candidate.tier] += 1

    screen.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "candidatesClassified": len(candidates),
        "tierBreakdown": {
            "tier1": tier_counts[1],
            "tier2": tier_counts[2],
            "tier3": tier_counts[3],
        },
    }


async def _run_effects_analysis(
    screen: ISTScreen,
    bottlenecks: list[ISTBottleneck],
    candidates: list[ISTEquityCandidate],
    db: Session,
    workflow_run_id: int,
    *,
    replace_artifact: bool = False,
    model: str | None = None,
) -> dict | None:
    """Core effects-analysis logic for IST and IST_REFRESH."""
    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "effects_analysis",
            "message": "Mapping downstream effects...",
            "percent": 10,
        },
    )

    if not bottlenecks:
        raise ValueError("No bottlenecks found for effects analysis. Run bottleneck_mapping first.")

    if replace_artifact:
        db.query(ISTEffectsChain).filter(ISTEffectsChain.screen_id == screen.id).delete()

    bottleneck_text = "\n".join(
        f"- {bn.name} (Phase {bn.phase}): {bn.description}"
        for bn in bottlenecks
    )

    candidate_text = (
        "\n".join(
            f"- {c.ticker} ({c.company_name}): Tier {c.tier}, "
            f"Bottleneck ID {c.bottleneck_id}"
            + (f", Moat: {c.moat_type}" if c.moat_type else "")
            for c in candidates
        )
        if candidates
        else "No equity candidates identified yet."
    )

    user_prompt = (
        f"<bottlenecks>\n{bottleneck_text}\n</bottlenecks>\n\n"
        f"<equity_candidates>\n{candidate_text}\n</equity_candidates>\n\n"
        f"Map 1st, 2nd, and 3rd order downstream effects from these bottlenecks.\n"
        f"Link effects to specific equity candidates via ticker where applicable.\n"
        f"Return JSON matching this schema: {EffectsResult.model_json_schema()}"
    )

    result = await call_claude(
        system_prompt=EFFECTS_ANALYSIS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=EffectsResult,
        model=model,
        max_tokens=16384,
    )

    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "effects_analysis",
            "message": f"Mapped {len(result.effects)} effects, storing...",
            "percent": 70,
        },
    )

    ticker_to_candidate: dict[str, int] = {c.ticker: c.id for c in candidates}

    for effect_data in result.effects:
        candidate_id = None
        if effect_data.equity_ticker:
            candidate_id = ticker_to_candidate.get(effect_data.equity_ticker)
            if candidate_id is None:
                logger.warning(
                    "Effect references unknown ticker '%s', storing without FK",
                    effect_data.equity_ticker,
                )

        db.add(
            ISTEffectsChain(
                screen_id=screen.id,
                thesis=effect_data.thesis,
                effect_order=effect_data.order,
                effect_description=effect_data.effect_description,
                equity_candidate_id=candidate_id,
            )
        )

    screen.updated_at = datetime.now(timezone.utc)
    db.commit()

    order_counts = {1: 0, 2: 0, 3: 0}
    for effect in result.effects:
        order_counts[effect.order] = order_counts.get(effect.order, 0) + 1

    return {
        "effectsMapped": len(result.effects),
        "orderBreakdown": order_counts,
    }


@register_step("IST", "equity_scanning")
async def handle_equity_scanning(workflow_run_id: int) -> dict | None:
    """Identify equity candidates for each bottleneck."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        bottlenecks = (
            db.query(ISTBottleneck)
            .filter(ISTBottleneck.screen_id == screen.id)
            .order_by(ISTBottleneck.id)
            .all()
        )
        claims = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .order_by(ISTClaim.id)
            .all()
        )

        model = await get_step_model_tier(workflow_run_id, "equity_scanning")
        return await _run_equity_scanning(
            screen,
            bottlenecks,
            claims,
            db,
            workflow_run_id,
            model=model,
        )
    finally:
        db.close()


@register_step("IST", "tier_classification")
async def handle_tier_classification(workflow_run_id: int) -> dict | None:
    """Classify equity candidates into Tier 1/2/3 via deterministic logic."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        candidates = (
            db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == screen.id)
            .order_by(ISTEquityCandidate.id)
            .all()
        )

        return await _run_tier_classification(screen, candidates, db, workflow_run_id)
    finally:
        db.close()


@register_step("IST", "effects_analysis")
async def handle_effects_analysis(workflow_run_id: int) -> dict | None:
    """Map 1st/2nd/3rd order downstream effects."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        bottlenecks = (
            db.query(ISTBottleneck)
            .filter(ISTBottleneck.screen_id == screen.id)
            .order_by(ISTBottleneck.id)
            .all()
        )
        candidates = (
            db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == screen.id)
            .order_by(ISTEquityCandidate.id)
            .all()
        )

        model = await get_step_model_tier(workflow_run_id, "effects_analysis")
        return await _run_effects_analysis(
            screen,
            bottlenecks,
            candidates,
            db,
            workflow_run_id,
            model=model,
        )
    finally:
        db.close()


@register_step("IST", "invariant_check")
async def handle_invariant_check(workflow_run_id: int) -> dict | None:
    """Check IST screening invariants 1-5 (deterministic server-side)."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "invariant_check",
                "message": "Running invariant checks...",
                "percent": 20,
            },
        )

        invariants = []

        claims = db.query(ISTClaim).filter(ISTClaim.screen_id == screen.id).all()
        total_claims = len(claims)
        claims_with_citation = sum(
            1
            for c in claims
            if c.source_citation is not None and c.source_citation.strip() != ""
        )
        inv1_pass = total_claims > 0 and claims_with_citation == total_claims
        invariants.append(
            {
                "id": "INV-1",
                "name": "Source Citation Required",
                "status": "PASS" if inv1_pass else "FAIL",
                "details": (
                    f"All {total_claims} claims have source citations."
                    if inv1_pass
                    else f"{claims_with_citation}/{total_claims} claims have source citations."
                ),
            }
        )

        claims_with_quant = sum(
            1
            for c in claims
            if c.quantitative_anchor is not None and c.quantitative_anchor.strip() != ""
        )
        quant_pct = (claims_with_quant / total_claims * 100) if total_claims > 0 else 0
        inv2_pass = total_claims > 0 and quant_pct >= 50
        invariants.append(
            {
                "id": "INV-2",
                "name": "Quantitative Anchor Required",
                "status": "PASS" if inv2_pass else "FAIL",
                "details": (
                    f"{claims_with_quant}/{total_claims} claims ({quant_pct:.0f}%) have "
                    "quantitative anchors (>= 50% required)."
                ),
            }
        )

        claims_with_temporal = sum(
            1
            for c in claims
            if c.temporal_marker is not None and c.temporal_marker.strip() != ""
        )
        inv3_pass = claims_with_temporal >= 1
        invariants.append(
            {
                "id": "INV-3",
                "name": "Temporal Marker Required",
                "status": "PASS" if inv3_pass else "FAIL",
                "details": f"{claims_with_temporal} claims have temporal markers (>= 1 required).",
            }
        )

        candidates = (
            db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == screen.id)
            .all()
        )
        total_candidates = len(candidates)
        orphan_candidates = sum(1 for c in candidates if c.bottleneck_id is None)
        inv4_pass = total_candidates == 0 or orphan_candidates == 0
        invariants.append(
            {
                "id": "INV-4",
                "name": "No Orphan Equities",
                "status": "PASS" if inv4_pass else "FAIL",
                "details": (
                    f"All {total_candidates} candidates linked to bottlenecks."
                    if inv4_pass
                    else f"{orphan_candidates}/{total_candidates} candidates lack bottleneck linkage."
                ),
            }
        )

        candidates_with_rationale = sum(
            1
            for c in candidates
            if c.tier_rationale is not None and c.tier_rationale.strip() != ""
        )
        inv5_pass = total_candidates == 0 or candidates_with_rationale == total_candidates
        invariants.append(
            {
                "id": "INV-5",
                "name": "Tier Justification Required",
                "status": "PASS" if inv5_pass else "FAIL",
                "details": (
                    f"All {total_candidates} candidates have tier rationale."
                    if inv5_pass
                    else f"{candidates_with_rationale}/{total_candidates} candidates have tier rationale."
                ),
            }
        )

        invariants.append(
            {
                "id": "INV-6",
                "name": "Dialectic Isolation",
                "status": "SKIPPED",
                "details": "Checked in Phase 4 (Dialectic Scrutiny).",
            }
        )
        invariants.append(
            {
                "id": "INV-7",
                "name": "Anti-Hallucination",
                "status": "SKIPPED",
                "details": "Checked in Phase 5 (Final Synthesis).",
            }
        )
        invariants.append(
            {
                "id": "INV-8",
                "name": "Report Completeness",
                "status": "SKIPPED",
                "details": "Checked in Phase 5 (Final Synthesis).",
            }
        )

        pass_count = sum(1 for inv in invariants if inv["status"] == "PASS")
        fail_count = sum(1 for inv in invariants if inv["status"] == "FAIL")
        skip_count = sum(1 for inv in invariants if inv["status"] == "SKIPPED")
        all_passed = fail_count == 0

        await emit_sse_event(
            workflow_run_id,
            "invariant_check_complete",
            {
                "stepName": "invariant_check",
                "allPassed": all_passed,
                "passCount": pass_count,
                "failCount": fail_count,
                "skipCount": skip_count,
            },
        )

        return {
            "allPassed": all_passed,
            "passCount": pass_count,
            "failCount": fail_count,
            "skipCount": skip_count,
            "invariants": invariants,
        }
    finally:
        db.close()


@register_step("IST", "research_sufficiency_gate")
async def handle_research_sufficiency_gate(workflow_run_id: int) -> dict | None:
    """Research sufficiency gate before dialectic phase."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "research_sufficiency_gate",
                "message": "Running research sufficiency checks...",
                "percent": 20,
            },
        )

        deficiencies: list[str] = []

        candidates = (
            db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == screen.id)
            .all()
        )
        if len(candidates) < 1:
            deficiencies.append("No equity candidates identified (need 1+ minimum)")

        candidates_without_score = sum(
            1 for c in candidates if c.scarcity_score is None or c.scarcity_score.strip() == ""
        )
        if candidates_without_score > 0:
            deficiencies.append(f"{candidates_without_score} candidates missing scarcity scores")

        candidates_without_tier = sum(1 for c in candidates if c.tier is None)
        if candidates_without_tier > 0:
            deficiencies.append(f"{candidates_without_tier} candidates missing tier classification")

        validation_count = (
            db.query(ISTValidation)
            .filter(ISTValidation.screen_id == screen.id)
            .count()
        )
        if validation_count < 1:
            deficiencies.append("No bottleneck validations found (need 1+ minimum)")

        if deficiencies:
            await emit_sse_event(
                workflow_run_id,
                "gate_failed",
                {
                    "stepName": "research_sufficiency_gate",
                    "deficiencies": deficiencies,
                },
            )
            raise ValueError("Research sufficiency gate FAILED: " + "; ".join(deficiencies))

        gate_details = {
            "candidateCount": len(candidates),
            "allHaveScarcityScores": True,
            "allHaveTiers": True,
            "validationCount": validation_count,
        }

        await emit_sse_event(
            workflow_run_id,
            "gate_passed",
            {
                "stepName": "research_sufficiency_gate",
                "details": gate_details,
            },
        )

        return {
            "gateResult": "PASSED",
            **gate_details,
        }
    finally:
        db.close()


def _get_overall_scarcity_score(scarcity_score_json: str | None) -> float:
    """Parse scarcity_score JSON and return overall score."""
    if not scarcity_score_json:
        return 0.0
    try:
        data = json.loads(scarcity_score_json)
        return float(data.get("overall", 0.0))
    except (json.JSONDecodeError, TypeError, ValueError):
        return 0.0
