# IST Synthesis — Fix Plan

**Date:** 2026-02-22
**Author:** Claude Code (CC)
**Source:** Root cause analysis of live synthesis run (workflow 12) + four-layer compliance review
**Scope:** 8 fixes to make the synthesis feature produce real analytical output

---

## Problem Summary

A live synthesis combining two completed IST screens (AI Agents + Jordi Video) completed in **149ms** — proving that **zero Claude API calls** were made. The output is:

- **Report tab:** Raw markdown table with "No cross-screen adjustment" for every equity
- **Dialectic tab:** 404 error — no SYNTHESIS-side dialectic row exists
- **HFRT Handoff tab:** Raw JSON dump (`JSON.stringify`)
- **Tier Changes tab:** Empty — no tiers changed because the heuristic cannot produce `contradicting` classifications
- **Thesis Interactions tab:** Generic "Theme overlap and tier alignment analysis" rationale for every pair

Every synthesis step is a stub that uses hardcoded strings or count tables instead of calling Claude.

---

## How to Use This Document

Each fix is numbered (F1–F8). Apply in order — F1–F5 are backend service changes (the core AI integration), F6–F8 are frontend rendering fixes.

**Reference pattern:** The existing IST services (`content_extraction.py`, `thematic_analysis.py`, `equity_identification.py`, `dialectic.py`, `final_synthesis.py`) all follow this pattern for Claude calls:

```python
from app.services.claude_client import call_claude, call_claude_raw

# Structured output:
result = await call_claude(
    system_prompt=SYSTEM_PROMPT,
    user_prompt=user_prompt,
    response_model=PydanticModel,
)

# Raw markdown output (returns str):
result = await call_claude_raw(
    system_prompt=SYSTEM_PROMPT,
    user_prompt=user_prompt,
)
```

All Claude calls MUST use XML tags for content/instruction separation (INV-AI-01).

---

## F1 — Implement Claude-powered `thesis_interactions`

**Priority:** CRITICAL
**File:** `backend/app/services/ist/synthesis.py`, lines 157–204
**Current behavior:** Word-overlap heuristic. Can never produce `contradicting`. Every pair gets "Theme overlap and tier alignment analysis" as rationale.

**Fix:** Replace the heuristic with a Claude call that analyzes each screen pair.

Add a Pydantic response model:

```python
class ThesisInteractionResult(BaseModel):
    """Claude output for thesis interaction analysis."""
    classification: str = Field(description="One of: reinforcing, contradicting, orthogonal")
    rationale: str = Field(description="2-3 sentence explanation of why these theses interact this way")
    impact: str = Field(description="How this interaction affects investment positioning")
```

Replace the inner loop body (lines 176–192) with:

