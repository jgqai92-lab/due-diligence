# Architecture Document

## System Overview

The Skeptical Analyst is a two-layer application: a **Python backend** (FastAPI) that handles financial data fetching via yfinance, forensic metric calculations, SQLite persistence, and Claude API integration, paired with a **Next.js frontend** (React) that delivers a commercial-grade Bloomberg Terminal-inspired UI.

The system ingests financial statement data from yfinance, computes quantitative forensic metrics (Beneish M-Score, Altman Z-Score, Rule of 40, Magic Number), and generates AI-authored narrative reports with citations, bear cases, and red flags. Portfolio management uses the Alpaca Paper Trading API (free tier).

**Phase 2 Expansion:** The application extends into a unified investment platform by adding two AI-powered research workflows: **IST (Investment Screening)** converts unstructured content into ranked, time-phased equity screens through a 5-phase AI pipeline with dialectic scrutiny. **HFRT (Hedge Fund Research)** performs deep-dive company analysis through a 5-phase research pipeline producing comprehensive investment memos. Both workflows are orchestrated by a shared **Workflow Engine** that provides background task execution, SSE progress streaming, and checkpoint-based phase progression.

**Design Constraint:** Zero infrastructure cost aside from the Claude API key. All data sources, database, and hosting are free.

**UI Constraint:** Commercial-grade polish -- the interface must be indistinguishable from a paid institutional product.

## Technology Stack

### Backend
- **Framework:** Python 3.11+ with FastAPI
- **Justification:** yfinance is a Python library, making Python the natural backend choice. FastAPI provides async support, automatic OpenAPI documentation, type validation via Pydantic, and high performance. It serves as the data/analysis layer that the Next.js frontend consumes.

### Frontend
- **Framework:** Next.js 14+ (App Router) with TypeScript
- **UI:** Tailwind CSS + shadcn/ui
- **Justification:** Next.js provides server-side rendering for data-dense pages, App Router for modern routing patterns, and a rich React ecosystem. Tailwind + shadcn/ui enable commercial-grade component quality with full customization control. TypeScript ensures type safety across the frontend.

### Database
- **Database:** SQLite 3 (local file-based)
- **ORM:** SQLAlchemy 2.0 (Python backend)
- **Justification:** SQLite is zero-cost, zero-configuration, and perfectly suited for a single-user local application. No cloud database, no connection strings, no monthly fees. SQLAlchemy provides a clean ORM layer with migration support via Alembic. The database file lives alongside the application. WAL mode enables concurrent reads during background task writes.

### LLM Integration
- **Provider:** Anthropic Claude API (Claude Sonnet)
- **Client Libraries:** `anthropic` (sync, existing forensic analysis) + `AsyncAnthropic` (async, new IST/HFRT workflows)
- **Tools:** Anthropic built-in `web_search` tool for IST external validation
- **Justification:** Strong instruction-following for structured financial report generation. Large context window accommodates full financial statements plus calculated metrics. The `web_search` tool enables claim verification without additional API keys. Only paid dependency in the stack.

### Portfolio/Market Data
- **Provider:** Alpaca Paper Trading API (free tier)
- **Base URL:** `https://paper-api.alpaca.markets`
- **Justification:** Free, developer-friendly API for portfolio tracking and paper trading. Provides real-time market data on the free tier sufficient for portfolio valuation.

### Hosting/Deployment
- **Strategy:** Local execution / self-hosted
- **Justification:** SQLite requires filesystem access and yfinance requires a persistent Python runtime. The application runs locally via `docker-compose` or direct process management (`uvicorn` for FastAPI, `npm run dev` for Next.js). No cloud hosting cost.

## System Design

### Component Diagram

