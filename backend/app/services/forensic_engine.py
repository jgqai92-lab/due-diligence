"""Forensic calculation engine — Beneish M-Score, Altman Z-Score, SaaS metrics.

All calculations are server-side. Claude never calculates; it only narrates.
Every metric produces citations mapping back to source data.
"""

import logging
from app.schemas.analysis import (
    BeneishMScore,
    BeneishMScoreComponents,
    BeneishThresholds,
    MetricComponent,
    Citation,
    AltmanZScore,
    AltmanZScoreVariant,
    RuleOf40,
    MagicNumber,
    ForensicMetrics,
    ComprehensiveAnalysis,
)
from app.utils.calculations import safe_divide, pct_change
from app.services.metric_definitions import get_definition, BENEISH_DEFINITIONS, ALTMAN_DEFINITIONS, SAAS_DEFINITIONS

logger = logging.getLogger(__name__)


def _is_valid_period(period_data: dict, key_fields: list[str] = None) -> bool:
    """Check if a period contains real data (not all NaN/None).

    Returns True if at least one key field has a valid number.
    If key_fields is None, checks for any valid value.
    """
    if not isinstance(period_data, dict):
        return False

    # If no key fields specified, check for any valid value
    if key_fields is None:
        for value in period_data.values():
            if value is not None:
                try:
                    float(value)
                    return True
                except (ValueError, TypeError):
                    continue
        return False

    # Check if any key field has valid data
    for field in key_fields:
        value = period_data.get(field)
        if value is not None:
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                continue
    return False


def _find_first_valid_period(data: dict, key_fields: list[str] = None) -> int:
    """Find the first period index that contains real data.

    Returns the period index, or 0 if no valid period is found.
    yfinance sometimes returns unreported future periods with all NaN values.

    Args:
        data: Financial data dictionary
        key_fields: List of key field names to check for validity (e.g. ['Total Revenue'])
                   If None, checks for any valid value
    """
    if not data or not isinstance(data, dict):
        return 0

    periods = list(data.keys())
    for idx, period_key in enumerate(periods):
        period_data = data.get(period_key, {})
        if _is_valid_period(period_data, key_fields):
            return idx

    return 0


def _get_field(data: dict, field_names: list[str], period_idx: int = 0, base_period_offset: int = 0) -> float | None:
    """Extract a numeric value from yfinance data, trying multiple field name variants.

    yfinance DataFrames converted to JSON have columns as date strings and rows as field names.
    Structure: { "2024-09-28T00:00:00.000Z": { "Total Revenue": 391035000000, ... }, ... }

    Args:
        data: Financial data dictionary
        field_names: List of possible field names to try
        period_idx: Requested period index (0=current, 1=prior, etc.)
        base_period_offset: Offset to first valid period (to skip NaN periods)
    """
    if not data or not isinstance(data, dict):
        return None

    # Adjust period index to skip NaN placeholder periods
    adjusted_idx = period_idx + base_period_offset

    periods = list(data.keys())
    if adjusted_idx >= len(periods):
        return None

    period_data = data.get(periods[adjusted_idx], {})
    if not isinstance(period_data, dict):
        return None

    for name in field_names:
        val = period_data.get(name)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue
    return None


def _cite(
    line_item: str,
    filing_type: str,
    period: str,
    raw_value: float | None,
    formula: str = "",
    description: str = "",
) -> Citation:
    return Citation(
        line_item=line_item,
        filing_type=filing_type,
        period=period,
        raw_value=raw_value,
        source=f"yfinance.{filing_type}",
        formula=formula,
        description=description,
    )


def _get_period_label(data: dict, idx: int = 0, base_period_offset: int = 0) -> str:
    """Get period label, adjusting for base period offset to skip NaN periods."""
    if not data:
        return "N/A"
    periods = list(data.keys())
    adjusted_idx = idx + base_period_offset
    if adjusted_idx < len(periods):
        return periods[adjusted_idx][:10]
    return "N/A"


# ─── Beneish M-Score ───────────────────────────────────────────────