```python
# Batch preload all screens referenced by sources to avoid N+1 queries
screen_ids_set = {s.screen_id for s in sources}
screens_list = db.query(ISTScreen).filter(ISTScreen.id.in_(screen_ids_set)).all()
screen_map = {s.id: s for s in screens_list}

n = len(sources)
total_pairs = max(1, n * (n - 1) // 2)
pair_idx = 0

for i in range(n):
    for j in range(i + 1, n):
        a = sources[i]
        b = sources[j]

        # Look up from pre-fetched map (no per-pair DB query)
        screen_a = screen_map.get(a.screen_id)
        screen_b = screen_map.get(b.screen_id)

        a_extraction = _load_json(screen_a.content_extraction, {}) if screen_a else {}
        b_extraction = _load_json(screen_b.content_extraction, {}) if screen_b else {}
        a_brief = _load_json(screen_a.screening_brief, {}) if screen_a else {}
        b_brief = _load_json(screen_b.screening_brief, {}) if screen_b else {}

        user_prompt = (
            f"<screen_a>\n"
            f"Name: {a.screen_name}\n"
            f"Primary Theme: {a.primary_theme or 'Not specified'}\n"
            f"Hypothesis: {a_brief.get('hypothesis', 'N/A')}\n"
            f"Key Themes: {json.dumps(a_extraction.get('themes', []))}\n"
            f"Tier 1 Count: {a.tier1_count}, Tier 2: {a.tier2_count}, Tier 3: {a.tier3_count}\n"
            f"</screen_a>\n\n"
            f"<screen_b>\n"
            f"Name: {b.screen_name}\n"
            f"Primary Theme: {b.primary_theme or 'Not specified'}\n"
            f"Hypothesis: {b_brief.get('hypothesis', 'N/A')}\n"
            f"Key Themes: {json.dumps(b_extraction.get('themes', []))}\n"
            f"Tier 1 Count: {b.tier1_count}, Tier 2: {b.tier2_count}, Tier 3: {b.tier3_count}\n"
            f"</screen_b>\n\n"
            f"Analyze how the investment thesis of Screen A interacts with Screen B.\n"
            f"Classify the relationship as exactly one of: reinforcing, contradicting, orthogonal.\n"
            f"- reinforcing: theses amplify each other's conviction or share beneficiaries\n"
            f"- contradicting: theses undermine each other or create opposing market bets\n"
            f"- orthogonal: theses are independent with no meaningful interaction\n\n"
            f"Return JSON matching: {ThesisInteractionResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt="You are an investment analyst comparing two screening theses. Be precise and cite specific themes.",
            user_prompt=user_prompt,
            response_model=ThesisInteractionResult,
        )

        interactions.append({
            "screenA": {"id": a.screen_id, "name": a.screen_name, "theme": a.primary_theme},
            "screenB": {"id": b.screen_id, "name": b.screen_name, "theme": b.primary_theme},
            "classification": result.classification,
            "rationale": result.rationale,
            "impact": result.impact,
        })

        pair_idx += 1
        await emit_sse_event(workflow_run_id, "step_progress", {
            "stepName": "thesis_interactions",
            "message": f"Analyzed {a.screen_name} × {b.screen_name}: {result.classification}",
            "percent": int((pair_idx / total_pairs) * 100),
        })
```

Add import at top of file:
```python
from app.services.claude_client import call_claude, call_claude_raw
```

**Depends on:** Nothing

---

## F2 — Implement Claude-powered `combined_bottleneck_analysis` and `cross_screen_effects`

**Priority:** CRITICAL
**File:** `backend/app/services/ist/synthesis.py`, lines 232–298
**Current behavior:** `combined_bottleneck_analysis` counts bottlenecks by phase. `cross_screen_effects` counts reinforcing pairs. Neither calls Claude.

**Fix — `combined_bottleneck_analysis` (lines 232–270):**

Add a Pydantic model:

```python
class CombinedBottleneckResult(BaseModel):
    """Claude output for combined bottleneck cascade analysis."""
    unified_cascade: list[dict] = Field(description="Ordered list of bottleneck phases with cross-screen dependencies")
    emergent_bottlenecks: list[str] = Field(description="New bottleneck dependencies that only emerge from combining screens")
    temporal_sequence: str = Field(description="How bottlenecks across screens interact temporally")
    summary: str = Field(description="2-3 paragraph analysis of the combined bottleneck landscape")
```

After loading bottlenecks (line 251), batch preload screens, then build a detailed prompt with all bottleneck names, phases, demand models, and screen associations. Call Claude:

