"""IST Phase 2: thematic analysis and quality gating."""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.ist import ISTBottleneck, ISTClaim, ISTDemandModel, ISTScreen, ISTValidation
from app.services.ist.claude_client import call_claude
from app.services.workflow_engine import emit_sse_event, register_step

logger = logging.getLogger(__name__)


class BottleneckItem(BaseModel):
    """A single temporal bottleneck identified from claims."""

    name: str
    phase: int = Field(ge=0, le=3)
    phase_label: str
    description: str
    quantitative_evidence: Optional[str] = None
    temporal_marker: Optional[str] = None
    resolution_trigger: Optional[str] = None
    claim_indices: list[int]
    causal_parent_name: Optional[str] = None


class BottleneckResult(BaseModel):
    """Structured output from bottleneck mapping."""

    bottlenecks: list[BottleneckItem]


class DemandModelItem(BaseModel):
    """A single demand model for a bottleneck."""

    bottleneck_name: str
    formula: str
    base_case: dict
    bull_case: dict
    bear_case: dict
    sensitivity_table: list[dict]
    multiplier_chain: Optional[str] = None


class DemandModelResult(BaseModel):
    """Structured output from demand modeling."""

    models: list[DemandModelItem]


class ValidationItem(BaseModel):
    """Validation result for one claim."""

    claim_index: int
    verdict: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    sources: list[dict]
    search_queries: list[str]


class ValidationResult(BaseModel):
    """Structured output from external validation."""

    validations: list[ValidationItem]


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

NEVER fabricate source URLs. If you cannot identify a real source, use a descriptive placeholder URL like \"https://example.com/industry-report\" and note it is illustrative. Verdicts must be honest -- do not confirm claims you cannot verify.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""


async def _run_bottleneck_mapping(
    screen: ISTScreen,
    claims: list[ISTClaim],
    db: Session,
    workflow_run_id: int,
    *,
    update_screen_status: bool = True,
    replace_artifact: bool = False,
) -> dict | None:
    """Core bottleneck-mapping logic for IST and IST_REFRESH."""
    if update_screen_status:
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

    if not claims:
        raise ValueError("No claims found for bottleneck mapping. Run content_extraction first.")

    if replace_artifact:
        db.query(ISTBottleneck).filter(ISTBottleneck.screen_id == screen.id).delete()
        db.query(ISTClaim).filter(ISTClaim.screen_id == screen.id).update({"bottleneck_name": None})

    claims_text = "\n".join(
        f"[{i}] {c.claim_text}"
        + (f" | Quant: {c.quantitative_anchor}" if c.quantitative_anchor else "")
        + (f" | Time: {c.temporal_marker}" if c.temporal_marker else "")
        for i, c in enumerate(claims)
    )

    user_prompt = (
        f"<claims>\n{claims_text}\n</claims>\n\n"
        f"Map these {len(claims)} claims into temporal bottlenecks.\n"
        f"Return JSON matching this schema: {BottleneckResult.model_json_schema()}"
    )

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

    db.flush()

    for bn_data in result.bottlenecks:
        if bn_data.causal_parent_name and bn_data.causal_parent_name in name_to_bottleneck:
            child = name_to_bottleneck[bn_data.name]
            parent = name_to_bottleneck[bn_data.causal_parent_name]
            child.causal_parent_id = parent.id

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


async def _run_demand_modeling(
    screen: ISTScreen,
    bottlenecks: list[ISTBottleneck],
    db: Session,
    workflow_run_id: int,
    *,
    replace_artifact: bool = False,
) -> dict | None:
    """Core demand-modeling logic for IST and IST_REFRESH."""
    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "demand_modeling",
            "message": "Building quantitative demand models...",
            "percent": 10,
        },
    )

    if not bottlenecks:
        raise ValueError("No bottlenecks found for demand modeling. Run bottleneck_mapping first.")

    if replace_artifact:
        db.query(ISTDemandModel).filter(ISTDemandModel.screen_id == screen.id).delete()

    bottleneck_text = "\n".join(
        f"- {bn.name} (Phase {bn.phase}: {bn.phase_label}): {bn.description}"
        + (f" | Evidence: {bn.quantitative_evidence}" if bn.quantitative_evidence else "")
        + (f" | Temporal: {bn.temporal_marker}" if bn.temporal_marker else "")
        for bn in bottlenecks
    )

    user_prompt = (
        f"<bottlenecks>\n{bottleneck_text}\n</bottlenecks>\n\n"
        f"Build quantitative demand models for each of these {len(bottlenecks)} bottlenecks.\n"
        f"Return JSON matching this schema: {DemandModelResult.model_json_schema()}"
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

    name_to_id: dict[str, int] = {bn.name: bn.id for bn in bottlenecks}

    for model_data in result.models:
        bottleneck_id = name_to_id.get(model_data.bottleneck_name)
        if bottleneck_id is None:
            logger.warning(
                "Demand model references unknown bottleneck '%s', skipping",
                model_data.bottleneck_name,
            )
            continue

        db.add(
            ISTDemandModel(
                screen_id=screen.id,
                bottleneck_id=bottleneck_id,
                formula=model_data.formula,
                base_case=json.dumps(model_data.base_case),
                bull_case=json.dumps(model_data.bull_case),
                bear_case=json.dumps(model_data.bear_case),
                sensitivity_table=json.dumps(model_data.sensitivity_table),
                multiplier_chain=model_data.multiplier_chain,
            )
        )

    screen.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"modelsCreated": len(result.models)}


