"""Pydantic schemas for Persona Overlay endpoints.

All response schemas use camelCase aliases via alias_generator for frontend consumption.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


# ── Request schemas ──────────────────────────────────────────────────────────


class PersonaAnalysisRequest(BaseModel):
    """Request body for running a single persona analysis."""

    persona_name: str = Field(
        ...,
        alias="personaName",
        description="Persona to run: visser, meldrum, or wissner_gross",
    )
    target_type: str = Field(
        ...,
        alias="targetType",
        description="Target type: ist_screen, hfrt_project, or standalone",
    )
    target_id: Optional[int] = Field(
        default=None,
        alias="targetId",
        description="ID of the IST screen or HFRT project (null for standalone)",
    )
    user_prompt: str = Field(
        ...,
        alias="userPrompt",
        min_length=10,
        max_length=10000,
        description="The question or thesis to analyze",
    )
    additional_context: Optional[str] = Field(
        default=None,
        alias="additionalContext",
        max_length=100000,
        description="Optional additional context data",
    )
    mode: str = Field(
        default="structured",
        description="Analysis mode: structured (forced output sections) or freeform (open-ended)",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("persona_name")
    @classmethod
    def validate_persona_name(cls, v: str) -> str:
        allowed = ("visser", "meldrum", "wissner_gross")
        if v not in allowed:
            raise ValueError(f"persona_name must be one of {allowed}")
        return v

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, v: str) -> str:
        allowed = ("ist_screen", "hfrt_project", "standalone")
        if v not in allowed:
            raise ValueError(f"target_type must be one of {allowed}")
        return v

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = ("structured", "freeform")
        if v not in allowed:
            raise ValueError(f"mode must be one of {allowed}")
        return v


class TrioAnalysisRequest(BaseModel):
    """Request body for running the full trio pipeline."""

    target_type: str = Field(
        ...,
        alias="targetType",
        description="Target type: ist_screen, hfrt_project, or standalone",
    )
    target_id: Optional[int] = Field(
        default=None,
        alias="targetId",
        description="ID of the IST screen or HFRT project (null for standalone)",
    )
    user_prompt: str = Field(
        ...,
        alias="userPrompt",
        min_length=10,
        max_length=10000,
        description="The question or thesis to analyze",
    )
    additional_context: Optional[str] = Field(
        default=None,
        alias="additionalContext",
        max_length=100000,
        description="Optional additional context data",
    )
    mode: str = Field(
        default="structured",
        description="Analysis mode: structured (forced output sections) or freeform (open-ended)",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, v: str) -> str:
        allowed = ("ist_screen", "hfrt_project", "standalone")
        if v not in allowed:
            raise ValueError(f"target_type must be one of {allowed}")
        return v

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = ("structured", "freeform")
        if v not in allowed:
            raise ValueError(f"mode must be one of {allowed}")
        return v


# ── Response schemas ─────────────────────────────────────────────────────────


class PersonaAnalysisResponse(BaseModel):
    """Response schema for a single persona analysis result."""

    id: int
    persona_name: str = Field(alias="personaName")
    target_type: str = Field(alias="targetType")
    target_id: Optional[int] = Field(default=None, alias="targetId")
    analysis_result: Optional[dict[str, Any]] = Field(
        default=None, alias="analysisResult"
    )
    raw_response: Optional[str] = Field(default=None, alias="rawResponse")
    model_used: Optional[str] = Field(default=None, alias="modelUsed")
    tokens_used: Optional[int] = Field(default=None, alias="tokensUsed")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TrioSummaryResponse(BaseModel):
    """Response schema for the full trio analysis pipeline."""

    visser: PersonaAnalysisResponse
    meldrum: PersonaAnalysisResponse
    wissner_gross: PersonaAnalysisResponse = Field(alias="wissnerGross")
    trio_summary: PersonaAnalysisResponse = Field(alias="trioSummary")

    model_config = ConfigDict(populate_by_name=True)


class PersonaAnalysisListResponse(BaseModel):
    """Paginated list of persona analyses."""

    analyses: list[PersonaAnalysisResponse]
    total: int
