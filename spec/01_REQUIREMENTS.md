# Requirements Document

## Project Goals
1. Provide forensic due diligence automation (M-Score, Z-Score, SaaS metrics) with citation-grounded analysis
2. Enable investment idea screening from unstructured content through a 5-phase AI pipeline (IST)
3. Support deep company research through a 15-template pipeline with SEC filing integration (HFRT)
4. Bridge screening to research with IST-to-HFRT handoff for Tier 1 candidates
5. Integrate portfolio tracking with watchdog alerting via Alpaca Paper Trading
6. Ground every claim in source data — zero tolerance for hallucination

---

## MVP Features (Phase 1 -- Forensic Due Diligence Engine)

### Feature 1: Ticker Search & Input
**User Story:** As an analyst, I want to enter a ticker symbol so I can run forensic due diligence on any publicly traded company.

**Acceptance Criteria:**
- [ ] Text input with autocomplete suggesting matching ticker symbols as user types
- [ ] Displays ticker symbol, company name, and sector in dropdown results
- [ ] Validates ticker against yfinance-known symbols before analysis
- [ ] Keyboard navigable (arrow keys, Enter to select, Escape to close)
- [ ] Debounced input (300ms) to minimize yfinance calls
- [ ] Recent searches displayed for quick re-access
- [ ] Case-insensitive (entering "aapl" resolves to "AAPL")
- [ ] Commercial-grade polish: smooth dropdown animation, hover states, loading spinner

**Priority:** High

---

### Feature 2: Financial Data Fetching & Caching
**User Story:** As an analyst, I want the system to automatically pull 10-K/10-Q financial data so I don't manually scrape SEC filings.

**Acceptance Criteria:**
- [ ] Fetches from yfinance: income statement, balance sheet, cash flow statement, key statistics
- [ ] Supports both annual and quarterly periods (last 5 years / 20 quarters)
- [ ] Caches responses in local SQLite database with 24-hour TTL
- [ ] Displays data freshness timestamp ("Data as of 2h ago") with color-coded indicator
- [ ] Manual refresh button bypasses cache and re-fetches from yfinance
- [ ] Graceful error handling for unknown tickers, yfinance failures, rate limits
- [ ] Loading states with skeleton loaders during data fetch
- [ ] Data normalization handles yfinance field naming inconsistencies

**Priority:** High

---

### Feature 3: Beneish M-Score Calculation
**User Story:** As an analyst, I want to see the probability of earnings manipulation so I can identify accounting red flags.

**Acceptance Criteria:**
- [ ] Calculates all 8 M-Score components:
  - DSRI (Days Sales in Receivables Index)
  - GMI (Gross Margin Index)
  - AQI (Asset Quality Index)
  - SGI (Sales Growth Index)
  - DEPI (Depreciation Index)
  - SGAI (Sales, General & Admin Expenses Index)
  - LVGI (Leverage Index)
  - TATA (Total Accruals to Total Assets)
- [ ] Computes composite M-Score: M = -4.84 + 0.920(DSRI) + 0.528(GMI) + 0.404(AQI) + 0.892(SGI) + 0.115(DEPI) - 0.172(SGAI) + 4.679(TATA) - 0.327(LVGI)
- [ ] Classifies: Unlikely Manipulator (< -2.22), Grey Zone (-2.22 to -1.78), Likely Manipulator (> -1.78)
- [ ] Each component has citation tooltip showing source line item from yfinance data
- [ ] Missing components show "Data Not Available" with reason
- [ ] Year-over-year trend sparkline for composite score (last 5 years)
- [ ] Flags specific suspicious patterns (e.g., "DSRI increased 20% while Revenue grew only 5%")
- [ ] Expandable "How This Works" methodology section

**Priority:** High

---

### Feature 4: Altman Z-Score Calculation (SaaS-Modified)
**User Story:** As an analyst, I want bankruptcy risk assessment customized for asset-light SaaS companies.

**Acceptance Criteria:**
- [ ] Calculates standard Z-Score: Z = 1.2(X1) + 1.4(X2) + 3.3(X3) + 0.6(X4) + 1.0(X5)
  - X1 = Working Capital / Total Assets
  - X2 = Retained Earnings / Total Assets
  - X3 = EBIT / Total Assets
  - X4 = Market Value of Equity / Total Liabilities
  - X5 = Revenue / Total Assets
