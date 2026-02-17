# Downstream Effects Mapping (Multi-Order Effects)

> **Classification:** NON-CONSENSUS IDEA GENERATION FRAMEWORK
> **Applied To:** Primary theses to extract 2nd and 3rd order investment ideas
> **Version:** 1.0
> **Framework Owner:** @Effects_Analyst

---

## Core Principle

**The best ideas live at the 2nd or 3rd order, where market attention hasn't reached.**

**If your idea is 1st order, you're already too late.** By the time an effect is consensus, the equity is priced. The uncomfortable corollary: if your screen is full of names that appear on CNBC, you haven't pushed far enough downstream.

First-order effects are consensus. When "AI needs power" is on every research note and podcast, the direct beneficiaries are priced. Alpha lives downstream -- in the 2nd and 3rd order consequences that the market hasn't mapped. The further from consensus, the greater the potential mispricing, but also the greater the uncertainty.

This framework provides a systematic method for mapping these downstream effects, identifying investable ideas at each order, and calibrating position sizing to the uncertainty inherent in multi-order reasoning.

---

## Order Definitions

| Order | Definition | Market Awareness | Pricing Status | Example |
|-------|------------|------------------|----------------|---------|
| **1st Order** | Direct, obvious beneficiary of the primary thesis | High (consensus) | Usually fully priced | "AI needs GPUs" -> NVDA |
| **2nd Order** | Consequence of the 1st order effect | Medium (emerging) | Pockets of mispricing | "GPUs need power" -> utilities, IPPs |
| **3rd Order** | Consequence of the 2nd order effect | Low (non-consensus) | Often un-followed, mispriced | "Power needs transformers" -> GOES steel |
| **4th Order** | Consequence of the 3rd order (use sparingly) | Very low (speculative) | Potentially un-investable due to uncertainty | "GOES scarcity" -> secondary transformer market |

### The Attention Gradient

```
1st Order ████████████████████ Market awareness: HIGH    | Alpha potential: LOW
2nd Order ████████████         Market awareness: MEDIUM  | Alpha potential: MEDIUM
3rd Order ████                 Market awareness: LOW     | Alpha potential: HIGH
4th Order ██                   Market awareness: MINIMAL | Alpha potential: HIGH but UNCERTAIN
```

**Key trade-off:** Alpha potential increases with order distance, but so does causal chain fragility. Position sizing must reflect this.

---

## Effects Mapping Template

For each primary thesis, map the downstream effects systematically.

```
### Effects Map: [Primary Thesis Name]
Date: [DATE]
Analyst: [AGENT]

Primary Thesis: [Statement of the core thesis]
Source: [TAG]
```

### Cascade Table

| Layer | Primary Thesis | 1st Order Effect | 2nd Order Effect | 3rd Order Effect |
|-------|---------------|-------------------|-------------------|-------------------|
| **Effect** | [Thesis statement] | [Direct consequence] | [Downstream consequence] | [Further downstream] |
| **Mechanism** | -- | [How thesis causes this] | [How 1st order causes this] | [How 2nd order causes this] |
| **Equity Exposure** | -- | [TICKER(s)] | [TICKER(s)] | [TICKER(s)] |
| **Market Awareness** | -- | High (consensus) | Medium (emerging) | Low (non-consensus) |
| **Evidence Quality** | -- | [Strong/Medium/Weak] | [Strong/Medium/Weak] | [Strong/Medium/Weak] |
| **Time Lag** | -- | [Immediate/months] | [Months/quarters] | [Quarters/years] |
| **Position Size Guidance** | -- | Standard | Reduced | Minimal |

### Multiple Branches

A single primary thesis often generates multiple 2nd and 3rd order branches. Map all of them:

```
                                    ┌─ [2nd Order A] ──── [3rd Order A1]
                                    │                └─── [3rd Order A2]
[Primary Thesis] ── [1st Order] ───┤
                                    │  ┌─ [3rd Order B1]
                                    ├─ [2nd Order B] ──── [3rd Order B2]
                                    │
                                    └─ [2nd Order C] ──── [3rd Order C1]
```

---

## The Transformer Bottleneck Exemplar

