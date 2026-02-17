# Bug Log — The Skeptical Analyst

Tracks all bugs found, how they were discovered, root cause analysis, fix details, and resolution dates.
Each entry follows a consistent format for future session context.

---

## Format

```
### BUG-XXXX: [Short title]
- **Status**: Open | In Progress | Fixed
- **Severity**: Critical | High | Medium | Low
- **Feature**: [IST | HFRT | Analysis | Portfolio | Alerts | Workflow Engine | UI]
- **Identified**: YYYY-MM-DD
- **Fixed**: YYYY-MM-DD (or N/A)
- **How Discovered**: [Screenshot, user report, test failure, code review, etc.]
- **Symptoms**: What the user sees
- **Root Cause**: Why it happens
- **Fix**: What was changed (files, logic)
- **Files Changed**: List of modified files
- **Regression Risk**: What could break if the fix is wrong
```

---

## Open Bugs

(none)

---

## Fixed Bugs

### BUG-0001: IST workflow fails immediately — timezone-naive vs timezone-aware datetime crash
- **Status**: Fixed
- **Severity**: Critical
- **Feature**: Workflow Engine (affects ALL IST and HFRT workflows)
- **Identified**: 2026-02-13
- **Fixed**: 2026-02-13
- **How Discovered**: User screenshot (`IST ERRORS SNAPSHOT.png`) — created IST screen, advanced workflow, failed at step 1 of 22 (`content_extraction`) with 0 steps completed. DB confirms error: `"can't subtract offset-naive and offset-aware datetimes"`.
- **Symptoms**: Workflow Progress shows "Failed". Step 1 `content_extraction` has red error icon. 0/22 steps complete. Every single workflow run fails identically — no step can ever complete.
- **Root Cause**: In `backend/app/services/workflow_engine.py` `_execute_step()`, the duration calculation subtracts `step.started_at` (timezone-naive after SQLite round-trip) from `step.completed_at` (timezone-aware, freshly created with `datetime.now(timezone.utc)`). SQLite stores datetimes as naive strings — when SQLAlchemy reads `started_at` back after the `db.commit()`, it loses `tzinfo`. The subtraction `aware - naive` raises `TypeError`. This crashed BOTH the success path AND the error path, meaning no step could ever record a duration or complete successfully.
- **Fix**: Added `_ensure_utc()` helper function at line 46 in `workflow_engine.py` that checks `dt.tzinfo is None` and applies `dt.replace(tzinfo=timezone.utc)` if needed. Applied to both the success path (line 352) and error path (line 368) duration calculations: `delta = step.completed_at - _ensure_utc(step.started_at)`.
- **Files Changed**: `backend/app/services/workflow_engine.py`
- **Regression Risk**: Low. `_ensure_utc` is defensive — it only adds tzinfo when missing, and UTC assumption is safe since all datetimes in the system are created with `datetime.now(timezone.utc)`.

### BUG-0002: Working Data sub-tabs show raw JSON errors for incomplete workflow phases
- **Status**: Fixed
- **Severity**: High (upgraded from Medium — affects 6 sub-tabs, not just 1)
- **Feature**: IST / Frontend
- **Identified**: 2026-02-13
- **Fixed**: 2026-02-13
- **How Discovered**: Same screenshot — user clicked "Dialectic" sub-tab for screen 2 (workflow never reached Phase 4). Error: `{"error":{"code":"REVIEW_NOT_FOUND","message":"No optimist review found for screen 2"}}`.
- **Symptoms**: Raw JSON error string displayed in red error banner with "Try again" link. Affects ALL 6 "Group 2" sub-tabs that query single records (Dialectic, Synthesis, Master Screen, Rotation, Catalysts, Stress Tests). The 7 "Group 1" sub-tabs that return empty arrays handle missing data gracefully.
- **Root Cause**: Three interconnected issues:
  1. `handleErrorResponse` JSON-stringified the `body.detail` object instead of extracting nested error messages.
  2. `DialecticView.tsx` 404 detection used string matching that never triggered.
  3. `WORKING_DATA_TABS` defined `minPhase` metadata but never used it — tabs rendered unconditionally regardless of workflow progress.
