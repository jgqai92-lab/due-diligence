"""Watchlist endpoints — cross-workflow ticker tracking.

Aggregates IST equity candidates and HFRT research projects for a unified
watchlist view. Tickers can be added from either workflow or standalone.

Endpoints:
    GET    /api/watchlist              -- list all watchlist entries with summary
    POST   /api/watchlist              -- add a ticker to the watchlist
    DELETE /api/watchlist/{ticker}     -- remove a ticker from the watchlist
    GET    /api/watchlist/{ticker}/summary  -- per-ticker aggregate from IST + HFRT
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hfrt import HFRTProject
from app.models.ist import ISTEquityCandidate, ISTScreen

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# INV-BE-01: Every router MUST use /api/ prefix
router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


# ── In-process watchlist store ───────────────────────────────────────────────
# Lightweight in-process store (dict keyed by uppercase ticker).
# Survives the lifetime of the server process.  A persistent DB table
# would be added here if the application outgrows this approach.

_watchlist: dict[str, dict] = {}


# ── Request / response schemas ────────────────────────────────────────────────


class WatchlistAddRequest(BaseModel):
    ticker: str
    note: Optional[str] = None

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        stripped = v.strip().upper()
        if not stripped:
            raise ValueError("ticker must not be empty")
        if len(stripped) > 10:
            raise ValueError("ticker must be at most 10 characters")
        return stripped


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ist_summary(db: Session, ticker: str) -> dict:
    """Return IST aggregate for a ticker: best tier, screens, top conviction."""
    rows = (
        db.query(ISTEquityCandidate, ISTScreen)
        .join(ISTScreen, ISTEquityCandidate.screen_id == ISTScreen.id)
        .filter(ISTEquityCandidate.ticker == ticker)
        .order_by(ISTEquityCandidate.tier, ISTEquityCandidate.id.desc())
        .all()
    )
    if not rows:
        return {"screenCount": 0, "bestTier": None, "conviction": None, "candidates": []}

    candidates = []
    for cand, screen in rows:
        scarcity = None
        try:
            parsed = json.loads(cand.scarcity_score)
            if isinstance(parsed, dict):
                scarcity = parsed.get("overall") or parsed.get("composite")
            else:
                scarcity = parsed
        except (json.JSONDecodeError, TypeError):
            pass

        candidates.append({
            "screenId": screen.id,
            "screenName": screen.name,
            "tier": cand.tier,
            "conviction": cand.conviction,
            "catalyst": cand.catalyst,
            "scarcityScore": scarcity,
            "screenStatus": screen.status,
            "isCertified": bool(screen.is_certified),
            "createdAt": cand.created_at.isoformat() if cand.created_at else None,
        })

    best_tier = min(c["tier"] for c in candidates)
    top_conviction = next(
        (c["conviction"] for c in candidates if c["tier"] == best_tier),
        None,
    )

    return {
        "screenCount": len(set(c["screenId"] for c in candidates)),
        "bestTier": best_tier,
        "conviction": top_conviction,
        "candidates": candidates,
    }


def _hfrt_summary(db: Session, ticker: str) -> dict:
    """Return HFRT aggregate for a ticker: latest project, recommendation, conviction."""
    projects = (
        db.query(HFRTProject)
        .filter(HFRTProject.ticker == ticker)
        .order_by(HFRTProject.created_at.desc())
        .all()
    )
    if not projects:
        return {
            "projectCount": 0,
            "latestProjectId": None,
            "latestStatus": None,
            "recommendation": None,
            "convictionScore": None,
            "isCertified": False,
        }

    latest = projects[0]
    return {
        "projectCount": len(projects),
        "latestProjectId": latest.id,
        "latestStatus": latest.status,
        "recommendation": latest.recommendation,
        "convictionScore": latest.conviction_score,
        "isCertified": bool(latest.is_certified),
    }


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("")
@limiter.limit("60/minute")
def list_watchlist(
    request: Request,
    db: Session = Depends(get_db),
):
    """List all watchlist tickers with IST and HFRT aggregate summaries.

    Returns:
        List of watchlist entries, each with ticker, note, addedAt, ist summary,
        and hfrt summary.
    """
    result = []
    for ticker, entry in sorted(_watchlist.items()):
        ist = _ist_summary(db, ticker)
        hfrt = _hfrt_summary(db, ticker)
        result.append({
            "ticker": ticker,
            "note": entry.get("note"),
            "addedAt": entry.get("added_at"),
            "ist": ist,
            "hfrt": hfrt,
        })
    return {"count": len(result), "items": result}


@router.post("", status_code=201)
@limiter.limit("30/minute")
def add_to_watchlist(
    request: Request,
    body: WatchlistAddRequest,
    db: Session = Depends(get_db),
):
    """Add a ticker to the watchlist.

    Idempotent: adding an existing ticker updates the note and returns 201.

    Returns:
        The watchlist entry with ticker, note, addedAt, ist summary, hfrt summary.
    """
    ticker = body.ticker  # already normalized to uppercase by validator
    _watchlist[ticker] = {
        "note": body.note,
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("Watchlist: added ticker %s", ticker)
    ist = _ist_summary(db, ticker)
    hfrt = _hfrt_summary(db, ticker)
    return {
        "ticker": ticker,
        "note": body.note,
        "addedAt": _watchlist[ticker]["added_at"],
        "ist": ist,
        "hfrt": hfrt,
    }


@router.delete("/{ticker}", status_code=204)
@limiter.limit("30/minute")
def remove_from_watchlist(
    request: Request,
    ticker: str,
):
    """Remove a ticker from the watchlist.

    Returns 204 No Content on success.
    Raises 404 if the ticker is not on the watchlist.
    """
    ticker_upper = ticker.strip().upper()
    if ticker_upper not in _watchlist:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ticker_not_found", "message": f"{ticker_upper} is not on the watchlist"}},
        )
    del _watchlist[ticker_upper]
    logger.info("Watchlist: removed ticker %s", ticker_upper)
    return None


@router.get("/{ticker}/summary")
@limiter.limit("60/minute")
def get_ticker_summary(
    request: Request,
    ticker: str,
    db: Session = Depends(get_db),
):
    """Get a detailed per-ticker aggregate from IST screens and HFRT projects.

    Works for both watchlist tickers and any ticker in the database.
    Does not require the ticker to be on the watchlist.

    Returns:
        ticker, isOnWatchlist, note, ist aggregate, hfrt aggregate.
    """
    ticker_upper = ticker.strip().upper()
    if not ticker_upper:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "invalid_ticker", "message": "Ticker must not be empty"}},
        )

    ist = _ist_summary(db, ticker_upper)
    hfrt = _hfrt_summary(db, ticker_upper)

    on_watchlist = ticker_upper in _watchlist
    note = _watchlist[ticker_upper].get("note") if on_watchlist else None
    added_at = _watchlist[ticker_upper].get("added_at") if on_watchlist else None

    return {
        "ticker": ticker_upper,
        "isOnWatchlist": on_watchlist,
        "note": note,
        "addedAt": added_at,
        "ist": ist,
        "hfrt": hfrt,
    }
