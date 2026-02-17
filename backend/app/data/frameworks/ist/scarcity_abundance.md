# Visser's Scarcity/Abundance Framework

> **Classification:** DEFAULT SCREENING FRAMEWORK
> **Applied To:** Every equity candidate entering the IST pipeline
> **Version:** 1.0
> **Framework Owner:** @Content_Analyst, @Equity_Scanner

---

## Core Principle

**AI creates digital abundance. Physical scarcity is where alpha lives.**

As AI scales, it drives the marginal cost of digital outputs toward zero. Knowledge, code, content, analysis, and generic software become commoditized. The investment implication is directional and stark: overweight what AI cannot replicate (atoms), discount what it can (bits).

The filtering question applied to every candidate:

> "Does this company benefit from scarcity or abundance?"

The heuristic:

> "If Claude can do it in 5 minutes, it's not a moat. If it takes 2 years and $500M in capex, it might be."

---

## Abundance Zone (Discount / Avoid)

Assets in the abundance zone face margin compression as AI commoditizes their output. These categories should carry a structural discount in IST screening unless exception criteria are met.

| Category | Why It's Abundant | Example Pressure |
|----------|-------------------|------------------|
| Knowledge / Research | Models synthesize faster, cheaper, at scale | Sell-side research, consulting reports |
| Code / Software Engineering | AI code generation reduces dev cost per feature | Generic SaaS, custom dev shops |
| Content Creation | Text, image, video generation at near-zero marginal cost | Content farms, stock media, ad copy |
| Generic SaaS | "We wrote complex software" is no longer a moat | Horizontal SaaS with no data network effects |
| Analysis / Reports | Structured analysis is a model's core competency | Financial modeling, market research |
| Customer Support | Agentic AI handles 80%+ of routine interactions | BPO, call centers, Tier 1 support |

**Key Insight:** SaaS moats built on "we wrote complex software that's hard to replicate" face compression. The complexity of the code was the moat; AI makes complexity cheap.

### SaaS Exception Criteria

A SaaS company may escape the abundance discount if it meets **2 or more** of these criteria:

| Exception | Description | Evidence Required |
|-----------|-------------|-------------------|
| Proprietary Data Moat | Company possesses unique, non-replicable datasets that improve with usage | Data flywheel metrics, exclusive data partnerships, user-generated data lock-in |
| Entrenched Business Model | Switching costs are structural, not merely contractual | Integration depth, workflow dependency, migration cost estimates |
| Agentic-World Innovation | Company is building *for* the agentic AI world, not defending against it | Agent-to-agent APIs, AI-native architecture, MCP/tool-use integration |
| Regulatory Lock-In | Compliance requirements create barriers AI alone cannot cross | Certifications, audit trails, regulated data handling |
| Network Effects | Value increases with user count in ways AI cannot replicate solo | Marketplace dynamics, social graphs, protocol standards |

---

## Scarcity Zone (Overweight)

Assets in the scarcity zone are constrained by physical reality, time, regulation, or irreplaceable positioning. These carry a structural premium in IST screening.

| Category | Why It's Scarce | Duration of Scarcity |
|----------|-----------------|----------------------|
| Physical Infrastructure | Data centers, grid interconnections, pipelines -- built in years, not months | Multi-year (permitting + construction) |
| Energy Generation | AI demand is additive to existing load; generation takes years to build | 3-7 years for new capacity |
| Critical Minerals | Geology, processing capacity, and geopolitics constrain supply | Structural (decade-scale) |
| Specialized Manufacturing | Fabs, GOES steel mills, transformer factories -- limited global capacity | 3-5 years minimum expansion |
| Regulatory Moats | Licenses, permits, environmental approvals that cannot be AI-generated | Permanent until policy change |
| Single-Source Suppliers | Sole domestic or global producer of a critical input | Structural until new entrant (years) |
| Skilled Trades / Physical Labor | Electricians, linemen, nuclear engineers -- cannot be automated near-term | 5-10 years (training pipeline) |
| Land / Rights-of-Way | Physical access to grid, water, fiber -- finite and location-specific | Permanent |

---

## Scarcity Strength Scoring