```
+========================================================================================+
|                              User Browser (Port 3000)                                  |
|  Next.js 14 Frontend  |  React + Tailwind + shadcn/ui                                 |
|                                                                                        |
|  +------------------+  +--------------------+  +---------------------+                 |
|  | Forensic Dash    |  | IST Screen Views   |  | HFRT Research Views |                 |
|  | (existing)       |  | - Report (primary) |  | - Template phases   |                 |
|  | - Analyze ticker |  | - Working Data     |  | - Investment Memo   |                 |
|  | - Portfolio      |  | - Workflow Tracker |  | - Bull/Bear         |                 |
|  | - Alerts         |  | - Frameworks       |  | - Frameworks        |                 |
|  +--------+---------+  +--------+-----------+  +---------+-----------+                 |
|           |                     |                        |                              |
|           +----------+----------+----------+-------------+                              |
|                      |  HTTP (JSON)        |  SSE (EventSource)                         |
+========================================================================================+
                       |                     |
+========================================================================================+
|                        FastAPI Backend (Port 8000)                                      |
|                                                                                        |
|  +---------------------+  +----------------------------+                               |
|  | EXISTING ROUTERS    |  | NEW ROUTERS                |                               |
|  | /api/analyze        |  | /api/workflows (CRUD+SSE)  |                               |
|  | /api/search         |  | /api/ist (screens+phases)  |                               |
|  | /api/portfolio      |  | /api/hfrt (projects+tmpl)  |                               |
|  | /api/alerts         |  | /api/frameworks (IST/HFRT) |                               |
|  | /api/health         |  | /api/bridge (IST->HFRT)    |                               |
|  +---------------------+  +----------------------------+                               |
|           |                           |                                                |
|  +--------+---------+    +-----------+--------------------+                            |
|  | EXISTING SERVICES |    | WORKFLOW ENGINE                |                            |
|  | yfinance_service  |    | workflow_engine.py             |                            |
|  | forensic_engine   |    |   asyncio.create_task per step |                            |
|  | general_metrics   |    |   asyncio.Queue for SSE events |                            |
|  | claude_service    |    |   checkpoint pause/resume      |                            |
|  | alert_service     |    |   8-state state machine        |                            |
|  | sector_service    |    +------+----------+--------------+                            |
|  | citation_service  |           |          |                                          |
|  +--------+---------+    +------+---+  +---+--------+                                  |
|           |              | IST      |  | HFRT       |                                  |
|           |              | SERVICES |  | SERVICES   |                                  |
|           |              | (13 mods)|  | (future)   |                                  |
|           |              +----+-----+  +---+--------+                                  |
|           |                   |             |                                          |
|  +--------+-------------------+-------------+-------+                                  |
|  |              SQLite Database (WAL mode)          |                                  |
|  |  Existing: cached_financials, analysis_reports,  |                                  |
|  |            holdings, alerts, watchlist,           |                                  |
|  |            alert_settings                        |                                  |
|  |  New:      workflow_runs, workflow_steps,         |                                  |
|  |            ist_screens, ist_claims, ist_*  (13)  |                                  |
|  +--------------------------------------------------+                                  |
|                                                                                        |
|  +---------------------+  +----------------------------+                               |
|  | Alpaca Paper API    |  | Anthropic Claude API       |                               |
|  | (portfolio values)  |  | - Sync (forensic reports)  |                               |
|  +---------------------+  | - Async (IST/HFRT phases)  |                               |
|                            | - web_search tool (IST)    |                               |
|                            +----------------------------+                               |
+========================================================================================+
```

### Service Layer Structure

```
backend/app/services/
  __init__.py
  yfinance_service.py        # Existing: financial data fetching + caching
  forensic_engine.py         # Existing: M-Score, Z-Score calculations
  general_metrics_engine.py  # Existing: profitability, leverage, cash flow
  claude_service.py          # Existing: sync Anthropic client for forensic reports
  alert_service.py           # Existing: alert generation
  sector_service.py          # Existing: sector classification
  citation_service.py        # Existing: citation mapping
  metric_definitions.py      # Existing: metric thresholds and definitions
  workflow_engine.py         # NEW: background task orchestration + SSE
  frameworks.py              # NEW: framework content loader
  ist/                       # NEW: IST service modules
    __init__.py
    claude_client.py         # AsyncAnthropic client (shared by IST services)
    content_extraction.py    # Phase 1: content -> structured claims
    source_bias.py           # Phase 1: source bias assessment
    bottleneck_mapper.py     # Phase 2: claims -> temporal bottleneck cascade
    demand_modeler.py        # Phase 2: bottlenecks -> quantitative demand models
    external_validator.py    # Phase 2: Claude + web_search claim verification
    quality_gates.py         # All gates: content sufficiency, research, coherence
    equity_scanner.py        # Phase 3: bottlenecks -> equity candidates
    tier_classifier.py       # Phase 3: scarcity scoring -> Tier 1/2/3
    effects_analyst.py       # Phase 3: multi-order effects mapping
    invariant_checker.py     # Phase 3: 8 IST screening invariants
    dialectic.py             # Phase 4: optimist/pessimist/synthesis
    synthesizer.py           # Phase 5: master screen, rotation, catalysts, stress
    report_generator.py      # Phase 5: Investment Thesis Report (primary output)
```

## Data Flow: Single-Ticker Forensic Analysis (Existing)

