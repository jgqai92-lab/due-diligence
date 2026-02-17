# Financials Sector Metrics Framework

> **Classification:** FINANCIALS SECTOR KPI FRAMEWORK
> **Applied To:** All financial companies (banks, insurance, asset management, capital markets, REITs, specialty finance) entering the HFRT pipeline
> **Version:** 1.0
> **Framework Owner:** @Sector_Financials

---

## Core Principle

**Financial companies are opaque by nature. The balance sheet IS the business model, and the metrics that matter are entirely different from every other sector.**

Financials require a completely different analytical toolkit. Revenue, EBITDA, and P/E -- the standard metrics for other sectors -- are misleading or meaningless for banks, insurers, and REITs. A bank's NIM, a P&C insurer's combined ratio, and a REIT's FFO each require specialized knowledge to interpret. Applying industrial-sector metrics to financials is a common and expensive mistake.

The uncomfortable truth: credit quality is a lagging indicator -- by the time NPLs rise, the damage is already done. The framework emphasizes leading indicators (criticized assets, vintage analysis, reserve adequacy) over the lagging metrics that most screens use. A bank reporting pristine credit quality today may be sitting on a CRE concentration that destroys 3 years of earnings next year. Similarly, an insurer with a 95% combined ratio looks great until you discover the prior year reserve releases that are flattering current results. This framework forces the analyst to look where the bodies are buried, not where the press release points.

---

## Banks (Commercial, Regional, Investment)

### Key Metrics

| Metric | Definition | Best-in-Class | Good | Concerning |
|--------|------------|---------------|------|------------|
| **NIM** | Net Interest Margin | >3.5% | 2.5-3.5% | <2.5% |
| **NII Growth** | Net Interest Income growth | >10% | 5-10% | <5% or negative |
| **Fee Income %** | Non-interest income / Revenue | >40% | 25-40% | <25% |
| **Efficiency Ratio** | Non-interest expense / Revenue | <55% | 55-65% | >65% |
| **ROTCE** | Return on Tangible Common Equity | >15% | 10-15% | <10% |
| **ROA** | Return on Assets | >1.2% | 0.8-1.2% | <0.8% |
| **CET1 Ratio** | Common Equity Tier 1 / RWA | >12% | 10-12% | <10% |
| **NPL Ratio** | Non-Performing Loans / Total Loans | <1% | 1-2% | >2% |
| **NCO Ratio** | Net Charge-Offs / Avg Loans | <0.5% | 0.5-1% | >1% |
| **Reserve Coverage** | Allowance / NPLs | >150% | 100-150% | <100% |
| **LDR** | Loan-to-Deposit Ratio | 80-90% | 70-100% | <70% or >100% |

### NIM Decomposition
```
NIM = (Interest Income - Interest Expense) / Average Earning Assets

Drivers:
- Asset yields (loan pricing, securities mix)
- Funding costs (deposit beta, wholesale funding)
- Asset mix (loans vs. securities)
- Rate environment sensitivity
```

### Credit Quality Waterfall
```
Criticized Assets -> NPLs -> NCOs
      |               |        |
   Watch List    Workout    Loss

Reserve Build = Provision - NCOs
```

### Red Flags
- Rising criticized/classified loans
- NIM compression without volume offset
- Deposit outflows requiring wholesale funding
- CRE concentration (>300% of capital)
- Insider loan issues
- BSA/AML compliance problems
- Rapid loan growth (>15% without explanation)

---

## Insurance (P&C, Life, Specialty)

### P&C Insurance Metrics

| Metric | Definition | Best-in-Class | Good | Concerning |
|--------|------------|---------------|------|------------|
| **Combined Ratio** | (Loss + Expense) / Earned Premium | <95% | 95-100% | >100% |
| **Loss Ratio** | Incurred Losses / Earned Premium | <60% | 60-70% | >70% |
| **Expense Ratio** | Underwriting Expense / Written Premium | <30% | 30-35% | >35% |
| **Accident Year Loss Ratio** | Current year losses only | Track trend | | Deteriorating |
| **Prior Year Development** | Reserve releases/strengthening | Favorable | Neutral | Adverse |
| **Retention Rate** | Renewed premium / Expiring premium | >85% | 75-85% | <75% |
| **Investment Yield** | Investment income / Avg invested assets | >3% | 2-3% | <2% |
| **ROE** | Net Income / Avg Equity | >12% | 8-12% | <8% |