- **Fix**: Three-layer fix applied:
  1. `frontend/lib/api/ist.ts` — Rewrote `handleErrorResponse` (lines 29-49) with proper extraction chain: checks `body.detail` as string, then `body.detail.error.message`, then `body.detail.message`, falling back to `JSON.stringify` only as last resort.
  2. `frontend/app/screens/[id]/page.tsx` — Wired `effectivePhase` (line 132) to tab rendering (line 482): `const isDisabled = effectivePhase < tab.minPhase`. Disabled tabs show `cursor-not-allowed` styling and tooltip "Available after Phase X".
  3. `frontend/components/ist/DialecticView.tsx` — Rewrote data fetching (lines 518-564) to use `Promise.allSettled` with per-resource 404 tolerance. Each of the 3 fetches (optimist, pessimist, synthesis) independently handles 404 as empty state. Only surfaces errors when all three fail and at least one wasn't a 404.
- **Files Changed**: `frontend/lib/api/ist.ts`, `frontend/app/screens/[id]/page.tsx`, `frontend/components/ist/DialecticView.tsx`
- **Regression Risk**: Low. Error message extraction is now more robust with a proper cascade. Tab gating uses the `minPhase` metadata that was always defined but never consumed. DialecticView's `Promise.allSettled` pattern is more resilient than the previous approach.

### BUG-0004: Workflow stuck after Phase 1 — advance re-pauses immediately at phase boundary
- **Status**: Fixed
- **Severity**: Critical
- **Feature**: Workflow Engine
- **Identified**: 2026-02-13
- **Fixed**: 2026-02-13
- **How Discovered**: User created IST screen "AI Security", workflow completed Phase 1 (content_extraction + source_bias_assessment) and paused for approval. Pressing the Advance button caused the screen to flicker but nothing happened — workflow stayed PAUSED at phase 1 with 2/22 steps. Curl confirmed `POST /api/workflows/9/advance` returned 202 but status immediately reverted to PAUSED.
- **Symptoms**: Advance button appears to do nothing. Screen flickers for a nanosecond. Workflow remains PAUSED at the same phase indefinitely. Every advance attempt re-pauses instantly. No error messages — the workflow silently refuses to progress.
- **Root Cause**: In `backend/app/services/workflow_engine.py` `_run_workflow()`, line 215 sets `current_phase = run.current_phase` (the last completed phase, e.g. 1). The phase boundary check at line 225 (`if step.phase > current_phase and current_phase > 0`) fires immediately for the first pending step (phase 2 > phase 1), re-pausing the workflow before executing any steps. On every resume, the same check re-triggers because `current_phase` is always initialized to the last completed phase, never the approved next phase.
- **Fix**: Added logic at line 215 to detect when the first pending step's phase exceeds `run.current_phase` (i.e., we're resuming into a new phase). In that case, initialize `current_phase` to the first pending step's phase so the boundary check doesn't re-trigger for the already-approved transition.
- **Files Changed**: `backend/app/services/workflow_engine.py`
- **Regression Risk**: Low. The fix only changes the initial value of the local `current_phase` variable when resuming. The phase boundary check still fires normally for subsequent phase transitions within the same run. New workflows starting from PENDING are unaffected (they start at phase 0→1 which skips the check via `current_phase > 0`).

### BUG-0003: New backend endpoints not served — stale uvicorn processes hold port 8000
- **Status**: Fixed
- **Severity**: Critical
- **Feature**: Workflow Engine / Backend
- **Identified**: 2026-02-13
- **Fixed**: 2026-02-13
- **How Discovered**: After adding Delete/Inputs/Rerun endpoints for IST and HFRT, user tried to create and run a new screen. Browser reported 404 on `GET /api/ist/screens/2/inputs` and 405 on `GET /api/ist/screens/1`. OpenAPI spec confirmed the new routes were missing from the running server.
- **Symptoms**: New API endpoints return 404 (default FastAPI "Not Found") or 405 (Method Not Allowed). The `--reload` flag on uvicorn did not pick up changes. Frontend actions relying on new endpoints (Delete, View Inputs, Rerun) fail silently or show error banners.
- **Root Cause**: Multiple zombie uvicorn processes (6 PIDs) were bound to port 8000 simultaneously. When the server was "restarted", a new process started but the old stale process continued to accept requests with the old code. `taskkill /F /PID` failed to kill some processes because they were being respawned by parent bash shells from prior Claude Code sessions. Only `taskkill //F //IM python.exe` (killing all Python processes) freed the port.
- **Fix**: Killed all Python processes via `taskkill //F //IM python.exe`, then started a single clean uvicorn instance. Verified via `netstat -ano` that only one process held port 8000, and via OpenAPI spec that all 4 new routes (`/inputs` and `/rerun` for both IST and HFRT) were registered.
- **Files Changed**: None (operational fix, not code fix)
- **Regression Risk**: Low. Future restarts should verify port is clear. Running multiple uvicorn instances on the same port is a recurring risk when Claude Code spawns background bash tasks.
