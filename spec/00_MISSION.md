# Project Mission

## Project Name
The "Skeptical Analyst" — Unified Investment Intelligence Platform

## Project Description
A high-fidelity, commercial-grade financial platform built for a solo capital allocator. The application combines three pillars of investment intelligence into a single "Bloomberg Terminal for one":

1. **Forensic Due Diligence Engine** (existing) — Automated Beneish M-Score, Altman Z-Score, and SaaS quality-of-revenue metrics with citation-grounded analysis.
2. **Investment Screening (IST)** (new) — Converts unstructured content (podcast transcripts, articles, earnings calls) into ranked, time-phased equity screens through a 5-phase AI pipeline with dialectic scrutiny. Primary deliverable: a unified Investment Thesis Report.
3. **Hedge Fund Research (HFRT)** (planned) — Deep-dives individual companies through a 5-phase research pipeline producing comprehensive investment memos with SEC-grade rigor.

The platform bridges the gap between discovering investment ideas (IST), validating them forensically (Due Diligence Engine), and conducting deep research (HFRT) — all grounded in source data with zero tolerance for hallucination. The IST-to-HFRT handoff allows Tier 1 screened candidates to flow directly into deep research.

Core philosophy: "Trust, but Verify (with Math)."

The UI is designed to commercial-grade standards — indistinguishable from a paid institutional product in polish, interaction quality, and data density.

## Primary Goals
1. **Automate forensic due diligence** with Beneish M-Score, Altman Z-Score (SaaS-modified), and SaaS quality-of-revenue metrics (Rule of 40, Magic Number)
2. **Screen investment ideas from unstructured content** via IST: extract claims, map bottlenecks, identify equities, apply dialectic scrutiny, and produce a self-contained Investment Thesis Report
3. **Deep-dive individual companies** via HFRT: 15-template research pipeline with SEC filing integration, competitive analysis, valuation, and bull/bear dialectic
4. **Bridge screening to research** with IST-to-HFRT handoff for Tier 1 candidates
5. **Provide forward-looking valuation** through AI-adjusted efficiency metrics (Revenue Per Employee) and sentiment-vs-fundamentals divergence signals
6. **Integrate portfolio watchdog** with active monitoring, weekly re-scanning, and forensic alert system via Alpaca Paper Trading API
7. **Ground every claim in source data** with citation tooltips on every financial figure — prevent LLM hallucination
8. **Unify discovery, due diligence, research, portfolio tracking, and synthesis** in a single interface
9. **Zero operational cost** beyond the Claude API key — all data sources and infrastructure are free

## AI Components
**Uses AI/LLM:** Yes

**Provider:** Anthropic Claude API (claude-sonnet or opus models)

**AI Use Cases:**
| Use Case | What Claude Does | What the App Does Server-Side |
|----------|-----------------|-------------------------------|
| Forensic Report Generation | Synthesizes narrative from calculated metrics | All M-Score, Z-Score, Rule of 40 calculations |
| IST Content Extraction | Parses unstructured text into structured claims with citations | Stores/indexes claims, enforces schema |
| IST Bottleneck Mapping | Identifies temporal bottleneck cascades from claims | Validates sequential dependencies |
| IST Demand Modeling | Produces quantitative demand models per bottleneck | Stores models, runs sensitivity tables |
| IST External Validation | Uses `web_search` tool to verify claims against independent sources | Records verdicts, updates claim status |
| IST Equity Identification | Identifies companies with bottleneck exposure | Scarcity scoring (5x5), tier classification |
| IST Dialectic Scrutiny | Optimist/pessimist analysis in isolated calls | Ensures isolation, runs synthesis |
| IST Report Generation | Produces pillar-organized Investment Thesis Report narrative | Validates report structure, stores output |
| HFRT Deep Research | Analyzes company fundamentals, competitive position, risks | DuPont decomposition, DCF, all quantitative work |
| HFRT SEC Filing Analysis | Interprets proxy statements, risk factors, footnotes | Fetches filings via edgartools, extracts sections |
| HFRT Bull/Bear Dialectic | Isolated bull and bear case generation | Ensures isolation, stores reviews |