REVENUE_FIELDS = ["Total Revenue", "Revenue", "Operating Revenue"]
RECEIVABLES_FIELDS = ["Net Receivables", "Accounts Receivable", "Receivables"]
GROSS_PROFIT_FIELDS = ["Gross Profit"]
TOTAL_ASSETS_FIELDS = ["Total Assets"]
CURRENT_ASSETS_FIELDS = ["Current Assets", "Total Current Assets"]
PPE_FIELDS = ["Net PPE", "Property Plant And Equipment Net", "Property Plant Equipment"]
DEPRECIATION_FIELDS = ["Depreciation", "Depreciation And Amortization", "Reconciled Depreciation"]
SGA_FIELDS = ["Selling General And Administration", "Selling General Administrative", "SGA"]
TOTAL_LIABILITIES_FIELDS = ["Total Liabilities Net Minority Interest", "Total Liabilities", "Total Liab"]
NET_INCOME_FIELDS = ["Net Income", "Net Income Common Stockholders"]
OPERATING_CF_FIELDS = ["Operating Cash Flow", "Total Cash From Operating Activities"]
CURRENT_LIABILITIES_FIELDS = ["Current Liabilities", "Total Current Liabilities"]
RETAINED_EARNINGS_FIELDS = ["Retained Earnings"]
EBIT_FIELDS = ["EBIT", "Ebit"]
MARKET_CAP_FIELDS = ["marketCap"]


