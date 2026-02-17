# Stress-Testing & Null Hypothesis Framework

> **Classification:** THESIS CHALLENGE AND POSITION SIZING FRAMEWORK
> **Applied To:** Every thesis before it receives a tier classification or position sizing
> **Version:** 1.0
> **Framework Owner:** @Screen_Pessimist, @Screen_Synthesizer

---

## Core Principle

**Every thesis must survive explicit challenge. Stress-testing informs position sizing, not just risk disclosure.**

Stress-testing is not a compliance exercise. It is the mechanism that translates conviction into position size. A thesis that survives 8 of 8 challenges earns a larger allocation than one that survives 5 of 8. A thesis that survives fewer than 3 does not earn a position at all.

The null hypothesis for every investment thesis is: **"This thesis is wrong, and the current market price is correct."** The burden of proof is on the thesis to survive challenge, not on the market to justify itself.

---

## Null Hypothesis Testing Template

Every thesis must be subjected to these 8 standard tests. Answers must include specific evidence, not vague reassurances.

```
### Null Hypothesis Test: [THESIS NAME / TICKER]
Date: [DATE]
Tested By: [AGENT]
```

| # | Test | Question | Answer | Evidence Tag | Impact if Wrong |
|---|------|----------|--------|--------------|-----------------|
| 1 | **Preconditions** | What must be true for this thesis to work? | [List every necessary condition explicitly] | [TAG] | [What happens if any precondition fails] |
| 2 | **Kill Shot** | What single development could make this thesis completely wrong? | [Identify the most dangerous threat] | [TAG] | [Severity: terminal / severe / manageable] |
| 3 | **Base Rate** | What is the base rate for this type of prediction being correct? | [Historical success rate of similar theses] | [TAG] | [If base rate is <50%, thesis needs exceptional evidence to proceed] |
| 4 | **Selection Bias** | Is there selection bias in the sourcing? | [Who provided the thesis? What are their incentives?] | [TAG] | [If bias exists, what independent corroboration exists?] |
| 5 | **Timeline Risk** | What is the timeline risk? | [Most tech predictions are wrong on timing, not direction] | [TAG] | [What happens if thesis is right but 2 years late?] |
| 6 | **Efficiency Gains** | What efficiency gains could reduce demand? | [DeepSeek-type risk: breakthroughs that reduce resource intensity] | [TAG] | [Quantify demand impact of 30-50% efficiency improvement] |
| 7 | **Coordination vs. Capacity** | Could the constraint be a coordination problem rather than a capacity problem? | [Some "shortages" are really misallocation, solvable without new supply] | [TAG] | [If coordination solves it, the scarcity premium disappears] |
| 8 | **Capex Deceleration** | What if AI capex decelerates due to ROI scrutiny? | [AI investment requires continued confidence in ROI; what if it falters?] | [TAG] | [Quantify thesis sensitivity to 20-30% capex reduction] |

### Survival Scoring

| Tests Survived | Classification |
|----------------|----------------|
| 7-8 of 8 | **High Survival** -- Thesis is robust; proceed with full conviction |
| 5-6 of 8 | **Medium Survival** -- Thesis has meaningful vulnerabilities; proceed with reduced conviction |
| 3-4 of 8 | **Low Survival** -- Thesis has significant weaknesses; proceed only at minimal size or as a watch position |
| 0-2 of 8 | **Failed** -- Thesis does not survive challenge; no position recommended |

### Test Survival Criteria

A test is "survived" if:
- The answer provides specific, sourced evidence (not vague reassurance)
- The impact, if wrong, is quantified and manageable at the proposed position size
- There is a monitoring mechanism to detect if the assumption is breaking down

A test is "failed" if:
- The answer is "we don't think that will happen" without evidence
- The impact if wrong would be catastrophic at the proposed position size
- There is no way to monitor the assumption in real-time

---

## Source Credibility Assessment

Every thesis originates from a source. That source has biases. Assess them explicitly.

