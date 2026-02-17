"""IST Phase 5: Final Synthesis -- master screen, rotation strategy, catalyst calendar,
stress tests, report generation, screen coherence gate, certification, and HFRT handoff.

Provides eight registered workflow steps:
  - master_screen (step_order 15): Ranked equity list with conviction scores
  - rotation_strategy (step_order 16): Phase-based allocation with rotation triggers
  - catalyst_calendar (step_order 17): Dated catalyst timeline
  - stress_tests (step_order 18): Framework-level + name-level stress tests
  - report_generation (step_order 19): Full markdown Investment Thesis Report (PRIMARY deliverable)
  - screen_coherence_gate (step_order 20): Server-side quality gate (no Claude)
  - screen_certification (step_order 21): Certify screen, write certification JSON (no Claude)
  - hfrt_handoff_generation (step_order 22): Extract Tier 1 candidates for HFRT bridge (no Claude)

Invariants enforced:
  - INV-AI-01: Content/instruction separation (user data in XML tags)
  - INV-AI-03: Pydantic-validated Claude outputs (except report_generation which uses raw)
  - INV-AI-04: Anti-hallucination instructions in system prompts (esp. report_generation)
  - INV-BE-05: Background tasks own their DB sessions
  - INV-BE-06: JSON stored via Pydantic serialization
  - INV-PE-01: Avoid N+1 queries (batch load all data)
  - INV-WF-01: Step ordering immutable -- report_generation at 19, coherence gate at 20
"""

import json
import logging
import math
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models.ist import (
    ISTBottleneck,
    ISTCatalystCalendar,
    ISTClaim,
    ISTDemandModel,
    ISTDialecticReview,
    ISTEffectsChain,
    ISTEquityCandidate,
    ISTMasterScreen,
    ISTReport,
    ISTRotationStrategy,
    ISTScreen,
    ISTStressTest,
    ISTValidation,
)
from app.services.ist.claude_client import call_claude, call_claude_raw
from app.services.workflow_engine import register_step, emit_sse_event

logger = logging.getLogger(__name__)


# -- Pydantic models for Claude structured output (INV-AI-03) -----------------


class RankedEquity(BaseModel):
    """A single ranked equity in the master screen."""

    rank: int = Field(ge=1, description="Rank position in the screen")
    ticker: str = Field(description="Stock ticker symbol")
    company_name: str = Field(description="Full company name")
    tier: int = Field(ge=1, le=3, description="Tier assignment (1-3)")
    scarcity_score: float = Field(ge=0, le=5, description="Overall scarcity score")
    conviction_score: int = Field(ge=0, le=100, description="Conviction score 0-100")
    pillar: str = Field(description="Bottleneck/pillar name the equity maps to")
    catalyst: Optional[str] = Field(default=None, description="Near-term catalyst")


class MasterScreenResult(BaseModel):
    """Structured output from master screen Claude call."""

    ranked_equities: list[RankedEquity]


class PhaseAllocation(BaseModel):
    """A single phase allocation in the rotation strategy."""

    phase: int = Field(description="Phase number")
    phase_label: str = Field(description="Phase label description")
    allocation_pct: float = Field(ge=0, le=100, description="Allocation percentage")
    tickers: list[str] = Field(description="Tickers to allocate to in this phase")
    rationale: str = Field(description="Rationale for this phase allocation")


class RotationTrigger(BaseModel):
    """A signal that triggers portfolio rotation."""

    trigger_name: str = Field(description="Name of the rotation trigger")
    description: str = Field(description="What the trigger means")
    action: str = Field(description="What action to take when triggered")
    affected_tickers: list[str] = Field(description="Tickers affected by this trigger")


class RiskLimit(BaseModel):
    """A risk limit for portfolio construction."""

    limit_name: str = Field(description="Name of the risk limit")
    limit_value: str = Field(description="Value or threshold")
    rationale: str = Field(description="Why this limit exists")


class RotationStrategyResult(BaseModel):
    """Structured output from rotation strategy Claude call."""

    phase_allocations: list[PhaseAllocation]
    rotation_triggers: list[RotationTrigger]
    risk_limits: list[RiskLimit]


class CatalystEvent(BaseModel):
    """A single catalyst event in the calendar."""

    date: str = Field(description="Expected date or date range (e.g. 'Q2 2025', '2025-06')")
    ticker: str = Field(description="Stock ticker related to this catalyst")
    event: str = Field(description="Description of the catalyst event")
    impact: str = Field(description="Expected impact (Positive/Negative/Mixed)")
    pillar: str = Field(description="Related bottleneck/pillar name")


class CatalystCalendarResult(BaseModel):
    """Structured output from catalyst calendar Claude call."""

    catalysts: list[CatalystEvent]


class FrameworkTest(BaseModel):
    """A framework-level stress test."""

    scenario: str = Field(description="Stress scenario name")
    description: str = Field(description="What the scenario tests")
    impact_assessment: str = Field(description="Assessment of impact")
    severity: str = Field(description="LOW, MEDIUM, or HIGH")
    affected_pillars: list[str] = Field(description="Pillars affected by this scenario")


class NameTest(BaseModel):
    """A name-level (equity-specific) stress test."""

    ticker: str = Field(description="Stock ticker")
    scenario: str = Field(description="Stress scenario for this equity")
    impact: str = Field(description="Expected impact on the equity")
    survival_probability: float = Field(
        ge=0.0, le=1.0, description="Probability the thesis survives"
    )