def compute_beneish_m_score(financials: dict, balance_sheet: dict, cashflow: dict) -> BeneishMScore:
    """Compute Beneish M-Score with all 8 components."""
    # Find first valid period to skip NaN placeholders - check for key revenue fields
    base_offset_fin = _find_first_valid_period(financials, REVENUE_FIELDS)
    base_offset_bs = _find_first_valid_period(balance_sheet, TOTAL_ASSETS_FIELDS)
    base_offset_cf = _find_first_valid_period(cashflow, OPERATING_CF_FIELDS)

    period_curr = _get_period_label(financials, 0, base_offset_fin)
    period_prior = _get_period_label(financials, 1, base_offset_fin)

    # Current and prior year values
    rev_curr = _get_field(financials, REVENUE_FIELDS, 0, base_offset_fin)
    rev_prior = _get_field(financials, REVENUE_FIELDS, 1, base_offset_fin)
    recv_curr = _get_field(balance_sheet, RECEIVABLES_FIELDS, 0, base_offset_bs)
    recv_prior = _get_field(balance_sheet, RECEIVABLES_FIELDS, 1, base_offset_bs)
    gp_curr = _get_field(financials, GROSS_PROFIT_FIELDS, 0, base_offset_fin)
    gp_prior = _get_field(financials, GROSS_PROFIT_FIELDS, 1, base_offset_fin)
    ta_curr = _get_field(balance_sheet, TOTAL_ASSETS_FIELDS, 0, base_offset_bs)
    ta_prior = _get_field(balance_sheet, TOTAL_ASSETS_FIELDS, 1, base_offset_bs)
    ca_curr = _get_field(balance_sheet, CURRENT_ASSETS_FIELDS, 0, base_offset_bs)
    ca_prior = _get_field(balance_sheet, CURRENT_ASSETS_FIELDS, 1, base_offset_bs)
    ppe_curr = _get_field(balance_sheet, PPE_FIELDS, 0, base_offset_bs)
    ppe_prior = _get_field(balance_sheet, PPE_FIELDS, 1, base_offset_bs)
    dep_curr = _get_field(financials, DEPRECIATION_FIELDS, 0, base_offset_fin)
    dep_prior = _get_field(financials, DEPRECIATION_FIELDS, 1, base_offset_fin)
    sga_curr = _get_field(financials, SGA_FIELDS, 0, base_offset_fin)
    sga_prior = _get_field(financials, SGA_FIELDS, 1, base_offset_fin)
    tl_curr = _get_field(balance_sheet, TOTAL_LIABILITIES_FIELDS, 0, base_offset_bs)
    tl_prior = _get_field(balance_sheet, TOTAL_LIABILITIES_FIELDS, 1, base_offset_bs)
    ni_curr = _get_field(financials, NET_INCOME_FIELDS, 0, base_offset_fin)
    ocf_curr = _get_field(cashflow, OPERATING_CF_FIELDS, 0, base_offset_cf)

    # DSRI = (Receivables_t / Revenue_t) / (Receivables_t-1 / Revenue_t-1)
    dsri_num = safe_divide(recv_curr, rev_curr)
    dsri_den = safe_divide(recv_prior, rev_prior)
    dsri = safe_divide(dsri_num, dsri_den)

    # GMI = ((Revenue_t-1 - COGS_t-1) / Revenue_t-1) / ((Revenue_t - COGS_t) / Revenue_t)
    # Simplified: (GrossMargin_prior) / (GrossMargin_current)
    gm_curr = safe_divide(gp_curr, rev_curr)
    gm_prior = safe_divide(gp_prior, rev_prior)
    gmi = safe_divide(gm_prior, gm_curr)

    # AQI = (1 - (CA_t + PPE_t) / TA_t) / (1 - (CA_t-1 + PPE_t-1) / TA_t-1)
    aqi = None
    if ca_curr is not None and ppe_curr is not None and ta_curr and ca_prior is not None and ppe_prior is not None and ta_prior:
        aq_curr = 1 - (ca_curr + ppe_curr) / ta_curr
        aq_prior = 1 - (ca_prior + ppe_prior) / ta_prior
        aqi = safe_divide(aq_curr, aq_prior)

    # SGI = Revenue_t / Revenue_t-1
    sgi = safe_divide(rev_curr, rev_prior)

    # DEPI = (Dep_t-1 / (Dep_t-1 + PPE_t-1)) / (Dep_t / (Dep_t + PPE_t))
    depi = None
    if dep_curr is not None and ppe_curr is not None and dep_prior is not None and ppe_prior is not None:
        dr_curr = safe_divide(dep_curr, dep_curr + ppe_curr) if (dep_curr + ppe_curr) != 0 else None
        dr_prior = safe_divide(dep_prior, dep_prior + ppe_prior) if (dep_prior + ppe_prior) != 0 else None
        depi = safe_divide(dr_prior, dr_curr)

    # SGAI = (SGA_t / Revenue_t) / (SGA_t-1 / Revenue_t-1)
    sgai_curr = safe_divide(sga_curr, rev_curr)
    sgai_prior = safe_divide(sga_prior, rev_prior)
    sgai = safe_divide(sgai_curr, sgai_prior)

    # LVGI = (TotalLiabilities_t / TotalAssets_t) / (TotalLiabilities_t-1 / TotalAssets_t-1)
    lev_curr = safe_divide(tl_curr, ta_curr)
    lev_prior = safe_divide(tl_prior, ta_prior)
    lvgi = safe_divide(lev_curr, lev_prior)

    # TATA = (NetIncome - OperatingCashFlow) / TotalAssets
    tata = None
    if ni_curr is not None and ocf_curr is not None and ta_curr:
        tata = (ni_curr - ocf_curr) / ta_curr

    # Composite M-Score = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
    #                     + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI
    composite = None
    components_list = [dsri, gmi, aqi, sgi, depi, sgai, tata, lvgi]
    if all(c is not None for c in components_list):
        composite = (
            -4.84
            + 0.920 * dsri
            + 0.528 * gmi
            + 0.404 * aqi
            + 0.892 * sgi
            + 0.115 * depi
            - 0.172 * sgai
            + 4.679 * tata
            - 0.327 * lvgi
        )

    # Interpretation
    interpretation = None
    if composite is not None:
        if composite < -2.22:
            interpretation = "UNLIKELY_MANIPULATOR"
        elif composite <= -1.78:
            interpretation = "GREY_ZONE"
        else:
            interpretation = "LIKELY_MANIPULATOR"

    # Get metric definitions for tooltips
    def _beneish_cite(metric_key: str, line_item: str, filing_type: str, period: str, raw_value: float | None) -> Citation:
        defn = BENEISH_DEFINITIONS.get(metric_key)
        return _cite(
            line_item, filing_type, period, raw_value,
            formula=defn.formula if defn else "",
            description=defn.description if defn else "",
        )

    return BeneishMScore(
        composite=round(composite, 4) if composite is not None else None,
        interpretation=interpretation,
        components=BeneishMScoreComponents(
            dsri=MetricComponent(value=round(dsri, 4) if dsri is not None else None, citation=_beneish_cite("dsri", "Net Receivables / Revenue", "balance_sheet, financials", f"{period_curr} vs {period_prior}", recv_curr)),
            gmi=MetricComponent(value=round(gmi, 4) if gmi is not None else None, citation=_beneish_cite("gmi", "Gross Profit / Revenue", "financials", f"{period_curr} vs {period_prior}", gp_curr)),
            aqi=MetricComponent(value=round(aqi, 4) if aqi is not None else None, citation=_beneish_cite("aqi", "Asset Quality Index", "balance_sheet", f"{period_curr} vs {period_prior}", ta_curr)),
            sgi=MetricComponent(value=round(sgi, 4) if sgi is not None else None, citation=_beneish_cite("sgi", "Revenue Growth", "financials", f"{period_curr} vs {period_prior}", rev_curr)),
            depi=MetricComponent(value=round(depi, 4) if depi is not None else None, citation=_beneish_cite("depi", "Depreciation Index", "balance_sheet, financials", f"{period_curr} vs {period_prior}", dep_curr)),
            sgai=MetricComponent(value=round(sgai, 4) if sgai is not None else None, citation=_beneish_cite("sgai", "SGA / Revenue", "financials", f"{period_curr} vs {period_prior}", sga_curr)),
            lvgi=MetricComponent(value=round(lvgi, 4) if lvgi is not None else None, citation=_beneish_cite("lvgi", "Leverage Index", "balance_sheet", f"{period_curr} vs {period_prior}", tl_curr)),
            tata=MetricComponent(value=round(tata, 4) if tata is not None else None, citation=_beneish_cite("tata", "Total Accruals / Total Assets", "financials, cashflow, balance_sheet", period_curr, ni_curr)),
        ),
        thresholds=BeneishThresholds(),
    )


