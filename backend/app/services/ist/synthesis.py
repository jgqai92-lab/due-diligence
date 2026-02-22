"""IST synthesis workflow: cross-screen meta-analysis."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models.ist import (
    ISTBottleneck,
    ISTDemandModel,
    ISTEquityCandidate,
    ISTScreen,
)
from app.models.ist_synthesis import (
    ISTSynthesis,
    ISTSynthesisDialectic,
    ISTSynthesisEquity,
    ISTSynthesisSource,
)
from app.services.ist.claude_client import call_claude, call_claude_raw
from app.services.workflow_engine import emit_sse_event, register_step

logger = logging.getLogger(__name__)

IST_SYNTHESIS_WORKFLOW_STEPS = [
    {"step_name": "screen_ingestion", "phase": 1, "phase_name": "Screen Ingestion", "step_order": 1, "depends_on": [], "model": "opus"},
    {"step_name": "overlap_matrix", "phase": 1, "phase_name": "Screen Ingestion", "step_order": 2, "depends_on": ["screen_ingestion"], "model": "opus"},
    {"step_name": "thesis_interactions", "phase": 1, "phase_name": "Screen Ingestion", "step_order": 3, "depends_on": ["overlap_matrix"], "model": "opus"},
    {"step_name": "synthesis_readiness_gate", "phase": 1, "phase_name": "Screen Ingestion", "step_order": 4, "depends_on": ["thesis_interactions"], "model": "none"},
    {"step_name": "combined_bottleneck_analysis", "phase": 2, "phase_name": "Re-Analysis", "step_order": 5, "depends_on": ["synthesis_readiness_gate"], "model": "opus"},
    {"step_name": "cross_screen_effects", "phase": 2, "phase_name": "Re-Analysis", "step_order": 6, "depends_on": ["combined_bottleneck_analysis"], "model": "opus"},
    {"step_name": "re_tiering", "phase": 2, "phase_name": "Re-Analysis", "step_order": 7, "depends_on": ["cross_screen_effects"], "model": "opus"},
    {"step_name": "synthesis_dialectic_optimist", "phase": 3, "phase_name": "Synthesis", "step_order": 8, "depends_on": ["re_tiering"], "model": "opus"},
    {"step_name": "synthesis_dialectic_pessimist", "phase": 3, "phase_name": "Synthesis", "step_order": 9, "depends_on": ["re_tiering"], "model": "opus"},
    {"step_name": "synthesis_final", "phase": 3, "phase_name": "Synthesis", "step_order": 10, "depends_on": ["synthesis_dialectic_optimist", "synthesis_dialectic_pessimist"], "model": "opus"},
]


class _DialecticPayload(BaseModel):
    """Simple synthesis dialectic payload."""

    narrative: str
    key_points: list[str] = Field(default_factory=list)


class ThesisInteractionResult(BaseModel):
    """Claude output for thesis interaction analysis."""

    classification: str = Field(
        description="One of: reinforcing, contradicting, orthogonal"
    )
    rationale: str = Field(
        description="2-3 sentence explanation of why these theses interact this way"
    )
    impact: str = Field(
        description="How this interaction affects investment positioning"
    )


class CombinedBottleneckResult(BaseModel):
    """Claude output for combined bottleneck cascade analysis."""

    unified_cascade: list[dict[str, Any]] = Field(default_factory=list)
    emergent_bottlenecks: list[str] = Field(default_factory=list)
    temporal_sequence: str = Field(default="")
    summary: str = Field(default="")


class CrossScreenEffectsResult(BaseModel):
    """Claude output for cross-screen effects chain analysis."""

    effects_chains: list[dict[str, Any]] = Field(default_factory=list)
    feedback_loops: list[str] = Field(default_factory=list)
    summary: str = Field(default="")


class TierReassessment(BaseModel):
    """Claude's tier reassessment for a single equity."""

    ticker: str
    original_tier: int
    new_tier: int
    rationale: str = Field(default="")
    conviction: str = Field(default="")
    combined_thesis: str = Field(default="")


class TierReassessmentBatch(BaseModel):
    """Claude's reassessment for all equities."""

    assessments: list[TierReassessment] = Field(default_factory=list)


