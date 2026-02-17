# Sequential Blockage Hierarchy

> **Classification:** TEMPORAL CONSTRAINT MAPPING FRAMEWORK
> **Applied To:** Bottleneck identification and rotation strategy
> **Version:** 1.0
> **Framework Owner:** @Bottleneck_Mapper

---

## Core Principle

**Constraints form a chain -- energy first, then grid (transformers), then chips. This creates a rotation strategy, not a static portfolio.**

Bottlenecks are not a flat list of "things that are scarce." They bind in sequence. Phase 1 constraints must partially resolve before Phase 2 constraints become the binding limit. Understanding the sequence is the difference between a static allocation and a dynamic rotation strategy that captures alpha at each phase transition.

The key insight: **investing in the Phase 3 bottleneck during Phase 1 means capital is deployed too early, suffering dead money risk.** Investing in Phase 1 during Phase 3 means the opportunity has passed.

**Uncomfortable truth:** Investing in the Phase 3 bottleneck during Phase 1 is not "being early" -- it is being wrong with a consolation prize of eventually being right. Capital has a time cost. Dead money is not a neutral outcome; it is an opportunity cost measured against what Phase 1 positions would have returned.

---

## Phase Framework Template

Each bottleneck must be assigned to a phase with explicit temporal markers, quantitative anchors, and rotation triggers.

### Phase Structure

```
┌──────────────────────────────────────────────────────────┐
│ Phase 1 (Now - [X] months)                               │
│ BINDING CONSTRAINT: [Name]                               │
│ Quantitative Anchor: [Specific metric defining binding]  │
│ Evidence: [SOURCE tag]                                   │
│ Resolution Pathway: [How this constraint eases]          │
│ Rotation Trigger: [Event signaling Phase 2 transition]   │
├──────────────────────────────────────────────────────────┤
│ Phase 2 ([X] - [Y] months)                               │
│ BINDING CONSTRAINT: [Name]                               │
│ Why Not Binding Now: [Blocked by Phase 1]                │
│ Quantitative Anchor: [Specific metric]                   │
│ Evidence: [SOURCE tag]                                   │
│ Resolution Pathway: [How this constraint eases]          │
│ Rotation Trigger: [Event signaling Phase 3 transition]   │
├──────────────────────────────────────────────────────────┤
│ Phase 3 ([Y]+ months)                                    │
│ BINDING CONSTRAINT: [Name]                               │
│ Why Not Binding Now: [Gated by Phase 1 and/or 2]        │
│ Quantitative Anchor: [Specific metric]                   │
│ Evidence: [SOURCE tag]                                   │
│ Resolution Pathway: [How this constraint eases, if ever] │
├──────────────────────────────────────────────────────────┤
│ CROSS-CUTTING CONSTRAINTS                                │
│ [Constraints that persist across all phases]             │
│ These do NOT rotate -- they are permanent portfolio      │
│ positions until structural resolution occurs.            │
└──────────────────────────────────────────────────────────┘
```

### Phase Assignment Template

| Field | Requirement | Example |
|-------|-------------|---------|
| **Phase Number** | Sequential integer (1, 2, 3...) | Phase 1 |
| **Binding Constraint** | Specific, named constraint | Power generation capacity |
| **Time Horizon** | Explicit start/end in months from analysis date | Now - 18 months |
| **Quantitative Anchor** | Measurable metric proving constraint is binding | Grid interconnection queue: 2,600 GW vs. 1,250 GW installed |
| **Evidence Tag** | Source citation per IST tagging standards | [SOURCE: DOE Interconnection Report 2024] |
| **Sequential Dependency** | Why this constraint binds *after* the previous one | "Power generation only becomes binding once transformer supply allows grid connection" |
| **Rotation Trigger** | Observable event or metric threshold | Transformer lead times drop below 24 months |

---

## Temporal Marker Requirements

**Every bottleneck needs an explicit time horizon.** Undated bottlenecks are analytically useless.

| Marker Type | Format | Purpose |
|-------------|--------|---------|
| **Absolute Date** | "By Q3 2026" | Hard deadlines (policy, contract, commissioning) |
| **Relative Duration** | "12-18 months from now" | Estimated resolution timelines |
| **Conditional** | "When [X] occurs" | Event-driven phase transitions |
| **Quantitative Threshold** | "When utilization exceeds 85%" | Metric-driven binding points |

### Time Horizon Confidence Levels

| Confidence | Definition | Implication |
|------------|------------|-------------|
| **High** | Based on physical construction timelines, signed contracts, or regulatory deadlines | Can size positions accordingly |
| **Medium** | Based on industry estimates, historical analogs, or supply chain forecasts | Position with wider bands |
| **Low** | Based on analyst estimates, management guidance, or extrapolation | Treat as directional only, reduce position size |

---

## Rotation Trigger Identification

The most valuable output of this framework is identifying **when to rotate** -- not just what to hold.

### Trigger Categories

