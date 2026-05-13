# Financial Due Diligence Application - Progress Tracker

## HFRT Enhancement Plan — 8 Gaps Across 4 Waves

### Status: COMPLETE — All 4 Waves

### Objective
Close 8 quality gaps in the HFRT backend to match IST workflow quality.

---

## Wave Status

| Wave | Gaps | Status | Reviewer |
|------|------|--------|----------|
| Wave 1 | 2, 6 | COMPLETE | Compliance: PASS (516 unit tests pass) |
| Wave 2 | 3, 4, 5 | COMPLETE | Compliance: PASS (516 unit tests pass) |
| Wave 3 | 1 | COMPLETE | Compliance: PASS (516 unit + 172 integration = 688 tests pass) |
| Wave 4 | 7, 8 | COMPLETE | Compliance: PASS (565 unit + 208 integration = 773 tests pass) |

---

## Wave 1: Safety & Prompt Quality (Gaps 2, 6) — COMPLETE

**Started:** 2026-02-27

### Gap 2: Upsert Safety for SEC Filings
- File: `backend/app/services/hfrt/edgar_service.py`
- Status: DONE — upsert by (project_id, filing_type) before inserting; returns updated: True/False

### Gap 6: Anti-Hallucination Prompt Audit
- Files: 7 HFRT service files + 6 sector prompt files
- Status: DONE — all prompts hardened with domain-specific fabrication guards

---

## Wave 2: Invariant Quality & Data Richness (Gaps 3, 4, 5) — COMPLETE

### Gap 3: Market-Cap-Tier-Aware Invariants
- File: `backend/app/services/hfrt/invariant_checker.py`
- Status: DONE — MARKET_CAP_TIER_THRESHOLDS dict, _get_market_cap_tier(), tier-aware INV-04/INV-05, enhanced INV-06

### Gap 4: Template Context Enrichment
- Files: `backend/app/services/hfrt/thesis_synthesizer.py`, `backend/app/services/hfrt/due_diligence.py`
- Status: DONE — _gather_all_templates() pulls SEC filing sections + yfinance snapshot; cache invalidation after fetch

### Gap 5: Coherence Gate Pre-Checks
- File: `backend/app/services/hfrt/thesis_synthesizer.py`
- Status: DONE — 5 server-side pre-checks before Claude call; fails immediately if any fail

---

## Wave 3: External Validation Pipeline (Gap 1) — COMPLETE

### Gap 1: Perplexity-Grounded Claim Validation
- Files: `backend/app/models/hfrt.py` (column), `backend/app/services/hfrt/due_diligence.py` (handler),
         `backend/app/routers/hfrt.py` (endpoint + step list 23→24),
         `backend/app/services/bridge.py` (synced step list 23→24),
         `backend/app/main.py` (startup migration)
- Status: DONE — external_validation step at position 14 in 24-step workflow

---

## Wave 4: Tests & Watchlist (Gaps 7, 8) — COMPLETE

**Completed:** 2026-02-27

### Gap 7: HFRT Test Coverage
- New: `backend/tests/integration/test_hfrt_endpoints.py` (36 tests, 8 classes)
- New: `backend/tests/unit/test_invariant_checker.py` (49 tests: TestMarketCapTier 9, TestDialecticIsolation 8, TestInvariants 32)
- Updated: `backend/tests/conftest.py` — added hfrt_router_mod to rate limiter reset loop
- Status: DONE

### Gap 8: Watchlist Router
- New: `backend/app/routers/watchlist.py` (4 endpoints: GET /api/watchlist, POST /api/watchlist, DELETE /api/watchlist/{ticker}, GET /api/watchlist/{ticker}/summary)
- Updated: `backend/app/main.py` — watchlist router imported and registered
- Status: DONE

---

## Dependencies Introduced

None.

---

## Performance Baselines

| Metric | Wave 1 | Wave 4 Final |
|--------|--------|--------------|
| Unit tests | 516 | 565 (+49) |
| Integration tests | — | 208 |
| Total tests | 516 | 773 |
| Unit test duration | ~42s | ~42s |
| Integration test duration | — | ~119s |
