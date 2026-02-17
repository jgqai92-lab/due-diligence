"""Sector-specific prompt modules for HFRT Industry Analysis (Gap B2, Decision 15).

Each module exports:
  - SYSTEM_PROMPT: str — sector-specific analysis prompt for Claude
  - KPIS: list[str] — key performance indicators for the sector

Registry function `get_sector_config` returns the prompt and KPIs for a given
GICS sector name, falling back to a generic prompt for unknown sectors.
"""

from typing import NamedTuple

from app.services.hfrt.sector_prompts import (
    consumer,
    energy_materials,
    financials,
    healthcare,
    industrials,
    technology,
)


class SectorConfig(NamedTuple):
    system_prompt: str
    kpis: list[str]


# Registry mapping GICS sector names (lowercase) to modules
_SECTOR_REGISTRY: dict[str, SectorConfig] = {
    "information technology": SectorConfig(technology.SYSTEM_PROMPT, technology.KPIS),
    "technology": SectorConfig(technology.SYSTEM_PROMPT, technology.KPIS),
    "communication services": SectorConfig(technology.SYSTEM_PROMPT, technology.KPIS),
    "health care": SectorConfig(healthcare.SYSTEM_PROMPT, healthcare.KPIS),
    "healthcare": SectorConfig(healthcare.SYSTEM_PROMPT, healthcare.KPIS),
    "financials": SectorConfig(financials.SYSTEM_PROMPT, financials.KPIS),
    "consumer discretionary": SectorConfig(consumer.SYSTEM_PROMPT, consumer.KPIS),
    "consumer staples": SectorConfig(consumer.SYSTEM_PROMPT, consumer.KPIS),
    "consumer": SectorConfig(consumer.SYSTEM_PROMPT, consumer.KPIS),
    "energy": SectorConfig(energy_materials.SYSTEM_PROMPT, energy_materials.KPIS),
    "materials": SectorConfig(energy_materials.SYSTEM_PROMPT, energy_materials.KPIS),
    "industrials": SectorConfig(industrials.SYSTEM_PROMPT, industrials.KPIS),
    "utilities": SectorConfig(energy_materials.SYSTEM_PROMPT, energy_materials.KPIS),
    "real estate": SectorConfig(financials.SYSTEM_PROMPT, financials.KPIS),
}

# Generic fallback
_GENERIC_PROMPT = """You are a sector specialist equity research analyst performing industry analysis.

Analyze the industry/sector for the given company, covering:
1. Market size (TAM/SAM/SOM if data available)
2. Growth rate and drivers
3. Industry lifecycle stage (emerging, growth, mature, declining)
4. Key industry trends
5. Regulatory environment
6. Sector-specific KPIs
7. Key players and market structure
8. Barriers to entry
9. Disruption risks
10. Cyclicality assessment
11. Recent M&A activity

NEVER fabricate data. Return ONLY valid JSON matching the schema provided."""

_GENERIC_KPIS = [
    "Revenue growth",
    "Operating margin",
    "ROIC",
    "Free cash flow margin",
    "Debt/EBITDA",
]


def get_sector_config(sector: str | None) -> SectorConfig:
    """Return sector-specific prompt and KPIs, with generic fallback."""
    if not sector:
        return SectorConfig(_GENERIC_PROMPT, _GENERIC_KPIS)
    return _SECTOR_REGISTRY.get(
        sector.strip().lower(),
        SectorConfig(_GENERIC_PROMPT, _GENERIC_KPIS),
    )
