"""HFRT Phase 4: Dialectic — isolated bull/bear case generation (Gap B6 audit).

Registered steps:
  - bull_case — generates bull case from Templates 00-09 (no access to bear)
  - bear_case — generates bear case from Templates 00-09 (no access to bull)
    After bear_case completes, runs dialectic isolation audit (Gap B6).

Isolation pattern: Bull receives only research data, Bear receives only research data.
Neither sees the other's output until synthesis in Phase 5.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models.hfrt import HFRTProject, HFRTTemplate, HFRTDialecticReview
from app.services.claude_client import call_claude, get_step_model_tier
from app.services.workflow_engine import register_step, emit_sse_event

logger = logging.getLogger(__name__)


# ── Pydantic models ──────────────────────────────────────────────────────────


class DialecticCaseResult(BaseModel):
    narrative: str = Field(description="Full narrative argument")
    key_arguments: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    conviction_level: str = Field(description="HIGH, MEDIUM, LOW")
    price_target: float | None = Field(default=None, description="Estimated price target")
    time_horizon: str = Field(default="12-18 months")
    key_metrics_to_watch: list[str] = Field(default_factory=list)


# ── System prompts ───────────────────────────────────────────────────────────

BULL_SYSTEM_PROMPT = """You are a bull-case equity analyst. Your job is to build the STRONGEST POSSIBLE investment case for this company.

You must:
1. Identify every upside opportunity the market may be underappreciating
2. Find catalysts that could drive significant price appreciation
3. Assess the strength and durability of competitive advantages
4. Quantify potential upside from revenue growth, margin expansion, multiple re-rating
5. Present a compelling narrative with supporting evidence

IMPORTANT: You are building the BULL case only. Focus on upside potential, positive catalysts, and reasons the market is too pessimistic. Do NOT present a balanced view — that's the synthesizer's job.

ISOLATION REQUIREMENT: You have NOT seen the opposing bear case. Do NOT reference, anticipate, or pre-emptively rebut the other side's arguments. Build your case solely from the research data provided.

Use ONLY data provided in the XML-wrapped context above.
NEVER fabricate catalysts, price targets, or financial projections not supported by the provided data.
Return ONLY valid JSON matching the schema provided."""

BEAR_SYSTEM_PROMPT = """You are a bear-case equity analyst. Your job is to build the STRONGEST POSSIBLE case AGAINST this investment.

You must:
1. Identify every downside risk the market may be underappreciating
2. Find potential negative catalysts and value traps
3. Challenge the assumptions behind bullish narratives
4. Quantify potential downside from competitive threats, margin pressure, multiple compression
5. Present a compelling counter-narrative with supporting evidence

IMPORTANT: You are building the BEAR case only. Focus on downside risks, negative catalysts, and reasons the market is too optimistic. Do NOT present a balanced view — that's the synthesizer's job.

ISOLATION REQUIREMENT: You have NOT seen the opposing bull case. Do NOT reference, anticipate, or pre-emptively rebut the other side's arguments. Build your case solely from the research data provided.

