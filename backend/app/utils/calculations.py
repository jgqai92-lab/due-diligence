"""Shared math helpers for forensic financial formulas."""


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def safe_ratio_change(current: float | None, prior: float | None) -> float | None:
    """Calculate (current / prior) ratio, returns None if either is missing or prior is 0."""
    return safe_divide(current, prior)


def pct_change(current: float | None, prior: float | None) -> float | None:
    """Calculate percentage change: (current - prior) / |prior| * 100."""
    if current is None or prior is None or prior == 0:
        return None
    return ((current - prior) / abs(prior)) * 100
