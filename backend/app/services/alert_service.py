"""Alert generation service -- creates alerts from comprehensive analysis metrics.

Checks computed metrics against defined thresholds and creates Alert records
when trigger conditions are met. Handles null values gracefully by skipping
any check where the required metric is missing.

Alert types:
  Existing (forensic):
    - m_score_warning       : Beneish M-Score above manipulation threshold
    - z_score_distress      : Altman Z-Score in distress zone
    - z_score_zone_change   : Altman Z-Score zone changed from prior analysis
    - rule_of_40_fail       : SaaS Rule of 40 score below 40
    - magic_number_low      : SaaS Magic Number below 0.5

  New (comprehensive, Wave 5):
    - profitability_decline  : Net margin drops >500bps YoY
    - leverage_warning       : D/E exceeds 3.0x OR net debt/EBITDA >5x
    - cash_flow_quality      : OCF/NI ratio <0.5
    - valuation_extreme      : P/E >50 or negative P/E
    - short_interest_spike   : Short % of float >20%
"""

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.alerts import Alert
from app.models.alert_settings import AlertSettings
from app.schemas.analysis import ComprehensiveAnalysis

logger = logging.getLogger(__name__)


# ─── Threshold constants ────────────────────────────────────────────

PROFITABILITY_MARGIN_DROP_BPS = 500  # 500 basis points = 5 percentage points
LEVERAGE_DE_THRESHOLD = 3.0          # Debt-to-Equity ratio
LEVERAGE_NET_DEBT_EBITDA_THRESHOLD = 5.0  # Net Debt / EBITDA
CASH_FLOW_OCF_NI_THRESHOLD = 0.5    # OCF / Net Income ratio
VALUATION_PE_HIGH_THRESHOLD = 50.0   # Trailing P/E
SHORT_INTEREST_THRESHOLD = 0.20      # 20% of float


# ─── Helper ─────────────────────────────────────────────────────────


def _create_alert(
    ticker: str,
    alert_type: str,
    severity: str,
    message: str,
    current_value: float | None = None,
    previous_value: float | None = None,
    details: dict | None = None,
) -> Alert:
    """Build an Alert model instance (not yet committed)."""
    return Alert(
        ticker=ticker.upper(),
        alert_type=alert_type,
        severity=severity,
        message=message,
        current_value=current_value,
        previous_value=previous_value,
        details=json.dumps(details) if details else None,
        is_dismissed=0,
        created_at=datetime.utcnow(),
    )


def _get_metric_value(metric_component) -> float | None:
    """Safely extract the numeric value from a MetricComponent."""
    if metric_component is None:
        return None
    return metric_component.value


def _should_create_alert(db: Session | None, ticker: str, alert_type: str) -> bool:
    """Check if a similar undismissed alert exists within the last 24 hours.

    Returns True if no recent duplicate exists (meaning we should create a new one).
    Always returns True when no database session is available (in-memory mode).
    """
    if db is None:
        return True  # No DB, always create (in-memory mode)

    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        existing = db.query(Alert).filter(
            Alert.ticker == ticker.upper(),
            Alert.alert_type == alert_type,
            Alert.is_dismissed == 0,
            Alert.created_at >= cutoff,
        ).first()
        return existing is None  # Create only if no recent duplicate
    except Exception as e:
        logger.warning("Deduplication check failed for %s/%s: %s", ticker, alert_type, e)
        return True  # On error, allow creation to avoid silently swallowing alerts


# ─── Individual alert checks ────────────────────────────────────────


