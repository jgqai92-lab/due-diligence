"""General metrics engine -- sector-agnostic financial calculations.

Computes profitability, leverage, cash flow quality, growth, valuation,
shareholder returns, and sentiment metrics from yfinance data.

Follows the same pattern as forensic_engine.py: extract from yfinance data,
return typed Pydantic models with citations, handle missing data gracefully.
"""

import logging

from app.schemas.analysis import (
    Citation,
    MetricComponent,
    ProfitabilityMetrics,
    LeverageMetrics,
    CashFlowMetrics,
    GrowthMetrics,
    ValuationMetrics,
    ShareholderMetrics,
    SentimentMetrics,
)
from app.utils.calculations import safe_divide, pct_change
from app.services.metric_definitions import (
    PROFITABILITY_DEFINITIONS,
    LEVERAGE_DEFINITIONS,
    CASH_FLOW_DEFINITIONS,
    GROWTH_DEFINITIONS,
    VALUATION_DEFINITIONS,
    SHAREHOLDER_DEFINITIONS,
    SENTIMENT_DEFINITIONS,
)

logger = logging.getLogger(__name__)


# ─── Field name constants (reused from forensic_engine where possible) ──────

REVENUE_FIELDS = ["Total Revenue", "Revenue", "Operating Revenue"]
GROSS_PROFIT_FIELDS = ["Gross Profit"]
OPERATING_INCOME_FIELDS = ["Operating Income", "Operating Revenue"]
NET_INCOME_FIELDS = ["Net Income", "Net Income Common Stockholders"]
EBIT_FIELDS = ["EBIT", "Ebit"]
EBITDA_FIELDS = ["EBITDA", "Ebitda", "Normalized EBITDA"]
INTEREST_EXPENSE_FIELDS = ["Interest Expense", "Interest Expense Non Operating", "Net Interest Income"]
TOTAL_ASSETS_FIELDS = ["Total Assets"]
TOTAL_LIABILITIES_FIELDS = ["Total Liabilities Net Minority Interest", "Total Liabilities", "Total Liab"]
CURRENT_ASSETS_FIELDS = ["Current Assets", "Total Current Assets"]
CURRENT_LIABILITIES_FIELDS = ["Current Liabilities", "Total Current Liabilities"]
TOTAL_DEBT_FIELDS = ["Total Debt", "Long Term Debt", "Long Term Debt And Capital Lease Obligation"]
STOCKHOLDERS_EQUITY_FIELDS = [
    "Stockholders Equity", "Total Stockholders Equity",
    "Stockholders' Equity", "Total Equity Gross Minority Interest",
]
OPERATING_CF_FIELDS = ["Operating Cash Flow", "Total Cash From Operating Activities"]
CAPEX_FIELDS = ["Capital Expenditure", "Capital Expenditures"]
TAX_RATE_FIELDS = ["Tax Rate For Calcs", "Tax Rate"]
INVENTORY_FIELDS = ["Inventory", "Inventories"]
CASH_FIELDS = ["Cash And Cash Equivalents", "Cash", "Cash Cash Equivalents And Short Term Investments"]


# ─── Helpers ──────────────────────────────────────────────────────────────


def _find_first_valid_period(data: dict, key_fields: list[str] | None = None) -> int:
    """Find the first period index that contains real data (not all NaN).

    yfinance sometimes returns unreported future periods with all NaN values.
    """
    if not data or not isinstance(data, dict):
        return 0

    periods = list(data.keys())
    for idx, period_key in enumerate(periods):
        period_data = data.get(period_key, {})
        if not isinstance(period_data, dict):
            continue
        if key_fields is None:
            for value in period_data.values():
                if value is not None:
                    try:
                        float(value)
                        return idx
                    except (ValueError, TypeError):
                        continue
        else:
            for field in key_fields:
                value = period_data.get(field)
                if value is not None:
                    try:
                        float(value)
                        return idx
                    except (ValueError, TypeError):
                        continue
    return 0


def _get_field(data: dict, field_names: list[str], period_idx: int = 0, base_period_offset: int = 0) -> float | None:
    """Extract a numeric value from yfinance data, trying multiple field name variants.

    Structure: { "2024-09-28T00:00:00.000Z": { "Total Revenue": 391035000000, ... }, ... }
    """
    if not data or not isinstance(data, dict):
        return None

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


