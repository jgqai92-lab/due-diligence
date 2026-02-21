"""IST Phase 1: Content extraction and source bias assessment."""

import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.ist import ISTClaim, ISTScreen
from app.schemas.ist import ContentExtractionSummary, SourceBiasSummary
from app.services.ist.claude_client import call_claude
from app.services.workflow_engine import emit_sse_event, register_step

logger = logging.getLogger(__name__)


class ExtractedClaim(BaseModel):
    """A single extracted claim."""

    claim_text: str = Field(description="The discrete, verifiable claim")
    source_citation: str = Field(description="Where in the source this came from")
    quantitative_anchor: Optional[str] = Field(default=None)
    temporal_marker: Optional[str] = Field(default=None)
    confidence: float = Field(ge=0.0, le=1.0)


class ContentExtractionResult(BaseModel):
    """Structured extraction output."""

    claims: list[ExtractedClaim]
    summary: str
    content_themes: list[str]


class SourceBiasResult(BaseModel):
    """Structured source-bias output."""

    rating: str
    notes: str
    source_credibility: str
    potential_blind_spots: list[str]


EXTRACTION_SYSTEM_PROMPT = """You are an investment research analyst extracting structured claims from unstructured content.

Your task:
1. Read the provided content carefully
2. Extract every discrete, verifiable claim that could be investment-relevant
3. For each claim, identify:
   - The exact claim text (concise, one sentence)
   - Source citation (where in the content this appears)
   - Any quantitative anchor (numbers, percentages, dollar amounts)
   - Any temporal marker (dates, time ranges, deadlines)
   - Your confidence in the extraction accuracy (0.0-1.0)
4. Provide a brief summary and key themes

NEVER fabricate data, statistics, or financial figures. Only cite information from the provided content. If a claim lacks a quantitative anchor or temporal marker, leave those fields as null rather than inventing them.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""

SOURCE_BIAS_SYSTEM_PROMPT = """You are an investment research analyst assessing source bias and credibility.

Analyze the provided content and its source metadata to assess:
1. Overall bias rating (low/moderate/high)
2. Notes explaining the bias assessment
3. Source credibility assessment
4. Potential blind spots -- what the source might underweight or miss

NEVER fabricate claims about the source. Base your assessment only on the content provided and the stated content type. If you cannot determine credibility, say so explicitly.

Return ONLY valid JSON matching the schema provided."""


async def _run_content_extraction(
    screen: ISTScreen,
    db: Session,
    workflow_run_id: int,
    *,
    raw_content: Optional[str] = None,
    claim_source_refresh_id: Optional[int] = None,
    update_screen_status: bool = True,
    replace_claims: bool = False,
) -> dict | None:
    """Core extraction logic reusable by IST and IST_REFRESH wrappers."""
    if update_screen_status:
        screen.status = "EXTRACTING"
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "content_extraction",
            "message": "Extracting claims from content...",
            "percent": 10,
        },
    )

    brief_data: dict = {}
    if screen.screening_brief:
        import json

        try:
            brief_data = json.loads(screen.screening_brief)
        except (ValueError, TypeError):
            brief_data = {}

    source_content = raw_content if raw_content is not None else screen.raw_content

    user_prompt = (
        f"<source_content>\n{source_content}\n</source_content>\n\n"
        f"<metadata>\n"
        f"Content type: {screen.content_type}\n"
        f"Hypothesis: {brief_data.get('hypothesis', 'Not specified')}\n"
        f"</metadata>\n\n"
        f"Extract all investment-relevant claims from the content above.\n"
        f"Return JSON matching this schema: "
        f"{ContentExtractionResult.model_json_schema()}"
    )

    result = await call_claude(
        system_prompt=EXTRACTION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=ContentExtractionResult,
    )

    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "content_extraction",
            "message": f"Extracted {len(result.claims)} claims, storing...",
            "percent": 70,
        },
    )

    if replace_claims:
        db.query(ISTClaim).filter(ISTClaim.screen_id == screen.id).delete()

    for claim_data in result.claims:
        db.add(
            ISTClaim(
                screen_id=screen.id,
                claim_text=claim_data.claim_text,
                source_citation=claim_data.source_citation,
                quantitative_anchor=claim_data.quantitative_anchor,
                temporal_marker=claim_data.temporal_marker,
                confidence=claim_data.confidence,
                source_refresh_id=claim_source_refresh_id,
            )
        )

    db.flush()
    total_claims = db.query(ISTClaim).filter(ISTClaim.screen_id == screen.id).count()

    extraction_summary = ContentExtractionSummary(
        totalClaims=total_claims,
        claimsWithQuantAnchors=sum(1 for c in result.claims if c.quantitative_anchor),
        claimsWithTemporalMarkers=sum(1 for c in result.claims if c.temporal_marker),
        summary=result.summary,
        themes=result.content_themes,
    )

    screen.content_extraction = extraction_summary.model_dump_json()
    screen.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "claimsExtracted": len(result.claims),
        "themes": result.content_themes,
    }


async def _run_source_bias(
    screen: ISTScreen,
    db: Session,
    workflow_run_id: int,
    *,
    raw_content: Optional[str] = None,
) -> dict | None:
    """Core source-bias logic reusable by IST and IST_REFRESH wrappers."""
    source_content = raw_content if raw_content is not None else screen.raw_content
    content_sample = source_content[:5000]

    user_prompt = (
        f"<source_content>\n{content_sample}\n</source_content>\n\n"
        f"<metadata>\n"
        f"Content type: {screen.content_type}\n"
        f"Full content length: {len(source_content)} characters\n"
        f"</metadata>\n\n"
        f"Assess the source bias and credibility of this content.\n"
        f"Return JSON matching this schema: "
        f"{SourceBiasResult.model_json_schema()}"
    )

    result = await call_claude(
        system_prompt=SOURCE_BIAS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=SourceBiasResult,
    )

    bias_summary = SourceBiasSummary(
        rating=result.rating,
        notes=result.notes,
        sourceCredibility=result.source_credibility,
        potentialBlindSpots=result.potential_blind_spots,
    )
    screen.source_bias = bias_summary.model_dump_json()
    screen.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"biasRating": result.rating}


@register_step("IST", "content_extraction")
async def handle_content_extraction(workflow_run_id: int) -> dict | None:
    """Extract claims from raw content and store them."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        return await _run_content_extraction(screen, db, workflow_run_id)
    finally:
        db.close()


@register_step("IST", "source_bias_assessment")
async def handle_source_bias(workflow_run_id: int) -> dict | None:
    """Assess source bias and credibility."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        return await _run_source_bias(screen, db, workflow_run_id)
    finally:
        db.close()
