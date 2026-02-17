import re

TICKER_PATTERN = re.compile(r"^[A-Z]{1,5}$")


def validate_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    if not TICKER_PATTERN.match(ticker):
        raise ValueError(f"Invalid ticker format: {ticker}. Must be 1-5 uppercase letters.")
    return ticker