```
1. User enters ticker in search bar (Next.js)
         |
2. Frontend calls GET /api/analyze/{ticker} (FastAPI)
         |
3. FastAPI checks SQLite cache for data < 24 hours old
         |
   +-----+------+
   |             |
 CACHE HIT    CACHE MISS
   |             |
   |     4. yfinance fetches (parallel):
   |        - ticker.financials (income statement)
   |        - ticker.balance_sheet
   |        - ticker.cashflow
   |        - ticker.info (key statistics)
   |             |
   |     5. Store raw data in SQLite with timestamp
   |             |
   +------+------+
          |
6. Forensic Calculation Engine processes data:
   - Beneish M-Score (8 components + composite)
   - Altman Z-Score (standard + SaaS-modified)
   - Rule of 40 (Revenue Growth % + FCF Margin %)
   - Magic Number (Net New ARR / S&M Spend)
          |
7. Construct Claude API prompt:
   - System prompt: forensic analyst persona + citation rules
   - User prompt: raw financial data + calculated metrics
   - Required: Executive Summary, Red Flags, Bear Case, Citations
          |
8. Claude API returns markdown report (streamed, ~3-8 seconds)
          |
9. Store report in SQLite (analysis_reports table)
          |
10. Return to Next.js frontend:
    { ticker, profile, forensicMetrics, report, dataSources }
          |
11. Frontend renders commercial-grade metric cards,
    markdown report, citation tooltips, red flag badges
```

## Data Flow: Portfolio Watchdog (Existing)

```
1. User clicks "Run Watchdog" or scheduled trigger fires
         |
2. GET /api/portfolio/watchdog
         |
3. Fetch all holdings from SQLite
         |
4. For each holding (throttled, max 3 concurrent):
   a. Run single-ticker analysis (same as above)
   b. Compare current metrics against previous scan
   c. Flag deterioration (zone changes, threshold crossings)
         |
5. Generate alerts, store in SQLite
         |
6. Return: { scannedCount, alertCount, alerts[], lastScanAt }
```

## Data Flow: IST Investment Screening Pipeline (New)

```
1. User creates new screen: name + paste content (podcast transcripts, articles)
         |
2. POST /api/ist/screens -> Creates ISTScreen + WorkflowRun
         |
3. Frontend opens SSE connection: GET /api/workflows/{id}/stream
         |
   +==================================================================+
   | PHASE 1: CONTENT EXTRACTION (background task)                    |
   |                                                                  |
   | 4. content_extraction.py: Claude parses unstructured text        |
   |    System prompt: extract claims with source tags, quant anchors |
   |    User content: raw pasted text (SEPARATED from instructions)   |
   |         |                                                        |
   | 5. source_bias.py: assess source credibility and bias            |
   |         |                                                        |
   | 6. Store ISTClaims in SQLite                                     |
   |         |                                                        |
   | 7. SSE event: { type: "step_complete", step: "extraction" }      |
   +==================================================================+
         |
   CHECKPOINT: User reviews extracted claims, edits brief
         |
   +==================================================================+
   | PHASE 2: THEMATIC ANALYSIS (background task)                     |
   |                                                                  |
   | 8.  bottleneck_mapper.py: claims -> temporal cascade             |
   |     Phase 1 (near-term) / Phase 2 (mid) / Phase 3 (secular)     |
   |         |                                                        |
   | 9.  demand_modeler.py: bottlenecks -> quantitative models        |
   |     1 GW Cluster Formula, multiplier library, sensitivity        |
   |         |                                                        |
   | 10. external_validator.py: Claude + web_search tool              |
   |     Anthropic API call with tools=[{type: web_search_20250514}]  |
   |     Claude autonomously searches web for corroboration           |
   |     Returns: confirmed/partially/contradicted/unvalidatable      |
   |         |                                                        |
   | 11. QUALITY GATE: Content Sufficiency                            |
   |     - 3+ claims with quantitative anchors?                       |
   |     - 1+ temporal marker?                                        |
   |     - Source bias assessed?                                      |
   |     - 1+ bottleneck identified?                                  |
   |     FAIL -> surfaces deficiency list, blocks Phase 3             |
   +==================================================================+
         |
   CHECKPOINT: User reviews bottlenecks, demand models, validation
         |
   +==================================================================+
   | PHASE 3: EQUITY IDENTIFICATION (background task)                 |
   |                                                                  |
   | 12. equity_scanner.py: Claude + yfinance identify companies      |
   |     Reuses existing yfinance_service.py for financial data       |
   |     Scarcity scoring: 5 dimensions x 5-point scale               |
   |         |                                                        |
   | 13. tier_classifier.py: assign Tier 1/2/3                        |
   |     Tier 1: scarcity >= 4.0, valuation data, moat verified       |
   |     Tier 2: scarcity 3.0-3.9 or missing one T1 criterion        |
   |     Tier 3: below Tier 2 thresholds                              |
   |         |                                                        |
   | 14. effects_analyst.py: 1st->2nd->3rd order downstream effects   |
   |         |                                                        |
   | 15. invariant_checker.py: 8 IST screening invariants             |
   |         |                                                        |
   | 16. QUALITY GATE: Research Sufficiency                           |
   |     FAIL -> surfaces deficiency list, blocks Phase 4             |
   +==================================================================+
         |
   CHECKPOINT: User reviews equity candidates, tier classifications
         |
   +==================================================================+
   | PHASE 4: DIALECTIC SCRUTINY (background task)                    |
   |                                                                  |
   | 17. dialectic.py -> run_both_isolated(screen_id):                |
   |     +-----------------------------------+                        |
   |     | asyncio.gather (parallel)         |                        |
   |     |                                   |                        |
   |     | OPTIMIST                PESSIMIST  |                        |
   |     | Bull case,              Null hyp,  |                        |
   |     | upside catalysts,       timeline   |                        |
   |     | market misperceptions   risk, bias |                        |
   |     |                                   |                        |
   |     | Receives Phase 1-3 data ONLY      |                        |
   |     | CANNOT see other side's output    |                        |
   |     +-----------------------------------+                        |
   |         |                                                        |
   | 18. dialectic.py -> run_synthesis(screen_id):                    |
   |     Synthesizer sees BOTH reviews + all Phase 1-3 data           |
   |     Reconciles disagreements, adjusts tiers                      |
   +==================================================================+
         |
   +==================================================================+
   | PHASE 5: FINAL SYNTHESIS (background task)                       |
   |                                                                  |
   | STEP ORDER IS CRITICAL:                                          |
   |                                                                  |
   | 19. synthesizer.py: master screen (ranked equities)              |
   | 20. synthesizer.py: rotation strategy (phase allocation)         |
   | 21. synthesizer.py: catalyst calendar (dated events)             |
   | 22. synthesizer.py: stress tests (framework + name level)        |
   | 23. report_generator.py: Investment Thesis Report (BEFORE gate)  |
   |     Single Claude call with ALL accumulated data                 |
   |     Output: full markdown matching IST OUTPUT EXAMPLE format     |
   |         |                                                        |
   | 24. QUALITY GATE: Screen Coherence (AFTER report)                |
   |     - Report complete and self-contained?                        |
   |     - Pillars align with bottleneck map?                         |
   |     - All Tier 1 names have narrative analysis?                  |
   |         |                                                        |
   | 25. Screen certification + HFRT handoff data generation          |
   +==================================================================+
         |
26. SSE event: { type: "workflow_complete" }
         |
27. Frontend displays Investment Thesis Report (primary view)
    + Working Data tabs for inspection of intermediate results
```

