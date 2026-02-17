# Database Schema

## Database: SQLite 3 (Local File)

**File Location:** `./data/skeptical_analyst.db`
**ORM:** SQLAlchemy 2.0 (Python)
**Migrations:** Alembic

SQLite is chosen for zero cost, zero configuration, and single-user suitability. WAL mode enabled for better read/write concurrency. Background workflow tasks use per-step session lifecycle to avoid holding locks during Claude API calls.

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=5000;
```

---

## Existing Tables (Waves 1-5)

### cached_financials
Caches raw yfinance data to minimize API calls and enable offline access for previously-analyzed tickers.

```sql
CREATE TABLE cached_financials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK(data_type IN ('financials', 'balance_sheet', 'cashflow', 'quarterly_financials', 'quarterly_balance_sheet', 'quarterly_cashflow', 'info')),
    raw_json TEXT NOT NULL,  -- JSON string of yfinance response
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,  -- fetched_at + 24 hours
    UNIQUE(ticker, data_type)
);

CREATE INDEX idx_cache_lookup ON cached_financials(ticker, data_type, expires_at);
CREATE INDEX idx_cache_expiry ON cached_financials(expires_at);
```

---

### analysis_reports
Stores completed forensic analysis results. Append-only for audit trail -- reports are never updated, only new ones created.

```sql
CREATE TABLE analysis_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    company_name TEXT,
    sector TEXT,
    beneish_m_score TEXT,       -- JSON: composite + 8 components + citations
    altman_z_score TEXT,         -- JSON: standard score + zone + components + citations
    altman_z_score_saas TEXT,    -- JSON: SaaS-modified variant
    rule_of_40 TEXT,             -- JSON: score + revenue_growth + fcf_margin + citations
    magic_number TEXT,           -- JSON: score + net_new_arr + sm_spend + citations
    llm_report TEXT,             -- Full markdown report from Claude
    bear_case TEXT,              -- Extracted bear case section
    red_flags TEXT,              -- JSON array of flagged items
    data_sources TEXT,           -- JSON: provider, periods, fetchedAt
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reports_ticker ON analysis_reports(ticker, created_at DESC);
```

---

### holdings
Portfolio holdings with cost basis for P&L tracking.

```sql
CREATE TABLE holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    shares REAL NOT NULL CHECK(shares > 0),
    cost_basis REAL NOT NULL CHECK(cost_basis > 0),  -- Price per share at purchase
    purchase_date TEXT NOT NULL,  -- ISO 8601 date string
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_holdings_ticker ON holdings(ticker);
```

---

### alerts
System-generated forensic deterioration alerts from watchdog scans.

```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    holding_id INTEGER REFERENCES holdings(id) ON DELETE SET NULL,
    ticker TEXT NOT NULL,
    alert_type TEXT NOT NULL CHECK(alert_type IN ('m_score_warning', 'z_score_distress', 'z_score_zone_change', 'rule_of_40_fail', 'magic_number_low', 'sentiment_divergence')),
    severity TEXT NOT NULL CHECK(severity IN ('info', 'warning', 'critical')),
    message TEXT NOT NULL,
    previous_value REAL,
    current_value REAL,
    details TEXT,  -- JSON for additional context
    is_dismissed INTEGER NOT NULL DEFAULT 0,  -- SQLite boolean (0/1)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alerts_active ON alerts(is_dismissed, created_at DESC);
CREATE INDEX idx_alerts_ticker ON alerts(ticker, created_at DESC);
```

---

### watchlist
Optional watchlist for tickers not in portfolio but worth monitoring.

```sql
CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL UNIQUE,
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

### alert_settings
User preferences for alert thresholds and notification types.

```sql
CREATE TABLE alert_settings (
    id INTEGER PRIMARY KEY CHECK(id = 1),  -- Single row, single user
    enable_z_score_alerts INTEGER NOT NULL DEFAULT 1,
    enable_m_score_alerts INTEGER NOT NULL DEFAULT 1,
    enable_rule_of_40_alerts INTEGER NOT NULL DEFAULT 1,
    enable_magic_number_alerts INTEGER NOT NULL DEFAULT 1,
    z_score_threshold REAL NOT NULL DEFAULT 2.99,
    m_score_threshold REAL NOT NULL DEFAULT -1.78,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Insert default settings row
INSERT INTO alert_settings (id) VALUES (1);
```