def _get_period_label(data: dict, idx: int = 0, base_period_offset: int = 0) -> str:
    """Get period label string, adjusting for base period offset."""
    if not data:
        return "N/A"
    periods = list(data.keys())
    adjusted_idx = idx + base_period_offset
    if adjusted_idx < len(periods):
        return periods[adjusted_idx][:10]
    return "N/A"


def _cite(
    line_item: str,
    filing_type: str,
    period: str,
    raw_value: float | None,
    formula: str = "",
    description: str = "",
) -> Citation:
    """Create a Citation object."""
    return Citation(
        line_item=line_item,
        filing_type=filing_type,
        period=period,
        raw_value=raw_value,
        source=f"yfinance.{filing_type}",
        formula=formula,
        description=description,
    )


def _info_cite(field_name: str, raw_value: float | None, formula: str = "", description: str = "") -> Citation:
    """Create a Citation object for a value sourced from yfinance info dict."""
    return Citation(
        line_item=field_name,
        filing_type="info",
        period="TTM",
        raw_value=raw_value,
        source="yfinance.info",
        formula=formula,
        description=description,
    )


def _metric(value: float | None, citation: Citation, round_digits: int = 4) -> MetricComponent:
    """Create a MetricComponent with optional rounding."""
    return MetricComponent(
        value=round(value, round_digits) if value is not None else None,
        citation=citation,
    )


def _safe_info(info: dict, field: str) -> float | None:
    """Safely extract a numeric value from the info dict."""
    val = info.get(field)
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# ─── Profitability & Efficiency ────────────────────────────────────────


def compute_profitability_metrics(info: dict, financials: dict) -> ProfitabilityMetrics:
    """Compute profitability metrics: margins, ROE, ROA, ROIC.

    Prefers info dict values (TTM), falls back to financial statement calculation.
    """
    base_offset_fin = _find_first_valid_period(financials, REVENUE_FIELDS)
    period = _get_period_label(financials, 0, base_offset_fin)

    # Helper to get definition
    def _defn(key: str):
        return PROFITABILITY_DEFINITIONS.get(key)

    # Gross Margin
    gross_margin_val = _safe_info(info, "grossMargins")
    if gross_margin_val is None:
        gp = _get_field(financials, GROSS_PROFIT_FIELDS, 0, base_offset_fin)
        rev = _get_field(financials, REVENUE_FIELDS, 0, base_offset_fin)
        gross_margin_val = safe_divide(gp, rev)
    d = _defn("gross_margin")
    gross_margin = _metric(gross_margin_val, _info_cite("grossMargins", gross_margin_val, d.formula if d else "", d.description if d else ""))

    # Operating Margin
    op_margin_val = _safe_info(info, "operatingMargins")
    if op_margin_val is None:
        op_inc = _get_field(financials, OPERATING_INCOME_FIELDS, 0, base_offset_fin)
        rev = _get_field(financials, REVENUE_FIELDS, 0, base_offset_fin)
        op_margin_val = safe_divide(op_inc, rev)
    d = _defn("operating_margin")
    operating_margin = _metric(op_margin_val, _info_cite("operatingMargins", op_margin_val, d.formula if d else "", d.description if d else ""))

    # Net Margin
    net_margin_val = _safe_info(info, "profitMargins")
    if net_margin_val is None:
        ni = _get_field(financials, NET_INCOME_FIELDS, 0, base_offset_fin)
        rev = _get_field(financials, REVENUE_FIELDS, 0, base_offset_fin)
        net_margin_val = safe_divide(ni, rev)
    d = _defn("net_margin")
    net_margin = _metric(net_margin_val, _info_cite("profitMargins", net_margin_val, d.formula if d else "", d.description if d else ""))

    # ROE
    roe_val = _safe_info(info, "returnOnEquity")
    d = _defn("roe")
    roe = _metric(roe_val, _info_cite("returnOnEquity", roe_val, d.formula if d else "", d.description if d else ""))

    # ROA
    roa_val = _safe_info(info, "returnOnAssets")
    d = _defn("roa")
    roa = _metric(roa_val, _info_cite("returnOnAssets", roa_val, d.formula if d else "", d.description if d else ""))

    # ROIC = NOPAT / Invested Capital
    # NOPAT = EBIT * (1 - tax_rate); Invested Capital = Total Debt + Equity - Cash
    roic_val = None
    ebit = _get_field(financials, EBIT_FIELDS, 0, base_offset_fin)
    tax_rate = _safe_info(info, "taxRate") or _safe_info(info, "effectiveTaxRate")
    if tax_rate is None:
        # Approximate tax rate: 21% (US corporate)
        tax_rate = 0.21
    if ebit is not None:
        nopat = ebit * (1 - tax_rate)
        # Need balance sheet for invested capital — use info fields as proxy
        total_debt = _safe_info(info, "totalDebt")
        equity = _safe_info(info, "totalStockholderEquity") or _safe_info(info, "bookValue")
        cash = _safe_info(info, "totalCash")
        if total_debt is not None and equity is not None:
            invested_capital = total_debt + equity - (cash or 0)
            roic_val = safe_divide(nopat, invested_capital)
    d = _defn("roic")
    roic = _metric(roic_val, _cite("EBIT * (1 - tax) / Invested Capital", "financials", period, roic_val, d.formula if d else "", d.description if d else ""))

    return ProfitabilityMetrics(
        gross_margin=gross_margin,
        operating_margin=operating_margin,
        net_margin=net_margin,
        roe=roe,
        roa=roa,
        roic=roic,
    )