**External Content Types Processed by AI:**
- User-pasted text (podcast transcripts, articles, earnings call notes)
- yfinance financial data (income statements, balance sheets, cash flows)
- SEC EDGAR filings (10-K, 10-Q, DEF 14A) via edgartools
- Web search results (via Anthropic `web_search` tool for claim validation)

**Anti-Hallucination Architecture:**
- Claude provides analysis and narrative ONLY; the application performs all calculations server-side
- Content/instruction separation enforced in all Claude system prompts
- Every financial figure must carry a source citation
- Missing data labeled "Data Not Available" — never estimated without disclosure
- 3 quality gates and 8 screening invariants enforce data integrity in IST pipeline
- Dialectic reviews run in isolated API calls (no shared context between optimist/pessimist)

**Security Considerations (triggers ATLAS threat modeling):**
- Prompt injection risk: user-pasted content flows into Claude prompts
- Content/instruction separation required in all LLM interactions
- LLM output validation before use in application logic (Pydantic parsing)
- Rate limiting on AI-powered endpoints
- Timeouts on all Claude API calls

## Tech Stack Summary
| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python), SQLAlchemy, Alembic |
| Database | SQLite (WAL mode) |
| Financial Data | yfinance (free) |
| SEC Filings | edgartools (free, SEC EDGAR public API) |
| Portfolio API | Alpaca Paper Trading (free tier) |
| AI/LLM | Anthropic Claude API |
| External Validation | Anthropic `web_search` tool |
| Real-Time Updates | Server-Sent Events (SSE) |

## Success Criteria
- [ ] Every financial figure displayed has a source citation tooltip (filing type, quarter, line item)
- [ ] Missing data explicitly shows "Data Not Available" — never estimates without labeling
- [ ] Every generated report concludes with a mandatory "Bear Case" section
- [ ] Forensic metrics (M-Score, Z-Score, Rule of 40, Magic Number) correctly calculated against yfinance data
- [ ] Portfolio holdings monitored weekly with triggered alert system via Alpaca Paper Trading
- [ ] IST workflow produces a self-contained Investment Thesis Report from unstructured content input
- [ ] IST quality gates block phase progression when data is insufficient
- [ ] IST-to-HFRT handoff pre-populates deep research projects for Tier 1 candidates
- [ ] UI meets commercial-grade polish standards (smooth animations, precise layout, professional typography)
- [ ] Application runs locally with zero paid infrastructure (SQLite, yfinance, Alpaca free tier)

## Target Users
- **Primary User:** A single Strategic Data Scientist & Solo Capital Allocator — values "Hard Data" over narrative, needs institutional-grade forensic analysis and investment screening at zero cost
- **Secondary Use:** Personal portfolio management, investment thesis validation, and systematic idea generation from content consumption

## Key Constraints
- **Zero infrastructure cost** — only the Claude API key is a paid dependency
- **Financial Data:** yfinance Python library (free, open-source) — rate limit aware with local caching
- **SEC Filings:** edgartools (free, SEC EDGAR public API) — rate limited to 10 req/sec per SEC policy
- **Portfolio API:** Alpaca Paper Trading API (free tier) for position tracking
- **Database:** SQLite (local file-based, WAL mode) — no cloud database
- **LLM:** Claude API (Anthropic) for analysis and narrative — only paid component
- **Single-user scope** — no multi-tenant, no auth beyond local use
- **Local/self-hosted deployment** — not serverless
- **Background processing required** — IST/HFRT workflow phases take minutes (multiple Claude API calls); must not block UI

## Out of Scope
- Live trading execution (paper trading only via Alpaca)
- Multi-user support or authentication system
- Mobile native app (web-responsive only)
- Real-time streaming market data (batch/on-demand only)
- Options or derivatives analysis
- Tax reporting or compliance filing
- Cloud hosting or serverless deployment

---

**Created:** 2026-01-30
**Last Updated:** 2026-02-07
**Owner:** @Product_Owner