---

## New Tables: Workflow Engine (Migration 004)

### workflow_runs
Orchestration state for any workflow (IST, HFRT, or future types). Each row represents a single end-to-end workflow execution.

```sql
CREATE TABLE workflow_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_type TEXT NOT NULL CHECK(workflow_type IN ('IST', 'HFRT')),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'RUNNING', 'PAUSED', 'COMPLETED', 'FAILED', 'CANCELLED', 'CANCELLING', 'RETRYING')),
    current_phase INTEGER NOT NULL DEFAULT 0,
    current_phase_name TEXT,
    config TEXT,              -- JSON: autoAdvance, claudeModel, timeoutPerStep, etc.
    error_message TEXT,       -- Populated on FAILED status
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_workflow_runs_type ON workflow_runs(workflow_type, status);
CREATE INDEX idx_workflow_runs_status ON workflow_runs(status, created_at DESC);
CREATE INDEX idx_workflow_runs_created ON workflow_runs(created_at DESC);
```

**Status State Machine:**
```
PENDING -> RUNNING -> PAUSED -> RUNNING -> COMPLETED
                   -> FAILED
                   -> CANCELLING -> CANCELLED
           RUNNING -> RETRYING -> RUNNING
```

---

### workflow_steps
Individual step execution records within a workflow run. Each row tracks the status, timing, inputs, and outputs of a single workflow step.

```sql
CREATE TABLE workflow_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_run_id INTEGER NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    step_name TEXT NOT NULL,
    phase INTEGER NOT NULL,
    phase_name TEXT NOT NULL,
    step_order INTEGER NOT NULL,            -- Execution order within the workflow
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED')),
    input_data TEXT,                         -- JSON: serialized input for the step
    output_data TEXT,                        -- JSON: serialized output from the step
    error_message TEXT,                      -- Populated on FAILED status
    retry_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,                     -- Computed: completed_at - started_at in milliseconds
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_workflow_steps_run ON workflow_steps(workflow_run_id, step_order);
CREATE INDEX idx_workflow_steps_status ON workflow_steps(workflow_run_id, status);
CREATE UNIQUE INDEX idx_workflow_steps_unique ON workflow_steps(workflow_run_id, step_name);
```

**Relationships:**
- `workflow_steps.workflow_run_id` -> `workflow_runs.id` (many-to-one, CASCADE delete)

---

## New Tables: IST Screening (Migration 005)

### ist_screens
Screen-level metadata for IST investment screens. Each row represents one complete screening exercise. Links to a workflow_run for orchestration.

```sql
CREATE TABLE ist_screens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_run_id INTEGER NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'EXTRACTING', 'ANALYZING', 'SCANNING', 'DIALECTIC', 'SYNTHESIZING', 'COMPLETED', 'FAILED')),
    content_type TEXT NOT NULL DEFAULT 'text' CHECK(content_type IN ('podcast_transcript', 'article', 'earnings_call', 'research_note', 'text')),
    raw_content TEXT NOT NULL,                -- Original user-pasted content
    screening_brief TEXT,                     -- JSON: hypothesis, constraints, frameworks, contentType
    content_extraction TEXT,                  -- JSON: summary stats (claim counts, bias assessment)
    source_bias TEXT,                         -- JSON: bias rating, notes, source credibility
    is_certified INTEGER NOT NULL DEFAULT 0,  -- SQLite boolean: screen has passed all gates
    certified_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ist_screens_workflow ON ist_screens(workflow_run_id);
CREATE INDEX idx_ist_screens_status ON ist_screens(status, created_at DESC);
CREATE INDEX idx_ist_screens_created ON ist_screens(created_at DESC);
```

**Relationships:**
- `ist_screens.workflow_run_id` -> `workflow_runs.id` (one-to-one)

---

### ist_claims
Individual claims extracted from source content. Each claim is a discrete, verifiable assertion with metadata for tracking provenance and validation status.