# ─── Leverage & Solvency ──────────────────────────────────────────────


def compute_leverage_metrics(info: dict, balance_sheet: dict) -> LeverageMetrics:
    """Compute leverage metrics: D/E, interest coverage, current/quick ratio, net debt/EBITDA."""
    base_offset_bs = _find_first_valid_period(balance_sheet, TOTAL_ASSETS_FIELDS)
    period = _get_period_label(balance_sheet, 0, base_offset_bs)

    def _defn(key: str):
        return LEVERAGE_DEFINITIONS.get(key)

    # Debt-to-Equity
    dte_val = _safe_info(info, "debtToEquity")
    # yfinance returns D/E as a percentage (e.g., 150 meaning 1.5x), normalize
    if dte_val is not None:
        dte_val = dte_val / 100.0 if dte_val > 10 else dte_val
    d = _defn("debt_to_equity")
    debt_to_equity = _metric(dte_val, _info_cite("debtToEquity", dte_val, d.formula if d else "", d.description if d else ""))

    # Interest Coverage = EBIT / Interest Expense
    ebit = _safe_info(info, "ebitda")  # Use EBITDA as proxy if EBIT not in info
    interest_exp = _safe_info(info, "interestExpense") or _safe_info(info, "totalInterestExpense")
    ic_val = None
    if ebit is not None and interest_exp is not None and interest_exp != 0:
        # Interest expense is often reported as negative in yfinance
        ic_val = safe_divide(ebit, abs(interest_exp))
    d = _defn("interest_coverage")
    interest_coverage = _metric(ic_val, _info_cite("EBITDA / Interest Expense", ic_val, d.formula if d else "", d.description if d else ""))

    # Current Ratio
    cr_val = _safe_info(info, "currentRatio")
    d = _defn("current_ratio")
    current_ratio = _metric(cr_val, _info_cite("currentRatio", cr_val, d.formula if d else "", d.description if d else ""))

    # Quick Ratio
    qr_val = _safe_info(info, "quickRatio")
    d = _defn("quick_ratio")
    quick_ratio = _metric(qr_val, _info_cite("quickRatio", qr_val, d.formula if d else "", d.description if d else ""))

    # Net Debt / EBITDA
    total_debt = _safe_info(info, "totalDebt")
    cash = _safe_info(info, "totalCash")
    ebitda = _safe_info(info, "ebitda")
    nd_ebitda_val = None
    if total_debt is not None and ebitda is not None and ebitda != 0:
        net_debt = total_debt - (cash or 0)
        nd_ebitda_val = safe_divide(net_debt, ebitda)
    d = _defn("net_debt_to_ebitda")
    net_debt_to_ebitda = _metric(nd_ebitda_val, _info_cite("(Total Debt - Cash) / EBITDA", nd_ebitda_val, d.formula if d else "", d.description if d else ""))

    return LeverageMetrics(
        debt_to_equity=debt_to_equity,
        interest_coverage=interest_coverage,
        current_ratio=current_ratio,
        quick_ratio=quick_ratio,
        net_debt_to_ebitda=net_debt_to_ebitda,
    )


# ─── Cash Flow Quality ────────────────────────────────────────────────


