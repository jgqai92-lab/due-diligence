"""Metric definitions — formulas, descriptions, and interpretations for all financial metrics.

This module provides the educational content shown in hover tooltips, ensuring
users understand both HOW metrics are calculated and WHAT they mean.
"""

from dataclasses import dataclass


@dataclass
class MetricDefinition:
    """Definition of a financial metric for tooltip display."""
    formula: str
    description: str
    interpretation: str = ""  # Optional interpretation guidance


# ─── Beneish M-Score Components ──────────────────────────────────────────

BENEISH_DEFINITIONS = {
    "dsri": MetricDefinition(
        formula="DSRI = (Receivables_t / Revenue_t) / (Receivables_t-1 / Revenue_t-1)",
        description="Days Sales in Receivables Index measures changes in receivables relative to sales. A large increase may indicate revenue inflation.",
        interpretation=">1.0 suggests receivables growing faster than revenue — potential red flag",
    ),
    "gmi": MetricDefinition(
        formula="GMI = Gross Margin_t-1 / Gross Margin_t",
        description="Gross Margin Index compares prior year gross margin to current. Deteriorating margins may incentivize earnings manipulation.",
        interpretation=">1.0 indicates declining gross margins — watch for quality issues",
    ),
    "aqi": MetricDefinition(
        formula="AQI = (1 - (CA + PPE) / TA)_t / (1 - (CA + PPE) / TA)_t-1",
        description="Asset Quality Index measures the proportion of assets where future benefits are less certain (intangibles, deferred costs).",
        interpretation=">1.0 suggests increasing 'soft' assets — potential capitalization of expenses",
    ),
    "sgi": MetricDefinition(
        formula="SGI = Revenue_t / Revenue_t-1",
        description="Sales Growth Index. High growth companies face pressure to maintain growth and may be more likely to manipulate earnings.",
        interpretation="Not inherently bad, but high growth + other red flags = concern",
    ),
    "depi": MetricDefinition(
        formula="DEPI = Depreciation Rate_t-1 / Depreciation Rate_t",
        description="Depreciation Index compares depreciation rates. Slowing depreciation can inflate earnings.",
        interpretation=">1.0 suggests depreciation is slowing — may be extending asset lives",
    ),
    "sgai": MetricDefinition(
        formula="SGAI = (SGA_t / Revenue_t) / (SGA_t-1 / Revenue_t-1)",
        description="SG&A Index measures changes in sales, general & administrative expenses relative to sales.",
        interpretation=">1.0 indicates SG&A rising faster than sales — potential inefficiency",
    ),
    "lvgi": MetricDefinition(
        formula="LVGI = (Total Liabilities / Total Assets)_t / (Total Liabilities / Total Assets)_t-1",
        description="Leverage Index measures change in financial leverage. Increasing debt may pressure management to manipulate earnings.",
        interpretation=">1.0 indicates increasing leverage — watch debt covenant pressure",
    ),
    "tata": MetricDefinition(
        formula="TATA = (Net Income - Operating Cash Flow) / Total Assets",
        description="Total Accruals to Total Assets. High accruals relative to cash flow may indicate aggressive accounting.",
        interpretation="Higher values suggest more earnings from accruals vs. cash — scrutinize",
    ),
    "composite": MetricDefinition(
        formula="M = -4.84 + 0.92×DSRI + 0.53×GMI + 0.40×AQI + 0.89×SGI + 0.12×DEPI - 0.17×SGAI + 4.68×TATA - 0.33×LVGI",
        description="Beneish M-Score is a probabilistic model to detect earnings manipulation. Developed by Prof. Messod Beneish using data from SEC enforcement actions.",
        interpretation="< -2.22: Unlikely manipulator | -2.22 to -1.78: Grey zone | > -1.78: Likely manipulator",
    ),
}


# ─── Altman Z-Score Components ───────────────────────────────────────────

