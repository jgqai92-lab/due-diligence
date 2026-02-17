"""IST Phase 4: Dialectic Scrutiny -- optimist review, pessimist review, and synthesis.

Provides three registered workflow steps:
  - dialectic_optimist (step_order 12): Bull-case analysis from Phase 1-3 data
  - dialectic_pessimist (step_order 13): Bear-case analysis from Phase 1-3 data
  - dialectic_synthesis (step_order 14): Reconciles optimist and pessimist views

CRITICAL INVARIANT (INV-6: Dialectic Isolation):
  The optimist and pessimist MUST NOT see each other's output. They receive identical
  Phase 1-3 data packages (via _build_phase_data_package) but different system prompts.
  The synthesis step reads BOTH reviews after they are complete.

Invariants enforced:
  - INV-AI-01: Content/instruction separation (user data in XML tags)
  - INV-AI-03: Pydantic-validated Claude outputs
  - INV-AI-04: Anti-hallucination instructions in system prompts
  - INV-BE-05: Background tasks own their DB sessions
  - INV-BE-06: JSON stored via Pydantic serialization
  - INV-PE-01: Avoid N+1 queries (batch load all Phase 1-3 data)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

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
from app.services.workflow_engine import register_step, emit_sse_event

logger = logging.getLogger(__name__)


# -- Pydantic models for Claude structured output (INV-AI-03) -----------------


class TierAdjustment(BaseModel):
    """Proposed tier change for a specific equity candidate."""

    ticker: str = Field(description="Stock ticker symbol")
    current_tier: int = Field(ge=1, le=3, description="Current tier assignment")
    proposed_tier: int = Field(ge=1, le=3, description="Proposed new tier")
    rationale: str = Field(description="Rationale for the tier change")


class DialecticReviewContent(BaseModel):
    """Structured content for optimist or pessimist dialectic review."""

    narrative: str = Field(description="Full bull/bear analysis in markdown")
    key_arguments: list[str] = Field(
        description="3-5 key arguments supporting the view"
    )
    tier_adjustments: list[TierAdjustment] = Field(
        description="Proposed tier changes with rationale"
    )
    conviction_level: str = Field(description="Overall conviction: HIGH, MEDIUM, or LOW")
    risk_discount: float = Field(
        ge=0.0, le=1.0, description="Risk discount factor 0.0-1.0"
    )


class Disagreement(BaseModel):
    """A specific point of disagreement between optimist and pessimist."""

    topic: str = Field(description="The topic of disagreement")
    optimist_view: str = Field(description="What the optimist argued")
    pessimist_view: str = Field(description="What the pessimist argued")
    resolution: str = Field(description="How the disagreement was resolved")
    impact_on_tiers: str = Field(description="How this affects tier assignments")


class SynthesisContent(BaseModel):
    """Structured content for the dialectic synthesis."""

    narrative: str = Field(description="Full synthesis analysis in markdown")
    disagreements: list[Disagreement] = Field(
        description="Key disagreements between optimist and pessimist"
    )
    final_tier_adjustments: list[TierAdjustment] = Field(
        description="Final tier changes after reconciliation"
    )
    overall_conviction: str = Field(
        description="Overall conviction after synthesis: HIGH, MEDIUM, or LOW"
    )
    key_risks: list[str] = Field(
        description="Key risks that survived dialectic scrutiny"
    )


# -- System prompts (INV-AI-04: anti-hallucination instructions) --------------

OPTIMIST_SYSTEM_PROMPT = """\
You are a BULL-CASE investment analyst conducting optimist review of an investment screen.

Your role is to advocate for the strongest possible investment case. Analyze the provided \
Phase 1-3 data (claims, bottlenecks, demand models, validations, equity candidates, effects chains) \
and build the most compelling bull thesis.

Focus on:
1. Market misperceptions the consensus is missing -- where is the market underpricing scarcity?
2. Upside catalysts and analytical parallels from historical scarcity cycles
3. Why scarcity persists LONGER than the market expects
4. Tier UPGRADE recommendations with specific rationale for each candidate
5. Time-arbitrage opportunities where near-term pain hides long-term value

For tier_adjustments, only include candidates where you recommend a tier change (upgrade). \
If a candidate should stay at current tier, do not include it.

NEVER fabricate financial data, price targets, or company metrics. Base all arguments strictly \
on the evidence provided in the data package. If the bull case for a candidate is weak, say so \
explicitly rather than inventing support.

Your conviction_level should reflect how strong the overall bull case is:
- HIGH: Multiple reinforcing catalysts with strong quantitative evidence
- MEDIUM: Plausible bull case but with material uncertainties
- LOW: Weak bull case, limited evidence

