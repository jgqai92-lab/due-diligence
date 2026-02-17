# Demand Quantification Framework

> **Classification:** QUANTITATIVE DEMAND MODELING FRAMEWORK
> **Applied To:** Every demand claim in the IST pipeline
> **Version:** 1.0
> **Framework Owner:** @Bottleneck_Mapper

---

## Core Principle

**No thesis without numbers. Every demand claim must resolve to a quantitative model.**

Narratives are hypotheses. Numbers are evidence. The IST does not advance a thesis on the basis of "demand is growing" or "there's a shortage." Every demand claim must be decomposed into a model with explicit inputs, multipliers, sources, and confidence levels. If you cannot quantify it, you cannot size a position on it.

**Uncomfortable truth:** Most demand estimates are wrong by at least 50%. The question is not whether your model is wrong, but whether it is *less wrong* than the market's implicit model. A model that is 30% off but structurally directional is more valuable than no model. But a model presented as precise when it is approximate is a liability.

---

## The 1 GW Cluster Formula (Exemplar)

This model demonstrates the standard for demand quantification. A single claim ("AI clusters need a lot of power") becomes a fully specified model:

| Component | Value | Source | Multiplier | Adjusted Value | Confidence |
|-----------|-------|--------|------------|----------------|------------|
| GPU count per cluster | 330,000 GPUs | [SOURCE: hyperscaler announcements] | -- | 330,000 GPUs | High |
| Base power per cluster | 1.0 GW | [SOURCE: industry estimates] | 1.0x | 1.0 GW | High |
| Cooling overhead | -- | [EXT-SOURCE: data center engineering] | 1.4x | 1.4 GW | Medium |
| Maintenance / availability | -- | [ESTIMATE(industry standard 80% uptime)] | 1.25x | 1.75 GW | Medium |
| **Total effective demand per cluster** | -- | -- | -- | **~1.75 GW** | Medium |

**Key insight:** The raw "1 GW" figure understates actual demand by 75%. Without the multipliers, every downstream calculation is wrong.

---

## Demand Model Template

Every demand model in the IST must follow this structure. Copy and populate for each demand claim.

```
### Demand Model: [Name / Thesis]
Date: [DATE]
Analyst: [AGENT]

| Component | Value | Source | Multiplier | Adjusted Value | Confidence |
|-----------|-------|--------|------------|----------------|------------|
| Base demand | [X] | [TAG] | 1.0x | [X] | [H/M/L] |
| Cooling / thermal multiplier | -- | [TAG] | [X.Xx] | [Adjusted] | [H/M/L] |
| Maintenance / availability | -- | [TAG] | [X.Xx] | [Adjusted] | [H/M/L] |
| Redundancy / N+1 | -- | [TAG] | [X.Xx] | [Adjusted] | [H/M/L] |
| Seasonal peak factor | -- | [TAG] | [X.Xx] | [Adjusted] | [H/M/L] |
| Growth rate (annualized) | -- | [TAG] | [X.Xx] | [Adjusted] | [H/M/L] |
| **Total effective demand** | -- | -- | -- | **[Total]** | **[Overall]** |

Composite Multiplier: [Product of all multipliers]
Headline-to-Effective Ratio: [Total / Base] (how much the headline underestimates reality)
```

### Multiplier Library

Common multipliers encountered in AI infrastructure demand modeling:

| Multiplier | Typical Range | Applies To | Source Basis |
|------------|---------------|------------|--------------|
| Cooling overhead | 1.2x - 1.5x | Power demand | PUE (Power Usage Effectiveness) ratios |
| Maintenance / uptime | 1.15x - 1.30x | Capacity planning | Target availability (80-90% uptime) |
| N+1 redundancy | 1.10x - 1.25x | Infrastructure count | Fault tolerance requirements |
| Seasonal peak | 1.05x - 1.20x | Energy / cooling | Summer peak load vs. annual average |
| Ramp inefficiency | 1.10x - 1.30x | New facilities | First 12-18 months sub-optimal utilization |
| Supply chain buffer | 1.05x - 1.15x | Component orders | Safety stock and lead time hedge |

---

## Supply-Demand Gap Analysis

After modeling demand, compare against modeled supply to identify gaps.

### Gap Analysis Template

```
### Supply-Demand Gap: [Constraint / Component]
Date: [DATE]
Time Horizon: [Months]

| Metric | Value | Source | Confidence |
|--------|-------|--------|------------|
| Total Effective Demand (from model above) | [X] | [Demand Model] | [H/M/L] |
| Current Supply (installed capacity) | [Y] | [TAG] | [H/M/L] |
| Planned Supply Additions | [Z] | [TAG] | [H/M/L] |
| Realistic Supply (adjusted for delays/cancellations) | [Z * adj] | [ESTIMATE(method)] | [H/M/L] |
| **Supply-Demand Gap** | **[Demand - Realistic Supply]** | -- | -- |
| **Gap as % of Demand** | **[Gap / Demand * 100]%** | -- | -- |

Gap Classification:
- [ ] Structural Deficit (>20% gap, persists 3+ years)
- [ ] Cyclical Deficit (10-20% gap, resolving within 2 years)
- [ ] Tight Balance (5-10% gap, pricing power but not shortage)
- [ ] Adequate Supply (<5% gap or surplus)

Investment Implication: [Statement]
```

---

## Sensitivity Analysis

Every demand model must include sensitivity testing. The standard test: **What if the key input is 20% higher or lower?**

### Sensitivity Template

