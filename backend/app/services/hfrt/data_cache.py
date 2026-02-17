"""Shared yfinance data cache for HFRT workflow handlers.

Problem: Multiple HFRT handlers (idea_screener, fundamental_analyst,
quantitative_analyst, due_diligence) independently call yfinance for the
same ticker, causing ~7 redundant API calls per workflow run.

Solution: Module-level cache dict with two cached fetch functions that wrap
the existing yfinance fetch patterns. Cache lives for the duration of the
Python process (cleared on project delete/rerun via clear_yfinance_cache).

Usage:
    from app.services.hfrt.data_cache import (
        get_yfinance_info,
        get_yfinance_financials,
        clear_yfinance_cache,
    )

    info = get_yfinance_info("MSFT")       # Cached after first call
    fins = get_yfinance_financials("MSFT") # Cached after first call
    clear_yfinance_cache("MSFT")           # Clear on rerun
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Module-level cache: keys are "{TICKER}:info" or "{TICKER}:financials"
_yfinance_cache: dict[str, dict] = {}


def get_yfinance_info(ticker: str) -> dict[str, Any]:
    """Cached yfinance info dict (market cap, sector, P/E, etc.).

    Returns the raw ``stock.info`` dict from yfinance, cached after
    the first call for a given ticker.
    """
    cache_key = f"{ticker}:info"
    if cache_key in _yfinance_cache:
        logger.info("yfinance cache HIT for %s", cache_key)
        return _yfinance_cache[cache_key]

    logger.info("yfinance cache MISS for %s", cache_key)
    import yfinance as yf

    stock = yf.Ticker(ticker)
    info = stock.info or {}
    _yfinance_cache[cache_key] = info
    return info


def get_yfinance_financials(ticker: str) -> dict[str, Any]:
    """Cached yfinance financial statements (income, balance, cashflow, up to 3 years).

    Returns a dict with three keys, each mapping to a dict of
    year-string -> row-dict::

        {
            "income_statement": {"2024-06-30": {...}, "2023-06-30": {...}, ...},
            "balance_sheet":    {"2024-06-30": {...}, ...},
            "cash_flow":        {"2024-06-30": {...}, ...},
        }

    Values in each row dict are ``float`` or ``None`` (for NaN).
    """
    cache_key = f"{ticker}:financials"
    if cache_key in _yfinance_cache:
        logger.info("yfinance cache HIT for %s", cache_key)
        return _yfinance_cache[cache_key]

    logger.info("yfinance cache MISS for %s", cache_key)
    import yfinance as yf

    stock = yf.Ticker(ticker)

    result: dict[str, Any] = {
        "income_statement": {},
        "balance_sheet": {},
        "cash_flow": {},
    }

    for attr, key in [
        ("financials", "income_statement"),
        ("balance_sheet", "balance_sheet"),
        ("cashflow", "cash_flow"),
    ]:
        try:
            df = getattr(stock, attr)
            if df is not None and not df.empty:
                for col_idx in range(min(3, len(df.columns))):
                    year = str(df.columns[col_idx])[:10]
                    result[key][year] = {
                        k: float(v) if v == v else None
                        for k, v in df.iloc[:, col_idx].to_dict().items()
                    }
        except Exception:
            logger.warning("Failed to fetch %s for %s", key, ticker, exc_info=True)

    _yfinance_cache[cache_key] = result
    return result


def clear_yfinance_cache(ticker: str | None = None) -> None:
    """Clear cache entries. Call on project delete/rerun.

    Args:
        ticker: If provided, clears only entries for that ticker.
                If None, clears the entire cache.
    """
    if ticker:
        keys_to_remove = [k for k in _yfinance_cache if k.startswith(f"{ticker}:")]
        for k in keys_to_remove:
            del _yfinance_cache[k]
        logger.info("yfinance cache cleared for ticker %s (%d entries)", ticker, len(keys_to_remove))
    else:
        count = len(_yfinance_cache)
        _yfinance_cache.clear()
        logger.info("yfinance cache fully cleared (%d entries)", count)