### Source Assessment Template

```
### Source Credibility: [SOURCE NAME / DESCRIPTION]
```

| Factor | Assessment |
|--------|------------|
| **Source Identity** | [Who is making this claim? Name, role, organization] |
| **Known Incentives** | [How does this source benefit if the claim is believed? Financial position, career incentives, attention incentives] |
| **Bias Direction** | [Bull bias (they own the stock / sell the product), Bear bias (they're short / competitive), or Neutral] |
| **Track Record on Predictions** | [Has this source made similar predictions before? Were they accurate? Cite specific examples] |
| **Specificity of Claims** | [Are claims specific and falsifiable, or vague and unfalsifiable?] |
| **Mitigation** | [What independent corroboration exists? Has the claim been verified by a source with different incentives?] |

### The Musk Timeline Caveat

Certain sources have well-documented patterns that must be explicitly factored in:

**Elon Musk Timeline Adjustment:**
- Track record of aggressive timelines: FSD ("next year" for 5+ years), Cybertruck (2+ years late), Robotaxi (repeatedly delayed), Mars colonization (decade+ behind stated timeline)
- **Framework rule:** Any Musk-sourced timeline must be multiplied by 2-3x for planning purposes
- **Implication:** If a thesis depends on Musk-stated timelines, the thesis must be robust to 2-3x delay
- **This is not a quality judgment** -- it is a calibration based on observed data

This principle generalizes: any source with a documented pattern of timeline optimism must have an explicit adjustment factor applied.

### Source Credibility Scoring

| Score | Meaning | Treatment |
|-------|---------|-----------|
| 5 | Independent, no financial incentive, strong track record | Accept claims with standard evidence bar |
| 4 | Credible source with minor incentive alignment | Accept with one independent corroboration |
| 3 | Known incentives but historically reliable | Require independent corroboration |
| 2 | Significant incentive bias, mixed track record | Require multiple independent corroborations |
| 1 | Strong incentive bias, poor track record, or promotional | Do not use as primary source; corroborate from scratch |

---

## Stress Test Categories (Extended)

Beyond the 8 standard tests, these additional stress tests can be applied when relevant:

### Technology Risk

| Test | Question |
|------|----------|
| Substitution | Could a different technology solve the same problem without this bottleneck? |
| Leapfrogging | Could a breakthrough skip the constraint entirely? (e.g., quantum computing reducing classical compute demand) |
| Commoditization | If the technology is successful, does success commoditize the investment? |

### Market Structure Risk

| Test | Question |
|------|----------|
| New entrants | What prevents new competitors from entering in 2-3 years? |
| Customer concentration | Is demand driven by 3-5 hyperscalers who could change strategy? |
| Pricing power durability | Can the company maintain pricing power as supply expands? |

### Policy / Regulatory Risk

| Test | Question |
|------|----------|
| Tariff / trade policy | Could trade policy changes disrupt the supply chain thesis? |
| Subsidy dependency | Does the thesis depend on government subsidies that could be revoked? |
| Environmental regulation | Could environmental policy slow or block the buildout? |

### Macro Risk

| Test | Question |
|------|----------|
| Interest rate sensitivity | How does the thesis perform at 2% higher interest rates? |
| Recession scenario | Does demand persist in a recession, or is it capex-dependent? |
| Dollar strength | Does currency movement affect the thesis (international supply chains)? |

---

## Stress Test to Position Sizing Mapping

This is the operational output of the framework. Survival score directly determines maximum position size.

| Survival Score | Position Size Range | Position Sizing Rationale |
|----------------|---------------------|---------------------------|
| **High (7-8 tests survived)** | 5-8% of thematic allocation | Thesis is robust to most challenges; size reflects high conviction |
| **Medium (5-6 tests survived)** | 3-5% of thematic allocation | Thesis has identified vulnerabilities; reduced size provides buffer |
| **Low (3-4 tests survived)** | 1-3% of thematic allocation | Thesis is fragile; minimal position allows participation without significant risk |
| **Failed (<3 tests survived)** | 0% -- No position / Tier 3 watch only | Thesis does not survive scrutiny; position would be speculation, not investment |

### Position Size Modifiers

| Modifier | Adjustment | Condition |
|----------|------------|-----------|
| Multiple independent theses converge | +1-2% | Effects convergence from `multi_order_effects.md` |
| Strong analytical parallel | +1% | Parallel score >= 4.0 from `analytical_parallels.md` |
| Scar tissue thesis confirmed | +1% | Scar tissue score >= 4.0 from `scar_tissue_thesis.md` |
| Liquidity risk (small cap, thin trading) | -1-2% | Average daily volume < $10M |
| Single catalyst dependency | -1% | Entire thesis depends on one event |
| Management quality concerns | -1% | Governance, track record, or alignment issues |

---

## Monitoring Framework

Every surviving thesis must have monitoring criteria defined. If assumptions break, the position should be reduced or exited.

### Monitoring Template

```
### Monitoring Criteria: [THESIS / TICKER]

| Assumption Being Monitored | Metric | Current Value | Warning Threshold | Exit Threshold |
|----------------------------|--------|---------------|-------------------|----------------|
| [Assumption 1] | [Metric] | [Value] | [Yellow] | [Red] |
| [Assumption 2] | [Metric] | [Value] | [Yellow] | [Red] |
| [Assumption 3] | [Metric] | [Value] | [Yellow] | [Red] |

Review Frequency: [Weekly / Monthly / Quarterly]
Last Reviewed: [DATE]
Status: [Green / Yellow / Red]
```

---

## Pre-Mortem Exercise

For high-conviction positions (5%+ allocation), conduct a pre-mortem:

> "It is 12 months from now. This position has lost 40% of its value. What happened?"

Write 3 distinct scenarios that could cause this outcome:

```
### Pre-Mortem: [TICKER]

Scenario 1: [Name]
- What happened: [Narrative]
- Warning signs we missed: [What we should have seen]
- Probability assessment: [X%]

Scenario 2: [Name]
- What happened: [Narrative]
- Warning signs we missed: [What we should have seen]
- Probability assessment: [X%]

Scenario 3: [Name]
- What happened: [Narrative]
- Warning signs we missed: [What we should have seen]
- Probability assessment: [X%]

Combined probability of significant loss: [Sum of scenarios, capped at 100%]
Acceptable given position size: [Yes / No]
```

---

## Interaction with Other Frameworks

| Framework | How It Interacts with Null Hypothesis |
|-----------|---------------------------------------|
| `scarcity_abundance.md` | Test #7 (coordination vs. capacity) directly challenges scarcity claims |
| `sequential_bottleneck.md` | Test #5 (timeline risk) challenges phase timing assumptions |
| `demand_modeling.md` | Test #6 (efficiency gains) challenges demand model inputs |
| `scar_tissue_thesis.md` | Test #3 (base rate) challenges whether "this time is different" |
| `analytical_parallels.md` | Parallels must survive stress tests independently; parallel conviction does not exempt from testing |
| `multi_order_effects.md` | Higher-order effects need stricter testing; 3rd order effects should survive all 8 tests despite higher inherent uncertainty |

---

## Integration

- **Primary Application:** `11_STRESS_TESTS.md` (all thesis stress tests) and `.ist/PESSIMIST_REVIEW.md` (pessimist's challenge document)
- **Feeds Into:** `06_TIER_CLASSIFICATION.md` (survival score is a tier determinant), position sizing in `10_PORTFOLIO_CONSTRUCTION.md`
- **Cross-Reference:** All other frameworks (every framework's output is subject to null hypothesis testing)
- **Authority:** @Screen_Pessimist has primary authority for stress test application; @Screen_Synthesizer has override authority with documented rationale

---

*The market is the null hypothesis. Every thesis must prove the market wrong, not assume it.*
