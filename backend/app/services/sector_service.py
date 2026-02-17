"""Sector detection and conditional metric routing.

Classifies companies into sector categories and returns sector-specific
metrics when applicable (e.g., SaaS efficiency metrics for software companies).
"""

import logging
from enum import Enum

from app.schemas.analysis import (
    MetricComponent,
    SectorSpecificMetrics,
)

logger = logging.getLogger(__name__)


class SectorCategory(str, Enum):
    SAAS = "SAAS"
    FINANCIAL = "FINANCIAL"
    REIT = "REIT"
    ENERGY = "ENERGY"
    HEALTHCARE = "HEALTHCARE"
    INDUSTRIAL = "INDUSTRIAL"
    CONSUMER = "CONSUMER"
    GENERAL = "GENERAL"


# Keywords used for sector classification
_SAAS_INDUSTRY_KEYWORDS = [
    "software",
    "internet content",
    "information technology",
    "cloud",
    "saas",
    "application software",
    "systems software",
    "infrastructure software",
]

_FINANCIAL_SECTOR_NAMES = [
    "financial services",
    "financial",
]

_REIT_INDUSTRY_KEYWORDS = [
    "reit",
    "real estate investment trust",
    "real estate",
]

_ENERGY_SECTOR_NAMES = [
    "energy",
]

_HEALTHCARE_SECTOR_NAMES = [
    "healthcare",
    "health care",
]

_INDUSTRIAL_SECTOR_NAMES = [
    "industrials",
    "industrial",
    "basic materials",
]

_CONSUMER_SECTOR_NAMES = [
    "consumer cyclical",
    "consumer defensive",
    "consumer discretionary",
    "consumer staples",
]


def detect_sector_category(info: dict) -> SectorCategory:
    """Classify a company into a SectorCategory using yfinance info dict.

    Uses info["sector"] and info["industry"] fields.
    Returns SectorCategory.GENERAL if classification is uncertain.
    """
    if not info or not isinstance(info, dict):
        return SectorCategory.GENERAL

    sector = (info.get("sector") or "").lower().strip()
    industry = (info.get("industry") or "").lower().strip()

    # SAAS: Technology sector AND industry contains software-related keyword
    if sector == "technology":
        for keyword in _SAAS_INDUSTRY_KEYWORDS:
            if keyword in industry:
                return SectorCategory.SAAS
        # Technology sector but not software => GENERAL
        return SectorCategory.GENERAL

    # REIT: check industry first (REITs can appear under various sectors)
    for keyword in _REIT_INDUSTRY_KEYWORDS:
        if keyword in industry:
            return SectorCategory.REIT

    # Financial
    for name in _FINANCIAL_SECTOR_NAMES:
        if name in sector:
            return SectorCategory.FINANCIAL

    # Energy
    for name in _ENERGY_SECTOR_NAMES:
        if name in sector:
            return SectorCategory.ENERGY

    # Healthcare
    for name in _HEALTHCARE_SECTOR_NAMES:
        if name in sector:
            return SectorCategory.HEALTHCARE

    # Industrial / Basic Materials
    for name in _INDUSTRIAL_SECTOR_NAMES:
        if name in sector:
            return SectorCategory.INDUSTRIAL

    # Consumer
    for name in _CONSUMER_SECTOR_NAMES:
        if name in sector:
            return SectorCategory.CONSUMER

    return SectorCategory.GENERAL


def get_sector_specific_metrics(
    category: SectorCategory,
    data: dict,
) -> SectorSpecificMetrics | None:
    """Return sector-specific metrics if applicable.

    Currently only SaaS companies get additional metrics (Rule of 40, Magic Number).
    Other sector-specific metrics (NIM for banks, FFO for REITs, etc.) can be
    added in future iterations.

    Args:
        category: Detected sector category.
        data: Full yfinance data dict (with financials, cashflow, etc.).

    Returns:
        SectorSpecificMetrics or None if no sector-specific metrics apply.
    """
    if category != SectorCategory.SAAS:
        return None

    # Import here to avoid circular imports — forensic_engine imports schemas
    from app.services.forensic_engine import compute_rule_of_40, compute_magic_number

    financials = data.get("financials", {})
    cashflow = data.get("cashflow", {})
    quarterly_financials = data.get("quarterly_financials", {})

    r40 = compute_rule_of_40(financials, cashflow)
    mn = compute_magic_number(financials, quarterly_financials)

    metrics = {}
    interpretations = {}

    # Rule of 40
    metrics["rule_of_40"] = MetricComponent(
        value=r40.score,
        citation=r40.citations.get("revenue_current", None),
    )
    interpretations["rule_of_40"] = r40.interpretation

    # Magic Number
    metrics["magic_number"] = MetricComponent(
        value=mn.score,
        citation=mn.citations.get("quarterly_revenue_current", None),
    )
    interpretations["magic_number"] = mn.interpretation

    return SectorSpecificMetrics(
        sector_category=category.value,
        label="SaaS Efficiency",
        metrics=metrics,
        interpretations=interpretations,
    )
