"""Search endpoint — ticker lookup."""

from fastapi import APIRouter, Query, HTTPException

from app.schemas.search import SearchResponse
from app.services.yfinance_service import search_tickers

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(q: str = Query(..., min_length=1, max_length=50)):
    """Search for tickers by query string."""
    results = search_tickers(q)
    return SearchResponse(
        results=results,
        query=q,
        count=len(results),
    )