```
### Sensitivity Analysis: [Model Name]

Base Case: [Total effective demand from model]

| Scenario | Key Variable Change | Adjusted Demand | Delta vs. Base | Implication |
|----------|---------------------|-----------------|----------------|-------------|
| Bull +20% | [Variable] +20% | [Recalculated] | [+X%] | [Impact on thesis] |
| Bull +10% | [Variable] +10% | [Recalculated] | [+X%] | [Impact on thesis] |
| Base | No change | [Base case] | 0% | Reference |
| Bear -10% | [Variable] -10% | [Recalculated] | [-X%] | [Impact on thesis] |
| Bear -20% | [Variable] -20% | [Recalculated] | [-X%] | [Impact on thesis] |

Thesis Robustness: Does the supply-demand gap persist in the Bear -20% scenario?
- [ ] Yes -> Thesis is robust to downside
- [ ] No -> Thesis is demand-estimate dependent (increase uncertainty)

Key Variable Identification: Which single input, if wrong, breaks the model?
Variable: [Name]
Break-even value: [The value at which the gap closes]
Likelihood of break-even: [Assessment]
```

---

## Source Validation Requirements

Every number in a demand model must carry a source tag. No exceptions.

| Tag | Meaning | Minimum Standard | Acceptable For |
|-----|---------|------------------|----------------|
| `[SOURCE]` | Primary source from IST research briefing | Direct quote or data point from input material | Base demand figures, primary claims |
| `[EXT-SOURCE]` | External corroboration | Named source, publication, date, retrievable | Multipliers, industry benchmarks |
| `[MARKET-DATA]` | Market data or financial metrics | Ticker, metric, date, data provider | Revenue, capacity, pricing data |
| `[ESTIMATE(method)]` | IST-generated estimate | Calculation shown, all assumptions explicit | Derived figures, gap calculations |
| `[CONSENSUS]` | Analyst consensus or industry survey | Source of consensus, date, range provided | Forecasts, growth rates |
| `[MANAGEMENT]` | Company management guidance | Earnings call date, exact quote | Capex plans, capacity targets |

### Source Quality Hierarchy

When multiple sources conflict, use this hierarchy:

1. **Physical/engineering constraints** (laws of physics, thermodynamics) -- highest confidence
2. **Installed base / capacity data** (measurable, verifiable)
3. **Order backlog / contractual commitments** (committed, but cancellable)
4. **Management guidance** (incentivized to be optimistic)
5. **Analyst estimates** (derived, varying quality)
6. **Extrapolation** (lowest confidence, must be flagged)

---

## Common Demand Modeling Pitfalls

| Pitfall | Why It's Wrong | Correction |
|---------|---------------|------------|
| **Assuming 100% utilization** | No facility runs at 100%; maintenance, ramp, and faults reduce effective capacity | Apply maintenance/availability multiplier (typically 1.15-1.30x) |
| **Ignoring seasonal peaks** | Annual average demand understates peak demand that drives capacity planning | Model peak demand separately; infrastructure must be sized for peaks |
| **Conflating nameplate vs. effective capacity** | A "1 GW" facility does not deliver 1 GW of usable compute power | Apply PUE and availability multipliers to get effective capacity |
| **Double-counting multipliers** | Applying cooling overhead *and* PUE when they measure the same thing | Clarify whether multiplier is incremental or inclusive |
| **Using announcement data as supply** | "Company X announced a new factory" != factory exists | Discount announced supply by historical completion rates (typically 60-80%) |
| **Linear extrapolation of exponential demand** | AI demand may grow exponentially; linear models understate | Use appropriate growth model, flag assumption explicitly |
| **Ignoring demand destruction** | At high enough prices, some demand gets destroyed or deferred | Include price elasticity assessment in sensitivity analysis |
| **Single-point estimates** | A single number implies false precision | Always provide a range (base, bull, bear) |

---

## Model Validation Checklist

Before a demand model is accepted into IST analysis:

| Check | Question | Pass/Fail |
|-------|----------|-----------|
| **Sourced** | Does every input have a source tag? | |
| **Multiplied** | Have all relevant multipliers been applied? | |
| **Bounded** | Is there a range (not just a point estimate)? | |
| **Sensitivity-Tested** | Has the key variable been stressed +/- 20%? | |
| **Gap-Analyzed** | Has supply been compared against demand? | |
| **Pitfall-Checked** | Have common pitfalls been explicitly avoided? | |
| **Time-Stamped** | Is the model dated and tied to a specific time horizon? | |
| **Unit-Consistent** | Are all units consistent (GW, MW, TWh -- not mixed)? | |
| **Cross-Referenced** | Does the model align with other IST demand models? | |
| **Falsifiable** | What evidence would invalidate this demand estimate? | |

---

## Aggregation Rules

When combining multiple demand models into a total demand picture:

1. **No double-counting:** Ensure models cover distinct demand segments
2. **Consistent time horizons:** All models must be for the same period
3. **Weighted by confidence:** High-confidence models weighted more in composite
4. **Range preservation:** Aggregate the ranges, not just the base cases
5. **Dependency mapping:** Note which demand models are independent vs. correlated

---

## Integration

- **Primary Application:** `03_DEMAND_MODELS.md` (all quantitative demand models)
- **Feeds Into:** `02_BOTTLENECK_MAP.md` (demand validates bottleneck binding), `05_EQUITY_CANDIDATES.md` (demand drives candidate selection)
- **Cross-Reference:** `sequential_bottleneck.md` (demand must be phase-aware), `scarcity_abundance.md` (demand without scarcity is not investable)
- **Override Authority:** @Screen_Synthesizer may adjust demand models with documented rationale and updated source tags

---

*If you can't model the demand, you can't size the position. Every narrative must become a number.*