class SurvivalScore(BaseModel):
    """Aggregated survival score for a ticker."""

    ticker: str = Field(description="Stock ticker")
    overall_survival: float = Field(ge=0.0, le=1.0, description="Overall survival probability")
    weakest_scenario: str = Field(description="Most challenging stress scenario")


class StressTestResult(BaseModel):
    """Structured output from stress tests Claude call."""

    framework_tests: list[FrameworkTest]
    name_tests: list[NameTest]
    survival_scores: list[SurvivalScore]


# -- System prompts (INV-AI-04: anti-hallucination instructions) --------------


MASTER_SCREEN_SYSTEM_PROMPT = """\
You are an investment portfolio analyst producing a final ranked equity screen from a \
multi-phase investment screening process.

Your task:
1. Rank all equity candidates by conviction, considering:
   - Scarcity scores from Phase 3
   - Tier classifications
   - Dialectic synthesis adjustments (tier changes, conviction level, risk discounts)
   - Effects chain exposure
2. Assign a conviction_score (0-100) to each equity based on the weight of evidence
3. Map each equity to its primary pillar (bottleneck name)
4. Include the nearest catalyst for each equity if available

Ranking rules:
- Tier 1 candidates should generally rank higher than Tier 2, which rank higher than Tier 3
- Within a tier, higher scarcity scores rank higher
- Dialectic synthesis adjustments may override default tier ordering
- Conviction scores must be calibrated: Tier 1 + HIGH conviction = 80-100, \
Tier 2 + MEDIUM = 40-60, Tier 3 + LOW = 10-30

NEVER fabricate ticker symbols, company names, or financial data. Use ONLY the data provided \
in the input. If a candidate's data is insufficient, assign a lower conviction score rather \
than inventing details.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""


ROTATION_STRATEGY_SYSTEM_PROMPT = """\
You are a portfolio construction strategist designing a phase-based rotation strategy.

Your task:
1. Design phase_allocations: For each bottleneck phase (temporal phase), specify what \
percentage to allocate and which tickers to include
2. Define rotation_triggers: Signals that indicate when to rotate between phases
3. Set risk_limits: Concentration limits, sector exposure caps, and position sizing rules

Rules:
- Phase allocations should reflect temporal urgency (near-term bottlenecks get higher allocation early)
- Rotation triggers should be based on resolution triggers from the bottleneck analysis
- Risk limits should prevent over-concentration in any single name or pillar
- Total allocation percentages across phases should be meaningful but do not need to sum to 100

NEVER fabricate data. Base all recommendations on the bottleneck data, equity candidates, \
and master screen rankings provided.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""


CATALYST_CALENDAR_SYSTEM_PROMPT = """\
You are an investment catalyst analyst building a dated catalyst timeline.

Your task:
1. Identify date-specific catalysts for each equity candidate
2. Include catalysts from the bottleneck resolution triggers, temporal markers, and \
candidate catalyst fields
3. Each catalyst should have a clear date (or date range), ticker, event description, \
impact direction, and associated pillar

NEVER fabricate specific dates that are not supported by the data provided. If a date is \
approximate, use quarter or year notation (e.g., "Q3 2025", "H2 2025"). Only create catalyst \
entries where there is evidence in the provided data.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""


STRESS_TEST_SYSTEM_PROMPT = """\
You are a risk analyst performing stress tests on an investment thesis.

Your task:
1. Framework tests: Test the overall thesis framework with macro-level scenarios \
(e.g., "What if the scarcity resolves earlier?", "What if demand drops?", \
"What if substitutes emerge?")
2. Name tests: Test each equity candidate individually with specific scenarios \
(e.g., competitive threat, regulatory risk, execution failure)
3. Survival scores: For each equity, assess the overall probability that the \
investment thesis survives stress testing, and identify the weakest scenario

NEVER fabricate financial projections or market data. Base all stress scenarios on the \
evidence provided. If a stress scenario outcome is genuinely uncertain, state the uncertainty \
rather than fabricating a precise impact estimate.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""


# INV-AI-04: Report generation MUST include explicit anti-hallucination instruction.
# "No new numbers, estimates, or claims. This is synthesis only."
REPORT_GENERATION_SYSTEM_PROMPT = """\
You are an investment report writer producing the final Investment Thesis Report.

CRITICAL ANTI-HALLUCINATION RULE:
No new numbers, estimates, or claims. This is synthesis only. You MUST only use data, \
numbers, and claims that appear in the provided input. Do NOT invent statistics, price \
targets, revenue estimates, or any quantitative claims not present in the data.

Report structure:
1. **Executive Summary**: Core investment insight in 2-3 sentences, followed by a \
consolidated screen table showing all equities with their tier, scarcity score, \
conviction, and primary catalyst.

2. **Pillar-by-Pillar Analysis**: One section per bottleneck/pillar. For each:
   - Describe the scarcity thesis
   - List the equity candidates mapped to this pillar
   - Include relevant stress test results as markdown blockquotes (> prefix)
   - Reference the dialectic synthesis conclusions

3. **Second & Third-Order Effects**: Summary of the effects chains analysis, \
highlighting non-obvious downstream opportunities.

4. **Portfolio Construction Guidance**: Present the tier-based allocation strategy, \
rotation triggers, and the catalyst calendar as a markdown table.

5. **Disclaimer**: Standard investment disclaimer noting this is AI-assisted research, \
not financial advice, and all data comes from the screened source material.

Write in clear, professional markdown. Use headers (##), bullet points, tables, and \
blockquotes for structure. The report should be comprehensive (1000+ words).

REMINDER: Synthesize ONLY from the provided data. No new numbers or claims."""