```python
# Batch preload screens for all bottlenecks to avoid N+1
bn_screen_ids = {b.screen_id for b in bottlenecks if b.screen_id}
bn_screens = db.query(ISTScreen).filter(ISTScreen.id.in_(bn_screen_ids)).all()
bn_screen_map = {s.id: s for s in bn_screens}

bottleneck_data = []
for b in bottlenecks:
    screen = bn_screen_map.get(b.screen_id)
    bottleneck_data.append({
        "name": b.name,
        "phase": b.phase,
        "screenName": screen.name if screen else "Unknown",
        "severity": _load_json(b.severity, None),
    })

user_prompt = (
    f"<bottlenecks>\n{json.dumps(bottleneck_data, indent=2)}\n</bottlenecks>\n\n"
    f"<thesis_interactions>\n{synthesis.thesis_interactions or '[]'}\n</thesis_interactions>\n\n"
    f"Build a unified bottleneck cascade from these {len(bottlenecks)} bottlenecks across {len(screen_ids)} screens.\n"
    f"Identify NEW bottleneck dependencies that only emerge from the combination.\n"
    f"Map the temporal sequence of how bottlenecks across different screens interact.\n\n"
    f"Return JSON matching: {CombinedBottleneckResult.model_json_schema()}"
)

result = await call_claude(
    system_prompt="You are an investment analyst building unified bottleneck cascade models from multiple screening theses.",
    user_prompt=user_prompt,
    response_model=CombinedBottleneckResult,
)

combined = {
    "sourceScreenCount": len(screen_ids),
    "bottleneckCount": len(bottlenecks),
    "unifiedCascade": result.unified_cascade,
    "emergentBottlenecks": result.emergent_bottlenecks,
    "temporalSequence": result.temporal_sequence,
    "summary": result.summary,
}
```

**Fix — `cross_screen_effects` (lines 273–298):**

Add a Pydantic model:

```python
class CrossScreenEffectsResult(BaseModel):
    """Claude output for cross-screen effects chain analysis."""
    effects_chains: list[dict] = Field(description="Cross-screen effects where Screen A's Nth-order effect feeds Screen B")
    feedback_loops: list[str] = Field(description="Identified feedback loops between screens")
    summary: str = Field(description="2-3 paragraph analysis of cross-screen effects")
```

Load the overlap matrix, thesis interactions, and combined bottleneck data. Build a prompt asking Claude to map cross-screen effects chains (where Screen A's 3rd-order effect feeds into Screen B's 1st-order). Call Claude and store the result in `combined_brief`.

**Depends on:** Nothing

---

## F3 — Implement Claude-powered `re_tiering`

**Priority:** CRITICAL
**File:** `backend/app/services/ist/synthesis.py`, lines 301–381
**Current behavior:** Purely heuristic. Only upgrades if `len(appearances) >= 2 AND has_reinforcing`. Only downgrades if `has_contradicting` (which is impossible without F1). Every ticker gets "No cross-screen adjustment."

**Fix:** Replace the tier adjustment logic with a Claude call that evaluates each multi-screen ticker (or tickers affected by thesis interactions) using the full analytical context.

Add a Pydantic model:

```python
class TierReassessment(BaseModel):
    """Claude's tier reassessment for a single equity."""
    ticker: str
    original_tier: int
    new_tier: int
    rationale: str = Field(description="Why the tier was changed or maintained, citing cross-screen evidence")
    conviction: str = Field(description="HIGH, MEDIUM, or LOW")
    combined_thesis: str = Field(description="How the combined screens affect the investment case for this equity")
```

class TierReassessmentBatch(BaseModel):
    """Claude's reassessment for all equities."""
    assessments: list[TierReassessment]
```

Build a prompt containing:
- The full overlap matrix (which tickers appear in which screens at which tiers)
- The thesis interactions (reinforcing/contradicting/orthogonal with rationales from F1)
- The combined bottleneck analysis (from F2)
- The cross-screen effects (from F2)

Ask Claude to reassess each ticker's tier, specifically looking for:
- Multi-screen tickers where reinforcing theses should upgrade the tier
- Tickers exposed to contradicting theses that should downgrade
- Single-screen tickers that gain or lose conviction from cross-screen effects

The response replaces the current heuristic loop.

**Depends on:** F1, F2 (needs real thesis interaction and bottleneck data)

---

## F4 — Implement Claude-powered dialectic (optimist, pessimist) + create SYNTHESIS row

**Priority:** CRITICAL
**File:** `backend/app/services/ist/synthesis.py`, lines 384–446 (optimist), lines 417–446 (pessimist), lines 449–513 (final)
**Current behavior:**
- Optimist: hardcoded string *"thesis interactions reinforce upside optionality"*
- Pessimist: hardcoded string *"cross-screen coupling introduces fragility"*
- Final: markdown table from DB, no Claude. No SYNTHESIS dialectic row created (causes 404).

**Fix — `synthesis_dialectic_optimist` (lines 384–414):**

Build a comprehensive data package with overlap matrix, thesis interactions, tier changes, combined bottleneck analysis, and cross-screen effects. Call Claude with a system prompt instructing it to build the optimist case for the combined thesis:

```python
data_package = {
    "overlapMatrix": _load_json(synthesis.overlap_matrix, []),
    "thesisInteractions": _load_json(synthesis.thesis_interactions, []),
    "tierChanges": _load_json(synthesis.tier_changes, []),
    "combinedBottlenecks": _load_json(synthesis.combined_brief, {}),
}

