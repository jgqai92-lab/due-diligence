"""Trio orchestrator -- runs independent parallel persona pipeline and moderator synthesis.

Pipeline: Visser, Meldrum, Wissner-Gross run INDEPENDENTLY in parallel (no context handoff).
Then a Moderator synthesizes by comparing and contrasting all three views.

Uses SessionLocal() for DB sessions (same pattern as IST/HFRT services).
"""

import asyncio
import json
import logging
from typing import Optional

from app.config import settings
from app.database import SessionLocal
from app.models.persona import PersonaAnalysis
from app.models.ist import (
    ISTScreen, ISTClaim, ISTBottleneck, ISTDemandModel, ISTValidation,
    ISTEquityCandidate, ISTEffectsChain, ISTDialecticReview, ISTMasterScreen,
    ISTRotationStrategy, ISTCatalystCalendar, ISTStressTest, ISTReport,
)
from app.models.hfrt import HFRTProject, HFRTTemplate, HFRTDialecticReview
from app.services.persona.visser_analyst import analyze_visser
from app.services.persona.meldrum_analyst import analyze_meldrum
from app.services.persona.wissner_gross_analyst import analyze_wissner_gross
from app.services.persona.persona_prompts import MODERATOR_SYSTEM_PROMPT
from app.services.claude_client import call_claude_raw

logger = logging.getLogger(__name__)

IST_CONTEXT_BUDGET = 80_000
HFRT_CONTEXT_BUDGET = 60_000
JSON_FIELD_TRUNCATE = 2_000
TEMPLATE_TRUNCATE = 3_000


def _truncate_json_field(value: str, max_chars: int) -> str:
    """Truncate a string, appending '...(truncated)' marker if cut."""
    if not value or len(value) <= max_chars:
        return value or ""
    return value[:max_chars] + "...(truncated)"


def _safe_json_loads(value: str) -> dict | list | None:
    """Safely parse JSON, returning None on failure."""
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


async def run_trio_analysis(
    target_type: str,
    target_id: Optional[int],
    user_prompt: str,
    additional_context: Optional[str] = None,
    mode: str = "structured",
) -> dict:
    """Run independent parallel trio pipeline: [Visser | Meldrum | Wissner-Gross] -> Moderator.

    All three personas receive the SAME base context and answer independently.
    They have NO knowledge of each other's output. The Moderator then synthesizes
    by comparing and contrasting their independent views.

    Args:
        target_type: "ist_screen", "hfrt_project", or "standalone".
        target_id: ID of the target (None for standalone).
        user_prompt: The investment thesis or question.
        additional_context: Optional extra context.
        mode: "structured" or "freeform".

    Returns:
        Dict with visser, meldrum, wissner_gross, and moderator records.
    """
    context = additional_context or ""

    # If target is an IST screen or HFRT project, load context from DB
    if target_type == "ist_screen" and target_id:
        context = await _load_ist_context(target_id, context)
    elif target_type == "hfrt_project" and target_id:
        context = await _load_hfrt_context(target_id, context)

    # Run all three personas INDEPENDENTLY in parallel -- same context, no handoff
    visser_result, meldrum_result, wg_result = await asyncio.gather(
        analyze_visser(context, user_prompt, mode=mode),
        analyze_meldrum(context, user_prompt, mode=mode),
        analyze_wissner_gross(context, user_prompt, mode=mode),
    )

    # Store all three results
    visser_record, meldrum_record, wg_record = await asyncio.gather(
        _store_analysis("visser", target_type, target_id, context, visser_result, user_prompt),
        _store_analysis("meldrum", target_type, target_id, context, meldrum_result, user_prompt),
        _store_analysis("wissner_gross", target_type, target_id, context, wg_result, user_prompt),
    )

    # Moderator synthesizes all three independent views
    moderator_result = await _generate_moderator_synthesis(
        visser_result, meldrum_result, wg_result, user_prompt
    )
    moderator_record = await _store_analysis(
        "trio_summary", target_type, target_id, "", moderator_result, user_prompt
    )

    return {
        "visser": visser_record,
        "meldrum": meldrum_record,
        "wissner_gross": wg_record,
        "trio_summary": moderator_record,
    }