# -- Helper: Build comprehensive data package for Phase 5 steps ---------------


def _build_full_data_package(db, screen_id: int) -> str:
    """Build the complete Phase 1-5 data package for synthesis steps.

    INV-AI-01: All data wrapped in XML tags for content/instruction separation.
    INV-PE-01: Batch queries to avoid N+1.
    """
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    if not screen:
        raise ValueError(f"No IST screen found with id {screen_id}")

    # Load all data in batch queries (INV-PE-01)
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
    dialectic_reviews = (
        db.query(ISTDialecticReview)
        .filter(ISTDialecticReview.screen_id == screen_id)
        .order_by(ISTDialecticReview.side)
        .all()
    )

    # Build bottleneck name lookup
    bn_id_to_name = {bn.id: bn.name for bn in bottlenecks}

    # Parse screening brief
    hypothesis_text = "Not specified."
    if screen.screening_brief:
        try:
            brief = json.loads(screen.screening_brief)
            hypothesis_text = brief.get("hypothesis", "Not specified.") or "Not specified."
        except (json.JSONDecodeError, TypeError):
            pass

    # Parse source bias
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

    # Format claims
    claims_text = "\n".join(
        f"- [{c.id}] {c.claim_text}"
        + (f" | Citation: {c.source_citation}" if c.source_citation else "")
        + (f" | Quant: {c.quantitative_anchor}" if c.quantitative_anchor else "")
        + (f" | Time: {c.temporal_marker}" if c.temporal_marker else "")
        + (f" | Confidence: {c.confidence}" if c.confidence else "")
        + (f" | Validated: {c.validation_verdict}" if c.validation_verdict else "")
        for c in claims
    ) if claims else "No claims extracted."

    # Format bottlenecks
    bottlenecks_text = "\n".join(
        f"- {bn.name} (Phase {bn.phase}: {bn.phase_label}): {bn.description}"
        + (f" | Evidence: {bn.quantitative_evidence}" if bn.quantitative_evidence else "")
        + (f" | Temporal: {bn.temporal_marker}" if bn.temporal_marker else "")
        + (f" | Resolution: {bn.resolution_trigger}" if bn.resolution_trigger else "")
        for bn in bottlenecks
    ) if bottlenecks else "No bottlenecks identified."

    # Format demand models
    demand_models_text = "\n".join(
        f"- Bottleneck: {bn_id_to_name.get(dm.bottleneck_id, 'Unknown')}"
        + f" | Formula: {dm.formula}"
        + f" | Base: {dm.base_case}"
        + f" | Bull: {dm.bull_case}"
        + f" | Bear: {dm.bear_case}"
        + (f" | Multiplier: {dm.multiplier_chain}" if dm.multiplier_chain else "")
        for dm in demand_models
    ) if demand_models else "No demand models built."

    # Format validations
    validations_text = "\n".join(
        f"- Claim {v.claim_id}: {v.verdict} (confidence {v.confidence})"
        + f" | Evidence: {v.evidence}"
        for v in validations
    ) if validations else "No validations performed."

    # Format candidates
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

    # Format effects chains
    def _get_ticker(candidate_id):
        for c in candidates:
            if c.id == candidate_id:
                return c.ticker
        return "Unknown"

    effects_text = "\n".join(
        f"- Order {ec.effect_order}: {ec.thesis} -> {ec.effect_description}"
        + (f" | Ticker: {_get_ticker(ec.equity_candidate_id)}"
           if ec.equity_candidate_id else "")
        for ec in effects_chains
    ) if effects_chains else "No effects chains mapped."

    # Format dialectic reviews
    dialectic_text_parts = []
    for review in dialectic_reviews:
        dialectic_text_parts.append(
            f"[{review.side}]\n{review.content}"
        )
    dialectic_text = "\n\n".join(dialectic_text_parts) if dialectic_text_parts else "No dialectic reviews."

    # Assemble complete data package with XML delimiters (INV-AI-01)
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
        f"<effects_chains count=\"{len(effects_chains)}\">\n{effects_text}\n</effects_chains>\n\n"
        f"<dialectic_reviews count=\"{len(dialectic_reviews)}\">\n{dialectic_text}\n</dialectic_reviews>"
    )

    return data_package


