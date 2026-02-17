"""IST Phase 2: Thematic Analysis -- bottleneck mapping, demand modeling,
external validation, and content sufficiency quality gate.

Provides four registered workflow steps:
  - bottleneck_mapping (step_order 3): Map claims into temporal bottleneck cascade
  - demand_modeling (step_order 4): Build quantitative demand models per bottleneck
  - external_validation (step_order 5): Validate claims against external knowledge
  - content_sufficiency_gate (step_order 6): Pure server-side quality gate

Invariants enforced:
  - INV-AI-01: Content/instruction separation (user data in XML tags)
  - INV-AI-03: Pydantic-validated Claude outputs
  - INV-AI-04: Anti-hallucination instructions in system prompts
  - INV-BE-05: Background tasks own their DB sessions
  - INV-BE-06: JSON stored via Pydantic serialization
  - INV-PE-01: Avoid N+1 queries (eager load where possible)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models.ist import ISTBottleneck, ISTClaim, ISTDemandModel, ISTScreen, ISTValidation
from app.services.ist.claude_client import call_claude
from app.services.workflow_engine import register_step, emit_sse_event

logger = logging.getLogger(__name__)


# ── Pydantic models for Claude structured output (INV-AI-03) ────────────────


class BottleneckItem(BaseModel):
    """A single temporal bottleneck identified from claims."""

    name: str = Field(description="Bottleneck name")
    phase: int = Field(
        ge=0, le=3,
        description="0=cross-cutting, 1=near-term, 2=mid-term, 3=secular",
    )
    phase_label: str = Field(description="Human-readable phase label")
    description: str = Field(description="Bottleneck description")
    quantitative_evidence: Optional[str] = Field(
        default=None, description="Numeric data supporting this bottleneck"
    )
    temporal_marker: Optional[str] = Field(
        default=None, description="Time reference for this bottleneck"
    )
    resolution_trigger: Optional[str] = Field(
        default=None, description="What would resolve this bottleneck"
    )
    claim_indices: list[int] = Field(
        description="Indices into the claims list that map to this bottleneck"
    )
    causal_parent_name: Optional[str] = Field(
        default=None, description="Name of parent bottleneck if any"
    )


class BottleneckResult(BaseModel):
    """Structured output from the bottleneck mapping Claude call."""

    bottlenecks: list[BottleneckItem]


class DemandModelItem(BaseModel):
    """A single demand model for a bottleneck."""

    bottleneck_name: str = Field(description="Name of the bottleneck this models")
    formula: str = Field(description="Demand formula")
    base_case: dict = Field(description="Base case: {demand, tam, assumptions}")
    bull_case: dict = Field(description="Bull case scenario")
    bear_case: dict = Field(description="Bear case scenario")
    sensitivity_table: list[dict] = Field(
        description="Sensitivity analysis: [{variable, low, base, high, tamImpact}]"
    )
    multiplier_chain: Optional[str] = Field(
        default=None, description="Multiplier chain description"
    )


class DemandModelResult(BaseModel):
    """Structured output from the demand modeling Claude call."""

    models: list[DemandModelItem]


class ValidationItem(BaseModel):
    """Validation result for a single claim."""

    claim_index: int = Field(description="Index into the claims list")
    verdict: str = Field(
        description="confirmed, partially_confirmed, contradicted, or unvalidatable"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Validation confidence")
    evidence: str = Field(description="Evidence supporting the verdict")
    sources: list[dict] = Field(description="Sources: [{url, title}]")
    search_queries: list[str] = Field(description="Queries used for validation")


class ValidationResult(BaseModel):
    """Structured output from the external validation Claude call."""

    validations: list[ValidationItem]


# ── System prompts (INV-AI-04: anti-hallucination instructions) ─────────────

BOTTLENECK_MAPPING_SYSTEM_PROMPT = """You are an investment research analyst specializing in temporal bottleneck analysis.

Your task:
1. Read the provided claims carefully
2. Map claims into a temporal bottleneck cascade with these phases:
   - Phase 1 (near-term, 0-18 months): Immediate supply/demand bottlenecks
   - Phase 2 (mid-term, 18-36 months): Emerging structural bottlenecks
   - Phase 3 (secular, 3+ years): Long-term systemic bottlenecks
   - Phase 0 (cross-cutting): Bottlenecks that span multiple time horizons