## Background Task Architecture

### Execution Model

IST (and future HFRT) workflow phases involve multiple Claude API calls that each take 10-60 seconds. Executing these synchronously in a request handler would block the server and time out. The architecture uses Python's native `asyncio.create_task` for background execution:

```
Request: POST /api/workflows/{id}/advance
  |
  +-> Validate state (must be PAUSED at checkpoint or PENDING)
  +-> Update status to RUNNING
  +-> asyncio.create_task(execute_phase(workflow_id, phase_number))
  +-> Return 202 Accepted immediately
        |
        +-> Background task runs phase steps sequentially
        +-> Each step:
            1. Create new SQLAlchemy session (per-step session lifecycle)
            2. Update WorkflowStep status to RUNNING
            3. Execute service function (Claude API call, computation, etc.)
            4. Store output_data in WorkflowStep
            5. Update WorkflowStep status to COMPLETED
            6. Push SSE event to in-memory queue
            7. Close session
        +-> On phase completion:
            - If checkpoint phase: set WorkflowRun status to PAUSED
            - If final phase: set WorkflowRun status to COMPLETED
        +-> On error:
            - Set WorkflowStep status to FAILED with error_message
            - Set WorkflowRun status to FAILED
            - Push SSE error event
```

### Per-Step Session Lifecycle

SQLite does not support true concurrent transactions. Each workflow step creates and closes its own SQLAlchemy session to avoid holding database locks across long-running Claude API calls:

```python
async def execute_step(workflow_id: int, step_name: str, service_fn):
    session = SessionLocal()
    try:
        step = session.query(WorkflowStep).filter_by(...).one()
        step.status = "RUNNING"
        session.commit()

        result = await service_fn(session, step.input_data)

        step.output_data = result
        step.status = "COMPLETED"
        session.commit()
    except Exception as e:
        step.status = "FAILED"
        step.error_message = str(e)
        session.commit()
        raise
    finally:
        session.close()
```

### SSE Event Flow

```
Backend (asyncio.Queue)              Frontend (EventSource)
         |                                    |
  step_complete event  ---- SSE stream --->  onmessage handler
  step_failed event    ---- SSE stream --->  onmessage handler
  heartbeat (15s)      ---- SSE stream --->  keepalive
         |                                    |
  workflow_complete    ---- SSE stream --->  redirect to report view
```

**SSE Event Types (13 types):**