def _run_invariant_checks(db, screen_id: int) -> list[dict]:
    """Run invariant checks 1-5 and return the results list.

    Reuses the same invariant logic from equity_identification.py and the router.
    """
    invariants = []

    # Load data
    claims = db.query(ISTClaim).filter(ISTClaim.screen_id == screen_id).all()
    candidates = (
        db.query(ISTEquityCandidate)
        .filter(ISTEquityCandidate.screen_id == screen_id)
        .all()
    )
    total_claims = len(claims)
    total_candidates = len(candidates)

    # INV-1: Source Citation Required
    claims_with_citation = sum(
        1 for c in claims
        if c.source_citation is not None and c.source_citation.strip() != ""
    )
    inv1_pass = total_claims > 0 and claims_with_citation == total_claims
    invariants.append({
        "id": "INV-1",
        "name": "Source Citation Required",
        "status": "PASS" if inv1_pass else "FAIL",
        "details": (
            f"All {total_claims} claims have source citations."
            if inv1_pass
            else f"{claims_with_citation}/{total_claims} claims have source citations."
        ),
    })

    # INV-2: Quantitative Anchor Required (>= 50%)
    claims_with_quant = sum(
        1 for c in claims
        if c.quantitative_anchor is not None and c.quantitative_anchor.strip() != ""
    )
    quant_pct = (claims_with_quant / total_claims * 100) if total_claims > 0 else 0
    inv2_pass = total_claims > 0 and quant_pct >= 50
    invariants.append({
        "id": "INV-2",
        "name": "Quantitative Anchor Required",
        "status": "PASS" if inv2_pass else "FAIL",
        "details": (
            f"{claims_with_quant}/{total_claims} claims ({quant_pct:.0f}%) have "
            f"quantitative anchors (>= 50% required)."
        ),
    })

    # INV-3: Temporal Marker Required
    claims_with_temporal = sum(
        1 for c in claims
        if c.temporal_marker is not None and c.temporal_marker.strip() != ""
    )
    inv3_pass = claims_with_temporal >= 1
    invariants.append({
        "id": "INV-3",
        "name": "Temporal Marker Required",
        "status": "PASS" if inv3_pass else "FAIL",
        "details": f"{claims_with_temporal} claims have temporal markers (>= 1 required).",
    })

    # INV-4: No Orphan Equities
    orphan_candidates = sum(1 for c in candidates if c.bottleneck_id is None)
    inv4_pass = total_candidates == 0 or orphan_candidates == 0
    invariants.append({
        "id": "INV-4",
        "name": "No Orphan Equities",
        "status": "PASS" if inv4_pass else "FAIL",
        "details": (
            f"All {total_candidates} candidates linked to bottlenecks."
            if inv4_pass
            else f"{orphan_candidates}/{total_candidates} candidates lack bottleneck linkage."
        ),
    })

    # INV-5: Tier Justification Required
    candidates_with_rationale = sum(
        1 for c in candidates
        if c.tier_rationale is not None and c.tier_rationale.strip() != ""
    )
    inv5_pass = total_candidates == 0 or candidates_with_rationale == total_candidates
    invariants.append({
        "id": "INV-5",
        "name": "Tier Justification Required",
        "status": "PASS" if inv5_pass else "FAIL",
        "details": (
            f"All {total_candidates} candidates have tier rationale."
            if inv5_pass
            else f"{candidates_with_rationale}/{total_candidates} candidates have tier rationale."
        ),
    })

    return invariants


# -- Registered workflow step handlers ----------------------------------------


@register_step("IST", "master_screen")
async def handle_master_screen(workflow_run_id: int) -> dict | None:
    """Produce a ranked equity list with conviction scores via Claude.

    Also runs invariant checks inline and stores compliance data.

    INV-BE-05: Creates its own SessionLocal, closed in finally block.
    INV-BE-06: JSON columns written via Pydantic serialization.
    """
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(
                f"No IST screen found for workflow {workflow_run_id}"
            )

        # Update screen status to SYNTHESIZING
        screen.status = "SYNTHESIZING"
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "master_screen",
                "message": "Building master screen...",
                "percent": 10,
            },
        )

        # Build full data package (INV-AI-01)
        data_package = _build_full_data_package(db, screen.id)

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "master_screen",
                "message": "Calling Claude for master screen ranking...",
                "percent": 30,
            },
        )

        user_prompt = (
            f"{data_package}\n\n"
            f"Produce a ranked equity screen from all the data above.\n"
            f"Rank by conviction considering scarcity scores, tier classifications, "
            f"and dialectic synthesis adjustments.\n"
            f"Return JSON matching this schema: "
            f"{MasterScreenResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=MASTER_SCREEN_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=MasterScreenResult,
            max_tokens=8192,
        )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "master_screen",
                "message": "Running invariant checks...",
                "percent": 70,
            },
        )

        # Run invariant checks inline
        invariants = _run_invariant_checks(db, screen.id)

        # Count tier 1 equities from the result
        tier1_count = sum(1 for eq in result.ranked_equities if eq.tier == 1)

        # Store master screen (INV-BE-06: Pydantic serialization)
        ranked_json = json.dumps([eq.model_dump() for eq in result.ranked_equities])
        invariant_json = json.dumps(invariants)

        master = ISTMasterScreen(
            screen_id=screen.id,
            ranked_equities=ranked_json,
            invariant_compliance=invariant_json,
            total_equities=len(result.ranked_equities),
            tier1_count=tier1_count,
        )
        db.add(master)

        # Sync master screen tier assignments back to ISTEquityCandidate rows.
        # Phase 3 (tier_classification) sets initial tiers; Phase 5 (master_screen)
        # may reclassify based on the full dialectic + synthesis context.
        # Without this write-back, downstream consumers (Brief tab, HFRT handoff)
        # that query ISTEquityCandidate.tier would see stale Phase 3 values.
        for eq_result in result.ranked_equities:
            cand = (
                db.query(ISTEquityCandidate)
                .filter(
                    ISTEquityCandidate.screen_id == screen.id,
                    ISTEquityCandidate.ticker == eq_result.ticker,
                )
                .first()
            )
            if cand and cand.tier != eq_result.tier:
                cand.tier = eq_result.tier

        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "totalEquities": len(result.ranked_equities),
            "tier1Count": tier1_count,
            "invariantsPassed": sum(1 for inv in invariants if inv["status"] == "PASS"),
            "invariantsFailed": sum(1 for inv in invariants if inv["status"] == "FAIL"),
        }
    finally:
        db.close()