def _check_profitability_decline(
    analysis: ComprehensiveAnalysis,
    ticker: str,
) -> Alert | None:
    """Check if net margin dropped more than 500bps YoY.

    Uses the growth metrics to assess YoY change in net margin. Since net_margin
    is a current-period snapshot, we compare current net margin to an implied
    prior-period net margin using earnings growth and revenue growth as proxies.

    More precisely: if net_margin (current) and the profitability data from the
    prior period are available, we compute the drop. The comprehensive analysis
    stores current net_margin. We compare against a computed prior net_margin
    derived from financial statement data when available through growth metrics.

    Simplified approach: use net_margin.value and revenue/earnings growth to
    infer prior margin. If net margin < 0 and earnings growth is very negative,
    or if we have explicit prior margin info, trigger the alert.

    Actually, the best approach with the available data: the general_metrics_engine
    computes net_margin for the current period. We can also check earnings_growth_yoy.
    A large negative earnings growth with a low current margin suggests decline.

    For a clean implementation, we check:
    - Current net margin vs implied prior net margin
    - Prior net margin = current net margin / (1 + earnings_growth_yoy) * (1 + revenue_growth_yoy)
      (this is approximate; exact requires raw data)

    Simplest reliable check: if we have both current net margin and the computed
    growth rates, we can estimate the drop.
    """
    current_margin = _get_metric_value(analysis.profitability.net_margin)
    rev_growth = _get_metric_value(analysis.growth.revenue_growth_yoy)
    earn_growth = _get_metric_value(analysis.growth.earnings_growth_yoy)

    if current_margin is None:
        return None

    # If we have both revenue growth and earnings growth, we can estimate prior margin.
    # Prior Net Income = Current NI / (1 + earn_growth)
    # Prior Revenue = Current Rev / (1 + rev_growth)
    # Prior margin = Prior NI / Prior Rev = (Current NI / (1 + earn_growth)) / (Current Rev / (1 + rev_growth))
    #              = current_margin * (1 + rev_growth) / (1 + earn_growth)
    if rev_growth is not None and earn_growth is not None:
        # Reject unreasonable growth rates that would produce nonsensical results
        # >500% growth is unreasonable for margin estimation
        if abs(rev_growth) > 5.0 or abs(earn_growth) > 5.0:
            return None  # Skip alert — data too extreme for reliable estimation

        # Avoid division by zero or nonsensical values
        if (1 + earn_growth) <= 0 or (1 + rev_growth) <= 0:
            # Can't reliably estimate prior margin with extreme growth values
            return None

        prior_margin = current_margin * (1 + rev_growth) / (1 + earn_growth)
        margin_drop_bps = (prior_margin - current_margin) * 10000  # Convert to basis points

        if margin_drop_bps > PROFITABILITY_MARGIN_DROP_BPS:
            return _create_alert(
                ticker=ticker,
                alert_type="profitability_decline",
                severity="warning",
                message=(
                    f"Net margin declined ~{margin_drop_bps:.0f} bps YoY "
                    f"(estimated prior: {prior_margin:.1%}, current: {current_margin:.1%}). "
                    f"Investigate margin compression drivers."
                ),
                current_value=round(current_margin, 4),
                previous_value=round(prior_margin, 4),
                details={
                    "margin_drop_bps": round(margin_drop_bps, 0),
                    "current_net_margin": round(current_margin, 4),
                    "estimated_prior_net_margin": round(prior_margin, 4),
                    "revenue_growth_yoy": round(rev_growth, 4),
                    "earnings_growth_yoy": round(earn_growth, 4),
                },
            )

    return None


def _check_leverage_warning(
    analysis: ComprehensiveAnalysis,
    ticker: str,
) -> Alert | None:
    """Check if D/E exceeds 3.0x OR net debt/EBITDA exceeds 5x."""
    de_ratio = _get_metric_value(analysis.leverage.debt_to_equity)
    nd_ebitda = _get_metric_value(analysis.leverage.net_debt_to_ebitda)

    triggers = []
    primary_value = None

    if de_ratio is not None and de_ratio > LEVERAGE_DE_THRESHOLD:
        triggers.append(f"Debt/Equity ratio of {de_ratio:.2f}x exceeds {LEVERAGE_DE_THRESHOLD:.1f}x threshold")
        primary_value = de_ratio

    if nd_ebitda is not None and nd_ebitda > LEVERAGE_NET_DEBT_EBITDA_THRESHOLD:
        triggers.append(f"Net Debt/EBITDA of {nd_ebitda:.2f}x exceeds {LEVERAGE_NET_DEBT_EBITDA_THRESHOLD:.1f}x threshold")
        if primary_value is None:
            primary_value = nd_ebitda

    if not triggers:
        return None

    message = "Elevated leverage detected: " + "; ".join(triggers) + ". Review debt sustainability."

    return _create_alert(
        ticker=ticker,
        alert_type="leverage_warning",
        severity="critical",
        message=message,
        current_value=primary_value,
        details={
            "debt_to_equity": round(de_ratio, 4) if de_ratio is not None else None,
            "net_debt_to_ebitda": round(nd_ebitda, 4) if nd_ebitda is not None else None,
            "de_threshold": LEVERAGE_DE_THRESHOLD,
            "nd_ebitda_threshold": LEVERAGE_NET_DEBT_EBITDA_THRESHOLD,
        },
    )