- [ ] Provides SaaS-modified variant (clearly labeled "Modified -- not academically validated")
- [ ] Displays both standard and SaaS-modified scores side by side
- [ ] Zone classification: Safe (> 2.99), Grey (1.81-2.99), Distress (< 1.81)
- [ ] Visual horizontal zone bar showing where score falls on spectrum
- [ ] Each input has source citation tooltip from yfinance data
- [ ] Year-over-year trend (last 5 years)

**Priority:** High

---

### Feature 5: SaaS Quality of Revenue Metrics
**User Story:** As an analyst, I want Rule of 40 and Magic Number to assess SaaS revenue quality.

**Acceptance Criteria:**
- [ ] **Rule of 40:** Revenue Growth % + Free Cash Flow Margin % (Pass >= 40, Marginal 30-39, Fail < 30)
- [ ] **Magic Number:** Net New ARR / Prior Period S&M Spend (Efficient > 0.75, Moderate 0.5-0.75, Inefficient < 0.5)
- [ ] Side-by-side display with pass/fail visual indicators
- [ ] Component breakdown showing each input value with citations
- [ ] Trailing 8-quarter trend chart for both metrics
- [ ] Non-SaaS disclaimer when applicable
- [ ] Handles missing ARR data gracefully (approximation from quarterly revenue delta)

**Priority:** High

---

### Feature 6: Forensic Report Generation (LLM)
**User Story:** As an analyst, I want a comprehensive markdown memo synthesizing all forensic findings with cited line items.

**Acceptance Criteria:**
- [ ] Claude API generates structured narrative report with sections:
  1. Executive Summary
  2. Earnings Manipulation Analysis (M-Score)
  3. Bankruptcy Risk Assessment (Z-Score)
  4. SaaS Quality of Revenue
  5. Red Flags and Suspicious Items (citing specific line items)
  6. **Bear Case (MANDATORY -- always present, always substantive)**
  7. Data Limitations
- [ ] Every financial figure cited includes source (filing type, period, line item name)
- [ ] "Data Not Available" for any missing metrics -- never estimates without labeling
- [ ] System prompt enforces: no fabricated numbers, no extrapolation without disclosure
- [ ] Report exportable as markdown (.md) file download
- [ ] Progress indicator during generation (Claude streaming)
- [ ] Regenerate button for fresh analysis
- [ ] Red flag badges highlight critical findings inline

**Priority:** High

---

### Feature 7: Citation System
**User Story:** As an analyst, I want to verify every number against its original source data.

**Acceptance Criteria:**
- [ ] Every financial figure has hover tooltip: "Source: [Filing Type], [Period], Line Item: [Name]"
- [ ] Tooltip shows raw value from yfinance alongside any calculated/derived value
- [ ] Visual indicator (subtle underline or icon) shows a value has citation data
- [ ] Citation tooltips accessible via keyboard (Tab to focus, Enter/Space to open)
- [ ] "View All Sources" panel lists every data point used in the analysis
- [ ] Consistent -- same source value never displayed differently in different UI locations

**Priority:** High

---

## MVP Features (Phase 1B -- Investment Screening / IST)

### Feature 12: Workflow Engine Foundation
**User Story:** As a user, I want a background workflow engine so that multi-phase AI pipelines (IST/HFRT) can run without blocking the UI, with real-time progress updates and checkpoint controls.

**Acceptance Criteria:**
- [ ] `WorkflowRun` tracks: id, workflow_type (IST/HFRT), name, status (PENDING/RUNNING/PAUSED/COMPLETED/FAILED), current_phase, timestamps
- [ ] `WorkflowStep` tracks: id, workflow_run_id, step_name, phase, status, input/output data (JSON), timestamps, error_message
- [ ] Background task execution via `asyncio.create_task` with per-step processing
- [ ] SSE endpoint (`GET /api/workflows/{id}/stream`) streams phase/step progress in real-time
- [ ] Checkpoint pausing: workflow pauses between phases until user approves advancement
- [ ] User can pause, resume, or cancel a running workflow at any time
- [ ] CRUD endpoints: list workflows (filterable by type), create, get details, advance, pause, cancel
- [ ] Frontend `WorkflowProgressTracker` component displays live phase/step status with approval buttons
- [ ] SSE client utility handles reconnection on network interruption

