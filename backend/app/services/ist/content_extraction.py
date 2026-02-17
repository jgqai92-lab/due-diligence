"""IST Phase 1: Content Extraction -- parses unstructured text into structured claims.

Provides two registered workflow steps:
  - content_extraction: Extract discrete, verifiable claims from source content
  - source_bias_assessment: Assess source bias and credibility

Invariants enforced:
  - INV-AI-01: Content/instruction separation (user data in XML tags)
  - INV-AI-03: Pydantic-validated Claude outputs
  - INV-AI-04: Anti-hallucination instruction in system prompts
  - INV-BE-05: Background tasks own their DB sessions
  - INV-BE-06: JSON stored via Pydantic serialization
  - INV-AC-03: Per-step session lifecycle (open -> write -> commit -> close)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models.ist import ISTScreen, ISTClaim
from app.schemas.ist import ContentExtractionSummary, SourceBiasSummary
from app.services.ist.claude_client import call_claude
from app.services.workflow_engine import register_step, emit_sse_event

logger = logging.getLogger(__name__)


# ── Pydantic models for Claude structured output (INV-AI-03) ────────────────


class ExtractedClaim(BaseModel):
    """A single claim extracted from source content."""

    claim_text: str = Field(description="The discrete, verifiable claim")
    source_citation: str = Field(
        description="Where in the source this came from"
    )
    quantitative_anchor: Optional[str] = Field(
        default=None, description="Numeric data point"
    )
    temporal_marker: Optional[str] = Field(
        default=None, description="Time reference"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Extraction confidence 0-1"
    )


class ContentExtractionResult(BaseModel):
    """Structured output from the content extraction Claude call."""

    claims: list[ExtractedClaim]
    summary: str = Field(description="Brief summary of the content")
    content_themes: list[str] = Field(description="Major themes identified")


class SourceBiasResult(BaseModel):
    """Structured output from the source bias assessment Claude call."""

    rating: str = Field(description="Overall bias rating: low, moderate, high")
    notes: str = Field(description="Bias assessment narrative")
    source_credibility: str = Field(
        description="Source credibility assessment"
    )
    potential_blind_spots: list[str] = Field(
        description="Areas the source may underweight"
    )


# ── System prompts (INV-AI-04: anti-hallucination instructions) ─────────────

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


# ── Registered workflow step handlers ───────────────────────────────────────


@register_step("IST", "content_extraction")
async def handle_content_extraction(workflow_run_id: int) -> dict | None:
    """Extract claims from raw content and store them in the database.

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

        # Build user prompt with content/instruction separation (INV-AI-01)
        brief_data = {}
        if screen.screening_brief:
            import json

            try:
                brief_data = json.loads(screen.screening_brief)
            except (ValueError, TypeError):
                pass

        user_prompt = (
            f"<source_content>\n{screen.raw_content}\n</source_content>\n\n"
            f"<metadata>\n"
            f"Content type: {screen.content_type}\n"
            f"Hypothesis: {brief_data.get('hypothesis', 'Not specified')}\n"
            f"</metadata>\n\n"
            f"Extract all investment-relevant claims from the content above.\n"
            f"Return JSON matching this schema: "
            f"{ContentExtractionResult.model_json_schema()}"
        )

        # Call Claude for extraction (INV-AI-03: validated via Pydantic)
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

        # Store claims in database (INV-BE-01: ORM writes only)
        for claim_data in result.claims:
            claim = ISTClaim(
                screen_id=screen.id,
                claim_text=claim_data.claim_text,
                source_citation=claim_data.source_citation,
                quantitative_anchor=claim_data.quantitative_anchor,
                temporal_marker=claim_data.temporal_marker,
                confidence=claim_data.confidence,
            )
            db.add(claim)

        # Update screen content_extraction summary (INV-BE-06: Pydantic-validated JSON)
        extraction_summary = ContentExtractionSummary(
            totalClaims=len(result.claims),
            claimsWithQuantAnchors=sum(
                1 for c in result.claims if c.quantitative_anchor
            ),
            claimsWithTemporalMarkers=sum(
                1 for c in result.claims if c.temporal_marker
            ),
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
    finally:
        db.close()


@register_step("IST", "source_bias_assessment")
async def handle_source_bias(workflow_run_id: int) -> dict | None:
    """Assess source bias and credibility.

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

        # Truncate content for bias assessment (first 5000 chars is enough)
        content_sample = screen.raw_content[:5000]

        # INV-AI-01: User data in XML tags, instructions in system prompt
        user_prompt = (
            f"<source_content>\n{content_sample}\n</source_content>\n\n"
            f"<metadata>\n"
            f"Content type: {screen.content_type}\n"
            f"Full content length: {len(screen.raw_content)} characters\n"
            f"</metadata>\n\n"
            f"Assess the source bias and credibility of this content.\n"
            f"Return JSON matching this schema: "
            f"{SourceBiasResult.model_json_schema()}"
        )

        # INV-AI-03: Pydantic-validated structured output
        result = await call_claude(
            system_prompt=SOURCE_BIAS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=SourceBiasResult,
        )

        # INV-BE-06: Write JSON via Pydantic serialization
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
    finally:
        db.close()