```sql
CREATE TABLE ist_claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL REFERENCES ist_screens(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    source_citation TEXT NOT NULL,             -- Where in the source content this came from
    quantitative_anchor TEXT,                  -- Numeric data point (e.g., "330K GPUs per GW")
    temporal_marker TEXT,                      -- Time reference (e.g., "2025-2027")
    bottleneck_name TEXT,                      -- Which bottleneck this claim supports (nullable until Phase 2)
    confidence REAL CHECK(confidence >= 0 AND confidence <= 1),
    is_validated INTEGER NOT NULL DEFAULT 0,   -- SQLite boolean
    validation_verdict TEXT CHECK(validation_verdict IN ('confirmed', 'partially_confirmed', 'contradicted', 'unvalidatable')),
    validation_source TEXT,                    -- Source of external validation
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ist_claims_screen ON ist_claims(screen_id);
CREATE INDEX idx_ist_claims_bottleneck ON ist_claims(screen_id, bottleneck_name);
CREATE INDEX idx_ist_claims_validated ON ist_claims(screen_id, is_validated);
```

**Relationships:**
- `ist_claims.screen_id` -> `ist_screens.id` (many-to-one, CASCADE delete)

---

### ist_bottlenecks
Temporal bottleneck records representing supply/demand constraints identified in the thematic analysis phase.

```sql
CREATE TABLE ist_bottlenecks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL REFERENCES ist_screens(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    phase INTEGER NOT NULL CHECK(phase IN (1, 2, 3, 0)),  -- 0 = cross-cutting
    phase_label TEXT NOT NULL,                 -- "Near-term (0-18 months)", "Mid-term", "Secular", "Cross-cutting"
    description TEXT NOT NULL,
    quantitative_evidence TEXT,                -- Key numbers supporting this bottleneck
    temporal_marker TEXT,                      -- Time range for this bottleneck
    resolution_trigger TEXT,                   -- What would resolve/diminish this bottleneck
    causal_parent_id INTEGER REFERENCES ist_bottlenecks(id) ON DELETE SET NULL,  -- For causal chains
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ist_bottlenecks_screen ON ist_bottlenecks(screen_id, phase);
CREATE INDEX idx_ist_bottlenecks_parent ON ist_bottlenecks(causal_parent_id);
```

**Relationships:**
- `ist_bottlenecks.screen_id` -> `ist_screens.id` (many-to-one, CASCADE delete)
- `ist_bottlenecks.causal_parent_id` -> `ist_bottlenecks.id` (self-referential, SET NULL)

---

### ist_demand_models
Quantitative demand models derived from bottleneck analysis. Each model quantifies the TAM/demand opportunity for a specific bottleneck.

```sql
CREATE TABLE ist_demand_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL REFERENCES ist_screens(id) ON DELETE CASCADE,
    bottleneck_id INTEGER NOT NULL REFERENCES ist_bottlenecks(id) ON DELETE CASCADE,
    formula TEXT NOT NULL,                    -- Human-readable demand formula
    base_case TEXT NOT NULL,                  -- JSON: { demand, tam, assumptions }
    bull_case TEXT NOT NULL,                  -- JSON: { demand, tam, assumptions }
    bear_case TEXT NOT NULL,                  -- JSON: { demand, tam, assumptions }
    sensitivity_table TEXT,                   -- JSON array: [{ variable, low, base, high, tamImpact }]
    multiplier_chain TEXT,                    -- Upstream/downstream multiplier description
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ist_demand_models_screen ON ist_demand_models(screen_id);
CREATE INDEX idx_ist_demand_models_bottleneck ON ist_demand_models(bottleneck_id);
```

**Relationships:**
- `ist_demand_models.screen_id` -> `ist_screens.id` (many-to-one, CASCADE delete)
- `ist_demand_models.bottleneck_id` -> `ist_bottlenecks.id` (many-to-one, CASCADE delete)

---

### ist_validations
External validation records from Claude's web_search tool. Each record represents the validation result for one claim.