@register_step("IST", "rotation_strategy")
async def handle_rotation_strategy(workflow_run_id: int) -> dict | None:
    """Produce phase-based allocation with rotation triggers via Claude.

    INV-BE-05: Creates its own SessionLocal, closed in finally block.
    INV-BE-06: JSON columns written via Pydantic serialization.
    """
    db = SessionLocal()
    try:
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
                "stepName": "rotation_strategy",
                "message": "Designing rotation strategy...",
                "percent": 10,
            },
        )

        data_package = _build_full_data_package(db, screen.id)

        # Also include master screen if available
        master = (
            db.query(ISTMasterScreen)
            .filter(ISTMasterScreen.screen_id == screen.id)
            .first()
        )
        master_text = ""
        if master:
            master_text = (
                f"\n\n<master_screen>\n{master.ranked_equities}\n</master_screen>"
            )

        user_prompt = (
            f"{data_package}{master_text}\n\n"
            f"Design a phase-based rotation strategy for this investment screen.\n"
            f"Include phase allocations, rotation triggers, and risk limits.\n"
            f"Return JSON matching this schema: "
            f"{RotationStrategyResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=ROTATION_STRATEGY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=RotationStrategyResult,
            max_tokens=8192,
        )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "rotation_strategy",
                "message": "Storing rotation strategy...",
                "percent": 80,
            },
        )

        # Store rotation strategy (INV-BE-06: Pydantic serialization)
        rotation = ISTRotationStrategy(
            screen_id=screen.id,
            phase_allocations=json.dumps([pa.model_dump() for pa in result.phase_allocations]),
            rotation_triggers=json.dumps([rt.model_dump() for rt in result.rotation_triggers]),
            risk_limits=json.dumps([rl.model_dump() for rl in result.risk_limits]),
        )
        db.add(rotation)
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "phaseCount": len(result.phase_allocations),
            "triggerCount": len(result.rotation_triggers),
            "riskLimitCount": len(result.risk_limits),
        }
    finally:
        db.close()


@register_step("IST", "catalyst_calendar")
async def handle_catalyst_calendar(workflow_run_id: int) -> dict | None:
    """Generate dated catalyst timeline via Claude.

    INV-BE-05: Creates its own SessionLocal, closed in finally block.
    INV-BE-06: JSON columns written via Pydantic serialization.
    """
    db = SessionLocal()
    try:
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
                "stepName": "catalyst_calendar",
                "message": "Building catalyst calendar...",
                "percent": 10,
            },
        )

        data_package = _build_full_data_package(db, screen.id)

        user_prompt = (
            f"{data_package}\n\n"
            f"Generate a dated catalyst timeline for all equity candidates.\n"
            f"Include catalysts from bottleneck resolution triggers, temporal markers, "
            f"and candidate catalyst fields.\n"
            f"Return JSON matching this schema: "
            f"{CatalystCalendarResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=CATALYST_CALENDAR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=CatalystCalendarResult,
            max_tokens=8192,
        )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "catalyst_calendar",
                "message": "Storing catalyst calendar...",
                "percent": 80,
            },
        )

        # Determine next catalyst date (earliest date string)
        next_date = None
        if result.catalysts:
            # Sort by date string (approximate but functional for dates/quarters)
            sorted_catalysts = sorted(result.catalysts, key=lambda c: c.date)
            next_date = sorted_catalysts[0].date

        # Store catalyst calendar (INV-BE-06: Pydantic serialization)
        calendar = ISTCatalystCalendar(
            screen_id=screen.id,
            catalysts=json.dumps([cat.model_dump() for cat in result.catalysts]),
            total_catalysts=len(result.catalysts),
            next_catalyst_date=next_date,
        )
        db.add(calendar)
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "totalCatalysts": len(result.catalysts),
            "nextCatalystDate": next_date,
        }
    finally:
        db.close()


@register_step("IST", "stress_tests")
async def handle_stress_tests(workflow_run_id: int) -> dict | None:
    """Perform framework-level + name-level stress tests via Claude.

    INV-BE-05: Creates its own SessionLocal, closed in finally block.
    INV-BE-06: JSON columns written via Pydantic serialization.
    """
    db = SessionLocal()
    try:
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
                "stepName": "stress_tests",
                "message": "Running stress tests...",
                "percent": 10,
            },
        )

        data_package = _build_full_data_package(db, screen.id)

        user_prompt = (
            f"{data_package}\n\n"
            f"Perform comprehensive stress tests on this investment thesis.\n"
            f"Include framework-level macro scenarios, name-level equity-specific tests, "
            f"and overall survival scores for each equity.\n"
            f"Return JSON matching this schema: "
            f"{StressTestResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=STRESS_TEST_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=StressTestResult,
            max_tokens=16384,
        )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "stress_tests",
                "message": "Storing stress test results...",
                "percent": 80,
            },
        )

        # Store stress test (INV-BE-06: Pydantic serialization)
        stress = ISTStressTest(
            screen_id=screen.id,
            framework_tests=json.dumps([ft.model_dump() for ft in result.framework_tests]),
            name_tests=json.dumps([nt.model_dump() for nt in result.name_tests]),
            survival_scores=json.dumps([ss.model_dump() for ss in result.survival_scores]),
        )
        db.add(stress)
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "frameworkTestCount": len(result.framework_tests),
            "nameTestCount": len(result.name_tests),
            "survivalScoreCount": len(result.survival_scores),
        }
    finally:
        db.close()


