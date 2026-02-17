"""Frameworks Reference Panel -- analytical framework reference material for IST and HFRT.

Endpoints:
  GET /api/frameworks/ist         -- list all IST frameworks (summaries only)
  GET /api/frameworks/ist/{name}  -- full detail for a single IST framework
  GET /api/frameworks/hfrt        -- list all HFRT frameworks (summaries only)
  GET /api/frameworks/hfrt/{name} -- full detail for a single HFRT framework

All endpoints under /api/frameworks prefix (INV-BE-01: /api/ prefix).
Error format: {"error": {"code": "...", "message": "..."}} (INV-BE-02).

Framework content is loaded from disk via framework_loader (Decision 14).
"""

import logging

from fastapi import APIRouter, HTTPException

from app.services.framework_loader import get_framework, get_framework_names, list_frameworks

logger = logging.getLogger(__name__)

# INV-BE-01: Every router MUST use /api/ prefix
router = APIRouter(prefix="/api/frameworks", tags=["frameworks"])


def _error(code: str, message: str) -> dict:
    """Build a standard error detail dict (INV-BE-02)."""
    return {"error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# IST Endpoints
# ---------------------------------------------------------------------------


@router.get("/ist")
def list_ist_frameworks():
    """List all IST analytical frameworks (summaries only).

    Returns framework name, display name, description, and category.
    Does NOT include the full markdown content.
    """
    summaries = list_frameworks("ist")
    return {"frameworks": summaries, "total": len(summaries)}


@router.get("/ist/{name}")
def get_ist_framework(name: str):
    """Get full detail for a single IST framework by name.

    Returns all fields including the full markdown content.
    404 if the framework name is not recognized.
    """
    framework = get_framework("ist", name)
    if framework is None:
        valid = get_framework_names("ist")
        raise HTTPException(
            status_code=404,
            detail=_error(
                "FRAMEWORK_NOT_FOUND",
                f"No IST framework with name '{name}'. Valid names: {valid}",
            ),
        )
    return framework


# ---------------------------------------------------------------------------
# HFRT Endpoints
# ---------------------------------------------------------------------------


@router.get("/hfrt")
def list_hfrt_frameworks():
    """List all HFRT analytical frameworks (summaries only)."""
    summaries = list_frameworks("hfrt")
    return {"frameworks": summaries, "total": len(summaries)}


@router.get("/hfrt/{name}")
def get_hfrt_framework(name: str):
    """Get full detail for a single HFRT framework by name.

    Returns metadata plus the full markdown content loaded from disk.
    404 if the framework name is not recognized.
    """
    framework = get_framework("hfrt", name)
    if framework is None:
        valid = get_framework_names("hfrt")
        raise HTTPException(
            status_code=404,
            detail=_error(
                "FRAMEWORK_NOT_FOUND",
                f"No HFRT framework with name '{name}'. Valid names: {valid}",
            ),
        )
    return framework