```sql
CREATE TABLE ist_validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL REFERENCES ist_screens(id) ON DELETE CASCADE,
    claim_id INTEGER NOT NULL REFERENCES ist_claims(id) ON DELETE CASCADE,
    verdict TEXT NOT NULL CHECK(verdict IN ('confirmed', 'partially_confirmed', 'contradicted', 'unvalidatable')),
    confidence REAL CHECK(confidence >= 0 AND confidence <= 1),
    evidence TEXT NOT NULL,                   -- Summary of corroborating/contradicting evidence
    sources TEXT NOT NULL,                    -- JSON array: [{ url, title }]
    search_queries TEXT,                      -- JSON array: queries used by Claude web_search
    validated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ist_validations_screen ON ist_validations(screen_id);
CREATE INDEX idx_ist_validations_claim ON ist_validations(claim_id);
CREATE INDEX idx_ist_validations_verdict ON ist_validations(screen_id, verdict);
```

**Relationships:**
- `ist_validations.screen_id` -> `ist_screens.id` (many-to-one, CASCADE delete)
- `ist_validations.claim_id` -> `ist_claims.id` (one-to-one, CASCADE delete)

---

### ist_equity_candidates
Company candidates identified during equity scanning with scarcity scores, moat evidence, and tier assignments.

```sql
CREATE TABLE ist_equity_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL REFERENCES ist_screens(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    company_name TEXT NOT NULL,
    bottleneck_id INTEGER REFERENCES ist_bottlenecks(id) ON DELETE SET NULL,
    scarcity_score TEXT NOT NULL,              -- JSON: { overall, dimensions: { supplyConstraint, demandVisibility, substitutionDifficulty, pricingPower, temporalUrgency } }
    moat_type TEXT,                            -- e.g., "Scale + IP + Ecosystem"
    moat_evidence TEXT,                        -- Narrative justification
    catalyst TEXT,                             -- Near-term catalyst description
    tier INTEGER NOT NULL CHECK(tier IN (1, 2, 3)),
    tier_rationale TEXT,                       -- Why this tier was assigned
    phase INTEGER,                             -- Which bottleneck phase (1, 2, 3)
    conviction TEXT CHECK(conviction IN ('HIGH', 'MEDIUM', 'LOW')),
    price_at_screen REAL,                      -- Stock price at time of screening
    pe_ratio REAL,
    market_cap REAL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ist_equity_screen ON ist_equity_candidates(screen_id, tier);
CREATE INDEX idx_ist_equity_ticker ON ist_equity_candidates(ticker);
CREATE INDEX idx_ist_equity_bottleneck ON ist_equity_candidates(bottleneck_id);
CREATE UNIQUE INDEX idx_ist_equity_unique ON ist_equity_candidates(screen_id, ticker);
```

**Relationships:**
- `ist_equity_candidates.screen_id` -> `ist_screens.id` (many-to-one, CASCADE delete)
- `ist_equity_candidates.bottleneck_id` -> `ist_bottlenecks.id` (many-to-one, SET NULL)

---

### ist_effects_chains
Multi-order effects chains mapping downstream impacts from primary theses.

```sql
CREATE TABLE ist_effects_chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL REFERENCES ist_screens(id) ON DELETE CASCADE,
    thesis TEXT NOT NULL,                     -- The primary thesis being extended
    effect_order INTEGER NOT NULL CHECK(effect_order IN (1, 2, 3)),
    effect_description TEXT NOT NULL,         -- What the nth-order effect is
    equity_candidate_id INTEGER REFERENCES ist_equity_candidates(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ist_effects_screen ON ist_effects_chains(screen_id, effect_order);
CREATE INDEX idx_ist_effects_candidate ON ist_effects_chains(equity_candidate_id);
```

**Relationships:**
- `ist_effects_chains.screen_id` -> `ist_screens.id` (many-to-one, CASCADE delete)
- `ist_effects_chains.equity_candidate_id` -> `ist_equity_candidates.id` (many-to-one, SET NULL)

---

### ist_dialectic_reviews
Dialectic review records (optimist, pessimist, synthesis). Isolation is enforced at the application layer: optimist and pessimist are generated from independent Claude API calls.

