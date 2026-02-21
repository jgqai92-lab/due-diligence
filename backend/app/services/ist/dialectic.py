"""IST Phase 4: dialectic scrutiny (optimist, pessimist, synthesis)."""

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
    ISTDemandModel,
    ISTDialecticReview,
    ISTEffectsChain,
    ISTEquityCandidate,
    ISTScreen,
    ISTValidation,
)
from app.services.ist.claude_client import call_claude
from app.services.workflow_engine import emit_sse_event, register_step

logger = logging.getLogger(__name__)


class TierAdjustment(BaseModel):
    """Proposed tier adjustment for a single ticker."""

    ticker: str
    current_tier: int = Field(ge=1, le=3)
    proposed_tier: int = Field(ge=1, le=3)
    rationale: str


class DialecticReviewContent(BaseModel):
    """Optimist/pessimist structured response."""

    narrative: str
    key_arguments: list[str]
    tier_adjustments: list[TierAdjustment]
    conviction_level: str
    risk_discount: float = Field(ge=0.0, le=1.0)


class Disagreement(BaseModel):
    """A disagreement resolved by synthesis."""

    topic: str
    optimist_view: str
    pessimist_view: str
    resolution: str
    impact_on_tiers: str


class SynthesisContent(BaseModel):
    """Synthesis structured response."""

    narrative: str
    disagreements: list[Disagreement]
    final_tier_adjustments: list[TierAdjustment]
    overall_conviction: str
    key_risks: list[str]


OPTIMIST_SYSTEM_PROMPT = """You are a BULL-CASE investment analyst conducting optimist review of an investment screen.

Your role is to advocate for the strongest possible investment case. Analyze the provided Phase 1-3 data (claims, bottlenecks, demand models, validations, equity candidates, effects chains) and build the most compelling bull thesis.

Focus on:
1. Market misperceptions the consensus is missing -- where is the market underpricing scarcity?
2. Upside catalysts and analytical parallels from historical scarcity cycles
3. Why scarcity persists LONGER than the market expects
4. Tier UPGRADE recommendations with specific rationale for each candidate
5. Time-arbitrage opportunities where near-term pain hides long-term value

For tier_adjustments, only include candidates where you recommend a tier change (upgrade). If a candidate should stay at current tier, do not include it.

NEVER fabricate financial data, price targets, or company metrics. Base all arguments strictly on the evidence provided in the data package. If the bull case for a candidate is weak, say so explicitly rather than inventing support.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""

PESSIMIST_SYSTEM_PROMPT = """You are a BEAR-CASE investment analyst conducting pessimist review of an investment screen.

Your role is to find every flaw in the investment thesis. Analyze the provided Phase 1-3 data (claims, bottlenecks, demand models, validations, equity candidates, effects chains) and stress-test the entire framework.

Focus on:
1. NULL HYPOTHESIS: What if the scarcity thesis is fundamentally wrong?
2. Source bias and echo chamber risks -- are the claims from a single perspective?
3. Timeline risk: What if bottlenecks resolve FASTER than expected?
4. Demand deceleration scenarios -- what could reduce demand growth?
5. Tier DOWNGRADE recommendations with specific rationale for each candidate
6. Competitive threats and substitution risks not captured in the screen

For tier_adjustments, only include candidates where you recommend a tier change (downgrade). If a candidate should stay at current tier, do not include it.

NEVER fabricate financial data or company metrics. Base all arguments strictly on the evidence provided.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""