ALTMAN_DEFINITIONS = {
    "x1": MetricDefinition(
        formula="X1 = (Current Assets - Current Liabilities) / Total Assets",
        description="Working Capital / Total Assets measures short-term liquidity relative to firm size.",
        interpretation="Higher is better — indicates ability to meet short-term obligations",
    ),
    "x2": MetricDefinition(
        formula="X2 = Retained Earnings / Total Assets",
        description="Retained Earnings / Total Assets reflects cumulative profitability and firm age.",
        interpretation="Higher is better — mature, profitable firms have higher X2",
    ),
    "x3": MetricDefinition(
        formula="X3 = EBIT / Total Assets",
        description="EBIT / Total Assets measures operating profitability independent of leverage and taxes.",
        interpretation="Higher is better — core earning power of assets",
    ),
    "x4": MetricDefinition(
        formula="X4 = Market Cap / Total Liabilities",
        description="Market Value of Equity / Total Liabilities shows how much the firm's assets can decline before liabilities exceed assets.",
        interpretation="Higher is better — market confidence in solvency",
    ),
    "x5": MetricDefinition(
        formula="X5 = Revenue / Total Assets",
        description="Asset Turnover measures sales generating ability of assets.",
        interpretation="Industry-dependent — generally higher is better",
    ),
    "standard": MetricDefinition(
        formula="Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5",
        description="Altman Z-Score predicts bankruptcy probability within 2 years. Developed in 1968 using manufacturing firms.",
        interpretation="> 2.99: Safe zone | 1.81-2.99: Grey zone | < 1.81: Distress zone",
    ),
    "saas_modified": MetricDefinition(
        formula="Z = 3.25 + 6.56×X1 + 3.26×X2 + 6.72×X3 + 1.05×X4",
        description="Modified Z-Score for asset-light/SaaS companies. Removes asset turnover (X5) which penalizes service businesses.",
        interpretation="> 2.6: Safe | 1.1-2.6: Grey zone | < 1.1: Distress (thresholds are approximate)",
    ),
}


# ─── SaaS Metrics ────────────────────────────────────────────────────────

SAAS_DEFINITIONS = {
    "rule_of_40": MetricDefinition(
        formula="Rule of 40 = Revenue Growth % + FCF Margin %",
        description="The Rule of 40 is a benchmark for SaaS company health. Companies should target combined growth + profitability ≥ 40%.",
        interpretation="≥40: Healthy | 25-40: Marginal | <25: Needs improvement",
    ),
    "magic_number": MetricDefinition(
        formula="Magic Number = (Net New ARR) / (Prior Quarter S&M Spend)",
        description="Sales efficiency metric showing revenue generated per dollar spent on sales & marketing.",
        interpretation="≥1.0: Efficient (invest more) | 0.5-1.0: Moderate | <0.5: Inefficient",
    ),
}


# ─── Profitability Metrics ───────────────────────────────────────────────

PROFITABILITY_DEFINITIONS = {
    "gross_margin": MetricDefinition(
        formula="Gross Margin = Gross Profit / Revenue",
        description="Percentage of revenue remaining after cost of goods sold. Indicates pricing power and production efficiency.",
        interpretation="Higher is better — compare to industry peers",
    ),
    "operating_margin": MetricDefinition(
        formula="Operating Margin = Operating Income / Revenue",
        description="Percentage of revenue remaining after operating expenses. Shows operational efficiency.",
        interpretation="Higher is better — indicates strong cost control",
    ),
    "net_margin": MetricDefinition(
        formula="Net Margin = Net Income / Revenue",
        description="Percentage of revenue converted to profit after all expenses, taxes, and interest.",
        interpretation="Higher is better — bottom-line profitability",
    ),
    "roe": MetricDefinition(
        formula="ROE = Net Income / Shareholders' Equity",
        description="Return on Equity measures profit generated per dollar of shareholder investment.",
        interpretation="Higher is better — but very high ROE may indicate excessive leverage",
    ),
    "roa": MetricDefinition(
        formula="ROA = Net Income / Total Assets",
        description="Return on Assets measures how efficiently a company uses its assets to generate profit.",
        interpretation="Higher is better — asset-light businesses typically have higher ROA",
    ),
    "roic": MetricDefinition(
        formula="ROIC = NOPAT / Invested Capital = EBIT×(1-Tax) / (Debt + Equity - Cash)",
        description="Return on Invested Capital measures returns generated on all capital invested in the business.",
        interpretation="Should exceed cost of capital (WACC) — value creation test",
    ),
}


# ─── Leverage Metrics ────────────────────────────────────────────────────