async def run_single_persona(
    persona_name: str,
    target_type: str,
    target_id: Optional[int],
    user_prompt: str,
    additional_context: Optional[str] = None,
    mode: str = "structured",
) -> dict:
    """Run a single persona analysis.

    Args:
        persona_name: "visser", "meldrum", or "wissner_gross".
        target_type: "ist_screen", "hfrt_project", or "standalone".
        target_id: ID of the target (None for standalone).
        user_prompt: The investment thesis or question.
        additional_context: Optional extra context.
        mode: "structured" or "freeform".

    Returns:
        Dict matching PersonaAnalysisResponse schema.

    Raises:
        ValueError: If persona_name is not recognized.
    """
    context = additional_context or ""

    if target_type == "ist_screen" and target_id:
        context = await _load_ist_context(target_id, context)
    elif target_type == "hfrt_project" and target_id:
        context = await _load_hfrt_context(target_id, context)

    analyzers = {
        "visser": analyze_visser,
        "meldrum": analyze_meldrum,
        "wissner_gross": analyze_wissner_gross,
    }

    analyzer = analyzers.get(persona_name)
    if not analyzer:
        raise ValueError(f"Unknown persona: {persona_name}")

    result = await analyzer(context, user_prompt, mode=mode)
    record = await _store_analysis(
        persona_name, target_type, target_id, context, result, user_prompt
    )
    return record


# ── Helper functions ─────────────────────────────────────────────────────────