def _check_cash_flow_quality(
    analysis: ComprehensiveAnalysis,
    ticker: str,
) -> Alert | None:
    """Check if OCF/NI ratio is below 0.5, indicating earnings quality concern."""
    ocf_ni = _get_metric_value(analysis.cash_flow.ocf_to_net_income)

    if ocf_ni is None:
        return None

    # Only trigger for positive net income situations where OCF is disproportionately low.
    # A negative OCF/NI could mean the company has negative NI (loss-making), which
    # is a different concern. We trigger when OCF/NI is positive but low (< 0.5)
    # OR when OCF/NI is negative (meaning OCF and NI have opposite signs).
    if ocf_ni < CASH_FLOW_OCF_NI_THRESHOLD:
        if ocf_ni < 0:
            detail_msg = (
                f"OCF/Net Income ratio is {ocf_ni:.2f} (negative), indicating operating cash flow "
                f"and net income have opposite signs. Significant earnings quality concern."
            )
        else:
            detail_msg = (
                f"OCF/Net Income ratio of {ocf_ni:.2f} is below {CASH_FLOW_OCF_NI_THRESHOLD} threshold. "
                f"Low cash conversion suggests potential accruals-based earnings. "
                f"Investigate working capital changes and non-cash items."
            )

        return _create_alert(
            ticker=ticker,
            alert_type="cash_flow_quality",
            severity="warning",
            message=detail_msg,
            current_value=round(ocf_ni, 4),
            details={
                "ocf_to_net_income": round(ocf_ni, 4),
                "threshold": CASH_FLOW_OCF_NI_THRESHOLD,
            },
        )

    return None


def _check_valuation_extreme(
    analysis: ComprehensiveAnalysis,
    ticker: str,
) -> Alert | None:
    """Check if P/E > 50 or negative P/E (loss-making)."""
    pe = _get_metric_value(analysis.valuation.pe_trailing)

    if pe is None:
        return None

    if pe < 0:
        return _create_alert(
            ticker=ticker,
            alert_type="valuation_extreme",
            severity="info",
            message=(
                f"Trailing P/E is negative ({pe:.2f}), indicating the company is currently "
                f"loss-making. Traditional P/E valuation is not meaningful; consider "
                f"EV/Revenue or forward P/E instead."
            ),
            current_value=round(pe, 2),
            details={
                "pe_trailing": round(pe, 2),
                "pe_forward": round(_get_metric_value(analysis.valuation.pe_forward), 2)
                if _get_metric_value(analysis.valuation.pe_forward) is not None
                else None,
                "reason": "negative_pe",
            },
        )

    if pe > VALUATION_PE_HIGH_THRESHOLD:
        return _create_alert(
            ticker=ticker,
            alert_type="valuation_extreme",
            severity="info",
            message=(
                f"Trailing P/E of {pe:.1f}x exceeds {VALUATION_PE_HIGH_THRESHOLD:.0f}x. "
                f"Elevated valuation may reflect high growth expectations or speculative premium. "
                f"Verify forward earnings estimates support the multiple."
            ),
            current_value=round(pe, 2),
            details={
                "pe_trailing": round(pe, 2),
                "pe_forward": round(_get_metric_value(analysis.valuation.pe_forward), 2)
                if _get_metric_value(analysis.valuation.pe_forward) is not None
                else None,
                "threshold": VALUATION_PE_HIGH_THRESHOLD,
                "reason": "high_pe",
            },
        )

    return None