def compute_cash_flow_metrics(info: dict, financials: dict, cashflow: dict) -> CashFlowMetrics:
    """Compute cash flow quality metrics: FCF yield, OCF/NI, FCF margin, capex/revenue."""
    base_offset_fin = _find_first_valid_period(financials, REVENUE_FIELDS)
    base_offset_cf = _find_first_valid_period(cashflow, OPERATING_CF_FIELDS)
    period = _get_period_label(cashflow, 0, base_offset_cf)

    def _defn(key: str):
        return CASH_FLOW_DEFINITIONS.get(key)

    revenue = _get_field(financials, REVENUE_FIELDS, 0, base_offset_fin)
    net_income = _get_field(financials, NET_INCOME_FIELDS, 0, base_offset_fin)
    ocf = _get_field(cashflow, OPERATING_CF_FIELDS, 0, base_offset_cf)
    capex = _get_field(cashflow, CAPEX_FIELDS, 0, base_offset_cf)
    market_cap = _safe_info(info, "marketCap")

    # Free Cash Flow
    fcf = None
    if ocf is not None and capex is not None:
        fcf = ocf - abs(capex)  # capex is sometimes negative in yfinance

    # FCF Yield = FCF / Market Cap
    fcf_yield_val = safe_divide(fcf, market_cap)
    d = _defn("fcf_yield")
    fcf_yield = _metric(fcf_yield_val, _cite("FCF / Market Cap", "cashflow, info", period, fcf_yield_val, d.formula if d else "", d.description if d else ""))

    # OCF / Net Income (accruals quality — higher is better)
    ocf_ni_val = safe_divide(ocf, net_income) if net_income and net_income != 0 else None
    d = _defn("ocf_to_net_income")
    ocf_to_net_income = _metric(ocf_ni_val, _cite("Operating CF / Net Income", "cashflow, financials", period, ocf_ni_val, d.formula if d else "", d.description if d else ""))

    # FCF Margin = FCF / Revenue
    fcf_margin_val = safe_divide(fcf, revenue)
    d = _defn("fcf_margin")
    fcf_margin = _metric(fcf_margin_val, _cite("FCF / Revenue", "cashflow, financials", period, fcf_margin_val, d.formula if d else "", d.description if d else ""))

    # CapEx % of Revenue = |CapEx| / Revenue
    capex_rev_val = safe_divide(abs(capex) if capex is not None else None, revenue)
    d = _defn("capex_to_revenue")
    capex_to_revenue = _metric(capex_rev_val, _cite("CapEx / Revenue", "cashflow, financials", period, capex_rev_val, d.formula if d else "", d.description if d else ""))

    return CashFlowMetrics(
        fcf_yield=fcf_yield,
        ocf_to_net_income=ocf_to_net_income,
        fcf_margin=fcf_margin,
        capex_to_revenue=capex_to_revenue,
    )


# ─── Growth ────────────────────────────────────────────────────────────


