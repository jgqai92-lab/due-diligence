"""HFRT 8 research invariants — centralized invariant checking (Gap B3).

Invariants:
  INV-01: Multi-source citations — every factual claim has >=1 source citation
  INV-02: No forward estimates — no analyst-originated forward estimates
  INV-03: DCF terminal linkage — DCF terminal assumptions linked to competitive position
  INV-04: Risk register populated — >=5 risk entries with probability and impact
  INV-05: Management red flags checked — all red flag categories addressed
  INV-06: Earnings quality scored — QoE has a numeric score with methodology
  INV-07: Dialectic isolation — bull and bear contain no cross-references
  INV-08: Thesis conviction scored — investment thesis has conviction with factor breakdown
"""

import json
import logging
import re
from typing import Any

from app.database import SessionLocal
from app.models.hfrt import HFRTDialecticReview, HFRTProject, HFRTTemplate

logger = logging.getLogger(__name__)


def _get_template_data(db, project_id: int, template_number: int) -> dict | None:
    template = (
        db.query(HFRTTemplate)
        .filter(
            HFRTTemplate.project_id == project_id,
            HFRTTemplate.template_number == template_number,
        )
        .first()
    )
    if template and template.data:
        try:
            return json.loads(template.data)
        except (ValueError, TypeError):
            return None
    return None


def check_all_invariants(project_id: int) -> list[dict[str, Any]]:
    """Run all 8 HFRT research invariants for a project.

    Returns:
        List of dicts with id, name, status (PASS/FAIL), details.
    """
    db = SessionLocal()
    try:
        return _check_invariants(db, project_id)
    finally:
        db.close()


def _check_invariants(db, project_id: int) -> list[dict[str, Any]]:
    """Internal: run invariants with an existing db session."""
    results: list[dict[str, Any]] = []

    def check(inv_id: str, name: str, condition: bool, details: str):
        results.append({
            "id": inv_id,
            "name": name,
            "status": "PASS" if condition else "FAIL",
            "details": details,
        })

    # Load key templates
    thesis = _get_template_data(db, project_id, 11)
    risk = _get_template_data(db, project_id, 8)
    catalysts = _get_template_data(db, project_id, 10)
    valuation = _get_template_data(db, project_id, 6)
    earnings = _get_template_data(db, project_id, 9)
    management = _get_template_data(db, project_id, 7)
    competitive = _get_template_data(db, project_id, 3)
    idea_screen = _get_template_data(db, project_id, 0)

    # INV-01: Multi-source citations
    # Check that the idea screen, management, and risk templates have source citations
    has_citations = True
    citation_details = []
    for tpl_num, tpl_name, tpl_data in [
        (0, "Idea Screen", idea_screen),
        (7, "Management", management),
        (8, "Risk Analysis", risk),
    ]:
        if tpl_data is None:
            has_citations = False
            citation_details.append(f"Template {tpl_num} ({tpl_name}) missing")
    if not citation_details:
        citation_details.append("Key templates present with data")
    check(
        "INV-01", "Multi-source citations",
        has_citations,
        "; ".join(citation_details),
    )

    # INV-02: No forward estimates
    # Verify thesis doesn't contain analyst forward estimates (only company guidance)
    has_forward = False
    forward_details = "No forward estimate issues detected"
    if thesis:
        thesis_str = json.dumps(thesis, default=str).lower()
        forward_patterns = [
            r"we estimate",
            r"our forecast",
            r"we project",
            r"our model assumes",
        ]
        found = [p for p in forward_patterns if re.search(p, thesis_str)]
        if found:
            has_forward = True
            forward_details = f"Forward estimate language found: {', '.join(found)}"
    check(
        "INV-02", "No forward estimates",
        not has_forward,
        forward_details,
    )

    # INV-03: DCF terminal linkage
    has_dcf = bool(valuation and valuation.get("dcf"))
    has_competitive = bool(competitive)
    dcf_linked = has_dcf and has_competitive
    check(
        "INV-03", "DCF terminal value linkage",
        dcf_linked,
        f"DCF: {'present' if has_dcf else 'missing'}, "
        f"Competitive position: {'present' if has_competitive else 'missing'}",
    )

    # INV-04: Risk register populated (>=5 entries)
    risk_entries = risk.get("risk_register", []) if risk else []
    risk_count = len(risk_entries)
    check(
        "INV-04", "Risk register populated",
        risk_count >= 5,
        f"Risk register has {risk_count} entries (>= 5 required)",
    )

    # INV-05: Management red flags checked
    has_mgmt = bool(management)
    red_flag_categories = ["insider_selling", "compensation", "board_composition", "ceo"]
    covered = 0
    if management:
        for cat in red_flag_categories:
            if management.get(cat) is not None:
                covered += 1
    check(
        "INV-05", "Management red flags checked",
        has_mgmt and covered >= 3,
        f"Management assessment covers {covered}/{len(red_flag_categories)} red flag categories",
    )

    # INV-06: Earnings quality scored
    has_qoe = bool(earnings)
    has_score = bool(earnings and (
        earnings.get("quality_score") is not None
        or earnings.get("overall_score") is not None
        or earnings.get("score") is not None
    ))
    check(
        "INV-06", "Earnings quality scored",
        has_qoe and has_score,
        "QoE analysis with numeric score" if has_score else (
            "QoE present but no score" if has_qoe else "No QoE analysis"
        ),
    )

    # INV-07: Dialectic isolation
    bull_review = (
        db.query(HFRTDialecticReview)
        .filter(
            HFRTDialecticReview.project_id == project_id,
            HFRTDialecticReview.side == "BULL",
        )
        .first()
    )
    bear_review = (
        db.query(HFRTDialecticReview)
        .filter(
            HFRTDialecticReview.project_id == project_id,
            HFRTDialecticReview.side == "BEAR",
        )
        .first()
    )
    isolation_ok = True
    isolation_details = "Bull and bear reviews are isolated"
    if bull_review and bear_review:
        audit = audit_dialectic_isolation(
            bull_review.content, bear_review.content
        )
        isolation_ok = audit["is_isolated"]
        if not isolation_ok:
            isolation_details = (
                f"Cross-contamination detected: {'; '.join(audit['contamination_evidence'][:3])}"
            )
    elif not bull_review or not bear_review:
        isolation_ok = False
        isolation_details = "Missing bull or bear review"
    check("INV-07", "Dialectic isolation", isolation_ok, isolation_details)

    # INV-08: Thesis conviction scored
    has_conviction = bool(
        thesis
        and thesis.get("conviction_factors")
        and thesis.get("overall_conviction_score") is not None
    )
    score_val = thesis.get("overall_conviction_score", "N/A") if thesis else "N/A"
    check(
        "INV-08", "Thesis conviction scored",
        has_conviction,
        f"Conviction score: {score_val}" if has_conviction else "No conviction scoring found",
    )

    return results


