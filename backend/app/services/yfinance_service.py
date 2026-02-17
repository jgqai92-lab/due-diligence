"""yfinance data fetching service with 24-hour SQLite caching."""

import json
import logging
from datetime import datetime, timedelta

import yfinance as yf
from sqlalchemy.orm import Session

from app.config import settings
from app.models.cached_financials import CachedFinancial

logger = logging.getLogger(__name__)

DATA_TYPES = [
    "financials",
    "balance_sheet",
    "cashflow",
    "quarterly_financials",
    "quarterly_balance_sheet",
    "quarterly_cashflow",
    "info",
]


def _df_to_json(df) -> str:
    """Convert a pandas DataFrame to JSON string, handling NaN and dates."""
    if df is None or (hasattr(df, "empty") and df.empty):
        return "{}"
    return df.to_json(date_format="iso")


def _get_cached(db: Session, ticker: str, data_type: str) -> str | None:
    """Check cache for valid (non-expired) data."""
    now = datetime.utcnow()
    row = (
        db.query(CachedFinancial)
        .filter(
            CachedFinancial.ticker == ticker,
            CachedFinancial.data_type == data_type,
            CachedFinancial.expires_at > now,
        )
        .first()
    )
    if row:
        return row.raw_json
    return None


def _store_cache(db: Session, ticker: str, data_type: str, raw_json: str) -> None:
    """Upsert cached data with new expiry."""
    now = datetime.utcnow()
    expires = now + timedelta(hours=settings.cache_ttl_hours)

    existing = (
        db.query(CachedFinancial)
        .filter(
            CachedFinancial.ticker == ticker,
            CachedFinancial.data_type == data_type,
        )
        .first()
    )
    if existing:
        existing.raw_json = raw_json
        existing.fetched_at = now
        existing.expires_at = expires
    else:
        db.add(
            CachedFinancial(
                ticker=ticker,
                data_type=data_type,
                raw_json=raw_json,
                fetched_at=now,
                expires_at=expires,
            )
        )
    db.commit()


def fetch_financial_data(db: Session, ticker_symbol: str, force_refresh: bool = False) -> dict:
    """Fetch all financial data for a ticker, using cache when available.

    Returns dict with keys: financials, balance_sheet, cashflow,
    quarterly_financials, quarterly_balance_sheet, quarterly_cashflow,
    info, cache_hit, fetched_at, periods.
    """
    result = {}
    all_cached = True

    ticker = yf.Ticker(ticker_symbol)

    for data_type in DATA_TYPES:
        cached = None if force_refresh else _get_cached(db, ticker_symbol, data_type)

        if cached is not None:
            result[data_type] = json.loads(cached)
        else:
            all_cached = False
            try:
                if data_type == "info":
                    raw = ticker.info or {}
                    raw_json = json.dumps(raw, default=str)
                else:
                    df = getattr(ticker, data_type, None)
                    raw_json = _df_to_json(df)

                result[data_type] = json.loads(raw_json)
                # Only cache if data fetch was successful and result is not empty
                if result[data_type]:
                    _store_cache(db, ticker_symbol, data_type, raw_json)
            except Exception as e:
                logger.warning("Failed to fetch %s for %s: %s", data_type, ticker_symbol, e)
                result[data_type] = {}
                # Do NOT cache error responses

    # Extract periods from financials columns
    periods = []
    fin = result.get("financials", {})
    if isinstance(fin, dict):
        periods = list(fin.keys())[:5]

    result["cache_hit"] = all_cached
    result["fetched_at"] = datetime.utcnow().isoformat() + "Z"
    result["periods"] = periods

    return result


def clear_cache(db: Session, ticker: str) -> int:
    """Clear all cached data for a ticker. Returns number of records deleted."""
    deleted = (
        db.query(CachedFinancial)
        .filter(CachedFinancial.ticker == ticker)
        .delete()
    )
    db.commit()
    logger.info("Cleared %d cache entries for ticker %s", deleted, ticker)
    return deleted


def search_tickers(query: str) -> list[dict]:
    """Search for tickers using yfinance. Returns list of matches."""
    if not query or not query.strip():
        return []

    try:
        # Use yf.Search for proper fuzzy search (available in yfinance >= 1.1.0)
        search = yf.Search(query, max_results=10, news_count=0)
        quotes = search.quotes

        if not quotes:
            logger.info("No results found for query: %s", query)
            return []

        results = []
        for quote in quotes:
            results.append({
                "symbol": quote.get("symbol", ""),
                "name": quote.get("longname") or quote.get("shortname", ""),
                "exchange": quote.get("exchange", ""),
                "type": quote.get("quoteType", "equity").lower(),
            })

        return results

    except Exception as e:
        logger.error("Ticker search failed for query '%s': %s", query, str(e))
        return []


def transform_statement(raw_dict: dict, max_periods: int = 5) -> dict:
    """Transform column-oriented yfinance dict to row-oriented FinancialStatement format.

    Input:  { "2024-09-28T00:00:00.000Z": { "Total Revenue": 391035000000, ... }, ... }
    Output: { "periods": ["2024-09-28", ...], "line_items": [{ "label": "...", "values": [...] }, ...] }

    Key behavior:
    - Sorts periods descending (most recent first)
    - Limits to max_periods (default 5)
    - Truncates period strings to date only (first 10 chars)
    - Collects all unique line item labels across all periods, preserving first-seen order
    - Handles missing values as None
    - Filters out NaN values (replaces with None)
    - Skips line items that are None/NaN across ALL periods
    """
    if not raw_dict:
        return {"periods": [], "line_items": []}

    # Sort periods descending (most recent first) and limit
    sorted_periods = sorted(raw_dict.keys(), reverse=True)[:max_periods]

    # Truncate period keys to date-only (YYYY-MM-DD)
    periods = [p[:10] for p in sorted_periods]

    # Collect the union of all line item labels, preserving first-seen order
    seen_labels: dict[str, bool] = {}
    for period_key in sorted_periods:
        items = raw_dict.get(period_key, {})
        if isinstance(items, dict):
            for label in items:
                if label not in seen_labels:
                    seen_labels[label] = True

    # Build row-oriented line items
    line_items = []
    for label in seen_labels:
        values = []
        all_none = True
        for period_key in sorted_periods:
            items = raw_dict.get(period_key, {})
            val = items.get(label) if isinstance(items, dict) else None
            # Convert NaN-like values to None for clean JSON serialization
            if val is not None:
                try:
                    float_val = float(val)
                    if float_val != float_val:  # NaN check
                        values.append(None)
                    else:
                        values.append(float_val)
                        all_none = False
                except (ValueError, TypeError):
                    values.append(None)
            else:
                values.append(None)

        # Skip line items that are None/NaN across ALL periods
        if not all_none:
            line_items.append({"label": label, "values": values})

    # Reverse line items so statements read in standard order (e.g. Revenue at top, EPS at bottom)
    line_items.reverse()

    return {"periods": periods, "line_items": line_items}