def compute_growth_metrics(info: dict, financials: dict, cashflow: dict) -> GrowthMetrics:
    """Compute growth metrics: revenue/earnings/FCF growth YoY, revenue CAGR 3Y."""
    base_offset_fin = _find_first_valid_period(financials, REVENUE_FIELDS)
    base_offset_cf = _find_first_valid_period(cashflow, OPERATING_CF_FIELDS)

    period_curr = _get_period_label(financials, 0, base_offset_fin)
    period_prior = _get_period_label(financials, 1, base_offset_fin)

    def _defn(key: str):
        return GROWTH_DEFINITIONS.get(key)

    # Revenue Growth YoY — prefer info, fall back to calculated
    rev_growth_val = _safe_info(info, "revenueGrowth")
    if rev_growth_val is None:
        rev_curr = _get_field(financials, REVENUE_FIELDS, 0, base_offset_fin)
        rev_prior = _get_field(financials, REVENUE_FIELDS, 1, base_offset_fin)
        pct = pct_change(rev_curr, rev_prior)
        rev_growth_val = pct / 100.0 if pct is not None else None
    d = _defn("revenue_growth_yoy")
    revenue_growth_yoy = _metric(
        rev_growth_val,
        _info_cite("revenueGrowth", rev_growth_val, d.formula if d else "", d.description if d else ""),
    )

    # Earnings Growth YoY — prefer info, fall back to calculated
    earn_growth_val = _safe_info(info, "earningsGrowth")
    if earn_growth_val is None:
        ni_curr = _get_field(financials, NET_INCOME_FIELDS, 0, base_offset_fin)
        ni_prior = _get_field(financials, NET_INCOME_FIELDS, 1, base_offset_fin)
        pct = pct_change(ni_curr, ni_prior)
        earn_growth_val = pct / 100.0 if pct is not None else None
    d = _defn("earnings_growth_yoy")
    earnings_growth_yoy = _metric(
        earn_growth_val,
        _info_cite("earningsGrowth", earn_growth_val, d.formula if d else "", d.description if d else ""),
    )

    # FCF Growth YoY — calculated from cashflow
    ocf_curr = _get_field(cashflow, OPERATING_CF_FIELDS, 0, base_offset_cf)
    capex_curr = _get_field(cashflow, CAPEX_FIELDS, 0, base_offset_cf)
    ocf_prior = _get_field(cashflow, OPERATING_CF_FIELDS, 1, base_offset_cf)
    capex_prior = _get_field(cashflow, CAPEX_FIELDS, 1, base_offset_cf)

    fcf_curr = None
    if ocf_curr is not None and capex_curr is not None:
        fcf_curr = ocf_curr - abs(capex_curr)
    fcf_prior = None
    if ocf_prior is not None and capex_prior is not None:
        fcf_prior = ocf_prior - abs(capex_prior)

    fcf_growth_pct = pct_change(fcf_curr, fcf_prior)
    fcf_growth_val = fcf_growth_pct / 100.0 if fcf_growth_pct is not None else None
    d = _defn("fcf_growth_yoy")
    fcf_growth_yoy = _metric(
        fcf_growth_val,
        _cite("FCF Growth YoY", "cashflow", f"{period_curr} vs {period_prior}", fcf_growth_val, d.formula if d else "", d.description if d else ""),
    )

    # Revenue CAGR 3Y = (Rev_curr / Rev_3yr_ago)^(1/3) - 1
    rev_curr = _get_field(financials, REVENUE_FIELDS, 0, base_offset_fin)
    rev_3yr = _get_field(financials, REVENUE_FIELDS, 3, base_offset_fin)  # 3 periods back
    cagr_val = None
    if rev_curr is not None and rev_3yr is not None and rev_3yr > 0 and rev_curr > 0:
        try:
            cagr_val = (rev_curr / rev_3yr) ** (1.0 / 3.0) - 1
        except (ValueError, ZeroDivisionError):
            cagr_val = None

    period_3yr = _get_period_label(financials, 3, base_offset_fin)
    d = _defn("revenue_cagr_3y")
    revenue_cagr_3y = _metric(
        cagr_val,
        _cite("Revenue CAGR 3Y", "financials", f"{period_curr} to {period_3yr}", cagr_val, d.formula if d else "", d.description if d else ""),
    )

    return GrowthMetrics(
        revenue_growth_yoy=revenue_growth_yoy,
        earnings_growth_yoy=earnings_growth_yoy,
        fcf_growth_yoy=fcf_growth_yoy,
        revenue_cagr_3y=revenue_cagr_3y,
    )


# ─── Valuation ─────────────────────────────────────────────────────────


def compute_valuation_metrics(info: dict) -> ValuationMetrics:
    """Compute valuation multiples from yfinance info dict."""
    def _defn(key: str):
        return VALUATION_DEFINITIONS.get(key)

    d = _defn("pe_trailing")
    pe_trailing_val = _safe_info(info, "trailingPE")
    pe_trailing = _metric(pe_trailing_val, _info_cite("trailingPE", pe_trailing_val, d.formula if d else "", d.description if d else ""))

    d = _defn("pe_forward")
    pe_forward_val = _safe_info(info, "forwardPE")
    pe_forward = _metric(pe_forward_val, _info_cite("forwardPE", pe_forward_val, d.formula if d else "", d.description if d else ""))

    d = _defn("ev_to_ebitda")
    ev_ebitda_val = _safe_info(info, "enterpriseToEbitda")
    ev_to_ebitda = _metric(ev_ebitda_val, _info_cite("enterpriseToEbitda", ev_ebitda_val, d.formula if d else "", d.description if d else ""))

    # Price/FCF = Market Cap / FCF
    market_cap = _safe_info(info, "marketCap")
    fcf = _safe_info(info, "freeCashflow")
    price_fcf_val = safe_divide(market_cap, fcf) if fcf and fcf > 0 else None
    d = _defn("price_to_fcf")
    price_to_fcf = _metric(price_fcf_val, _info_cite("marketCap / freeCashflow", price_fcf_val, d.formula if d else "", d.description if d else ""))

    d = _defn("price_to_sales")
    ps_val = _safe_info(info, "priceToSalesTrailing12Months")
    price_to_sales = _metric(ps_val, _info_cite("priceToSalesTrailing12Months", ps_val, d.formula if d else "", d.description if d else ""))

    d = _defn("peg_ratio")
    peg_val = _safe_info(info, "trailingPegRatio") or _safe_info(info, "pegRatio")
    peg_ratio = _metric(peg_val, _info_cite("trailingPegRatio", peg_val, d.formula if d else "", d.description if d else ""))

    return ValuationMetrics(
        pe_trailing=pe_trailing,
        pe_forward=pe_forward,
        ev_to_ebitda=ev_to_ebitda,
        price_to_fcf=price_to_fcf,
        price_to_sales=price_to_sales,
        peg_ratio=peg_ratio,
    )