3. Identify sequential dependencies between bottlenecks (causal chains) using causal_parent_name
4. Each bottleneck MUST cite quantitative evidence from the claims
5. Map each claim to at least one bottleneck via claim_indices (0-based index)

NEVER fabricate data, statistics, or financial figures. Only cite information found in the provided claims. If a bottleneck lacks quantitative evidence from the claims, set quantitative_evidence to null.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""

DEMAND_MODELING_SYSTEM_PROMPT = """You are a quantitative investment analyst building demand models from bottleneck analysis.

Your task:
1. For each bottleneck provided, build a quantitative demand model
2. Create base, bull, and bear case scenarios with demand estimates and TAM
3. Define the demand formula showing how inputs drive the output
4. Build a sensitivity table showing how key variables impact TAM
5. If applicable, describe the multiplier chain

Structure each scenario with keys: demand, tam, assumptions (as a dict or string).
Structure sensitivity_table entries with keys: variable, low, base, high, tamImpact.

NEVER fabricate specific company revenue or earnings data. You may estimate market-level TAM ranges based on the bottleneck evidence provided. If insufficient data exists for a credible model, state that explicitly in the formula field.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""

EXTERNAL_VALIDATION_SYSTEM_PROMPT = """You are a fact-checking analyst validating investment claims against your knowledge base.

Your task:
1. For each claim provided, assess whether it is:
   - confirmed: Claim is well-supported by widely available evidence
   - partially_confirmed: Claim has some support but key details may differ
   - contradicted: Claim conflicts with widely available evidence
   - unvalidatable: Insufficient information to assess the claim
2. Provide specific evidence for your verdict
3. List sources (with url and title) where possible -- use real, well-known sources
4. List the search queries you would use to validate each claim

NEVER fabricate source URLs. If you cannot identify a real source, use a descriptive placeholder URL like "https://example.com/industry-report" and note it is illustrative. Verdicts must be honest -- do not confirm claims you cannot verify.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""


# ── Registered workflow step handlers ───────────────────────────────────────