user_prompt = (
    f"<synthesis_data>\n{json.dumps(data_package, indent=2)}\n</synthesis_data>\n\n"
    f"Build the OPTIMIST case for the combined investment thesis '{synthesis.name}'.\n"
    f"Focus on: cross-screen reinforcement, emergent opportunities, amplified conviction.\n"
    f"Structure as: narrative (3-5 paragraphs) and key_points (5-8 bullet points).\n\n"
    f"Return JSON matching: {_DialecticPayload.model_json_schema()}"
)

result = await call_claude(
    system_prompt="You are an optimistic investment analyst synthesizing multiple screening theses to build the strongest possible bull case.",
    user_prompt=user_prompt,
    response_model=_DialecticPayload,
)
```

**Fix — `synthesis_dialectic_pessimist` (lines 417–446):** Same pattern but with pessimist system prompt focusing on: concentration risk, thesis contradictions, timing fragility, execution sequencing risk.

**Fix — `synthesis_final` (lines 449–513):**

1. Call `call_claude_raw` to generate a comprehensive markdown report (matching the `handle_report_generation` pattern in `final_synthesis.py`). The prompt should include the full data package plus both dialectic narratives:

```python
optimist = db.query(ISTSynthesisDialectic).filter(
    ISTSynthesisDialectic.synthesis_id == synthesis.id,
    ISTSynthesisDialectic.side == "OPTIMIST",
).first()

pessimist = db.query(ISTSynthesisDialectic).filter(
    ISTSynthesisDialectic.synthesis_id == synthesis.id,
    ISTSynthesisDialectic.side == "PESSIMIST",
).first()

report_prompt = (
    # ... full data package + dialectic content ...
    f"Write a comprehensive Combined Investment Thesis Report in markdown.\n"
    f"Include: Executive Summary, Cross-Screen Analysis, Tier Reassessment Rationale, "
    f"Risk Assessment, Recommended Actions, HFRT Research Priorities.\n"
)

report = await call_claude_raw(
    system_prompt="You are a senior investment analyst writing the definitive cross-screen synthesis report.",
    user_prompt=report_prompt,
)

synthesis.combined_report = report
```

2. **Create a SYNTHESIS dialectic row** so the frontend `dialectic/SYNTHESIS` endpoint doesn't 404:

```python
# After generating the report, create a SYNTHESIS dialectic combining both views
synthesis_prompt = (
    f"<optimist>\n{optimist.content if optimist else '{}'}\n</optimist>\n"
    f"<pessimist>\n{pessimist.content if pessimist else '{}'}\n</pessimist>\n\n"
    f"Synthesize the optimist and pessimist views into a balanced assessment.\n"
    f"Return JSON matching: {_DialecticPayload.model_json_schema()}"
)

synthesis_dialectic = await call_claude(
    system_prompt="You are a balanced investment analyst reconciling bull and bear cases.",
    user_prompt=synthesis_prompt,
    response_model=_DialecticPayload,
)

