# Technology Sector Metrics Framework

> **Classification:** TECHNOLOGY SECTOR KPI FRAMEWORK
> **Applied To:** All technology companies (software/SaaS, semiconductors, hardware, internet/platforms) entering the HFRT pipeline
> **Version:** 1.0
> **Framework Owner:** @Sector_Technology

---

## Core Principle

**Technology sector analysis bifurcates into two fundamentally different exercises: recurring revenue businesses (software) where retention metrics are destiny, and cyclical hardware businesses (semis) where the demand cycle determines everything.**

"Technology" is a misleadingly broad category. A SaaS company with 120% NRR and a semiconductor company with 70% capacity utilization require completely different analytical frameworks despite both being "tech." The framework provides sub-sector-specific KPIs because applying SaaS metrics to semis (or vice versa) produces meaningless analysis. For software, the Rule of 40 and NRR are the north star metrics. For semiconductors, the book-to-bill ratio and inventory days tell you where you are in the cycle. For platforms, DAU/MAU engagement and ARPU trends reveal whether the network effect is strengthening or decaying.

The uncomfortable truth: most technology stock pitches conflate TAM expansion with investability. A company addressing a $100B TAM with 5% gross margins is not an opportunity -- it's a commodity business with a technology wrapper. The framework forces the analyst to evaluate each sub-sector on its own terms: SaaS on unit economics and retention, semis on cycle position and cost structure, platforms on engagement and monetization efficiency. TAM slides are not analysis.

---

## Software (SaaS / Enterprise / Consumer)

### Key Metrics

| Metric | Definition | Best-in-Class | Good | Concerning |
|--------|------------|---------------|------|------------|
| **ARR** | Annual Recurring Revenue | N/A (scale) | Growing >25% | <15% growth |
| **NRR** | Net Revenue Retention | >120% | 110-120% | <100% |
| **Gross Retention** | Retention excluding expansion | >95% | 90-95% | <90% |
| **Rule of 40** | Revenue Growth % + FCF Margin % | >40% | 25-40% | <25% |
| **Magic Number** | Net New ARR / Prior Period S&M | >1.0 | 0.5-1.0 | <0.5 |
| **CAC Payback** | Months to recover acquisition cost | <12 months | 12-24 months | >24 months |
| **LTV/CAC** | Lifetime Value / Customer Acquisition Cost | >3.0x | 2.0-3.0x | <2.0x |
| **Gross Margin** | Gross Profit / Revenue | >75% | 65-75% | <65% |
| **S&M %** | Sales & Marketing / Revenue | <40% at scale | 40-60% | >60% at scale |
| **R&D %** | R&D / Revenue | 15-25% | 10-30% | Extremes |

### Calculations

```
NRR = (Starting ARR + Expansion - Contraction - Churn) / Starting ARR

Magic Number = (QoQ ARR change x 4) / Prior Quarter S&M

Rule of 40 = Revenue Growth Rate + FCF Margin

LTV = (ARPU x Gross Margin) / Churn Rate
CAC = Total S&M Spend / New Customers Acquired
```

### Red Flags
- NRR declining quarter-over-quarter
- Billings growth diverging from revenue growth
- Increasing CAC payback periods
- Heavy reliance on professional services revenue
- RPO growth slowing faster than revenue

---

## Semiconductors

### Key Metrics

| Metric | Definition | Best-in-Class | Good | Concerning |
|--------|------------|---------------|------|------------|
| **Capacity Utilization** | Actual output / Max capacity | >85% | 70-85% | <70% |
| **Inventory (DOI)** | Days of Inventory | <60 days | 60-90 days | >90 days |
| **Gross Margin** | Industry varies by segment | >50% | 40-50% | <40% |
| **Book-to-Bill** | Orders / Shipments | >1.1 | 0.9-1.1 | <0.9 |
| **Design Wins** | New customer/product victories | Growing | Stable | Declining |
| **Content per Device** | $ per end unit | Increasing | Stable | Decreasing |
| **R&D Intensity** | R&D / Revenue | 15-25% | 10-30% | |

### Segment Benchmarks