@register_step("IST", "bottleneck_mapping")
async def handle_bottleneck_mapping(workflow_run_id: int) -> dict | None:
    """Map extracted claims into a temporal bottleneck cascade.

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
        screen.status = "ANALYZING"
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "bottleneck_mapping",
                "message": "Mapping claims into temporal bottleneck cascade...",
                "percent": 10,
            },
        )

        # Load all claims for this screen (INV-PE-01: single query)
        claims = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .order_by(ISTClaim.id)
            .all()
        )

        if not claims:
            raise ValueError(
                "No claims found for bottleneck mapping. "
                "Run content_extraction first."
            )

        # Build claims text for Claude (INV-AI-01: user data in XML tags)
        claims_text = "\n".join(
            f"[{i}] {c.claim_text}"
            + (f" | Quant: {c.quantitative_anchor}" if c.quantitative_anchor else "")
            + (f" | Time: {c.temporal_marker}" if c.temporal_marker else "")
            for i, c in enumerate(claims)
        )

        user_prompt = (
            f"<claims>\n{claims_text}\n</claims>\n\n"
            f"Map these {len(claims)} claims into temporal bottlenecks.\n"
            f"Return JSON matching this schema: "
            f"{BottleneckResult.model_json_schema()}"
        )

        # Call Claude (INV-AI-03: validated via Pydantic)
        result = await call_claude(
            system_prompt=BOTTLENECK_MAPPING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=BottleneckResult,
        )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "bottleneck_mapping",
                "message": f"Identified {len(result.bottlenecks)} bottlenecks, storing...",
                "percent": 70,
            },
        )

        # Store bottleneck records -- two-pass for causal parent resolution
        # First pass: create all bottleneck records
        name_to_bottleneck: dict[str, ISTBottleneck] = {}
        for bn_data in result.bottlenecks:
            bottleneck = ISTBottleneck(
                screen_id=screen.id,
                name=bn_data.name,
                phase=bn_data.phase,
                phase_label=bn_data.phase_label,
                description=bn_data.description,
                quantitative_evidence=bn_data.quantitative_evidence,
                temporal_marker=bn_data.temporal_marker,
                resolution_trigger=bn_data.resolution_trigger,
            )
            db.add(bottleneck)
            name_to_bottleneck[bn_data.name] = bottleneck

        db.flush()  # Get IDs for causal parent resolution

        # Second pass: link causal parents
        for bn_data in result.bottlenecks:
            if bn_data.causal_parent_name and bn_data.causal_parent_name in name_to_bottleneck:
                child = name_to_bottleneck[bn_data.name]
                parent = name_to_bottleneck[bn_data.causal_parent_name]
                child.causal_parent_id = parent.id

        # Map claims to bottleneck names
        for bn_data in result.bottlenecks:
            for idx in bn_data.claim_indices:
                if 0 <= idx < len(claims):
                    claims[idx].bottleneck_name = bn_data.name

        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "bottlenecksIdentified": len(result.bottlenecks),
            "phaseBreakdown": {
                "phase0": sum(1 for b in result.bottlenecks if b.phase == 0),
                "phase1": sum(1 for b in result.bottlenecks if b.phase == 1),
                "phase2": sum(1 for b in result.bottlenecks if b.phase == 2),
                "phase3": sum(1 for b in result.bottlenecks if b.phase == 3),
            },
        }
    finally:
        db.close()


@register_step("IST", "demand_modeling")
async def handle_demand_modeling(workflow_run_id: int) -> dict | None:
    """Build quantitative demand models per bottleneck.

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
                "stepName": "demand_modeling",
                "message": "Building quantitative demand models...",
                "percent": 10,
            },
        )

        # Load bottlenecks for this screen (INV-PE-01: single query)
        bottlenecks = (
            db.query(ISTBottleneck)
            .filter(ISTBottleneck.screen_id == screen.id)
            .order_by(ISTBottleneck.id)
            .all()
        )

        if not bottlenecks:
            raise ValueError(
                "No bottlenecks found for demand modeling. "
                "Run bottleneck_mapping first."
            )

        # Build bottleneck text for Claude (INV-AI-01: user data in XML tags)
        bottleneck_text = "\n".join(
            f"- {bn.name} (Phase {bn.phase}: {bn.phase_label}): {bn.description}"
            + (f" | Evidence: {bn.quantitative_evidence}" if bn.quantitative_evidence else "")
            + (f" | Temporal: {bn.temporal_marker}" if bn.temporal_marker else "")
            for bn in bottlenecks
        )

        user_prompt = (
            f"<bottlenecks>\n{bottleneck_text}\n</bottlenecks>\n\n"
            f"Build quantitative demand models for each of these {len(bottlenecks)} bottlenecks.\n"
            f"Return JSON matching this schema: "
            f"{DemandModelResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=DEMAND_MODELING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=DemandModelResult,
        )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "demand_modeling",
                "message": f"Created {len(result.models)} demand models, storing...",
                "percent": 70,
            },
        )

        # Build name-to-bottleneck lookup for FK resolution
        name_to_id: dict[str, int] = {bn.name: bn.id for bn in bottlenecks}

        # Store demand model records (INV-BE-06: JSON via Pydantic serialization)
        for model_data in result.models:
            bottleneck_id = name_to_id.get(model_data.bottleneck_name)
            if bottleneck_id is None:
                # Try fuzzy match -- skip if no match at all
                logger.warning(
                    "Demand model references unknown bottleneck '%s', skipping",
                    model_data.bottleneck_name,
                )
                continue

            demand_model = ISTDemandModel(
                screen_id=screen.id,
                bottleneck_id=bottleneck_id,
                formula=model_data.formula,
                base_case=json.dumps(model_data.base_case),
                bull_case=json.dumps(model_data.bull_case),
                bear_case=json.dumps(model_data.bear_case),
                sensitivity_table=json.dumps(model_data.sensitivity_table),
                multiplier_chain=model_data.multiplier_chain,
            )
            db.add(demand_model)

        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "modelsCreated": len(result.models),
        }
    finally:
        db.close()


