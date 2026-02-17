"""File-based framework content loader with mtime-based cache invalidation.

Loads analytical framework markdown files from disk for IST and HFRT workflows.
Parses metadata from blockquote headers (Classification, Version, Framework Owner).
Caches content with per-file mtime tracking so edits are picked up automatically.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Framework directories relative to this file's package root.
_BASE = Path(__file__).resolve().parent.parent / "data" / "frameworks"
_DIRS: Dict[str, Path] = {
    "ist": _BASE / "ist",
    "hfrt": _BASE / "hfrt",
}

# Per-file cache: { (workflow_type, stem) : (mtime, parsed_dict) }
_cache: Dict[tuple, tuple] = {}


def _parse_framework(filepath: Path) -> Dict[str, Any]:
    """Parse a framework markdown file into a structured dict.

    Expected format:
        # Framework Title

        > **Classification:** SOME_TYPE
        > **Applied To:** ...
        > **Version:** 1.0
        > **Framework Owner:** @Agent1, @Agent2

        ---

        ## Core Principle
        ...
    """
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    # --- Extract display name from first H1 ---
    display_name = filepath.stem.replace("_", " ").title()
    for line in lines:
        if line.startswith("# "):
            display_name = line[2:].strip()
            break

    # --- Extract blockquote metadata ---
    classification = ""
    version = ""
    owner = ""
    applied_to = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("> **Classification:**"):
            classification = re.sub(r"^>\s*\*\*Classification:\*\*\s*", "", stripped).strip()
        elif stripped.startswith("> **Version:**"):
            version = re.sub(r"^>\s*\*\*Version:\*\*\s*", "", stripped).strip()
        elif stripped.startswith("> **Framework Owner:**"):
            owner = re.sub(r"^>\s*\*\*Framework Owner:\*\*\s*", "", stripped).strip()
        elif stripped.startswith("> **Applied To:**"):
            applied_to = re.sub(r"^>\s*\*\*Applied To:\*\*\s*", "", stripped).strip()

    # --- Extract description: first paragraph after metadata block ---
    description = applied_to  # fallback
    in_body = False
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            in_body = True
            continue
        if in_body and stripped.startswith("## "):
            # Read next non-empty lines as description paragraph
            idx = lines.index(line)
            desc_lines = []
            for dl in lines[idx + 1 :]:
                dl_stripped = dl.strip()
                if dl_stripped == "" and desc_lines:
                    break
                if dl_stripped.startswith("#") or dl_stripped == "---":
                    break
                if dl_stripped:
                    desc_lines.append(dl_stripped)
            if desc_lines:
                description = " ".join(desc_lines)
            break

    # --- Derive category from classification ---
    category = _classify(classification)

    return {
        "name": filepath.stem,
        "displayName": display_name,
        "description": description,
        "category": category,
        "classification": classification,
        "version": version,
        "owner": owner,
        "content": text,
    }


def _classify(classification: str) -> str:
    """Map a Classification string to a short category tag."""
    cl = classification.upper()
    if "EQUITY" in cl or "SCORING" in cl:
        return "equity_analysis"
    if "DEMAND" in cl or "QUANTITATIVE" in cl:
        return "thematic_analysis"
    if "CHALLENGE" in cl or "STRESS" in cl or "NULL" in cl:
        return "quality_assurance"
    if "CONVICTION" in cl:
        return "conviction_building"
    if "BEHAVIORAL" in cl or "SCAR" in cl:
        return "behavioral_analysis"
    if "NON-CONSENSUS" in cl or "EFFECTS" in cl:
        return "idea_generation"
    if "TEMPORAL" in cl or "CONSTRAINT" in cl or "BOTTLENECK" in cl:
        return "thematic_analysis"
    if "CATALYST" in cl:
        return "thesis_analysis"
    if "FINANCIAL" in cl or "DUPONT" in cl or "EARNINGS" in cl:
        return "financial_analysis"
    if "DUE DILIGENCE" in cl or "RED FLAG" in cl or "MANAGEMENT" in cl:
        return "due_diligence"
    if "COMPETITIVE" in cl or "MOAT" in cl or "PORTER" in cl or "SEVEN" in cl or "POWER" in cl:
        return "competitive_analysis"
    if "SECTOR" in cl:
        return "sector_metrics"
    if "SCREENING" in cl or "DEFAULT" in cl:
        return "equity_analysis"
    return "general"


def _get_cached(workflow_type: str, stem: str, filepath: Path) -> Dict[str, Any]:
    """Return parsed framework, using cache if file hasn't changed."""
    key = (workflow_type, stem)
    mtime = filepath.stat().st_mtime
    cached = _cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    parsed = _parse_framework(filepath)
    _cache[key] = (mtime, parsed)
    return parsed


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_frameworks(workflow_type: str) -> List[Dict[str, Any]]:
    """List all frameworks for a workflow type (summaries only).

    Args:
        workflow_type: "ist" or "hfrt"

    Returns:
        List of dicts with name, displayName, description, category.
    """
    directory = _DIRS.get(workflow_type)
    if directory is None or not directory.exists():
        logger.warning("Framework directory not found for %s", workflow_type)
        return []

    summaries = []
    for filepath in sorted(directory.glob("*.md")):
        fw = _get_cached(workflow_type, filepath.stem, filepath)
        summaries.append({
            "name": fw["name"],
            "displayName": fw["displayName"],
            "description": fw["description"],
            "category": fw["category"],
        })
    return summaries


def get_framework(workflow_type: str, name: str) -> Optional[Dict[str, Any]]:
    """Get full detail for a single framework by name.

    Args:
        workflow_type: "ist" or "hfrt"
        name: Framework file stem (e.g. "scarcity_abundance")

    Returns:
        Full framework dict including content, or None if not found.
    """
    directory = _DIRS.get(workflow_type)
    if directory is None or not directory.exists():
        return None

    filepath = directory / f"{name}.md"
    if not filepath.exists():
        return None

    return _get_cached(workflow_type, name, filepath)


def get_framework_names(workflow_type: str) -> List[str]:
    """Return list of valid framework names for a workflow type."""
    directory = _DIRS.get(workflow_type)
    if directory is None or not directory.exists():
        return []
    return sorted(p.stem for p in directory.glob("*.md"))
