"""Pydantic schemas for IST synthesis endpoints."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ISTSynthesisCreate(BaseModel):
    """Request payload for creating a synthesis."""

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


class ISTSynthesisCreateResponse(BaseModel):
    id: int
    name: str
    status: str
    workflow_run_id: int = Field(alias="workflowRunId")
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    warning: Optional[str] = None
    idempotent: Optional[bool] = None

    model_config = ConfigDict(populate_by_name=True)


class SynthesisListItem(BaseModel):
    id: int
    name: str
    status: str
    workflow_run_id: int = Field(alias="workflowRunId")
    source_screen_count: int = Field(default=0, alias="sourceScreenCount")
    tier_change_count: int = Field(default=0, alias="tierChangeCount")
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class SynthesisListResponse(BaseModel):
    syntheses: list[SynthesisListItem]
    total: int


class SynthesisDetailResponse(BaseModel):
    id: int
    name: str
    status: str
    workflow_run_id: int = Field(alias="workflowRunId")
    overlap_matrix: list[dict[str, Any]] = Field(default_factory=list, alias="overlapMatrix")
    thesis_interactions: list[dict[str, Any]] = Field(default_factory=list, alias="thesisInteractions")
    tier_changes: list[dict[str, Any]] = Field(default_factory=list, alias="tierChanges")
    combined_brief: dict[str, Any] = Field(default_factory=dict, alias="combinedBrief")
    report: Optional[str] = None
    report_metadata: dict[str, Any] = Field(default_factory=dict, alias="reportMetadata")
    certification: dict[str, Any] = Field(default_factory=dict)
    hfrt_handoff: dict[str, Any] = Field(default_factory=dict, alias="hfrtHandoff")
    is_certified: bool = Field(alias="isCertified")
    certified_at: Optional[str] = Field(default=None, alias="certifiedAt")
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class SynthesisSourceResponse(BaseModel):
    id: int
    screen_id: int = Field(alias="screenId")
    screen_name: str = Field(alias="screenName")
    tier1_count: int = Field(alias="tier1Count")
    tier2_count: int = Field(alias="tier2Count")
    tier3_count: int = Field(alias="tier3Count")
    primary_theme: Optional[str] = Field(default=None, alias="primaryTheme")

    model_config = ConfigDict(populate_by_name=True)


class SynthesisSourcesResponse(BaseModel):
    synthesis_id: int = Field(alias="synthesisId")
    sources: list[SynthesisSourceResponse]

    model_config = ConfigDict(populate_by_name=True)


class SynthesisOverlapResponse(BaseModel):
    synthesis_id: int = Field(alias="synthesisId")
    overlap: list[dict[str, Any]]

    model_config = ConfigDict(populate_by_name=True)


class SynthesisInteractionsResponse(BaseModel):
    synthesis_id: int = Field(alias="synthesisId")
    interactions: list[dict[str, Any]]

    model_config = ConfigDict(populate_by_name=True)


class SynthesisTierChangesResponse(BaseModel):
    synthesis_id: int = Field(alias="synthesisId")
    tier_changes: list[dict[str, Any]] = Field(alias="tierChanges")

    model_config = ConfigDict(populate_by_name=True)


class SynthesisEquityResponse(BaseModel):
    id: int
    ticker: str
    company_name: str = Field(alias="companyName")
    original_tier: int = Field(alias="originalTier")
    new_tier: int = Field(alias="newTier")
    tier_changed: bool = Field(alias="tierChanged")
    tier_change_rationale: Optional[str] = Field(default=None, alias="tierChangeRationale")
    source_screen_count: int = Field(alias="sourceScreenCount")
    source_screen_ids: list[int] = Field(default_factory=list, alias="sourceScreenIds")
    combined_scarcity_score: dict[str, Any] = Field(default_factory=dict, alias="combinedScarcityScore")
    combined_thesis: Optional[str] = Field(default=None, alias="combinedThesis")
    combined_catalyst: Optional[str] = Field(default=None, alias="combinedCatalyst")
    conviction: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class SynthesisEquitiesResponse(BaseModel):
    synthesis_id: int = Field(alias="synthesisId")
    equities: list[SynthesisEquityResponse]

    model_config = ConfigDict(populate_by_name=True)


class SynthesisDialecticResponse(BaseModel):
    synthesis_id: int = Field(alias="synthesisId")
    side: str
    content: dict[str, Any]
    created_at: Optional[str] = Field(default=None, alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class SynthesisReportResponse(BaseModel):
    synthesis_id: int = Field(alias="synthesisId")
    report: str
    metadata: dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)


class SynthesisHandoffResponse(BaseModel):
    synthesis_id: int = Field(alias="synthesisId")
    handoff: dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)