async def _run_external_validation(
    screen: ISTScreen,
    claims: list[ISTClaim],
    db: Session,
    workflow_run_id: int,
    *,
    replace_artifact: bool = False,
) -> dict | None:
    """Core external-validation logic for IST and IST_REFRESH."""
    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "external_validation",
            "message": "Validating claims against external sources...",
            "percent": 10,
        },
    )

    if not claims:
        raise ValueError("No claims found for validation. Run content_extraction first.")

    if replace_artifact:
        db.query(ISTValidation).filter(ISTValidation.screen_id == screen.id).delete()
        for claim in claims:
            claim.is_validated = 0
            claim.validation_verdict = None
            claim.validation_source = None

    claims_text = "\n".join(
        f"[{i}] {c.claim_text}"
        + (f" | Quant: {c.quantitative_anchor}" if c.quantitative_anchor else "")
        + (f" | Time: {c.temporal_marker}" if c.temporal_marker else "")
        for i, c in enumerate(claims)
    )

    user_prompt = (
        f"<claims>\n{claims_text}\n</claims>\n\n"
        f"Validate each of these {len(claims)} claims.\n"
        f"Return JSON matching this schema: {ValidationResult.model_json_schema()}"
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
        db.add(
            ISTValidation(
                screen_id=screen.id,
                claim_id=claim.id,
                verdict=val_data.verdict,
                confidence=val_data.confidence,
                evidence=val_data.evidence,
                sources=json.dumps(val_data.sources),
                search_queries=json.dumps(val_data.search_queries),
            )
        )

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


@register_step("IST", "bottleneck_mapping")
async def handle_bottleneck_mapping(workflow_run_id: int) -> dict | None:
    """Map extracted claims into a temporal bottleneck cascade."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        claims = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .order_by(ISTClaim.id)
            .all()
        )

        return await _run_bottleneck_mapping(screen, claims, db, workflow_run_id)
    finally:
        db.close()


@register_step("IST", "demand_modeling")
async def handle_demand_modeling(workflow_run_id: int) -> dict | None:
    """Build quantitative demand models per bottleneck."""
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

        return await _run_demand_modeling(screen, bottlenecks, db, workflow_run_id)
    finally:
        db.close()


@register_step("IST", "external_validation")
async def handle_external_validation(workflow_run_id: int) -> dict | None:
    """Validate claims against external sources."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        claims = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .order_by(ISTClaim.id)
            .all()
        )

        return await _run_external_validation(screen, claims, db, workflow_run_id)
    finally:
        db.close()


@register_step("IST", "content_sufficiency_gate")
async def handle_content_sufficiency_gate(workflow_run_id: int) -> dict | None:
    """Content sufficiency quality gate (deterministic server-side)."""
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
                "stepName": "content_sufficiency_gate",
                "message": "Running content sufficiency checks...",
                "percent": 20,
            },
        )

        deficiencies: list[str] = []

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

        temporal_marker_count = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .filter(ISTClaim.temporal_marker.isnot(None))
            .count()
        )
        if temporal_marker_count < 1:
            deficiencies.append("No temporal markers found across claims (need 1+ minimum)")

        if not screen.source_bias:
            deficiencies.append("Source bias assessment has not been completed")

        bottleneck_count = (
            db.query(ISTBottleneck)
            .filter(ISTBottleneck.screen_id == screen.id)
            .count()
        )
        if bottleneck_count < 1:
            deficiencies.append("No bottlenecks identified (need 1+ minimum)")

        if deficiencies:
            await emit_sse_event(
                workflow_run_id,
                "gate_failed",
                {
                    "stepName": "content_sufficiency_gate",
                    "deficiencies": deficiencies,
                },
            )
            raise ValueError("Content sufficiency gate FAILED: " + "; ".join(deficiencies))

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