| Segment | Typical GM | Key Drivers |
|---------|------------|-------------|
| Fabless | 50-70% | Design differentiation |
| IDM | 40-55% | Manufacturing efficiency |
| Foundry | 45-55% | Utilization, node leadership |
| Equipment | 40-50% | Technology cycles |
| Memory | 30-50% | Supply/demand balance |

### Red Flags
- Rising inventory at customers (channel stuffing)
- ASP pressure without volume offset
- Losing design wins to competitors
- Falling behind on node transitions
- End-market mix deteriorating

---

## Hardware / Devices

### Key Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Unit Growth** | YoY device shipments | Positive |
| **ASP Trend** | Average Selling Price | Stable/Up |
| **Attach Rate** | Services/accessories per device | Increasing |
| **Installed Base** | Active devices | Growing |
| **Replacement Cycle** | Average time between purchases | Stable |
| **Market Share** | Units or revenue share | Stable/Growing |
| **Gross Margin** | Gross Profit / Revenue | >30% |

### Red Flags
- Elongating product cycles
- Losing share in core markets
- Margin pressure from components
- Over-reliance on single product (>50% revenue)
- Channel inventory build

---

## Internet / Digital Platforms

### Key Metrics

| Metric | Definition | Best-in-Class | Good | Concerning |
|--------|------------|---------------|------|------------|
| **MAU/DAU** | Monthly/Daily Active Users | Growing >20% | 10-20% growth | <10% or declining |
| **DAU/MAU Ratio** | Engagement indicator | >50% | 30-50% | <30% |
| **ARPU** | Average Revenue Per User | Increasing | Stable | Declining |
| **Time Spent** | Engagement depth | Increasing | Stable | Declining |
| **Take Rate** | Platform fee (marketplaces) | Stable/Up | | Declining |
| **Ad Load** | Ads per impression/session | Balanced | | Excessive |
| **CAC** | Cost to acquire user | Declining | Stable | Increasing |
| **Content Cost %** | Content / Revenue | Decreasing | Stable | Increasing |

### Platform-Specific Metrics

**Social/UGC:**
- Time spent per DAU
- Content creation rate
- Virality coefficient

**E-commerce/Marketplace:**
- GMV (Gross Merchandise Value)
- Take rate
- Buyer/seller ratio
- Repeat purchase rate

**Ad-Supported:**
- Ad revenue per user
- Ad pricing (CPM/CPC)
- Advertiser count and diversification

### Red Flags
- User growth deceleration
- Engagement metrics declining
- Rising content/traffic acquisition costs
- Regulatory pressure on core model
- Negative network effects (spam, quality decline)

---

## Technology Valuation Context

### Typical Multiples by Sub-Sector

| Sub-Sector | EV/Revenue | EV/EBITDA | P/E | Key Driver |
|------------|------------|-----------|-----|------------|
| High-Growth SaaS | 10-30x | 50-100x+ | N/A | Growth rate, NRR |
| Mature Software | 5-10x | 15-25x | 25-40x | FCF margin, growth |
| Semiconductors | 3-8x | 10-20x | 15-25x | Cycle position, content |
| Hardware | 1-3x | 8-15x | 12-20x | Market share, margin |
| Internet | 5-15x | 20-40x | 30-60x | Growth, engagement |

### Multiple Drivers

**Premium Factors:**
- >30% revenue growth
- >110% NRR
- Rule of 40 > 40%
- Market leadership
- Expanding TAM

**Discount Factors:**
- <15% growth
- <100% NRR
- Negative FCF at scale
- Competitive pressure
- Regulatory risk

## Integration

- **Primary Application:** `04_INDUSTRY_ANALYSIS.md` (sector-specific KPI analysis for technology companies)
- **Feeds Into:** `02_BUSINESS_MODEL.md` (SaaS unit economics, semiconductor cost structure), `05_FINANCIAL_ANALYSIS.md` (sector-appropriate margin analysis), `06_VALUATION.md` (growth-adjusted multiples, Rule of 40 context)
- **Cross-Reference:** `seven_powers_framework.md` (network effects and switching costs especially relevant for platforms/SaaS), `moat_assessment.md` (technology moat durability assessment)
- **Authority:** @Sector_Technology has sole authority for technology sector metric selection and benchmarking

---

*TAM is not a thesis. Retention, margins, and cycle position are. Know which kind of tech company you're analyzing.*