This worked example demonstrates multi-order mapping from a real thesis.

**Primary Thesis:** AI data center buildout requires massive new power infrastructure.

| Layer | Effect | Mechanism | Equity Exposure | Market Awareness |
|-------|--------|-----------|-----------------|------------------|
| **1st Order** | Transformer manufacturers benefit from surging orders | Direct demand for power transformers from data center builds | Large-cap industrials (e.g., Eaton, Siemens) | HIGH -- widely discussed |
| **2nd Order (Branch A)** | GOES steel producers face demand surge | Transformers require grain-oriented electrical steel; only 1 US producer | CLF (Cleveland-Cliffs) | LOW -- steel analysts don't cover transformer supply chain |
| **2nd Order (Branch B)** | Data center site selection shifts to grid-available locations | Power availability becomes the binding constraint on where to build | Utilities and land owners near substations | MEDIUM -- emerging awareness |
| **3rd Order (from A)** | GOES becomes a strategic material | Single domestic source + critical infrastructure dependency = national security classification | CLF (policy catalyst), potential new entrants (long timeline) | VERY LOW -- not in any research coverage |
| **3rd Order (from B)** | Secondary transformer market emerges | New transformers have 4-year lead times; refurbished/repurposed transformers command premium pricing | Private market, potentially publicly traded electrical equipment firms | VERY LOW -- niche market |

### What Makes This Example Powerful

1. The 1st order (transformer manufacturers) is consensus and largely priced
2. The 2nd order (GOES steel) is non-consensus because it crosses sector boundaries (industrial -> materials)
3. The 3rd order (GOES as strategic material) requires understanding regulatory dynamics that neither steel analysts nor utility analysts typically cover
4. The causal chain is verifiable at each link (transformers need GOES, GOES has one domestic source, domestic sourcing matters for critical infrastructure)

---

## Causal Chain Validation

Every link in the effects chain must be validated. A broken link invalidates everything downstream.

### Link Validation Template

| Link | From | To | Causal Mechanism | Evidence | Strength |
|------|------|----|------------------|----------|----------|
| Link 1 | Primary Thesis | 1st Order | [Mechanism] | [TAG] | [Strong/Medium/Weak] |
| Link 2 | 1st Order | 2nd Order | [Mechanism] | [TAG] | [Strong/Medium/Weak] |
| Link 3 | 2nd Order | 3rd Order | [Mechanism] | [TAG] | [Strong/Medium/Weak] |

### Validation Questions

For each link, answer:

| Question | Purpose |
|----------|---------|
| Is the causal mechanism direct or indirect? | Direct mechanisms are more reliable |
| Is there a transmission mechanism? (How does effect A cause effect B?) | Without a clear mechanism, the link may be coincidental |
| Are there counter-forces that could absorb the effect? | Substitution, demand destruction, or policy intervention may dampen transmission |
| What is the time lag? | Longer lags increase uncertainty and reduce position urgency |
| Has this causal chain operated before? (Historical analog) | Prior instances increase confidence |
| Is there a quantitative model supporting the link? | Narrative links are weaker than quantified links |

### Chain Strength Assessment

| Weakest Link Strength | Overall Chain Assessment | Action |
|----------------------|--------------------------|--------|
| All Strong | High confidence in full chain | Position across all orders (size by order) |
| Strong to 2nd, Medium at 3rd | Moderate confidence; 3rd order is speculative | Position in 1st and 2nd; watch 3rd |
| Any link Weak | Chain unreliable beyond weak link | Do not position beyond the weak link |
| Multiple links Weak | Chain is speculative | Thesis not actionable until links strengthened |

---

## Position Sizing by Order Distance

The fundamental rule: **position size inversely with order distance.** Higher-order effects have higher uncertainty.

| Order | Position Size Guidance | Rationale |
|-------|------------------------|-----------|
| **1st Order** | Full position (if not fully priced) | High conviction, strong evidence, consensus validates direction |
| **2nd Order** | 50-70% of standard position | Emerging awareness, some mispricing, causal chain has one link |
| **3rd Order** | 25-40% of standard position | Non-consensus, meaningful mispricing likely, but two+ causal links |
| **4th Order** | 10-20% of standard position (or watch-only) | Speculative, high alpha if right but low confidence in chain |