### Combined Ratio Decomposition
```
Combined Ratio = Loss Ratio + Expense Ratio
              = (Current AY Loss Ratio + Prior Year Development) + Expense Ratio

Underwriting Profit = Premium - (Losses + Expenses)
If CR < 100%: Underwriting profit
If CR > 100%: Underwriting loss (must be offset by investment income)
```

### Life Insurance Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Statutory Capital** | Risk-based capital ratio | >350% |
| **Spread Income** | Investment yield - Credited rate | Positive, stable |
| **Persistency** | Policies in force retention | >90% |
| **Mortality/Morbidity** | Actual vs. expected claims | At or below expected |
| **DAC Amortization** | Deferred acquisition cost ratio | Stable |

### Red Flags
- Reserve deficiency (adverse prior year development)
- Cat exposure concentration
- Reinsurance credit risk
- Investment portfolio quality deterioration
- Rapid premium growth without rate adequacy
- Persistency decline (life)
- Spread compression (life)

---

## Asset Management

### Key Metrics

| Metric | Definition | Best-in-Class | Good | Concerning |
|--------|------------|---------------|------|------------|
| **AUM Growth** | Assets Under Management change | >10% | 0-10% | Negative |
| **Organic Growth** | Net flows / Beginning AUM | >5% | 0-5% | Negative |
| **Net Flows** | Inflows - Outflows | Positive | Neutral | Negative |
| **Revenue Yield** | Revenue / Avg AUM (bps) | Stable/Up | Slight decline | Sharp decline |
| **Operating Margin** | Operating Income / Revenue | >35% | 25-35% | <25% |
| **Performance Fees %** | Performance fees / Revenue | 10-30% | 5-30% | Over-reliance (>50%) |
| **Investment Performance** | % AUM beating benchmark | >60% | 50-60% | <50% |

### AUM Bridge
```
Ending AUM = Beginning AUM + Net Flows + Market Appreciation + FX Impact

Net Flows = Gross Sales - Redemptions

Organic Growth Rate = Net Flows / Beginning AUM
```

### Fee Rate Analysis

| Product Type | Typical Fee (bps) | Trend |
|--------------|------------------|-------|
| Active Equity | 50-100 | Declining |
| Active Fixed Income | 25-50 | Declining |
| Passive/ETF | 3-20 | Declining |
| Alternatives | 100-200+ | Stable |
| Solutions/Multi-Asset | 30-60 | Stable |

### Red Flags
- Persistent negative flows
- Fee compression without cost offset
- Investment underperformance (>3 years)
- Key personnel departures
- Product concentration risk
- Institutional mandate losses
- Seed/co-investment losses

---

## Capital Markets / Investment Banking

### Key Metrics

| Metric | Definition | Assessment |
|--------|------------|------------|
| **Wallet Share** | Firm share of industry fee pool | vs. peers |
| **League Table Rank** | Position in deal rankings | Improving/declining |
| **Compensation Ratio** | Comp / Net Revenue | <50% preferred |
| **ROE** | Return on allocated equity | >15% |
| **VaR** | Value at Risk | Trend and utilization |
| **Trading Revenue Volatility** | Std dev of trading revenue | Lower preferred |

### Revenue Mix Analysis

| Business | Cyclicality | Margin Profile |
|----------|-------------|----------------|
| M&A Advisory | High | Highest |
| ECM | Very High | High |
| DCM | Moderate | Medium |
| Trading (FICC) | High | Variable |
| Trading (Equities) | High | Variable |
| Prime Services | Lower | Stable |

### Red Flags
- Market share losses
- Key banker departures
- Prop trading losses
- Risk limit breaches
- Regulatory issues
- Counterparty concentration

---

## REITs (Real Estate Investment Trusts)

### Key Metrics

| Metric | Definition | Best-in-Class | Good | Concerning |
|--------|------------|---------------|------|------------|
| **FFO/Share Growth** | Funds From Operations growth | >5% | 0-5% | Negative |
| **AFFO/Share** | Adjusted FFO (maintenance capex) | Growing | Stable | Declining |
| **Occupancy** | Leased space / Total space | >95% | 90-95% | <90% |
| **Same-Store NOI Growth** | Existing property income growth | >3% | 0-3% | Negative |
| **Rent Spread** | New lease vs. expiring lease | Positive | Flat | Negative |
| **Debt/EBITDA** | Leverage ratio | <6x | 6-8x | >8x |
| **Interest Coverage** | EBITDA / Interest expense | >4x | 3-4x | <3x |
| **Payout Ratio** | Dividend / AFFO | <80% | 80-90% | >90% |
| **NAV Premium/Discount** | Price vs. Net Asset Value | Premium | At NAV | Discount |