def _check_short_interest_spike(
    analysis: ComprehensiveAnalysis,
    ticker: str,
) -> Alert | None:
    """Check if short % of float exceeds 20%."""
    short_pct = _get_metric_value(analysis.sentiment.short_percent_float)

    if short_pct is None:
        return None

    if short_pct > SHORT_INTEREST_THRESHOLD:
        pct_display = short_pct * 100 if short_pct <= 1.0 else short_pct
        threshold_display = SHORT_INTEREST_THRESHOLD * 100

        return _create_alert(
            ticker=ticker,
            alert_type="short_interest_spike",
            severity="warning",
            message=(
                f"Short interest is {pct_display:.1f}% of float, exceeding {threshold_display:.0f}% threshold. "
                f"Elevated short interest may indicate bearish sentiment or potential short squeeze dynamics. "
                f"Review fundamental thesis carefully."
            ),
            current_value=round(short_pct, 4),
            details={
                "short_percent_float": round(short_pct, 4),
                "short_ratio": round(_get_metric_value(analysis.sentiment.short_ratio), 2)
                if _get_metric_value(analysis.sentiment.short_ratio) is not None
                else None,
                "threshold": SHORT_INTEREST_THRESHOLD,
            },
        )

    return None


# ─── Existing forensic alert checks ────────────────────────────────


def _check_m_score_warning(
    analysis: ComprehensiveAnalysis,
    ticker: str,
    threshold: float = -1.78,
) -> Alert | None:
    """Check if Beneish M-Score exceeds manipulation threshold."""
    m_score = analysis.beneish_m_score.composite
    interpretation = analysis.beneish_m_score.interpretation

    if m_score is None:
        return None

    if m_score > threshold:
        return _create_alert(
            ticker=ticker,
            alert_type="m_score_warning",
            severity="warning" if interpretation == "GREY_ZONE" else "critical",
            message=(
                f"Beneish M-Score of {m_score:.2f} exceeds {threshold} threshold "
                f"({interpretation or 'UNKNOWN'}). Elevated risk of earnings manipulation."
            ),
            current_value=round(m_score, 4),
            details={
                "m_score": round(m_score, 4),
                "interpretation": interpretation,
                "threshold": threshold,
            },
        )

    return None


def _check_z_score_distress(
    analysis: ComprehensiveAnalysis,
    ticker: str,
) -> Alert | None:
    """Check if Altman Z-Score is in distress zone."""
    z_score = analysis.altman_z_score.standard.score
    zone = analysis.altman_z_score.standard.zone

    if z_score is None or zone is None:
        return None

    if zone == "DISTRESS":
        return _create_alert(
            ticker=ticker,
            alert_type="z_score_distress",
            severity="critical",
            message=(
                f"Altman Z-Score of {z_score:.2f} indicates financial distress "
                f"(below 1.81 threshold). Elevated bankruptcy risk."
            ),
            current_value=round(z_score, 4),
            details={
                "z_score": round(z_score, 4),
                "zone": zone,
            },
        )

    return None


def _check_rule_of_40(
    analysis: ComprehensiveAnalysis,
    ticker: str,
) -> Alert | None:
    """Check if Rule of 40 score is failing (for SaaS companies)."""
    if analysis.sector_specific is None:
        return None
    if analysis.sector_category != "SAAS":
        return None

    r40_metric = analysis.sector_specific.metrics.get("rule_of_40")
    if r40_metric is None or r40_metric.value is None:
        return None

    score = r40_metric.value
    if score < 40:
        return _create_alert(
            ticker=ticker,
            alert_type="rule_of_40_fail",
            severity="warning",
            message=(
                f"Rule of 40 score of {score:.1f} is below 40 threshold. "
                f"SaaS efficiency benchmark not met."
            ),
            current_value=round(score, 2),
            details={
                "rule_of_40_score": round(score, 2),
                "interpretation": analysis.sector_specific.interpretations.get("rule_of_40"),
            },
        )

    return None