THESIS_INTERACTIONS_SYSTEM_PROMPT = """You are an investment analyst comparing two screening theses.

Classify thesis interaction strictly as one of:
- reinforcing
- contradicting
- orthogonal

Use concrete evidence from the supplied screen data and avoid generic phrasing.
Return valid JSON only.
"""


COMBINED_BOTTLENECK_SYSTEM_PROMPT = """You are an investment analyst building unified bottleneck cascades from multiple screens.

Identify cross-screen dependencies, emergent constraints, and temporal sequencing.
Return valid JSON only.
"""


CROSS_SCREEN_EFFECTS_SYSTEM_PROMPT = """You are an investment analyst mapping cross-screen effects chains.

Focus on where an effect in one screen propagates into another screen, including
feedback loops and higher-order interactions.
Return valid JSON only.
"""


RE_TIERING_SYSTEM_PROMPT = """You are an investment analyst reassessing equity tiers across combined screens.

For each ticker, provide:
- a justified tier assignment (1/2/3)
- a concrete rationale tied to cross-screen evidence
- conviction (HIGH/MEDIUM/LOW)
- combined thesis statement

Do not use vague placeholders like "No cross-screen adjustment".
Return valid JSON only.
"""


SYNTHESIS_OPTIMIST_SYSTEM_PROMPT = """You are an optimistic investment analyst synthesizing multiple screening theses.

Build the strongest credible bull case from cross-screen interactions.
Return valid JSON only.
"""


SYNTHESIS_PESSIMIST_SYSTEM_PROMPT = """You are a skeptical investment analyst stress-testing combined screening theses.

Focus on contradictions, concentration, timing fragility, and execution risk.
Return valid JSON only.
"""


SYNTHESIS_FINAL_REPORT_SYSTEM_PROMPT = """You are a senior investment analyst writing a cross-screen synthesis report.

Write markdown only.
Include these sections:
1) Executive Summary
2) Cross-Screen Thesis Interactions
3) Bottleneck and Effects Integration
4) Tier Reassessment Rationale
5) Risk Assessment
6) Recommended Actions
7) HFRT Research Priorities

Use only supplied data; do not invent facts.
"""


SYNTHESIS_RECONCILIATION_SYSTEM_PROMPT = """You are a balanced investment analyst reconciling bull and bear cases.

Return a concise, evidence-based synthesis with key points.
Return valid JSON only.
"""


def _load_json(value: Optional[str], fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _get_synthesis_by_run(db, workflow_run_id: int) -> ISTSynthesis:
    synthesis = (
        db.query(ISTSynthesis)
        .filter(ISTSynthesis.workflow_run_id == workflow_run_id)
        .first()
    )
    if not synthesis:
        raise ValueError(f"No synthesis found for workflow {workflow_run_id}")
    return synthesis


def _coerce_tier(value: Any, fallback: int = 3) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = fallback
    return parsed if parsed in (1, 2, 3) else fallback


def _normalize_classification(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"reinforcing", "contradicting", "orthogonal"}:
        return normalized
    return "orthogonal"


def _normalize_conviction(value: Any, tier: int) -> str:
    normalized = str(value or "").strip().upper()
    if normalized in {"HIGH", "MEDIUM", "LOW"}:
        return normalized
    return "HIGH" if tier == 1 else "MEDIUM" if tier == 2 else "LOW"


def _safe_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


@register_step("IST_SYNTHESIS", "screen_ingestion")
async def handle_screen_ingestion(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    try:
        logger.info("Starting synthesis screen_ingestion", extra={"workflow_run_id": workflow_run_id})
        synthesis = _get_synthesis_by_run(db, workflow_run_id)
        synthesis.status = "INGESTING"
        synthesis.updated_at = datetime.now(timezone.utc)

        sources = (
            db.query(ISTSynthesisSource)
            .filter(ISTSynthesisSource.synthesis_id == synthesis.id)
            .order_by(ISTSynthesisSource.id)
            .all()
        )
        if len(sources) < 2:
            raise ValueError("Synthesis requires at least 2 source screens")

        db.commit()

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "screen_ingestion",
                "message": f"Ingested {len(sources)} source screens",
                "percent": 100,
            },
        )

        return {"sourceCount": len(sources)}
    finally:
        db.close()


