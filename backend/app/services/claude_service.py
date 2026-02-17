"""Claude API integration for comprehensive due-diligence report generation."""

import json
import logging
from datetime import datetime

from anthropic import Anthropic

from app.config import settings
from app.schemas.analysis import ComprehensiveAnalysis, ForensicMetrics, ForensicReport

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are The Skeptical Analyst — an institutional-grade hedge fund analyst who delivers comprehensive due diligence briefs to portfolio managers. Your role:

1. NEVER fabricate numbers. Only cite figures from the provided pre-calculated data.
2. Every claim must reference specific metrics from the data provided.
3. You MUST include a Bear Case section — no exceptions. Even for the strongest companies, identify material risks.
4. Adopt a skeptical stance: question consensus, look for what could go wrong, and highlight what the market may be mispricing.

Structure your report with these EXACT sections in this order:

## Executive Summary
2-3 sentences: investment thesis, key risk, and recommendation (INVEST / MONITOR / AVOID).

## Macro Context
- Sector/industry positioning and macro trends
- Cyclical vs secular assessment
- Regulatory or geopolitical considerations
- Risks of hype or overconcentration

## Fundamental Analysis
### Financial Health
- Profitability analysis (margins, ROE, ROA, ROIC)
- Leverage & solvency assessment (D/E, interest coverage, current/quick ratio, net debt/EBITDA)
- Cash flow quality (FCF yield, OCF/NI ratio, FCF margin, capex intensity)

### Forensic Red Flags
- Beneish M-Score interpretation (manipulation likelihood)
- Altman Z-Score interpretation (bankruptcy risk)
- Any accounting irregularities inferred from the data

### Growth & Valuation
- Growth trajectory and sustainability (revenue, earnings, FCF growth)
- Valuation relative to growth (PEG, EV/EBITDA, P/E context)
- Contrarian insights — what the market may be mispricing

## Management & Sentiment Assessment
- Capital allocation assessment (inferred from dividends, payout ratio, debt management)
- Analyst consensus and potential herding risks
- Short interest signals (days to cover, % of float)
- Institutional vs insider ownership dynamics

## Scenario Planning
- **Bull Case:** What the numbers support — be specific with metrics
- **Base Case:** Most likely path forward
- **Bear Case (MANDATORY):** What could go wrong — this section must be substantive

## Recommendation
- Clear verdict: INVEST / MONITOR / AVOID
- Position sizing considerations (conviction level)
- Key watchpoints for next quarter

Format in markdown. Be direct, data-driven, and skeptical. Use the pre-calculated metrics provided — do not recalculate or fabricate any figures."""


def _format_metric(value, label: str = "") -> str:
    """Format a metric value for display in the prompt."""
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _build_comprehensive_user_prompt(
    ticker: str,
    company_name: str,
    comprehensive: ComprehensiveAnalysis,
    raw_data_summary: dict,
) -> str:
    """Build the user prompt containing all pre-calculated metrics for Claude."""
    p = comprehensive.profitability
    l = comprehensive.leverage
    cf = comprehensive.cash_flow
    g = comprehensive.growth
    v = comprehensive.valuation
    sh = comprehensive.shareholder_returns
    s = comprehensive.sentiment

    sector_section = ""
    if comprehensive.sector_specific:
        ss = comprehensive.sector_specific
        metrics_str = ", ".join(
            f"{k}={_format_metric(mc.value)}" for k, mc in ss.metrics.items()
        )
        interp_str = ", ".join(
            f"{k}={v}" for k, v in ss.interpretations.items() if v
        )
        sector_section = f"""
## Sector-Specific Metrics ({ss.label})
{metrics_str}
Interpretations: {interp_str}
"""

    return f"""Analyze {ticker} ({company_name}) using these pre-calculated metrics:

## Company Context
Sector Category: {comprehensive.sector_category}

## Forensic Scores

### Beneish M-Score
Composite: {_format_metric(comprehensive.beneish_m_score.composite)}
Interpretation: {comprehensive.beneish_m_score.interpretation or "N/A"}
Components: DSRI={_format_metric(comprehensive.beneish_m_score.components.dsri.value)}, GMI={_format_metric(comprehensive.beneish_m_score.components.gmi.value)}, AQI={_format_metric(comprehensive.beneish_m_score.components.aqi.value)}, SGI={_format_metric(comprehensive.beneish_m_score.components.sgi.value)}, DEPI={_format_metric(comprehensive.beneish_m_score.components.depi.value)}, SGAI={_format_metric(comprehensive.beneish_m_score.components.sgai.value)}, LVGI={_format_metric(comprehensive.beneish_m_score.components.lvgi.value)}, TATA={_format_metric(comprehensive.beneish_m_score.components.tata.value)}

### Altman Z-Score
Standard: {_format_metric(comprehensive.altman_z_score.standard.score)} ({comprehensive.altman_z_score.standard.zone or "N/A"})
SaaS-Modified: {_format_metric(comprehensive.altman_z_score.saas_modified.score)} ({comprehensive.altman_z_score.saas_modified.zone or "N/A"})

## Profitability
Gross Margin: {_format_metric(p.gross_margin.value)}
Operating Margin: {_format_metric(p.operating_margin.value)}
Net Margin: {_format_metric(p.net_margin.value)}
ROE: {_format_metric(p.roe.value)}
ROA: {_format_metric(p.roa.value)}
ROIC: {_format_metric(p.roic.value)}