```sql
CREATE TABLE ist_dialectic_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL REFERENCES ist_screens(id) ON DELETE CASCADE,
    side TEXT NOT NULL CHECK(side IN ('OPTIMIST', 'PESSIMIST', 'SYNTHESIS')),
    content TEXT NOT NULL,                    -- JSON: { narrative, keyArguments, tierAdjustments, convictionLevel, riskDiscount }
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ist_dialectic_screen ON ist_dialectic_reviews(screen_id, side);
CREATE UNIQUE INDEX idx_ist_dialectic_unique ON ist_dialectic_reviews(screen_id, side);
```

**Relationships:**
- `ist_dialectic_reviews.screen_id` -> `ist_screens.id` (many-to-one, CASCADE delete)

**Constraint:** At most one review per (screen_id, side) combination. Unique index enforces this.

---

### ist_master_screens
Final ranked equity output after all phases complete and invariants pass.

```sql
CREATE TABLE ist_master_screens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL REFERENCES ist_screens(id) ON DELETE CASCADE,
    ranked_equities TEXT NOT NULL,            -- JSON array: [{ rank, ticker, companyName, tier, scarcityScore, convictionScore, pillar, catalyst, priceAtScreen, peRatio, marketCap }]
    invariant_compliance TEXT NOT NULL,       -- JSON: { allPassed, checkedAt, results: [...] }
    total_equities INTEGER NOT NULL,
    tier1_count INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_ist_master_screen ON ist_master_screens(screen_id);
```

**Relationships:**
- `ist_master_screens.screen_id` -> `ist_screens.id` (one-to-one, CASCADE delete)

---

### ist_rotation_strategies
Phase-based portfolio allocation strategies with rotation triggers and risk limits.

```sql
CREATE TABLE ist_rotation_strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL REFERENCES ist_screens(id) ON DELETE CASCADE,
    phase_allocations TEXT NOT NULL,          -- JSON array: [{ phase, phaseLabel, allocationPercent, tickers, rationale }]
    rotation_triggers TEXT NOT NULL,          -- JSON array: [{ trigger, action, monitorMetric }]
    risk_limits TEXT NOT NULL,                -- JSON: { maxSingleName, maxSinglePillar, maxTier3Allocation }
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_ist_rotation_screen ON ist_rotation_strategies(screen_id);
```

**Relationships:**
- `ist_rotation_strategies.screen_id` -> `ist_screens.id` (one-to-one, CASCADE delete)

---

### ist_catalyst_calendars
Dated catalyst events associated with the screen's equity candidates.

```sql
CREATE TABLE ist_catalyst_calendars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL REFERENCES ist_screens(id) ON DELETE CASCADE,
    catalysts TEXT NOT NULL,                  -- JSON array: [{ date, dateType, event, tickers, expectedImpact, pillar, importance }]
    total_catalysts INTEGER NOT NULL,
    next_catalyst_date TEXT,                  -- ISO 8601 date of nearest upcoming catalyst
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_ist_catalyst_screen ON ist_catalyst_calendars(screen_id);
```

**Relationships:**
- `ist_catalyst_calendars.screen_id` -> `ist_screens.id` (one-to-one, CASCADE delete)

---

### ist_stress_tests
Stress test results at both framework level and individual equity level.

```sql
CREATE TABLE ist_stress_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL REFERENCES ist_screens(id) ON DELETE CASCADE,
    framework_tests TEXT NOT NULL,            -- JSON array: [{ framework, scenario, impact, survivorTickers, casualtyTickers }]
    name_tests TEXT NOT NULL,                 -- JSON array: [{ ticker, companyName, scenarios: [{ scenario, impactSeverity, survivalScore }], overallSurvivalScore }]
    survival_scores TEXT NOT NULL,            -- JSON: { averageTier1, averageTier2, lowestSurvivor: { ticker, score } }
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_ist_stress_screen ON ist_stress_tests(screen_id);
```

**Relationships:**
- `ist_stress_tests.screen_id` -> `ist_screens.id` (one-to-one, CASCADE delete)

---

