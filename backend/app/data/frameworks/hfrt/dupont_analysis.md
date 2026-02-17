# DuPont Analysis Framework

> **Classification:** PROFITABILITY DECOMPOSITION FRAMEWORK
> **Applied To:** Every company undergoing financial analysis in the HFRT pipeline
> **Version:** 1.0
> **Framework Owner:** @Quantitative_Analyst

---

## Core Principle

**ROE is a composite number that hides more than it reveals. Decompose it or be deceived by it.**

A 15% ROE can come from excellent operations (high margins, efficient asset utilization) or from dangerous leverage. Without decomposition, these two companies look identical on a quantitative screen. DuPont analysis is the only way to distinguish quality ROE from leveraged ROE, and the framework is applied to every company in the HFRT pipeline to identify the *source* of returns, not just the level.

The uncomfortable truth: many "high-quality" companies that pass quantitative screens are actually leveraging their way to attractive ROE numbers. A company with 8% margins, mediocre asset turnover, and 4x leverage can post the same ROE as a company with 20% margins and no debt. Without decomposition, this is invisible -- and the leveraged company carries far more risk in a downturn. The framework forces the question: "Where does this ROE come from, and would it survive a stress scenario?"

---

## 3-Factor DuPont Model

### Formula
```
ROE = Net Profit Margin x Asset Turnover x Financial Leverage

ROE = (Net Income / Revenue) x (Revenue / Total Assets) x (Total Assets / Shareholders' Equity)
```

### Component Definitions

| Component | Formula | What It Measures |
|-----------|---------|------------------|
| **Net Profit Margin** | Net Income / Revenue | Operating efficiency and pricing power |
| **Asset Turnover** | Revenue / Total Assets | Asset utilization efficiency |
| **Financial Leverage** | Total Assets / Equity | Use of debt financing |

### Interpretation

**High ROE can come from:**
1. High margins (pricing power, cost control)
2. High asset turnover (efficient use of assets)
3. High leverage (debt financing)

**Quality Assessment:**
- ROE from margins/turnover = High quality
- ROE from leverage = Lower quality, higher risk

## 5-Factor Extended DuPont Model

### Formula
```
ROE = Tax Burden x Interest Burden x EBIT Margin x Asset Turnover x Leverage

ROE = (NI/EBT) x (EBT/EBIT) x (EBIT/Revenue) x (Revenue/Assets) x (Assets/Equity)
```

### Component Definitions

| Component | Formula | What It Measures |
|-----------|---------|------------------|
| **Tax Burden** | Net Income / EBT | Tax efficiency (1 - effective tax rate) |
| **Interest Burden** | EBT / EBIT | Impact of debt servicing |
| **EBIT Margin** | EBIT / Revenue | Operating profitability |
| **Asset Turnover** | Revenue / Total Assets | Asset efficiency |
| **Financial Leverage** | Total Assets / Equity | Capital structure |

### When to Use 5-Factor
- Comparing companies with different tax rates
- Analyzing impact of debt on profitability
- Understanding operational vs. financial drivers

## Analysis Template

### 3-Factor DuPont Analysis

| Component | FY-4 | FY-3 | FY-2 | FY-1 | LTM | Trend |
|-----------|------|------|------|------|-----|-------|
| Net Profit Margin | | | | | | |
| Asset Turnover | | | | | | |
| Financial Leverage | | | | | | |
| **ROE** | | | | | | |

### 5-Factor DuPont Analysis

| Component | FY-4 | FY-3 | FY-2 | FY-1 | LTM | Trend |
|-----------|------|------|------|------|-----|-------|
| Tax Burden | | | | | | |
| Interest Burden | | | | | | |
| EBIT Margin | | | | | | |
| Asset Turnover | | | | | | |
| Financial Leverage | | | | | | |
| **ROE** | | | | | | |

### Peer Comparison

| Metric | Company | Peer 1 | Peer 2 | Peer 3 | Industry Avg |
|--------|---------|--------|--------|--------|--------------|
| Net Profit Margin | | | | | |
| Asset Turnover | | | | | |
| Financial Leverage | | | | | |
| **ROE** | | | | | |

## Interpretation Guidelines

### Margin Analysis
| Margin Level | Assessment | Typical Causes |
|--------------|------------|----------------|
| > Industry avg | Positive | Pricing power, cost efficiency, product mix |
| = Industry avg | Neutral | Competitive market |
| < Industry avg | Investigate | Cost issues, pricing pressure, mix |

### Asset Turnover Analysis
| Turnover Level | Assessment | Typical Causes |
|----------------|------------|----------------|
| > Industry avg | Positive | Efficient operations, low capital intensity |
| = Industry avg | Neutral | Industry standard |
| < Industry avg | Investigate | Overcapacity, inefficiency, different business model |

### Leverage Analysis
| Leverage Level | Assessment | Considerations |
|----------------|------------|----------------|
| < 2.0x | Conservative | Lower risk, may be under-optimized |
| 2.0-3.0x | Moderate | Typical range for many industries |
| > 3.0x | Aggressive | Higher risk, magnifies returns and losses |

## ROE Quality Assessment

### High-Quality ROE Characteristics
- Driven primarily by margins or asset turnover
- Consistent or improving over time
- Above cost of equity
- Sustainable (not from one-time items)

### Low-Quality ROE Characteristics
- Driven primarily by leverage
- Volatile year-over-year
- Declining trend
- Inflated by accounting choices

### ROE Quality Score

| Factor | Score (1-5) | Weight | Weighted |
|--------|-------------|--------|----------|
| Margin contribution | | 30% | |
| Turnover contribution | | 30% | |
| Leverage reasonableness | | 20% | |
| Trend stability | | 20% | |
| **Total Quality Score** | | 100% | |

## Connection to Valuation
- High-quality ROE justifies higher P/B multiples
- Sustainable ROE drives residual income models
- ROE vs. cost of equity determines value creation

## Red Flags

- ROE primarily from leverage (>50% contribution)
- Declining margin trend
- Asset turnover declining without margin offset
- Leverage increasing to maintain ROE
- ROE < Cost of Equity over multiple years

## Industry Considerations

### Capital-Light Businesses (Tech, Services)
- Expect high margins, high turnover
- Low leverage typical
- Focus on margin analysis

### Capital-Intensive Businesses (Manufacturing, Utilities)
- Lower margins, lower turnover typical
- Higher leverage common
- Focus on ROIC alongside ROE

### Financial Services
- Traditional DuPont less meaningful
- Use industry-specific metrics (NIM, efficiency ratio)
- Leverage is core to business model

## Integration

- **Primary Application:** `05_FINANCIAL_ANALYSIS.md` (primary profitability analysis)
- **Feeds Into:** `02_BUSINESS_MODEL.md` (margin driver analysis), `06_VALUATION.md` (quality-adjusted multiples)
- **Cross-Reference:** `quality_of_earnings.md` (earnings quality validates DuPont components), `conviction_scoring.md` (data quality factor)
- **Authority:** @Quantitative_Analyst has primary authority for DuPont analysis

---

*A high ROE is not a compliment until you know where it comes from.*