## Leverage & Solvency
Debt-to-Equity: {_format_metric(l.debt_to_equity.value)}
Interest Coverage: {_format_metric(l.interest_coverage.value)}
Current Ratio: {_format_metric(l.current_ratio.value)}
Quick Ratio: {_format_metric(l.quick_ratio.value)}
Net Debt/EBITDA: {_format_metric(l.net_debt_to_ebitda.value)}

## Cash Flow Quality
FCF Yield: {_format_metric(cf.fcf_yield.value)}
OCF/Net Income: {_format_metric(cf.ocf_to_net_income.value)}
FCF Margin: {_format_metric(cf.fcf_margin.value)}
CapEx/Revenue: {_format_metric(cf.capex_to_revenue.value)}

## Growth
Revenue Growth YoY: {_format_metric(g.revenue_growth_yoy.value)}
Earnings Growth YoY: {_format_metric(g.earnings_growth_yoy.value)}
FCF Growth YoY: {_format_metric(g.fcf_growth_yoy.value)}
Revenue CAGR 3Y: {_format_metric(g.revenue_cagr_3y.value)}

## Valuation
P/E Trailing: {_format_metric(v.pe_trailing.value)}
P/E Forward: {_format_metric(v.pe_forward.value)}
EV/EBITDA: {_format_metric(v.ev_to_ebitda.value)}
Price/FCF: {_format_metric(v.price_to_fcf.value)}
Price/Sales: {_format_metric(v.price_to_sales.value)}
PEG Ratio: {_format_metric(v.peg_ratio.value)}

## Shareholder Returns
Dividend Yield: {_format_metric(sh.dividend_yield.value)}
Payout Ratio: {_format_metric(sh.payout_ratio.value)}

## Sentiment & Positioning
Analyst Rating (1=Strong Buy, 5=Sell): {_format_metric(s.analyst_rating.value)}
Analyst Count: {s.analyst_count or "N/A"}
Analyst Recommendation: {s.analyst_recommendation or "N/A"}
Short Ratio (days to cover): {_format_metric(s.short_ratio.value)}
Short % of Float: {_format_metric(s.short_percent_float.value)}
Institutional Ownership: {_format_metric(s.institutional_pct.value)}
Insider Ownership: {_format_metric(s.insider_pct.value)}
{sector_section}
## Key Financial Data (raw)
{json.dumps(raw_data_summary, indent=2, default=str)[:4000]}

IMPORTANT: Only reference numbers from the data above. Do NOT fabricate any figures."""


def generate_report(
    ticker: str,
    company_name: str,
    metrics: ForensicMetrics | ComprehensiveAnalysis,
    raw_data_summary: dict,
) -> ForensicReport:
    """Generate a Claude-authored due-diligence narrative report.

    Accepts either ForensicMetrics (legacy) or ComprehensiveAnalysis (new).
    When ComprehensiveAnalysis is provided, uses the full due-diligence prompt.
    """
    if not settings.anthropic_api_key:
        return ForensicReport(
            markdown="*Report generation requires an Anthropic API key. Set ANTHROPIC_API_KEY in .env.*",
            generated_at=datetime.utcnow().isoformat() + "Z",
            model="none",
        )

    client = Anthropic(api_key=settings.anthropic_api_key)

    # Build prompt based on metrics type
    if isinstance(metrics, ComprehensiveAnalysis):
        user_prompt = _build_comprehensive_user_prompt(
            ticker, company_name, metrics, raw_data_summary
        )
    else:
        # Legacy path for ForensicMetrics
        user_prompt = f"""Analyze {ticker} ({company_name}) using these pre-calculated forensic metrics:

## Beneish M-Score
Composite: {metrics.beneish_m_score.composite}
Interpretation: {metrics.beneish_m_score.interpretation}
Components: DSRI={metrics.beneish_m_score.components.dsri.value}, GMI={metrics.beneish_m_score.components.gmi.value}, AQI={metrics.beneish_m_score.components.aqi.value}, SGI={metrics.beneish_m_score.components.sgi.value}, DEPI={metrics.beneish_m_score.components.depi.value}, SGAI={metrics.beneish_m_score.components.sgai.value}, LVGI={metrics.beneish_m_score.components.lvgi.value}, TATA={metrics.beneish_m_score.components.tata.value}

## Altman Z-Score
Standard: {metrics.altman_z_score.standard.score} ({metrics.altman_z_score.standard.zone})
SaaS-Modified: {metrics.altman_z_score.saas_modified.score} ({metrics.altman_z_score.saas_modified.zone})

## SaaS Metrics
Rule of 40: {metrics.rule_of_40.score} (Revenue Growth: {metrics.rule_of_40.revenue_growth_percent}%, FCF Margin: {metrics.rule_of_40.fcf_margin_percent}%) -- {metrics.rule_of_40.interpretation}
Magic Number: {metrics.magic_number.score} -- {metrics.magic_number.interpretation}

## Key Financial Data
{json.dumps(raw_data_summary, indent=2, default=str)[:3000]}

IMPORTANT: Only reference numbers from the data above. Do NOT fabricate any figures."""

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=6000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            timeout=settings.claude_timeout,
        )
        markdown = response.content[0].text
    except Exception as e:
        logger.error("Claude API error for %s: %s", ticker, e)
        markdown = f"*Report generation failed: {e}*"

    return ForensicReport(
        markdown=markdown,
        generated_at=datetime.utcnow().isoformat() + "Z",
        model=settings.claude_model,
    )
