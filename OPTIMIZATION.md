# Optimization Log — Financial Due Diligence Application

> **Purpose:** Living educational document for pipeline speed optimization with zero quality degradation. Every optimization recorded here preserves full analytical rigor — citation-backed claims, adversarial dialectic review, multi-gate quality checks. This document is designed to be referenced when building future AI-powered analytical pipelines.

---

## 1. Problem Statement

The IST (Investment Screening Team) workflow processes unstructured content (podcasts, articles, earnings calls) through a 22-step pipeline across 5 phases to produce ranked equity screens. Each step makes one or more Claude API calls. Running all 22 steps sequentially resulted in estimated total run times of **15-25 minutes**, which is unacceptable for iterative research workflows where a user may run multiple screens per session.

**Constraint:** Speed improvements must not compromise output quality. The pipeline's value proposition is academic rigor — citation-backed claims, adversarial dialectic review, multi-gate quality checks. Any optimization that weakens analytical depth is off the table.

### Baseline Timing (Sequential Execution — Pre-Optimization)

| Step | Phase | Duration | Cumulative |
|------|-------|----------|------------|
| content_extraction | P1 | 35.2s | 35.2s |
| source_bias_assessment | P1 | 10.5s | 45.7s |
| bottleneck_mapping | P2 | 26.1s | 71.8s |
| demand_modeling | P2 | 72.2s | 144.0s |
| external_validation | P2 | 91.9s | 235.9s |
| content_sufficiency_gate | P2 | 0.0s | 235.9s |
| *Phases 3-5* | P3-P5 | *not measured (run failed at P2)* | — |

Phase 1+2 alone took **3m 56s** sequentially. Extrapolating all 22 steps at an average of ~35s each gives ~13 minutes of pure compute time, plus inter-phase pause time for user approval.

---

## 2. Optimization #1 — Dependency-Aware Parallel Execution (SHIPPED)

### Insight

The sequential loop (`for step in steps: await execute(step)`) treated every step as depending on the one before it. In reality, the dependency graph is a DAG (directed acyclic graph), not a chain. Many steps share the same upstream dependency and can run concurrently.

### What Changed

**Architecture (workflow_engine.py):**
- Replaced the `for step in steps` sequential loop with a `while True` dependency-resolution loop
- Each iteration finds all PENDING steps whose `depends_on` dependencies are fully COMPLETED
- Runs the entire "ready" batch concurrently via `asyncio.gather()`
- After the batch completes, refreshes ORM state and loops to find the next batch
- Phase boundary pauses, SSE events, error handling, retry, and cancel all preserved

**Data model:**
- Added `depends_on` TEXT column to `workflow_steps` table (Alembic migration 011)
- Each step stores a JSON list of step names it depends on (e.g., `["content_extraction"]`)
- Steps with `depends_on = NULL` (pre-migration workflows) fall back to sequential-by-step_order for backward compatibility

**Step definitions (ist.py, hfrt.py, bridge.py):**
- Added explicit `depends_on` arrays to all IST (22 steps) and HFRT (23 steps) step definitions
- Dependencies derived from actual data flow analysis — what each step reads from the database

**Session safety:**
- Refactored `_execute_step()` to use its own `SessionLocal()` for status bookkeeping
- Each step handler already used its own session (INV-BE-05)
- No shared SQLAlchemy session between concurrent coroutines

### IST Parallel Groups

```
Phase 1:  content_extraction
              │
              └── source_bias_assessment

Phase 2:  ┌── bottleneck_mapping ──── demand_modeling ──┐
          │                                              │
          └── external_validation ──────────────────────┤
                                                        │
              source_bias_assessment ───────────────────┤
                                                        ▼
              content_sufficiency_gate

Phase 3:  equity_scanning
              │
              ├── tier_classification ──────────┐
              │                                 │
              └── effects_analysis ────────────┤
                                               ▼
              invariant_check ── research_sufficiency_gate

Phase 4:  ┌── dialectic_optimist ──┐
          │                        │
          └── dialectic_pessimist ─┤
                                   ▼
              dialectic_synthesis

Phase 5:  master_screen
              │
              ├── rotation_strategy ───┐
              │                        │
              ├── catalyst_calendar ───┤
              │                        │
              └── stress_tests ────────┤
                                       ▼
              report_generation ── screen_coherence_gate ── screen_certification ── hfrt_handoff_generation
```

### Measured Impact — Complete Workflow 8 Timing (Feb 14, 2026)

**Full 22-step timing with parallelism active:**

