"""Pydantic schemas for HFRT (Hedge Fund Research Team) endpoints."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Request schemas ──────────────────────────────────────────────────────────

class HFRTProjectCreate(BaseModel):
    """Request body for creating a new HFRT research project."""

    ticker: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Stock ticker symbol (e.g., MSFT, AAPL)",
    )
    auto_advance: bool = Field(
        default=False,
        alias="autoAdvance",
        description="If true, workflow advances between phases automatically without user approval",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        stripped = v.strip().upper()
        if not stripped:
            raise ValueError("ticker must not be empty")
        if not stripped.isalpha():
            raise ValueError("ticker must contain only letters")
        return stripped


# ── Response schemas ─────────────────────────────────────────────────────────

class HFRTProjectResponse(BaseModel):
    """Response schema for project creation."""

    id: int
    workflow_run_id: int = Field(alias="workflowRunId")
    ticker: str
    company_name: Optional[str] = Field(default=None, alias="companyName")
    status: str
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HFRTProjectListItem(BaseModel):
    """Response schema for a single project in list view."""

    id: int
    ticker: str
    company_name: Optional[str] = Field(default=None, alias="companyName")
    status: str
    workflow_run_id: int = Field(alias="workflowRunId")
    sector: Optional[str] = None
    market_cap: Optional[float] = Field(default=None, alias="marketCap")
    investable: bool = False
    conviction_score: Optional[float] = Field(default=None, alias="convictionScore")
    recommendation: Optional[str] = None
    current_phase: int = Field(default=0, alias="currentPhase")
    templates_populated: int = Field(default=0, alias="templatesPopulated")
    source: Optional[str] = None
    ist_screen_id: Optional[int] = Field(default=None, alias="istScreenId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HFRTProjectListResponse(BaseModel):
    """Paginated list of HFRT projects."""

    projects: list[HFRTProjectListItem]
    total: int


class HFRTProjectDetailResponse(BaseModel):
    """Full project detail response."""

    id: int
    workflow_run_id: int = Field(alias="workflowRunId")
    ticker: str
    company_name: Optional[str] = Field(default=None, alias="companyName")
    status: str
    sector: Optional[str] = None
    exchange: Optional[str] = None
    market_cap: Optional[float] = Field(default=None, alias="marketCap")
    investable: bool = False
    investable_verdict: Optional[str] = Field(default=None, alias="investableVerdict")
    conviction_score: Optional[float] = Field(default=None, alias="convictionScore")
    position_tier: Optional[str] = Field(default=None, alias="positionTier")
    recommendation: Optional[str] = None
    current_phase: int = Field(default=0, alias="currentPhase")
    source: Optional[str] = None
    ist_screen_id: Optional[int] = Field(default=None, alias="istScreenId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HFRTTemplateResponse(BaseModel):
    """Response for a single template."""

    template_number: int = Field(alias="templateNumber")
    template_name: str = Field(alias="templateName")
    status: str
    data: Optional[dict[str, Any]] = None
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HFRTTemplateListResponse(BaseModel):
    """List of all templates for a project."""

    project_id: int = Field(alias="projectId")
    templates: list[HFRTTemplateResponse]

    model_config = ConfigDict(populate_by_name=True)


# ── Claude output schemas (used in step handlers) ───────────────────────────

class IdeaScreenResult(BaseModel):
    """Structured output from the idea screen Claude call."""

    investable: bool = Field(description="Whether the ticker passes initial screen")
    verdict: str = Field(description="PASS, FAIL, or CONDITIONAL")
    company_name: str = Field(description="Full company name")
    sector: str = Field(description="Sector classification")
    exchange: str = Field(description="Stock exchange")
    market_cap_billions: Optional[float] = Field(
        default=None, description="Market cap in billions USD"
    )
    liquidity_check: dict[str, Any] = Field(
        description="Liquidity assessment details"
    )
    red_flags: list[str] = Field(
        default_factory=list, description="Initial red flags identified"
    )
    rationale: str = Field(description="Reasoning for the verdict")
