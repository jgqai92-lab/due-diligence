"""Alpaca Paper Trading API integration for portfolio valuation."""

import logging
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

HEADERS = {
    "APCA-API-KEY-ID": settings.alpaca_api_key,
    "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
}


def _get_headers() -> dict:
    return {
        "APCA-API-KEY-ID": settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
    }


def get_current_price(ticker: str) -> float | None:
    """Get current price for a ticker via Alpaca."""
    if not settings.alpaca_api_key:
        return None
    try:
        url = f"{settings.alpaca_base_url}/v2/assets/{ticker}"
        resp = httpx.get(url, headers=_get_headers(), timeout=10)
        if resp.status_code == 200:
            # Alpaca asset endpoint doesn't return price directly
            # Use latest trade endpoint instead
            trade_url = f"https://data.alpaca.markets/v2/stocks/{ticker}/trades/latest"
            trade_resp = httpx.get(trade_url, headers=_get_headers(), timeout=10)
            if trade_resp.status_code == 200:
                data = trade_resp.json()
                return float(data.get("trade", {}).get("p", 0))
    except Exception as e:
        logger.warning("Alpaca price fetch failed for %s: %s", ticker, e)
    return None


def get_account_info() -> dict | None:
    """Get Alpaca paper trading account info."""
    if not settings.alpaca_api_key:
        return None
    try:
        url = f"{settings.alpaca_base_url}/v2/account"
        resp = httpx.get(url, headers=_get_headers(), timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning("Alpaca account fetch failed: %s", e)
    return None