### Position Size Adjustment Factors

| Factor | Adjustment |
|--------|------------|
| Causal chain fully quantified (demand model exists) | +10% to position size |
| Analytical parallel supports the thesis (score >= 3.5) | +10% to position size |
| Stress test survival (>= 6 of 8 tests) | +10% to position size |
| Cross-sector effect (analysts don't cover the chain) | +5% (mispricing more likely) |
| Single company exposure (no diversification) | -10% to position size |
| Management quality unknown | -10% to position size |
| Timeline uncertain (> 12 months to realization) | -10% to position size |

---

## Effects Convergence

When multiple independent primary theses produce effects that converge on the same equity, conviction increases significantly.

### Convergence Template

```
### Effects Convergence: [TICKER]

| Source Thesis | Order Distance | Effect on [TICKER] | Evidence |
|---------------|----------------|---------------------|----------|
| [Thesis A] | [2nd/3rd] | [How it benefits TICKER] | [TAG] |
| [Thesis B] | [2nd/3rd] | [How it benefits TICKER] | [TAG] |
| [Thesis C] | [2nd/3rd] | [How it benefits TICKER] | [TAG] |

Convergence Count: [Number of independent theses pointing to same equity]
Independence Verified: [Yes/No -- are the theses truly independent?]
Combined Conviction: [Higher than any single chain alone]
```

**Rule:** If 3+ independent effects chains converge on the same equity, and independence is verified, the combined conviction exceeds the sum of parts. This is a strong Tier 1 signal.

---

## Effects Mapping Process

Step-by-step process for the @Effects_Analyst:

1. **Start with the primary thesis** (from `01_CONTENT_ANALYSIS.md` or `02_BOTTLENECK_MAP.md`)
2. **Identify 1st order effects** -- the obvious, consensus beneficiaries
3. **For each 1st order effect, ask:** "What does this require / cause / constrain?"
4. **Map 2nd order effects** -- the downstream consequences
5. **For each 2nd order effect, repeat:** "What does this require / cause / constrain?"
6. **Map 3rd order effects** -- the further downstream consequences
7. **Validate each link** using the causal chain validation template
8. **Identify equity exposure** at each order
9. **Assess market awareness** at each order
10. **Size position guidance** by order distance

---

## Common Errors in Effects Mapping

| Error | Description | Correction |
|-------|-------------|------------|
| **Skipping orders** | Jumping from 1st to 3rd without establishing the 2nd order link | Map every intermediate step; the chain must be continuous |
| **Assuming transmission** | Asserting a downstream effect without explaining the mechanism | Every link needs a "because" -- the transmission mechanism |
| **Ignoring absorption** | Not considering whether the effect is absorbed before reaching the next order | Ask: "Could substitution, demand destruction, or policy action absorb this effect?" |
| **Treating all branches equally** | Some 2nd order effects are much more likely than others | Score each branch independently; weight by probability |
| **Narrative without numbers** | "This will be big" without quantifying the downstream demand | Quantify using `demand_modeling.md` framework |
| **Order inflation** | Labeling a 1st order effect as 3rd order to make it seem non-consensus | Be honest about market awareness; check analyst coverage |
| **Single-chain dependency** | Entire thesis depends on one fragile causal link | Seek convergence from multiple chains; diversify across orders |

---

## Integration

- **Primary Application:** `07_EFFECTS_MAP.md` (all multi-order effects mapping)
- **Feeds Into:** `05_EQUITY_CANDIDATES.md` (2nd and 3rd order effects generate new candidates), `06_TIER_CLASSIFICATION.md` (convergence elevates tier)
- **Cross-Reference:** `demand_modeling.md` (quantify each order's demand impact), `sequential_bottleneck.md` (bottleneck sequence is itself a multi-order chain)
- **Challenge Required:** @Screen_Pessimist must challenge the weakest link in every chain in `.ist/PESSIMIST_REVIEW.md`

---

*First-order effects are priced. Second-order effects are emerging. Third-order effects are where the edge lives. But every link must hold.*