LEVERAGE_DEFINITIONS = {
    "debt_to_equity": MetricDefinition(
        formula="D/E = Total Debt / Shareholders' Equity",
        description="Measures financial leverage — how much debt is used relative to equity financing.",
        interpretation="Lower is safer — but optimal leverage varies by industry",
    ),
    "interest_coverage": MetricDefinition(
        formula="Interest Coverage = EBIT / Interest Expense",
        description="Measures ability to pay interest on debt. How many times over can the company cover interest?",
        interpretation=">3x is comfortable | <1.5x is concerning | <1x means losing money on debt",
    ),
    "current_ratio": MetricDefinition(
        formula="Current Ratio = Current Assets / Current Liabilities",
        description="Measures short-term liquidity — ability to pay debts due within one year.",
        interpretation=">1.5 is healthy | <1.0 may indicate liquidity problems",
    ),
    "quick_ratio": MetricDefinition(
        formula="Quick Ratio = (Current Assets - Inventory) / Current Liabilities",
        description="More conservative liquidity measure excluding inventory (which may be hard to liquidate quickly).",
        interpretation=">1.0 is healthy | <0.5 may indicate liquidity risk",
    ),
    "net_debt_to_ebitda": MetricDefinition(
        formula="Net Debt/EBITDA = (Total Debt - Cash) / EBITDA",
        description="Measures how many years it would take to pay off debt using operating earnings.",
        interpretation="<2x is conservative | 2-4x is moderate | >4x is highly leveraged",
    ),
}


# ─── Cash Flow Metrics ───────────────────────────────────────────────────

CASH_FLOW_DEFINITIONS = {
    "fcf_yield": MetricDefinition(
        formula="FCF Yield = Free Cash Flow / Market Cap",
        description="Cash return to shareholders relative to market value. Similar to earnings yield but uses cash.",
        interpretation="Higher is better — compare to bond yields and peers",
    ),
    "ocf_to_net_income": MetricDefinition(
        formula="OCF/NI = Operating Cash Flow / Net Income",
        description="Cash conversion ratio — how much reported earnings convert to actual cash.",
        interpretation=">1.0 is healthy (cash > earnings) | <1.0 may indicate accrual concerns",
    ),
    "fcf_margin": MetricDefinition(
        formula="FCF Margin = Free Cash Flow / Revenue",
        description="Percentage of revenue converted to free cash flow available for shareholders.",
        interpretation="Higher is better — strong FCF margin = capital allocation flexibility",
    ),
    "capex_to_revenue": MetricDefinition(
        formula="CapEx/Revenue = Capital Expenditures / Revenue",
        description="Capital intensity — how much must be reinvested to maintain/grow the business.",
        interpretation="Lower is better for mature companies — asset-light is advantageous",
    ),
}


# ─── Growth Metrics ──────────────────────────────────────────────────────

GROWTH_DEFINITIONS = {
    "revenue_growth_yoy": MetricDefinition(
        formula="Revenue Growth = (Revenue_t - Revenue_t-1) / Revenue_t-1",
        description="Year-over-year revenue growth rate. Primary indicator of business momentum.",
        interpretation="Compare to industry growth — sustainable growth > market growth",
    ),
    "earnings_growth_yoy": MetricDefinition(
        formula="Earnings Growth = (EPS_t - EPS_t-1) / EPS_t-1",
        description="Year-over-year earnings growth. Should track with or exceed revenue growth.",
        interpretation="Earnings growing faster than revenue = improving margins",
    ),
    "fcf_growth_yoy": MetricDefinition(
        formula="FCF Growth = (FCF_t - FCF_t-1) / FCF_t-1",
        description="Year-over-year free cash flow growth. Most reliable growth metric.",
        interpretation="Consistent FCF growth = sustainable business model",
    ),
    "revenue_cagr_3y": MetricDefinition(
        formula="CAGR = (Revenue_t / Revenue_t-3)^(1/3) - 1",
        description="Compound Annual Growth Rate over 3 years. Smooths out year-to-year volatility.",
        interpretation="More reliable than single-year growth — shows trend",
    ),
}


# ─── Valuation Metrics ───────────────────────────────────────────────────