### ist_reports
Investment Thesis Report -- the primary deliverable of the IST pipeline. Contains the full markdown report synthesizing all analysis phases.

```sql
CREATE TABLE ist_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_id INTEGER NOT NULL REFERENCES ist_screens(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,                    -- Full markdown report (may be 5000-15000 words)
    metadata TEXT NOT NULL,                   -- JSON: { pillarCount, equityCount, tier1Count, tier2Count, tier3Count, wordCount, model }
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_ist_report_screen ON ist_reports(screen_id);
```

**Relationships:**
- `ist_reports.screen_id` -> `ist_screens.id` (one-to-one, CASCADE delete)

---

## Entity Relationship Diagram

```
EXISTING TABLES (unchanged):

+----------------------+
|  cached_financials   |
|----------------------|
| id (PK)              |
| ticker               |
| data_type            |
| raw_json             |
| fetched_at           |
| expires_at           |
+----------------------+

+----------------------+
|  analysis_reports    |
|----------------------|
| id (PK)              |
| ticker               |
| beneish_m_score (J)  |
| altman_z_score (J)   |
| rule_of_40 (J)       |
| magic_number (J)     |
| llm_report           |
| bear_case            |
| red_flags (J)        |
| created_at           |
+----------------------+

+----------------------+       +----------------------+
|  holdings            |       |  alerts              |
|----------------------|       |----------------------|
| id (PK)              |<------| holding_id (FK,NULL) |
| ticker               |       | id (PK)              |
| shares               |       | ticker               |
| cost_basis           |       | alert_type           |
| purchase_date        |       | severity             |
| notes                |       | message              |
| created_at           |       | is_dismissed         |
| updated_at           |       | created_at           |
+----------------------+       +----------------------+

+----------------------+       +----------------------+
|  watchlist           |       |  alert_settings      |
|----------------------|       |----------------------|
| id (PK)              |       | id (PK, always 1)    |
| ticker (UNIQUE)      |       | enable_*_alerts      |
| added_at             |       | *_threshold          |
+----------------------+       | updated_at           |
                               +----------------------+


NEW TABLES: WORKFLOW ENGINE (Migration 004)

+---------------------------+
|  workflow_runs            |
|---------------------------|
| id (PK)                   |
| workflow_type (IST/HFRT)  |
| name                      |
| status (8 states)         |
| current_phase             |
| current_phase_name        |
| config (J)                |
| error_message             |
| started_at                |
| completed_at              |
| created_at                |
| updated_at                |
+-------------+-------------+
              |
              | 1:N
              |
+-------------+-------------+
|  workflow_steps            |
|----------------------------|
| id (PK)                    |
| workflow_run_id (FK) ------+
| step_name                  |
| phase                      |
| phase_name                 |
| step_order                 |
| status (5 states)          |
| input_data (J)             |
| output_data (J)            |
| error_message              |
| retry_count                |
| started_at                 |
| completed_at               |
| duration_ms                |
| created_at                 |
+----------------------------+


NEW TABLES: IST SCREENING (Migration 005)

+---------------------------+         +---------------------------+
|  workflow_runs            |         |  ist_screens              |
|  (from Migration 004)     |         |---------------------------|
|                           |    1:1  | id (PK)                   |
|  id (PK) +---------------+-------->| workflow_run_id (FK)       |
|                           |         | name                      |
+---------------------------+         | status (8 states)         |
                                      | content_type              |
                                      | raw_content               |
                                      | screening_brief (J)       |
                                      | content_extraction (J)    |
                                      | source_bias (J)           |
                                      | is_certified              |
                                      | certified_at              |
                                      | created_at                |
                                      | updated_at                |
                                      +--------+------------------+
                                               |
          +------------------------------------+------------------------------------+
          |                    |                |                |                   |
          | 1:N               | 1:N            | 1:N            | 1:N               |
          v                   v                v                v                   |
+-----------------+  +----------------+  +--------------+  +------------------+     |
| ist_claims      |  | ist_bottlenecks|  | ist_equity_  |  | ist_effects_     |     |
|-----------------|  |----------------|  | candidates   |  | chains           |     |
| id (PK)         |  | id (PK)        |  |--------------|  |------------------|     |
| screen_id (FK)  |  | screen_id (FK) |  | id (PK)      |  | id (PK)          |     |
| claim_text      |  | name           |  | screen_id(FK)|  | screen_id (FK)   |     |
| source_citation |  | phase (1/2/3/0)|  | ticker       |  | thesis           |     |
| quant_anchor    |  | phase_label    |  | company_name |  | effect_order     |     |
| temporal_marker |  | description    |  | bottleneck_id|  | effect_desc      |     |
| bottleneck_name |  | quant_evidence |  |   (FK) ------+->| equity_cand_id   |     |
| confidence      |  | temporal_marker|  | scarcity (J) |  |   (FK) ----------+---->|
| is_validated    |  | resolution_trig|  | moat_type    |  | created_at       |     |
| valid_verdict   |  | causal_parent  |  | catalyst     |  +------------------+     |
| valid_source    |  |   (self FK) ---+->| tier (1/2/3) |                           |
| created_at      |  | created_at     |  | conviction   |                           |
+---------+-------+  +--------+-------+  | price_at_scr |                           |
          |                   |           | pe_ratio     |                           |
          | 1:1               | 1:N       | market_cap   |                           |
          v                   v           | created_at   |                           |
+-----------------+  +----------------+   +--------------+                           |
| ist_validations |  | ist_demand_    |                                              |
|-----------------|  | models         |   1:N from ist_screens                       |
| id (PK)         |  |----------------|   +---+---+---+---+---+                      |
| screen_id (FK)  |  | id (PK)        |   |   |   |   |   |   |                      |
| claim_id (FK) --+->| screen_id (FK) |   v   v   v   v   v   v                      |
| verdict         |  | bottleneck_id  |                                              |
| confidence      |  |   (FK) --------+-> +------------------+ +------------------+  |
| evidence        |  | formula        |   | ist_dialectic_   | | ist_master_      |  |
| sources (J)     |  | base_case (J)  |   | reviews          | | screens          |  |
| search_queries  |  | bull_case (J)  |   |------------------| |------------------|  |
| validated_at    |  | bear_case (J)  |   | id (PK)          | | id (PK)          |  |
+-----------------+  | sensitivity (J)|   | screen_id (FK)   | | screen_id (FK)   |  |
                     | multiplier     |   | side (OPT/PES/SY)| | ranked_equities  |  |
                     | created_at     |   | content (J)      | | invariant_comp   |  |
                     +----------------+   | created_at       | | total_equities   |  |
                                          +------------------+ | tier1_count      |  |
                                                               | created_at       |  |
                                          +------------------+ +------------------+  |
                                          | ist_rotation_    |                       |
                                          | strategies       | +------------------+  |
                                          |------------------| | ist_catalyst_    |  |
                                          | id (PK)          | | calendars        |  |
                                          | screen_id (FK)   | |------------------|  |
                                          | phase_alloc (J)  | | id (PK)          |  |
                                          | rotation_trig (J)| | screen_id (FK)   |  |
                                          | risk_limits (J)  | | catalysts (J)    |  |
                                          | created_at       | | total_catalysts  |  |
                                          +------------------+ | next_catalyst    |  |
                                                               | created_at       |  |
                                          +------------------+ +------------------+  |
                                          | ist_stress_tests |                       |
                                          |------------------| +------------------+  |
                                          | id (PK)          | | ist_reports      |  |
                                          | screen_id (FK)   | |------------------|  |
                                          | framework_tests  | | id (PK)          |  |
                                          | name_tests (J)   | | screen_id (FK)   |  |
                                          | survival_scores  | | title            |  |
                                          | created_at       | | content (TEXT)   |  |
                                          +------------------+ | metadata (J)     |  |
                                                               | created_at       |  |
                                                               +------------------+  |
```

