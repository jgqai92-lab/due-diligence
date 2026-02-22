"""Pydantic schemas for IST (Investment Screening Team) endpoints."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Internal JSON-column validation models


class ScreeningBrief(BaseModel):
    """Validated schema for ist_screens.screening_brief JSON column."""

    hypothesis: Optional[str] = None
    content_type: str = "text"
    constraints: Optional[dict[str, Any]] = None
    frameworks: Optional[list[str]] = None


class ContentExtractionSummary(BaseModel):
    """Validated schema for ist_screens.content_extraction JSON column."""

    totalClaims: int = 0
    claimsWithQuantAnchors: int = 0
    claimsWithTemporalMarkers: int = 0
    summary: str = ""
    themes: list[str] = Field(default_factory=list)


class SourceBiasSummary(BaseModel):
    """Validated schema for ist_screens.source_bias JSON column."""

    rating: str
    notes: str
    sourceCredibility: str
    potentialBlindSpots: list[str] = Field(default_factory=list)


# Request schemas


class ISTScreenCreate(BaseModel):
    """Request body for creating a new IST screen."""

    name: str = Field(
        ...,
        max_length=200,
        description="Human-readable name for this screen",
    )
    content: str = Field(
        ...,
        min_length=100,
        max_length=512000,
        description="Full content text to analyze",
    )
    content_type: Optional[str] = Field(
        default="text",
        alias="contentType",
        description="Content type: podcast_transcript, article, earnings_call, research_note, text",
    )
    hypothesis: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional investment hypothesis to test",
    )
    constraints: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional screening constraints",
    )
    frameworks: Optional[list[str]] = Field(
        default=None,
        description="Optional list of framework names to apply",
    )
    auto_advance: bool = Field(
        default=False,
        alias="autoAdvance",
        description="If true, workflow advances between phases automatically",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name must not be empty")
        return stripped

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str | None) -> str:
        if v is None:
            return "text"
        allowed = (
            "podcast_transcript",
            "article",
            "earnings_call",
            "research_note",
            "text",
        )
        if v not in allowed:
            raise ValueError(f"contentType must be one of {allowed}")
        return v


class ISTScreenBriefUpdate(BaseModel):
    """Request body for updating the screening brief at checkpoints."""

    hypothesis: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Updated investment hypothesis",
    )
    constraints: Optional[dict[str, Any]] = Field(
        default=None,
        description="Updated screening constraints",
    )
    frameworks: Optional[list[str]] = Field(
        default=None,
        description="Updated list of framework names",
    )

    model_config = ConfigDict(populate_by_name=True)


class ISTSynthesisCreate(BaseModel):
    """Request body for creating a cross-screen synthesis."""

    name: str = Field(..., max_length=200)
    screen_ids: list[int] = Field(
        ...,
        alias="screenIds",
        min_length=2,
        max_length=10,
    )
    auto_advance: bool = Field(default=False, alias="autoAdvance")
    idempotency_key: Optional[str] = Field(
        default=None,
        alias="idempotencyKey",
        max_length=64,
    )

    model_config = ConfigDict(populate_by_name=True)


class ISTScreenRefreshCreate(BaseModel):
    """Request body for refreshing an existing completed IST screen."""

    content: str = Field(
        ...,
        min_length=100,
        max_length=512000,
        description="New content delta to merge into the existing screen context",
    )
    content_type: Optional[str] = Field(
        default="text",
        alias="contentType",
        description="Content type for the delta input",
    )
    auto_advance: bool = Field(default=False, alias="autoAdvance")
    idempotency_key: Optional[str] = Field(
        default=None,
        alias="idempotencyKey",
        max_length=64,
    )

    model_config = ConfigDict(populate_by_name=True)


# Response schemas


class ISTScreenResponse(BaseModel):
    """Response schema for screen creation."""

    id: int
    workflow_run_id: int = Field(alias="workflowRunId")
    active_workflow_run_id: Optional[int] = Field(default=None, alias="activeWorkflowRunId")
    name: str
    status: str
    content_type: str = Field(alias="contentType")
    hypothesis: Optional[str] = None
    refresh_count: int = Field(default=0, alias="refreshCount")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ISTScreenListItem(BaseModel):
    """Response schema for a single screen in the list view."""

    id: int
    name: str
    status: str
    workflow_run_id: int = Field(alias="workflowRunId")
    active_workflow_run_id: Optional[int] = Field(default=None, alias="activeWorkflowRunId")
    claim_count: int = Field(default=0, alias="claimCount")
    candidate_count: int = Field(default=0, alias="candidateCount")
    tier1_count: int = Field(default=0, alias="tier1Count")
    refresh_count: int = Field(default=0, alias="refreshCount")
    current_phase: int = Field(default=0, alias="currentPhase")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ISTScreenListResponse(BaseModel):
    """Paginated list of IST screens."""

    screens: list[ISTScreenListItem]
    total: int


class ISTScreenDetailResponse(BaseModel):
    """Full screen detail response."""

    id: int
    workflow_run_id: int = Field(alias="workflowRunId")
    active_workflow_run_id: Optional[int] = Field(default=None, alias="activeWorkflowRunId")
    name: str
    status: str
    content_type: str = Field(alias="contentType")
    screening_brief: Optional[dict[str, Any]] = Field(
        default=None, alias="screeningBrief"
    )
    content_extraction: Optional[dict[str, Any]] = Field(
        default=None, alias="contentExtraction"
    )
    source_bias: Optional[dict[str, Any]] = Field(
        default=None, alias="sourceBias"
    )
    refresh_count: int = Field(default=0, alias="refreshCount")
    current_phase: int = Field(default=0, alias="currentPhase")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ISTClaimResponse(BaseModel):
    """Response schema for a single claim."""

    id: int
    claim_text: str = Field(alias="claimText")
    source_citation: str = Field(alias="sourceCitation")
    quantitative_anchor: Optional[str] = Field(
        default=None, alias="quantitativeAnchor"
    )
    temporal_marker: Optional[str] = Field(
        default=None, alias="temporalMarker"
    )
    bottleneck_name: Optional[str] = Field(
        default=None, alias="bottleneckName"
    )
    confidence: Optional[float] = None
    is_validated: bool = Field(default=False, alias="isValidated")
    validation_verdict: Optional[str] = Field(
        default=None, alias="validationVerdict"
    )
    validation_source: Optional[str] = Field(
        default=None, alias="validationSource"
    )
    source_refresh_id: Optional[int] = Field(
        default=None,
        alias="sourceRefreshId",
    )
    source_refresh_number: Optional[int] = Field(
        default=None,
        alias="sourceRefreshNumber",
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ISTClaimsListResponse(BaseModel):
    """Response for the claims list endpoint."""

    screen_id: int = Field(alias="screenId")
    claims: list[ISTClaimResponse]
    total_count: int = Field(alias="totalCount")
    validated_count: int = Field(alias="validatedCount")

    model_config = ConfigDict(populate_by_name=True)


class ScreenRefreshListItem(BaseModel):
    """Response schema for refresh list rows."""

    id: int
    workflow_run_id: int = Field(alias="workflowRunId")
    refresh_number: int = Field(alias="refreshNumber")
    status: str
    content_type: str = Field(alias="contentType")
    delta_claim_count: int = Field(alias="deltaClaimCount")
    new_claims_count: int = Field(default=0, alias="newClaimsCount")
    tier_change_count: int = Field(default=0, alias="tierChangeCount")
    steps_reexecuted: Optional[list[str]] = Field(default=None, alias="stepsReexecuted")
    impact_assessment: Optional[dict[str, Any]] = Field(default=None, alias="impactAssessment")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    is_active: bool = Field(alias="isActive")
    started_at: Optional[str] = Field(default=None, alias="startedAt")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")
    created_at: Optional[str] = Field(default=None, alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class ScreenRefreshDetail(BaseModel):
    """Response schema for refresh detail."""

    id: int
    screen_id: int = Field(alias="screenId")
    workflow_run_id: int = Field(alias="workflowRunId")
    refresh_number: int = Field(alias="refreshNumber")
    status: str
    content_type: str = Field(alias="contentType")
    delta_content: str = Field(alias="deltaContent")
    delta_claim_count: int = Field(alias="deltaClaimCount")
    new_claims_count: int = Field(default=0, alias="newClaimsCount")
    new_claims: list[dict[str, Any]] = Field(default_factory=list, alias="newClaims")
    new_source_bias: Optional[dict[str, Any]] = Field(default=None, alias="newSourceBias")
    tier_changes: list[dict[str, Any]] = Field(default_factory=list, alias="tierChanges")
    tier_change_count: int = Field(default=0, alias="tierChangeCount")
    steps_reexecuted: Optional[list[str]] = Field(default=None, alias="stepsReexecuted")
    impact_assessment: Optional[dict[str, Any]] = Field(default=None, alias="impactAssessment")
    refresh_notes: Optional[dict[str, Any]] = Field(default=None, alias="refreshNotes")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    is_active: bool = Field(alias="isActive")
    started_at: Optional[str] = Field(default=None, alias="startedAt")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")
    created_at: Optional[str] = Field(default=None, alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)