Use ONLY data provided in the XML-wrapped context above.
NEVER fabricate negative catalysts, price targets, or competitive threats not supported by the provided data.
Return ONLY valid JSON matching the schema provided."""


# ── Helper ───────────────────────────────────────────────────────────────────

def _gather_research_context(db, project_id: int) -> str:
    """Gather Templates 00-09 as context for dialectic review (no dialectic data)."""
    context_parts = []
    for num in range(10):
        template = (
            db.query(HFRTTemplate)
            .filter(
                HFRTTemplate.project_id == project_id,
                HFRTTemplate.template_number == num,
            )
            .first()
        )
        if template and template.data:
            try:
                data = json.loads(template.data)
                # Truncate each template to keep within context limits
                data_str = json.dumps(data, indent=2, default=str)[:4000]
                context_parts.append(
                    f"<template_{num:02d} name=\"{template.template_name}\">\n"
                    f"{data_str}\n"
                    f"</template_{num:02d}>"
                )
            except (ValueError, TypeError):
                pass
    return "\n\n".join(context_parts)


# ── Step handlers ────────────────────────────────────────────────────────────


@register_step("HFRT", "bull_case")
async def handle_bull_case(workflow_run_id: int) -> dict | None:
    """Generate bull case review — isolated, no access to bear case."""
    db = SessionLocal()
    try:
        project = (
            db.query(HFRTProject)
            .filter(HFRTProject.workflow_run_id == workflow_run_id)
            .first()
        )
        if not project:
            raise ValueError(f"No HFRT project for workflow {workflow_run_id}")

        project.status = "DIALECTIC"
        project.updated_at = datetime.now(timezone.utc)
        db.commit()

        await emit_sse_event(workflow_run_id, "step_progress", {
            "stepName": "bull_case", "message": "Building bull case...", "percent": 10,
        })

        research_context = _gather_research_context(db, project.id)

        user_prompt = (
            f"<research_data>\n{research_context}\n</research_data>\n\n"
            f"Build the strongest possible BULL case for {project.ticker} ({project.company_name}).\n"
            f"Return JSON matching this schema: {DialecticCaseResult.model_json_schema()}"
        )

        model = await get_step_model_tier(workflow_run_id, "bull_case")
        result = await call_claude(
            system_prompt=BULL_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=DialecticCaseResult,
            model=model,
            max_tokens=12288,
        )

        # Store in dialectic reviews table
        existing = (
            db.query(HFRTDialecticReview)
            .filter(
                HFRTDialecticReview.project_id == project.id,
                HFRTDialecticReview.side == "BULL",
            )
            .first()
        )
        if existing:
            existing.content = json.dumps(result.model_dump(), default=str)
            existing.created_at = datetime.now(timezone.utc)
        else:
            review = HFRTDialecticReview(
                project_id=project.id,
                side="BULL",
                content=json.dumps(result.model_dump(), default=str),
            )
            db.add(review)

        db.commit()

        return {"side": "BULL", "conviction": result.conviction_level}
    finally:
        db.close()


@register_step("HFRT", "bear_case")
async def handle_bear_case(workflow_run_id: int) -> dict | None:
    """Generate bear case review — isolated, no access to bull case."""
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
            "stepName": "bear_case", "message": "Building bear case...", "percent": 10,
        })

        research_context = _gather_research_context(db, project.id)

        user_prompt = (
            f"<research_data>\n{research_context}\n</research_data>\n\n"
            f"Build the strongest possible BEAR case against {project.ticker} ({project.company_name}).\n"
            f"Return JSON matching this schema: {DialecticCaseResult.model_json_schema()}"
        )

        model = await get_step_model_tier(workflow_run_id, "bear_case")
        result = await call_claude(
            system_prompt=BEAR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=DialecticCaseResult,
            model=model,
            max_tokens=12288,
        )

        existing = (
            db.query(HFRTDialecticReview)
            .filter(
                HFRTDialecticReview.project_id == project.id,
                HFRTDialecticReview.side == "BEAR",
            )
            .first()
        )
        bear_content_str = json.dumps(result.model_dump(), default=str)
        if existing:
            existing.content = bear_content_str
            existing.created_at = datetime.now(timezone.utc)
        else:
            review = HFRTDialecticReview(
                project_id=project.id,
                side="BEAR",
                content=bear_content_str,
            )
            db.add(review)

        db.commit()

        # Post-hoc isolation audit (Gap B6): check for cross-contamination
        isolation_result = _run_isolation_audit(db, project.id)
        if isolation_result and not isolation_result["is_isolated"]:
            logger.warning(
                "Dialectic isolation audit FAILED for project %d: %s",
                project.id,
                isolation_result["contamination_evidence"],
            )

        return {
            "side": "BEAR",
            "conviction": result.conviction_level,
            "isolation_audit": isolation_result,
        }
    finally:
        db.close()


def _run_isolation_audit(db, project_id: int) -> dict[str, Any] | None:
    """Run dialectic isolation audit after both sides complete."""
    from app.services.hfrt.invariant_checker import audit_dialectic_isolation

    bull = (
        db.query(HFRTDialecticReview)
        .filter(
            HFRTDialecticReview.project_id == project_id,
            HFRTDialecticReview.side == "BULL",
        )
        .first()
    )
    bear = (
        db.query(HFRTDialecticReview)
        .filter(
            HFRTDialecticReview.project_id == project_id,
            HFRTDialecticReview.side == "BEAR",
        )
        .first()
    )

    if not bull or not bear:
        return None

    return audit_dialectic_isolation(bull.content, bear.content)