async def _store_analysis(
    persona_name: str,
    target_type: str,
    target_id: Optional[int],
    context: str,
    result: dict,
    user_prompt: str,
) -> dict:
    """Create a PersonaAnalysis record in DB and return a dict matching PersonaAnalysisResponse."""
    db = SessionLocal()
    try:
        input_context_data = {
            "user_prompt": user_prompt,
            "context_length": len(context),
            "context_preview": context[:500] if context else "",
        }

        raw_narrative = result.get("raw_narrative", "")
        structured_result = {k: v for k, v in result.items() if k != "raw_narrative"}

        record = PersonaAnalysis(
            persona_name=persona_name,
            target_type=target_type,
            target_id=target_id,
            input_context=json.dumps(input_context_data),
            analysis_result=json.dumps(structured_result),
            raw_response=raw_narrative,
            model_used=settings.claude_model,
            tokens_used=None,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return {
            "id": record.id,
            "personaName": record.persona_name,
            "targetType": record.target_type,
            "targetId": record.target_id,
            "analysisResult": structured_result,
            "rawResponse": raw_narrative,
            "modelUsed": record.model_used,
            "tokensUsed": record.tokens_used,
            "createdAt": record.created_at.isoformat() if record.created_at else None,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def _load_ist_context(screen_id: int, existing_context: str) -> str:
    """Load comprehensive IST screen data from DB using tiered strategy.

    Tier 1 (always, full): screen fields, claims, bottlenecks, equity candidates, validations
    Tier 2 (always, full): demand models, effects chains, dialectic reviews, master screen
    Tier 3 (truncated JSON): rotation strategy, catalyst calendar, stress test
    Tier 4 (summary): report title + metadata + content preview
    """
    db = SessionLocal()
    try:
        screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
        if not screen:
            logger.warning("IST screen %d not found for persona context", screen_id)
            return existing_context

        parts = [f'<ist_screen id="{screen_id}">']

        # ── Screen-level fields ──
        parts.append(f"<screen_name>{screen.name}</screen_name>")
        parts.append(f"<status>{screen.status}</status>")
        parts.append(f"<content_type>{screen.content_type}</content_type>")

        if screen.screening_brief:
            parts.append(f"<screening_brief>{_truncate_json_field(screen.screening_brief, 5000)}</screening_brief>")

        if screen.content_extraction:
            parts.append(f"<content_extraction>{_truncate_json_field(screen.content_extraction, 5000)}</content_extraction>")

        if screen.source_bias:
            parts.append(f"<source_bias>{screen.source_bias}</source_bias>")

        # ── Tier 1: Claims ──
        if screen.claims:
            claim_lines = []
            for c in screen.claims:
                line = (
                    f'  <claim id="{c.id}" confidence="{c.confidence}"'
                    f' validated="{c.validation_verdict or "pending"}">'
                    f"\n    <text>{c.claim_text}</text>"
                    f"\n    <citation>{c.source_citation}</citation>"
                )
                if c.quantitative_anchor:
                    line += f"\n    <quant_anchor>{c.quantitative_anchor}</quant_anchor>"
                if c.temporal_marker:
                    line += f"\n    <temporal>{c.temporal_marker}</temporal>"
                if c.bottleneck_name:
                    line += f"\n    <bottleneck>{c.bottleneck_name}</bottleneck>"
                line += "\n  </claim>"
                claim_lines.append(line)
            parts.append(f"<claims count=\"{len(screen.claims)}\">\n" + "\n".join(claim_lines) + "\n</claims>")

        # ── Tier 1: Bottlenecks ──
        if screen.bottlenecks:
            bn_lines = []
            for b in screen.bottlenecks:
                line = (
                    f'  <bottleneck id="{b.id}" phase="{b.phase}" phase_label="{b.phase_label}">'
                    f"\n    <name>{b.name}</name>"
                    f"\n    <description>{b.description}</description>"
                )
                if b.quantitative_evidence:
                    line += f"\n    <quant_evidence>{b.quantitative_evidence}</quant_evidence>"
                if b.temporal_marker:
                    line += f"\n    <temporal>{b.temporal_marker}</temporal>"
                if b.resolution_trigger:
                    line += f"\n    <resolution_trigger>{b.resolution_trigger}</resolution_trigger>"
                line += "\n  </bottleneck>"
                bn_lines.append(line)
            parts.append(f"<bottlenecks count=\"{len(screen.bottlenecks)}\">\n" + "\n".join(bn_lines) + "\n</bottlenecks>")

        # ── Tier 1: Equity Candidates (expanded) ──
        if screen.equity_candidates:
            eq_lines = []
            for e in screen.equity_candidates:
                line = (
                    f'  <equity ticker="{e.ticker}" tier="{e.tier}" conviction="{e.conviction or "N/A"}">'
                    f"\n    <company>{e.company_name}</company>"
                )
                if e.scarcity_score:
                    line += f"\n    <scarcity_score>{_truncate_json_field(e.scarcity_score, 500)}</scarcity_score>"
                if e.moat_type:
                    line += f"\n    <moat type=\"{e.moat_type}\">{e.moat_evidence or ''}</moat>"
                if e.catalyst:
                    line += f"\n    <catalyst>{e.catalyst}</catalyst>"
                if e.tier_rationale:
                    line += f"\n    <tier_rationale>{e.tier_rationale}</tier_rationale>"
                if e.phase is not None:
                    line += f"\n    <phase>{e.phase}</phase>"
                if e.market_cap:
                    line += f"\n    <market_cap>{e.market_cap}</market_cap>"
                if e.pe_ratio:
                    line += f"\n    <pe_ratio>{e.pe_ratio}</pe_ratio>"
                if e.price_at_screen:
                    line += f"\n    <price_at_screen>{e.price_at_screen}</price_at_screen>"
                line += "\n  </equity>"
                eq_lines.append(line)
            parts.append(f"<equity_candidates count=\"{len(screen.equity_candidates)}\">\n" + "\n".join(eq_lines) + "\n</equity_candidates>")

        # ── Tier 1: Validations ──
        if screen.validations:
            val_lines = []
            for v in screen.validations:
                val_lines.append(
                    f'  <validation claim_id="{v.claim_id}" verdict="{v.verdict}" confidence="{v.confidence}">'
                    f"\n    <evidence>{v.evidence}</evidence>"
                    f"\n  </validation>"
                )
            parts.append(f"<validations count=\"{len(screen.validations)}\">\n" + "\n".join(val_lines) + "\n</validations>")

        # ── Tier 2: Demand Models ──
        if screen.demand_models:
            dm_lines = []
            for d in screen.demand_models:
                dm_lines.append(
                    f'  <demand_model bottleneck_id="{d.bottleneck_id}">'
                    f"\n    <formula>{d.formula}</formula>"
                    f"\n    <base_case>{d.base_case}</base_case>"
                    f"\n    <bull_case>{d.bull_case}</bull_case>"
                    f"\n    <bear_case>{d.bear_case}</bear_case>"
                    f"\n  </demand_model>"
                )
            parts.append(f"<demand_models count=\"{len(screen.demand_models)}\">\n" + "\n".join(dm_lines) + "\n</demand_models>")

        # ── Tier 2: Effects Chains ──
        if screen.effects_chains:
            ec_lines = []
            for ec in screen.effects_chains:
                ec_lines.append(
                    f'  <effect order="{ec.effect_order}" equity_id="{ec.equity_candidate_id}">'
                    f"\n    <thesis>{ec.thesis}</thesis>"
                    f"\n    <description>{ec.effect_description}</description>"
                    f"\n  </effect>"
                )
            parts.append(f"<effects_chains count=\"{len(screen.effects_chains)}\">\n" + "\n".join(ec_lines) + "\n</effects_chains>")

        # ── Tier 2: Dialectic Reviews ──
        if screen.dialectic_reviews:
            dr_lines = []
            for dr in screen.dialectic_reviews:
                content_preview = _truncate_json_field(dr.content, 3000)
                dr_lines.append(
                    f'  <dialectic side="{dr.side}">'
                    f"\n    {content_preview}"
                    f"\n  </dialectic>"
                )
            parts.append("<dialectic_reviews>\n" + "\n".join(dr_lines) + "\n</dialectic_reviews>")

        # ── Tier 2: Master Screen ──
        if screen.master_screen:
            ms = screen.master_screen
            parts.append(
                f"<master_screen total_equities=\"{ms.total_equities}\" tier1_count=\"{ms.tier1_count}\">"
                f"\n  <ranked_equities>{_truncate_json_field(ms.ranked_equities, 3000)}</ranked_equities>"
                f"\n  <invariant_compliance>{_truncate_json_field(ms.invariant_compliance, 2000)}</invariant_compliance>"
                f"\n</master_screen>"
            )

        # ── Tier 3: Rotation Strategy (truncated) ──
        if screen.rotation_strategy:
            rs = screen.rotation_strategy
            parts.append(
                "<rotation_strategy>"
                f"\n  <phase_allocations>{_truncate_json_field(rs.phase_allocations, JSON_FIELD_TRUNCATE)}</phase_allocations>"
                f"\n  <rotation_triggers>{_truncate_json_field(rs.rotation_triggers, JSON_FIELD_TRUNCATE)}</rotation_triggers>"
                f"\n  <risk_limits>{_truncate_json_field(rs.risk_limits, JSON_FIELD_TRUNCATE)}</risk_limits>"
                f"\n</rotation_strategy>"
            )

        # ── Tier 3: Catalyst Calendar (truncated) ──
        if screen.catalyst_calendar:
            cc = screen.catalyst_calendar
            parts.append(
                f"<catalyst_calendar total=\"{cc.total_catalysts}\" next=\"{cc.next_catalyst_date or 'N/A'}\">"
                f"\n  <catalysts>{_truncate_json_field(cc.catalysts, 3000)}</catalysts>"
                f"\n</catalyst_calendar>"
            )

        # ── Tier 3: Stress Test (truncated) ──
        if screen.stress_test:
            st = screen.stress_test
            parts.append(
                "<stress_test>"
                f"\n  <framework_tests>{_truncate_json_field(st.framework_tests, JSON_FIELD_TRUNCATE)}</framework_tests>"
                f"\n  <name_tests>{_truncate_json_field(st.name_tests, JSON_FIELD_TRUNCATE)}</name_tests>"
                f"\n  <survival_scores>{_truncate_json_field(st.survival_scores, JSON_FIELD_TRUNCATE)}</survival_scores>"
                f"\n</stress_test>"
            )

        # ── Tier 4: Report (summary only) ──
        if screen.report:
            rpt = screen.report
            parts.append(
                f"<report title=\"{rpt.title}\">"
                f"\n  <metadata>{rpt.report_metadata}</metadata>"
                f"\n  <content_preview>{_truncate_json_field(rpt.content, 4000)}</content_preview>"
                f"\n</report>"
            )

        parts.append("</ist_screen>")

        ist_context = "\n".join(parts)

        # Enforce budget cap
        if len(ist_context) > IST_CONTEXT_BUDGET:
            logger.warning(
                "IST context for screen %d exceeded budget (%d > %d), truncating",
                screen_id, len(ist_context), IST_CONTEXT_BUDGET,
            )
            ist_context = ist_context[:IST_CONTEXT_BUDGET] + "\n</ist_screen>"

        if existing_context:
            return f"{ist_context}\n\n{existing_context}"
        return ist_context

    finally:
        db.close()


async def _load_hfrt_context(project_id: int, existing_context: str) -> str:
    """Load comprehensive HFRT project data from DB.

    Loads all populated templates (not just 0 and 11), dialectic reviews,
    and additional project fields. Budget: 60K chars.
    """
    db = SessionLocal()
    try:
        project = (
            db.query(HFRTProject).filter(HFRTProject.id == project_id).first()
        )
        if not project:
            logger.warning("HFRT project %d not found for persona context", project_id)
            return existing_context

        parts = [f'<hfrt_project id="{project_id}">']

        # ── Project-level fields ──
        parts.append(f"<ticker>{project.ticker}</ticker>")
        if project.company_name:
            parts.append(f"<company_name>{project.company_name}</company_name>")
        parts.append(f"<status>{project.status}</status>")
        if project.sector:
            parts.append(f"<sector>{project.sector}</sector>")
        if project.exchange:
            parts.append(f"<exchange>{project.exchange}</exchange>")
        if project.market_cap:
            parts.append(f"<market_cap>{project.market_cap}</market_cap>")
        if project.investable_verdict:
            parts.append(f"<investable_verdict>{project.investable_verdict}</investable_verdict>")
        if project.conviction_score:
            parts.append(f"<conviction_score>{project.conviction_score}</conviction_score>")
        if project.position_tier:
            parts.append(f"<position_tier>{project.position_tier}</position_tier>")
        if project.recommendation:
            parts.append(f"<recommendation>{project.recommendation}</recommendation>")
        if project.source:
            parts.append(f"<source>{project.source}</source>")
        if project.invariant_results:
            parts.append(f"<invariant_results>{_truncate_json_field(project.invariant_results, JSON_FIELD_TRUNCATE)}</invariant_results>")

        # ── ALL populated templates (truncated per template) ──
        populated_templates = (
            db.query(HFRTTemplate)
            .filter(
                HFRTTemplate.project_id == project_id,
                HFRTTemplate.status == "POPULATED",
            )
            .order_by(HFRTTemplate.template_number)
            .all()
        )
        if populated_templates:
            tmpl_lines = []
            for tmpl in populated_templates:
                if tmpl.data:
                    truncated_data = _truncate_json_field(tmpl.data, TEMPLATE_TRUNCATE)
                    tmpl_lines.append(
                        f'  <template name="{tmpl.template_name}" number="{tmpl.template_number}">'
                        f"\n    {truncated_data}"
                        f"\n  </template>"
                    )
            if tmpl_lines:
                parts.append(f"<templates count=\"{len(tmpl_lines)}\">\n" + "\n".join(tmpl_lines) + "\n</templates>")

        # ── Dialectic Reviews ──
        if project.dialectic_reviews:
            dr_lines = []
            for dr in project.dialectic_reviews:
                content_preview = _truncate_json_field(dr.content, TEMPLATE_TRUNCATE)
                dr_lines.append(
                    f'  <dialectic side="{dr.side}">'
                    f"\n    {content_preview}"
                    f"\n  </dialectic>"
                )
            parts.append("<dialectic_reviews>\n" + "\n".join(dr_lines) + "\n</dialectic_reviews>")

        parts.append("</hfrt_project>")

        hfrt_context = "\n".join(parts)

        # Enforce budget cap
        if len(hfrt_context) > HFRT_CONTEXT_BUDGET:
            logger.warning(
                "HFRT context for project %d exceeded budget (%d > %d), truncating",
                project_id, len(hfrt_context), HFRT_CONTEXT_BUDGET,
            )
            hfrt_context = hfrt_context[:HFRT_CONTEXT_BUDGET] + "\n</hfrt_project>"

        if existing_context:
            return f"{hfrt_context}\n\n{existing_context}"
        return hfrt_context

    finally:
        db.close()


async def _generate_moderator_synthesis(
    visser_result: dict,
    meldrum_result: dict,
    wg_result: dict,
    user_prompt: str,
) -> dict:
    """Call Claude with MODERATOR_SYSTEM_PROMPT to synthesize all three independent analyses.

    The moderator compares and contrasts the three views, identifying agreements,
    disagreements, and drawing a conclusion that directly answers the user's question.

    Args:
        visser_result: Visser's analysis result dict.
        meldrum_result: Meldrum's analysis result dict.
        wg_result: Wissner-Gross's analysis result dict.
        user_prompt: The original user question.

    Returns:
        Dict with moderator synthesis and raw narrative.
    """
    user_message = (
        "<original_question>\n"
        f"{user_prompt}\n"
        "</original_question>\n\n"
        '<independent_analysis analyst="Jordi Visser" role="Macro Regime Analyst">\n'
        f"{visser_result.get('raw_narrative', '')}\n"
        "</independent_analysis>\n\n"
        '<independent_analysis analyst="Mark Meldrum" role="Fundamental Analyst">\n'
        f"{meldrum_result.get('raw_narrative', '')}\n"
        "</independent_analysis>\n\n"
        '<independent_analysis analyst="Alex Wissner-Gross" role="Physics/AI Overlay Analyst">\n'
        f"{wg_result.get('raw_narrative', '')}\n"
        "</independent_analysis>\n\n"
        "These three analysts answered the question independently with no knowledge of "
        "each other's work. Synthesize their views by comparing and contrasting their "
        "perspectives, then draw your own conclusion to answer the original question."
    )

    raw = await call_claude_raw(
        system_prompt=MODERATOR_SYSTEM_PROMPT,
        user_prompt=user_message,
    )

    return {
        "consensus_areas": None,
        "disagreements": None,
        "composite_conviction_score": None,
        "action_recommendation": None,
        "unified_kill_conditions": [],
        "key_insight": None,
        "raw_narrative": raw,
    }