# ─── Altman Z-Score ─────────────────────────────────────────────────

def compute_altman_z_score(financials: dict, balance_sheet: dict, info: dict) -> AltmanZScore:
    """Compute Altman Z-Score (standard and SaaS-modified variants)."""
    # Find first valid period to skip NaN placeholders
    base_offset_fin = _find_first_valid_period(financials, REVENUE_FIELDS)
    base_offset_bs = _find_first_valid_period(balance_sheet, TOTAL_ASSETS_FIELDS)

    period = _get_period_label(financials, 0, base_offset_fin)

    ta = _get_field(balance_sheet, TOTAL_ASSETS_FIELDS, 0, base_offset_bs)
    ca = _get_field(balance_sheet, CURRENT_ASSETS_FIELDS, 0, base_offset_bs)
    cl = _get_field(balance_sheet, CURRENT_LIABILITIES_FIELDS, 0, base_offset_bs)
    re = _get_field(balance_sheet, RETAINED_EARNINGS_FIELDS, 0, base_offset_bs)
    ebit = _get_field(financials, EBIT_FIELDS, 0, base_offset_fin)
    revenue = _get_field(financials, REVENUE_FIELDS, 0, base_offset_fin)
    tl = _get_field(balance_sheet, TOTAL_LIABILITIES_FIELDS, 0, base_offset_bs)
    market_cap = info.get("marketCap") if isinstance(info, dict) else None

    # X1 = Working Capital / Total Assets
    x1 = None
    if ca is not None and cl is not None and ta:
        x1 = (ca - cl) / ta

    # X2 = Retained Earnings / Total Assets
    x2 = safe_divide(re, ta)

    # X3 = EBIT / Total Assets
    x3 = safe_divide(ebit, ta)

    # X4 = Market Cap / Total Liabilities
    x4 = safe_divide(market_cap, tl) if market_cap else None

    # X5 = Revenue / Total Assets
    x5 = safe_divide(revenue, ta)

    # Standard Z-Score = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
    standard_score = None
    std_components = [x1, x2, x3, x4, x5]
    if all(c is not None for c in std_components):
        standard_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

    std_zone = None
    if standard_score is not None:
        if standard_score > 2.99:
            std_zone = "SAFE"
        elif standard_score >= 1.81:
            std_zone = "GREY"
        else:
            std_zone = "DISTRESS"

    def _comp(name: str, val: float | None, item: str, src: str) -> tuple[str, MetricComponent]:
        defn = ALTMAN_DEFINITIONS.get(name)
        return (name, MetricComponent(
            value=round(val, 4) if val is not None else None,
            citation=_cite(item, src, period, val, formula=defn.formula if defn else "", description=defn.description if defn else "")
        ))

    standard = AltmanZScoreVariant(
        score=round(standard_score, 4) if standard_score is not None else None,
        zone=std_zone,
        components=dict([
            _comp("x1", x1, "Working Capital / Total Assets", "balance_sheet"),
            _comp("x2", x2, "Retained Earnings / Total Assets", "balance_sheet"),
            _comp("x3", x3, "EBIT / Total Assets", "financials, balance_sheet"),
            _comp("x4", x4, "Market Cap / Total Liabilities", "info, balance_sheet"),
            _comp("x5", x5, "Revenue / Total Assets", "financials, balance_sheet"),
        ]),
    )

    # SaaS-modified: re-weights X4 and X5, drops asset-heavy assumptions
    # Z = 3.25 + 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4 (no X5 for asset-light)
    saas_score = None
    saas_components = [x1, x2, x3, x4]
    if all(c is not None for c in saas_components):
        saas_score = 3.25 + 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4

    saas_zone = None
    if saas_score is not None:
        if saas_score > 2.6:
            saas_zone = "SAFE"
        elif saas_score >= 1.1:
            saas_zone = "GREY"
        else:
            saas_zone = "DISTRESS"

    saas_modified = AltmanZScoreVariant(
        score=round(saas_score, 4) if saas_score is not None else None,
        zone=saas_zone,
        components=dict([
            _comp("x1", x1, "Working Capital / Total Assets", "balance_sheet"),
            _comp("x2", x2, "Retained Earnings / Total Assets", "balance_sheet"),
            _comp("x3", x3, "EBIT / Total Assets", "financials, balance_sheet"),
            _comp("x4", x4, "Market Cap / Total Liabilities", "info, balance_sheet"),
        ]),
        disclaimer="Modified variant for asset-light/SaaS companies — not academically validated",
    )

    return AltmanZScore(standard=standard, saas_modified=saas_modified)