| Trigger Type | Description | Example |
|--------------|-------------|---------|
| **Lead Time Compression** | Lead times for the Phase N constraint begin shortening | Transformer lead times drop from 4 years to 2 years |
| **Capacity Announcement** | Major new supply announced for Phase N constraint | New fab groundbreaking, new power plant commissioning |
| **Pricing Reversal** | Pricing power in Phase N weakens, pricing power in Phase N+1 strengthens | Transformer spot premiums decline while copper premiums rise |
| **Utilization Threshold** | Phase N capacity utilization drops below critical level | Grid utilization drops below 90% in key markets |
| **Policy Catalyst** | Government action accelerates Phase N resolution | Fast-track permitting for transmission lines |
| **Earnings Signal** | Phase N companies guide down while Phase N+1 companies guide up | Utility capex guidance shifts from generation to transmission |

### Rotation Signal Monitoring Template

```
Current Phase: [N]
Monitoring For: Phase [N] -> Phase [N+1] Transition

| Signal | Current Value | Trigger Threshold | Status |
|--------|---------------|-------------------|--------|
| [Signal 1] | [Value] | [Threshold] | [Green/Yellow/Red] |
| [Signal 2] | [Value] | [Threshold] | [Green/Yellow/Red] |
| [Signal 3] | [Value] | [Threshold] | [Green/Yellow/Red] |

Rotation Readiness: [Not Yet / Approaching / Triggered]
Recommended Action: [Hold Phase N / Begin Rotating / Fully Rotate]
```

---

## Portfolio Allocation by Phase

Phase assignment drives allocation weight. The binding constraint commands the largest allocation.

| Phase | Allocation Weight | Rationale |
|-------|-------------------|-----------|
| **Phase 1 (Current Binding)** | 40-50% of thematic allocation | Maximum urgency, pricing power now |
| **Phase 2 (Next Binding)** | 25-35% of thematic allocation | Building position ahead of transition |
| **Phase 3 (Future Binding)** | 10-20% of thematic allocation | Early positioning, higher uncertainty |
| **Cross-Cutting** | 10-15% of thematic allocation | Persistent positions, lower volatility |

### Allocation Adjustment Rules

| Event | Adjustment |
|-------|------------|
| Rotation trigger fires for Phase N | Reduce Phase N by 15-20%, add to Phase N+1 |
| New constraint identified | Re-sequence entire hierarchy, redistribute |
| Phase N resolves faster than expected | Accelerate rotation, increase Phase N+1 weight |
| Phase N resolves slower than expected | Maintain Phase N weight, reduce Phase N+1 temporarily |
| Cross-cutting constraint intensifies | Increase cross-cutting allocation from other phases |

---

## Validation Checklist

Before accepting a sequential bottleneck map, validate each element:

| Check | Question | Pass/Fail |
|-------|----------|-----------|
| **Causal Dependency** | Is the sequence causal or merely coincidental? Can Phase 2 bind independently of Phase 1? | |
| **Sequential Evidence** | Is there evidence that Phase 2 constraint is currently *not* binding because Phase 1 blocks it? | |
| **Temporal Realism** | Are the time horizons realistic given physical/regulatory constraints? | |
| **Quantitative Grounding** | Does each phase have a measurable anchor, not just a narrative? | |
| **Rotation Clarity** | Is the rotation trigger observable and unambiguous? | |
| **Completeness** | Are there constraints missing from the sequence? Cross-cutting constraints identified? | |
| **Falsifiability** | What evidence would invalidate this sequence? Is that evidence being monitored? | |
| **Historical Analog** | Has a similar sequential pattern occurred before? What was the outcome? | |

---

## Cascade Mapping Notation

For visual clarity, use cascade notation when mapping sequences:

```
[Phase 1: ENERGY] ──resolves──> [Phase 2: GRID/TRANSFORMERS] ──resolves──> [Phase 3: CHIPS/COMPUTE]
       │                                    │                                       │
       ▼                                    ▼                                       ▼
  Equities: [TICKER]                  Equities: [TICKER]                    Equities: [TICKER]
  Binding: [Metric]                   Binding: [Metric]                     Binding: [Metric]
  Timeline: [X months]               Timeline: [Y months]                  Timeline: [Z months]

Cross-Cutting: [CONSTRAINT] ──────────────────────────────────────────────────────────────────
                                    Equities: [TICKER]
                                    Duration: [Structural / Until X]
```

---

## Common Errors

| Error | Why It's Wrong | Correction |
|-------|---------------|------------|
| Treating all bottlenecks as simultaneous | Ignores sequential dependency; leads to over-diversification | Map the causal chain, weight by phase |
| No rotation triggers defined | Creates static portfolio that misses phase transitions | Every phase needs explicit exit criteria |
| Undated phases | "Eventually" is not an investment thesis | Assign time horizons with confidence levels |
| Ignoring cross-cutting constraints | Some constraints persist regardless of phase; missing them creates blind spots | Always include cross-cutting category |
| Confusing supply expansion with constraint resolution | New supply announced != constraint resolved (lead times matter) | Track actual capacity online, not announcements |

---

## Integration

- **Primary Application:** `02_BOTTLENECK_MAP.md` (bottleneck identification and sequencing)
- **Secondary Application:** `09_ROTATION_STRATEGY.md` (rotation triggers and timing)
- **Feeds Into:** `05_EQUITY_CANDIDATES.md` (phase assignment determines candidate priority)
- **Cross-Reference:** `scarcity_abundance.md` (scarcity is phase-dependent), `demand_modeling.md` (demand validates binding status)
- **Override Authority:** @Screen_Synthesizer may re-sequence phases with documented evidence

---

*Bottlenecks bind in sequence. The portfolio must rotate with the sequence, not against it.*
