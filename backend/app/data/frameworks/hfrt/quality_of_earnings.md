# Quality of Earnings Framework

> **Classification:** EARNINGS RELIABILITY AND ACCOUNTING RISK FRAMEWORK
> **Applied To:** Every company undergoing financial due diligence in the HFRT pipeline
> **Version:** 1.0
> **Framework Owner:** @Due_Diligence_Officer

---

## Core Principle

**Reported earnings are an opinion. Cash flow is a fact. The gap between them is where accounting risk lives.**

Quality of earnings analysis is the financial due diligence counterpart to management red flags -- it tests whether the reported numbers can be trusted. High-quality earnings are cash-backed, recurring, and transparent. Low-quality earnings rely on accruals, aggressive recognition, and non-GAAP flattery. The framework exists because valuation models assume earnings are real -- if they're not, every multiple applied to them is wrong.

The uncomfortable truth: the most common source of permanent capital loss is not paying too high a multiple, but paying any multiple on earnings that turn out to be fabricated or unsustainable. A stock at 30x real earnings is expensive. A stock at 10x fake earnings is worthless. This framework forces the analyst to verify that earnings convert to cash, that revenue is genuinely recognized, and that the gap between GAAP and non-GAAP metrics is justified -- not just accepted.

---

## Quality of Earnings Checklist

### Revenue Quality

| Check | Metric | Red Flag Threshold | Current | Flag? |
|-------|--------|-------------------|---------|-------|
| DSO Trend | Days Sales Outstanding | >10% YoY increase | | |
| DSO vs. Revenue | DSO growth vs. Revenue growth | DSO growing faster | | |
| Deferred Revenue | Change in deferred revenue | Declining for subscription businesses | | |
| Revenue Concentration | Top customer % | >20% from single customer | | |
| Revenue Recognition | Policy changes | Recent changes | | |
| Barter/Related Party | % of revenue | Any material amount | | |

### Expense/Cost Quality

| Check | Metric | Red Flag Threshold | Current | Flag? |
|-------|--------|-------------------|---------|-------|
| DIO Trend | Days Inventory Outstanding | >15% YoY increase | | |
| Inventory vs. COGS | Inventory growth vs. COGS growth | Inventory growing faster | | |
| DPO Trend | Days Payable Outstanding | Significant extension | | |
| Capitalization | Capitalized costs / Revenue | Increasing trend | | |
| Depreciation | D&A / Capex | <80% sustained | | |

### Accruals Analysis

| Check | Metric | Red Flag Threshold | Current | Flag? |
|-------|--------|-------------------|---------|-------|
| Accrual Ratio | (NI - CFO) / Avg Assets | >10% | | |
| Accruals Trend | Multi-year trend | Increasing | | |
| Total Accruals | NI - CFO (absolute) | Large positive | | |

### Cash Conversion

| Check | Metric | Red Flag Threshold | Current | Flag? |
|-------|--------|-------------------|---------|-------|
| CFO/NI Ratio | CFO / Net Income | <1.0 sustained | | |
| 3-Year Avg CFO/NI | Average over 3 years | <1.0 | | |
| FCF/NI Ratio | FCF / Net Income | <0.8 sustained | | |
| Cash Conversion Trend | Year-over-year trend | Deteriorating | | |

### Non-GAAP Analysis

| Check | Metric | Red Flag Threshold | Current | Flag? |
|-------|--------|-------------------|---------|-------|
| GAAP vs Non-GAAP Gap | Non-GAAP NI / GAAP NI | >1.5x | | |
| SBC Add-back | Stock comp / Revenue | >15% added back | | |
| Restructuring | Restructuring charges | "Recurring" restructuring | | |
| Acquisition Costs | M&A costs frequency | Frequent/ongoing | | |
| Adjustments Trend | Total adjustments over time | Growing | | |

## Detailed Analysis Components

### 1. Revenue Recognition Deep Dive

**Questions to Answer:**
- When is revenue recognized vs. cash received?
- Are there significant timing differences?
- Has revenue recognition policy changed?
- Is there evidence of channel stuffing?

**Warning Signs:**
- Revenue recognized before delivery
- Bill-and-hold arrangements
- Revenue spikes at quarter-end
- Unusual contractual terms

### 2. Working Capital Analysis

**Formula:** Cash Conversion Cycle = DSO + DIO - DPO