@register_step("IST", "report_generation")
async def handle_report_generation(workflow_run_id: int) -> dict | None:
    """Generate the full markdown Investment Thesis Report -- PRIMARY IST deliverable.

    Uses call_claude_raw() for unstructured markdown output.

    INV-AI-04: System prompt includes explicit anti-hallucination instruction:
    "No new numbers, estimates, or claims. This is synthesis only."

    INV-BE-05: Creates its own SessionLocal, closed in finally block.
    INV-BE-06: JSON columns written via Pydantic serialization.
    """
    db = SessionLocal()
    try:
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
                "stepName": "report_generation",
                "message": "Generating Investment Thesis Report...",
                "percent": 5,
            },
        )

        # Build full data package
        data_package = _build_full_data_package(db, screen.id)

        # Load Phase 5 synthesis artifacts for report context
        master = (
            db.query(ISTMasterScreen)
            .filter(ISTMasterScreen.screen_id == screen.id)
            .first()
        )
        rotation = (
            db.query(ISTRotationStrategy)
            .filter(ISTRotationStrategy.screen_id == screen.id)
            .first()
        )
        catalyst = (
            db.query(ISTCatalystCalendar)
            .filter(ISTCatalystCalendar.screen_id == screen.id)
            .first()
        )
        stress = (
            db.query(ISTStressTest)
            .filter(ISTStressTest.screen_id == screen.id)
            .first()
        )

        # Build extra data XML from Phase 5 artifacts
        extra_parts = []
        if master:
            extra_parts.append(
                f"<master_screen>\n{master.ranked_equities}\n</master_screen>"
            )
        if rotation:
            extra_parts.append(
                f"<rotation_strategy>\n"
                f"Phase Allocations: {rotation.phase_allocations}\n"
                f"Rotation Triggers: {rotation.rotation_triggers}\n"
                f"Risk Limits: {rotation.risk_limits}\n"
                f"</rotation_strategy>"
            )
        if catalyst:
            extra_parts.append(
                f"<catalyst_calendar>\n{catalyst.catalysts}\n</catalyst_calendar>"
            )
        if stress:
            extra_parts.append(
                f"<stress_tests>\n"
                f"Framework Tests: {stress.framework_tests}\n"
                f"Name Tests: {stress.name_tests}\n"
                f"Survival Scores: {stress.survival_scores}\n"
                f"</stress_tests>"
            )
        extra_data = "\n\n".join(extra_parts)

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "report_generation",
                "message": "Generating Investment Thesis Report via Claude...",
                "percent": 20,
            },
        )

        user_prompt = (
            f"{data_package}\n\n"
            f"{extra_data}\n\n"
            f"Generate the complete Investment Thesis Report in markdown format.\n"
            f"Follow the report structure specified in the system prompt.\n"
            f"REMINDER: No new numbers, estimates, or claims. This is synthesis only."
        )

        # Use call_claude_raw for unstructured markdown (not Pydantic-parsed)
        report_content = await call_claude_raw(
            system_prompt=REPORT_GENERATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=16384,
        )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "report_generation",
                "message": "Storing Investment Thesis Report...",
                "percent": 85,
            },
        )

        # Count pillars (bottlenecks) and equities for metadata
        bottleneck_count = (
            db.query(ISTBottleneck)
            .filter(ISTBottleneck.screen_id == screen.id)
            .count()
        )
        candidates = (
            db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == screen.id)
            .all()
        )
        tier1_count = sum(1 for c in candidates if c.tier == 1)
        tier2_count = sum(1 for c in candidates if c.tier == 2)
        tier3_count = sum(1 for c in candidates if c.tier == 3)
        word_count = len(report_content.split())

        from app.config import settings
        report_metadata = json.dumps({
            "pillarCount": bottleneck_count,
            "equityCount": len(candidates),
            "tier1Count": tier1_count,
            "tier2Count": tier2_count,
            "tier3Count": tier3_count,
            "wordCount": word_count,
            "model": settings.claude_model,
        })

        # Generate title from screen name
        title = f"Investment Thesis Report: {screen.name}"

        report = ISTReport(
            screen_id=screen.id,
            title=title,
            content=report_content,
            report_metadata=report_metadata,
        )
        db.add(report)
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "title": title,
            "wordCount": word_count,
            "pillarCount": bottleneck_count,
            "equityCount": len(candidates),
        }
    finally:
        db.close()


def _bottleneck_name_in_report(name: str, content: str) -> tuple[bool, list[str]]:
    """Fuzzy check whether a bottleneck name is covered in the report.

    Splits the bottleneck name into "key words" (length >= 4 chars),
    lowercases everything, and checks what fraction of key words appear
    anywhere in the report content.  A bottleneck passes if >= 60% of its
    key words are found.

    Returns:
        (passed, missing_words) -- *missing_words* is the list of key words
        that were NOT found in the report (empty when passed is True or when
        no key words could be extracted).
    """
    words = name.split()
    key_words = [w.lower() for w in words if len(w) >= 4]

    # If the name has no qualifying key words (e.g. very short name),
    # fall back to a simple case-insensitive substring check.
    if not key_words:
        return (name.lower() in content.lower(), [])

    content_lower = content.lower()
    missing = [w for w in key_words if w not in content_lower]
    found_count = len(key_words) - len(missing)
    threshold = math.ceil(len(key_words) * 0.6)
    passed = found_count >= threshold
    return (passed, missing)