@register_step("IST", "external_validation")
async def handle_external_validation(workflow_run_id: int) -> dict | None:
    """Validate claims against external sources using Claude's knowledge.

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
                "stepName": "external_validation",
                "message": "Validating claims against external sources...",
                "percent": 10,
            },
        )

        # Load claims for this screen (INV-PE-01: single query)
        claims = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .order_by(ISTClaim.id)
            .all()
        )

        if not claims:
            raise ValueError(
                "No claims found for validation. "
                "Run content_extraction first."
            )

        # Build claims text for Claude (INV-AI-01: user data in XML tags)
        claims_text = "\n".join(
            f"[{i}] {c.claim_text}"
            + (f" | Quant: {c.quantitative_anchor}" if c.quantitative_anchor else "")
            + (f" | Time: {c.temporal_marker}" if c.temporal_marker else "")
            for i, c in enumerate(claims)
        )

        user_prompt = (
            f"<claims>\n{claims_text}\n</claims>\n\n"
            f"Validate each of these {len(claims)} claims.\n"
            f"Return JSON matching this schema: "
            f"{ValidationResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=EXTERNAL_VALIDATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=ValidationResult,
        )

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "external_validation",
                "message": f"Validated {len(result.validations)} claims, storing...",
                "percent": 70,
            },
        )

        # Store validation records and update claims
        verdict_counts: dict[str, int] = {
            "confirmed": 0,
            "partially_confirmed": 0,
            "contradicted": 0,
            "unvalidatable": 0,
        }

        for val_data in result.validations:
            idx = val_data.claim_index
            if idx < 0 or idx >= len(claims):
                logger.warning(
                    "Validation references out-of-range claim index %d, skipping",
                    idx,
                )
                continue

            claim = claims[idx]

            # Create ISTValidation record (INV-BE-06: JSON via serialization)
            validation = ISTValidation(
                screen_id=screen.id,
                claim_id=claim.id,
                verdict=val_data.verdict,
                confidence=val_data.confidence,
                evidence=val_data.evidence,
                sources=json.dumps(val_data.sources),
                search_queries=json.dumps(val_data.search_queries),
            )
            db.add(validation)

            # Update claim validation fields
            claim.is_validated = 1
            claim.validation_verdict = val_data.verdict
            claim.validation_source = json.dumps(val_data.sources)

            verdict_counts[val_data.verdict] = verdict_counts.get(val_data.verdict, 0) + 1

        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "claimsValidated": len(result.validations),
            "verdictBreakdown": verdict_counts,
        }
    finally:
        db.close()


@register_step("IST", "content_sufficiency_gate")
async def handle_content_sufficiency_gate(workflow_run_id: int) -> dict | None:
    """Content sufficiency quality gate -- pure server-side validation.

    No Claude call. Checks minimum thresholds before allowing
    the workflow to proceed past Phase 2.

    Checks:
      1. 3+ claims with quantitative anchors
      2. 1+ temporal marker across all claims
      3. Source bias assessed (screen.source_bias is not null)
      4. 1+ bottleneck identified

    If all pass: step completes with pass details.
    If any fail: raises ValueError (FAILED status stops workflow).

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
                "stepName": "content_sufficiency_gate",
                "message": "Running content sufficiency checks...",
                "percent": 20,
            },
        )

        # Run all checks
        deficiencies: list[str] = []

        # Check 1: 3+ claims with quantitative anchors
        quant_anchor_count = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .filter(ISTClaim.quantitative_anchor.isnot(None))
            .count()
        )
        if quant_anchor_count < 3:
            deficiencies.append(
                f"Insufficient quantitative anchors: {quant_anchor_count}/3 minimum"
            )

        # Check 2: 1+ temporal marker across all claims
        temporal_marker_count = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .filter(ISTClaim.temporal_marker.isnot(None))
            .count()
        )
        if temporal_marker_count < 1:
            deficiencies.append(
                "No temporal markers found across claims (need 1+ minimum)"
            )

        # Check 3: Source bias assessed
        if not screen.source_bias:
            deficiencies.append("Source bias assessment has not been completed")

        # Check 4: 1+ bottleneck identified
        bottleneck_count = (
            db.query(ISTBottleneck)
            .filter(ISTBottleneck.screen_id == screen.id)
            .count()
        )
        if bottleneck_count < 1:
            deficiencies.append(
                "No bottlenecks identified (need 1+ minimum)"
            )

        # Emit gate result event
        if deficiencies:
            await emit_sse_event(
                workflow_run_id,
                "gate_failed",
                {
                    "stepName": "content_sufficiency_gate",
                    "deficiencies": deficiencies,
                },
            )
            raise ValueError(
                "Content sufficiency gate FAILED: " + "; ".join(deficiencies)
            )

        # All checks passed
        gate_details = {
            "quantitativeAnchors": quant_anchor_count,
            "temporalMarkers": temporal_marker_count,
            "sourceBiasAssessed": True,
            "bottleneckCount": bottleneck_count,
        }

        await emit_sse_event(
            workflow_run_id,
            "gate_passed",
            {
                "stepName": "content_sufficiency_gate",
                "details": gate_details,
            },
        )

        return {
            "gateResult": "PASSED",
            **gate_details,
        }
    finally:
        db.close()
