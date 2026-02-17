# Conviction Scoring Framework

> **Classification:** POSITION SIZING AND CONVICTION FRAMEWORK
> **Applied To:** Every investment thesis at the recommendation stage
> **Version:** 1.0
> **Framework Owner:** @Thesis_Synthesizer

---

## Core Principle

**Conviction is not a feeling -- it is a weighted score across six measurable factors that maps directly to position size.**

Conviction scoring exists to prevent two failure modes: oversizing positions based on narrative enthusiasm, and undersizing positions where the evidence is strong but the idea is uncomfortable. The score is mechanical by design -- it forces the analyst to justify every dimension independently rather than letting a compelling story carry weak fundamentals.

The uncomfortable truth: most fund managers size positions by gut feel and post-rationalize the decision. "High conviction" becomes whatever position they happened to take, not the output of a disciplined process. This framework makes the sizing decision auditable and repeatable. If two analysts score the same company and arrive at different conviction levels, the disagreement is visible at the factor level -- not buried in competing narratives.

---

## Conviction Score Definition

The **conviction score** is a 1-5 rating that reflects confidence in the investment thesis based on multiple factors. It directly maps to position sizing recommendations.

## Scoring Rubric

### Factor Definitions

| Factor | Weight | Description |
|--------|--------|-------------|
| **Thesis Clarity** | 20% | How clear, specific, and differentiated is the thesis? |
| **Moat Strength** | 20% | How strong and durable is the competitive advantage? |
| **Catalyst Clarity** | 20% | How identifiable and timely are the catalysts? |
| **Risk/Reward** | 20% | How attractive is the asymmetry of outcomes? |
| **Data Quality** | 10% | How complete and reliable is the research? |
| **Management Quality** | 10% | How capable and aligned is management? |

### Individual Factor Scoring

#### Thesis Clarity (20%)

| Score | Definition |
|-------|------------|
| 5 | Unique, highly specific thesis with clear variant perception |
| 4 | Clear thesis with identifiable market misperception |
| 3 | Reasonable thesis but limited differentiation |
| 2 | Generic thesis with unclear differentiation |
| 1 | No clear thesis or highly speculative |

**Questions to Answer:**
- What specifically is the market missing?
- Why are we right and the market wrong?
- How differentiated is our view?

#### Moat Strength (20%)

| Score | Definition |
|-------|------------|
| 5 | Wide moat with multiple durable sources, strengthening |
| 4 | Wide or strong narrow moat, stable |
| 3 | Narrow moat, stable |
| 2 | Weak moat or narrow moat that's eroding |
| 1 | No moat or rapidly eroding moat |

**Questions to Answer:**
- What is the source of competitive advantage?
- How long can advantage persist?
- Is the moat strengthening or weakening?

#### Catalyst Clarity (20%)

| Score | Definition |
|-------|------------|
| 5 | Multiple clear catalysts with specific timing in next 6 months |
| 4 | At least one clear catalyst with reasonable timing estimate |
| 3 | Catalyst identified but timing uncertain |
| 2 | Vague catalyst or very uncertain timing |
| 1 | No identifiable catalyst ("just cheap") |

**Questions to Answer:**
- What will cause the market to re-rate?
- When will the catalyst occur?
- How confident are we in the catalyst?

#### Risk/Reward (20%)

| Score | Definition |
|-------|------------|
| 5 | >3:1 upside/downside ratio with high probability of base case |
| 4 | 2-3:1 ratio with reasonable base case probability |
| 3 | 1-2:1 ratio, balanced risk/reward |
| 2 | <1:1 ratio or high uncertainty on outcomes |
| 1 | Unfavorable risk/reward or extreme uncertainty |

**Questions to Answer:**
- What is the upside to bull case?
- What is the downside to bear case?
- What is the probability-weighted expected return?

#### Data Quality (10%)

| Score | Definition |
|-------|------------|
| 5 | Comprehensive research with all key questions answered |
| 4 | Solid research with minor gaps |
| 3 | Adequate research but some meaningful gaps |
| 2 | Significant data gaps affecting confidence |
| 1 | Major data gaps or unverifiable claims |

**Questions to Answer:**
- Are there significant data gaps?
- How verifiable is the analysis?
- Is there meaningful uncertainty from data limitations?

#### Management Quality (10%)

| Score | Definition |
|-------|------------|
| 5 | Excellent track record, strong alignment, no red flags |
| 4 | Good track record, reasonable alignment, minor concerns |
| 3 | Adequate management, some concerns |
| 2 | Meaningful concerns about capability or alignment |
| 1 | Significant red flags or poor track record |

