# IST Extension — Fix Plan

**Date:** 2026-02-21
**Author:** Claude Code (CC)
**Source:** Four-layer compliance review of Codex's IST extension implementation
**Scope:** 11 critical issues, plus high-priority warnings that must ship together

---

## How to Use This Document

Each fix is numbered (F1–F16) with:
- **Priority:** CRITICAL (blocks correctness) or HIGH (blocks quality)
- **File(s):** Exact paths and line numbers
- **Problem:** What's wrong
- **Fix:** Exactly what to change
- **Depends on:** Other fixes that must be applied first

Apply fixes in the order listed — dependencies are already sorted.

---

## Phase 1: Database & Schema Foundation (F1–F3)

These must land first because service and API fixes depend on the correct column set.

### F1 — Add Missing Columns to `ISTScreenRefresh` Model + Migration

**Priority:** CRITICAL
**Files:**
- `backend/app/models/ist_refresh.py` (lines 38–42)
- `backend/alembic/versions/015_ist_synthesis_and_refresh.py` (lines 223–286)

**Problem:** The model is missing 5 output columns that service handlers need to write delta results to: `new_claims_count`, `new_claims`, `new_source_bias`, `tier_changes`, `tier_change_count`. Without these, the refresh pipeline cannot persist its analytical output and the `ScreenRefreshDetail` API response cannot be populated.

**Fix — Model (`ist_refresh.py`):** Add the following columns after `steps_reexecuted` (line 41):

```python
    # Delta output columns
    new_claims_count = Column(Integer, nullable=False, default=0)
    new_claims = Column(Text, nullable=True)          # JSON: list of new/modified claim summaries
    new_source_bias = Column(Text, nullable=True)      # JSON: bias assessment of delta content
    tier_changes = Column(Text, nullable=True)          # JSON: list of {ticker, old_tier, new_tier}
    tier_change_count = Column(Integer, nullable=False, default=0)
```

**Fix — Migration (`015_...py`):** Add matching `op.add_column` calls in the `ist_screen_refreshes` table creation section. Add `server_default="0"` for the integer columns.

**Fix — Migration backfill SQL guard** (line ~313): Wrap the `active_workflow_run_id` backfill in `sa.text()` and add a NULL guard:

```python
op.execute(sa.text(
    "UPDATE ist_screens SET active_workflow_run_id = workflow_run_id "
    "WHERE active_workflow_run_id IS NULL AND workflow_run_id IS NOT NULL"
))
```

**Depends on:** Nothing

---

### F2 — Verify Migration Chain

**Priority:** CRITICAL
**Files:** `backend/alembic/versions/`

**Problem:** Migration 015 uses bare revision ID `"015"` chaining to `"014"`. The chain must resolve cleanly.

**Fix:** Run:
```bash
cd backend
source venv/Scripts/activate
alembic history
alembic check
```

If the chain resolves, no code change needed — just confirm. If it fails, update the `down_revision` to match the actual previous revision string.

**Depends on:** F1

---

### F3 — Create Response Schemas for Synthesis and Refresh

**Priority:** CRITICAL
**Files:**
- NEW: `backend/app/schemas/ist_synthesis.py`
- MODIFY: `backend/app/schemas/ist.py` (add refresh response schemas + `source_refresh_id` to `ISTClaimResponse`)
- MODIFY: `backend/app/routers/ist_synthesis.py` (update imports)

**Problem:** The plan requires `backend/app/schemas/ist_synthesis.py` with full synthesis response schemas. It was never created. The routers currently return raw dicts, bypassing Pydantic validation. `ISTClaimResponse` is also missing `source_refresh_id`.

**Fix — Create `backend/app/schemas/ist_synthesis.py`:**