# ─── Shareholder Returns ──────────────────────────────────────────────


def compute_shareholder_metrics(info: dict) -> ShareholderMetrics:
    """Compute shareholder return metrics: dividend yield, payout ratio."""
    def _defn(key: str):
        return SHAREHOLDER_DEFINITIONS.get(key)

    d = _defn("dividend_yield")
    div_yield_val = _safe_info(info, "dividendYield")
    dividend_yield = _metric(div_yield_val, _info_cite("dividendYield", div_yield_val, d.formula if d else "", d.description if d else ""))

    d = _defn("payout_ratio")
    payout_val = _safe_info(info, "payoutRatio")
    payout_ratio = _metric(payout_val, _info_cite("payoutRatio", payout_val, d.formula if d else "", d.description if d else ""))

    return ShareholderMetrics(
        dividend_yield=dividend_yield,
        payout_ratio=payout_ratio,
    )


# ─── Sentiment & Positioning ──────────────────────────────────────────


def compute_sentiment_metrics(info: dict) -> SentimentMetrics:
    """Compute sentiment metrics: analyst consensus, short interest, ownership."""
    def _defn(key: str):
        return SENTIMENT_DEFINITIONS.get(key)

    # Analyst rating (1=Strong Buy, 5=Sell)
    d = _defn("analyst_rating")
    rating_val = _safe_info(info, "recommendationMean")
    analyst_rating = _metric(rating_val, _info_cite("recommendationMean", rating_val, d.formula if d else "", d.description if d else ""))

    # Analyst count
    analyst_count_raw = info.get("numberOfAnalystOpinions")
    analyst_count = int(analyst_count_raw) if analyst_count_raw is not None else None

    # Analyst recommendation string
    analyst_recommendation = info.get("recommendationKey")

    # Short ratio (days to cover)
    d = _defn("short_ratio")
    short_ratio_val = _safe_info(info, "shortRatio")
    short_ratio = _metric(short_ratio_val, _info_cite("shortRatio", short_ratio_val, d.formula if d else "", d.description if d else ""))

    # Short % of float
    d = _defn("short_percent_float")
    short_pct_val = _safe_info(info, "shortPercentOfFloat")
    short_percent_float = _metric(short_pct_val, _info_cite("shortPercentOfFloat", short_pct_val, d.formula if d else "", d.description if d else ""))

    # Institutional ownership %
    d = _defn("institutional_pct")
    inst_pct_val = _safe_info(info, "heldPercentInstitutions")
    institutional_pct = _metric(inst_pct_val, _info_cite("heldPercentInstitutions", inst_pct_val, d.formula if d else "", d.description if d else ""))

    # Insider ownership %
    d = _defn("insider_pct")
    insider_pct_val = _safe_info(info, "heldPercentInsiders")
    insider_pct = _metric(insider_pct_val, _info_cite("heldPercentInsiders", insider_pct_val, d.formula if d else "", d.description if d else ""))

    return SentimentMetrics(
        analyst_rating=analyst_rating,
        analyst_count=analyst_count,
        analyst_recommendation=analyst_recommendation,
        short_ratio=short_ratio,
        short_percent_float=short_percent_float,
        institutional_pct=institutional_pct,
        insider_pct=insider_pct,
    )