## Migration Strategy

### Existing Migrations

#### Migration 001: create_tables (Existing)
Creates the original 6 tables: `cached_financials`, `analysis_reports`, `holdings`, `alerts`, `watchlist`, `alert_settings`.

#### Migration 002: add_comprehensive_analysis (Existing)
Adds comprehensive analysis columns to `analysis_reports`.

#### Migration 003: add_general_screener (Existing)
Adds general screener support.

### New Migrations

#### Migration 004: workflow_engine
Creates the 2 workflow engine tables:
- `workflow_runs` with indexes on type, status, and created_at
- `workflow_steps` with indexes on run_id, status, and unique constraint on (run_id, step_name)

```bash
cd backend
alembic revision --autogenerate -m "004_workflow_engine"
alembic upgrade head
```

#### Migration 005: ist_tables
Creates all 13 IST tables:
- `ist_screens`
- `ist_claims`
- `ist_bottlenecks`
- `ist_demand_models`
- `ist_validations`
- `ist_equity_candidates`
- `ist_effects_chains`
- `ist_dialectic_reviews`
- `ist_master_screens`
- `ist_rotation_strategies`
- `ist_catalyst_calendars`
- `ist_stress_tests`
- `ist_reports`

```bash
cd backend
alembic revision --autogenerate -m "005_ist_tables"
alembic upgrade head
```