```python
"""Pydantic schemas for IST synthesis endpoints."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SynthesisSourceResponse(BaseModel):
    id: int
    screen_id: int = Field(alias="screenId")
    screen_name: str = Field(alias="screenName")
    primary_theme: Optional[str] = Field(default=None, alias="primaryTheme")
    tier1_count: int = Field(default=0, alias="tier1Count")
    tier2_count: int = Field(default=0, alias="tier2Count")
    tier3_count: int = Field(default=0, alias="tier3Count")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SynthesisEquityResponse(BaseModel):
    id: int
    ticker: str
    company_name: Optional[str] = Field(default=None, alias="companyName")
    original_tier: int = Field(alias="originalTier")
    new_tier: int = Field(alias="newTier")
    conviction: Optional[str] = None
    rationale: Optional[str] = None
    source_screen_ids: Optional[str] = Field(default=None, alias="sourceScreenIds")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SynthesisDialecticResponse(BaseModel):
    id: int
    side: str
    narrative: Optional[str] = None
    key_arguments: Optional[str] = Field(default=None, alias="keyArguments")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SynthesisListItem(BaseModel):
    id: int
    name: str
    status: str
    workflow_run_id: int = Field(alias="workflowRunId")
    source_screen_count: int = Field(default=0, alias="sourceScreenCount")
    tier_change_count: int = Field(default=0, alias="tierChangeCount")
    is_certified: int = Field(default=0, alias="isCertified")
    certified_at: Optional[datetime] = Field(default=None, alias="certifiedAt")
    created_at: datetime = Field(alias="createdAt")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SynthesisDetailResponse(BaseModel):
    id: int
    name: str
    status: str
    workflow_run_id: int = Field(alias="workflowRunId")
    source_screen_count: int = Field(default=0, alias="sourceScreenCount")
    tier_change_count: int = Field(default=0, alias="tierChangeCount")
    is_certified: int = Field(default=0, alias="isCertified")
    certified_at: Optional[datetime] = Field(default=None, alias="certifiedAt")
    overlap_matrix: Optional[str] = Field(default=None, alias="overlapMatrix")
    thesis_interactions: Optional[str] = Field(default=None, alias="thesisInteractions")
    combined_brief: Optional[str] = Field(default=None, alias="combinedBrief")
    combined_report: Optional[str] = Field(default=None, alias="combinedReport")
    created_at: datetime = Field(alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
```

**Fix — Add to `backend/app/schemas/ist.py`:**

Add `source_refresh_id: Optional[int] = Field(default=None, alias="sourceRefreshId")` to the `ISTClaimResponse` class.

Add refresh response schemas:

```python
class ScreenRefreshListItem(BaseModel):
    id: int
    refresh_number: int = Field(alias="refreshNumber")
    status: str
    content_type: str = Field(alias="contentType")
    new_claims_count: int = Field(default=0, alias="newClaimsCount")
    tier_change_count: int = Field(default=0, alias="tierChangeCount")
    created_at: datetime = Field(alias="createdAt")
    completed_at: Optional[datetime] = Field(default=None, alias="completedAt")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ScreenRefreshDetail(BaseModel):
    id: int
    refresh_number: int = Field(alias="refreshNumber")
    status: str
    content_type: str = Field(alias="contentType")
    delta_content: str = Field(alias="deltaContent")
    new_claims_count: int = Field(default=0, alias="newClaimsCount")
    new_claims: Optional[str] = Field(default=None, alias="newClaims")
    new_source_bias: Optional[str] = Field(default=None, alias="newSourceBias")
    tier_changes: Optional[str] = Field(default=None, alias="tierChanges")
    tier_change_count: int = Field(default=0, alias="tierChangeCount")
    impact_assessment: Optional[str] = Field(default=None, alias="impactAssessment")
    steps_reexecuted: Optional[str] = Field(default=None, alias="stepsReexecuted")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")
    completed_at: Optional[datetime] = Field(default=None, alias="completedAt")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
```

**Fix — Update imports in `ist_synthesis.py` router:**
Change `from app.schemas.ist import ISTSynthesisCreate` to also import from `app.schemas.ist_synthesis`.

**Depends on:** F1

---

## Phase 2: Service Layer Fixes (F4–F8)

These fix behavioral defects in the workflow handlers.

### F4 — Extract `_run_*` Functions from `final_synthesis.py`

**Priority:** CRITICAL
**Files:** `backend/app/services/ist/final_synthesis.py` (1554 lines)

**Problem:** The plan (CC Resolution A2) required extracting core logic from all 5 service files. `final_synthesis.py` was not refactored. The refresh service's `conditional_resynthesis` calls registered handlers directly with `canonical_run_id`, which:
1. Emits SSE events on the original run ID (refresh SSE subscribers miss them)
2. Sets `screen.status = "SYNTHESIZING"` at line 588, violating Resolution B2

**Fix:** For each of the 5 Phase 5 handlers that run Claude or produce artifacts (`handle_master_screen`, `handle_rotation_strategy`, `handle_catalyst_calendar`, `handle_stress_tests`, `handle_report_generation`), extract the core logic into a `_run_*` function with this signature pattern:

