"""HFRT Phase 2: Industry Analysis — sector-routed industry analysis (Gap B2).

Registered step: industry_analysis (Template 04)

Uses sector_prompts registry (Decision 15) for sector-specific system prompts.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models.hfrt import HFRTProject, HFRTTemplate
from app.services.claude_client import call_claude, get_step_model_tier
from app.services.hfrt.sector_prompts import get_sector_config
from app.services.perplexity_client import is_available as perplexity_available, search_and_analyze
from app.services.workflow_engine import register_step, emit_sse_event

logger = logging.getLogger(__name__)


# ── Pydantic models ──────────────────────────────────────────────────────────


class IndustryAnalysisResult(BaseModel):
    industry: str
    sector: str
    market_size: Optional[str] = None
    tam_sam_som: dict[str, Any] = Field(default_factory=dict)
    growth_rate: Optional[str] = None
    industry_lifecycle_stage: str = ""
    key_trends: list[str] = Field(default_factory=list)
    regulatory_environment: str = ""
    sector_specific_kpis: dict[str, Any] = Field(default_factory=dict)
    key_players: list[dict[str, Any]] = Field(default_factory=list)
    barriers_to_entry: list[str] = Field(default_factory=list)
    disruption_risks: list[str] = Field(default_factory=list)
    cyclicality: str = ""
    recent_m_and_a: list[str] = Field(default_factory=list)


# ── Helper ───────────────────────────────────────────────────────────────────

def _get_template_data(db, project_id: int, template_number: int) -> dict | None:
    template = (
        db.query(HFRTTemplate)
        .filter(
            HFRTTemplate.project_id == project_id,
            HFRTTemplate.template_number == template_number,
        )
        .first()
    )
    if template and template.data:
        try:
            return json.loads(template.data)
        except (ValueError, TypeError):
            return None
    return None


# ── Step handler ─────────────────────────────────────────────────────────────


@register_step("HFRT", "industry_analysis")
async def handle_industry_analysis(workflow_run_id: int) -> dict | None:
    """Generate Template 04: Industry Analysis."""
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
            "stepName": "industry_analysis", "message": "Analyzing industry...", "percent": 10,
        })

        overview = _get_template_data(db, project.id, 1)
        biz_model = _get_template_data(db, project.id, 2)
        competitive = _get_template_data(db, project.id, 3)

        # Sector-routed prompt (Gap B2, Decision 15)
        sector_config = get_sector_config(project.sector)

        # Optionally enrich with current industry trends from Perplexity
        industry_trends_block = ""
        if perplexity_available():
            try:
                pplx = await search_and_analyze(
                    system_prompt=(
                        "You are an industry analyst. Provide current industry trends, "
                        "recent regulatory changes, market size updates, and key "
                        "developments in the given sector."
                    ),
                    user_prompt=(
                        f"Current trends, regulatory changes, and market developments "
                        f"in the {project.sector or 'Unknown'} sector relevant to "
                        f"{project.ticker} ({project.company_name})"
                    ),
                    model="sonar",
                    max_tokens=4096,
                    workflow_run_id=workflow_run_id,
                )
                industry_trends_block = (
                    f"<current_industry_data>\n{pplx.content}\n</current_industry_data>\n\n"
                )
                logger.info("Perplexity industry enrichment: %d citations", len(pplx.citations))
            except Exception:
                logger.warning("Perplexity industry enrichment failed, continuing without", exc_info=True)

        user_prompt = (
            f"{industry_trends_block}"
            f"<company_overview>\n{json.dumps(overview, indent=2, default=str)[:5000]}\n</company_overview>\n\n"
            f"<business_model>\n{json.dumps(biz_model, indent=2, default=str)[:4000]}\n</business_model>\n\n"
            f"<competitive_position>\n{json.dumps(competitive, indent=2, default=str)[:4000]}\n</competitive_position>\n\n"
            f"<metadata>\n"
            f"Ticker: {project.ticker}\n"
            f"Company: {project.company_name}\n"
            f"Sector: {project.sector or 'Unknown'}\n"
            f"Sector KPIs to analyze: {', '.join(sector_config.kpis)}\n"
            f"</metadata>\n\n"
            f"Perform a comprehensive industry analysis for {project.ticker} in the {project.sector or 'Unknown'} sector.\n"
            f"Return JSON matching this schema: {IndustryAnalysisResult.model_json_schema()}"
        )

        model = await get_step_model_tier(workflow_run_id, "industry_analysis")
        result = await call_claude(
            system_prompt=sector_config.system_prompt,
            user_prompt=user_prompt,
            response_model=IndustryAnalysisResult,
            model=model,
        )

        template = (
            db.query(HFRTTemplate)
            .filter(
                HFRTTemplate.project_id == project.id,
                HFRTTemplate.template_number == 4,
            )
            .first()
        )
        if template:
            template.data = json.dumps(result.model_dump(), default=str)
            template.status = "POPULATED"
            template.updated_at = datetime.now(timezone.utc)

        db.commit()
        return {"template": 4, "status": "POPULATED"}
    finally:
        db.close()
