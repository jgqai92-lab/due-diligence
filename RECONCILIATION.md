# Implementation Reconciliation

## Handoff Reference
- **Source:** `IST_EXTENSION_FIX_PLAN.md`
- **Date:** 2026-02-22

## Summary
Implemented the fix plan end to end across backend and frontend, including refresh delta persistence, reusable final-synthesis core runners, API schema hardening, and synthesis UX corrections. The implementation matches the prescribed fixes with one consistency-focused extension in the synthesis detail UI refresh path.

## Deviations

### Consistent Parallel Fetching on Manual Refresh
- **Plan specified:** Optimize the initial synthesis detail `load` function with parallel workflow/equities fetch and conditional equities call.
- **What was implemented:** Applied the same optimization to both `load` and `refresh` paths in `frontend/app/screens/syntheses/[id]/page.tsx`.
- **Why the plan was suboptimal:** Only fixing initial load leaves manual refresh on the slower, unconditional fetch path.
- **How the change improves the output:** Keeps behavior consistent and avoids unnecessary equities API calls while synthesis is in progress.
- **Files affected:** `frontend/app/screens/syntheses/[id]/page.tsx`

## Plan Followed As-Is
- Added missing refresh delta columns in model + migration:
  - `new_claims_count`, `new_claims`, `new_source_bias`, `tier_changes`, `tier_change_count`
- Hardened migration SQL backfill with `sa.text(...)` and `workflow_run_id IS NOT NULL` guard.
- Added synthesis schema module and router `response_model` usage.
- Added `sourceRefreshId` / `sourceRefreshNumber` support for claim responses.
- Refactored final synthesis handlers into reusable `_run_*` cores with `update_screen_status` gating and wrapper handlers.
- Switched refresh conditional re-synthesis to `_run_*` calls on refresh run IDs.
- Added refresh-level source bias persistence (`target_refresh`) to avoid overwriting parent screen bias.
- Replaced fragile `locals()` exception sentinel checks with explicit `refresh = None`, `screen = None` initialization.
- Added logging scaffolding in refresh/synthesis services.
- Fixed `create_synthesis` variable shadowing (`raw_themes`).
- Added rate limiting to refresh create endpoint.
- Added synthesis existence checks for `/sources` and `/equities` endpoints.
- Added synthesis router limiter reset in test fixture setup.
- Frontend fixes:
  - Refresh panels shown only when refresh data exists on screen detail.
  - Synthesis detail loading made parallel + conditional.
  - Synthesis create now sends `idempotencyKey`.
  - Synthesis tab labels now human-readable.
  - `SynthesisReport` now renders markdown instead of raw markdown text.

## Implementation Notes
- Backend tests passed:
  - `backend/tests/integration/test_ist_endpoints.py`
  - `backend/tests/integration/test_ist_extension_endpoints.py`
  - `backend/tests/integration/test_dialectic_endpoints.py`
  - `backend/tests/integration/test_final_synthesis_endpoints.py`
  - Result: `79 passed`
- Frontend verification passed:
  - `npm run build`
  - Build includes one pre-existing lint warning in `frontend/components/TickerSearchInput.tsx` (`jsx-a11y/role-has-required-aria-props`).
- Migration chain verification:
  - `alembic history` confirms `014 -> 015 (head)` chain.
  - `alembic check` / `alembic upgrade head` against the current local DB failed due pre-existing schema drift (`ist_syntheses` table already exists while revision is behind), not due revision chain breakage.
