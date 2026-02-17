"""HFRT citation validation — checks that factual claims have source citations (Gap B5).

Scans template content for citation markers and verifies they are referenced.
Pattern matching only, not web verification.
"""

import json
import logging
import re
from typing import Any

from app.database import SessionLocal
from app.models.hfrt import HFRTTemplate

logger = logging.getLogger(__name__)

# Citation patterns: [Source: ...], [1], (Source: ...), etc.
CITATION_PATTERNS = [
    r'\[source:?\s*[^\]]+\]',
    r'\[\d+\]',
    r'\(source:?\s*[^\)]+\)',
    r'(?:per|according to|from)\s+(?:the\s+)?(?:10-K|10-Q|DEF\s*14A|proxy|annual report|SEC filing)',
    r'(?:yfinance|yahoo finance|sec\.gov|edgar)',
]

# Claim patterns: sentences that contain quantitative assertions
CLAIM_PATTERNS = [
    r'\$[\d,.]+\s*(?:billion|million|B|M|bn|mn)',
    r'(?:revenue|earnings|EBITDA|EPS|margin|growth)\s+(?:of|was|is|at)\s+[\d,.]+%?',
    r'(?:increased|decreased|grew|fell|rose|declined)\s+(?:by\s+)?[\d,.]+%',
    r'(?:market\s+(?:cap|share)|P/?E\s+(?:ratio|of))\s+(?:of\s+)?[\d,.]+',
]


def validate_citations(
    project_id: int, template_number: int
) -> dict[str, Any]:
    """Validate citations for a specific HFRT template.

    Scans the template content for factual claims (quantitative assertions)
    and checks whether they have nearby citation markers.

    Returns:
        dict with total_claims, cited_claims, uncited_claims list, coverage_pct.
    """
    db = SessionLocal()
    try:
        template = (
            db.query(HFRTTemplate)
            .filter(
                HFRTTemplate.project_id == project_id,
                HFRTTemplate.template_number == template_number,
            )
            .first()
        )
        if not template or not template.data:
            return {
                "total_claims": 0,
                "cited_claims": 0,
                "uncited_claims": [],
                "coverage_pct": 0,
                "error": f"Template {template_number} has no data",
            }

        try:
            data = json.loads(template.data)
        except (json.JSONDecodeError, TypeError):
            return {
                "total_claims": 0,
                "cited_claims": 0,
                "uncited_claims": [],
                "coverage_pct": 0,
                "error": "Template data is not valid JSON",
            }

        # Flatten all text content from the template
        text = _flatten_text(data)

        # Find all quantitative claims
        claims = _find_claims(text)

        # Check each claim for nearby citations
        cited = 0
        uncited = []
        for claim in claims:
            if _has_nearby_citation(text, claim):
                cited += 1
            else:
                uncited.append(claim)

        total = len(claims)
        coverage = (cited / total * 100) if total > 0 else 100.0

        return {
            "total_claims": total,
            "cited_claims": cited,
            "uncited_claims": uncited[:20],  # Cap at 20 for response size
            "coverage_pct": round(coverage, 1),
        }
    finally:
        db.close()


def _flatten_text(data: Any, depth: int = 0) -> str:
    """Recursively extract all text from a JSON structure."""
    if depth > 10:
        return ""
    if isinstance(data, str):
        return data + "\n"
    if isinstance(data, list):
        return "\n".join(_flatten_text(item, depth + 1) for item in data)
    if isinstance(data, dict):
        return "\n".join(_flatten_text(v, depth + 1) for v in data.values())
    return str(data) if data is not None else ""


def _find_claims(text: str) -> list[str]:
    """Find quantitative claims in text."""
    claims = []
    sentences = re.split(r'[.!?\n]', text)
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 15:
            continue
        for pattern in CLAIM_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                claims.append(sentence[:200])  # Truncate long claims
                break
    return claims


def _has_nearby_citation(text: str, claim: str) -> bool:
    """Check if a claim has a citation marker within 200 chars."""
    idx = text.find(claim[:50])
    if idx < 0:
        return False

    # Search in a window around the claim
    start = max(0, idx - 100)
    end = min(len(text), idx + len(claim) + 200)
    window = text[start:end].lower()

    for pattern in CITATION_PATTERNS:
        if re.search(pattern, window, re.IGNORECASE):
            return True
    return False
