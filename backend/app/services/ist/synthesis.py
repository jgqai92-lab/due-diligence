"""IST synthesis workflow: cross-screen meta-analysis."""

import json
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models.ist import ISTBottleneck, ISTEquityCandidate, ISTScreen
from app.models.ist_synthesis import (
    ISTSynthesis,
    ISTSynthesisDialectic,
    ISTSynthesisEquity,
    ISTSynthesisSource,
)
from app.services.workflow_engine import emit_sse_event, register_step

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


@register_step("IST_SYNTHESIS", "screen_ingestion")
async def handle_screen_ingestion(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    try:
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
            bottleneck_name = None
            if cand.bottleneck_id:
                bn = db.query(ISTBottleneck).filter(ISTBottleneck.id == cand.bottleneck_id).first()
                bottleneck_name = bn.name if bn else None
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
        synthesis = _get_synthesis_by_run(db, workflow_run_id)

        sources = (
            db.query(ISTSynthesisSource)
            .filter(ISTSynthesisSource.synthesis_id == synthesis.id)
            .order_by(ISTSynthesisSource.id)
            .all()
        )

        interactions = []
        for i in range(len(sources)):
            for j in range(i + 1, len(sources)):
                a = sources[i]
                b = sources[j]
                relation = "orthogonal"
                if a.primary_theme and b.primary_theme:
                    a_words = {w.lower() for w in a.primary_theme.split() if len(w) > 3}
                    b_words = {w.lower() for w in b.primary_theme.split() if len(w) > 3}
                    overlap = len(a_words.intersection(b_words))
                    if overlap >= 2:
                        relation = "reinforcing"
                if a.tier1_count and b.tier1_count and abs(a.tier1_count - b.tier1_count) <= 1:
                    relation = "reinforcing" if relation == "orthogonal" else relation

                interactions.append(
                    {
                        "screenA": {"id": a.screen_id, "name": a.screen_name, "theme": a.primary_theme},
                        "screenB": {"id": b.screen_id, "name": b.screen_name, "theme": b.primary_theme},
                        "classification": relation,
                        "rationale": "Theme overlap and tier alignment analysis",
                    }
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

        combined = {
            "sourceScreenCount": len(screen_ids),
            "bottleneckCount": len(bottlenecks),
            "phaseBreakdown": {
                "phase0": sum(1 for b in bottlenecks if b.phase == 0),
                "phase1": sum(1 for b in bottlenecks if b.phase == 1),
                "phase2": sum(1 for b in bottlenecks if b.phase == 2),
                "phase3": sum(1 for b in bottlenecks if b.phase == 3),
            },
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
        synthesis = _get_synthesis_by_run(db, workflow_run_id)

        interactions = _load_json(synthesis.thesis_interactions, [])
        reinforcing = [x for x in interactions if x.get("classification") == "reinforcing"]

        combined = _load_json(synthesis.combined_brief, {})
        combined["crossScreenEffects"] = {
            "reinforcingPairs": len(reinforcing),
            "observedLoops": len(reinforcing),
        }

        synthesis.combined_brief = json.dumps(combined)
        synthesis.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "reinforcingPairs": len(reinforcing),
            "observedLoops": len(reinforcing),
        }
    finally:
        db.close()


@register_step("IST_SYNTHESIS", "re_tiering")
async def handle_re_tiering(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    try:
        synthesis = _get_synthesis_by_run(db, workflow_run_id)

        overlap = _load_json(synthesis.overlap_matrix, [])
        interactions = _load_json(synthesis.thesis_interactions, [])
        has_reinforcing = any(x.get("classification") == "reinforcing" for x in interactions)
        has_contradicting = any(x.get("classification") == "contradicting" for x in interactions)

        db.query(ISTSynthesisEquity).filter(ISTSynthesisEquity.synthesis_id == synthesis.id).delete()

        tier_changes = []
        created = 0
        for item in overlap:
            appearances = item.get("appearances", [])
            if not appearances:
                continue

            tiers = [a.get("tier", 3) for a in appearances]
            original_tier = min(tiers)
            new_tier = original_tier
            rationale = "No cross-screen adjustment"

            if len(appearances) >= 2 and has_reinforcing:
                new_tier = max(1, original_tier - 1)
                rationale = "Multi-screen reinforcing thesis overlap"
            if has_contradicting and new_tier == original_tier:
                new_tier = min(3, original_tier + 1)
                rationale = "Cross-screen contradiction risk"

            tier_changed = 1 if new_tier != original_tier else 0

            entry = ISTSynthesisEquity(
                synthesis_id=synthesis.id,
                ticker=item.get("ticker"),
                company_name=item.get("companyName") or item.get("ticker"),
                original_tier=original_tier,
                new_tier=new_tier,
                tier_changed=tier_changed,
                tier_change_rationale=rationale,
                source_screen_count=len(appearances),
                source_screen_ids=json.dumps([a.get("screenId") for a in appearances]),
                combined_scarcity_score=json.dumps(
                    {
                        "overall": round(
                            sum((a.get("scarcityScore") or 0) for a in appearances)
                            / max(1, len(appearances)),
                            2,
                        )
                    }
                ),
                combined_thesis=rationale,
                combined_catalyst=None,
                conviction="HIGH" if new_tier == 1 else "MEDIUM" if new_tier == 2 else "LOW",
            )
            db.add(entry)
            created += 1

            if tier_changed:
                tier_changes.append(
                    {
                        "ticker": item.get("ticker"),
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
        synthesis = _get_synthesis_by_run(db, workflow_run_id)
        synthesis.status = "DIALECTIC"

        db.query(ISTSynthesisDialectic).filter(
            ISTSynthesisDialectic.synthesis_id == synthesis.id,
            ISTSynthesisDialectic.side == "OPTIMIST",
        ).delete()

        payload = _DialecticPayload(
            narrative="Optimist view: thesis interactions reinforce upside optionality across source screens.",
            key_points=["Cross-screen overlap strengthens conviction", "Reinforcing themes support upside persistence"],
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
        synthesis = _get_synthesis_by_run(db, workflow_run_id)

        db.query(ISTSynthesisDialectic).filter(
            ISTSynthesisDialectic.synthesis_id == synthesis.id,
            ISTSynthesisDialectic.side == "PESSIMIST",
        ).delete()

        payload = _DialecticPayload(
            narrative="Pessimist view: cross-screen coupling introduces fragility and timing risk.",
            key_points=["Over-concentration risk", "Execution sequencing risk across bottlenecks"],
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
        synthesis = _get_synthesis_by_run(db, workflow_run_id)
        synthesis.status = "SYNTHESIZING"

        equities = (
            db.query(ISTSynthesisEquity)
            .filter(ISTSynthesisEquity.synthesis_id == synthesis.id)
            .order_by(ISTSynthesisEquity.new_tier, ISTSynthesisEquity.ticker)
            .all()
        )

        lines = [f"# Combined Investment Thesis: {synthesis.name}", "", "## Re-tiered Equities"]
        if equities:
            lines.append("| Ticker | Original Tier | New Tier | Rationale |")
            lines.append("| --- | --- | --- | --- |")
            for eq in equities:
                lines.append(
                    f"| {eq.ticker} | {eq.original_tier} | {eq.new_tier} | {eq.tier_change_rationale or ''} |"
                )
        else:
            lines.append("No combined equities identified.")

        synthesis.combined_report = "\n".join(lines)
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
