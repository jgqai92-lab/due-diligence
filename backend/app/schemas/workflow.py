"""Pydantic schemas for workflow engine endpoints."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Request schemas ──────────────────────────────────────────────────────────

class WorkflowCreate(BaseModel):
    """Request body for creating a new workflow run."""

    workflow_type: str = Field(
        ...,
        alias="workflowType",
        description="Workflow type: IST, HFRT, IST_SYNTHESIS, or IST_REFRESH",
    )
    name: str = Field(
        ...,
        max_length=200,
        description="Human-readable name for this workflow run",
    )
    config: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional JSON config for the workflow",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("workflow_type")
    @classmethod
    def validate_workflow_type(cls, v: str) -> str:
        allowed = ("IST", "HFRT", "IST_SYNTHESIS", "IST_REFRESH")
        if v not in allowed:
            raise ValueError(f"workflow_type must be one of {allowed}")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name must not be empty")
        return stripped


class WorkflowAdvanceRequest(BaseModel):
    """Request body for advancing a workflow past a checkpoint."""

    user_notes: Optional[str] = Field(
        default=None,
        alias="userNotes",
        max_length=2000,
        description="Optional notes from the user when approving a phase transition",
    )

    model_config = ConfigDict(populate_by_name=True)


# ── Response schemas ─────────────────────────────────────────────────────────

class WorkflowStepResponse(BaseModel):
    """Response schema for a single workflow step."""

    id: int
    step_name: str = Field(alias="stepName")
    phase: int
    phase_name: str = Field(alias="phaseName")
    status: str
    started_at: Optional[datetime] = Field(default=None, alias="startedAt")
    completed_at: Optional[datetime] = Field(default=None, alias="completedAt")
    duration_ms: Optional[int] = Field(default=None, alias="durationMs")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WorkflowResponse(BaseModel):
    """Response schema for a workflow run (list/summary view)."""

    id: int
    workflow_type: str = Field(alias="workflowType")
    name: str
    status: str
    current_phase: int = Field(alias="currentPhase")
    current_phase_name: Optional[str] = Field(default=None, alias="currentPhaseName")
    config: Optional[dict[str, Any]] = None
    auto_advance: bool = Field(default=False, alias="autoAdvance")
    steps_completed: int = Field(alias="stepsCompleted")
    steps_total: int = Field(alias="stepsTotal")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WorkflowDetailResponse(BaseModel):
    """Response schema for a single workflow run with step details."""

    id: int
    workflow_type: str = Field(alias="workflowType")
    name: str
    status: str
    current_phase: int = Field(alias="currentPhase")
    current_phase_name: Optional[str] = Field(default=None, alias="currentPhaseName")
    config: Optional[dict[str, Any]] = None
    auto_advance: bool = Field(default=False, alias="autoAdvance")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    steps_completed: int = Field(alias="stepsCompleted")
    steps_total: int = Field(alias="stepsTotal")
    started_at: Optional[datetime] = Field(default=None, alias="startedAt")
    completed_at: Optional[datetime] = Field(default=None, alias="completedAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    steps: list[WorkflowStepResponse] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WorkflowAdvanceResponse(BaseModel):
    """Response for the advance/start endpoint."""

    id: int
    status: str
    advancing_to_phase: Optional[int] = Field(default=None, alias="advancingToPhase")
    message: str

    model_config = ConfigDict(populate_by_name=True)


class SSEEvent(BaseModel):
    """Schema for Server-Sent Events."""

    type: str
    data: dict[str, Any]


# ── List response wrapper ───────────────────────────────────────────────────

class WorkflowListResponse(BaseModel):
    """Paginated list of workflow runs."""

    workflows: list[WorkflowResponse]
    total: int
    limit: int
    offset: int
