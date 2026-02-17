"""Tests for forensic calculation engine — 100% coverage target."""

import pytest
from app.services.forensic_engine import (
    compute_beneish_m_score,
    compute_altman_z_score,
    compute_rule_of_40,
    compute_magic_number,
    run_forensic_analysis,
)


class TestBeneishMScore:
    def test_all_components_computed(self, sample_financials, sample_balance_sheet, sample_cashflow):
        result = compute_beneish_m_score(sample_financials, sample_balance_sheet, sample_cashflow)
        assert result.composite is not None
        assert result.interpretation is not None
        assert result.components.dsri.value is not None
        assert result.components.gmi.value is not None
        assert result.components.aqi.value is not None
        assert result.components.sgi.value is not None
        assert result.components.depi.value is not None
        assert result.components.sgai.value is not None
        assert result.components.lvgi.value is not None
        assert result.components.tata.value is not None

    def test_dsri_calculation(self, sample_financials, sample_balance_sheet, sample_cashflow):
        result = compute_beneish_m_score(sample_financials, sample_balance_sheet, sample_cashflow)
        # DSRI = (Recv_t/Rev_t) / (Recv_t-1/Rev_t-1)
        recv_curr = 66243000000 / 391035000000
        recv_prior = 60985000000 / 383285000000
        expected = recv_curr / recv_prior
        assert abs(result.components.dsri.value - round(expected, 4)) < 0.001

    def test_gmi_calculation(self, sample_financials, sample_balance_sheet, sample_cashflow):
        result = compute_beneish_m_score(sample_financials, sample_balance_sheet, sample_cashflow)
        gm_curr = 180683000000 / 391035000000
        gm_prior = 169148000000 / 383285000000
        expected = gm_prior / gm_curr
        assert abs(result.components.gmi.value - round(expected, 4)) < 0.001

    def test_sgi_calculation(self, sample_financials, sample_balance_sheet, sample_cashflow):
        result = compute_beneish_m_score(sample_financials, sample_balance_sheet, sample_cashflow)
        expected = 391035000000 / 383285000000
        assert abs(result.components.sgi.value - round(expected, 4)) < 0.001

    def test_composite_formula(self, sample_financials, sample_balance_sheet, sample_cashflow):
        result = compute_beneish_m_score(sample_financials, sample_balance_sheet, sample_cashflow)
        c = result.components
        expected = (
            -4.84
            + 0.920 * c.dsri.value
            + 0.528 * c.gmi.value
            + 0.404 * c.aqi.value
            + 0.892 * c.sgi.value
            + 0.115 * c.depi.value
            - 0.172 * c.sgai.value
            + 4.679 * c.tata.value
            - 0.327 * c.lvgi.value
        )
        assert abs(result.composite - round(expected, 4)) < 0.01

    def test_interpretation_unlikely_manipulator(self, sample_financials, sample_balance_sheet, sample_cashflow):
        result = compute_beneish_m_score(sample_financials, sample_balance_sheet, sample_cashflow)
        # Apple should typically be UNLIKELY_MANIPULATOR
        if result.composite < -2.22:
            assert result.interpretation == "UNLIKELY_MANIPULATOR"

    def test_all_citations_present(self, sample_financials, sample_balance_sheet, sample_cashflow):
        result = compute_beneish_m_score(sample_financials, sample_balance_sheet, sample_cashflow)
        for name in ["dsri", "gmi", "aqi", "sgi", "depi", "sgai", "lvgi", "tata"]:
            comp = getattr(result.components, name)
            assert comp.citation.source != "", f"Missing citation source for {name}"

    def test_empty_data_returns_nulls(self):
        result = compute_beneish_m_score({}, {}, {})
        assert result.composite is None
        assert result.interpretation is None

    def test_partial_data_handles_gracefully(self, sample_financials):
        result = compute_beneish_m_score(sample_financials, {}, {})
        # Some components should be None when balance_sheet is missing
        assert result.components.dsri.value is None

    def test_thresholds_present(self, sample_financials, sample_balance_sheet, sample_cashflow):
        result = compute_beneish_m_score(sample_financials, sample_balance_sheet, sample_cashflow)
        assert result.thresholds.likely_manipulator == -1.78
        assert result.thresholds.grey_zone == [-2.22, -1.78]