Your risk_discount (0.0-1.0) represents how much to discount the bull case for risks. \
0.0 = no discount (maximum conviction), 1.0 = fully discounted (no conviction).

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""

PESSIMIST_SYSTEM_PROMPT = """\
You are a BEAR-CASE investment analyst conducting pessimist review of an investment screen.

Your role is to find every flaw in the investment thesis. Analyze the provided Phase 1-3 data \
(claims, bottlenecks, demand models, validations, equity candidates, effects chains) \
and stress-test the entire framework.

Focus on:
1. NULL HYPOTHESIS: What if the scarcity thesis is fundamentally wrong?
2. Source bias and echo chamber risks -- are the claims from a single perspective?
3. Timeline risk: What if bottlenecks resolve FASTER than expected?
4. Demand deceleration scenarios -- what could reduce demand growth?
5. Tier DOWNGRADE recommendations with specific rationale for each candidate
6. Competitive threats and substitution risks not captured in the screen

For tier_adjustments, only include candidates where you recommend a tier change (downgrade). \
If a candidate should stay at current tier, do not include it.

NEVER fabricate financial data or company metrics. Base all arguments strictly on the evidence \
provided. If a bear argument requires external data you don't have, state the assumption \
explicitly rather than fabricating evidence.

Your conviction_level reflects how strong the bear case is:
- HIGH: Material flaws identified with strong counter-evidence
- MEDIUM: Plausible concerns but the bull case has some merit
- LOW: Weak bear case, limited counter-evidence

Your risk_discount (0.0-1.0) represents how risky the overall thesis is from the bear perspective. \
0.0 = minimal risk (bear case is weak), 1.0 = maximum risk (thesis is fundamentally flawed).

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""

SYNTHESIS_SYSTEM_PROMPT = """\
You are a SYNTHESIS analyst reconciling optimist and pessimist reviews of an investment screen.

You have access to BOTH the bull-case (optimist) and bear-case (pessimist) analyses, as well as \
the original Phase 1-3 data. Your job is to produce a balanced final assessment.

Focus on:
1. Identify specific disagreements between optimist and pessimist -- state the topic, each side's \
view, your resolution, and the impact on tier assignments
2. For each disagreement, determine who was right and WHY with specific reference to evidence
3. Produce FINAL tier adjustments that override both sides where needed -- these are the \
authoritative tier changes after dialectic scrutiny
4. Assess overall conviction after weighing both perspectives
5. Identify key risks that SURVIVED the dialectic process (acknowledged by both sides or \
unresolved after scrutiny)

For final_tier_adjustments, include ALL tier changes you recommend (whether upgrades or \
downgrades from the current tiers). Only include a candidate if you are changing its tier.

NEVER fabricate data. Your synthesis must be grounded in the arguments presented by both sides \
and the underlying evidence from the Phase 1-3 data.

overall_conviction reflects the post-dialectic conviction:
- HIGH: Bull case survived scrutiny with minor concessions
- MEDIUM: Material debate remains but thesis is broadly intact
- LOW: Bear case raised significant unresolved concerns

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""


# -- Helper function for building the Phase 1-3 data package ------------------