SYNTHESIS_SYSTEM_PROMPT = """You are a SYNTHESIS analyst reconciling optimist and pessimist reviews of an investment screen.

You have access to BOTH the bull-case (optimist) and bear-case (pessimist) analyses, as well as the original Phase 1-3 data. Your job is to produce a balanced final assessment.

Focus on:
1. Identify specific disagreements and resolve each with explicit evidence-based reasoning
2. Produce final tier adjustments after reconciliation
3. Assess post-dialectic conviction
4. List key risks that survived scrutiny

NEVER fabricate data. Your synthesis must be grounded in the provided evidence.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""


def _build_phase_data_package(db: Session, screen_id: int, workflow_run_id: int) -> str:
    """Build a comprehensive Phase 1-3 data package for dialectic steps."""
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise ValueError(f"No IST screen found with id {screen_id}")

    claims = (
        db.query(ISTClaim)
        .filter(ISTClaim.screen_id == screen_id)
        .order_by(ISTClaim.id)
        .all()
    )
    bottlenecks = (
        db.query(ISTBottleneck)
        .filter(ISTBottleneck.screen_id == screen_id)
        .order_by(ISTBottleneck.phase, ISTBottleneck.id)
        .all()
    )
    demand_models = (
        db.query(ISTDemandModel)
        .filter(ISTDemandModel.screen_id == screen_id)
        .order_by(ISTDemandModel.id)
        .all()
    )
    validations = (
        db.query(ISTValidation)
        .filter(ISTValidation.screen_id == screen_id)
        .order_by(ISTValidation.id)
        .all()
    )
    candidates = (
        db.query(ISTEquityCandidate)
        .filter(ISTEquityCandidate.screen_id == screen_id)
        .order_by(ISTEquityCandidate.tier, ISTEquityCandidate.id)
        .all()
    )
    effects_chains = (
        db.query(ISTEffectsChain)
        .filter(ISTEffectsChain.screen_id == screen_id)
        .order_by(ISTEffectsChain.effect_order, ISTEffectsChain.id)
        .all()
    )

    bn_id_to_name = {bn.id: bn.name for bn in bottlenecks}

    claims_text = (
        "\n".join(
            f"- [{c.id}] {c.claim_text}"
            + (f" | Citation: {c.source_citation}" if c.source_citation else "")
            + (f" | Quant: {c.quantitative_anchor}" if c.quantitative_anchor else "")
            + (f" | Time: {c.temporal_marker}" if c.temporal_marker else "")
            + (f" | Confidence: {c.confidence}" if c.confidence else "")
            + (f" | Validated: {c.validation_verdict}" if c.validation_verdict else "")
            for c in claims
        )
        if claims
        else "No claims extracted."
    )

    bottlenecks_text = (
        "\n".join(
            f"- {bn.name} (Phase {bn.phase}: {bn.phase_label}): {bn.description}"
            + (f" | Evidence: {bn.quantitative_evidence}" if bn.quantitative_evidence else "")
            + (f" | Temporal: {bn.temporal_marker}" if bn.temporal_marker else "")
            + (f" | Resolution: {bn.resolution_trigger}" if bn.resolution_trigger else "")
            for bn in bottlenecks
        )
        if bottlenecks
        else "No bottlenecks identified."
    )

    demand_models_text = (
        "\n".join(
            f"- Bottleneck: {bn_id_to_name.get(dm.bottleneck_id, 'Unknown')}"
            + f" | Formula: {dm.formula}"
            + f" | Base: {dm.base_case}"
            + f" | Bull: {dm.bull_case}"
            + f" | Bear: {dm.bear_case}"
            + (f" | Multiplier: {dm.multiplier_chain}" if dm.multiplier_chain else "")
            for dm in demand_models
        )
        if demand_models
        else "No demand models built."
    )

    validations_text = (
        "\n".join(
            f"- Claim {v.claim_id}: {v.verdict} (confidence {v.confidence})"
            + f" | Evidence: {v.evidence}"
            for v in validations
        )
        if validations
        else "No validations performed."
    )

    candidates_text = (
        "\n".join(
            f"- {c.ticker} ({c.company_name}): Tier {c.tier}"
            + (f" | Bottleneck: {bn_id_to_name.get(c.bottleneck_id, 'Unknown')}" if c.bottleneck_id else "")
            + f" | Scarcity: {c.scarcity_score}"
            + (f" | Moat: {c.moat_type}" if c.moat_type else "")
            + (f" | Evidence: {c.moat_evidence}" if c.moat_evidence else "")
            + (f" | Catalyst: {c.catalyst}" if c.catalyst else "")
            + (f" | Conviction: {c.conviction}" if c.conviction else "")
            + (f" | Tier Rationale: {c.tier_rationale}" if c.tier_rationale else "")
            + (f" | Phase: {c.phase}" if c.phase is not None else "")
            for c in candidates
        )
        if candidates
        else "No equity candidates identified."
    )

    effects_text = (
        "\n".join(
            f"- Order {ec.effect_order}: {ec.thesis} -> {ec.effect_description}"
            + (
                f" | Ticker: {_get_ticker_for_candidate(candidates, ec.equity_candidate_id)}"
                if ec.equity_candidate_id
                else ""
            )
            for ec in effects_chains
        )
        if effects_chains
        else "No effects chains mapped."
    )

    source_bias_text = "Not assessed."
    if screen.source_bias:
        try:
            bias = json.loads(screen.source_bias)
            source_bias_text = (
                f"Rating: {bias.get('rating', 'Unknown')}"
                + f" | Notes: {bias.get('notes', '')}"
                + f" | Credibility: {bias.get('sourceCredibility', '')}"
                + f" | Blind spots: {', '.join(bias.get('potentialBlindSpots', []))}"
            )
        except (json.JSONDecodeError, TypeError):
            pass

    hypothesis_text = "Not specified."
    if screen.screening_brief:
        try:
            brief = json.loads(screen.screening_brief)
            hypothesis_text = brief.get("hypothesis", "Not specified.") or "Not specified."
        except (json.JSONDecodeError, TypeError):
            pass

    return (
        f"<screen_metadata>\n"
        f"Screen: {screen.name}\n"
        f"Content type: {screen.content_type}\n"
        f"Hypothesis: {hypothesis_text}\n"
        f"Source bias: {source_bias_text}\n"
        f"</screen_metadata>\n\n"
        f"<claims count=\"{len(claims)}\">\n{claims_text}\n</claims>\n\n"
        f"<bottlenecks count=\"{len(bottlenecks)}\">\n{bottlenecks_text}\n</bottlenecks>\n\n"
        f"<demand_models count=\"{len(demand_models)}\">\n{demand_models_text}\n</demand_models>\n\n"
        f"<validations count=\"{len(validations)}\">\n{validations_text}\n</validations>\n\n"
        f"<equity_candidates count=\"{len(candidates)}\">\n{candidates_text}\n</equity_candidates>\n\n"
        f"<effects_chains count=\"{len(effects_chains)}\">\n{effects_text}\n</effects_chains>"
    )


def _get_ticker_for_candidate(
    candidates: list[ISTEquityCandidate],
    candidate_id: Optional[int],
) -> str:
    """Look up ticker for a candidate ID."""
    if candidate_id is None:
        return "N/A"
    for candidate in candidates:
        if candidate.id == candidate_id:
            return candidate.ticker
    return "Unknown"


async def _run_dialectic_optimist(
    screen: ISTScreen,
    db: Session,
    workflow_run_id: int,
    *,
    update_screen_status: bool = True,
    replace_artifact: bool = False,
) -> dict | None:
    """Core optimist dialectic logic."""
    if update_screen_status:
        screen.status = "DIALECTIC"
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "dialectic_optimist",
            "message": "Building bull-case analysis...",
            "percent": 10,
        },
    )

    data_package = _build_phase_data_package(db, screen.id, workflow_run_id)

    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "dialectic_optimist",
            "message": "Calling Claude for optimist review...",
            "percent": 30,
        },
    )

    user_prompt = (
        f"{data_package}\n\n"
        f"Conduct a comprehensive BULL-CASE review of this investment screen.\n"
        f"For each equity candidate, evaluate whether a tier UPGRADE is warranted.\n"
        f"Return JSON matching this schema: {DialecticReviewContent.model_json_schema()}"
    )

    result = await call_claude(
        system_prompt=OPTIMIST_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=DialecticReviewContent,
        max_tokens=16384,
    )

    if replace_artifact:
        db.query(ISTDialecticReview).filter(
            ISTDialecticReview.screen_id == screen.id,
            ISTDialecticReview.side == "OPTIMIST",
        ).delete()

    db.add(
        ISTDialecticReview(
            screen_id=screen.id,
            side="OPTIMIST",
            content=result.model_dump_json(),
        )
    )
    screen.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "side": "OPTIMIST",
        "convictionLevel": result.conviction_level,
        "riskDiscount": result.risk_discount,
        "keyArgumentCount": len(result.key_arguments),
        "tierAdjustmentCount": len(result.tier_adjustments),
    }


async def _run_dialectic_pessimist(
    screen: ISTScreen,
    db: Session,
    workflow_run_id: int,
    *,
    replace_artifact: bool = False,
) -> dict | None:
    """Core pessimist dialectic logic."""
    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "dialectic_pessimist",
            "message": "Building bear-case analysis...",
            "percent": 10,
        },
    )

    data_package = _build_phase_data_package(db, screen.id, workflow_run_id)

    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "dialectic_pessimist",
            "message": "Calling Claude for pessimist review...",
            "percent": 30,
        },
    )

    user_prompt = (
        f"{data_package}\n\n"
        f"Conduct a comprehensive BEAR-CASE review of this investment screen.\n"
        f"Stress-test every assumption. For each equity candidate, evaluate whether a tier DOWNGRADE is warranted.\n"
        f"Return JSON matching this schema: {DialecticReviewContent.model_json_schema()}"
    )

    result = await call_claude(
        system_prompt=PESSIMIST_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=DialecticReviewContent,
        max_tokens=16384,
    )

    if replace_artifact:
        db.query(ISTDialecticReview).filter(
            ISTDialecticReview.screen_id == screen.id,
            ISTDialecticReview.side == "PESSIMIST",
        ).delete()

    db.add(
        ISTDialecticReview(
            screen_id=screen.id,
            side="PESSIMIST",
            content=result.model_dump_json(),
        )
    )
    screen.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "side": "PESSIMIST",
        "convictionLevel": result.conviction_level,
        "riskDiscount": result.risk_discount,
        "keyArgumentCount": len(result.key_arguments),
        "tierAdjustmentCount": len(result.tier_adjustments),
    }


async def _run_dialectic_synthesis(
    screen: ISTScreen,
    db: Session,
    workflow_run_id: int,
    *,
    replace_artifact: bool = False,
) -> dict | None:
    """Core synthesis dialectic logic."""
    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "dialectic_synthesis",
            "message": "Loading optimist and pessimist reviews...",
            "percent": 10,
        },
    )

    optimist_review = (
        db.query(ISTDialecticReview)
        .filter(
            ISTDialecticReview.screen_id == screen.id,
            ISTDialecticReview.side == "OPTIMIST",
        )
        .first()
    )
    pessimist_review = (
        db.query(ISTDialecticReview)
        .filter(
            ISTDialecticReview.screen_id == screen.id,
            ISTDialecticReview.side == "PESSIMIST",
        )
        .first()
    )

    if not optimist_review or not pessimist_review:
        raise ValueError(
            "Both optimist and pessimist reviews must be completed before synthesis. Missing: "
            + ("OPTIMIST " if not optimist_review else "")
            + ("PESSIMIST" if not pessimist_review else "")
        )

    data_package = _build_phase_data_package(db, screen.id, workflow_run_id)

    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "dialectic_synthesis",
            "message": "Calling Claude for synthesis...",
            "percent": 30,
        },
    )

    user_prompt = (
        f"{data_package}\n\n"
        f"<optimist_review>\n{optimist_review.content}\n</optimist_review>\n\n"
        f"<pessimist_review>\n{pessimist_review.content}\n</pessimist_review>\n\n"
        f"Synthesize the optimist and pessimist reviews. Reconcile their disagreements, determine final tier adjustments, and assess overall conviction.\n"
        f"Return JSON matching this schema: {SynthesisContent.model_json_schema()}"
    )

    result = await call_claude(
        system_prompt=SYNTHESIS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=SynthesisContent,
        max_tokens=16384,
    )

    if replace_artifact:
        db.query(ISTDialecticReview).filter(
            ISTDialecticReview.screen_id == screen.id,
            ISTDialecticReview.side == "SYNTHESIS",
        ).delete()

    db.add(
        ISTDialecticReview(
            screen_id=screen.id,
            side="SYNTHESIS",
            content=result.model_dump_json(),
        )
    )
    screen.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "side": "SYNTHESIS",
        "overallConviction": result.overall_conviction,
        "disagreementCount": len(result.disagreements),
        "finalTierAdjustmentCount": len(result.final_tier_adjustments),
        "keyRiskCount": len(result.key_risks),
    }


@register_step("IST", "dialectic_optimist")
async def handle_dialectic_optimist(workflow_run_id: int) -> dict | None:
    """Bull-case dialectic review of the investment screen."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        return await _run_dialectic_optimist(screen, db, workflow_run_id)
    finally:
        db.close()


@register_step("IST", "dialectic_pessimist")
async def handle_dialectic_pessimist(workflow_run_id: int) -> dict | None:
    """Bear-case dialectic review of the investment screen."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        return await _run_dialectic_pessimist(screen, db, workflow_run_id)
    finally:
        db.close()


@register_step("IST", "dialectic_synthesis")
async def handle_dialectic_synthesis(workflow_run_id: int) -> dict | None:
    """Synthesize optimist and pessimist reviews."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        return await _run_dialectic_synthesis(screen, db, workflow_run_id)
    finally:
        db.close()