```python
async def _run_master_screen(
    db: Session,
    screen: ISTScreen,
    workflow_run_id: int,  # for SSE — allows refresh to pass its own run ID
    *,
    update_screen_status: bool = False,  # default False for safety
) -> dict:
    """Core master screen logic, reusable by IST and IST_REFRESH."""
    if update_screen_status:
        screen.status = "SYNTHESIZING"
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()
    # ... existing Claude call and artifact creation logic ...
```

The existing registered handlers become thin wrappers:

```python
@register_step("IST", "master_screen")
async def handle_master_screen(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    try:
        screen = db.query(ISTScreen).filter(ISTScreen.workflow_run_id == workflow_run_id).first()
        if not screen:
            raise ValueError(f"No IST screen for workflow {workflow_run_id}")
        return await _run_master_screen(db, screen, workflow_run_id, update_screen_status=True)
    finally:
        db.close()
```

Apply the same pattern to: `_run_rotation_strategy`, `_run_catalyst_calendar`, `_run_stress_tests`, `_run_report_generation`.

The `handle_screen_certification` and `handle_hfrt_handoff_generation` handlers do NOT call Claude and can stay as-is, but they also set `screen.status`. Extract `_run_screen_certification` and `_run_hfrt_handoff_generation` with the same `update_screen_status` guard.

**Depends on:** Nothing

---

### F5 — Fix `conditional_resynthesis` in Refresh Service

**Priority:** CRITICAL
**Files:** `backend/app/services/ist/refresh.py` (lines 474–505)

**Problem:** `conditional_resynthesis` calls `handle_master_screen(canonical_run_id)` etc., which emits SSE on the wrong run and mutates screen status.

**Fix:** After F4 is applied, update `conditional_resynthesis` to call the extracted functions:

```python
# Replace lines 483-488 with:
await _run_master_screen(db, screen, workflow_run_id, update_screen_status=False)
await _run_rotation_strategy(db, screen, workflow_run_id, update_screen_status=False)
await _run_catalyst_calendar(db, screen, workflow_run_id, update_screen_status=False)
await _run_stress_tests(db, screen, workflow_run_id, update_screen_status=False)
await _run_report_generation(db, screen, workflow_run_id, update_screen_status=False)
```

Import the `_run_*` functions from `final_synthesis.py`:
```python
from app.services.ist.final_synthesis import (
    _run_master_screen,
    _run_rotation_strategy,
    _run_catalyst_calendar,
    _run_stress_tests,
    _run_report_generation,
)
```

Also fix `handle_refresh_certification` (line 508) — replace `await handle_screen_certification(canonical_run_id)` with `await _run_screen_certification(db, screen, workflow_run_id, update_screen_status=False)`.

**Remove line 491** (`screen.status = "COMPLETED"`) — this is the band-aid that papered over the B2 violation. With `update_screen_status=False`, the status never changes.

**Depends on:** F4

---

### F6 — Fix `_run_source_bias` to Preserve Original Screen Bias

**Priority:** CRITICAL
**Files:** `backend/app/services/ist/content_extraction.py` (lines 205–213)

**Problem:** `_run_source_bias` unconditionally writes `screen.source_bias = bias_summary.model_dump_json()`. During refresh, this permanently overwrites the original screen's bias with the delta content's bias.

**Fix:** Add a `target_refresh` parameter:

```python
async def _run_source_bias(
    db,
    screen: ISTScreen,
    workflow_run_id: int,
    *,
    update_screen_status: bool = True,
    target_refresh: Optional["ISTScreenRefresh"] = None,  # NEW
) -> dict:
    # ... existing Claude call ...

    bias_summary = SourceBiasSummary(
        rating=result.rating,
        notes=result.notes,
        sourceCredibility=result.source_credibility,
        potentialBlindSpots=result.potential_blind_spots,
    )

    if target_refresh is not None:
        # Write to refresh record, not the parent screen
        target_refresh.new_source_bias = bias_summary.model_dump_json()
    else:
        screen.source_bias = bias_summary.model_dump_json()

    screen.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"biasRating": result.rating}
```

**Fix — Update the refresh caller** in `backend/app/services/ist/refresh.py` (`handle_delta_bias_assessment`, ~line 159):