@register_step("IST", "screen_coherence_gate")
async def handle_screen_coherence_gate(workflow_run_id: int) -> dict | None:
    """Screen coherence quality gate -- pure server-side validation (no Claude call).

    Checks:
      1. Report exists and is not empty
      2. Report word count >= 1000
      3. All Tier 1 tickers appear in the report content
      4. All bottleneck names appear in the report content (pillar alignment)
      5. Master screen exists

    If fail: raises ValueError with deficiency list.
    Emits gate_passed or gate_failed SSE.

    INV-BE-05: Creates its own SessionLocal, closed in finally block.
    """
    db = SessionLocal()
    try:
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
                "stepName": "screen_coherence_gate",
                "message": "Running screen coherence checks...",
                "percent": 20,
            },
        )

        deficiencies: list[str] = []

        # Check 1: Report exists and is not empty
        report = (
            db.query(ISTReport)
            .filter(ISTReport.screen_id == screen.id)
            .first()
        )
        if not report:
            deficiencies.append("Report does not exist")
        elif not report.content or report.content.strip() == "":
            deficiencies.append("Report exists but content is empty")

        # Check 2: Report word count >= 1000
        if report and report.content:
            word_count = len(report.content.split())
            if word_count < 1000:
                deficiencies.append(
                    f"Report word count {word_count} is below minimum 1000"
                )
        elif not report:
            deficiencies.append("Cannot check word count: report missing")

        # Check 3: All Tier 1 tickers appear in the report content
        tier1_candidates = (
            db.query(ISTEquityCandidate)
            .filter(
                ISTEquityCandidate.screen_id == screen.id,
                ISTEquityCandidate.tier == 1,
            )
            .all()
        )
        if report and report.content:
            for cand in tier1_candidates:
                if cand.ticker not in report.content:
                    deficiencies.append(
                        f"Tier 1 ticker {cand.ticker} not found in report"
                    )

        # Check 4: All bottleneck names appear in the report content (fuzzy)
        bottlenecks = (
            db.query(ISTBottleneck)
            .filter(ISTBottleneck.screen_id == screen.id)
            .all()
        )
        if report and report.content:
            for bn in bottlenecks:
                passed, missing = _bottleneck_name_in_report(
                    bn.name, report.content
                )
                if not passed:
                    missing_str = ", ".join(missing) if missing else bn.name
                    deficiencies.append(
                        f"Bottleneck '{bn.name}' not sufficiently covered "
                        f"in report (missing key words: {missing_str})"
                    )

        # Check 5: Master screen exists
        master = (
            db.query(ISTMasterScreen)
            .filter(ISTMasterScreen.screen_id == screen.id)
            .first()
        )
        if not master:
            deficiencies.append("Master screen does not exist")

        # Check 6: Rotation strategy exists
        rotation = (
            db.query(ISTRotationStrategy)
            .filter(ISTRotationStrategy.screen_id == screen.id)
            .first()
        )
        if not rotation:
            deficiencies.append("Rotation strategy does not exist")

        # Check 7: Catalyst calendar exists
        catalyst = (
            db.query(ISTCatalystCalendar)
            .filter(ISTCatalystCalendar.screen_id == screen.id)
            .first()
        )
        if not catalyst:
            deficiencies.append("Catalyst calendar does not exist")

        # Check 8: Stress tests exist
        stress = (
            db.query(ISTStressTest)
            .filter(ISTStressTest.screen_id == screen.id)
            .first()
        )
        if not stress:
            deficiencies.append("Stress tests do not exist")

        # Check 9: All three dialectic reviews exist
        dialectic_sides = (
            db.query(ISTDialecticReview.side)
            .filter(ISTDialecticReview.screen_id == screen.id)
            .all()
        )
        existing_sides = {row.side for row in dialectic_sides}
        for required_side in ("OPTIMIST", "PESSIMIST", "SYNTHESIS"):
            if required_side not in existing_sides:
                deficiencies.append(f"Dialectic review '{required_side}' does not exist")

        # Check 10: All 5 core invariants pass
        invariant_results = _run_invariant_checks(db, screen.id)
        failed_invariants = [
            inv for inv in invariant_results if inv["status"] == "FAIL"
        ]
        for inv in failed_invariants:
            deficiencies.append(f"Invariant {inv['id']} ({inv['name']}) FAILED: {inv['details']}")

        # Check 11: Report metadata has pillar and equity counts
        if report and report.report_metadata:
            try:
                meta = json.loads(report.report_metadata)
                if meta.get("pillarCount", 0) < 1:
                    deficiencies.append("Report metadata pillarCount < 1")
                if meta.get("equityCount", 0) < 1:
                    deficiencies.append("Report metadata equityCount < 1")
            except (json.JSONDecodeError, TypeError):
                deficiencies.append("Report metadata is not valid JSON")

        # Emit gate result
        if deficiencies:
            await emit_sse_event(
                workflow_run_id,
                "gate_failed",
                {
                    "stepName": "screen_coherence_gate",
                    "deficiencies": deficiencies,
                },
            )
            raise ValueError(
                "Screen coherence gate FAILED: " + "; ".join(deficiencies)
            )

        # All checks passed
        gate_details = {
            "reportExists": True,
            "wordCount": len(report.content.split()) if report and report.content else 0,
            "tier1TickersPresent": len(tier1_candidates),
            "bottlenecksPresent": len(bottlenecks),
            "masterScreenExists": True,
        }

        await emit_sse_event(
            workflow_run_id,
            "gate_passed",
            {
                "stepName": "screen_coherence_gate",
                "details": gate_details,
            },
        )

        return {
            "gateResult": "PASSED",
            **gate_details,
        }
    finally:
        db.close()