### FFO Reconciliation
```
Net Income
+ Depreciation (real estate)
+ Amortization (real estate)
- Gains on property sales
+ Losses on property sales
= FFO

FFO
- Recurring capex (maintenance)
- Straight-line rent adjustment
- Stock compensation
= AFFO
```

### Property Type Benchmarks

| Property Type | Typical Cap Rate | Key Drivers |
|---------------|-----------------|-------------|
| Industrial | 4-6% | E-commerce, supply chain |
| Multifamily | 4-6% | Demographics, supply |
| Office | 6-8% | WFH trends, employment |
| Retail | 6-9% | E-commerce impact, traffic |
| Healthcare | 5-7% | Demographics, reimbursement |
| Data Centers | 4-6% | Cloud, AI demand |
| Self-Storage | 5-7% | Population, housing |

### Red Flags
- Occupancy decline
- Negative rent spreads
- Rising tenant defaults
- Development pipeline risk
- Floating rate debt exposure
- Near-term lease expirations concentrated
- Geographic/tenant concentration

---

## Specialty Finance / Consumer Finance

### Key Metrics

| Metric | Definition | Best-in-Class | Good | Concerning |
|--------|------------|---------------|------|------------|
| **Yield** | Interest income / Avg receivables | Stable/Up | | Declining |
| **Net Interest Margin** | NIM on receivables | Stable/Up | | Compression |
| **Credit Losses** | NCOs / Avg receivables | Below guidance | At guidance | Above guidance |
| **Delinquency Rate** | 30+ DPD / Total receivables | Stable/declining | | Rising |
| **Provision Rate** | Provision / Avg receivables | Stable | | Rising |
| **Operating Efficiency** | OpEx / Avg receivables | Declining | Stable | Rising |
| **ROA** | Net Income / Avg Assets | >2% | 1-2% | <1% |
| **Tangible Leverage** | Assets / Tangible equity | <10x | 10-12x | >12x |

### Vintage Analysis Framework
```
Vintage = Loans originated in a given period

Track each vintage's:
- Loss curve (cumulative losses over time)
- Delinquency progression
- Recovery rates

Compare vintages to assess:
- Underwriting changes
- Economic cycle impact
- Model accuracy
```

### Red Flags
- Delinquency uptick (leading indicator)
- Vintage deterioration
- Loosening underwriting standards
- Funding cost pressure
- Regulatory scrutiny (rates, practices)
- Concentration in stressed demographics

---

## Financials Valuation Context

### Typical Multiples

| Sub-Sector | P/E | P/TBV | P/B | Key Driver |
|------------|-----|-------|-----|------------|
| Large Banks | 10-14x | 1.5-2.5x | 1.0-1.5x | ROTCE, credit |
| Regional Banks | 10-14x | 1.2-2.0x | 1.0-1.5x | NIM, credit |
| P&C Insurance | 10-14x | 1.5-2.5x | 1.2-1.8x | Combined ratio |
| Life Insurance | 8-12x | 0.8-1.5x | 0.8-1.2x | Spread, capital |
| Asset Management | 12-18x | N/A | 2-5x | Flows, AUM |
| REITs | 15-25x FFO | N/A | 0.8-1.2x NAV | FFO growth, property type |
| Specialty Finance | 8-12x | 1.0-2.0x | 0.8-1.5x | Credit, ROA |

### Bank Valuation Framework
```
P/TBV = (ROE - g) / (COE - g)

Where:
- ROE = Sustainable return on equity
- g = Growth rate
- COE = Cost of equity

Higher ROE -> Higher P/TBV multiple deserved
```

### Premium Factors
- Consistent credit outperformance
- Sustainable ROE above cost of equity
- Fee income diversification
- Strong deposit franchise
- Clean regulatory record

## Integration

- **Primary Application:** `04_INDUSTRY_ANALYSIS.md` (sector-specific KPI analysis for financial companies)
- **Feeds Into:** `02_BUSINESS_MODEL.md` (financial business model specifics), `05_FINANCIAL_ANALYSIS.md` (sector-appropriate metrics), `06_VALUATION.md` (P/TBV framework, FFO multiples for REITs)
- **Cross-Reference:** `dupont_analysis.md` (leverage is core to financial business models -- interpret differently), `management_red_flags.md` (governance especially critical for opaque businesses)
- **Authority:** @Sector_Financials has sole authority for financial sector metric selection and benchmarking

---

*Financials are balance sheet businesses. If you're using revenue multiples, you've already gone wrong.*