**Priority:** High

---

### Feature 13: IST Content Input & Extraction
**User Story:** As a user, I want to create a new investment screen by pasting unstructured content (podcast transcripts, articles, earnings calls) so that the system extracts structured claims with source citations, quantitative anchors, and temporal markers.

**Acceptance Criteria:**
- [ ] New screen creation wizard: name, paste/upload content, select frameworks
- [ ] Claude-powered content extraction parses unstructured text into structured claims
- [ ] Each extracted claim includes: claim_text, source_citation, quantitative_anchor, temporal_marker, bottleneck_name, confidence score
- [ ] Source bias assessment performed on input content (identifies potential biases of the source)
- [ ] Screening brief is auto-generated and user-editable (constraints, frameworks, hypothesis)
- [ ] Claims displayed in a sortable table with source tags and confidence badges
- [ ] System prompt enforces: source tagging, quantitative anchors, temporal markers for every claim
- [ ] API endpoints: create screen, submit content, get/edit screening brief, list screens

**Priority:** High

---

### Feature 14: IST Thematic Analysis (Phase 2)
**User Story:** As a user, I want the system to map extracted claims into temporal bottleneck cascades, build quantitative demand models, and validate claims against external sources so that I have a verified thematic foundation for equity identification.

**Acceptance Criteria:**
- [ ] **Bottleneck Mapping:** Claude maps claims to Phase 1/2/3 temporal bottleneck cascade with sequential dependency validation
- [ ] **Demand Modeling:** Quantitative demand models per bottleneck using formulas (e.g., 1 GW Cluster pattern), multiplier library, sensitivity analysis
- [ ] **External Validation:** Claude uses Anthropic `web_search` tool to verify each claim against independent sources; returns verdicts (confirmed/partially confirmed/contradicted/unvalidatable) with source URLs
- [ ] **Content Sufficiency Gate (Quality Gate 1):** Blocks phase progression unless: 3+ claims with quantitative anchors, 1+ temporal marker, bias assessed, 1+ bottleneck identified
- [ ] Gate failure surfaces specific deficiency list to user
- [ ] Visual bottleneck map shows Phase 1 -> 2 -> 3 temporal cascade
- [ ] Demand model panel displays formulas, multipliers, and sensitivity tables
- [ ] Validation status badges on each claim (confirmed/contradicted/pending)

**Priority:** High

---

### Feature 15: IST Equity Identification (Phase 3)
**User Story:** As a user, I want the system to identify companies with exposure to mapped bottlenecks, score them on scarcity dimensions, and classify them into tiers so that I have a ranked candidate list with conviction levels.

**Acceptance Criteria:**
- [ ] **Equity Scanning:** Claude + yfinance identifies companies with bottleneck exposure; reuses existing `yfinance_service.py`
- [ ] **Scarcity Scoring:** 5-dimension x 5-point scale (each dimension scored 1-5) producing a composite scarcity score per candidate
- [ ] **Tier Classification (deterministic, server-side):**
  - Tier 1 (high conviction): scarcity >= 4.0, valuation data present, moat verified, multi-source corroboration
  - Tier 2 (watchlist): scarcity 3.0-3.9 or missing one Tier 1 criterion
  - Tier 3 (speculative): below Tier 2 thresholds
- [ ] **Multi-Order Effects:** Claude maps 1st -> 2nd -> 3rd order downstream effects per primary thesis; identifies new equity candidates from effects
- [ ] **8 Screening Invariants (all CRITICAL severity):** INV-1 through INV-8 enforced as individual check functions; `check_all_invariants(screen_id)` returns violation list
- [ ] **Research Sufficiency Gate (Quality Gate 2):** Blocks phase progression when research data is insufficient
- [ ] Sortable equity candidates table with scarcity scores, tier badges, moat type, catalyst
- [ ] 5-dimension scarcity radar chart per candidate
- [ ] Tier 1/2/3 grouped display with conviction indicators
- [ ] Visual effects cascade tree (1st -> 2nd -> 3rd order)
- [ ] Invariant checklist with pass/fail status for all 8 invariants