def _check_magic_number(
    analysis: ComprehensiveAnalysis,
    ticker: str,
) -> Alert | None:
    """Check if Magic Number is below 0.5 (for SaaS companies)."""
    if analysis.sector_specific is None:
        return None
    if analysis.sector_category != "SAAS":
        return None

    mn_metric = analysis.sector_specific.metrics.get("magic_number")
    if mn_metric is None or mn_metric.value is None:
        return None

    score = mn_metric.value
    if score < 0.5:
        return _create_alert(
            ticker=ticker,
            alert_type="magic_number_low",
            severity="info",
            message=(
                f"Magic Number of {score:.2f} is below 0.5 threshold. "
                f"Sales & marketing spend efficiency is low."
            ),
            current_value=round(score, 4),
            details={
                "magic_number": round(score, 4),
                "interpretation": analysis.sector_specific.interpretations.get("magic_number"),
            },
        )

    return None


# ─── Main orchestration ─────────────────────────────────────────────


def generate_comprehensive_alerts(
    comprehensive_analysis: ComprehensiveAnalysis,
    ticker: str,
    db: Session | None = None,
    settings: AlertSettings | None = None,
) -> list[Alert]:
    """Generate alerts from comprehensive analysis metrics.

    Checks all trigger conditions against the computed metrics and creates
    Alert records. Respects AlertSettings toggles when available.

    Args:
        comprehensive_analysis: The computed comprehensive analysis with all metrics.
        ticker: Stock ticker symbol.
        db: Optional database session. If provided, alerts are persisted.
        settings: Optional AlertSettings. If not provided and db is given,
                  settings are loaded from the database.

    Returns:
        List of generated Alert objects.
    """
    ticker = ticker.upper()

    # Load settings if not provided
    if settings is None and db is not None:
        settings = db.query(AlertSettings).filter(AlertSettings.id == 1).first()

    # Get M-Score threshold from settings (default -1.78)
    m_score_threshold = settings.m_score_threshold if settings else -1.78

    # Build list of (check_function, settings_toggle_attr) pairs
    checks = [
        # Existing forensic alerts
        (
            lambda: _check_m_score_warning(comprehensive_analysis, ticker, m_score_threshold),
            "enable_m_score_alerts",
        ),
        (
            lambda: _check_z_score_distress(comprehensive_analysis, ticker),
            "enable_z_score_alerts",
        ),
        (
            lambda: _check_rule_of_40(comprehensive_analysis, ticker),
            "enable_rule_of_40_alerts",
        ),
        (
            lambda: _check_magic_number(comprehensive_analysis, ticker),
            "enable_magic_number_alerts",
        ),
        # New comprehensive alerts (Wave 5)
        (
            lambda: _check_profitability_decline(comprehensive_analysis, ticker),
            "enable_profitability_alerts",
        ),
        (
            lambda: _check_leverage_warning(comprehensive_analysis, ticker),
            "enable_leverage_alerts",
        ),
        (
            lambda: _check_cash_flow_quality(comprehensive_analysis, ticker),
            "enable_cash_flow_alerts",
        ),
        (
            lambda: _check_valuation_extreme(comprehensive_analysis, ticker),
            "enable_valuation_alerts",
        ),
        (
            lambda: _check_short_interest_spike(comprehensive_analysis, ticker),
            "enable_short_interest_alerts",
        ),
    ]

    alerts: list[Alert] = []

    for check_fn, toggle_attr in checks:
        # Check if this alert type is enabled in settings
        if settings is not None:
            enabled = getattr(settings, toggle_attr, 1)
            if not enabled:
                continue

        try:
            alert = check_fn()
            if alert is not None:
                # Deduplication: skip if a similar undismissed alert
                # already exists within the last 24 hours
                if _should_create_alert(db, ticker, alert.alert_type):
                    alerts.append(alert)
                else:
                    logger.debug(
                        "Skipping duplicate alert %s for %s",
                        alert.alert_type,
                        ticker,
                    )
        except Exception as e:
            logger.error(
                "Error generating alert (type toggle: %s) for %s: %s",
                toggle_attr,
                ticker,
                e,
            )

    # Persist alerts if database session is provided
    if db is not None and alerts:
        try:
            for alert in alerts:
                db.add(alert)
            db.commit()
            logger.info("Generated %d alerts for %s", len(alerts), ticker)
        except Exception as e:
            logger.error("Failed to persist alerts for %s: %s", ticker, e)
            db.rollback()

    return alerts