```python
# Pass the refresh object so bias is written there, not to the parent screen
await _run_source_bias(
    db, screen, workflow_run_id,
    update_screen_status=False,
    target_refresh=refresh,
)
```

**Depends on:** F1 (needs `new_source_bias` column)

---

### F7 — Fix `locals()` Sentinel Pattern in Refresh Handlers

**Priority:** HIGH
**Files:** `backend/app/services/ist/refresh.py` (lines 141–143, 169–171, 211–213, 251–254, 500–502)

**Problem:** All refresh handlers use `if "refresh" in locals()` in except blocks, which is fragile and can leave refresh records stuck in PENDING if the exception occurs before `refresh` is assigned.

**Fix:** In every handler, declare sentinels at the top:

```python
refresh = None
screen = None
try:
    refresh = _get_refresh_by_run(db, workflow_run_id)
    screen = _get_refresh_screen(db, refresh)
    # ... rest of handler ...
except Exception as exc:
    if refresh is not None:
        _mark_refresh_failed(db, refresh, screen, exc)
    raise
finally:
    db.close()
```

Apply to all 6 refresh handlers: `handle_delta_extraction`, `handle_delta_bias_assessment`, `handle_delta_sufficiency_gate`, `handle_impact_assessment`, `handle_selective_reanalysis`, `handle_conditional_resynthesis`, `handle_refresh_certification`.

**Depends on:** Nothing

---

### F8 — Add Logging to Refresh and Synthesis Services

**Priority:** HIGH
**Files:**
- `backend/app/services/ist/refresh.py`
- `backend/app/services/ist/synthesis.py`

**Problem:** Both files lack `import logging` and a module-level logger, unlike all other service files.

**Fix:** Add to both files at the top (after existing imports):

```python
import logging
logger = logging.getLogger(__name__)
```

Add `logger.info(...)` at handler entry and `logger.warning(...)` at error-skipping branches.

**Depends on:** Nothing

---

## Phase 3: API Layer Fixes (F9–F11)

### F9 — Fix Variable Shadowing in `create_synthesis`

**Priority:** CRITICAL
**Files:** `backend/app/routers/ist_synthesis.py` (line 169)

**Problem:** The outer `themes: set[str]` (line 111) is overwritten by `themes = extraction.get("themes")` (line 169) inside the source-creation loop. The accumulated set is destroyed.

**Fix:** Rename the inner variable on line 169:

```python
        # Line 168-171: change from:
        if not primary_theme and isinstance(extraction, dict):
            themes = extraction.get("themes")
            if isinstance(themes, list) and themes:
                primary_theme = themes[0]

        # To:
        if not primary_theme and isinstance(extraction, dict):
            raw_themes = extraction.get("themes")
            if isinstance(raw_themes, list) and raw_themes:
                primary_theme = raw_themes[0]
```

**Depends on:** Nothing

---

### F10 — Add Rate Limiter to Refresh Endpoint

**Priority:** HIGH
**Files:** `backend/app/routers/ist.py` (line 432)

**Problem:** `POST /screens/{screen_id}/refresh` creates a workflow run and triggers Claude API calls but has no rate limiter, unlike `create_screen` and `create_synthesis` which both have `@limiter.limit("5/hour")`.

**Fix:** Add the decorator and `Request` parameter:

```python
@router.post("/screens/{screen_id}/refresh", status_code=201)
@limiter.limit("5/hour")
async def create_screen_refresh(
    request: Request,  # ADD THIS
    screen_id: int,
    data: ISTScreenRefreshCreate,
    db: Session = Depends(get_db),
):
```

Ensure `from starlette.requests import Request` is imported (it likely already is).

**Depends on:** Nothing

---

### F11 — Fix `/sources` and `/equities` 404 Behavior + Conftest Limiter Reset

**Priority:** HIGH
**Files:**
- `backend/app/routers/ist_synthesis.py` (lines 328–350, 377–405)
- `backend/tests/conftest.py`

**Problem:**
1. `GET /syntheses/{id}/sources` and `GET /syntheses/{id}/equities` return HTTP 200 with empty list for non-existent synthesis IDs. Every other sub-resource endpoint correctly returns 404.
2. The test conftest doesn't reset the `ist_synthesis` router's rate limiter, which will cause flaky 429s as tests grow.

**Fix — Add existence check to both endpoints:**