def _build_phase_data_package(db, screen_id: int, workflow_run_id: int) -> str:
    """Build a comprehensive Phase 1-3 data package as a structured text block.

    Used by BOTH optimist and pessimist to ensure dialectic isolation (INV-6):
    both sides receive IDENTICAL input data.

    INV-AI-01: All data wrapped in XML tags for content/instruction separation.
    INV-PE-01: Batch queries to avoid N+1.
    """
    # Load screen
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise ValueError(f"No IST screen found with id {screen_id}")

    # Load all Phase 1-3 data in batch queries (INV-PE-01)
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

    # Build bottleneck name lookup for enriching other sections
    bn_id_to_name = {bn.id: bn.name for bn in bottlenecks}

    # Format claims section
    claims_text = "\n".join(
        f"- [{c.id}] {c.claim_text}"
        + (f" | Citation: {c.source_citation}" if c.source_citation else "")
        + (f" | Quant: {c.quantitative_anchor}" if c.quantitative_anchor else "")
        + (f" | Time: {c.temporal_marker}" if c.temporal_marker else "")
        + (f" | Confidence: {c.confidence}" if c.confidence else "")
        + (f" | Validated: {c.validation_verdict}" if c.validation_verdict else "")
        for c in claims
    ) if claims else "No claims extracted."

    # Format bottlenecks section
    bottlenecks_text = "\n".join(
        f"- {bn.name} (Phase {bn.phase}: {bn.phase_label}): {bn.description}"
        + (f" | Evidence: {bn.quantitative_evidence}" if bn.quantitative_evidence else "")
        + (f" | Temporal: {bn.temporal_marker}" if bn.temporal_marker else "")
        + (f" | Resolution: {bn.resolution_trigger}" if bn.resolution_trigger else "")
        for bn in bottlenecks
    ) if bottlenecks else "No bottlenecks identified."

    # Format demand models section
    demand_models_text = "\n".join(
        f"- Bottleneck: {bn_id_to_name.get(dm.bottleneck_id, 'Unknown')}"
        + f" | Formula: {dm.formula}"
        + f" | Base: {dm.base_case}"
        + f" | Bull: {dm.bull_case}"
        + f" | Bear: {dm.bear_case}"
        + (f" | Multiplier: {dm.multiplier_chain}" if dm.multiplier_chain else "")
        for dm in demand_models
    ) if demand_models else "No demand models built."

    # Format validations section
    validations_text = "\n".join(
        f"- Claim {v.claim_id}: {v.verdict} (confidence {v.confidence})"
        + f" | Evidence: {v.evidence}"
        for v in validations
    ) if validations else "No validations performed."

    # Format candidates section
    candidates_text = "\n".join(
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
    ) if candidates else "No equity candidates identified."

    # Format effects chains section
    effects_text = "\n".join(
        f"- Order {ec.effect_order}: {ec.thesis} -> {ec.effect_description}"
        + (f" | Ticker: {_get_ticker_for_candidate(candidates, ec.equity_candidate_id)}"
           if ec.equity_candidate_id else "")
        for ec in effects_chains
    ) if effects_chains else "No effects chains mapped."

    # Parse source bias from screen
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

    # Parse screening brief
    hypothesis_text = "Not specified."
    if screen.screening_brief:
        try:
            brief = json.loads(screen.screening_brief)
            hypothesis_text = brief.get("hypothesis", "Not specified.") or "Not specified."
        except (json.JSONDecodeError, TypeError):
            pass

    # Assemble the complete data package with XML delimiters (INV-AI-01)
    data_package = (
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

    return data_package


def _get_ticker_for_candidate(
    candidates: list[ISTEquityCandidate],
    candidate_id: Optional[int],
) -> str:
    """Look up ticker for a candidate by ID."""
    if candidate_id is None:
        return "N/A"
    for c in candidates:
        if c.id == candidate_id:
            return c.ticker
    return "Unknown"


# -- Registered workflow step handlers ----------------------------------------


@register_step("IST", "dialectic_optimist")
async def handle_dialectic_optimist(workflow_run_id: int) -> dict | None:
    """Bull-case dialectic review of the investment screen.

    Reads all Phase 1-3 data via the shared data package builder.
    Does NOT read pessimist output (INV-6: Dialectic Isolation).

    INV-BE-05: Creates its own SessionLocal, closed in finally block.
    INV-BE-06: JSON columns written via Pydantic serialization.
    """
    db = SessionLocal()
    try:
        # Find the IST screen linked to this workflow
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(
                f"No IST screen found for workflow {workflow_run_id}"
            )

        # Update screen status
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

        # Build Phase 1-3 data package (shared with pessimist — INV-6)
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

        # Build user prompt (INV-AI-01: data in XML tags, instructions separate)
        user_prompt = (
            f"{data_package}\n\n"
            f"Conduct a comprehensive BULL-CASE review of this investment screen.\n"
            f"For each equity candidate, evaluate whether a tier UPGRADE is warranted.\n"
            f"Return JSON matching this schema: "
            f"{DialecticReviewContent.model_json_schema()}"
        )

        # Call Claude (INV-AI-03: validated via Pydantic)
        result = await call_claude(
            system_prompt=OPTIMIST_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=DialecticReviewContent,
            max_tokens=16384,
        )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "dialectic_optimist",
                "message": "Storing optimist review...",
                "percent": 80,
            },
        )

        # Store result in ISTDialecticReview (INV-BE-06: Pydantic-serialized JSON)
        content_json = result.model_dump_json()
        review = ISTDialecticReview(
            screen_id=screen.id,
            side="OPTIMIST",
            content=content_json,
        )
        db.add(review)
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "side": "OPTIMIST",
            "convictionLevel": result.conviction_level,
            "riskDiscount": result.risk_discount,
            "keyArgumentCount": len(result.key_arguments),
            "tierAdjustmentCount": len(result.tier_adjustments),
        }
    finally:
        db.close()