Every equity candidate is scored across 5 dimensions of scarcity. Scores are integers from 1 (weak) to 5 (strong).

| Dimension | 1 (Weak) | 3 (Moderate) | 5 (Strong) | Weight |
|-----------|----------|--------------|------------|--------|
| **Physical Constraint** | Digital/virtual product, easily scaled | Some physical component but not primary | Entirely constrained by atoms, geology, or physics | 25% |
| **Time-to-Replicate** | Competitor could replicate in <6 months | 1-3 year replication timeline | 5+ years to replicate even with unlimited capital | 25% |
| **Pricing Power** | Commodity pricing, no differentiation | Some pricing power in tight markets | Price-maker with demonstrated ability to raise prices | 20% |
| **AI Demand Sensitivity** | No connection to AI/compute buildout | Indirect beneficiary of AI demand | Direct, quantifiable demand driver from AI scaling | 15% |
| **Supply Response Lag** | Supply can respond within 1 year | 2-4 year supply response time | 5+ year lag due to permitting, construction, geology | 15% |

### Composite Score Interpretation

| Composite Score | Classification | Screening Action |
|-----------------|----------------|------------------|
| 4.0 - 5.0 | **Deep Scarcity** | Priority screening, potential Tier 1 candidate |
| 3.0 - 3.9 | **Moderate Scarcity** | Standard screening, Tier 2 candidate |
| 2.0 - 2.9 | **Mixed** | Requires SaaS Exception or other thesis to proceed |
| 1.0 - 1.9 | **Abundance Zone** | Discount or exclude unless exception criteria met |

### Scoring Template

```
Company: [TICKER]
Date Scored: [DATE]

| Dimension              | Score (1-5) | Evidence                          |
|------------------------|-------------|-----------------------------------|
| Physical Constraint    |             | [Specific evidence]               |
| Time-to-Replicate      |             | [Specific evidence]               |
| Pricing Power          |             | [Specific evidence]               |
| AI Demand Sensitivity  |             | [Specific evidence]               |
| Supply Response Lag    |             | [Specific evidence]               |
|------------------------|-------------|-----------------------------------|
| Weighted Composite     |             |                                   |

Classification: [Deep Scarcity / Moderate Scarcity / Mixed / Abundance Zone]
SaaS Exceptions Met: [None / List exceptions]
Screening Decision: [Advance / Hold / Exclude]
```

---

## Evidence Requirements

Every scarcity claim must be supported by tagged evidence:

| Tag | Meaning | Minimum Standard |
|-----|---------|------------------|
| `[SOURCE]` | Primary source from IST research briefing | Direct quote or data point from input |
| `[EXT-SOURCE]` | External corroboration | Named source with date |
| `[MARKET-DATA]` | Market data or financial metrics | Ticker, metric, date |
| `[ESTIMATE(method)]` | IST estimate with methodology | Calculation shown, assumptions explicit |

**No untagged claims.** If a scarcity assertion cannot be sourced, it must be flagged as `[UNVERIFIED]` and cannot contribute to scoring.

---

## Common Misapplications

| Mistake | Correction |
|---------|------------|
| Calling all tech "abundant" | Some tech companies own scarce physical assets (data centers, fabs) |
| Ignoring demand growth rate | A scarce asset with flat demand is not an opportunity |
| Static scarcity assessment | Scarcity changes over time; what's scarce today may not be in 3 years |
| Confusing *current* scarcity with *structural* scarcity | Check if supply is expanding; if lead times are shortening, scarcity is resolving |
| Applying framework to non-AI sectors without adjustment | Framework is calibrated for AI-era dynamics; other sectors need different lenses |

---

## Integration

- **Primary Application:** Applied to every equity candidate in `05_EQUITY_CANDIDATES.md`
- **Feeds Into:** `06_TIER_CLASSIFICATION.md` (scarcity score is a primary tier determinant)
- **Cross-Reference:** `sequential_bottleneck.md` (scarcity is phase-dependent), `demand_modeling.md` (scarcity without demand is irrelevant)
- **Override Authority:** @Screen_Synthesizer may override scarcity classification with documented rationale

---

*This is the default screening lens. Every candidate must pass through this framework before advancing to tier classification.*