**Priority:** High

---

### Feature 16: IST Dialectic Scrutiny (Phase 4)
**User Story:** As a user, I want the system to stress-test the screen through optimist/pessimist dialectic analysis so that I can see both sides of the thesis before reaching conclusions.

**Acceptance Criteria:**
- [ ] **Optimist review:** Claude call with bull-case system prompt (market misperceptions, upside catalysts); receives all Phase 1-3 data
- [ ] **Pessimist review:** Claude call with bear-case system prompt (null hypothesis, source bias, timeline risk, demand deceleration); receives same Phase 1-3 data
- [ ] **Isolation enforced:** Optimist and pessimist run as parallel `asyncio.gather` calls; neither sees the other's output
- [ ] **Synthesis:** Claude call that receives BOTH reviews + all Phase 1-3 data; reconciles disagreements, adjusts tier classifications, produces synthesis report
- [ ] Side-by-side optimist/pessimist display
- [ ] Synthesis report showing specific disagreements and resolutions
- [ ] Live progress indicator during parallel dialectic execution

**Priority:** High

---

### Feature 17: IST Final Synthesis & Investment Thesis Report (Phase 5)
**User Story:** As a user, I want the system to produce a self-contained Investment Thesis Report as the primary deliverable, along with supporting outputs (master screen, rotation strategy, catalyst calendar, stress tests), so that I have a complete, printable research document.

**Acceptance Criteria:**
- [ ] **Phase 5 step ordering enforced:**
  1. Generate Master Screen (ranked equity table with conviction scores)
  2. Generate Rotation Strategy (phase-based allocation with triggers)
  3. Generate Catalyst Calendar (dated catalyst timeline)
  4. Generate Stress Tests (framework-level + name-level, survival scores)
  5. Generate Investment Thesis Report (BEFORE gate)
  6. Screen Coherence Gate evaluation (verifies report exists and is complete)
  7. Screen Certification + HFRT Handoff data
  8. Complete
- [ ] **Investment Thesis Report structure** (matches IST OUTPUT EXAMPLE.md):
  - I. Executive Summary (core insight + consolidated screen table with all tickers)
  - II. Pillar-by-Pillar Analysis (bottlenecks as investable pillars, quantitative formulas in narrative, inline stress test blockquotes, per-equity narrative prose)
  - III. Second & Third-Order Effects ("If X remains the binding constraint" scenario format)
  - IV. Civilizational Framing (optional, only when source content warrants)
  - V. Portfolio Construction Guidance (tier allocation percentages + catalyst table)
  - VI. Disclaimer (date, source list)
- [ ] Report is self-contained: reader understands full thesis without viewing other templates
- [ ] Report is synthesis only: no new analysis; everything traces to prior phase data
- [ ] Every equity gets narrative prose (not just table entries)
- [ ] Anti-hallucination: no new numbers, estimates, or claims introduced in report
- [ ] **Screen Coherence Gate (Quality Gate 3):** Verifies report is complete, pillars align with bottleneck map, all Tier 1 names have narrative analysis
- [ ] Report renderer with section navigation (table of contents sidebar), blockquote styling, sortable screen table
- [ ] Export options: print/PDF
- [ ] Master screen table, rotation strategy chart, catalyst calendar timeline, and stress test results available as secondary "Working Data" views

**Priority:** High

---

### Feature 18: IST Screen Detail Page UX
**User Story:** As a user, I want the screen detail page organized with the Investment Thesis Report as the primary view and working data as a secondary inspection view so that I can focus on the deliverable while still drilling into analytical details.

**Acceptance Criteria:**
- [ ] Two primary tabs on screen detail page (`/screens/[id]`):
  - **Report tab (DEFAULT):** Renders `InvestmentThesisReport` -- the unified narrative thesis (primary view)
  - **Working Data tab:** Tabbed sub-navigation with: Brief, Claims, Bottleneck Map, Demand Models, Validation, Equity Candidates, Tiers, Effects, Master Screen, Rotation, Catalysts, Stress Tests
- [ ] Persistent **Workflow Progress** header/sidebar showing current phase, step status, and checkpoint controls
- [ ] Report tab is the default landing view when a screen is complete
- [ ] Working Data tab is the default when a screen is still in progress (user monitors workflow)