| Event Type | Payload | When |
|---|---|---|
| `workflow_started` | `{ workflow_id, workflow_type }` | Workflow begins |
| `phase_started` | `{ phase, phase_name }` | Phase execution begins |
| `step_started` | `{ step_name, phase }` | Individual step begins |
| `step_progress` | `{ step_name, message, percent }` | Mid-step progress (optional) |
| `step_complete` | `{ step_name, phase, duration_ms }` | Step finished successfully |
| `step_failed` | `{ step_name, phase, error }` | Step failed |
| `phase_complete` | `{ phase, phase_name }` | Phase finished |
| `checkpoint_reached` | `{ phase, next_phase, requires_approval }` | Waiting for user |
| `gate_passed` | `{ gate_name, details }` | Quality gate passed |
| `gate_failed` | `{ gate_name, deficiencies[] }` | Quality gate failed |
| `workflow_complete` | `{ workflow_id, duration_ms }` | Workflow finished |
| `workflow_failed` | `{ workflow_id, error }` | Workflow failed |
| `heartbeat` | `{ timestamp }` | Every 15 seconds |

### Workflow State Machine

```
                        POST /api/workflows (create)
                                |
                                v
                          +----------+
                          | PENDING  |
                          +----+-----+
                               |  POST .../advance (start)
                               v
                          +----------+
              +---------->| RUNNING  |<---------+
              |           +----+-----+          |
              |                |                |
              |     +----------+----------+     |
              |     |          |          |     |
              |     v          v          v     |
              | +--------+ +--------+ +------+  |
              | | PAUSED | | FAILED | | COMP | (terminal)
              | | (chkpt)| |        | | LETED|  |
              | +---+----+ +--------+ +------+  |
              |     |                            |
              |     | POST .../advance           |
              +-----+                            |
              |                                  |
              | POST .../cancel                  |
              v                                  |
          +----------+                           |
          |CANCELLED |                           |
          +----------+                           |

  States: PENDING, RUNNING, PAUSED, COMPLETED, FAILED,
          CANCELLED, CANCELLING, RETRYING
```

## AI Integration Architecture Patterns

This section addresses the security and reliability requirements for the application's extensive use of Claude API across forensic reports (existing), IST screening (new), and HFRT research (future).

### Content/Instruction Separation

All Claude API calls maintain strict separation between system instructions and user-provided content. This prevents prompt injection from user-pasted content (podcast transcripts, articles) from overriding analytical instructions.

**Pattern applied across all IST services:**

```
System Message (instructions):
  - Analyst persona and role definition
  - Output format requirements (JSON schema or markdown structure)
  - Anti-hallucination rules ("only cite provided data")
  - Specific analytical framework to apply

User Message (content):
  - Clearly delimited user-provided content within XML-style tags:
    <source_content>{user_pasted_text}</source_content>
  - Pre-calculated data from prior pipeline steps:
    <accumulated_data>{structured JSON from previous phases}</accumulated_data>
  - Task-specific parameters:
    <parameters>{screening constraints, framework selections}</parameters>
```

**Key rules:**
1. User-pasted content is ALWAYS wrapped in `<source_content>` tags within the user message, never injected into system prompts.
2. System prompts are static per service module -- they contain no user-supplied strings.
3. Accumulated data from prior phases is serialized as JSON and placed in the user message, separate from source content.

### Output Validation Pipeline

Every Claude API response passes through validation before being stored or used by downstream steps:

```
Claude API Response
      |
      v
1. Parse response.content[0].text
      |
      v
2. Pydantic model validation (structured output)
   - JSON responses parsed into typed Pydantic models
   - Missing required fields -> step fails with specific error
   - Type mismatches -> step fails with specific error
      |
      v
3. Business rule validation
   - Claim counts within expected range (not 0, not 10000)
   - Scores within defined bounds (scarcity: 1-5, not -999)
   - Tickers match /^[A-Z]{1,5}$/ regex
   - No empty required text fields
      |
      v
4. Cross-reference validation (where applicable)
   - Report pillars align with bottleneck map
   - Cited tickers exist in equity candidates list
   - Tier assignments consistent with scarcity scores
      |
      v
5. Store validated output in SQLite
```

### Sandboxing Approach

AI components are isolated from core application logic through multiple boundaries:

1. **Service module isolation:** Each IST service module (`content_extraction.py`, `bottleneck_mapper.py`, etc.) is a self-contained unit that takes structured input and produces structured output. No service module directly modifies another module's data.

2. **Separate Claude client:** IST/HFRT workflows use a dedicated `AsyncAnthropic` client instantiated in `ist/claude_client.py`, completely separate from the existing sync `Anthropic` client in `claude_service.py`. This prevents configuration cross-contamination.

3. **Session boundaries:** Each workflow step creates its own database session. A Claude API call failure in one step cannot corrupt data written by a previous step.

4. **Read-only downstream:** The IST pipeline is append-only within a screen. Phase 3 reads Phase 1-2 data but cannot modify it. Phase 4 (dialectic) reads Phase 1-3 data but cannot modify it. This prevents cascading corruption.

5. **Timeout enforcement:** Every Claude API call has a per-call timeout (configurable, default 120s). A hung API call cannot block the workflow engine indefinitely.