VALUATION_DEFINITIONS = {
    "pe_trailing": MetricDefinition(
        formula="P/E Trailing = Stock Price / Earnings Per Share (TTM)",
        description="Price-to-Earnings ratio using trailing twelve months earnings. Most common valuation metric.",
        interpretation="Lower = cheaper | Compare to growth rate and industry peers",
    ),
    "pe_forward": MetricDefinition(
        formula="P/E Forward = Stock Price / Expected EPS (next 12 months)",
        description="Forward P/E uses analyst estimates. More relevant for growing companies.",
        interpretation="Lower than trailing P/E suggests expected earnings growth",
    ),
    "ev_to_ebitda": MetricDefinition(
        formula="EV/EBITDA = (Market Cap + Debt - Cash) / EBITDA",
        description="Enterprise Value to EBITDA. Capital structure-neutral valuation metric.",
        interpretation="Better for comparing companies with different leverage — lower is cheaper",
    ),
    "price_to_fcf": MetricDefinition(
        formula="P/FCF = Market Cap / Free Cash Flow",
        description="Price to Free Cash Flow. Values company based on cash generation.",
        interpretation="More conservative than P/E — cash is harder to manipulate",
    ),
    "price_to_sales": MetricDefinition(
        formula="P/S = Market Cap / Revenue",
        description="Price-to-Sales ratio. Useful for unprofitable growth companies.",
        interpretation="Lower is cheaper — but must consider margin potential",
    ),
    "peg_ratio": MetricDefinition(
        formula="PEG = P/E Ratio / Earnings Growth Rate",
        description="Price/Earnings to Growth. Adjusts P/E for growth rate.",
        interpretation="<1.0 may be undervalued | >2.0 may be expensive relative to growth",
    ),
}


# ─── Shareholder Metrics ─────────────────────────────────────────────────

SHAREHOLDER_DEFINITIONS = {
    "dividend_yield": MetricDefinition(
        formula="Dividend Yield = Annual Dividends Per Share / Stock Price",
        description="Annual dividend return relative to stock price.",
        interpretation="Higher yield = more income | Very high yield may signal dividend cut risk",
    ),
    "payout_ratio": MetricDefinition(
        formula="Payout Ratio = Dividends / Net Income",
        description="Percentage of earnings paid out as dividends.",
        interpretation="<60% is sustainable | >100% means paying from reserves/debt",
    ),
}


# ─── Sentiment/Positioning Metrics ───────────────────────────────────────

SENTIMENT_DEFINITIONS = {
    "analyst_rating": MetricDefinition(
        formula="Mean of analyst recommendations (1=Strong Buy, 5=Sell)",
        description="Average analyst recommendation. Aggregated from sell-side research.",
        interpretation="<2.0 = Bullish consensus | >3.0 = Bearish consensus | Beware of herding",
    ),
    "short_ratio": MetricDefinition(
        formula="Short Ratio = Short Interest / Average Daily Volume",
        description="Days to cover — how many days of trading volume needed to close all short positions.",
        interpretation=">5 days = significant short interest | Can indicate bearish sentiment or squeeze risk",
    ),
    "short_percent_float": MetricDefinition(
        formula="Short % Float = Shares Sold Short / Float",
        description="Percentage of tradeable shares currently sold short.",
        interpretation=">10% is elevated | >20% is very high — potential squeeze candidate",
    ),
    "institutional_pct": MetricDefinition(
        formula="Institutional % = Shares Held by Institutions / Shares Outstanding",
        description="Percentage of shares held by institutional investors (mutual funds, pensions, etc.).",
        interpretation="High % = institutional endorsement | Very high % may limit liquidity",
    ),
    "insider_pct": MetricDefinition(
        formula="Insider % = Shares Held by Insiders / Shares Outstanding",
        description="Percentage of shares held by company insiders (executives, directors).",
        interpretation="Some insider ownership is good (aligned incentives) | >30% may limit governance",
    ),
}


def get_definition(category: str, metric: str) -> MetricDefinition | None:
    """Get the definition for a specific metric.

    Args:
        category: One of 'beneish', 'altman', 'saas', 'profitability', 'leverage',
                  'cash_flow', 'growth', 'valuation', 'shareholder', 'sentiment'
        metric: The metric key (e.g., 'dsri', 'roe', 'pe_trailing')

    Returns:
        MetricDefinition if found, None otherwise
    """
    definitions = {
        "beneish": BENEISH_DEFINITIONS,
        "altman": ALTMAN_DEFINITIONS,
        "saas": SAAS_DEFINITIONS,
        "profitability": PROFITABILITY_DEFINITIONS,
        "leverage": LEVERAGE_DEFINITIONS,
        "cash_flow": CASH_FLOW_DEFINITIONS,
        "growth": GROWTH_DEFINITIONS,
        "valuation": VALUATION_DEFINITIONS,
        "shareholder": SHAREHOLDER_DEFINITIONS,
        "sentiment": SENTIMENT_DEFINITIONS,
    }

    category_defs = definitions.get(category, {})
    return category_defs.get(metric)