**Important:** Tables are also auto-created via `Base.metadata.create_all(bind=engine)` in the FastAPI lifespan handler (existing pattern). Alembic migrations are the authoritative schema source; `create_all` is a convenience fallback.

### Data Lifecycle

- **Cache eviction:** Rows in `cached_financials` where `expires_at < NOW()` are purged on each fetch attempt or via periodic cleanup.
- **Report retention:** All reports kept indefinitely (append-only audit trail).
- **Alert cleanup:** Dismissed alerts older than 90 days can be purged.
- **Workflow retention:** Completed and failed workflow_runs and their steps are retained indefinitely for audit trail. Cancelled workflows may be purged after 30 days.
- **IST screen retention:** All IST screens and their child records are retained indefinitely. The Investment Thesis Report is the primary deliverable and must never be auto-purged.

### Backup Strategy
- SQLite database is a single file: `./data/skeptical_analyst.db`
- Backup via file copy: `cp skeptical_analyst.db skeptical_analyst.backup.db`
- No cloud backup needed for single-user local application
- **Recommendation:** Back up before running new Alembic migrations (004, 005)

## Performance Considerations

- **WAL mode** provides concurrent reads during writes
- **busy_timeout=5000** prevents immediate `SQLITE_BUSY` errors during brief write contention from background tasks
- **Per-step session lifecycle** prevents holding database locks across long-running Claude API calls (10-60 seconds each)
- **Indexes** on `(ticker, data_type, expires_at)` for cache lookups -- O(log n)
- **Indexes** on `(screen_id, tier)` and `(screen_id, phase)` for IST query patterns
- **Unique indexes** enforce one-to-one relationships (screen_id on master_screens, rotation_strategies, etc.)
- **JSON stored as TEXT** in SQLite (no native JSONB) -- parsed in Python, not queried by key
- **Queryable filter columns** (status, tier, phase, ticker) have their own indexed columns separate from JSON blobs
- **Expected volume:** Single user, ~10-50 IST screens over time, each with ~20-50 claims and ~10-20 equity candidates. Total IST data per screen: ~50KB of structured data + report text. Trivial for SQLite.
- **No connection pooling needed** -- single-user, single-process access. Per-step sessions are lightweight.

### Query Pattern Optimization

| Query Pattern | Index Used | Expected Frequency |
|---|---|---|
| List screens by status | `idx_ist_screens_status` | Low (user browsing) |
| Get claims for screen | `idx_ist_claims_screen` | Medium (per screen view) |
| Get candidates by tier | `idx_ist_equity_screen` | Medium (filtered views) |
| Get workflow steps | `idx_workflow_steps_run` | High (SSE polling) |
| Check workflow status | `idx_workflow_runs_status` | High (dashboard) |
| Look up candidate by ticker | `idx_ist_equity_ticker` | Low (cross-reference) |
| Validate claim uniqueness | `idx_ist_claims_bottleneck` | Low (during extraction) |

---

**Created:** 2026-01-30
**Last Updated:** 2026-02-07
**Owner:** @Chief_Architect