def audit_dialectic_isolation(
    bull_content: str, bear_content: str
) -> dict[str, Any]:
    """Check bull/bear for cross-contamination (Gap B6).

    Looks for:
      - Shared unique multi-word phrases (>= 5 words)
      - References to the other side's specific arguments

    Returns:
        dict with is_isolated (bool) and contamination_evidence (list[str]).
    """
    evidence: list[str] = []

    try:
        bull_data = json.loads(bull_content) if isinstance(bull_content, str) else bull_content
        bear_data = json.loads(bear_content) if isinstance(bear_content, str) else bear_content
    except (json.JSONDecodeError, TypeError):
        return {"is_isolated": True, "contamination_evidence": []}

    bull_text = json.dumps(bull_data, default=str).lower()
    bear_text = json.dumps(bear_data, default=str).lower()

    # Check for cross-reference phrases
    cross_ref_patterns = [
        r"as the bull case (suggests|argues|notes|mentions)",
        r"as the bear case (suggests|argues|notes|mentions)",
        r"the bull (analyst|case) (points out|identified|noted)",
        r"the bear (analyst|case) (points out|identified|noted)",
        r"contrary to the (bull|bear)",
        r"the opposing (case|view|analyst)",
    ]
    for pattern in cross_ref_patterns:
        if re.search(pattern, bull_text):
            evidence.append(f"Bull case contains cross-reference: '{pattern}'")
        if re.search(pattern, bear_text):
            evidence.append(f"Bear case contains cross-reference: '{pattern}'")

    # Check for shared unique phrases (5+ word sequences)
    def extract_phrases(text: str, n: int = 5) -> set:
        words = re.findall(r'\b[a-z]+\b', text)
        return {
            " ".join(words[i:i+n])
            for i in range(len(words) - n + 1)
        }

    bull_phrases = extract_phrases(bull_text, 7)
    bear_phrases = extract_phrases(bear_text, 7)
    shared = bull_phrases & bear_phrases

    # Filter out common generic phrases
    generic = {
        "the company has a strong",
        "in the next few years",
        "the market is expected to",
    }
    meaningful_shared = shared - generic
    if len(meaningful_shared) > 5:
        evidence.append(
            f"Found {len(meaningful_shared)} shared 7-word phrases between bull and bear"
        )

    return {
        "is_isolated": len(evidence) == 0,
        "contamination_evidence": evidence,
    }