# ─── SaaS Metrics ───────────────────────────────────────────────────

def compute_rule_of_40(financials: dict, cashflow: dict) -> RuleOf40:
    """Rule of 40 = Revenue Growth % + FCF Margin %."""
    # Find first valid period to skip NaN placeholders
    base_offset_fin = _find_first_valid_period(financials, REVENUE_FIELDS)
    base_offset_cf = _find_first_valid_period(cashflow, OPERATING_CF_FIELDS)

    period_curr = _get_period_label(financials, 0, base_offset_fin)

    rev_curr = _get_field(financials, REVENUE_FIELDS, 0, base_offset_fin)
    rev_prior = _get_field(financials, REVENUE_FIELDS, 1, base_offset_fin)
    ocf = _get_field(cashflow, OPERATING_CF_FIELDS, 0, base_offset_cf)
    capex = _get_field(cashflow, ["Capital Expenditure", "Capital Expenditures"], 0, base_offset_cf)

    rev_growth = pct_change(rev_curr, rev_prior)

    fcf = None
    if ocf is not None and capex is not None:
        fcf = ocf - abs(capex)

    fcf_margin = None
    if fcf is not None and rev_curr and rev_curr != 0:
        fcf_margin = (fcf / rev_curr) * 100

    score = None
    if rev_growth is not None and fcf_margin is not None:
        score = rev_growth + fcf_margin

    interpretation = None
    if score is not None:
        if score >= 40:
            interpretation = "PASSING"
        elif score >= 25:
            interpretation = "MARGINAL"
        else:
            interpretation = "FAILING"

    r40_defn = SAAS_DEFINITIONS.get("rule_of_40")
    return RuleOf40(
        score=round(score, 2) if score is not None else None,
        revenue_growth_percent=round(rev_growth, 2) if rev_growth is not None else None,
        fcf_margin_percent=round(fcf_margin, 2) if fcf_margin is not None else None,
        interpretation=interpretation,
        citations={
            "revenue_current": _cite("Total Revenue", "financials", period_curr, rev_curr, formula=r40_defn.formula if r40_defn else "", description=r40_defn.description if r40_defn else ""),
            "revenue_prior": _cite("Total Revenue (prior)", "financials", _get_period_label(financials, 1, base_offset_fin), rev_prior),
            "operating_cash_flow": _cite("Operating Cash Flow", "cashflow", period_curr, ocf),
            "capex": _cite("Capital Expenditure", "cashflow", period_curr, capex),
        },
    )