**Priority:** High

---

### Feature 19: IST Frameworks Reference Panel
**User Story:** As a user, I want to access the 7 IST analytical frameworks as reference material while reviewing screen results so that I understand the scoring methodology and analytical foundations.

**Acceptance Criteria:**
- [ ] 7 IST framework markdown files bundled in `backend/app/data/frameworks/ist/`
- [ ] API endpoints: `GET /api/frameworks/ist` (list summaries), `GET /api/frameworks/ist/{name}` (full content)
- [ ] Slide-out reference panel accessible from any IST screen page via floating button
- [ ] Framework selector dropdown within the panel
- [ ] Markdown renderer for framework content with proper heading hierarchy and code block styling

**Priority:** Medium

---

### Feature 20: IST Quality Gates & Invariants System
**User Story:** As a user, I want to see quality gate results and invariant compliance so that I can trust the rigor of the screening process and understand any deficiencies blocking progression.

**Acceptance Criteria:**
- [ ] **3 Quality Gates** evaluated as server-side validation functions:
  - Content Sufficiency Gate: 3+ claims with quant anchors, 1+ temporal marker, bias assessed, 1+ bottleneck
  - Research Sufficiency Gate: equity candidates identified, scarcity scored, tiers assigned
  - Screen Coherence Gate: report complete, pillars align with bottleneck map, all Tier 1 names have narrative
- [ ] Failed gates block phase advancement and surface specific deficiency lists to the user
- [ ] Gate status display: pass/fail badge with expandable deficiency detail
- [ ] **8 Screening Invariants (all CRITICAL severity):** INV-1 through INV-8
- [ ] Invariant check endpoint: `GET /api/ist/screens/{id}/invariants`
- [ ] Invariant checklist UI with pass/fail status per invariant
- [ ] Violations surfaced clearly with specific remediation guidance

**Priority:** High

---

## Phase 2 Features (Post-MVP)

### Feature 8: Revenue Per Employee (RPE) Tracking
**User Story:** As an analyst, I want to track AI-adjusted efficiency by monitoring Revenue Per Employee over time.

**Acceptance Criteria:**
- [ ] Calculates RPE = Total Revenue / Total Employees for each period
- [ ] Tracks RPE rate of change (second derivative) over multiple periods
- [ ] Classifies: "Agent-Native" (RPE accelerating, headcount flat) vs "Legacy SaaS" (RPE flat, headcount growing)
- [ ] Visual chart showing RPE trend over time
- [ ] Employee count sourced from yfinance or supplemental data

**Priority:** Medium

---

### Feature 9: Sentiment vs. Fundamentals Divergence
**User Story:** As an analyst, I want to see when market sentiment diverges from fundamental health.

**Acceptance Criteria:**
- [ ] News sentiment score (0-100) from available free sources
- [ ] Fundamental health score (0-100) from composite forensic metrics
- [ ] Divergence chart plotting sentiment vs fundamentals over time
- [ ] Flags: "Caution: Sentiment exceeds fundamentals" / "Opportunity: Fundamentals exceed sentiment"

**Priority:** Medium

---

## Phase 2 Features (HFRT -- Hedge Fund Research)

### Feature 21: HFRT Deep Research Pipeline
**User Story:** As a user, I want to deep-dive individual companies through a 15-template research pipeline (idea screen, fundamentals, competitive position, industry analysis, financial analysis, valuation, management assessment, risk analysis, quality of earnings, catalysts, thesis synthesis, bull/bear dialectic, investment memo) so that I produce institutional-grade investment memos.

**Acceptance Criteria:**
- [ ] 15-template pipeline: Templates 00-14 covering full research lifecycle
- [ ] SEC EDGAR integration via `edgartools` for 10-K, 10-Q, DEF 14A filings
- [ ] Reuses existing forensic engine (M-Score, Z-Score) and general metrics engine
- [ ] Bull/Bear dialectic with same isolation pattern as IST
- [ ] 3 quality gates (research sufficiency, DD sufficiency, thesis coherence)
- [ ] 8 research invariants
- [ ] Final deliverable: Investment Memo (printable format)
- [ ] Can be initiated manually (enter ticker) or from IST handoff