### Rate Limiting and Resource Management for AI Endpoints

| Resource | Strategy | Limit |
|---|---|---|
| IST screen creation | Rate limit on POST /api/ist/screens | Max 5 per hour |
| Claude API (IST steps) | Sequential within a phase, parallel only in dialectic | Max 2 concurrent IST API calls |
| Claude web_search tool | Inherits Anthropic API rate limits | Per Anthropic plan limits |
| Workflow engine | Max concurrent running workflows | 2 simultaneous workflows |
| SSE connections | One per workflow per client | Max 5 total SSE connections |
| yfinance (IST equity scan) | Reuses existing cache + throttle | Max 5 concurrent yfinance calls |

## Key Architectural Decisions

1. **Two-layer architecture (Python + Next.js):** yfinance is Python-only, and the UI requires React/Next.js for commercial-grade quality. FastAPI serves as the data/analysis API; Next.js handles rendering. Clean API boundary between concerns.

2. **SQLite as the sole data store:** For a single-user local application, SQLite eliminates all database infrastructure cost and complexity. It handles caching, reports, portfolio, alerts, workflows, and IST screens in a single file. Write concurrency is managed via per-step session lifecycle and WAL mode.

3. **Server-side calculations only:** All forensic metrics computed in Python on the backend. Never on the client. Ensures calculation consistency, protects raw data, and centralizes rounding/precision handling.

4. **Claude as narrator, not calculator:** Claude receives pre-calculated metrics and raw data. Its role is narrative interpretation, pattern recognition, and bear case construction -- not arithmetic. Prevents hallucinated calculations. This principle extends to IST: Claude performs thematic analysis and claim extraction, but scarcity scoring formulas and tier classification thresholds are server-side Python logic.

5. **yfinance with aggressive caching:** yfinance data cached 24 hours in SQLite. Manual refresh available. This minimizes API calls and provides offline capability for previously-analyzed tickers.

6. **Local-first deployment:** No cloud dependencies. `docker-compose up` starts both services. SQLite file persists between restarts. Portable and reproducible.

7. **Workflow Engine as shared infrastructure:** A single workflow engine serves both IST and HFRT (and any future workflow types). This avoids duplicating background task management, SSE streaming, and checkpoint logic.

8. **AsyncAnthropic for workflows, sync Anthropic for forensic:** The existing `claude_service.py` uses the synchronous `Anthropic` client, which works fine for single-request forensic reports. IST/HFRT workflows make multiple sequential and parallel API calls within background tasks, requiring `AsyncAnthropic` for proper async/await integration. The two clients coexist without interference.

9. **In-memory asyncio.Queue for SSE:** SSE events are propagated via in-memory asyncio queues rather than a message broker (Redis, RabbitMQ). This is appropriate for a single-process, single-user application and avoids adding infrastructure. The trade-off: SSE state is lost on server restart (acceptable -- the workflow state in SQLite persists and the frontend can reconnect and hydrate from database state).

10. **Investment Thesis Report as primary IST deliverable:** The IST pipeline produces a unified markdown report as the primary output, not a collection of template data views. Individual template data is retained as "Working Data" for inspection and debugging, but the user-facing deliverable is the narrative report.

## Authentication & Authorization

**Single-user application -- no authentication required.**

The application runs locally and is accessed by one person. There is no login, no signup, no JWT, no session management. All data belongs to the single user. If future multi-user support is needed, NextAuth.js can be added without architectural changes.

## Security Considerations