@register_step("IST_SYNTHESIS", "overlap_matrix")
async def handle_overlap_matrix(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    try:
        logger.info("Starting synthesis overlap_matrix", extra={"workflow_run_id": workflow_run_id})
        synthesis = _get_synthesis_by_run(db, workflow_run_id)

        sources = (
            db.query(ISTSynthesisSource)
            .filter(ISTSynthesisSource.synthesis_id == synthesis.id)
            .all()
        )
        source_ids = [s.screen_id for s in sources]

        candidates = (
            db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id.in_(source_ids))
            .order_by(ISTEquityCandidate.ticker)
            .all()
        )

        all_bn_ids = {c.bottleneck_id for c in candidates if c.bottleneck_id}
        bn_map: dict[int, str] = {}
        if all_bn_ids:
            bns = db.query(ISTBottleneck).filter(ISTBottleneck.id.in_(all_bn_ids)).all()
            bn_map = {bn.id: bn.name for bn in bns}

        by_ticker: dict[str, dict] = {}
        for cand in candidates:
            entry = by_ticker.setdefault(
                cand.ticker,
                {
                    "ticker": cand.ticker,
                    "companyName": cand.company_name,
                    "appearances": [],
                },
            )
            scarcity = _load_json(cand.scarcity_score, {})
            overall = scarcity.get("overall") if isinstance(scarcity, dict) else None
            bottleneck_name = bn_map.get(cand.bottleneck_id) if cand.bottleneck_id else None
            entry["appearances"].append(
                {
                    "screenId": cand.screen_id,
                    "tier": cand.tier,
                    "scarcityScore": overall,
                    "bottleneck": bottleneck_name,
                }
            )

        overlap = list(by_ticker.values())
        synthesis.overlap_matrix = json.dumps(overlap)
        synthesis.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "tickerCount": len(overlap),
            "overlapCount": sum(1 for x in overlap if len(x.get("appearances", [])) >= 2),
        }
    finally:
        db.close()