db.add(ISTSynthesisDialectic(
    synthesis_id=synthesis.id,
    side="SYNTHESIS",
    content=synthesis_dialectic.model_dump_json(),
))
```

**Depends on:** F1, F2, F3 (needs real data from all prior steps)

---

## F5 — Fix N+1 Query in `handle_overlap_matrix`

**Priority:** HIGH
**File:** `backend/app/services/ist/synthesis.py`, lines 132–134
**Current behavior:** Per-candidate DB query for bottleneck name inside the loop.

**Fix:** Batch pre-fetch all bottleneck IDs before the loop:

```python
# Before the candidate loop (after line 117):
all_bn_ids = {c.bottleneck_id for c in candidates if c.bottleneck_id}
bn_map = {}
if all_bn_ids:
    bns = db.query(ISTBottleneck).filter(ISTBottleneck.id.in_(all_bn_ids)).all()
    bn_map = {bn.id: bn.name for bn in bns}

# Replace lines 132-134 with:
bottleneck_name = bn_map.get(cand.bottleneck_id) if cand.bottleneck_id else None
```

**Depends on:** Nothing

---

## F6 — Refine `SynthesisReport.tsx` Metadata Display

**Priority:** REFINEMENT
**File:** `frontend/components/ist/synthesis/SynthesisReport.tsx` (30 lines)
**Current behavior:** Markdown body already renders correctly via `ReactMarkdown` + `remarkGfm` (Codex implemented this). However, the metadata block still uses raw `JSON.stringify` in a `<pre>` tag, which is inconsistent with the polished report body.

**Fix:** Replace the metadata `<pre>` block (lines 18–22) with structured display. Keep the existing `ReactMarkdown` rendering for the report body:

```tsx
{metadata && (
  <div className="flex items-center gap-3 text-xs text-text-secondary">
    {metadata.equityCount != null && <span>{String(metadata.equityCount)} equities analyzed</span>}
    {metadata.tierBreakdown && (
      <span>
        T1: {String((metadata.tierBreakdown as Record<string, number>).tier1 ?? 0)} ·
        T2: {String((metadata.tierBreakdown as Record<string, number>).tier2 ?? 0)} ·
        T3: {String((metadata.tierBreakdown as Record<string, number>).tier3 ?? 0)}
      </span>
    )}
  </div>
)}
```

**Note:** Do NOT replace the `ReactMarkdown` rendering — it is already correct. Only change the metadata section above it.

**Depends on:** Nothing

---

## F7 — Fix `SynthesisHandoff.tsx` Raw JSON

**Priority:** HIGH
**File:** `frontend/components/ist/synthesis/SynthesisHandoff.tsx` (18 lines)
**Current behavior:** `JSON.stringify(handoff, null, 2)` in a `<pre>` tag.

**Fix:** Replace with a structured card layout matching the existing `HandoffPanel.tsx` pattern:

```tsx
"use client";

interface HandoffCandidate {
  ticker: string;
  companyName: string;
  tier: number;
  conviction: string;
  sourceScreenCount: number;
}

interface SynthesisHandoffProps {
  handoff: Record<string, unknown> | null;
}