| Metric | Calculation | What It Indicates |
|--------|-------------|-------------------|
| DSO | (AR / Revenue) x 365 | Collection efficiency |
| DIO | (Inventory / COGS) x 365 | Inventory management |
| DPO | (AP / COGS) x 365 | Payment management |
| CCC | DSO + DIO - DPO | Cash efficiency |

**Warning Signs:**
- DSO increasing faster than industry
- DIO building without revenue growth
- DPO extending artificially
- Working capital consuming cash

### 3. Accruals Quality

**Accrual Ratio Calculation:**
```
Accrual Ratio = (Net Income - Cash from Operations) / Average Total Assets
```

**Interpretation:**
| Accrual Ratio | Quality Assessment |
|---------------|-------------------|
| <5% | High quality |
| 5-10% | Moderate quality |
| >10% | Low quality / Investigate |

**Common Accrual Issues:**
- Aggressive revenue recognition
- Delayed expense recognition
- Reserve manipulation
- Unusual non-cash items

### 4. Cash Flow Quality

**Key Ratios:**
| Ratio | Formula | Healthy Range |
|-------|---------|---------------|
| Cash Quality | CFO / Net Income | >1.0 |
| FCF Yield | FCF / Market Cap | >5% |
| FCF Conversion | FCF / EBITDA | >50% |
| Capex Quality | Maintenance Capex / D&A | ~100% |

**Warning Signs:**
- CFO consistently below Net Income
- Large gap between EBITDA and CFO
- Capex significantly exceeds D&A
- Negative FCF despite positive earnings

### 5. Non-GAAP Adjustments Assessment

**Legitimate Adjustments:**
- One-time restructuring (truly one-time)
- Acquisition-related amortization
- Litigation settlements
- Asset impairments (non-recurring)

**Questionable Adjustments:**
- Stock-based compensation (ongoing)
- "Recurring" restructuring
- Integration costs (for serial acquirers)
- Vague "other" adjustments

### 6. Auditor Assessment

| Factor | Green | Yellow | Red |
|--------|-------|--------|-----|
| Auditor | Big 4 | Non-Big 4 for large cap | Recent change |
| Opinion | Clean | Emphasis of matter | Qualified |
| KAMs | Routine | Unusual areas | Revenue recognition |
| Controls | No issues | Significant deficiency | Material weakness |
| Tenure | Stable | Recent change | Multiple changes |

## Quality of Earnings Score

### Scoring Rubric

| Category | Weight | Score (1-5) | Weighted |
|----------|--------|-------------|----------|
| Revenue Quality | 25% | | |
| Expense Quality | 15% | | |
| Accruals | 20% | | |
| Cash Conversion | 25% | | |
| Non-GAAP Integrity | 10% | | |
| Auditor/Controls | 5% | | |
| **Total** | 100% | | |

### Score Interpretation

| Score Range | Quality Rating | Implication |
|-------------|---------------|-------------|
| 4.0-5.0 | High | Earnings are reliable |
| 3.0-3.9 | Adequate | Some concerns, monitor |
| 2.0-2.9 | Concerning | Significant quality issues |
| 1.0-1.9 | Poor | Earnings not reliable |

## Impact on Thesis
- Low earnings quality = discount to valuation
- Deteriorating quality = potential catalyst risk
- High quality = supports premium multiple

## Red Flags Summary

**Critical (investigate immediately):**
- [ ] Material weakness in internal controls
- [ ] Auditor change with disagreement
- [ ] CFO < 50% of Net Income for 2+ years
- [ ] Accrual ratio > 15%

**High (significant concern):**
- [ ] DSO increasing >10% YoY
- [ ] Non-GAAP >> GAAP consistently
- [ ] "Recurring" restructuring charges
- [ ] Revenue recognition policy changes

**Medium (monitor closely):**
- [ ] DIO increasing without volume growth
- [ ] Cash conversion cycle extending
- [ ] SBC > 10% of revenue
- [ ] Aggressive capitalization

## Integration

- **Primary Application:** `09_QUALITY_OF_EARNINGS.md` (primary earnings quality analysis)
- **Feeds Into:** `05_FINANCIAL_ANALYSIS.md` (earnings quality summary), `08_RISK_ANALYSIS.md` (accounting risk factors)
- **Cross-Reference:** `management_red_flags.md` (management controls earnings quality), `dupont_analysis.md` (DuPont components must reconcile with cash flows), `conviction_scoring.md` (data quality factor)
- **Authority:** @Due_Diligence_Officer has sole authority for quality of earnings assessment

---

*Never trust earnings that can't be reconciled to cash. Accruals are promises; cash is proof.*
