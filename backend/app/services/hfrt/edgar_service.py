"""SEC EDGAR filing fetcher using edgartools.

Provides:
  - fetch_10k, fetch_10q, fetch_proxy for specific filing types
  - extract_filing_sections for structured section extraction
  - Content hash dedup and rate limiting (100ms between requests)

Caches filings in hfrt_sec_filings table.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Optional

from app.config import settings
from app.database import SessionLocal
from app.models.hfrt import HFRTSECFiling

logger = logging.getLogger(__name__)

# Rate limiting: minimum 100ms between SEC requests
_last_request_time: float = 0.0
_RATE_LIMIT_MS = 100


def _rate_limit():
    """Enforce SEC EDGAR rate limit (10 req/sec max)."""
    global _last_request_time
    now = time.time()
    elapsed_ms = (now - _last_request_time) * 1000
    if elapsed_ms < _RATE_LIMIT_MS:
        time.sleep((_RATE_LIMIT_MS - elapsed_ms) / 1000)
    _last_request_time = time.time()


def _content_hash(content: str) -> str:
    """Generate SHA-256 hash for dedup."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _check_cache(db, ticker: str, filing_type: str) -> HFRTSECFiling | None:
    """Check if we already have this filing cached."""
    return (
        db.query(HFRTSECFiling)
        .filter(
            HFRTSECFiling.ticker == ticker.upper(),
            HFRTSECFiling.filing_type == filing_type,
        )
        .order_by(HFRTSECFiling.fetched_at.desc())
        .first()
    )


def fetch_filing(
    ticker: str,
    filing_type: str,
    project_id: int,
) -> dict[str, Any]:
    """Fetch a filing from SEC EDGAR via edgartools.

    Returns dict with filing metadata and content.
    Uses cache dedup via content_hash.
    """
    try:
        from edgar import Company

        _rate_limit()

        company = Company(ticker.upper())
        filings = company.get_filings(form=filing_type)

        if filings is None or len(filings) == 0:
            return {
                "success": False,
                "error": f"No {filing_type} filings found for {ticker}",
                "filing_type": filing_type,
            }

        # Get the most recent filing
        latest = filings[0]

        # Extract key info
        filing_date = str(latest.filing_date) if hasattr(latest, "filing_date") else None
        accession_number = str(latest.accession_number) if hasattr(latest, "accession_number") else None

        _rate_limit()

        # Get the filing text content
        try:
            content = str(latest.text())[:500000]  # Limit to 500K chars
        except Exception:
            content = str(latest)[:100000]

        content_h = _content_hash(content)

        # Check if this exact content is already cached
        db = SessionLocal()
        try:
            existing = (
                db.query(HFRTSECFiling)
                .filter(HFRTSECFiling.content_hash == content_h)
                .first()
            )
            if existing:
                logger.info("Cache hit for %s %s (hash match)", ticker, filing_type)
                return {
                    "success": True,
                    "cached": True,
                    "filing_id": existing.id,
                    "filing_type": filing_type,
                    "filing_date": existing.filing_date,
                    "content_length": len(existing.content or ""),
                }

            # Save new filing
            filing_record = HFRTSECFiling(
                project_id=project_id,
                ticker=ticker.upper(),
                filing_type=filing_type,
                filing_date=filing_date,
                accession_number=accession_number,
                content_hash=content_h,
                content=content,
                url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type={filing_type}",
            )
            db.add(filing_record)
            db.commit()
            db.refresh(filing_record)

            return {
                "success": True,
                "cached": False,
                "filing_id": filing_record.id,
                "filing_type": filing_type,
                "filing_date": filing_date,
                "content_length": len(content),
            }
        finally:
            db.close()

    except ImportError:
        logger.warning("edgartools not installed — skipping SEC filing fetch")
        return {
            "success": False,
            "error": "edgartools not installed. Install with: pip install edgartools",
            "filing_type": filing_type,
        }
    except Exception as e:
        logger.error("Failed to fetch %s for %s: %s", filing_type, ticker, e)
        return {
            "success": False,
            "error": str(e)[:500],
            "filing_type": filing_type,
        }


def get_filing_content(
    project_id: int,
    filing_type: str,
    max_chars: int = 50000,
) -> str | None:
    """Retrieve cached filing content for a project."""
    db = SessionLocal()
    try:
        filing = (
            db.query(HFRTSECFiling)
            .filter(
                HFRTSECFiling.project_id == project_id,
                HFRTSECFiling.filing_type == filing_type,
            )
            .order_by(HFRTSECFiling.fetched_at.desc())
            .first()
        )
        if filing and filing.content:
            return filing.content[:max_chars]
        return None
    finally:
        db.close()


def extract_filing_sections(content: str) -> dict[str, str]:
    """Extract key sections from a 10-K or 10-Q filing.

    Looks for common section headers (Item 1, Item 7, etc.) and
    extracts content between them.
    """
    sections = {}
    section_markers = [
        ("Item 1.", "Business", "business"),
        ("Item 1A.", "Risk Factors", "risk_factors"),
        ("Item 2.", "Properties", "properties"),
        ("Item 7.", "Management's Discussion", "md_and_a"),
        ("Item 7A.", "Quantitative and Qualitative", "market_risk"),
        ("Item 8.", "Financial Statements", "financial_statements"),
    ]

    content_upper = content.upper()
    for marker, label, key in section_markers:
        marker_upper = marker.upper()
        pos = content_upper.find(marker_upper)
        if pos != -1:
            # Find next section marker or take up to 20K chars
            end_pos = len(content)
            for other_marker, _, _ in section_markers:
                other_upper = other_marker.upper()
                other_pos = content_upper.find(other_upper, pos + len(marker))
                if other_pos != -1 and other_pos < end_pos:
                    end_pos = other_pos
            sections[key] = content[pos:min(pos + 20000, end_pos)].strip()

    return sections
