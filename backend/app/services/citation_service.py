"""Citation generation — ensures every metric has a verifiable source trail."""

from app.schemas.analysis import ForensicMetrics


def validate_citations(metrics: ForensicMetrics) -> list[str]:
    """Check that all computed metrics have valid citations. Returns list of issues."""
    issues = []

    # Check M-Score components
    m = metrics.beneish_m_score
    for name in ["dsri", "gmi", "aqi", "sgi", "depi", "sgai", "lvgi", "tata"]:
        comp = getattr(m.components, name)
        if comp.value is not None and not comp.citation.source:
            issues.append(f"M-Score {name.upper()} has value but no citation source")

    # Check Z-Score components
    for variant_name in ["standard", "saas_modified"]:
        variant = getattr(metrics.altman_z_score, variant_name)
        for key, comp in variant.components.items():
            if comp.value is not None and not comp.citation.source:
                issues.append(f"Z-Score {variant_name}.{key} has value but no citation source")

    # Check Rule of 40
    r40 = metrics.rule_of_40
    if r40.score is not None and not r40.citations:
        issues.append("Rule of 40 has score but no citations")

    # Check Magic Number
    mn = metrics.magic_number
    if mn.score is not None and not mn.citations:
        issues.append("Magic Number has score but no citations")

    return issues