**Questions to Answer:**
- Does management have a track record of execution?
- Is management aligned with shareholders?
- Are there governance red flags?

## Conviction Calculation

### Weighted Score Calculation

| Factor | Weight | Score (1-5) | Weighted Score |
|--------|--------|-------------|----------------|
| Thesis Clarity | 20% | [X] | [X * 0.20] |
| Moat Strength | 20% | [X] | [X * 0.20] |
| Catalyst Clarity | 20% | [X] | [X * 0.20] |
| Risk/Reward | 20% | [X] | [X * 0.20] |
| Data Quality | 10% | [X] | [X * 0.10] |
| Management Quality | 10% | [X] | [X * 0.10] |
| **Total Conviction** | 100% | | **[Sum]** |

### Conviction to Score Mapping

| Weighted Score | Conviction Level | Description |
|----------------|-----------------|-------------|
| 4.5-5.0 | **5 - Very High** | Strong thesis, clear catalyst, asymmetric R/R |
| 3.5-4.4 | **4 - High** | Solid thesis, identifiable catalyst, favorable R/R |
| 2.5-3.4 | **3 - Medium** | Reasonable thesis, catalyst timing uncertain |
| 1.5-2.4 | **2 - Low** | Thesis has holes, catalyst unclear |
| 1.0-1.4 | **1 - Very Low** | Weak thesis, no clear catalyst |

## Position Sizing Tiers

### Tier Definitions

| Tier | Size Range | Conviction | Additional Requirements |
|------|------------|------------|------------------------|
| **Tier 1** | 4-6% | 5 | Multiple catalysts, >3:1 R/R, wide moat |
| **Tier 2** | 2-4% | 4-5 | Clear catalyst, >2:1 R/R |
| **Tier 3** | 1-2% | 3-4 | Reasonable thesis, balanced R/R |
| **Tier 4** | 0.5-1% | 2-3 | Speculative, requires monitoring |
| **Pass** | 0% | 1-2 | Insufficient conviction |

### Tier Requirements Matrix

| Requirement | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|-------------|--------|--------|--------|--------|
| Conviction Score | >=4.5 | >=3.5 | >=2.5 | >=1.5 |
| Catalyst Identified | Yes, multiple | Yes | Preferred | Optional |
| Risk/Reward | >3:1 | >2:1 | >1:1 | Any |
| Moat | Wide | Narrow+ | Any | Any |
| Data Completeness | High | Good | Adequate | Limited |

## Conviction Modifiers

### Upward Modifiers
| Modifier | Impact | Condition |
|----------|--------|-----------|
| Insider buying | +0.25 | Material recent purchases |
| Activist involved | +0.25 | Credible activist with history |
| Multiple catalysts | +0.25 | 3+ catalysts in 12 months |
| Hidden value | +0.25 | SOTP > market value |

### Downward Modifiers
| Modifier | Impact | Condition |
|----------|--------|-----------|
| Management concerns | -0.25 | Red flags identified |
| High short interest | -0.25 | >15% SI with credible thesis |
| Data quality issues | -0.25 | Significant unverified claims |
| Thesis crowded | -0.25 | Consensus already reflects thesis |

## Conviction Review Triggers

### When to Review Conviction

| Trigger | Action |
|---------|--------|
| Earnings release | Re-evaluate thesis and catalyst |
| Price move >15% | Reassess risk/reward |
| Catalyst occurs | Update catalyst score |
| New information | Re-evaluate relevant factors |
| Quarterly | Routine review |

### Conviction Change Log

| Date | Old Score | New Score | Reason |
|------|-----------|-----------|--------|
| [Date] | [X] | [Y] | [Brief reason] |

## Output Format

```
## Conviction Assessment

**Conviction Score:** [X]/5
**Position Tier:** [Tier X]
**Recommended Size:** [X-Y]%

| Factor | Score |
|--------|-------|
| Thesis Clarity | [X]/5 |
| Moat Strength | [X]/5 |
| Catalyst Clarity | [X]/5 |
| Risk/Reward | [X]/5 |
| Data Quality | [X]/5 |
| Management | [X]/5 |

**Rationale:** [Why this conviction level?]
```

## Integration

- **Primary Application:** `11_INVESTMENT_THESIS.md` (conviction section), `14_INVESTMENT_MEMO_FINAL.md` (recommendation and position sizing)
- **Cross-Reference:** `catalyst_taxonomy.md` (catalyst clarity factor), `moat_assessment.md` (moat strength factor), `management_red_flags.md` (management quality factor)
- **Authority:** @Thesis_Synthesizer has sole authority for final conviction scoring

---

*Conviction without a framework is gambling. Size positions by evidence, not enthusiasm.*