class TestAltmanZScore:
    def test_standard_score_computed(self, sample_financials, sample_balance_sheet, sample_info):
        result = compute_altman_z_score(sample_financials, sample_balance_sheet, sample_info)
        assert result.standard.score is not None
        assert result.standard.zone is not None

    def test_saas_modified_computed(self, sample_financials, sample_balance_sheet, sample_info):
        result = compute_altman_z_score(sample_financials, sample_balance_sheet, sample_info)
        assert result.saas_modified.score is not None
        assert result.saas_modified.zone is not None
        assert result.saas_modified.disclaimer is not None

    def test_standard_components(self, sample_financials, sample_balance_sheet, sample_info):
        result = compute_altman_z_score(sample_financials, sample_balance_sheet, sample_info)
        assert "x1" in result.standard.components
        assert "x2" in result.standard.components
        assert "x3" in result.standard.components
        assert "x4" in result.standard.components
        assert "x5" in result.standard.components

    def test_x1_working_capital(self, sample_financials, sample_balance_sheet, sample_info):
        result = compute_altman_z_score(sample_financials, sample_balance_sheet, sample_info)
        ca = 152987000000
        cl = 176392000000
        ta = 364980000000
        expected = (ca - cl) / ta
        assert abs(result.standard.components["x1"].value - round(expected, 4)) < 0.001

    def test_zone_classification_safe(self, sample_financials, sample_balance_sheet, sample_info):
        result = compute_altman_z_score(sample_financials, sample_balance_sheet, sample_info)
        if result.standard.score and result.standard.score > 2.99:
            assert result.standard.zone == "SAFE"

    def test_zone_classification_distress(self):
        # Minimal data that produces distress
        financials = {"2024-01-01": {"Total Revenue": 100, "EBIT": -50}}
        bs = {
            "2024-01-01": {
                "Total Assets": 1000, "Current Assets": 100, "Current Liabilities": 900,
                "Retained Earnings": -500, "Total Liabilities Net Minority Interest": 950,
            }
        }
        info = {"marketCap": 50}
        result = compute_altman_z_score(financials, bs, info)
        if result.standard.score and result.standard.score < 1.81:
            assert result.standard.zone == "DISTRESS"

    def test_empty_data(self):
        result = compute_altman_z_score({}, {}, {})
        assert result.standard.score is None
        assert result.saas_modified.score is None

    def test_citations_on_all_components(self, sample_financials, sample_balance_sheet, sample_info):
        result = compute_altman_z_score(sample_financials, sample_balance_sheet, sample_info)
        for key, comp in result.standard.components.items():
            assert comp.citation.source != "", f"Missing citation for {key}"


class TestRuleOf40:
    def test_score_computed(self, sample_financials, sample_cashflow):
        result = compute_rule_of_40(sample_financials, sample_cashflow)
        assert result.score is not None
        assert result.revenue_growth_percent is not None
        assert result.fcf_margin_percent is not None

    def test_revenue_growth(self, sample_financials, sample_cashflow):
        result = compute_rule_of_40(sample_financials, sample_cashflow)
        expected = ((391035000000 - 383285000000) / 383285000000) * 100
        assert abs(result.revenue_growth_percent - round(expected, 2)) < 0.1

    def test_interpretation_passing(self, sample_financials, sample_cashflow):
        result = compute_rule_of_40(sample_financials, sample_cashflow)
        if result.score and result.score >= 40:
            assert result.interpretation == "PASSING"

    def test_citations_present(self, sample_financials, sample_cashflow):
        result = compute_rule_of_40(sample_financials, sample_cashflow)
        assert "revenue_current" in result.citations
        assert "operating_cash_flow" in result.citations

    def test_empty_data(self):
        result = compute_rule_of_40({}, {})
        assert result.score is None


class TestMagicNumber:
    def test_score_computed(self, sample_financials, sample_quarterly_financials):
        result = compute_magic_number(sample_financials, sample_quarterly_financials)
        assert result.score is not None

    def test_net_new_arr(self, sample_quarterly_financials, sample_financials):
        result = compute_magic_number(sample_financials, sample_quarterly_financials)
        expected = (94930000000 - 85778000000) * 4
        assert abs(result.net_new_arr - expected) < 1

    def test_interpretation(self, sample_financials, sample_quarterly_financials):
        result = compute_magic_number(sample_financials, sample_quarterly_financials)
        assert result.interpretation in ["EFFICIENT", "MODERATE", "INEFFICIENT"]

    def test_empty_data(self):
        result = compute_magic_number({}, {})
        assert result.score is None


class TestRunForensicAnalysis:
    def test_full_analysis(self, sample_financials, sample_balance_sheet, sample_cashflow, sample_info, sample_quarterly_financials):
        data = {
            "financials": sample_financials,
            "balance_sheet": sample_balance_sheet,
            "cashflow": sample_cashflow,
            "info": sample_info,
            "quarterly_financials": sample_quarterly_financials,
        }
        result = run_forensic_analysis(data)
        assert result.beneish_m_score.composite is not None
        assert result.altman_z_score.standard.score is not None
        assert result.rule_of_40.score is not None
        assert result.magic_number.score is not None