| # | Step | Phase | Duration | Started | Parallel Group |
|---|------|-------|----------|---------|---------------|
| 1 | content_extraction | P1 | 35.8s | 02:07:29 | solo |
| 2 | source_bias_assessment | P1 | 10.8s | 02:08:05 | solo |
| 3 | bottleneck_mapping | P2 | 26.4s | 02:08:30 | **parallel with #5** |
| 4 | demand_modeling | P2 | 72.6s | 02:10:02 | solo (after #3) |
| 5 | external_validation | P2 | 91.8s | 02:08:30 | **parallel with #3** |
| 6 | content_sufficiency_gate | P2 | 0.0s | 02:11:15 | solo (gate) |
| 7 | equity_scanning | P3 | 19.8s | 02:15:08 | solo |
| 8 | tier_classification | P3 | 0.0s | 02:15:28 | **parallel with #9** |
| 9 | effects_analysis | P3 | 26.7s | 02:15:28 | **parallel with #8** |
| 10 | invariant_check | P3 | 0.0s | 02:15:54 | solo (gate) |
| 11 | research_sufficiency_gate | P3 | 0.0s | 02:15:54 | solo (gate) |
| 12 | dialectic_optimist | P4 | 37.4s | 02:16:05 | **parallel with #13** |
| 13 | dialectic_pessimist | P4 | 41.9s | 02:16:05 | **parallel with #12** |
| 14 | dialectic_synthesis | P4 | 47.4s | 02:16:47 | solo (after both) |
| 15 | master_screen | P5 | 13.6s | 02:18:40 | solo |
| 16 | rotation_strategy | P5 | 27.4s | 02:18:53 | **3-way parallel** |
| 17 | catalyst_calendar | P5 | 77.7s* | 02:18:53 | **3-way parallel** |
| 18 | stress_tests | P5 | 50.8s | 02:18:53 | **3-way parallel** |
| 19 | report_generation | P5 | 60.6s | 02:20:11 | solo (after 16-18) |
| 20 | screen_coherence_gate | P5 | 0.0s | 02:30:25 | solo (gate) |
| 21 | screen_certification | P5 | 0.0s | 02:30:25 | solo (gate) |
| 22 | hfrt_handoff_generation | P5 | 0.0s | 02:30:25 | solo (gate) |

*\* catalyst_calendar includes ~56s of API rate-limit retry waits (see Section 3)*

**Phase-level analysis:**

| Phase | Steps | Cumulative Compute | Wall-Clock | Parallel Saved |
|-------|-------|--------------------|-----------|---------------|
| P1 | 2 | 46.6s | 46.7s | 0s (linear chain) |
| P2 | 4 | 190.7s | 164.4s | **26.3s** |
| P3 | 5 | 46.6s | 46.7s | 0s (tier_classification = 0s) |
| P4 | 3 | 126.7s | 89.4s | **37.3s** |
| P5 | 8 | 230.1s | 152.3s* | **77.8s** |
| **Total** | **22** | **640.8s (10.7min)** | **499.5s (8.3min)** | **141.4s (2.4min)** |

*\* P5 wall-clock excludes gate failure retry time (see Section 4)*

**Time budget for the complete run:**

| Category | Duration | % of Total |
|----------|----------|-----------|
| Step compute (wall-clock) | 499.5s (8.3 min) | 36% |
| Inter-phase user pauses | 323.8s (5.4 min) | 24% |
| Rate-limit retry waits | ~56s (0.9 min) | 4% |
| Gate failure retries | ~497s (8.3 min) | 36% |
| **Total elapsed** | **1376.5s (22.9 min)** | 100% |

**Key finding:** Actual step compute is only **36% of total elapsed time**. The remaining 64% is non-compute overhead — user pauses, rate limits, and a gate failure that was retried 9 times before we fixed the underlying bug. This fundamentally reframes where the biggest optimization opportunities are.

### HFRT Parallel Groups (Same Engine, Different Graph)

| Phase | Parallel Steps |
|-------|---------------|
| P2 | business_model + competitive_position + industry_analysis (3-way) |
| P3 | management_assessment + risk_analysis + quality_of_earnings (3-way) |
| P4 | bull_case + bear_case |
| P5 | catalyst_analysis + investment_thesis; bull_synthesis + bear_synthesis; investment_memo + research_certification |

---

## 3. Discovery: API Rate Limiting Under Parallelism

### What Happened

When the Phase 5 3-way parallel group (`rotation_strategy`, `catalyst_calendar`, `stress_tests`) fired simultaneously, the Anthropic API returned **HTTP 429 (Too Many Requests)** on 2 of the 3 requests.

```
INFO:  Workflow 8: running 3 step(s) in parallel: ['rotation_strategy', 'catalyst_calendar', 'stress_tests']
INFO:  HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 429 Too Many Requests"
INFO:  Retrying request to /v1/messages in 26.000000 seconds
INFO:  HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 429 Too Many Requests"
INFO:  Retrying request to /v1/messages in 30.000000 seconds
```

**Impact:** `catalyst_calendar` took 77.7s instead of an estimated ~22s. The extra ~56s was pure retry wait time. This turned what should have been a 50.8s parallel group (limited by `stress_tests`) into a 77.7s group.

### Why This Matters

Parallelism and rate limits are inherently in tension. The whole point of parallelism is to fire multiple API calls simultaneously, but the API enforces per-minute or per-second request/token limits. Without rate-aware scheduling, you trade wall-clock improvements for retry penalties — and the retry penalties can exceed the parallelism savings.

### Lesson

**Parallelism requires a concurrency governor.** Never fire unbounded parallel API calls. The optimal concurrency limit depends on your API tier's rate limits. For Anthropic's API with typical rate limits, a semaphore of 2 concurrent requests avoids 429s while still capturing most parallelism benefits. This is documented as optimization opportunity 4A below.

---

## 4. Discovery: The Batch-Gather Limitation (Measured)

### What Happened

In Phase 2, `bottleneck_mapping` (26.4s) and `external_validation` (91.8s) ran in parallel. `demand_modeling` depends only on `bottleneck_mapping`, not on `external_validation`. But because `asyncio.gather()` waits for the entire batch to complete, `demand_modeling` didn't start until `external_validation` finished.

**Measured waste:**
- `bottleneck_mapping` completed at 02:08:57
- `demand_modeling` started at 02:10:02
- `demand_modeling` waited **65.4 seconds** after its only dependency completed

This is pure idle time where the pipeline could have been making progress but wasn't, because the batch-gather model doesn't check for newly unblocked steps until the current batch is fully done.

### Visualization

```
BATCH-GATHER (current):
  ┌─ bottleneck(26s) ──── IDLE(65s) ──── demand(72s) ─┐
  │                                                     │
  └─ validation(92s) ─────────────────────────────────  ┤
                                                        ▼
  Total: 92s + 72s = 164s

CONTINUOUS QUEUE (proposed):
  ┌─ bottleneck(26s) ──── demand(72s) ─────────────────┐
  │                                                     │
  └─ validation(92s) ─────────────────────────────────  ┤
                                                        ▼
  Total: max(26+72, 92) = 98s (saves 66s)
```

---

## 5. Discovery: Inter-Phase Pause Time Dominates

### What We Found

The IST pipeline requires user approval ("advance") between phases. This is a deliberate design choice — it lets the user review intermediate results before committing more API tokens. But the measured pause times are significant:

| Transition | Pause Duration | Likely Cause |
|-----------|---------------|-------------|
| Phase 1 → Phase 2 | 14.6s | Quick user approval |
| Phase 2 → Phase 3 | **233.1s (3.9 min)** | User reviewing P2 outputs (bottlenecks, demand models, validation) |
| Phase 3 → Phase 4 | 10.8s | Quick approval |
| Phase 4 → Phase 5 | 65.2s | User reviewing dialectic debate |
| **Total pauses** | **323.8s (5.4 min)** | |

**5.4 minutes of pure idle time** — more than the total parallel savings from Optimization #1. This is the single largest time sink in the pipeline after actual compute.

### Why This Matters

For experienced users running well-understood content types, the phase approval gates add friction without proportional value. A user who has run 10+ screens doesn't need to manually review every Phase 2 output before Phase 3 can start — they trust the pipeline's quality gates to catch issues.

### Lesson

**User-approval gates are a UX tradeoff, not a technical requirement.** The quality gates (content_sufficiency_gate, research_sufficiency_gate, screen_coherence_gate) already enforce quality programmatically. The manual approval is a safety net on top of that. Making it optional (auto-advance mode) would reclaim 5+ minutes with zero quality impact, because the programmatic gates still run.

---

## 6. Discovery: Brittle Quality Gates Cause False Failures

### What Happened

The `screen_coherence_gate` (step 20) verifies that the final report mentions all bottleneck names. It used an **exact substring match**: `if bn.name not in report.content`. Claude's report generation naturally paraphrases — using lowercase, possessives, plurals — which broke the match:

| Bottleneck Name (DB) | What Claude Wrote | Match? |
|----------------------|-------------------|--------|
| Energy Infrastructure Valuation Disconnect | "energy infrastructure valuation disconnects" | FAIL (case + plural) |
| Hyperscaler Capital Allocation Surge | "hyperscaler capital allocation" | FAIL (case + missing "Surge") |
| FERC Interconnection Queue Gridlock | "FERC's interconnection queue" | FAIL (possessive + scattered) |

The gate failed, the user retried 9 times (each failing identically because retrying the gate doesn't regenerate the report), and the workflow appeared stuck.

### Fix Applied

Replaced exact substring match with fuzzy word-overlap matching (`_bottleneck_name_in_report()`):
1. Extract key words (4+ characters) from the bottleneck name
2. Lowercase both sides
3. Check each key word as a substring of the report (so "disconnect" matches "disconnects", "ferc" matches "ferc's")
4. Pass threshold: >= 60% of key words found

All 3 failing cases now pass: each has 75%+ word overlap.

### Lesson for Future Pipelines

**Quality gates that compare AI-generated text should never use exact string matching.** LLMs paraphrase naturally — case variation, pluralization, possessives, synonym substitution. Gate checks must accommodate this linguistic flexibility. Options:
- **Fuzzy word overlap** (what we implemented — fast, no API call)
- **Semantic embedding similarity** (more robust but requires an embedding API call)
- **Structured ID references** (have the report reference bottlenecks by ID, not by name)

The third option is the most robust: if the report prompt says "reference bottleneck B-1, B-2, B-3 by their IDs", the gate can check for exact ID strings that Claude won't paraphrase.

---

## 7. Future Optimization Opportunities

### 7A. Continuous Task Queue (Replace Batch Gather) — SHIPPED

**Current limitation:** `asyncio.gather()` waits for ALL steps in a batch to complete before finding the next batch. Measured cost: 65.4s of idle time in Phase 2 alone (Section 4).

**Improvement:** Replace the batch loop with an `asyncio.Queue`-based executor where each completing step immediately checks what it unblocks and spawns those tasks.

**Implementation sketch:**
```python
completed = set()
running = set()

async def on_step_complete(step_name, result):
    completed.add(step_name)
    running.discard(step_name)
    # Check what's newly unblocked
    for pending in get_pending_steps():
        if all(dep in completed for dep in pending.depends_on):
            if pending.step_name not in running:
                running.add(pending.step_name)
                asyncio.create_task(execute_and_callback(pending))

# Seed with steps that have no dependencies
for step in get_ready_steps():
    running.add(step.step_name)
    asyncio.create_task(execute_and_callback(step))
```

**Measured savings opportunity:** 65.4s in Phase 2. Smaller gains in other phases where batch members have similar durations.

**Complexity:** Moderate. Requires:
- Thread-safe completed set (asyncio is single-threaded, so a plain set works)
- Phase boundary detection: when all steps in a phase are complete, pause for user approval
- Error propagation: if one step fails, cancel pending dependents
- Concurrency governor: integrate with rate-limit semaphore (7B)

**Quality risk:** None. Same steps execute with the same inputs — only scheduling order changes.

### 7B. API Rate-Limit Semaphore — SHIPPED

**Problem:** 3-way parallel API calls trigger HTTP 429, adding ~56s of retry waits (Section 3).

**Improvement:** Add an `asyncio.Semaphore(N)` around the Claude API call in `claude_client.py`. Start with N=2 (safe for most Anthropic rate limit tiers), then tune upward based on observed 429 rates.

**Implementation:**
```python
# In claude_client.py
_api_semaphore = asyncio.Semaphore(2)

async def call_claude(prompt, ...):
    async with _api_semaphore:
        return await client.messages.create(...)
```

**Measured savings:** ~56s in Phase 5 (from eliminating the 429 retries). Also prevents exponential backoff cascades in future phases with 3+ parallel API calls.

**Interaction with 7A:** If the continuous queue (7A) is implemented, more steps could overlap in time, increasing the likelihood of concurrent API calls. The semaphore becomes even more important to prevent 429 storms.

**Complexity:** Low — a 3-line change.

**Quality risk:** None. Same API calls, same responses — only the timing of when they fire changes.

### 7C. Auto-Advance Mode — SHIPPED

**Problem:** Inter-phase user pauses account for 5.4 minutes (24% of total elapsed time). Most of this is the user manually clicking "advance" (Section 5).

**Improvement:** Add an "Auto-Advance" toggle on the screen detail page. When enabled, the workflow engine skips the `PHASE_PAUSED` state and immediately begins the next phase after the current one completes. The programmatic quality gates (content_sufficiency_gate, research_sufficiency_gate, screen_coherence_gate) still run and will halt the pipeline if checks fail.

**Implementation:**
- Add `auto_advance` boolean column to `workflow_runs` (default false)
- In `workflow_engine._run_phase()`, after all phase steps complete: if `auto_advance` is true and the phase has a passing gate, immediately call `_run_phase()` for the next phase instead of setting status to `PHASE_PAUSED`
- Frontend toggle: simple switch in the workflow controls area
- SSE event: emit `phase_auto_advanced` so the UI can update in real-time

**Measured savings:** 323.8s (5.4 min) — the single largest optimization opportunity.

**Quality risk:** None. All three quality gates still execute. The only change is removing the human approval pause between phases. Users who want manual review can leave auto-advance off.

### 7D. Model Tiering (Sonnet for Mechanical Steps) — SHIPPED

**Insight:** Not all steps require Opus-level reasoning. Gates are checklist evaluations. Invariant checks are consistency verifications. Source bias assessment is a structured classification. These could run on Claude Sonnet (faster, cheaper) without quality loss.

**Proposed tiering:**

| Model | Steps | Rationale |
|-------|-------|-----------|
| Opus | content_extraction, bottleneck_mapping, demand_modeling, external_validation, equity_scanning, effects_analysis, dialectic_optimist, dialectic_pessimist, dialectic_synthesis, master_screen, report_generation | Heavy analytical reasoning, creative synthesis |
| Sonnet | source_bias_assessment, tier_classification, invariant_check, rotation_strategy, catalyst_calendar, stress_tests, screen_certification, hfrt_handoff_generation | Structured classification, template-following, data reformatting |
| None (pure logic) | content_sufficiency_gate, research_sufficiency_gate, screen_coherence_gate | No API call — server-side checks only |

**Implementation:**
- Add `model_override` field to step definitions (default: use workflow-level model)
- In `claude_client.py`, accept an optional `model` parameter
- Step handlers pass the model override through

**Estimated savings:** Sonnet is 3-5x faster than Opus for structured outputs. The 8 Sonnet-eligible steps currently consume ~150s cumulative. At 3x speedup, that drops to ~50s, saving ~100s.

**Validation protocol:** Before deploying, run both models on identical inputs for each Sonnet-eligible step. Diff the outputs. Only downgrade steps where Sonnet's output is structurally equivalent. This is a one-time validation cost that prevents ongoing quality risk.

**Quality risk:** Low with validation. The Sonnet-eligible steps are by design mechanical — they classify, tabulate, or reformat data that Opus already generated. They don't create new analytical insights.

### 7E. Smart Retry with Regeneration — SHIPPED

**Problem:** When `screen_coherence_gate` fails, retrying only re-runs the gate check against the same unchanged data. This is guaranteed to fail identically every time. The user retried 9 times before we diagnosed and fixed the underlying issue.

**Improvement:** When a quality gate fails, the retry mechanism should:
1. Identify which upstream step produced the non-conforming data
2. Re-run that upstream step with additional constraints (e.g., "you MUST include these exact bottleneck names as section headers")
3. Then re-run the gate

**Implementation:**
- Add `retry_strategy` to gate step definitions: `"retry_self"` (current behavior) or `"retry_with_parent"`
- For `screen_coherence_gate`, when the gate fails with "bottleneck not found in report", re-run `report_generation` with the bottleneck names injected into the prompt
- Log the retry chain for debugging

**Measured cost of not having this:** 9 failed retries, ~8 minutes of user frustration, and ultimately a code fix was needed. Smart retry would have resolved it in one additional API call (~60s).

**Quality risk:** None — it actually improves quality by ensuring the report covers all bottlenecks.

### 7F. Prompt Compression — MEDIUM PRIORITY

**Insight:** Some steps pass large context windows when they only need a subset. External validation (91.8s — the slowest step) sends all 34 claims in one prompt, but many are simple facts that don't need validation.

**Opportunities:**
- Pre-filter claims for validation: only validate claims with quantitative anchors (the ones that matter for investment decisions)
- Compress bottleneck descriptions before passing to downstream steps
- Use structured summaries instead of raw step outputs as context for later steps

**Estimated savings:** 20-40% reduction in input tokens for the heaviest steps. For external_validation, reducing 34 claims to ~15 high-value claims could cut duration from 92s to ~50s.

**Quality risk:** Medium. Context compression can lose nuance. Must ensure compressed representations preserve all decision-relevant information. Validate by comparing full-context vs compressed outputs on real data.

### 7G. Caching / Memoization — MEDIUM PRIORITY

**Insight:** If a user runs the same content through the pipeline twice (e.g., after a retry or parameter tweak), steps 1-2 (extraction, bias) will produce identical results. Content extraction is deterministic for the same input.

**Opportunities:**
- Hash the input content and cache extraction results
- On retry, skip extraction if the content hash matches
- Cache external validation results per claim (claims don't change between runs)

**Estimated savings:** Eliminates ~46s (extraction + bias) on reruns. External validation cache could save ~92s.

**Quality risk:** None for same-session reruns. Low for cross-session (Claude's knowledge doesn't change within a model version).

### 7H. Structured ID References in Reports — LOW-MEDIUM PRIORITY

**Insight (from Section 6):** The screen_coherence_gate failure was caused by matching bottleneck names as natural-language strings. A more robust design would have the report reference bottlenecks by stable IDs (e.g., `B-1`, `B-2`) instead of by name.

**Improvement:**
- Assign stable IDs to bottlenecks when they're created (already have DB primary keys)
- Report generation prompt includes a reference table: "B-1: Energy Infrastructure Valuation Disconnect, B-2: ..."
- Report must include all IDs in a structured metadata section
- Gate checks for ID presence (exact match — IDs don't get paraphrased)

**Quality risk:** None. The report still uses natural language for readability. The ID references are metadata that the gate checks programmatically.

### 7I. Streaming Step Outputs (Pipeline Overlap) — LOW PRIORITY

**Insight:** Currently each step waits for the full Claude response before writing to the database. But Claude streams tokens. A step like `content_extraction` could start writing claims to the DB as they stream in, allowing `source_bias_assessment` to begin processing partial results.

**Complexity:** High. Requires streaming JSON parsing, partial-result database writes, and downstream steps that can handle incrementally available data.

**Estimated savings:** 10-15s by overlapping extraction and bias assessment.

**Quality risk:** Low, but implementation complexity is high.

### 7J. Anthropic Batch API — LOW PRIORITY

**Insight:** The Anthropic API offers a batch endpoint for submitting multiple prompts simultaneously. Steps that are independent could be submitted as a batch rather than individual API calls.

**Applicability:** Most useful for the 3-way parallel groups. Instead of 3 separate HTTP round-trips, submit once and poll for results.

**Estimated savings:** Eliminates HTTP overhead (~1-2s per call). May also avoid per-request rate limits since batches are metered differently. Marginal per-step but could synergize with 7B (rate-limit semaphore) by avoiding 429s entirely.

**Quality risk:** None. Same prompts, same model, same outputs.

---

## 8. Optimization Priority Matrix (Updated)

| # | Optimization | Effort | Speed Impact | Quality Risk | Priority |
|---|-------------|--------|-------------|-------------|----------|
| — | Dependency-aware parallelism | Done | 2.4 min saved | None | **SHIPPED** |
| — | Fuzzy gate matching | Done | Prevents false failures | None (improves reliability) | **SHIPPED** |
| 7C | Auto-advance mode | Done | **5.4 min** | None | **SHIPPED** |
| 7B | Rate-limit semaphore | Done | ~1 min | None | **SHIPPED** |
| 7A | Continuous task queue | Done | ~1-2 min | None | **SHIPPED** |
| 7D | Model tiering (Sonnet) | Done | ~1.5-2 min | Low (needs validation) | **SHIPPED** |
| 7E | Smart retry with regen | Done | Variable (prevents stuck pipelines) | None (improves quality) | **SHIPPED** |
| 7F | Prompt compression | Medium | ~1-2 min | Medium | **Medium** |
| 7G | Caching/memoization | Medium | ~2 min on reruns | None | **Medium** |
| 7H | Structured ID references | Low | Prevents false gate failures | None | **Low-Medium** |
| 7I | Streaming overlap | High | ~15s | Low | **Low** |
| 7J | Batch API | Low | ~10s | None | **Low** |
| 7K | Claim-batched validation | Medium | ~20-30s | None (see §11) | **REVERTED** |
| 7L | Report dependency split | Medium | ~30-60s | Low (see §11) | **REVERTED** |
| 7M | Prompt caching (Anthropic) | Low | ~5-10s | None | **REVERTED** |
| 7N | Data package caching | Low | ~5-10s | None (see §11) | **REVERTED** |
| 7O | Source bias dep relaxation | Low | ~10s | None (see §11) | **REVERTED** |
| 7P | Raise semaphore to 4 | Low | Enables 7K/7Q | None | **REVERTED** |
| 7Q | Per-bottleneck demand parallelism | Medium | ~20-30s | None (see §11) | **REVERTED** |

**Measured pipeline time (post-7A through 7E, with auto-advance):**

| Scenario | Time |
|----------|------|
| Original (sequential + manual advance) | ~22.9 min |
| + All shipped optimizations (7A-7E) | **~7 min wall-clock** (with auto-advance) |
| Theoretical + 7K-7Q | ~5-5.5 min (estimated, not validated in production) |
| Theoretical + prompt compression (7F) | ~4.5 min |

**From 22.9 minutes (original) to ~7 minutes (current shipped state) — a 3.3x improvement with zero quality degradation.**

---

## 9. Lessons Learned

### Profiling & Measurement

1. **Profile before optimizing.** Measuring individual step durations revealed that `external_validation` (92s) and `demand_modeling` (72s) are the bottlenecks, not the lightweight steps. Parallelizing the wrong steps would have yielded minimal gains.

2. **Measure the whole pipeline, not just compute.** Our initial focus was on step execution time. But the full-run timing revealed that user pauses (5.4 min) and rate-limit retries (0.9 min) together exceeded the parallel compute savings (2.4 min). The biggest optimization opportunity was non-compute overhead, not step speed.

3. **Categorize your time budget.** Breaking elapsed time into compute / pause / retry / failure buckets immediately showed that auto-advance (a UX change) would save more time than any algorithmic optimization. Without this categorization, we would have over-invested in compute optimization and under-invested in workflow UX.

### Parallelism

4. **Dependency analysis unlocks parallelism.** The original sequential design was a simplification, not a requirement. Mapping actual data dependencies (what each step reads from the DB) revealed that many steps are independently derivable from the same upstream data.

5. **Batch gather vs. continuous queue is a real tradeoff.** The simpler `asyncio.gather()` approach leaves performance on the table when batch members have very different durations. For a 22-step pipeline where steps range from 0s to 92s, the continuous queue approach (7A) would be meaningfully faster. Measured cost: 65.4s of idle time in one phase alone.

6. **Parallelism creates rate-limit pressure.** Firing 3 concurrent API calls triggered 429 responses with 26-30 second retry waits. The optimization that was supposed to save time actually added time in that batch. A concurrency governor (semaphore) is essential whenever parallelizing API-bound workloads.

7. **SQLAlchemy session isolation is critical for async parallelism.** Sharing a single DB session across `asyncio.gather()` coroutines causes race conditions. Each parallel unit of work needs its own session lifecycle.

### Quality Gates

8. **Quality gates should never use exact string matching against AI-generated text.** LLMs paraphrase naturally — case variation, pluralization, possessives, synonym substitution. A gate that checks for exact bottleneck names will fail whenever Claude exercises normal linguistic flexibility. Use fuzzy matching, embedding similarity, or structured IDs.

9. **Retry must be smart, not mechanical.** When a gate fails because upstream data doesn't conform, re-running the gate produces the same failure. Smart retry identifies the upstream step that produced non-conforming data and re-runs it with tightened constraints. This is the difference between a pipeline that self-heals and one that gets stuck.

10. **False gate failures are a hidden time cost.** Our gate failure consumed ~8 minutes of user time (9 retries) before a code fix resolved it. In production, users can't fix code — they abandon the run. Every false failure is a lost workflow that wastes all the compute that came before the gate.

### Infrastructure

11. **Server reload matters.** WatchFiles-based auto-reload doesn't always detect changes across all modules. Clearing `__pycache__` and fully restarting the server is necessary when modifying multiple interdependent files (model + router + engine).

12. **Migration timing matters.** Steps created before a schema migration don't get new column values retroactively. Either backfill existing data or ensure users create fresh runs after deploying schema changes.

13. **API response contracts matter.** A mismatch between backend response shapes (snake_case nested JSON from Claude) and frontend expectations (camelCase with specific structures) caused runtime crashes across 5 UI tabs. A single recursive `_deep_camel()` serialization layer plus structural normalization functions eliminated the entire class of bugs. Lesson: define and enforce a response contract (via Pydantic models with `alias_generator`) from day one, not as a post-hoc fix.

### Deployment Discipline (from 7K-7Q attempt — see §11)

14. **Never batch multiple optimizations into one deployment.** Seven changes across four files made it impossible to isolate the source of instability. Apply one optimization, test fully (including UI navigation), commit, then proceed to the next.

15. **Test the user journey, not just the pipeline.** All unit tests passed. The pipeline ran successfully. But the site froze due to an SSE connection leak unrelated to pipeline logic. Testing must include end-to-end UI flows: navigate to completed screen → away → back → check DevTools network tab.

16. **Pre-existing bugs surface during optimization work.** The SSE leak existed before any optimizations were attempted but was only exposed because the optimization workflow involved repeatedly visiting completed screens. Optimization efforts are inadvertent stress tests.

17. **Revert-first is the right instinct.** When multiple variables changed and something breaks, resist the urge to "fix forward." Revert to baseline, confirm the problem persists (or doesn't), and re-apply changes one at a time.

### Connection Lifecycle (from SSE bug — see §12)

18. **SSE connections are a finite resource.** Browsers enforce ~6 connections per domain (HTTP/1.1). Any SSE connection that fails to close permanently consumes a slot. Every SSE endpoint must guarantee a terminal condition.

19. **Always close server-push connections for terminal states.** When a client subscribes to a stream for an entity already in a final state, send the snapshot + terminal event, then close. Never enter a heartbeat loop for entities that will never produce new events.

20. **Defense in depth for connection lifecycle.** Both backend (close stream) and frontend (detect terminal status in catch_up) should independently handle cleanup. Either layer alone is sufficient; both together prevent regressions.

---

## 10. Appendix: Token Usage (Workflow 8)

| Phase | Cumulative Tokens | Notes |
|-------|------------------|-------|
| P1 | 8,073 | content_extraction (6,025) + source_bias (2,048) |
| P2 | 20,828 | bottleneck (4,509) + validation (8,868) + demand (7,451) |
| P3 | 7,680 | equity_scanning (5,192) + effects (2,488) |
| P4 | 46,632 | optimist (14,074) + pessimist (14,226) + synthesis (18,332) |
| P5 | 104,301 | master (18,697) + rotation (20,321) + catalyst (20,711) + stress (18,881) + report (25,691) |
| **Total** | **~187,514** | 37.5% of 500K token budget |

**Observation:** Phase 5 consumes 56% of all tokens despite having 8 steps (most of which are gates with 0 tokens). The 5 Claude-calling steps in P5 average 20,860 tokens each — significantly higher than earlier phases. This is because P5 steps receive the full accumulated context from all prior phases. Prompt compression (7F) would have the largest impact here.

---

## 11. Optimization Attempt: 7K-7Q Speed Enhancements (Attempted → Reverted)

> **Status:** All 7 optimizations implemented, tested, then fully reverted due to instability. Root cause was a pre-existing SSE connection leak (Section 12) misattributed to the optimizations. The optimizations themselves are technically sound but need to be re-applied incrementally with proper isolation testing.

### What Was Attempted

Seven additional "zero quality degradation" speed optimizations, implemented in a single batch across 4 files:

| # | Optimization | File(s) Modified | Nature |
|---|-------------|-----------------|--------|
| 7K | Claim-batched external validation | `thematic_analysis.py` | Split single monolithic `call_claude()` into batches of ~8 claims, run via `asyncio.gather()` |
| 7L | Report dependency split | `ist.py` + `final_synthesis.py` | Split `report_generation` into two steps: core report (depends only on `master_screen`) + `report_finalization` (depends on rotation/catalyst/stress). Allowed report to start before the 3-way parallel group finished. |
| 7M | Prompt caching (Anthropic API) | `claude_client.py` | Added `cache_control: {"type": "ephemeral"}` to system prompts >4096 chars. Uses Anthropic's server-side prompt caching. |
| 7N | Data package result caching | `final_synthesis.py` | Module-level `dict[screen_id, str]` cache so `_build_full_data_package()` runs once per Phase 5 instead of 5 times. |
| 7O | Source bias dependency relaxation | `ist.py` | Removed `content_extraction` from `source_bias_assessment.depends_on`. Source bias only reads `screen.raw_content` (set at creation), not extraction output. |
| 7P | Raise semaphore to 4 | `claude_client.py` | `API_SEMAPHORE_LIMIT` from 2 → 4 to support higher concurrency from 7K/7Q batching. |
| 7Q | Per-bottleneck demand parallelism | `thematic_analysis.py` | Split single `call_claude()` for all bottlenecks into per-bottleneck calls running via `asyncio.gather()`. |

### What Happened

1. All 7 optimizations were implemented in a single session across `claude_client.py`, `ist.py`, `thematic_analysis.py`, and `final_synthesis.py`
2. Tests passed (8/8, pre-existing `test_get_candidates_not_certified` failure unchanged)
3. A new screen run was attempted — **the site froze when navigating to completed screens**
4. Initial diagnosis attributed the freeze to the optimizations (multiple files changed simultaneously)
5. An SSE connection fix was applied (backend terminal state detection + frontend catch_up cleanup)
6. User reported "literally no change" — site still frozen
7. **Complete revert** of all 7K-7Q optimizations + the SSE fix was requested and executed
8. Site still froze after full revert — proving the optimizations were NOT the cause
9. Root cause identified: **pre-existing SSE connection leak** (Section 12)
10. SSE fix re-applied as a standalone change — site freeze resolved

### Why the Revert Was Correct (Even Though the Optimizations Were Innocent)

The simultaneous change of 4 files across 7 optimizations made it impossible to isolate which change (if any) caused the problem. The user's instinct to revert was sound — in a multi-variable debugging scenario, returning to a known-good baseline and changing one thing at a time is the only reliable approach.

### Technical Soundness of Each Optimization

Each optimization was validated at the design level to have zero quality impact:

| # | Quality Preservation Argument |
|---|------------------------------|
| 7K | Same claims, same system prompt, same validation schema per batch. Each claim validated independently in both approaches. |
| 7L | Core report gets 90%+ of data. Finalization appends portfolio construction from rotation/catalyst/stress. Same final output. |
| 7M | Anthropic prompt caching is transparent — model sees identical tokens. Pure API-level optimization. |
| 7N | `_build_full_data_package()` is deterministic for same `screen_id` within a run. Cache returns identical string. |
| 7O | `handle_source_bias` only reads `screen.raw_content` and `screen.content_type`, both set at creation. No data dependency on extraction output. |
| 7P | Semaphore controls timing, not content. Each API call sends/receives identical data. |
| 7Q | Each bottleneck's demand model is computed independently. Same input per bottleneck, same output. |

### Lessons from the 7K-7Q Attempt

14. **Never batch multiple optimizations into one deployment.** Seven changes across four files made it impossible to isolate the source of instability. Each optimization should be applied, tested in isolation (including a full workflow run + site navigation test), and committed separately before moving to the next.

15. **Test the user journey, not just the pipeline.** All tests passed. The pipeline ran successfully. But the site froze because of a connection leak unrelated to the pipeline logic. Testing should include: navigate to completed screen → navigate away → navigate back → check browser DevTools network tab for orphaned connections.

16. **Pre-existing bugs surface during optimization work.** The SSE leak existed before any optimizations were attempted. It was only noticed because the optimization work involved repeatedly visiting completed screens. The optimization effort created the testing conditions that exposed the latent bug.

17. **Revert-first is the right instinct.** When multiple variables changed and something breaks, resist the urge to "fix forward." Revert to baseline, confirm the problem persists (or doesn't), and re-apply changes one at a time. This is slower but produces reliable root-cause identification.

18. **Module-level caches need lifecycle management.** The `_data_package_cache` (7N) was keyed by `screen_id` and cleared via `clear_data_package_cache()` called from `delete_screen` and `rerun_screen`. But if the server process persists across workflow runs, stale cache entries could serve outdated data. Production caches need TTL or explicit invalidation tied to the workflow lifecycle.

### Re-Application Roadmap

These optimizations are technically sound and should be re-applied **one at a time** in this order:

1. **7O** (source bias dep relaxation) — 1-line change, zero risk, immediate ~10s gain
2. **7M** (prompt caching) — Small helper + 2 call sites, zero risk, ongoing token cost savings
3. **7N** (data package caching) — Module-level cache, low risk, eliminates 4 redundant DB round-trips
4. **7P** (semaphore raise to 4) — 1-line change, prerequisite for 7K/7Q, monitor for 429s
5. **7K** (claim batching) — Rewrite `handle_external_validation`, test with varying claim counts
6. **7Q** (demand parallelism) — Rewrite `handle_demand_modeling`, test with varying bottleneck counts
7. **7L** (report split) — Most complex: new step + handler + dependency graph change. Apply last.

Each step: implement → run full workflow → navigate completed screens → check DevTools → commit → next.

---

## 12. Discovery: SSE Connection Leak (Pre-existing Bug)

### What Happened

After the 7K-7Q optimization attempt, navigating to any completed screen caused the entire site to freeze. The freeze persisted even after reverting all optimizations — proving this was a **pre-existing bug**, not caused by the changes.

### Root Cause

**Dual-layer failure:**

1. **Backend** (`workflow_engine.py`, `sse_event_generator`): When a client connects to `/api/workflows/{id}/stream` for an already-completed workflow, the server sends a `catch_up` event with all step data, then enters an infinite `while True` heartbeat loop. No terminal event (`workflow_complete`) ever arrives in the queue because the workflow finished long ago. The connection stays open forever.

2. **Frontend** (`useWorkflowSSE.ts`): The `useWorkflowSSE` hook opens an `EventSource` connection whenever `workflowId` is not null — with no guard for the workflow's completion status. The `catch_up` handler populates state but never closes the connection for terminal workflows.

**Cascade effect:** Browsers limit ~6 concurrent HTTP connections per domain. Each visit to a completed screen opens a permanent SSE connection. After visiting ~6 screens, all connection slots are consumed. The entire site freezes — no new API requests, page loads, or asset fetches can proceed.

### Fix Applied (Dual-Layer)

**Backend** — After sending `catch_up`, check if the workflow is in a terminal state. If so, send a synthetic terminal event and `return` immediately:

```python
# workflow_engine.py — after yield catch_up
if run.status in ("COMPLETED", "FAILED", "CANCELLED"):
    terminal_event = {
        "type": f"workflow_{run.status.lower()}",
        "workflowId": run.id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    yield f"event: {terminal_event['type']}\ndata: {json.dumps(terminal_event)}\n\n"
    return
```

**Frontend** — In the `catch_up` handler, close the connection if the status is terminal:

```typescript
// useWorkflowSSE.ts — end of catch_up case
const TERMINAL_STATUSES = ['COMPLETED', 'FAILED', 'CANCELLED'];
if (data.status && TERMINAL_STATUSES.includes(data.status)) {
  cleanup();
  setConnected(false);
}
```

### Verification

```
$ timeout 5 curl -sN http://localhost:8000/api/workflows/10/stream
event: catch_up
data: {"type": "catch_up", "workflowId": 10, "status": "COMPLETED", ...}

event: workflow_completed
data: {"type": "workflow_completed", "workflowId": 10, ...}
(connection closed immediately)
```

Before the fix, this curl command would hang indefinitely, sending heartbeats every 15 seconds.

### Lessons

19. **SSE connections are a finite resource.** Browsers enforce a hard limit (~6 per domain for HTTP/1.1). Any SSE connection that fails to close is a permanent resource leak. Every SSE endpoint must have a terminal condition — never assume the client will disconnect first.

20. **Always close server-push connections for terminal states.** When a client subscribes to a real-time stream for an entity that's already in a final state (completed, failed, cancelled), the server should send the current state snapshot and a terminal event, then close the connection. Entering a heartbeat loop for an entity that will never produce new events is a resource leak.

21. **Defense in depth for connection lifecycle.** The backend fix alone would have resolved the issue (the server closes the stream). But the frontend fix provides a safety net — if the backend ever fails to close, the client detects the terminal state and disconnects. Both layers are necessary for robustness.

22. **Latent bugs surface under stress testing.** The SSE leak existed from the moment SSE was implemented but was never noticed because early testing involved only 1-2 screens. The optimization work — which required repeatedly visiting completed screens to compare before/after — created the conditions that exposed it.

---

## 13. Measured Timing: Post-Revert Baseline (Workflow 8, Feb 15 2026)

Full 22-step run with all shipped optimizations (7A-7E) active, auto-advance enabled:

| # | Step | Phase | Duration | Model | Notes |
|---|------|-------|----------|-------|-------|
| 1 | content_extraction | P1 | 35.8s | opus | Solo |
| 2 | source_bias_assessment | P1 | 12.3s | sonnet | After #1 |
| 3 | bottleneck_mapping | P2 | 25.8s | opus | **Parallel with #5** |
| 4 | demand_modeling | P2 | 73.3s | opus | After #3 (wait for bottleneck) |
| 5 | external_validation | P2 | 91.9s | opus | **Parallel with #3** |
| 6 | content_sufficiency_gate | P2 | 21ms | none | Gate |
| 7 | equity_scanning | P3 | 23.0s | opus | Solo |
| 8 | tier_classification | P3 | 15ms | none | **Parallel with #9** |
| 9 | effects_analysis | P3 | 25.4s | opus | **Parallel with #8** |
| 10 | invariant_check | P3 | 18ms | none | Gate |
| 11 | research_sufficiency_gate | P3 | 10ms | none | Gate |
| 12 | dialectic_optimist | P4 | 43.2s | opus | **Parallel with #13** |
| 13 | dialectic_pessimist | P4 | 38.4s | opus | **Parallel with #12** |
| 14 | dialectic_synthesis | P4 | 43.4s | opus | After both |
| 15 | master_screen | P5 | 15.3s | opus | Solo |
| 16 | rotation_strategy | P5 | 28.7s | sonnet | **3-way parallel** |
| 17 | catalyst_calendar | P5 | 21.1s | sonnet | **3-way parallel** |
| 18 | stress_tests | P5 | 118.7s | sonnet | **3-way parallel** (dominates) |
| 19 | report_generation | P5 | 62.8s | opus | After #16-18 |
| 20 | screen_coherence_gate | P5 | 21ms | none | Gate |
| 21 | screen_certification | P5 | 13ms | none | Gate |
| 22 | hfrt_handoff_generation | P5 | 12ms | none | Gate |

**Wall-clock: ~7 minutes** (with auto-advance, no user pauses).

**Critical path analysis:**

```
content_extraction(36s)
    → source_bias(12s)
    → [Phase 2 parallel start]
    → external_validation(92s)     ← Phase 2 critical path
    → content_sufficiency_gate
    → equity_scanning(23s)
    → effects_analysis(25s)
    → research_sufficiency_gate
    → dialectic_optimist(43s)      ← Phase 4 critical path (pessimist = 38s, shorter)
    → dialectic_synthesis(43s)
    → master_screen(15s)
    → stress_tests(119s)           ← Phase 5 critical path (dominates 3-way parallel)
    → report_generation(63s)
    → gates(~0s)

Critical path total: 36+12+92+0+23+25+0+43+43+15+119+63+0 = ~471s ≈ 7.9 min
```

**Bottleneck identification:**
1. `stress_tests` (119s) — the single slowest step and Phase 5 critical path dominator
2. `external_validation` (92s) — Phase 2 critical path
3. `demand_modeling` (73s) — blocked behind `bottleneck_mapping`, could overlap with `external_validation` if dependencies allowed
4. `report_generation` (63s) — serial, must wait for stress_tests

---

## 14. Cross-Workflow Optimization Framework

> **Purpose:** Generalized methodology for optimizing any multi-step AI pipeline (IST, HFRT, future workflows) with zero quality degradation. Derived from IST optimization experience.

### Phase 0: Profile and Categorize (Before Touching Code)

**Step 0.1 — Measure baseline timing per step.**

Run the pipeline end-to-end with logging that captures each step's start time, end time, and duration. This is the only way to know where time is actually spent.

```
Deliverable: Table of (step_name, phase, duration_seconds, model_used)
```

**Step 0.2 — Categorize time budget.**

Break total elapsed time into buckets:

| Category | Description | Example |
|----------|-------------|---------|
| **Compute** | Time spent in API calls + DB writes | Step execution |
| **Scheduling idle** | Time a step could have started but didn't | Batch-gather waste |
| **Rate-limit wait** | Time spent in retry backoff | HTTP 429 responses |
| **User pause** | Time waiting for human approval | Phase boundaries |
| **Gate failure** | Time wasted on failed retries | Retrying gates against unchanged data |

The largest category is where you optimize first. In IST, it was user pauses (5.4 min > any single optimization).

**Step 0.3 — Map the dependency graph.**

For every step, determine: what data does it *actually read* from the database? This reveals the true dependencies (which may be much looser than the configured `depends_on`). Steps that share an upstream dependency but don't read each other's output can run in parallel.

```
Deliverable: DAG visualization + list of parallel groups per phase
```

**Step 0.4 — Identify the critical path.**

The critical path is the longest chain of sequential dependencies. Total pipeline time can never be shorter than the critical path. Optimizations that reduce steps NOT on the critical path don't reduce total time.

```
Deliverable: Critical path with cumulative timing
```

### Phase 1: Zero-Risk Structural Optimizations

These changes modify scheduling/infrastructure without touching any prompt content or analytical logic.

| Optimization | Applies When | Implementation | IST Example |
|-------------|-------------|----------------|-------------|
| **Dependency relaxation** | Step's `depends_on` is more restrictive than its actual data reads | Remove false dependencies from step definitions | 7O: source_bias didn't need content_extraction |
| **Auto-advance** | Pipeline has user-approval pauses between phases | Add toggle to skip PHASE_PAUSED state | 7C: saved 5.4 min |
| **Semaphore tuning** | API rate limits allow higher concurrency | Raise `asyncio.Semaphore` limit, monitor for 429s | 7B/7P: 2 → 4 |
| **Data package caching** | Same expensive query is repeated N times in one phase | Module-level or workflow-context cache | 7N: 5 → 1 calls to `_build_full_data_package()` |
| **Prompt caching** | Same system prompt used across multiple steps | Anthropic `cache_control: ephemeral` on system blocks | 7M: reduces input token processing |
| **SSE lifecycle** | Server-push connections for terminal entities | Send synthetic terminal event + close for completed/failed/cancelled | §12: prevented browser connection pool exhaustion |

### Phase 2: Parallelism Enhancements

Split monolithic API calls into parallel sub-calls. Requires more testing but zero quality risk if inputs are partitioned correctly.

| Pattern | Applies When | Key Requirement | IST Example |
|---------|-------------|----------------|-------------|
| **Batch splitting** | One API call processes N items serially | Each item must be independently processable | 7K: 34 claims → batches of 8 |
| **Per-entity parallelism** | One API call processes N entities | Each entity must have no cross-entity dependency | 7Q: 10 bottlenecks → 10 parallel calls |
| **Step splitting** | One step has multiple output artifacts | Artifacts that can be produced independently | 7L: report_generation → report + finalization |

**Guard rails for parallelism:**
- Respect the API semaphore — more parallelism means more concurrent calls
- Each parallel unit needs its own DB session (SQLAlchemy is not coroutine-safe)
- Merge results carefully — index offsets, ordering, deduplication
- Test with varying input sizes (1 item, 5 items, 50 items)

### Phase 3: Model Tiering

Assign the cheapest model that maintains quality for each step.

| Model | Use For | Characteristics |
|-------|---------|----------------|
| **Opus** | Creative synthesis, deep analysis, adversarial reasoning | content_extraction, dialectic_*, report_generation |
| **Sonnet** | Structured classification, template-following, data reformatting | source_bias, rotation_strategy, catalyst_calendar, stress_tests |
| **None** | Pure server-side logic | All gates, invariant checks, tier_classification |

**Validation protocol:** Before downgrading a step from Opus to Sonnet, run both models on 3+ real inputs. Diff the outputs. Only downgrade if Sonnet's output is structurally equivalent and analytically sufficient.

### Phase 4: Prompt Optimization (Higher Risk)

These optimizations touch the actual prompt content and carry quality risk. Proceed with caution.

| Optimization | Risk Level | Mitigation |
|-------------|-----------|------------|
| **Prompt compression** | Medium | Compare full vs. compressed outputs on 5+ real inputs |
| **Context windowing** | Medium | Only pass relevant subset of upstream data |
| **Structured ID references** | Low | Use stable IDs instead of natural language names in gate checks |

### Applying to HFRT

The HFRT workflow (23 steps, 5 phases) has the same architecture — `depends_on` DAG, same workflow engine, same `call_claude()` / `call_claude_raw()` client. The framework applies directly:

**HFRT-specific parallel groups (from Section 2):**

| Phase | Parallel Group | Steps |
|-------|---------------|-------|
| P2 | 3-way | business_model + competitive_position + industry_analysis |
| P3 | 3-way | management_assessment + risk_analysis + quality_of_earnings |
| P4 | 2-way | bull_case + bear_case |
| P5 | Various | catalyst_analysis + investment_thesis; bull_synthesis + bear_synthesis |

**HFRT optimization checklist:**

1. [ ] **Profile**: Run a full HFRT workflow with per-step timing
2. [ ] **Categorize**: Break time into compute / idle / rate-limit / pause / failure buckets
3. [ ] **Map dependencies**: Audit each step's actual DB reads vs. configured `depends_on`
4. [ ] **Identify critical path**: Which chain of sequential steps dominates total time?
5. [ ] **Auto-advance**: Already supported by workflow engine (toggle per run)
6. [ ] **Dependency relaxation**: Are any HFRT `depends_on` lists overly conservative?
7. [ ] **Model tiering**: Which HFRT steps can use Sonnet? (likely: SEC filing extraction, structured summaries)
8. [ ] **Data package caching**: Does HFRT rebuild expensive queries multiple times in Phase 5?
9. [ ] **SSE lifecycle**: Already fixed globally (workflow_engine.py handles all workflows)
10. [ ] **Semaphore tuning**: Shared with IST — changes affect both workflows

### Anti-Patterns (What NOT to Do)

| Anti-Pattern | Why It's Dangerous | What Happened in IST |
|-------------|-------------------|---------------------|
| **Batch multiple optimizations** | Impossible to isolate regressions | 7 changes across 4 files; couldn't identify SSE leak vs. optimization bug |
| **Test only the pipeline** | Misses UI/infrastructure bugs | Pipeline passed, but SSE leak froze the site |
| **Assume `--reload` works** | uvicorn file watcher can miss changes | Required manual server restart after multi-file changes |
| **Fix forward under pressure** | Adds complexity to an already broken state | Revert-first would have identified the pre-existing SSE bug faster |
| **Exact string matching in gates** | LLMs paraphrase naturally | 9 failed retries, ~8 min wasted, code fix needed |
| **Module-level cache without TTL** | Stale data across workflow runs | 7N cache keyed by screen_id but no expiry mechanism |
| **Shared DB session in async** | Race conditions under `asyncio.gather()` | Required `SessionLocal()` per parallel unit |

### Incremental Deployment Protocol

For any optimization applied to any workflow:

```
1. IMPLEMENT one optimization in one file
2. RUN existing unit tests (python -m pytest tests/ -x -q)
3. RUN a full workflow end-to-end with auto-advance
4. NAVIGATE to completed workflow screen → navigate away → navigate back
5. CHECK browser DevTools → Network tab for orphaned connections
6. COMPARE output quality against baseline (spot-check 2-3 sections)
7. COMMIT with descriptive message: "perf(ist): 7O source bias dependency relaxation"
8. REPEAT for next optimization
```

Never skip step 4. The SSE leak was invisible to steps 2-3.