```python
# At the top of get_synthesis_sources and get_synthesis_equities:
synthesis = db.query(ISTSynthesis).filter(ISTSynthesis.id == synthesis_id).first()
if not synthesis:
    raise HTTPException(
        status_code=404,
        detail=_error("SYNTHESIS_NOT_FOUND", f"No synthesis with id {synthesis_id}"),
    )
```

**Fix — Update conftest:**

```python
from app.routers import ist as ist_router_mod, workflows as wf_router_mod, ist_synthesis as ist_synth_mod
for mod in [ist_router_mod, wf_router_mod, ist_synth_mod]:
    if hasattr(mod, "limiter"):
        try:
            mod.limiter.reset()
        except Exception:
            pass
```

**Depends on:** Nothing

---

## Phase 4: Frontend Fixes (F12–F16)

### F12 — Gate Refresh Panels on Refresh Count

**Priority:** CRITICAL
**Files:** `frontend/app/screens/[id]/page.tsx` (lines 750–762)

**Problem:** `RefreshHistory` and `RefreshDelta` render unconditionally on every screen detail page, showing empty panels with "No refresh operations yet" even for screens that have never been refreshed.

**Fix:** Wrap the grid in a conditional:

```tsx
{/* Refresh History - only show if screen has been refreshed */}
{(refreshes.length > 0 || (screen && screen.refreshCount > 0)) && (
  <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
    <RefreshHistory
      refreshes={refreshes}
      selectedRefreshId={selectedRefreshId}
      onSelectRefresh={setSelectedRefreshId}
    />
    <RefreshDelta
      detail={selectedRefresh}
      claims={selectedRefreshClaims}
      loading={refreshDetailLoading}
      error={refreshDetailError}
    />
  </div>
)}
```

**Depends on:** Nothing

---

### F13 — Fix Synthesis Detail Page Loading Pattern

**Priority:** CRITICAL
**Files:** `frontend/app/screens/syntheses/[id]/page.tsx` (lines 46–62)

**Problem:** Three sequential `await` calls where workflow + equities could be parallel. Equities fetched unconditionally for in-progress syntheses (guaranteed empty/error).

**Fix:** Replace the `load` function body:

```typescript
const load = useCallback(async () => {
  if (Number.isNaN(synthesisId)) return;
  setLoading(true);
  setError(null);
  try {
    const detail = await getSynthesis(synthesisId);
    setSynthesis(detail);

    const [wf, eq] = await Promise.all([
      getWorkflow(detail.workflowRunId),
      detail.status === "COMPLETED"
        ? getSynthesisEquities(detail.id)
        : Promise.resolve({ equities: [] }),
    ]);
    setWorkflow(wf);
    setEquities(eq.equities);
  } catch (err) {
    setError(err instanceof Error ? err.message : "Failed to load synthesis");
  } finally {
    setLoading(false);
  }
}, [synthesisId]);
```

**Depends on:** Nothing

---

### F14 — Add Idempotency Key to Synthesis Creation

**Priority:** CRITICAL
**Files:** `frontend/app/screens/syntheses/new/page.tsx` (lines 46–50)

**Problem:** The `createSynthesis` call does not include `idempotencyKey`, silently dropping the duplicate-prevention protection mandated by Resolution C2.

**Fix:**

```typescript
async function onSubmit(e: React.FormEvent) {
  e.preventDefault();
  if (!canSubmit) return;
  setSubmitting(true);
  setError(null);
  try {
    const idempotencyKey =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `synth-${Date.now()}`;
    const created = await createSynthesis({
      name: name.trim(),
      screenIds: selectedIds,
      autoAdvance,
      idempotencyKey,
    });
    await advanceWorkflow(created.workflowRunId);
    router.push(`/screens/syntheses/${created.id}`);
  } catch (err) {
    setError(err instanceof Error ? err.message : "Failed to create synthesis");
    setSubmitting(false);
  }
}
```

**Depends on:** Nothing

---

### F15 — Fix Synthesis Tab Labels

**Priority:** HIGH
**Files:** `frontend/app/screens/syntheses/[id]/page.tsx` (lines 176–196)

**Problem:** Tab labels render raw enum strings like "tier-changes" and "interactions" instead of proper display names.

**Fix:** Add a label map and use it in the render:

```typescript
const TAB_LABELS: Record<Tab, string> = {
  report: "Report",
  overlap: "Overlap Matrix",
  interactions: "Thesis Interactions",
  "tier-changes": "Tier Changes",
  equities: "Equities",
  dialectic: "Dialectic",
  handoff: "HFRT Handoff",
};

// In the JSX, replace {t} with {TAB_LABELS[t]}:
<button
  key={t}
  onClick={() => setTab(t)}
  className={cn(
    "px-3 py-2.5 text-sm whitespace-nowrap",
    tab === t ? "text-primary border-b-2 border-primary" : "text-text-secondary hover:text-text-primary"
  )}
>
  {TAB_LABELS[t]}
</button>
```

**Depends on:** Nothing

---

### F16 — Fix Markdown Rendering in `SynthesisReport`

**Priority:** HIGH
**Files:** `frontend/components/ist/synthesis/SynthesisReport.tsx`

**Problem:** Report markdown is rendered as plain text. Raw `##`, `**`, `-` characters are visible to users. The plan says to "reuse `InvestmentThesisReport.tsx` pattern."

**Fix:** Find the markdown rendering approach used in `InvestmentThesisReport.tsx` (likely `react-markdown` or `marked`) and apply the same pattern. Replace:

```tsx
<article className="prose prose-invert max-w-none text-sm whitespace-pre-wrap">
  {report}
</article>
```

With the same markdown renderer used in `InvestmentThesisReport.tsx`. If that component uses `react-markdown`:

```tsx
import ReactMarkdown from "react-markdown";

<article className="prose prose-invert max-w-none text-sm">
  <ReactMarkdown>{report}</ReactMarkdown>
</article>
```

If it uses `dangerouslySetInnerHTML` with `marked`, follow that same pattern. Match what already exists in the codebase.

**Depends on:** Nothing

---

## Dependency Graph

```
F1 ──→ F2
F1 ──→ F3
F1 ──→ F6
F4 ──→ F5

All others are independent.
```

**Recommended execution order:**

```
Batch 1 (parallel):  F1, F4, F7, F8, F9, F10, F11, F12, F13, F14, F15, F16
Batch 2 (after F1):  F2, F3, F6
Batch 3 (after F4):  F5
```

---

## Out of Scope (Deferred to Future Pass)

The following were identified in the review but are intentionally deferred. They do not block correctness.

1. **Synthesis Claude stubs** — `thesis_interactions`, `combined_bottleneck_analysis`, `cross_screen_effects`, `synthesis_dialectic_optimist`, `synthesis_dialectic_pessimist`, `synthesis_final` all use hardcoded heuristics instead of Claude calls. These are functionally incomplete but architecturally wired correctly. Claude integration should be added in a dedicated pass after the critical fixes land, to avoid conflating structural fixes with prompt engineering.

2. **N+1 query in `handle_overlap_matrix`** — Bottleneck names fetched inside a loop. Fix with batch pre-fetch. Low urgency.

3. **RefreshModal ARIA/focus trap** — Accessibility compliance. Should be addressed but not blocking.

4. **`SynthesisListItem` missing `isCertified`** — Frontend type missing certification fields. Minor.

5. **`OverlapMatrix` shows screen IDs not names** — Missing `screenName` in `OverlapAppearance` type.

6. **`SynthesisHandoff` renders raw JSON** — Should reuse `HandoffPanel` pattern.

7. **`update_screen_status` default** — Currently defaults to `True`; should default to `False` for safety. Addressed implicitly in F4/F5/F6 for the new `_run_*` functions, but the existing `_run_content_extraction`, `_run_bottleneck_mapping`, etc. still have `True` as default. Requires a coordinated change across all callers.

8. **Partial unique index for idempotency_key** — Add `WHERE idempotency_key IS NOT NULL` for production correctness. Works on SQLite and PostgreSQL as-is; only matters for MySQL.

9. **`useWorkflowSSE` stale closure reconnect** — Pre-existing issue. `currentStep` in dependency array causes SSE reconnect on every step transition.

---

## Verification

After all fixes are applied, run:

```bash
# Backend
cd backend
source venv/Scripts/activate
alembic upgrade head
pytest tests/integration/test_ist_endpoints.py tests/integration/test_ist_extension_endpoints.py tests/integration/test_dialectic_endpoints.py tests/integration/test_final_synthesis_endpoints.py -q

# Frontend
cd ../frontend
npm run build
```

Both must pass cleanly.