**Priority:** Medium (Mega-Phase B)

---

### Feature 22: IST-to-HFRT Bridge
**User Story:** As a user, I want to send Tier 1 candidates from a completed IST screen directly into HFRT deep research projects so that I can seamlessly transition from screening to deep-dive analysis.

**Acceptance Criteria:**
- [ ] Handoff panel displays Tier 1 names with checkboxes and "Send to Deep Research" button
- [ ] `POST /api/bridge/ist-to-hfrt` creates HFRT projects pre-populated with IST context (thesis, bottleneck exposure, scarcity assessment, catalyst, tier rationale)
- [ ] Pre-fills HFRT Template 00 (Idea Screen) with IST-derived data
- [ ] Links `HFRTProject.ist_screen_id` back to source screen for traceability
- [ ] After handoff, user can navigate directly to the new HFRT project

**Priority:** Medium (Mega-Phase C)

---

## Phase 3 Features (Portfolio Watchdog)

### Feature 10: Shadow Portfolio
**User Story:** As an analyst, I want to input holdings and cost basis to track my portfolio alongside forensic metrics.

**Acceptance Criteria:**
- [ ] Add holdings: ticker, shares, cost basis, purchase date
- [ ] Edit and remove holdings
- [ ] Current valuation via Alpaca Paper Trading API
- [ ] P&L per holding and total portfolio
- [ ] Each holding links to its forensic report

**Priority:** Medium

---

### Feature 11: Portfolio Watchdog & Alerting
**User Story:** As an analyst, I want weekly forensic re-scans on all holdings with alerts for deterioration.

**Acceptance Criteria:**
- [ ] Weekly automated re-scan of all portfolio holdings
- [ ] Alerts when metrics cross thresholds (M-Score > -1.78, Z-Score enters distress, etc.)
- [ ] Alert types: m_score_warning, z_score_distress, rule_of_40_fail, magic_number_low
- [ ] Alert severities: info, warning, critical
- [ ] Alert dismissal and history
- [ ] Configurable thresholds

**Priority:** Medium

---

## Non-Functional Requirements

### Performance
- [ ] Page load time < 2 seconds
- [ ] API response < 500ms for cached data (p95)
- [ ] yfinance data cached 24 hours in SQLite
- [ ] Forensic calculations < 1 second server-side
- [ ] LLM report generation < 15 seconds with streaming progress
- [ ] IST/HFRT workflow phases run as background tasks -- must not block the UI or event loop
- [ ] SSE progress streaming maintains connection for workflow durations (minutes per phase)
- [ ] SSE client reconnects automatically on network interruption

### Security
- [ ] API keys (Anthropic, Alpaca) stored in .env file, never in source code
- [ ] .gitignore excludes .env, SQLite database files, and any credential files
- [ ] Input validation on all ticker inputs
- [ ] No secrets exposed to frontend client code
- [ ] Content/instruction separation enforced in all Claude API system prompts (user content never treated as instructions)
- [ ] LLM output validated via Pydantic models before use in application logic
- [ ] Protection against prompt injection: user-pasted content (podcast transcripts, articles) sanitized before inclusion in Claude prompts
- [ ] Rate limiting on workflow creation and AI-powered endpoints
- [ ] Timeouts on all Claude API calls (prevent runaway costs)
- [ ] `SEC_EDGAR_USER_AGENT` configured in .env (required by SEC EDGAR policy)

### Accessibility
- [ ] WCAG 2.1 AA compliance
- [ ] Full keyboard navigation
- [ ] Screen reader compatible (ARIA labels on all interactive elements)
- [ ] Color contrast meets 4.5:1 minimum for text
- [ ] Financial color coding has non-color indicators (icons, text labels)

### UI Quality (Commercial-Grade)
- [ ] Pixel-perfect alignment and spacing throughout
- [ ] Smooth, purposeful animations (no jank, no unnecessary motion)
- [ ] Professional typography with proper font hierarchy
- [ ] Consistent component styling across all pages
- [ ] Polished loading states (skeletons, not spinners where possible)
- [ ] Error states that are informative and well-designed (not raw error dumps)
- [ ] Responsive layout from 320px to ultrawide
- [ ] Bloomberg Terminal data density without feeling cramped
- [ ] IST workflow progress states show meaningful phase/step detail (not generic spinners)
- [ ] Report renderer produces print-quality output with proper typography and layout