@register_step("IST", "dialectic_pessimist")
async def handle_dialectic_pessimist(workflow_run_id: int) -> dict | None:
    """Bear-case dialectic review of the investment screen.

    Reads all Phase 1-3 data via the SAME shared data package builder.
    Does NOT read optimist output (INV-6: Dialectic Isolation enforced).

    INV-BE-05: Creates its own SessionLocal, closed in finally block.
    INV-BE-06: JSON columns written via Pydantic serialization.
    """
    db = SessionLocal()
    try:
        # Find the IST screen linked to this workflow
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(
                f"No IST screen found for workflow {workflow_run_id}"
            )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "dialectic_pessimist",
                "message": "Building bear-case analysis...",
                "percent": 10,
            },
        )

        # Build Phase 1-3 data package — IDENTICAL to what optimist received (INV-6)
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

        # Build user prompt (INV-AI-01: data in XML tags, instructions separate)
        user_prompt = (
            f"{data_package}\n\n"
            f"Conduct a comprehensive BEAR-CASE review of this investment screen.\n"
            f"Stress-test every assumption. For each equity candidate, evaluate whether "
            f"a tier DOWNGRADE is warranted.\n"
            f"Return JSON matching this schema: "
            f"{DialecticReviewContent.model_json_schema()}"
        )

        # Call Claude (INV-AI-03: validated via Pydantic)
        result = await call_claude(
            system_prompt=PESSIMIST_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=DialecticReviewContent,
            max_tokens=16384,
        )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "dialectic_pessimist",
                "message": "Storing pessimist review...",
                "percent": 80,
            },
        )

        # Store result in ISTDialecticReview (INV-BE-06: Pydantic-serialized JSON)
        content_json = result.model_dump_json()
        review = ISTDialecticReview(
            screen_id=screen.id,
            side="PESSIMIST",
            content=content_json,
        )
        db.add(review)
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "side": "PESSIMIST",
            "convictionLevel": result.conviction_level,
            "riskDiscount": result.risk_discount,
            "keyArgumentCount": len(result.key_arguments),
            "tierAdjustmentCount": len(result.tier_adjustments),
        }
    finally:
        db.close()


@register_step("IST", "dialectic_synthesis")
async def handle_dialectic_synthesis(workflow_run_id: int) -> dict | None:
    """Synthesize optimist and pessimist reviews into a balanced assessment.

    Reads BOTH optimist and pessimist reviews plus all Phase 1-3 data.
    This is the ONLY step that reads both sides.

    INV-BE-05: Creates its own SessionLocal, closed in finally block.
    INV-BE-06: JSON columns written via Pydantic serialization.
    """
    db = SessionLocal()
    try:
        # Find the IST screen linked to this workflow
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(
                f"No IST screen found for workflow {workflow_run_id}"
            )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "dialectic_synthesis",
                "message": "Loading optimist and pessimist reviews...",
                "percent": 10,
            },
        )

        # Load BOTH reviews (only synthesis reads both — INV-6)
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
                "Both optimist and pessimist reviews must be completed "
                "before synthesis. Missing: "
                + ("OPTIMIST " if not optimist_review else "")
                + ("PESSIMIST" if not pessimist_review else "")
            )

        # Build Phase 1-3 data package for context
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

        # Build user prompt with both reviews (INV-AI-01: data in XML tags)
        user_prompt = (
            f"{data_package}\n\n"
            f"<optimist_review>\n{optimist_review.content}\n</optimist_review>\n\n"
            f"<pessimist_review>\n{pessimist_review.content}\n</pessimist_review>\n\n"
            f"Synthesize the optimist and pessimist reviews. Reconcile their disagreements, "
            f"determine final tier adjustments, and assess overall conviction.\n"
            f"Return JSON matching this schema: "
            f"{SynthesisContent.model_json_schema()}"
        )

        # Call Claude (INV-AI-03: validated via Pydantic)
        result = await call_claude(
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=SynthesisContent,
            max_tokens=16384,
        )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "dialectic_synthesis",
                "message": "Storing synthesis results...",
                "percent": 80,
            },
        )

        # Store result in ISTDialecticReview (INV-BE-06: Pydantic-serialized JSON)
        content_json = result.model_dump_json()
        review = ISTDialecticReview(
            screen_id=screen.id,
            side="SYNTHESIS",
            content=content_json,
        )
        db.add(review)
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "side": "SYNTHESIS",
            "overallConviction": result.overall_conviction,
            "disagreementCount": len(result.disagreements),
            "finalTierAdjustmentCount": len(result.final_tier_adjustments),
            "keyRiskCount": len(result.key_risks),
        }
    finally:
        db.close()
