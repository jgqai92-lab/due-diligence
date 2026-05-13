"""IST-to-HFRT bridge endpoints -- retrieve handoff candidates and create HFRT projects.

All endpoints under /api/bridge prefix (INV-BE-01: /api/ prefix).
Error format: {"error": {"code": "...", "message": "..."}} (INV-BE-02).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.bridge import get_handoff_candidates, create_hfrt_from_handoff

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# INV-BE-01: Every router MUST use /api/ prefix
router = APIRouter(prefix="/api/bridge", tags=["bridge"])


def _error(code: str, message: str) -> dict:
    """Build a standard error detail dict (INV-BE-02)."""
    return {"error": {"code": code, "message": message}}


# ── Request schema ──────────────────────────────────────────────────────────


class BridgeCreateRequest(BaseModel):
    """Request body for creating HFRT projects from IST handoff."""

    screen_id: int = Field(..., alias="screenId", description="ID of the certified IST screen")
    tickers: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of ticker symbols to create HFRT projects for",
    )

    model_config = {"populate_by_name": True}

    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, v: list[str]) -> list[str]:
        cleaned = []
        for ticker in v:
            stripped = ticker.strip().upper()
            if not stripped:
                raise ValueError("ticker must not be empty")
            if not stripped.isalpha():
                raise ValueError(f"ticker '{ticker}' must contain only letters")
            if len(stripped) > 10:
                raise ValueError(f"ticker '{ticker}' exceeds maximum length of 10")
            cleaned.append(stripped)
        # Check for duplicates
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("duplicate tickers are not allowed")
        return cleaned


# ── GET /api/bridge/ist-to-hfrt/candidates/{screen_id} ─────────────────────


@router.get("/ist-to-hfrt/candidates/{screen_id}")
def get_candidates(screen_id: int, db: Session = Depends(get_db)):
    """Get handoff candidates from a certified IST screen.

    Returns the Tier 1 candidates formatted for HFRT project creation.
    The screen must be certified before candidates can be retrieved.
    """
    try:
        handoff_data = get_handoff_candidates(db, screen_id)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=404,
                detail=_error("SCREEN_NOT_FOUND", msg),
            )
        elif "not certified" in msg.lower():
            raise HTTPException(
                status_code=400,
                detail=_error("NOT_CERTIFIED", msg),
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=_error("NO_HANDOFF_DATA", msg),
            )

    return handoff_data


# ── POST /api/bridge/ist-to-hfrt ───────────────────────────────────────────


@router.post("/ist-to-hfrt", status_code=201)
@limiter.limit("10/hour")
def create_hfrt_projects(
    request: Request,
    data: BridgeCreateRequest,
    db: Session = Depends(get_db),
):
    """Create HFRT research projects from IST handoff candidates.

    For each ticker provided, creates a full HFRT project (WorkflowRun,
    HFRTProject, 23 steps, 15 templates) with the Idea Screen template
    pre-populated from IST handoff data.

    Individual ticker failures do not prevent other tickers from being created.
    Failures are reported in the response alongside successful creations.
    """
    created = []
    failed = []

    for ticker in data.tickers:
        try:
            result = create_hfrt_from_handoff(db, data.screen_id, ticker)
            created.append(result)
        except ValueError as exc:
            msg = str(exc)
            logger.warning(
                "Bridge creation failed for ticker %s from screen %d: %s",
                ticker,
                data.screen_id,
                msg,
            )
            failed.append({
                "ticker": ticker,
                "error": msg,
            })
        except Exception as exc:
            logger.error(
                "Unexpected error creating HFRT project for ticker %s from screen %d: %s",
                ticker,
                data.screen_id,
                exc,
                exc_info=True,
            )
            failed.append({
                "ticker": ticker,
                "error": "Unexpected error during project creation",
            })

    # If all tickers failed and there was a screen-level issue, return appropriate error
    if not created and failed:
        # Check if all failures are the same screen-level error (not found, not certified)
        # Distinguish "Screen X not found" from "Ticker X not found in handoff candidates"
        first_error = failed[0]["error"]
        first_lower = first_error.lower()
        if first_lower.startswith("screen") and "not found" in first_lower:
            raise HTTPException(
                status_code=404,
                detail=_error("SCREEN_NOT_FOUND", first_error),
            )
        elif "not certified" in first_lower:
            raise HTTPException(
                status_code=400,
                detail=_error("NOT_CERTIFIED", first_error),
            )

    return {
        "created": created,
        "failed": failed,
        "total": len(created),
        "screenId": data.screen_id,
    }