def compute_magic_number(financials: dict, quarterly_financials: dict) -> MagicNumber:
    """Magic Number = (Net New ARR) / (Prior Quarter S&M Spend).
    Approximated as: (QoQ Revenue Delta * 4) / Prior Q SGA.
    """
    # Find first valid period to skip NaN placeholders
    base_offset_qfin = _find_first_valid_period(quarterly_financials, REVENUE_FIELDS)

    period = _get_period_label(quarterly_financials, 0, base_offset_qfin)

    q_rev_curr = _get_field(quarterly_financials, REVENUE_FIELDS, 0, base_offset_qfin)
    q_rev_prior = _get_field(quarterly_financials, REVENUE_FIELDS, 1, base_offset_qfin)
    q_sga_prior = _get_field(quarterly_financials, SGA_FIELDS, 1, base_offset_qfin)

    net_new_arr = None
    if q_rev_curr is not None and q_rev_prior is not None:
        net_new_arr = (q_rev_curr - q_rev_prior) * 4

    score = safe_divide(net_new_arr, q_sga_prior) if q_sga_prior and q_sga_prior != 0 else None

    interpretation = None
    if score is not None:
        if score >= 1.0:
            interpretation = "EFFICIENT"
        elif score >= 0.5:
            interpretation = "MODERATE"
        else:
            interpretation = "INEFFICIENT"

    mn_defn = SAAS_DEFINITIONS.get("magic_number")
    return MagicNumber(
        score=round(score, 4) if score is not None else None,
        net_new_arr=round(net_new_arr, 2) if net_new_arr is not None else None,
        sales_and_marketing_spend=round(q_sga_prior, 2) if q_sga_prior is not None else None,
        interpretation=interpretation,
        citations={
            "quarterly_revenue_current": _cite("Quarterly Revenue", "quarterly_financials", period, q_rev_curr, formula=mn_defn.formula if mn_defn else "", description=mn_defn.description if mn_defn else ""),
            "quarterly_revenue_prior": _cite("Quarterly Revenue (prior)", "quarterly_financials", _get_period_label(quarterly_financials, 1, base_offset_qfin), q_rev_prior),
            "quarterly_sga_prior": _cite("SGA Expense (prior Q)", "quarterly_financials", _get_period_label(quarterly_financials, 1, base_offset_qfin), q_sga_prior),
        },
    )


# ─── Orchestration ──────────────────────────────────────────────────

def run_forensic_analysis(data: dict) -> ForensicMetrics:
    """Run all forensic calculations on fetched financial data."""
    financials = data.get("financials", {})
    balance_sheet = data.get("balance_sheet", {})
    cashflow = data.get("cashflow", {})
    quarterly_financials = data.get("quarterly_financials", {})
    info = data.get("info", {})

    return ForensicMetrics(
        beneish_m_score=compute_beneish_m_score(financials, balance_sheet, cashflow),
        altman_z_score=compute_altman_z_score(financials, balance_sheet, info),
        rule_of_40=compute_rule_of_40(financials, cashflow),
        magic_number=compute_magic_number(financials, quarterly_financials),
    )


# ─── Comprehensive Analysis (forensic + general metrics) ─────────────

def run_comprehensive_analysis(data: dict) -> ComprehensiveAnalysis:
    """Run all forensic + general metric calculations on fetched financial data.

    Orchestrates:
    1. Existing forensic scores (Beneish M-Score, Altman Z-Score)
    2. New general metrics (profitability, leverage, cash flow, growth, valuation,
       shareholder returns, sentiment)
    3. Sector detection and conditional sector-specific metrics (e.g., SaaS)
    """
    from app.services.general_metrics_engine import (
        compute_profitability_metrics,
        compute_leverage_metrics,
        compute_cash_flow_metrics,
        compute_growth_metrics,
        compute_valuation_metrics,
        compute_shareholder_metrics,
        compute_sentiment_metrics,
    )
    from app.services.sector_service import detect_sector_category, get_sector_specific_metrics

    financials = data.get("financials", {})
    balance_sheet = data.get("balance_sheet", {})
    cashflow = data.get("cashflow", {})
    info = data.get("info", {})

    # 1. Existing forensic scores
    beneish = compute_beneish_m_score(financials, balance_sheet, cashflow)
    altman = compute_altman_z_score(financials, balance_sheet, info)

    # 2. New general metrics
    profitability = compute_profitability_metrics(info, financials)
    leverage = compute_leverage_metrics(info, balance_sheet)
    cash_flow = compute_cash_flow_metrics(info, financials, cashflow)
    growth = compute_growth_metrics(info, financials, cashflow)
    valuation = compute_valuation_metrics(info)
    shareholder = compute_shareholder_metrics(info)
    sentiment = compute_sentiment_metrics(info)

    # 3. Sector detection and conditional metrics
    sector_cat = detect_sector_category(info)
    sector_specific = get_sector_specific_metrics(sector_cat, data)

    return ComprehensiveAnalysis(
        beneish_m_score=beneish,
        altman_z_score=altman,
        profitability=profitability,
        leverage=leverage,
        cash_flow=cash_flow,
        growth=growth,
        valuation=valuation,
        shareholder_returns=shareholder,
        sentiment=sentiment,
        sector_category=sector_cat.value,
        sector_specific=sector_specific,
    )
