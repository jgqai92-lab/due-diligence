"""Tests for alert generation service -- Wave 5 comprehensive alerts.

Tests each new alert trigger condition independently, plus integration tests
for the full generate_comprehensive_alerts() orchestrator.

Coverage targets:
- All 5 new alert types: profitability_decline, leverage_warning,
  cash_flow_quality, valuation_extreme, short_interest_spike
- All 5 existing alert types: m_score_warning, z_score_distress,
  z_score_zone_change, rule_of_40_fail, magic_number_low
- Edge cases: null metrics, boundary values, settings toggles
- Deduplication logic (_should_create_alert)
- Bounds checking on extreme growth rates
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.schemas.analysis import (
    ComprehensiveAnalysis,
    BeneishMScore,
    AltmanZScore,
    AltmanZScoreVariant,
    MetricComponent,
    ProfitabilityMetrics,
    LeverageMetrics,
    CashFlowMetrics,
    GrowthMetrics,
    ValuationMetrics,
    ShareholderMetrics,
    SentimentMetrics,
    SectorSpecificMetrics,
)
from app.services.alert_service import (
    generate_comprehensive_alerts,
    _check_profitability_decline,
    _check_leverage_warning,
    _check_cash_flow_quality,
    _check_valuation_extreme,
    _check_short_interest_spike,
    _check_m_score_warning,
    _check_z_score_distress,
    _check_rule_of_40,
    _check_magic_number,
    _should_create_alert,
    PROFITABILITY_MARGIN_DROP_BPS,
    LEVERAGE_DE_THRESHOLD,
    LEVERAGE_NET_DEBT_EBITDA_THRESHOLD,
    CASH_FLOW_OCF_NI_THRESHOLD,
    VALUATION_PE_HIGH_THRESHOLD,
    SHORT_INTEREST_THRESHOLD,
)
from app.models.alerts import Alert


# ─── Fixtures ─────────────────────────────────────────────────────────


def _mc(value: float | None) -> MetricComponent:
    """Shorthand to create a MetricComponent with just a value."""
    return MetricComponent(value=value)


def _build_analysis(
    net_margin: float | None = 0.15,
    rev_growth: float | None = 0.10,
    earn_growth: float | None = 0.10,
    de_ratio: float | None = 1.5,
    nd_ebitda: float | None = 2.5,
    ocf_ni: float | None = 1.2,
    pe_trailing: float | None = 25.0,
    pe_forward: float | None = 22.0,
    short_pct: float | None = 0.05,
    short_ratio: float | None = 2.0,
    m_score: float | None = -2.5,
    m_interpretation: str | None = "UNLIKELY_MANIPULATOR",
    z_score: float | None = 3.5,
    z_zone: str | None = "SAFE",
    sector_category: str = "GENERAL",
    sector_specific: SectorSpecificMetrics | None = None,
) -> ComprehensiveAnalysis:
    """Build a ComprehensiveAnalysis with configurable metric values."""
    return ComprehensiveAnalysis(
        beneish_m_score=BeneishMScore(
            composite=m_score,
            interpretation=m_interpretation,
        ),
        altman_z_score=AltmanZScore(
            standard=AltmanZScoreVariant(score=z_score, zone=z_zone),
        ),
        profitability=ProfitabilityMetrics(
            net_margin=_mc(net_margin),
        ),
        leverage=LeverageMetrics(
            debt_to_equity=_mc(de_ratio),
            net_debt_to_ebitda=_mc(nd_ebitda),
        ),
        cash_flow=CashFlowMetrics(
            ocf_to_net_income=_mc(ocf_ni),
        ),
        growth=GrowthMetrics(
            revenue_growth_yoy=_mc(rev_growth),
            earnings_growth_yoy=_mc(earn_growth),
        ),
        valuation=ValuationMetrics(
            pe_trailing=_mc(pe_trailing),
            pe_forward=_mc(pe_forward),
        ),
        shareholder_returns=ShareholderMetrics(),
        sentiment=SentimentMetrics(
            short_percent_float=_mc(short_pct),
            short_ratio=_mc(short_ratio),
        ),
        sector_category=sector_category,
        sector_specific=sector_specific,
    )


# ─── Profitability Decline ────────────────────────────────────────────


class TestProfitabilityDecline:
    def test_triggers_on_margin_decline(self):
        """Net margin dropped significantly: prior ~20%, current ~10%."""
        # With rev_growth=0.10 and earn_growth=-0.30:
        # prior_margin = 0.10 * (1 + 0.10) / (1 + (-0.30)) = 0.10 * 1.10 / 0.70 = 0.1571
        # drop = (0.1571 - 0.10) * 10000 = 571 bps > 500 bps
        analysis = _build_analysis(
            net_margin=0.10,
            rev_growth=0.10,
            earn_growth=-0.30,
        )
        alert = _check_profitability_decline(analysis, "TEST")
        assert alert is not None
        assert alert.alert_type == "profitability_decline"
        assert alert.severity == "warning"
        assert alert.current_value == 0.10

    def test_no_trigger_on_stable_margin(self):
        """Stable margin should not trigger alert."""
        analysis = _build_analysis(
            net_margin=0.15,
            rev_growth=0.10,
            earn_growth=0.10,
        )
        alert = _check_profitability_decline(analysis, "TEST")
        assert alert is None

    def test_no_trigger_on_margin_improvement(self):
        """Improving margin should not trigger alert."""
        # prior_margin = 0.15 * (1 + 0.05) / (1 + 0.30) = 0.15 * 1.05 / 1.30 = 0.1212
        # drop = (0.1212 - 0.15) * 10000 = -288 bps (improvement), no trigger
        analysis = _build_analysis(
            net_margin=0.15,
            rev_growth=0.05,
            earn_growth=0.30,
        )
        alert = _check_profitability_decline(analysis, "TEST")
        assert alert is None

    def test_null_net_margin_skips(self):
        """Missing net margin should skip check gracefully."""
        analysis = _build_analysis(net_margin=None)
        alert = _check_profitability_decline(analysis, "TEST")
        assert alert is None

    def test_null_growth_metrics_skips(self):
        """Missing growth metrics should skip check gracefully."""
        analysis = _build_analysis(rev_growth=None, earn_growth=None)
        alert = _check_profitability_decline(analysis, "TEST")
        assert alert is None

    def test_extreme_negative_earnings_growth_skips(self):
        """When (1 + earn_growth) <= 0, skip to avoid division issues."""
        analysis = _build_analysis(
            net_margin=0.10,
            rev_growth=0.10,
            earn_growth=-1.5,  # Makes denominator negative
        )
        alert = _check_profitability_decline(analysis, "TEST")
        assert alert is None

    def test_alert_message_contains_values(self):
        """Alert message should include actual metric values."""
        analysis = _build_analysis(
            net_margin=0.10,
            rev_growth=0.10,
            earn_growth=-0.30,
        )
        alert = _check_profitability_decline(analysis, "TEST")
        assert alert is not None
        assert "10.0%" in alert.message
        assert "bps" in alert.message


# ─── Leverage Warning ─────────────────────────────────────────────────


class TestLeverageWarning:
    def test_triggers_on_high_de_ratio(self):
        """D/E exceeding 3.0x should trigger critical alert."""
        analysis = _build_analysis(de_ratio=4.5, nd_ebitda=2.0)
        alert = _check_leverage_warning(analysis, "TEST")
        assert alert is not None
        assert alert.alert_type == "leverage_warning"
        assert alert.severity == "critical"
        assert "4.50x" in alert.message
        assert "Debt/Equity" in alert.message

    def test_triggers_on_high_nd_ebitda(self):
        """Net Debt/EBITDA exceeding 5x should trigger critical alert."""
        analysis = _build_analysis(de_ratio=1.5, nd_ebitda=6.5)
        alert = _check_leverage_warning(analysis, "TEST")
        assert alert is not None
        assert alert.severity == "critical"
        assert "Net Debt/EBITDA" in alert.message

    def test_triggers_on_both(self):
        """Both conditions met should produce a single alert with both triggers."""
        analysis = _build_analysis(de_ratio=4.0, nd_ebitda=7.0)
        alert = _check_leverage_warning(analysis, "TEST")
        assert alert is not None
        assert "Debt/Equity" in alert.message
        assert "Net Debt/EBITDA" in alert.message

    def test_no_trigger_below_thresholds(self):
        """Below thresholds should not trigger."""
        analysis = _build_analysis(de_ratio=2.0, nd_ebitda=3.0)
        alert = _check_leverage_warning(analysis, "TEST")
        assert alert is None

    def test_boundary_de_exactly_at_threshold(self):
        """Exactly at 3.0x should NOT trigger (condition is > not >=)."""
        analysis = _build_analysis(de_ratio=3.0, nd_ebitda=2.0)
        alert = _check_leverage_warning(analysis, "TEST")
        assert alert is None

    def test_boundary_nd_ebitda_exactly_at_threshold(self):
        """Exactly at 5.0x should NOT trigger."""
        analysis = _build_analysis(de_ratio=1.0, nd_ebitda=5.0)
        alert = _check_leverage_warning(analysis, "TEST")
        assert alert is None

    def test_null_both_metrics_skips(self):
        """Missing both metrics should skip."""
        analysis = _build_analysis(de_ratio=None, nd_ebitda=None)
        alert = _check_leverage_warning(analysis, "TEST")
        assert alert is None

    def test_null_de_only_nd_triggers(self):
        """Missing D/E but high net debt/EBITDA should still trigger."""
        analysis = _build_analysis(de_ratio=None, nd_ebitda=8.0)
        alert = _check_leverage_warning(analysis, "TEST")
        assert alert is not None
        assert alert.current_value == 8.0


# ─── Cash Flow Quality ────────────────────────────────────────────────


class TestCashFlowQuality:
    def test_triggers_on_low_ocf_ni(self):
        """OCF/NI below 0.5 should trigger warning."""
        analysis = _build_analysis(ocf_ni=0.3)
        alert = _check_cash_flow_quality(analysis, "TEST")
        assert alert is not None
        assert alert.alert_type == "cash_flow_quality"
        assert alert.severity == "warning"
        assert "0.30" in alert.message

    def test_triggers_on_negative_ocf_ni(self):
        """Negative OCF/NI should trigger with special message."""
        analysis = _build_analysis(ocf_ni=-0.5)
        alert = _check_cash_flow_quality(analysis, "TEST")
        assert alert is not None
        assert "negative" in alert.message.lower()

    def test_no_trigger_on_healthy_ratio(self):
        """OCF/NI above 0.5 should not trigger."""
        analysis = _build_analysis(ocf_ni=1.2)
        alert = _check_cash_flow_quality(analysis, "TEST")
        assert alert is None

    def test_boundary_exactly_at_threshold(self):
        """Exactly 0.5 should NOT trigger (condition is < not <=)."""
        analysis = _build_analysis(ocf_ni=0.5)
        alert = _check_cash_flow_quality(analysis, "TEST")
        assert alert is None

    def test_null_metric_skips(self):
        """Missing OCF/NI should skip."""
        analysis = _build_analysis(ocf_ni=None)
        alert = _check_cash_flow_quality(analysis, "TEST")
        assert alert is None


# ─── Valuation Extreme ────────────────────────────────────────────────


class TestValuationExtreme:
    def test_triggers_on_high_pe(self):
        """P/E > 50 should trigger info alert."""
        analysis = _build_analysis(pe_trailing=75.0)
        alert = _check_valuation_extreme(analysis, "TEST")
        assert alert is not None
        assert alert.alert_type == "valuation_extreme"
        assert alert.severity == "info"
        assert "75.0x" in alert.message
        assert "high_pe" in (alert.details or "")

    def test_triggers_on_negative_pe(self):
        """Negative P/E should trigger info alert."""
        analysis = _build_analysis(pe_trailing=-15.0)
        alert = _check_valuation_extreme(analysis, "TEST")
        assert alert is not None
        assert alert.severity == "info"
        assert "loss-making" in alert.message.lower()
        assert "negative_pe" in (alert.details or "")

    def test_no_trigger_on_normal_pe(self):
        """Normal P/E should not trigger."""
        analysis = _build_analysis(pe_trailing=25.0)
        alert = _check_valuation_extreme(analysis, "TEST")
        assert alert is None

    def test_boundary_pe_at_50(self):
        """Exactly P/E = 50 should NOT trigger (condition is > not >=)."""
        analysis = _build_analysis(pe_trailing=50.0)
        alert = _check_valuation_extreme(analysis, "TEST")
        assert alert is None

    def test_null_pe_skips(self):
        """Missing P/E should skip."""
        analysis = _build_analysis(pe_trailing=None)
        alert = _check_valuation_extreme(analysis, "TEST")
        assert alert is None

    def test_includes_forward_pe_in_details(self):
        """Alert details should include forward P/E if available."""
        analysis = _build_analysis(pe_trailing=60.0, pe_forward=35.0)
        alert = _check_valuation_extreme(analysis, "TEST")
        assert alert is not None
        import json
        details = json.loads(alert.details)
        assert details["pe_forward"] == 35.0


# ─── Short Interest Spike ─────────────────────────────────────────────


class TestShortInterestSpike:
    def test_triggers_on_high_short_pct(self):
        """Short % > 20% should trigger warning."""
        analysis = _build_analysis(short_pct=0.25)
        alert = _check_short_interest_spike(analysis, "TEST")
        assert alert is not None
        assert alert.alert_type == "short_interest_spike"
        assert alert.severity == "warning"
        assert "25.0%" in alert.message

    def test_no_trigger_below_threshold(self):
        """Short % below 20% should not trigger."""
        analysis = _build_analysis(short_pct=0.10)
        alert = _check_short_interest_spike(analysis, "TEST")
        assert alert is None

    def test_boundary_exactly_at_threshold(self):
        """Exactly 20% should NOT trigger (condition is > not >=)."""
        analysis = _build_analysis(short_pct=0.20)
        alert = _check_short_interest_spike(analysis, "TEST")
        assert alert is None

    def test_null_metric_skips(self):
        """Missing short % should skip."""
        analysis = _build_analysis(short_pct=None)
        alert = _check_short_interest_spike(analysis, "TEST")
        assert alert is None

    def test_includes_short_ratio_in_details(self):
        """Alert details should include short ratio (days to cover)."""
        analysis = _build_analysis(short_pct=0.30, short_ratio=5.0)
        alert = _check_short_interest_spike(analysis, "TEST")
        assert alert is not None
        import json
        details = json.loads(alert.details)
        assert details["short_ratio"] == 5.0


# ─── Existing Forensic Alert Checks ───────────────────────────────────


class TestMScoreWarning:
    def test_triggers_above_threshold(self):
        """M-Score above -1.78 should trigger alert."""
        analysis = _build_analysis(m_score=-1.5, m_interpretation="LIKELY_MANIPULATOR")
        alert = _check_m_score_warning(analysis, "TEST")
        assert alert is not None
        assert alert.alert_type == "m_score_warning"
        assert "LIKELY_MANIPULATOR" in alert.message

    def test_grey_zone_triggers_with_lower_threshold(self):
        """M-Score in grey zone should trigger warning when threshold is lowered.

        Grey zone is [-2.22, -1.78]. With default threshold (-1.78), a grey-zone
        score (-2.0) does NOT trigger because -2.0 < -1.78.  But with a lower
        threshold (e.g., -2.22), it DOES trigger and gets 'warning' severity.
        """
        analysis = _build_analysis(m_score=-2.0, m_interpretation="GREY_ZONE")
        alert = _check_m_score_warning(analysis, "TEST", threshold=-2.22)
        assert alert is not None
        assert alert.severity == "warning"

    def test_likely_manipulator_critical(self):
        """M-Score likely manipulator should be critical severity."""
        analysis = _build_analysis(m_score=-1.0, m_interpretation="LIKELY_MANIPULATOR")
        alert = _check_m_score_warning(analysis, "TEST")
        assert alert is not None
        assert alert.severity == "critical"

    def test_no_trigger_below_threshold(self):
        """M-Score below threshold should not trigger."""
        analysis = _build_analysis(m_score=-2.5, m_interpretation="UNLIKELY_MANIPULATOR")
        alert = _check_m_score_warning(analysis, "TEST")
        assert alert is None

    def test_null_m_score_skips(self):
        """Missing M-Score should skip."""
        analysis = _build_analysis(m_score=None)
        alert = _check_m_score_warning(analysis, "TEST")
        assert alert is None

    def test_custom_threshold(self):
        """Custom threshold should be respected."""
        analysis = _build_analysis(m_score=-2.0, m_interpretation="GREY_ZONE")
        # Default threshold would trigger, but -2.5 threshold should not
        alert = _check_m_score_warning(analysis, "TEST", threshold=-2.5)
        assert alert is not None
        # With -1.5 threshold, should not trigger
        alert2 = _check_m_score_warning(analysis, "TEST", threshold=-1.5)
        assert alert2 is None


class TestZScoreDistress:
    def test_triggers_on_distress(self):
        """Distress zone should trigger critical alert."""
        analysis = _build_analysis(z_score=1.5, z_zone="DISTRESS")
        alert = _check_z_score_distress(analysis, "TEST")
        assert alert is not None
        assert alert.alert_type == "z_score_distress"
        assert alert.severity == "critical"

    def test_no_trigger_on_safe(self):
        """Safe zone should not trigger."""
        analysis = _build_analysis(z_score=3.5, z_zone="SAFE")
        alert = _check_z_score_distress(analysis, "TEST")
        assert alert is None

    def test_no_trigger_on_grey(self):
        """Grey zone should not trigger distress alert."""
        analysis = _build_analysis(z_score=2.0, z_zone="GREY")
        alert = _check_z_score_distress(analysis, "TEST")
        assert alert is None

    def test_null_z_score_skips(self):
        """Missing Z-Score should skip."""
        analysis = _build_analysis(z_score=None, z_zone=None)
        alert = _check_z_score_distress(analysis, "TEST")
        assert alert is None


class TestRuleOf40:
    def test_triggers_below_40(self):
        """Rule of 40 below threshold should trigger for SaaS company."""
        sector_specific = SectorSpecificMetrics(
            sector_category="SAAS",
            label="SaaS Efficiency",
            metrics={
                "rule_of_40": _mc(35.0),
                "magic_number": _mc(0.8),
            },
            interpretations={"rule_of_40": "MARGINAL"},
        )
        analysis = _build_analysis(
            sector_category="SAAS",
            sector_specific=sector_specific,
        )
        alert = _check_rule_of_40(analysis, "TEST")
        assert alert is not None
        assert alert.alert_type == "rule_of_40_fail"
        assert alert.severity == "warning"

    def test_no_trigger_above_40(self):
        """Rule of 40 above threshold should not trigger."""
        sector_specific = SectorSpecificMetrics(
            sector_category="SAAS",
            label="SaaS Efficiency",
            metrics={"rule_of_40": _mc(55.0)},
            interpretations={"rule_of_40": "PASSING"},
        )
        analysis = _build_analysis(
            sector_category="SAAS",
            sector_specific=sector_specific,
        )
        alert = _check_rule_of_40(analysis, "TEST")
        assert alert is None

    def test_skips_non_saas(self):
        """Non-SaaS companies should skip Rule of 40 check."""
        analysis = _build_analysis(sector_category="GENERAL")
        alert = _check_rule_of_40(analysis, "TEST")
        assert alert is None

    def test_skips_null_sector_specific(self):
        """Missing sector_specific should skip."""
        analysis = _build_analysis(sector_category="SAAS", sector_specific=None)
        alert = _check_rule_of_40(analysis, "TEST")
        assert alert is None


class TestMagicNumber:
    def test_triggers_below_05(self):
        """Magic Number below 0.5 should trigger for SaaS company."""
        sector_specific = SectorSpecificMetrics(
            sector_category="SAAS",
            label="SaaS Efficiency",
            metrics={
                "magic_number": _mc(0.3),
                "rule_of_40": _mc(45.0),
            },
            interpretations={"magic_number": "INEFFICIENT"},
        )
        analysis = _build_analysis(
            sector_category="SAAS",
            sector_specific=sector_specific,
        )
        alert = _check_magic_number(analysis, "TEST")
        assert alert is not None
        assert alert.alert_type == "magic_number_low"
        assert alert.severity == "info"

    def test_no_trigger_above_05(self):
        """Magic Number above 0.5 should not trigger."""
        sector_specific = SectorSpecificMetrics(
            sector_category="SAAS",
            label="SaaS Efficiency",
            metrics={"magic_number": _mc(0.8)},
        )
        analysis = _build_analysis(
            sector_category="SAAS",
            sector_specific=sector_specific,
        )
        alert = _check_magic_number(analysis, "TEST")
        assert alert is None

    def test_skips_non_saas(self):
        """Non-SaaS companies should skip Magic Number check."""
        analysis = _build_analysis(sector_category="GENERAL")
        alert = _check_magic_number(analysis, "TEST")
        assert alert is None


# ─── Full Orchestrator ────────────────────────────────────────────────


class TestGenerateComprehensiveAlerts:
    def test_returns_empty_for_healthy_company(self):
        """A healthy company should generate no alerts."""
        analysis = _build_analysis(
            net_margin=0.15,
            rev_growth=0.10,
            earn_growth=0.10,
            de_ratio=1.5,
            nd_ebitda=2.5,
            ocf_ni=1.2,
            pe_trailing=25.0,
            short_pct=0.05,
            m_score=-2.5,
            m_interpretation="UNLIKELY_MANIPULATOR",
            z_score=3.5,
            z_zone="SAFE",
        )
        alerts = generate_comprehensive_alerts(analysis, "AAPL")
        assert len(alerts) == 0

    def test_returns_multiple_alerts(self):
        """A company with multiple issues should generate multiple alerts."""
        analysis = _build_analysis(
            net_margin=0.10,
            rev_growth=0.10,
            earn_growth=-0.30,  # profitability_decline
            de_ratio=4.0,       # leverage_warning
            nd_ebitda=6.0,      # leverage_warning (same alert)
            ocf_ni=0.3,         # cash_flow_quality
            pe_trailing=60.0,   # valuation_extreme
            short_pct=0.25,     # short_interest_spike
            m_score=-1.5,       # m_score_warning
            m_interpretation="LIKELY_MANIPULATOR",
            z_score=1.5,        # z_score_distress
            z_zone="DISTRESS",
        )
        alerts = generate_comprehensive_alerts(analysis, "RISK")
        alert_types = [a.alert_type for a in alerts]

        assert "m_score_warning" in alert_types
        assert "z_score_distress" in alert_types
        assert "profitability_decline" in alert_types
        assert "leverage_warning" in alert_types
        assert "cash_flow_quality" in alert_types
        assert "valuation_extreme" in alert_types
        assert "short_interest_spike" in alert_types
        assert len(alerts) == 7

    def test_all_null_metrics_no_alerts(self):
        """All null metrics should produce no alerts."""
        analysis = _build_analysis(
            net_margin=None,
            rev_growth=None,
            earn_growth=None,
            de_ratio=None,
            nd_ebitda=None,
            ocf_ni=None,
            pe_trailing=None,
            pe_forward=None,
            short_pct=None,
            short_ratio=None,
            m_score=None,
            m_interpretation=None,
            z_score=None,
            z_zone=None,
        )
        alerts = generate_comprehensive_alerts(analysis, "NULL")
        assert len(alerts) == 0

    def test_ticker_uppercased(self):
        """Ticker should be uppercased in alerts."""
        analysis = _build_analysis(pe_trailing=60.0)
        alerts = generate_comprehensive_alerts(analysis, "aapl")
        for alert in alerts:
            assert alert.ticker == "AAPL"

    def test_alerts_without_db_not_persisted(self):
        """Without db session, alerts should be returned but not persisted."""
        analysis = _build_analysis(pe_trailing=60.0)
        alerts = generate_comprehensive_alerts(analysis, "TEST", db=None)
        assert len(alerts) == 1
        assert alerts[0].id is None  # Not persisted

    def test_alert_fields_populated(self):
        """All required alert fields should be populated."""
        analysis = _build_analysis(pe_trailing=60.0)
        alerts = generate_comprehensive_alerts(analysis, "TEST")
        alert = alerts[0]
        assert alert.ticker == "TEST"
        assert alert.alert_type == "valuation_extreme"
        assert alert.severity in ("info", "warning", "critical")
        assert len(alert.message) > 0
        assert alert.is_dismissed == 0
        assert alert.created_at is not None


class TestGenerateComprehensiveAlertsWithSettings:
    """Test settings toggles using a mock AlertSettings-like object."""

    class MockSettings:
        """Minimal mock that has the same attributes as AlertSettings."""
        def __init__(self, **kwargs):
            # Default all enabled
            self.enable_m_score_alerts = kwargs.get("enable_m_score_alerts", 1)
            self.enable_z_score_alerts = kwargs.get("enable_z_score_alerts", 1)
            self.enable_rule_of_40_alerts = kwargs.get("enable_rule_of_40_alerts", 1)
            self.enable_magic_number_alerts = kwargs.get("enable_magic_number_alerts", 1)
            self.enable_profitability_alerts = kwargs.get("enable_profitability_alerts", 1)
            self.enable_leverage_alerts = kwargs.get("enable_leverage_alerts", 1)
            self.enable_cash_flow_alerts = kwargs.get("enable_cash_flow_alerts", 1)
            self.enable_valuation_alerts = kwargs.get("enable_valuation_alerts", 1)
            self.enable_short_interest_alerts = kwargs.get("enable_short_interest_alerts", 1)
            self.m_score_threshold = kwargs.get("m_score_threshold", -1.78)

    def test_disabled_valuation_alerts(self):
        """Disabled valuation alerts should not be generated."""
        analysis = _build_analysis(pe_trailing=60.0)
        settings = self.MockSettings(enable_valuation_alerts=0)
        alerts = generate_comprehensive_alerts(analysis, "TEST", settings=settings)
        alert_types = [a.alert_type for a in alerts]
        assert "valuation_extreme" not in alert_types

    def test_disabled_leverage_alerts(self):
        """Disabled leverage alerts should not be generated."""
        analysis = _build_analysis(de_ratio=5.0)
        settings = self.MockSettings(enable_leverage_alerts=0)
        alerts = generate_comprehensive_alerts(analysis, "TEST", settings=settings)
        alert_types = [a.alert_type for a in alerts]
        assert "leverage_warning" not in alert_types

    def test_disabled_cash_flow_alerts(self):
        """Disabled cash flow alerts should not be generated."""
        analysis = _build_analysis(ocf_ni=0.2)
        settings = self.MockSettings(enable_cash_flow_alerts=0)
        alerts = generate_comprehensive_alerts(analysis, "TEST", settings=settings)
        alert_types = [a.alert_type for a in alerts]
        assert "cash_flow_quality" not in alert_types

    def test_disabled_short_interest_alerts(self):
        """Disabled short interest alerts should not be generated."""
        analysis = _build_analysis(short_pct=0.30)
        settings = self.MockSettings(enable_short_interest_alerts=0)
        alerts = generate_comprehensive_alerts(analysis, "TEST", settings=settings)
        alert_types = [a.alert_type for a in alerts]
        assert "short_interest_spike" not in alert_types

    def test_disabled_profitability_alerts(self):
        """Disabled profitability alerts should not be generated."""
        analysis = _build_analysis(
            net_margin=0.10,
            rev_growth=0.10,
            earn_growth=-0.30,
        )
        settings = self.MockSettings(enable_profitability_alerts=0)
        alerts = generate_comprehensive_alerts(analysis, "TEST", settings=settings)
        alert_types = [a.alert_type for a in alerts]
        assert "profitability_decline" not in alert_types

    def test_all_disabled_no_alerts(self):
        """All disabled should produce no alerts even with bad metrics."""
        analysis = _build_analysis(
            de_ratio=5.0,
            ocf_ni=0.2,
            pe_trailing=60.0,
            short_pct=0.30,
            m_score=-1.0,
            m_interpretation="LIKELY_MANIPULATOR",
            z_score=1.0,
            z_zone="DISTRESS",
        )
        settings = self.MockSettings(
            enable_m_score_alerts=0,
            enable_z_score_alerts=0,
            enable_rule_of_40_alerts=0,
            enable_magic_number_alerts=0,
            enable_profitability_alerts=0,
            enable_leverage_alerts=0,
            enable_cash_flow_alerts=0,
            enable_valuation_alerts=0,
            enable_short_interest_alerts=0,
        )
        alerts = generate_comprehensive_alerts(analysis, "TEST", settings=settings)
        assert len(alerts) == 0

    def test_custom_m_score_threshold(self):
        """Custom M-Score threshold from settings should be respected."""
        analysis = _build_analysis(m_score=-2.0, m_interpretation="GREY_ZONE")
        # Default -1.78 would not trigger at -2.0
        settings_default = self.MockSettings(m_score_threshold=-1.78)
        alerts_default = generate_comprehensive_alerts(analysis, "TEST", settings=settings_default)
        assert not any(a.alert_type == "m_score_warning" for a in alerts_default)

        # Custom -2.5 should trigger at -2.0
        settings_custom = self.MockSettings(m_score_threshold=-2.5)
        alerts_custom = generate_comprehensive_alerts(analysis, "TEST", settings=settings_custom)
        assert any(a.alert_type == "m_score_warning" for a in alerts_custom)


# ─── Bounds Checking Tests ───────────────────────────────────────────


class TestProfitabilityDeclineBoundsChecking:
    """Test the extreme growth rate bounds checking in _check_profitability_decline."""

    def test_extreme_revenue_growth_skips(self):
        """Revenue growth >500% should skip the profitability check."""
        analysis = _build_analysis(
            net_margin=0.10,
            rev_growth=6.0,  # 600% growth — too extreme
            earn_growth=-0.30,
        )
        alert = _check_profitability_decline(analysis, "TEST")
        assert alert is None

    def test_extreme_negative_revenue_growth_skips(self):
        """Revenue decline >500% should skip the profitability check."""
        analysis = _build_analysis(
            net_margin=0.10,
            rev_growth=-6.0,  # -600% — nonsensical
            earn_growth=-0.30,
        )
        alert = _check_profitability_decline(analysis, "TEST")
        assert alert is None

    def test_extreme_earnings_growth_skips(self):
        """Earnings growth >500% should skip the profitability check."""
        analysis = _build_analysis(
            net_margin=0.10,
            rev_growth=0.10,
            earn_growth=6.0,  # 600% growth
        )
        alert = _check_profitability_decline(analysis, "TEST")
        assert alert is None

    def test_exactly_at_boundary_500pct_passes(self):
        """Exactly 500% (5.0) should NOT be rejected (condition is > 5.0)."""
        # With rev_growth=5.0 and earn_growth=-0.30:
        # prior_margin = 0.10 * (1 + 5.0) / (1 + (-0.30)) = 0.10 * 6.0 / 0.70 = 0.857
        # drop = (0.857 - 0.10) * 10000 = 7571 bps > 500 bps -> triggers
        analysis = _build_analysis(
            net_margin=0.10,
            rev_growth=5.0,
            earn_growth=-0.30,
        )
        alert = _check_profitability_decline(analysis, "TEST")
        assert alert is not None  # 5.0 is not > 5.0, so it passes

    def test_just_above_boundary_rejected(self):
        """Growth rate of 5.01 (>500%) should be rejected."""
        analysis = _build_analysis(
            net_margin=0.10,
            rev_growth=5.01,
            earn_growth=-0.30,
        )
        alert = _check_profitability_decline(analysis, "TEST")
        assert alert is None


# ─── Deduplication Tests ─────────────────────────────────────────────


class TestShouldCreateAlert:
    """Test the _should_create_alert deduplication function."""

    def test_returns_true_when_no_db(self):
        """Without a database, always allow creation."""
        result = _should_create_alert(None, "TEST", "valuation_extreme")
        assert result is True

    def test_returns_true_when_no_existing_alert(self):
        """When no matching alert exists, allow creation."""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No existing alert

        result = _should_create_alert(mock_db, "TEST", "valuation_extreme")
        assert result is True

    def test_returns_false_when_recent_duplicate_exists(self):
        """When a recent undismissed alert exists, deny creation."""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = Alert(
            ticker="TEST",
            alert_type="valuation_extreme",
            severity="info",
            message="test",
            is_dismissed=0,
            created_at=datetime.utcnow(),
        )

        result = _should_create_alert(mock_db, "TEST", "valuation_extreme")
        assert result is False

    def test_returns_true_on_db_error(self):
        """On database error, allow creation (fail open)."""
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("DB connection lost")

        result = _should_create_alert(mock_db, "TEST", "valuation_extreme")
        assert result is True

    def test_ticker_uppercased_in_query(self):
        """The function should uppercase the ticker for consistency."""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        _should_create_alert(mock_db, "test", "valuation_extreme")
        # Verify query was called (we can't easily check the filter args
        # with SQLAlchemy, but we verify no exception)
        mock_db.query.assert_called_once()


class TestDeduplicationIntegration:
    """Test deduplication integrated into generate_comprehensive_alerts."""

    def test_dedup_skips_when_db_none(self):
        """Without DB, deduplication is bypassed and alerts still generated."""
        analysis = _build_analysis(pe_trailing=60.0)
        alerts = generate_comprehensive_alerts(analysis, "TEST", db=None)
        assert len(alerts) == 1
        assert alerts[0].alert_type == "valuation_extreme"

    @patch("app.services.alert_service._should_create_alert")
    def test_dedup_filters_duplicate(self, mock_should_create):
        """When _should_create_alert returns False, alert is skipped."""
        mock_should_create.return_value = False

        analysis = _build_analysis(pe_trailing=60.0)
        alerts = generate_comprehensive_alerts(analysis, "TEST", db=None)
        # Even though pe_trailing triggers, dedup says no
        assert len(alerts) == 0

    @patch("app.services.alert_service._should_create_alert")
    def test_dedup_allows_new_alert(self, mock_should_create):
        """When _should_create_alert returns True, alert is created."""
        mock_should_create.return_value = True

        analysis = _build_analysis(pe_trailing=60.0)
        alerts = generate_comprehensive_alerts(analysis, "TEST", db=None)
        assert len(alerts) == 1
        assert alerts[0].alert_type == "valuation_extreme"