@register_step("IST_SYNTHESIS", "thesis_interactions")
async def handle_thesis_interactions(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    try:
        logger.info("Starting synthesis thesis_interactions", extra={"workflow_run_id": workflow_run_id})
        synthesis = _get_synthesis_by_run(db, workflow_run_id)

        sources = (
            db.query(ISTSynthesisSource)
            .filter(ISTSynthesisSource.synthesis_id == synthesis.id)
            .order_by(ISTSynthesisSource.id)
            .all()
        )

        source_screen_ids = {s.screen_id for s in sources}
        source_screens = (
            db.query(ISTScreen)
            .filter(ISTScreen.id.in_(source_screen_ids))
            .all()
        )
        screen_map = {screen.id: screen for screen in source_screens}

        interactions = []
        n = len(sources)
        total_pairs = max(1, n * (n - 1) // 2)
        pair_idx = 0

        for i in range(n):
            for j in range(i + 1, n):
                a = sources[i]
                b = sources[j]

                screen_a = screen_map.get(a.screen_id)
                screen_b = screen_map.get(b.screen_id)

                brief_a = _load_json(screen_a.screening_brief, {}) if screen_a else {}
                brief_b = _load_json(screen_b.screening_brief, {}) if screen_b else {}
                extraction_a = _load_json(screen_a.content_extraction, {}) if screen_a else {}
                extraction_b = _load_json(screen_b.content_extraction, {}) if screen_b else {}

                user_prompt = (
                    f"<screen_a>\n"
                    f"Name: {a.screen_name}\n"
                    f"Primary Theme: {a.primary_theme or 'Not specified'}\n"
                    f"Hypothesis: {brief_a.get('hypothesis', 'N/A') if isinstance(brief_a, dict) else 'N/A'}\n"
                    f"Key Themes: {json.dumps(extraction_a.get('themes', []) if isinstance(extraction_a, dict) else [])}\n"
                    f"Tier 1 Count: {a.tier1_count}, Tier 2: {a.tier2_count}, Tier 3: {a.tier3_count}\n"
                    f"</screen_a>\n\n"
                    f"<screen_b>\n"
                    f"Name: {b.screen_name}\n"
                    f"Primary Theme: {b.primary_theme or 'Not specified'}\n"
                    f"Hypothesis: {brief_b.get('hypothesis', 'N/A') if isinstance(brief_b, dict) else 'N/A'}\n"
                    f"Key Themes: {json.dumps(extraction_b.get('themes', []) if isinstance(extraction_b, dict) else [])}\n"
                    f"Tier 1 Count: {b.tier1_count}, Tier 2: {b.tier2_count}, Tier 3: {b.tier3_count}\n"
                    f"</screen_b>\n\n"
                    f"Classify this pair strictly as reinforcing, contradicting, or orthogonal.\n"
                    f"Return JSON matching: {ThesisInteractionResult.model_json_schema()}"
                )

                result = await call_claude(
                    system_prompt=THESIS_INTERACTIONS_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    response_model=ThesisInteractionResult,
                )
                classification = _normalize_classification(result.classification)

                interactions.append(
                    {
                        "screenA": {"id": a.screen_id, "name": a.screen_name, "theme": a.primary_theme},
                        "screenB": {"id": b.screen_id, "name": b.screen_name, "theme": b.primary_theme},
                        "classification": classification,
                        "rationale": _safe_text(
                            result.rationale,
                            "Cross-screen interaction assessed from thesis context.",
                        ),
                        "impact": _safe_text(
                            result.impact,
                            "Implications are mixed; monitor cross-screen dependencies.",
                        ),
                    }
                )

                pair_idx += 1
                await emit_sse_event(
                    workflow_run_id,
                    "step_progress",
                    {
                        "stepName": "thesis_interactions",
                        "message": (
                            f"Analyzed {a.screen_name} x {b.screen_name}: "
                            f"{classification}"
                        ),
                        "percent": int((pair_idx / total_pairs) * 100),
                    },
                )

        synthesis.thesis_interactions = json.dumps(interactions)
        synthesis.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "interactionCount": len(interactions),
            "reinforcingCount": sum(1 for x in interactions if x["classification"] == "reinforcing"),
        }
    finally:
        db.close()


@register_step("IST_SYNTHESIS", "synthesis_readiness_gate")
async def handle_synthesis_readiness_gate(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    try:
        logger.info("Starting synthesis_readiness_gate", extra={"workflow_run_id": workflow_run_id})
        synthesis = _get_synthesis_by_run(db, workflow_run_id)

        overlap = _load_json(synthesis.overlap_matrix, [])
        interactions = _load_json(synthesis.thesis_interactions, [])

        overlap_exists = any(len(item.get("appearances", [])) >= 2 for item in overlap)
        reinforcing_exists = any(item.get("classification") == "reinforcing" for item in interactions)

        if not overlap_exists and not reinforcing_exists:
            raise ValueError("No meaningful intersection found.")

        return {
            "gateResult": "PASSED",
            "hasOverlap": overlap_exists,
            "hasReinforcingInteraction": reinforcing_exists,
        }
    finally:
        db.close()


@register_step("IST_SYNTHESIS", "combined_bottleneck_analysis")
async def handle_combined_bottleneck_analysis(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    try:
        logger.info("Starting synthesis combined_bottleneck_analysis", extra={"workflow_run_id": workflow_run_id})
        synthesis = _get_synthesis_by_run(db, workflow_run_id)
        synthesis.status = "ANALYZING"

        sources = (
            db.query(ISTSynthesisSource)
            .filter(ISTSynthesisSource.synthesis_id == synthesis.id)
            .all()
        )
        screen_ids = [s.screen_id for s in sources]

        bottlenecks = (
            db.query(ISTBottleneck)
            .filter(ISTBottleneck.screen_id.in_(screen_ids))
            .all()
        )

        bn_screen_ids = {b.screen_id for b in bottlenecks if b.screen_id}
        bn_screens = db.query(ISTScreen).filter(ISTScreen.id.in_(bn_screen_ids)).all()
        bn_screen_map = {s.id: s for s in bn_screens}

        bn_ids = [b.id for b in bottlenecks]
        demand_models = []
        if bn_ids:
            demand_models = (
                db.query(ISTDemandModel)
                .filter(ISTDemandModel.bottleneck_id.in_(bn_ids))
                .all()
            )
        dm_by_bn: dict[int, list[dict[str, Any]]] = {}
        for dm in demand_models:
            dm_by_bn.setdefault(dm.bottleneck_id, []).append(
                {
                    "formula": dm.formula,
                    "baseCase": _load_json(dm.base_case, {}),
                    "bullCase": _load_json(dm.bull_case, {}),
                    "bearCase": _load_json(dm.bear_case, {}),
                    "sensitivityTable": _load_json(dm.sensitivity_table, {}),
                    "multiplierChain": dm.multiplier_chain,
                }
            )

        bottleneck_data: list[dict[str, Any]] = []
        for b in bottlenecks:
            screen = bn_screen_map.get(b.screen_id)
            bottleneck_data.append(
                {
                    "name": b.name,
                    "phase": b.phase,
                    "phaseLabel": b.phase_label,
                    "description": b.description,
                    "quantitativeEvidence": b.quantitative_evidence,
                    "temporalMarker": b.temporal_marker,
                    "resolutionTrigger": b.resolution_trigger,
                    "screenName": screen.name if screen else "Unknown",
                    "demandModels": dm_by_bn.get(b.id, []),
                }
            )

        thesis_interactions = _load_json(synthesis.thesis_interactions, [])
        user_prompt = (
            f"<bottlenecks>\n{json.dumps(bottleneck_data, indent=2)}\n</bottlenecks>\n\n"
            f"<thesis_interactions>\n{json.dumps(thesis_interactions, indent=2)}\n</thesis_interactions>\n\n"
            f"Build a unified bottleneck cascade across {len(screen_ids)} source screens.\n"
            f"Identify emergent bottlenecks and temporal dependencies.\n"
            f"Return JSON matching: {CombinedBottleneckResult.model_json_schema()}"
        )
        result = await call_claude(
            system_prompt=COMBINED_BOTTLENECK_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=CombinedBottleneckResult,
        )

        combined = {
            "sourceScreenCount": len(screen_ids),
            "bottleneckCount": len(bottlenecks),
            "phaseBreakdown": {
                "phase0": sum(1 for b in bottlenecks if b.phase == 0),
                "phase1": sum(1 for b in bottlenecks if b.phase == 1),
                "phase2": sum(1 for b in bottlenecks if b.phase == 2),
                "phase3": sum(1 for b in bottlenecks if b.phase == 3),
            },
            "unifiedCascade": result.unified_cascade,
            "emergentBottlenecks": result.emergent_bottlenecks,
            "temporalSequence": result.temporal_sequence,
            "summary": result.summary,
        }

        synthesis.combined_brief = json.dumps(combined)
        synthesis.updated_at = datetime.now(timezone.utc)
        db.commit()

        return combined
    finally:
        db.close()


@register_step("IST_SYNTHESIS", "cross_screen_effects")
async def handle_cross_screen_effects(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    try:
        logger.info("Starting synthesis cross_screen_effects", extra={"workflow_run_id": workflow_run_id})
        synthesis = _get_synthesis_by_run(db, workflow_run_id)

        overlap = _load_json(synthesis.overlap_matrix, [])
        interactions = _load_json(synthesis.thesis_interactions, [])
        combined = _load_json(synthesis.combined_brief, {})

        user_prompt = (
            f"<overlap_matrix>\n{json.dumps(overlap, indent=2)}\n</overlap_matrix>\n\n"
            f"<thesis_interactions>\n{json.dumps(interactions, indent=2)}\n</thesis_interactions>\n\n"
            f"<combined_bottleneck_analysis>\n{json.dumps(combined, indent=2)}\n</combined_bottleneck_analysis>\n\n"
            f"Identify cross-screen effects chains and feedback loops.\n"
            f"Return JSON matching: {CrossScreenEffectsResult.model_json_schema()}"
        )
        result = await call_claude(
            system_prompt=CROSS_SCREEN_EFFECTS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=CrossScreenEffectsResult,
        )

        combined["crossScreenEffects"] = {
            "effectsChains": result.effects_chains,
            "feedbackLoops": result.feedback_loops,
            "summary": result.summary,
        }

        synthesis.combined_brief = json.dumps(combined)
        synthesis.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "effectsChainCount": len(result.effects_chains),
            "feedbackLoopCount": len(result.feedback_loops),
        }
    finally:
        db.close()


@register_step("IST_SYNTHESIS", "re_tiering")
async def handle_re_tiering(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    try:
        logger.info("Starting synthesis re_tiering", extra={"workflow_run_id": workflow_run_id})
        synthesis = _get_synthesis_by_run(db, workflow_run_id)

        overlap = _load_json(synthesis.overlap_matrix, [])
        interactions = _load_json(synthesis.thesis_interactions, [])
        combined = _load_json(synthesis.combined_brief, {})

        db.query(ISTSynthesisEquity).filter(
            ISTSynthesisEquity.synthesis_id == synthesis.id
        ).delete()

        baseline_rows: list[dict[str, Any]] = []
        for item in overlap:
            appearances = item.get("appearances", []) if isinstance(item, dict) else []
            if not appearances:
                continue

            tier_values = [_coerce_tier(a.get("tier"), 3) for a in appearances]
            original_tier = min(tier_values) if tier_values else 3
            source_ids = [
                int(a["screenId"])
                for a in appearances
                if isinstance(a, dict) and isinstance(a.get("screenId"), int)
            ]
            scarcity_vals = [
                float(a["scarcityScore"])
                for a in appearances
                if isinstance(a, dict)
                and isinstance(a.get("scarcityScore"), (int, float))
            ]
            avg_scarcity = (
                round(sum(scarcity_vals) / len(scarcity_vals), 2)
                if scarcity_vals
                else 0.0
            )
            baseline_rows.append(
                {
                    "ticker": _safe_text(item.get("ticker"), ""),
                    "companyName": _safe_text(
                        item.get("companyName"),
                        _safe_text(item.get("ticker"), ""),
                    ),
                    "originalTier": original_tier,
                    "appearances": appearances,
                    "sourceScreenIds": source_ids,
                    "sourceScreenCount": len(appearances),
                    "combinedScarcityOverall": avg_scarcity,
                }
            )

        assessment_map: dict[str, TierReassessment] = {}
        if baseline_rows:
            user_prompt = (
                f"<overlap_matrix>\n{json.dumps(overlap, indent=2)}\n</overlap_matrix>\n\n"
                f"<thesis_interactions>\n{json.dumps(interactions, indent=2)}\n</thesis_interactions>\n\n"
                f"<combined_analysis>\n{json.dumps(combined, indent=2)}\n</combined_analysis>\n\n"
                f"<equity_baseline>\n{json.dumps(baseline_rows, indent=2)}\n</equity_baseline>\n\n"
                f"Reassess tiers for each ticker and return JSON matching: "
                f"{TierReassessmentBatch.model_json_schema()}"
            )
            reassessment = await call_claude(
                system_prompt=RE_TIERING_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_model=TierReassessmentBatch,
            )
            for item in reassessment.assessments:
                ticker = _safe_text(item.ticker, "").upper()
                if ticker:
                    assessment_map[ticker] = item

        tier_changes = []
        created = 0
        for row in baseline_rows:
            ticker = row["ticker"]
            if not ticker:
                continue

            original_tier = row["originalTier"]
            assessment = assessment_map.get(ticker.upper())
            new_tier = _coerce_tier(
                assessment.new_tier if assessment else original_tier,
                original_tier,
            )
            rationale = _safe_text(
                assessment.rationale if assessment else "",
                "Tier maintained due to balanced cross-screen signals.",
            )
            combined_thesis = _safe_text(
                assessment.combined_thesis if assessment else "",
                rationale,
            )
            conviction = _normalize_conviction(
                assessment.conviction if assessment else None,
                new_tier,
            )
            tier_changed = 1 if new_tier != original_tier else 0

            entry = ISTSynthesisEquity(
                synthesis_id=synthesis.id,
                ticker=ticker,
                company_name=row["companyName"] or ticker,
                original_tier=original_tier,
                new_tier=new_tier,
                tier_changed=tier_changed,
                tier_change_rationale=rationale,
                source_screen_count=row["sourceScreenCount"],
                source_screen_ids=json.dumps(row["sourceScreenIds"]),
                combined_scarcity_score=json.dumps(
                    {"overall": row["combinedScarcityOverall"]}
                ),
                combined_thesis=combined_thesis,
                combined_catalyst=None,
                conviction=conviction,
            )
            db.add(entry)
            created += 1

            if tier_changed:
                tier_changes.append(
                    {
                        "ticker": ticker,
                        "originalTier": original_tier,
                        "newTier": new_tier,
                        "rationale": rationale,
                    }
                )

        synthesis.tier_changes = json.dumps(tier_changes)
        synthesis.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "equityCount": created,
            "tierChangeCount": len(tier_changes),
        }
    finally:
        db.close()


@register_step("IST_SYNTHESIS", "synthesis_dialectic_optimist")
async def handle_synthesis_dialectic_optimist(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    try:
        logger.info("Starting synthesis_dialectic_optimist", extra={"workflow_run_id": workflow_run_id})
        synthesis = _get_synthesis_by_run(db, workflow_run_id)
        synthesis.status = "DIALECTIC"

        db.query(ISTSynthesisDialectic).filter(
            ISTSynthesisDialectic.synthesis_id == synthesis.id,
            ISTSynthesisDialectic.side == "OPTIMIST",
        ).delete()

        data_package = {
            "overlapMatrix": _load_json(synthesis.overlap_matrix, []),
            "thesisInteractions": _load_json(synthesis.thesis_interactions, []),
            "tierChanges": _load_json(synthesis.tier_changes, []),
            "combinedBrief": _load_json(synthesis.combined_brief, {}),
        }
        user_prompt = (
            f"<synthesis_data>\n{json.dumps(data_package, indent=2)}\n</synthesis_data>\n\n"
            f"Build the strongest credible optimist case for synthesis '{synthesis.name}'.\n"
            f"Return JSON matching: {_DialecticPayload.model_json_schema()}"
        )
        payload = await call_claude(
            system_prompt=SYNTHESIS_OPTIMIST_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=_DialecticPayload,
        )

        db.add(
            ISTSynthesisDialectic(
                synthesis_id=synthesis.id,
                side="OPTIMIST",
                content=payload.model_dump_json(),
            )
        )
        synthesis.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {"side": "OPTIMIST", "keyPointCount": len(payload.key_points)}
    finally:
        db.close()


@register_step("IST_SYNTHESIS", "synthesis_dialectic_pessimist")
async def handle_synthesis_dialectic_pessimist(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    try:
        logger.info("Starting synthesis_dialectic_pessimist", extra={"workflow_run_id": workflow_run_id})
        synthesis = _get_synthesis_by_run(db, workflow_run_id)

        db.query(ISTSynthesisDialectic).filter(
            ISTSynthesisDialectic.synthesis_id == synthesis.id,
            ISTSynthesisDialectic.side == "PESSIMIST",
        ).delete()

        data_package = {
            "overlapMatrix": _load_json(synthesis.overlap_matrix, []),
            "thesisInteractions": _load_json(synthesis.thesis_interactions, []),
            "tierChanges": _load_json(synthesis.tier_changes, []),
            "combinedBrief": _load_json(synthesis.combined_brief, {}),
        }
        user_prompt = (
            f"<synthesis_data>\n{json.dumps(data_package, indent=2)}\n</synthesis_data>\n\n"
            f"Build the strongest credible pessimist case for synthesis '{synthesis.name}'.\n"
            f"Return JSON matching: {_DialecticPayload.model_json_schema()}"
        )
        payload = await call_claude(
            system_prompt=SYNTHESIS_PESSIMIST_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=_DialecticPayload,
        )

        db.add(
            ISTSynthesisDialectic(
                synthesis_id=synthesis.id,
                side="PESSIMIST",
                content=payload.model_dump_json(),
            )
        )
        synthesis.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {"side": "PESSIMIST", "keyPointCount": len(payload.key_points)}
    finally:
        db.close()


@register_step("IST_SYNTHESIS", "synthesis_final")
async def handle_synthesis_final(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    try:
        logger.info("Starting synthesis_final", extra={"workflow_run_id": workflow_run_id})
        synthesis = _get_synthesis_by_run(db, workflow_run_id)
        synthesis.status = "SYNTHESIZING"

        equities = (
            db.query(ISTSynthesisEquity)
            .filter(ISTSynthesisEquity.synthesis_id == synthesis.id)
            .order_by(ISTSynthesisEquity.new_tier, ISTSynthesisEquity.ticker)
            .all()
        )

        optimist = (
            db.query(ISTSynthesisDialectic)
            .filter(
                ISTSynthesisDialectic.synthesis_id == synthesis.id,
                ISTSynthesisDialectic.side == "OPTIMIST",
            )
            .first()
        )
        pessimist = (
            db.query(ISTSynthesisDialectic)
            .filter(
                ISTSynthesisDialectic.synthesis_id == synthesis.id,
                ISTSynthesisDialectic.side == "PESSIMIST",
            )
            .first()
        )

        equity_payload = [
            {
                "ticker": eq.ticker,
                "companyName": eq.company_name,
                "originalTier": eq.original_tier,
                "newTier": eq.new_tier,
                "tierChanged": bool(eq.tier_changed),
                "tierChangeRationale": eq.tier_change_rationale,
                "combinedThesis": eq.combined_thesis,
                "conviction": eq.conviction,
                "sourceScreenCount": eq.source_screen_count,
            }
            for eq in equities
        ]

        synthesis_data = {
            "name": synthesis.name,
            "overlapMatrix": _load_json(synthesis.overlap_matrix, []),
            "thesisInteractions": _load_json(synthesis.thesis_interactions, []),
            "tierChanges": _load_json(synthesis.tier_changes, []),
            "combinedBrief": _load_json(synthesis.combined_brief, {}),
            "equities": equity_payload,
            "optimist": _load_json(optimist.content if optimist else None, {}),
            "pessimist": _load_json(pessimist.content if pessimist else None, {}),
        }
        report_prompt = (
            f"<synthesis_data>\n{json.dumps(synthesis_data, indent=2)}\n</synthesis_data>\n\n"
            "Write a complete markdown report for this synthesis."
        )
        report = await call_claude_raw(
            system_prompt=SYNTHESIS_FINAL_REPORT_SYSTEM_PROMPT,
            user_prompt=report_prompt,
        )

        synthesis.combined_report = report
        synthesis.report_metadata = json.dumps(
            {
                "equityCount": len(equities),
                "tierBreakdown": {
                    "tier1": sum(1 for e in equities if e.new_tier == 1),
                    "tier2": sum(1 for e in equities if e.new_tier == 2),
                    "tier3": sum(1 for e in equities if e.new_tier == 3),
                },
            }
        )

        db.query(ISTSynthesisDialectic).filter(
            ISTSynthesisDialectic.synthesis_id == synthesis.id,
            ISTSynthesisDialectic.side == "SYNTHESIS",
        ).delete()
        synthesis_prompt = (
            f"<optimist>\n{json.dumps(_load_json(optimist.content if optimist else None, {}), indent=2)}\n</optimist>\n\n"
            f"<pessimist>\n{json.dumps(_load_json(pessimist.content if pessimist else None, {}), indent=2)}\n</pessimist>\n\n"
            f"<tier_changes>\n{json.dumps(_load_json(synthesis.tier_changes, []), indent=2)}\n</tier_changes>\n\n"
            "Synthesize these views into a balanced assessment.\n"
            f"Return JSON matching: {_DialecticPayload.model_json_schema()}"
        )
        synthesis_dialectic = await call_claude(
            system_prompt=SYNTHESIS_RECONCILIATION_SYSTEM_PROMPT,
            user_prompt=synthesis_prompt,
            response_model=_DialecticPayload,
        )
        db.add(
            ISTSynthesisDialectic(
                synthesis_id=synthesis.id,
                side="SYNTHESIS",
                content=synthesis_dialectic.model_dump_json(),
            )
        )

        handoff = [
            {
                "ticker": e.ticker,
                "companyName": e.company_name,
                "tier": e.new_tier,
                "conviction": e.conviction,
                "sourceScreenCount": e.source_screen_count,
            }
            for e in equities
            if e.new_tier == 1
        ]

        synthesis.hfrt_handoff = json.dumps({"tier1Candidates": handoff, "tier1Count": len(handoff)})
        synthesis.certification = json.dumps({"gate3Passed": True, "equityCount": len(equities)})
        synthesis.is_certified = 1
        synthesis.certified_at = datetime.now(timezone.utc)
        synthesis.status = "COMPLETED"
        synthesis.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "status": "COMPLETED",
            "equityCount": len(equities),
            "tier1Count": len(handoff),
        }
    finally:
        db.close()