export default function SynthesisHandoff({ handoff }: SynthesisHandoffProps) {
  if (!handoff) {
    return <p className="text-sm text-text-secondary">HFRT handoff not generated yet.</p>;
  }

  const candidates = (handoff.tier1Candidates || []) as HandoffCandidate[];
  const tier1Count = (handoff.tier1Count as number) || 0;

  if (!candidates.length) {
    return <p className="text-sm text-text-secondary">No Tier 1 candidates for HFRT handoff.</p>;
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-text-secondary">
        {tier1Count} Tier 1 candidate{tier1Count !== 1 ? "s" : ""} ready for HFRT research
      </p>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left text-sm">
          <thead className="bg-white/5">
            <tr>
              <th className="px-3 py-2">Ticker</th>
              <th className="px-3 py-2">Company</th>
              <th className="px-3 py-2">Conviction</th>
              <th className="px-3 py-2">Sources</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c) => (
              <tr key={c.ticker} className="border-t border-border">
                <td className="px-3 py-2 font-mono font-medium text-primary">{c.ticker}</td>
                <td className="px-3 py-2 text-text-primary">{c.companyName}</td>
                <td className="px-3 py-2">
                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                    c.conviction === "HIGH" ? "bg-green-500/20 text-green-400" :
                    c.conviction === "MEDIUM" ? "bg-yellow-500/20 text-yellow-400" :
                    "bg-red-500/20 text-red-400"
                  }`}>
                    {c.conviction}
                  </span>
                </td>
                <td className="px-3 py-2 text-text-secondary">{c.sourceScreenCount} screen{c.sourceScreenCount !== 1 ? "s" : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

**Note:** Tab labels (`TAB_LABELS` map + `{TAB_LABELS[t]}` usage) are already implemented in `frontend/app/screens/syntheses/[id]/page.tsx` (lines 33–41, 214). No action needed.

**Depends on:** Nothing

---

## F8 — Fix Dialectic Tab Raw JSON Rendering

**Priority:** HIGH
**File:** `frontend/app/screens/syntheses/[id]/page.tsx`, lines 250–252
**Current behavior:** The dialectic tab renders `JSON.stringify(dialecticContent, null, 2)` in a `<pre>` block. Even after F4 creates the SYNTHESIS row, users will see raw JSON like `{"narrative": "...", "key_points": [...]}` instead of formatted content.

**Fix:** Replace the dialectic `<pre>` block (lines 250–252) with a structured renderer that parses the dialectic payload and displays narrative + key points:

```tsx
{tab === "dialectic" && (
  <div className="space-y-3">
    <div className="flex items-center gap-2">
      {(["OPTIMIST", "PESSIMIST", "SYNTHESIS"] as const).map((side) => (
        <button
          key={side}
          onClick={() => setDialecticSide(side)}
          className={cn(
            "px-3 py-1.5 text-xs rounded-full",
            dialecticSide === side ? "bg-primary/20 text-primary" : "bg-white/10 text-text-secondary"
          )}
        >
          {side}
        </button>
      ))}
    </div>
    {dialecticContent ? (
      <div className="space-y-4">
        {(dialecticContent as Record<string, unknown>).narrative && (
          <MarkdownNarrative content={String((dialecticContent as Record<string, unknown>).narrative)} />
        )}
        {Array.isArray((dialecticContent as Record<string, unknown>).key_points) && (
          <div className="space-y-1.5">
            <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wide">Key Points</h4>
            <ul className="space-y-1 text-sm text-text-primary">
              {((dialecticContent as Record<string, unknown>).key_points as string[]).map((pt, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-primary mt-0.5">-</span>
                  <span>{pt}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    ) : (
      <p className="text-sm text-text-secondary">No dialectic content available for this side.</p>
    )}
  </div>
)}
```

This requires importing `MarkdownNarrative` at the top of the file:
```typescript
import MarkdownNarrative from "@/components/MarkdownNarrative";
```

**Note:** The dialectic payload shape (`{ narrative: string, key_points: string[] }`) is defined by `_DialecticPayload` in the backend (F4). If the payload shape differs, adjust field names accordingly.

**Depends on:** F4 (needs SYNTHESIS dialectic row to exist)

---

## Dependency Graph

```
F1 ──→ F3
F2 ──→ F3
F1 + F2 + F3 ──→ F4
F4 ──→ F8 (dialectic rendering needs SYNTHESIS row from F4)

F5, F6, F7 are independent of everything.
```

**Recommended execution order:**

```
Batch 1 (parallel):  F1, F2, F5, F6, F7
Batch 2 (after F1+F2): F3
Batch 3 (after F3):    F4, F8
```

---

## Verification

After all fixes are applied:

1. **Delete existing syntheses** so they can be re-run with real Claude calls. Use the UI or API to delete all syntheses for the target screens. Do NOT assume ID=1 — query the list first:
```bash
# List existing syntheses to find the right ID:
curl http://127.0.0.1:8000/api/ist/syntheses/
# Then delete the relevant one:
curl -X DELETE http://127.0.0.1:8000/api/ist/syntheses/<ID>
```

2. **Create a new synthesis** from the UI (select 2+ completed screens)

3. **Verify in the backend logs:**
   - `httpx: HTTP Request: POST https://api.anthropic.com/v1/messages` appears for steps: `thesis_interactions`, `combined_bottleneck_analysis`, `cross_screen_effects`, `re_tiering`, `synthesis_dialectic_optimist`, `synthesis_dialectic_pessimist`, `synthesis_final`
   - `Claude API tokens` cumulative count increases substantially (expect 50K–150K tokens total)
   - Completion time is measured in minutes, not milliseconds

4. **Verify in the frontend:**
   - **Report tab:** Rendered markdown with proper headers, paragraphs, and styled tables (not raw `#` and `|`). Metadata shows structured counts (not raw JSON).
   - **Thesis Interactions tab:** Each pair shows a substantive rationale (not "Theme overlap and tier alignment analysis")
   - **Tier Changes tab:** At least some tickers show tier adjustments with cited cross-screen evidence
   - **Dialectic tab:** SYNTHESIS view loads without 404. Displays narrative paragraphs + key points list (not raw JSON in a `<pre>` block). OPTIMIST and PESSIMIST sides also render as formatted content.
   - **HFRT Handoff tab:** Structured table with ticker, company, conviction, source count (not raw JSON)
   - **Tab labels:** Already verified as working ("Overlap Matrix", "Thesis Interactions", etc.)

5. **Run backend tests:**
```bash
# From the backend directory, activate venv appropriate to your shell:
# Bash: source venv/Scripts/activate
# PowerShell: .\venv\Scripts\Activate.ps1
pytest tests/integration/test_ist_extension_endpoints.py -q
pytest tests/integration/test_final_synthesis_endpoints.py -q
```

6. **New test coverage required for F1–F4:**
   Add or extend integration tests that verify:
   - `POST /api/ist/syntheses/` creates a synthesis and triggers the workflow
   - After workflow completion, `GET /api/ist/syntheses/<id>` returns non-empty `thesisInteractions`, `combinedBrief`, `tierChanges`, and `combinedReport` fields
   - `GET /api/ist/syntheses/<id>/dialectic/SYNTHESIS` returns 200 (not 404) with `content` containing `narrative` and `key_points`
   - `GET /api/ist/syntheses/<id>/equities` returns equities where at least one has a non-generic `crossScreenRationale` (not "No cross-screen adjustment")
   - Output payload shapes match the Pydantic models defined in F1–F3

---

## CC Resolution of CX Review Comments

Date: 2026-02-22
Reviewer: Claude Code (CC)
Scope: Resolution of all 7 Codex review findings

| # | Finding | Severity | Verdict | Action Taken |
|---|---------|----------|---------|-------------|
| 1 | `call_claude_raw` signature mismatch | HIGH | **Valid** | Removed `workflow_run_id` from reference pattern (line 44) and F4 snippet |
| 2 | Verification under-scoped | HIGH | **Valid** | Expanded verification section with test coverage requirements for F1-F4 output shapes, SYNTHESIS row creation, and payload contracts |
| 3 | N+1 queries in F1/F2 | MEDIUM | **Valid** | Added batch preload pattern to both F1 (screen_map) and F2 (bn_screen_map) |
| 4 | Progress math incorrect | MEDIUM | **Valid** | Fixed denominator from `len(sources) ** 2` to `n * (n - 1) // 2` with `pair_idx` counter |
| 5 | F6/F7 claims stale | MEDIUM | **Partially valid** | F6 reclassified from CRITICAL to REFINEMENT (markdown rendering already works via `ReactMarkdown`; only metadata display needs fixing). Tab labels confirmed already implemented — removed from F7 scope. Handoff raw JSON confirmed still present — kept in F7. |
| 6 | Dialectic rendering UX gap | MEDIUM | **Valid** | Added new F8 — dialectic tab narrative + key points rendering using `MarkdownNarrative` |
| 7 | Verification fragility | LOW | **Valid** | Replaced hardcoded `syntheses/1` with query-first approach; noted both bash and PowerShell venv activation |