@register_step("IST", "screen_certification")
async def handle_screen_certification(workflow_run_id: int) -> dict | None:
    """Certify the screen and record certification metadata -- no Claude call.

    Updates ISTScreen: is_certified = 1, certified_at = now, status = COMPLETED.
    Writes Gate 3 certification results to `ISTScreen.certification` JSON column.

    INV-BE-05: Creates its own SessionLocal, closed in finally block.
    INV-BE-06: JSON columns written via json.dumps.
    """
    db = SessionLocal()
    try:
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
                "stepName": "screen_certification",
                "message": "Certifying screen...",
                "percent": 20,
            },
        )

        now = datetime.now(timezone.utc)

        # Gather certification metadata from completed artifacts
        report = (
            db.query(ISTReport)
            .filter(ISTReport.screen_id == screen.id)
            .first()
        )
        master = (
            db.query(ISTMasterScreen)
            .filter(ISTMasterScreen.screen_id == screen.id)
            .first()
        )
        invariant_results = _run_invariant_checks(db, screen.id)
        invariants_passed = sum(1 for inv in invariant_results if inv["status"] == "PASS")
        invariants_failed = sum(1 for inv in invariant_results if inv["status"] == "FAIL")

        report_meta = {}
        if report and report.report_metadata:
            try:
                report_meta = json.loads(report.report_metadata)
            except (json.JSONDecodeError, TypeError):
                pass

        certification_data = {
            "certifiedAt": now.isoformat(),
            "gate3Passed": True,
            "invariantsPassed": invariants_passed,
            "invariantsFailed": invariants_failed,
            "invariantResults": invariant_results,
            "reportWordCount": report_meta.get("wordCount", 0),
            "pillarCount": report_meta.get("pillarCount", 0),
            "equityCount": report_meta.get("equityCount", 0),
            "tierBreakdown": {
                "tier1": report_meta.get("tier1Count", 0),
                "tier2": report_meta.get("tier2Count", 0),
                "tier3": report_meta.get("tier3Count", 0),
            },
            "totalRankedEquities": master.total_equities if master else 0,
            "model": report_meta.get("model", "unknown"),
        }

        # Update screen certification fields
        screen.is_certified = 1
        screen.certified_at = now
        screen.status = "COMPLETED"
        screen.updated_at = now
        screen.certification = json.dumps(certification_data)

        db.commit()

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "screen_certification",
                "message": "Screen certified successfully.",
                "percent": 100,
            },
        )

        return {
            "certified": True,
            "certifiedAt": now.isoformat(),
            "status": "COMPLETED",
            "invariantsPassed": invariants_passed,
            "invariantsFailed": invariants_failed,
        }
    finally:
        db.close()


@register_step("IST", "hfrt_handoff_generation")
async def handle_hfrt_handoff_generation(workflow_run_id: int) -> dict | None:
    """Generate HFRT handoff data from certified screen -- no Claude call.

    Extracts Tier 1 candidates and writes structured handoff data to
    `ISTScreen.hfrt_handoff` JSON column for the IST->HFRT bridge.

    INV-BE-05: Creates its own SessionLocal, closed in finally block.
    INV-BE-06: JSON columns written via json.dumps.
    """
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(
                f"No IST screen found for workflow {workflow_run_id}"
            )

        if not screen.is_certified:
            raise ValueError(
                f"Screen {screen.id} is not certified. "
                "Certification must pass before generating HFRT handoff."
            )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "hfrt_handoff_generation",
                "message": "Building HFRT handoff from Tier 1 candidates...",
                "percent": 20,
            },
        )

        # Build HFRT handoff data from Tier 1 candidates
        tier1_candidates = (
            db.query(ISTEquityCandidate)
            .filter(
                ISTEquityCandidate.screen_id == screen.id,
                ISTEquityCandidate.tier == 1,
            )
            .order_by(ISTEquityCandidate.id)
            .all()
        )

        # Load bottleneck names for the handoff (INV-PE-01: batch)
        bn_ids = {c.bottleneck_id for c in tier1_candidates if c.bottleneck_id}
        bn_map = {}
        if bn_ids:
            bns = (
                db.query(ISTBottleneck)
                .filter(ISTBottleneck.id.in_(bn_ids))
                .all()
            )
            bn_map = {bn.id: bn.name for bn in bns}

        handoff_candidates = []
        for cand in tier1_candidates:
            # scarcity_score is stored as JSON text: {"overall": 4.6, "dimensions": {...}}
            # Extract the numeric overall score for the handoff.
            scarcity_val = None
            if cand.scarcity_score:
                try:
                    parsed = json.loads(cand.scarcity_score)
                    scarcity_val = parsed.get("overall") if isinstance(parsed, dict) else parsed
                except (json.JSONDecodeError, TypeError):
                    scarcity_val = None
            handoff_candidates.append({
                "ticker": cand.ticker,
                "companyName": cand.company_name,
                "tier": cand.tier,
                "conviction": cand.conviction,
                "pillar": bn_map.get(cand.bottleneck_id, "Unknown"),
                "catalyst": cand.catalyst,
                "scarcityScore": scarcity_val,
            })

        handoff_data = {
            "screenName": screen.name,
            "screenId": screen.id,
            "certifiedAt": screen.certified_at.isoformat() if screen.certified_at else None,
            "tier1Count": len(handoff_candidates),
            "candidates": handoff_candidates,
        }

        # Write to hfrt_handoff column (INV-BE-06)
        screen.hfrt_handoff = json.dumps(handoff_data)
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "hfrt_handoff_generation",
                "message": f"HFRT handoff ready: {len(handoff_candidates)} Tier 1 candidate(s).",
                "percent": 100,
            },
        )

        return {
            "screenName": screen.name,
            "tier1Count": len(handoff_candidates),
            "candidates": [c["ticker"] for c in handoff_candidates],
        }
    finally:
        db.close()