### Secrets Management
- `ANTHROPIC_API_KEY`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY` stored in `.env` file
- `.env` is git-ignored (enforced in `.gitignore`)
- Frontend never accesses API keys -- all external API calls made from Python backend
- No `NEXT_PUBLIC_` prefix on any secret

### Input Validation
- Ticker symbols validated against strict regex: `/^[A-Z]{1,5}$/`
- All user inputs sanitized before database queries (SQLAlchemy parameterized queries)
- Claude API responses treated as untrusted content, sanitized before rendering
- IST content input: user-pasted text is stored as-is but wrapped in `<source_content>` tags before inclusion in Claude prompts (content/instruction separation)
- Workflow IDs validated as integers; non-existent IDs return 404

### OWASP Mitigations (Relevant Subset)
- **Injection:** SQLAlchemy parameterized queries; no raw SQL with user input
- **XSS:** React's built-in escaping; Claude output sanitized before rendering; IST report markdown sanitized before HTML rendering
- **Security Misconfiguration:** CORS restricted to localhost origins
- **SSRF:** No user-supplied URLs fetched; ticker symbols validated before use in yfinance; Claude's web_search tool is API-side (Anthropic infrastructure), not server-side

### AI-Specific Security (ATLAS Threat Model)
- **Prompt Injection via content:** User-pasted content (podcasts, articles) could contain adversarial instructions. Mitigated by content/instruction separation (source content in XML tags within user message, never in system prompt).
- **Model output manipulation:** Claude could produce malformed JSON, unexpected tickers, or hallucinated data. Mitigated by Pydantic validation on all structured outputs and business rule checks.
- **Data exfiltration:** Claude's web_search tool could theoretically be manipulated to exfiltrate data. Mitigated by: (a) web_search is read-only, (b) Claude cannot make arbitrary HTTP requests, (c) the tool is Anthropic-managed infrastructure.
- **Denial of service via Claude costs:** Unrestricted workflow creation could run up API bills. Mitigated by rate limiting on screen/project creation and max concurrent workflow limits.

## Rate Limiting & Throttling

| Resource | Strategy | Limit |
|----------|----------|-------|
| yfinance calls | SQLite cache (24h TTL) + request throttling | Max 5 concurrent fetches |
| Claude API (forensic) | Per-analysis rate limit | Max 3 concurrent requests |
| Claude API (IST/HFRT) | Sequential within phase, capped concurrency | Max 2 concurrent workflow API calls |
| Alpaca API | Cache portfolio data (5 min TTL) | Per Alpaca free tier limits |
| Workflow creation | Rate limit on POST endpoints | Max 5 screens/hour, 2 running workflows |
| SSE connections | Per-client limit | Max 5 total connections |

## Scalability Considerations

### Current Design Point
- Single user, single machine, single process
- SQLite with WAL mode handles all concurrency needs
- In-memory queues for SSE (no message broker)

### 10x Growth Path (if needed)
- **Database:** Migrate SQLite to PostgreSQL (straightforward via SQLAlchemy ORM abstraction). Gains: true concurrent writes, JSONB queries, connection pooling.
- **Background tasks:** Replace `asyncio.create_task` with Celery + Redis. Gains: task persistence across restarts, distributed execution, retry policies.
- **SSE:** Replace in-memory queues with Redis Pub/Sub. Gains: multi-process SSE, horizontal scaling.
- **Claude API:** Add request queuing with priority (forensic reports = high priority, background IST phases = normal priority).

## Risk Assessment

### Risk 1: yfinance Reliability and Rate Limits
- **Impact:** High -- yfinance is the sole data source
- **Probability:** Medium -- yfinance scrapes Yahoo Finance, which may throttle
- **Mitigation:** Aggressive 24-hour caching in SQLite. Exponential backoff on failures. Graceful degradation showing cached data with staleness warning.

### Risk 2: yfinance Data Quality
- **Impact:** Medium -- garbage in, garbage out for forensic metrics
- **Probability:** Low -- Yahoo Finance data sourced from SEC filings
- **Mitigation:** Validate critical fields (revenue, net income, total assets) are non-null before calculations. Flag tickers with insufficient history as "Insufficient Data."

### Risk 3: Claude Hallucination in Financial Reports
- **Impact:** High -- incorrect analysis could drive bad investment decisions
- **Probability:** Medium -- Claude may fabricate figures
- **Mitigation:** (1) Pre-calculate all metrics server-side. (2) Strict system prompt: cite only provided data. (3) Post-generation validation cross-references cited figures against raw data. (4) Legal disclaimer on all reports.

### Risk 4: SQLite Concurrency Under Workflow Load
- **Impact:** Medium -- write contention during multi-step workflow execution
- **Probability:** Medium -- IST workflows perform many sequential writes during background tasks
- **Mitigation:** WAL mode for concurrent reads during writes. Per-step session lifecycle (open session, write, close) prevents holding locks across long Claude API calls. Busy timeout configured to handle brief lock contention.

### Risk 5: yfinance Breaking Changes
- **Impact:** High -- field names or data structure changes break calculations
- **Probability:** Medium -- yfinance is community-maintained
- **Mitigation:** Data normalization layer abstracts yfinance response structure. Unit tests verify expected field names against live data. Pin yfinance version in requirements.txt.

### Risk 6: Claude API Latency in Multi-Step Workflows
- **Impact:** Medium -- IST pipeline makes 15-20 Claude API calls per screen, each 10-60 seconds
- **Probability:** High -- API latency is inherent
- **Mitigation:** (1) Background execution via asyncio.create_task prevents blocking. (2) SSE streaming keeps user informed of progress. (3) Checkpoint pausing allows user to review intermediate results. (4) Per-call timeout (120s) prevents indefinite hangs. (5) Dialectic runs optimist/pessimist in parallel (asyncio.gather) to save wall-clock time.

### Risk 7: IST Report Quality Drift
- **Impact:** Medium -- Investment Thesis Report may not match expected format
- **Probability:** Medium -- Claude output varies across runs
- **Mitigation:** (1) Detailed system prompt specifying exact section structure. (2) Screen Coherence Gate validates report structure before certification. (3) Pydantic validation on structured components. (4) Report metadata tracks pillar count, equity count, tier breakdown for consistency checks.

### Risk 8: Prompt Injection via User-Pasted Content
- **Impact:** High -- adversarial content could manipulate Claude's analysis
- **Probability:** Low -- single-user local app, but content may come from untrusted sources
- **Mitigation:** (1) Content/instruction separation: user text in `<source_content>` tags within user message, never in system prompt. (2) System prompt explicitly instructs Claude to treat content as raw data for analysis, not as instructions. (3) Output validation catches anomalous results.

## Wave/Phase Planning

### Wave 1: Foundation (Existing -- Complete)
- Python project scaffold (FastAPI + SQLAlchemy + SQLite)
- Next.js 14 project scaffold (App Router + TypeScript + Tailwind + shadcn/ui)
- SQLite schema and migrations (Alembic)
- yfinance data fetching service with caching
- Docker-compose for local development
- Project structure: `/backend` (Python), `/frontend` (Next.js)

### Wave 2: Core Analysis Engine (Existing -- Complete)
- Forensic calculation engine (Python):
  - Beneish M-Score (8 components + composite)
  - Altman Z-Score (standard + SaaS-modified)
  - Rule of 40
  - Magic Number
- Citation data generation (map each calculated value to source line items)
- Claude API integration with structured prompts
- FastAPI endpoints: /api/analyze/{ticker}, /api/search
- SQLite caching layer for yfinance responses

### Wave 3: Frontend Dashboard (Existing -- Complete)
- Commercial-grade design system implementation (Tailwind config)
- Ticker search with autocomplete
- Forensic metric cards (M-Score gauge, Z-Score zone bar, SaaS metrics panels)
- Markdown report renderer with styled sections
- Citation tooltip system (hover to verify any number)
- Bear case callout component
- Red flag badges
- Loading skeletons, error states, empty states
- Responsive layout optimized for data density
- Commercial-grade polish: animations, transitions, typography

### Wave 4: Portfolio & Watchdog (Existing -- Complete)
- Alpaca Paper Trading API integration
- Portfolio CRUD (add, edit, remove holdings)
- Portfolio dashboard with aggregate metrics and P&L
- Watchdog scan engine (batch forensic analysis)
- Alert generation and display
- Alert history and dismissal

### Wave 5: Polish & Hardening (Existing -- Complete)
- Edge case handling (delisted tickers, insufficient data, ADRs)
- Performance optimization (query analysis, bundle size)
- Accessibility audit (keyboard nav, screen reader, contrast)
- Unit tests for forensic calculations (100% coverage)
- Integration tests for API endpoints
- E2E tests for critical paths (Playwright)
- Documentation and methodology pages

### Mega-Phase A: IST Integration (Waves A1-A8)

#### Wave A1: Workflow Engine Foundation
- WorkflowRun and WorkflowStep SQLAlchemy models
- Background task runner (asyncio.create_task)
- SSE endpoint with in-memory asyncio.Queue
- Phase progression with checkpoint pausing
- Workflow CRUD + control endpoints
- Alembic migration 004_workflow_engine

#### Wave A2: IST Data Models & Content Input
- ISTScreen, ISTClaim, ISTBottleneck models
- Content extraction service (Claude-powered)
- Source bias assessment
- IST router with screen CRUD endpoints
- Alembic migration 005_ist_tables

#### Wave A3: IST Phase 2 -- Thematic Analysis
- Bottleneck mapper, demand modeler, external validator services
- Quality gates (content sufficiency)
- Additional IST model tables (ISTDemandModel, ISTValidation)

#### Wave A4: IST Phase 3 -- Equity Identification
- Equity scanner, tier classifier, effects analyst, invariant checker
- ISTEquityCandidate, ISTEffectsChain models
- Quality gate (research sufficiency)

#### Wave A5: IST Phase 4 -- Dialectic Scrutiny
- Dialectic orchestration (optimist/pessimist/synthesis)
- ISTDialecticReview model
- Parallel execution via asyncio.gather

#### Wave A6: IST Phase 5 -- Final Synthesis & Report
- Master screen, rotation strategy, catalyst calendar, stress tests
- Investment Thesis Report generator (primary deliverable)
- Screen Coherence Gate (verifies report completeness)
- ISTMasterScreen, ISTRotationStrategy, ISTCatalystCalendar, ISTStressTest, ISTReport models

#### Wave A7: IST Frameworks Reference Panel
- Framework content loader (static markdown files)
- Framework API endpoints
- Frontend framework panel

#### Wave A8: IST Integration Testing & Polish
- End-to-end flow testing
- SSE reliability, quality gate edge cases, invariant enforcement
- Report quality validation
- UI polish

---

**Created:** 2026-01-30
**Last Updated:** 2026-02-07
**Owner:** @Chief_Architect