### Browser/Device Support
- [ ] Chrome, Firefox, Safari, Edge (latest 2 versions)
- [ ] Mobile responsive (read-only optimized)
- [ ] Minimum viewport: 320px width

### AI-Specific Non-Functional Requirements
- [ ] All metrics displayed in IST/HFRT views must carry source citations (reuses existing `CitationTooltip` / `MetricComponent` pattern)
- [ ] Claude provides analysis and narrative ONLY; the application performs all calculations server-side (scarcity scoring, tier classification, quality gate evaluation, invariant checks)
- [ ] Dialectic isolation: optimist/pessimist (IST) and bull/bear (HFRT) run as separate Claude API calls with no shared conversation context
- [ ] Anti-hallucination: Claude system prompts explicitly prohibit fabricating numbers, estimating without disclosure, or introducing new claims in synthesis steps
- [ ] Content/instruction separation: all Claude prompts separate system instructions from user-provided content to mitigate indirect prompt injection
- [ ] External validation (web_search) results include source URLs for user verification

---

## Route Structure

| Route | Feature | Status |
|-------|---------|--------|
| `/` | Home dashboard | Existing (enhanced with IST/HFRT summary cards) |
| `/analyze/[ticker]` | Forensic analysis | Existing (add "Start Deep Research" link) |
| `/screens` | IST screen list | New (Phase 1B) |
| `/screens/new` | Create new IST screen | New (Phase 1B) |
| `/screens/[id]` | IST screen detail (Report + Working Data tabs) | New (Phase 1B) |
| `/screens/[id]/handoff` | IST-to-HFRT handoff | New (Mega-Phase C) |
| `/research` | HFRT project list | New (Mega-Phase B) |
| `/research/new` | Create new HFRT project | New (Mega-Phase B) |
| `/research/[id]` | HFRT project detail (phased tabs) | New (Mega-Phase B) |
| `/portfolio` | Portfolio holdings | Existing |
| `/alerts` | Alert dashboard | Existing |

---

## Database Schema Additions (IST)

| Table | Purpose | Wave |
|-------|---------|------|
| `workflow_runs` | Orchestration state for any workflow type | A1 |
| `workflow_steps` | Individual step execution records | A1 |
| `ist_screens` | Screen metadata + brief/extraction JSON | A2 |
| `ist_claims` | Individual extracted claims (queryable) | A2 |
| `ist_bottlenecks` | Temporal bottleneck records | A3 |
| `ist_demand_models` | Quantitative demand models | A3 |
| `ist_validations` | External validation records | A3 |
| `ist_equity_candidates` | Company candidates with scarcity scores | A4 |
| `ist_effects_chains` | Multi-order effects | A4 |
| `ist_dialectic_reviews` | Optimist/Pessimist/Synthesis | A5 |
| `ist_master_screens` | Final ranked output | A6 |
| `ist_rotation_strategies` | Phase allocation + triggers | A6 |
| `ist_catalyst_calendars` | Dated catalyst data | A6 |
| `ist_stress_tests` | Stress test results | A6 |
| `ist_reports` | Investment Thesis Report (PRIMARY DELIVERABLE) | A6 |

---

## Implementation Wave Mapping (IST / Mega-Phase A)

| Wave | Scope | Features Covered |
|------|-------|-----------------|
| A1 | Workflow Engine Foundation | Feature 12 |
| A2 | IST Data Models & Content Input | Feature 13 |
| A3 | IST Thematic Analysis (Phase 2) | Feature 14 |
| A4 | IST Equity Identification (Phase 3) | Feature 15 |
| A5 | IST Dialectic Scrutiny (Phase 4) | Feature 16 |
| A6 | IST Final Synthesis & Report (Phase 5) | Feature 17, Feature 18 |
| A7 | IST Frameworks Reference Panel | Feature 19 |
| A8 | IST Integration Testing & Polish | Feature 20 (gates/invariants verified end-to-end) |

---

**Created:** 2026-01-30
**Last Updated:** 2026-02-07
**Owner:** @Product_Owner
