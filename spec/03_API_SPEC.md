# API Specification

## Overview

The Skeptical Analyst uses a two-layer API architecture:
- **FastAPI Backend (Port 8000):** Python backend handling yfinance data, forensic calculations, SQLite, Claude API, workflow engine, IST screening, and HFRT research
- **Next.js Frontend (Port 3000):** Consumes the FastAPI backend and renders the commercial-grade UI

All endpoints below are served by the FastAPI backend. The Next.js frontend calls these endpoints via HTTP (and SSE for streaming).

## Base URL
- **Development:** `http://localhost:8000/api`

## Common Response Codes
- `200 OK`: Request succeeded
- `201 Created`: Resource created successfully
- `202 Accepted`: Request accepted for background processing (workflow advancement)
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Ticker or resource not found
- `409 Conflict`: Invalid state transition (e.g., advancing a completed workflow)
- `422 Unprocessable Entity`: Valid request but insufficient data for analysis
- `429 Too Many Requests`: Rate limit / throttle exceeded
- `500 Internal Server Error`: Server error
- `502 Bad Gateway`: External API (Claude, Alpaca) failure
- `504 Gateway Timeout`: External API timeout

## Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

Error codes: `TICKER_INVALID`, `TICKER_NOT_FOUND`, `INSUFFICIENT_DATA`, `RATE_LIMITED`, `YFINANCE_ERROR`, `CLAUDE_ERROR`, `CLAUDE_TIMEOUT`, `ALPACA_ERROR`, `WORKFLOW_NOT_FOUND`, `WORKFLOW_INVALID_STATE`, `SCREEN_NOT_FOUND`, `GATE_FAILED`, `INTERNAL_ERROR`

---

## Data Source: yfinance (Python Library)

Instead of external REST API calls, the backend uses yfinance method calls:

```python
import yfinance as yf

ticker = yf.Ticker("AAPL")

# Income Statement (annual)
ticker.financials          # DataFrame: Revenue, COGS, Gross Profit, EBIT, Net Income, etc.

# Balance Sheet (annual)
ticker.balance_sheet       # DataFrame: Total Assets, Current Assets, Total Liabilities, etc.

# Cash Flow (annual)
ticker.cashflow            # DataFrame: Operating Cash Flow, CapEx, Free Cash Flow, etc.

# Quarterly variants
ticker.quarterly_financials
ticker.quarterly_balance_sheet
ticker.quarterly_cashflow

# Key statistics
ticker.info                # Dict: marketCap, sector, industry, fullTimeEmployees, etc.

# Search (for autocomplete)
# yfinance does not have a native search endpoint.
# Use a local ticker list or the yfinance download with validation.
```

### yfinance to Forensic Metric Mapping

| Forensic Metric | yfinance Source | Fields Used |
|----------------|-----------------|-------------|
| **DSRI** (M-Score) | `ticker.balance_sheet`, `ticker.financials` | Accounts Receivable (Net Receivables), Total Revenue |
| **GMI** (M-Score) | `ticker.financials` | Gross Profit, Total Revenue |
| **AQI** (M-Score) | `ticker.balance_sheet` | Total Assets, Current Assets, Net PPE |
| **SGI** (M-Score) | `ticker.financials` | Total Revenue (current vs prior) |
| **DEPI** (M-Score) | `ticker.balance_sheet`, `ticker.financials` | Net PPE, Depreciation |
| **SGAI** (M-Score) | `ticker.financials` | SGA Expense, Total Revenue |
| **LVGI** (M-Score) | `ticker.balance_sheet` | Total Liabilities, Total Assets |
| **TATA** (M-Score) | `ticker.financials`, `ticker.cashflow`, `ticker.balance_sheet` | Net Income, Operating Cash Flow, Total Assets |
| **Z-Score X1** | `ticker.balance_sheet` | Current Assets - Current Liabilities, Total Assets |
| **Z-Score X2** | `ticker.balance_sheet` | Retained Earnings, Total Assets |
| **Z-Score X3** | `ticker.financials`, `ticker.balance_sheet` | EBIT, Total Assets |
| **Z-Score X4** | `ticker.info`, `ticker.balance_sheet` | Market Cap, Total Liabilities |
| **Z-Score X5** | `ticker.financials`, `ticker.balance_sheet` | Total Revenue, Total Assets |
| **Rule of 40** | `ticker.financials`, `ticker.cashflow` | Total Revenue (growth), Free Cash Flow, Total Revenue (margin) |
| **Magic Number** | `ticker.financials` | Total Revenue (quarterly delta * 4), SGA Expense |

---

## Internal API Endpoints

### Analysis Endpoints (Existing)

#### Run Forensic Analysis
- **Method:** `GET`
- **Path:** `/api/analyze/{ticker}`
- **Description:** Run complete forensic analysis. Returns cached results if data < 24h old.

**Path Parameters:**
- `ticker`: Stock ticker symbol (1-5 uppercase letters)

**Response (200 OK):**
```json
{
  "ticker": "AAPL",
  "companyProfile": {
    "name": "Apple Inc.",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "marketCap": 2890000000000,
    "fullTimeEmployees": 164000
  },
  "forensicMetrics": {
    "beneishMScore": {
      "composite": -2.45,
      "interpretation": "UNLIKELY_MANIPULATOR",
      "components": {
        "dsri": { "value": 1.02, "citation": { "numerator": "Net Receivables / Revenue (2024)", "denominator": "Net Receivables / Revenue (2023)", "source": "balance_sheet, financials" } },
        "gmi": { "value": 0.98, "citation": {} },
        "aqi": { "value": 1.01, "citation": {} },
        "sgi": { "value": 1.15, "citation": {} },
        "depi": { "value": 0.95, "citation": {} },
        "sgai": { "value": 1.03, "citation": {} },
        "lvgi": { "value": 0.97, "citation": {} },
        "tata": { "value": -0.04, "citation": {} }
      },
      "thresholds": { "likelyManipulator": -1.78, "greyZone": [-2.22, -1.78] }
    },
    "altmanZScore": {
      "standard": { "score": 5.82, "zone": "SAFE", "components": {} },
      "saasModified": { "score": 7.15, "zone": "SAFE", "disclaimer": "Modified variant -- not academically validated" }
    },
    "ruleOf40": {
      "score": 42.3,
      "revenueGrowthPercent": 8.5,
      "fcfMarginPercent": 33.8,
      "interpretation": "PASSING",
      "citations": {}
    },
    "magicNumber": {
      "score": 1.2,
      "netNewARR": 15000000000,
      "salesAndMarketingSpend": 12500000000,
      "interpretation": "EFFICIENT",
      "citations": {}
    }
  },
  "report": {
    "markdown": "## Executive Summary\n\n...\n\n## Bear Case\n\n...",
    "generatedAt": "2026-01-30T12:00:00Z",
    "model": "claude-sonnet-4-20250514"
  },
  "dataSources": {
    "provider": "yfinance",
    "periods": ["2024", "2023", "2022", "2021", "2020"],
    "fetchedAt": "2026-01-30T10:00:00Z",
    "cacheHit": true
  }
}
```

**Error Responses:**
- `400 TICKER_INVALID`: Ticker doesn't match `/^[A-Z]{1,5}$/`
- `404 TICKER_NOT_FOUND`: yfinance returned no data for this ticker
- `422 INSUFFICIENT_DATA`: Fewer than 2 years of financial history
- `429 RATE_LIMITED`: Too many requests
- `502 CLAUDE_ERROR`: Claude API failure
- `504 CLAUDE_TIMEOUT`: Claude API timeout (30s)

---

#### Force Refresh Analysis
- **Method:** `GET`
- **Path:** `/api/analyze/{ticker}/refresh`
- **Description:** Bypass cache, re-fetch from yfinance, regenerate Claude report.

**Response:** Same schema as `/api/analyze/{ticker}` with `cacheHit: false`

---

#### Get Report Only
- **Method:** `GET`
- **Path:** `/api/analyze/{ticker}/report`
- **Description:** Retrieve only the Claude-generated markdown report.

**Response (200 OK):**
```json
{
  "ticker": "AAPL",
  "report": {
    "markdown": "## Executive Summary\n\n...",
    "generatedAt": "2026-01-30T12:00:00Z",
    "model": "claude-sonnet-4-20250514"
  }
}
```

---

### Search Endpoints (Existing)

#### Search Tickers
- **Method:** `GET`
- **Path:** `/api/search`
- **Description:** Search for tickers. Uses a local ticker database or yfinance validation.

**Query Parameters:**
- `q`: Search query (required, 1-50 characters)

**Response (200 OK):**
```json
{
  "results": [
    { "symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "type": "stock" }
  ],
  "query": "AAPL",
  "count": 1
}
```

---

### Portfolio Endpoints (Existing)

#### List Holdings
- **Method:** `GET`
- **Path:** `/api/portfolio`
- **Description:** Get all portfolio holdings with current valuation from Alpaca.

**Response (200 OK):**
```json
{
  "holdings": [
    {
      "id": 1,
      "ticker": "AAPL",
      "shares": 100.0,
      "costBasis": 150.25,
      "purchaseDate": "2024-06-15",
      "currentPrice": 185.50,
      "marketValue": 18550.00,
      "gainLoss": 3525.00,
      "gainLossPercent": 23.46
    }
  ],
  "summary": {
    "totalMarketValue": 18550.00,
    "totalCostBasis": 15025.00,
    "totalGainLoss": 3525.00,
    "holdingCount": 1
  }
}
```

---

#### Add Holding
- **Method:** `POST`
- **Path:** `/api/portfolio`
- **Description:** Add a new holding.

**Request Body:**
```json
{
  "ticker": "AAPL",
  "shares": 100.0,
  "costBasis": 150.25,
  "purchaseDate": "2024-06-15"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "ticker": "AAPL",
  "shares": 100.0,
  "costBasis": 150.25,
  "purchaseDate": "2024-06-15"
}
```

---

#### Update Holding
- **Method:** `PATCH`
- **Path:** `/api/portfolio/{id}`

**Request Body (all optional):**
```json
{ "shares": 150.0, "costBasis": 155.00, "purchaseDate": "2024-07-01" }
```

**Response (200 OK):** Updated holding object.

---

#### Delete Holding
- **Method:** `DELETE`
- **Path:** `/api/portfolio/{id}`

**Response (200 OK):**
```json
{ "message": "Holding deleted", "id": 1 }
```

---

#### Run Portfolio Watchdog
- **Method:** `GET`
- **Path:** `/api/portfolio/watchdog`
- **Description:** Run forensic scan on all holdings. Rate limited to 2/hour.

**Response (200 OK):**
```json
{
  "scannedCount": 5,
  "alertCount": 2,
  "alerts": [
    {
      "id": 1,
      "ticker": "TSLA",
      "alertType": "ZSCORE_ZONE_CHANGE",
      "severity": "HIGH",
      "message": "Altman Z-Score dropped from SAFE (3.2) to GREY (2.5)",
      "previousValue": 3.2,
      "currentValue": 2.5
    }
  ],
  "lastScanAt": "2026-01-30T14:00:00Z"
}
```

---

### Alert Endpoints (Existing)

#### List Alerts
- **Method:** `GET`
- **Path:** `/api/alerts`
- **Query:** `?severity=HIGH&dismissed=false&ticker=TSLA`

**Response (200 OK):**
```json
{
  "alerts": [ { "id": 1, "ticker": "TSLA", "alertType": "ZSCORE_ZONE_CHANGE", "severity": "HIGH", "message": "...", "dismissed": false, "createdAt": "2026-01-30T14:00:00Z" } ],
  "count": 1,
  "undismissedCount": 1
}
```

---

#### Dismiss Alert
- **Method:** `DELETE`
- **Path:** `/api/alerts/{id}`

**Response (200 OK):**
```json
{ "message": "Alert dismissed", "id": 1 }
```

---

## Workflow Endpoints (New)

### List Workflow Runs
- **Method:** `GET`
- **Path:** `/api/workflows`
- **Description:** List all workflow runs, optionally filtered by type and/or status.
- **Authentication:** None (single-user)

**Query Parameters:**
- `type` (optional): Filter by workflow type. Values: `IST`, `HFRT`
- `status` (optional): Filter by status. Values: `PENDING`, `RUNNING`, `PAUSED`, `COMPLETED`, `FAILED`, `CANCELLED`
- `limit` (optional, default 20): Max results
- `offset` (optional, default 0): Pagination offset

**Response (200 OK):**
```json
{
  "workflows": [
    {
      "id": 1,
      "workflowType": "IST",
      "name": "AI Data Center Scarcity Screen",
      "status": "PAUSED",
      "currentPhase": 3,
      "currentPhaseName": "Equity Identification",
      "stepsCompleted": 12,
      "stepsTotal": 25,
      "createdAt": "2026-02-07T10:00:00Z",
      "updatedAt": "2026-02-07T11:30:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

### Create Workflow Run
- **Method:** `POST`
- **Path:** `/api/workflows`
- **Description:** Create a new workflow run. Returns the created workflow in PENDING status.
- **Rate Limit:** 5 per hour

**Request Body:**
```json
{
  "workflowType": "IST",
  "name": "AI Data Center Scarcity Screen",
  "config": {
    "autoAdvance": false,
    "claudeModel": "claude-sonnet-4-20250514",
    "timeoutPerStep": 120
  }
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "workflowType": "IST",
  "name": "AI Data Center Scarcity Screen",
  "status": "PENDING",
  "currentPhase": 0,
  "config": {
    "autoAdvance": false,
    "claudeModel": "claude-sonnet-4-20250514",
    "timeoutPerStep": 120
  },
  "createdAt": "2026-02-07T10:00:00Z"
}
```

**Error Responses:**
- `400`: Invalid workflow type or missing name
- `429 RATE_LIMITED`: Too many workflow creations

---

### Get Workflow Details
- **Method:** `GET`
- **Path:** `/api/workflows/{id}`
- **Description:** Get full workflow details including all steps and their statuses.

**Path Parameters:**
- `id`: Workflow run ID (integer)

**Response (200 OK):**
```json
{
  "id": 1,
  "workflowType": "IST",
  "name": "AI Data Center Scarcity Screen",
  "status": "PAUSED",
  "currentPhase": 2,
  "currentPhaseName": "Thematic Analysis",
  "config": {},
  "steps": [
    {
      "id": 1,
      "stepName": "content_extraction",
      "phase": 1,
      "phaseName": "Content Extraction",
      "status": "COMPLETED",
      "startedAt": "2026-02-07T10:01:00Z",
      "completedAt": "2026-02-07T10:01:45Z",
      "durationMs": 45000,
      "errorMessage": null
    },
    {
      "id": 2,
      "stepName": "source_bias_assessment",
      "phase": 1,
      "phaseName": "Content Extraction",
      "status": "COMPLETED",
      "startedAt": "2026-02-07T10:01:45Z",
      "completedAt": "2026-02-07T10:02:10Z",
      "durationMs": 25000,
      "errorMessage": null
    },
    {
      "id": 3,
      "stepName": "bottleneck_mapping",
      "phase": 2,
      "phaseName": "Thematic Analysis",
      "status": "PENDING",
      "startedAt": null,
      "completedAt": null,
      "durationMs": null,
      "errorMessage": null
    }
  ],
  "createdAt": "2026-02-07T10:00:00Z",
  "updatedAt": "2026-02-07T10:02:10Z"
}
```

**Error Responses:**
- `404 WORKFLOW_NOT_FOUND`: No workflow with this ID

---

### Advance Workflow
- **Method:** `POST`
- **Path:** `/api/workflows/{id}/advance`
- **Description:** Approve a checkpoint and advance to the next phase. Can also start a PENDING workflow. Returns 202 Accepted because execution happens in a background task.

**Request Body (optional):**
```json
{
  "userNotes": "Claims look good, proceed to bottleneck mapping"
}
```

**Response (202 Accepted):**
```json
{
  "id": 1,
  "status": "RUNNING",
  "advancingToPhase": 2,
  "message": "Workflow advancing to Phase 2: Thematic Analysis"
}
```

**Error Responses:**
- `404 WORKFLOW_NOT_FOUND`: No workflow with this ID
- `409 WORKFLOW_INVALID_STATE`: Workflow is not in PENDING or PAUSED state (cannot advance a RUNNING, COMPLETED, FAILED, or CANCELLED workflow)

---

### Pause Workflow
- **Method:** `POST`
- **Path:** `/api/workflows/{id}/pause`
- **Description:** Pause workflow at the current step. The current step will complete, but no further steps will execute.

**Response (200 OK):**
```json
{
  "id": 1,
  "status": "PAUSED",
  "pausedAtStep": "bottleneck_mapping",
  "message": "Workflow paused after current step completes"
}
```

**Error Responses:**
- `404 WORKFLOW_NOT_FOUND`
- `409 WORKFLOW_INVALID_STATE`: Workflow is not RUNNING

---

### Cancel Workflow
- **Method:** `POST`
- **Path:** `/api/workflows/{id}/cancel`
- **Description:** Cancel workflow. The current step will complete, but the workflow status transitions to CANCELLED.

**Response (200 OK):**
```json
{
  "id": 1,
  "status": "CANCELLED",
  "message": "Workflow cancelled"
}
```

**Error Responses:**
- `404 WORKFLOW_NOT_FOUND`
- `409 WORKFLOW_INVALID_STATE`: Workflow is already COMPLETED, FAILED, or CANCELLED

---

### Stream Workflow Progress (SSE)
- **Method:** `GET`
- **Path:** `/api/workflows/{id}/stream`
- **Description:** Server-Sent Events stream for real-time workflow progress. Returns `text/event-stream` content type. Sends heartbeat every 15 seconds. Closes when workflow reaches a terminal state (COMPLETED, FAILED, CANCELLED).

**Response:** `text/event-stream`

**SSE Event Format:**
```
event: step_complete
data: {"type": "step_complete", "stepName": "content_extraction", "phase": 1, "durationMs": 45000, "timestamp": "2026-02-07T10:01:45Z"}

event: checkpoint_reached
data: {"type": "checkpoint_reached", "phase": 1, "nextPhase": 2, "requiresApproval": true, "timestamp": "2026-02-07T10:02:10Z"}

event: heartbeat
data: {"type": "heartbeat", "timestamp": "2026-02-07T10:02:25Z"}
```

**SSE Event Types:**

| Event | Data Fields | Description |
|---|---|---|
| `workflow_started` | `workflowId`, `workflowType` | Workflow execution begins |
| `phase_started` | `phase`, `phaseName` | Phase begins |
| `step_started` | `stepName`, `phase` | Step begins |
| `step_progress` | `stepName`, `message`, `percent` | Optional mid-step progress |
| `step_complete` | `stepName`, `phase`, `durationMs` | Step finished |
| `step_failed` | `stepName`, `phase`, `error` | Step failed |
| `phase_complete` | `phase`, `phaseName` | Phase finished |
| `checkpoint_reached` | `phase`, `nextPhase`, `requiresApproval` | Waiting for user approval |
| `gate_passed` | `gateName`, `details` | Quality gate passed |
| `gate_failed` | `gateName`, `deficiencies` | Quality gate blocked |
| `workflow_complete` | `workflowId`, `durationMs` | Workflow finished |
| `workflow_failed` | `workflowId`, `error` | Workflow failed |
| `heartbeat` | `timestamp` | Keepalive (every 15s) |

**Error Responses:**
- `404 WORKFLOW_NOT_FOUND`

---

## IST (Investment Screening) Endpoints (New)

### Create IST Screen
- **Method:** `POST`
- **Path:** `/api/ist/screens`
- **Description:** Create a new IST investment screen. Creates both an ISTScreen record and an associated WorkflowRun.
- **Rate Limit:** 5 per hour

**Request Body:**
```json
{
  "name": "AI Data Center Scarcity Screen",
  "content": "Full transcript or article text to analyze...",
  "contentType": "podcast_transcript",
  "hypothesis": "AI infrastructure buildout creates multi-year scarcity across power, cooling, and networking",
  "constraints": {
    "minMarketCap": 1000000000,
    "excludeSectors": ["Utilities"],
    "geographicFocus": "US",
    "timeHorizon": "2-5 years"
  },
  "frameworks": ["scarcity_scoring", "bottleneck_cascade"]
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "workflowRunId": 1,
  "name": "AI Data Center Scarcity Screen",
  "status": "PENDING",
  "contentType": "podcast_transcript",
  "hypothesis": "AI infrastructure buildout creates multi-year scarcity across power, cooling, and networking",
  "createdAt": "2026-02-07T10:00:00Z"
}
```

**Error Responses:**
- `400`: Missing name or content
- `429 RATE_LIMITED`: Too many screen creations

---

### List IST Screens
- **Method:** `GET`
- **Path:** `/api/ist/screens`
- **Description:** List all IST screens with summary info.

**Query Parameters:**
- `status` (optional): Filter by status
- `limit` (optional, default 20): Max results
- `offset` (optional, default 0): Pagination offset

**Response (200 OK):**
```json
{
  "screens": [
    {
      "id": 1,
      "name": "AI Data Center Scarcity Screen",
      "status": "COMPLETED",
      "workflowRunId": 1,
      "claimCount": 24,
      "candidateCount": 18,
      "tier1Count": 6,
      "currentPhase": 5,
      "createdAt": "2026-02-07T10:00:00Z",
      "updatedAt": "2026-02-07T14:30:00Z"
    }
  ],
  "total": 1
}
```

---

### Get IST Screen Detail
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}`
- **Description:** Get full screen detail including screening brief, content extraction summary, and current workflow state.

**Response (200 OK):**
```json
{
  "id": 1,
  "workflowRunId": 1,
  "name": "AI Data Center Scarcity Screen",
  "status": "COMPLETED",
  "screeningBrief": {
    "hypothesis": "AI infrastructure buildout creates multi-year scarcity...",
    "contentType": "podcast_transcript",
    "constraints": { "minMarketCap": 1000000000 },
    "frameworks": ["scarcity_scoring", "bottleneck_cascade"]
  },
  "contentExtraction": {
    "totalClaims": 24,
    "claimsWithQuantAnchors": 18,
    "claimsWithTemporalMarkers": 12,
    "sourceBias": { "rating": "moderate", "notes": "Single podcast source, industry insider perspective" }
  },
  "currentPhase": 5,
  "createdAt": "2026-02-07T10:00:00Z",
  "updatedAt": "2026-02-07T14:30:00Z"
}
```

**Error Responses:**
- `404 SCREEN_NOT_FOUND`

---

### Get Screen Claims
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/claims`
- **Description:** Get all extracted claims for this screen.

**Query Parameters:**
- `validated` (optional): Filter by validation status (`true`/`false`)
- `hasQuantAnchor` (optional): Filter claims with quantitative anchors

**Response (200 OK):**
```json
{
  "screenId": 1,
  "claims": [
    {
      "id": 1,
      "claimText": "Each 1 GW AI cluster requires 330,000 GB300 GPUs",
      "sourceCitation": "Podcast transcript, timestamp 12:45",
      "quantitativeAnchor": "330000 GPUs per GW",
      "temporalMarker": "2025-2027",
      "bottleneckName": "GPU Supply",
      "confidence": 0.85,
      "isValidated": true,
      "validationVerdict": "confirmed",
      "validationSource": "NVIDIA earnings call Q3 2025"
    }
  ],
  "totalCount": 24,
  "validatedCount": 20
}
```

---

### Get Bottleneck Map
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/bottlenecks`
- **Description:** Get the temporal bottleneck cascade for this screen.

**Response (200 OK):**
```json
{
  "screenId": 1,
  "bottlenecks": [
    {
      "id": 1,
      "name": "GPU Supply Scarcity",
      "phase": 1,
      "phaseLabel": "Near-term (0-18 months)",
      "description": "NVIDIA GB300 production capacity insufficient for 2025-2026 AI cluster buildout demand",
      "quantitativeEvidence": "330K GPUs/GW cluster, 5+ GW announced, TSMC CoWoS capacity constrained",
      "temporalMarker": "2025-2026",
      "resolutionTrigger": "TSMC CoWoS expansion + competitor GPUs (AMD MI400)"
    },
    {
      "id": 2,
      "name": "Power Infrastructure Gap",
      "phase": 2,
      "phaseLabel": "Mid-term (18-36 months)",
      "description": "Grid interconnection queue exceeds 5 years; data center power demand growing 15% CAGR",
      "quantitativeEvidence": "1.4 GW cooling overhead per GW compute, 2000+ GW in interconnection queue",
      "temporalMarker": "2026-2028",
      "resolutionTrigger": "Modular nuclear deployment, grid modernization policy"
    }
  ],
  "phaseCount": { "phase1": 3, "phase2": 2, "phase3": 1, "crossCutting": 1 }
}
```

---

### Get Demand Models
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/demand-models`
- **Description:** Get quantitative demand models derived from bottleneck analysis.

**Response (200 OK):**
```json
{
  "screenId": 1,
  "demandModels": [
    {
      "id": 1,
      "bottleneckId": 1,
      "bottleneckName": "GPU Supply Scarcity",
      "formula": "1 GW cluster = 330K GB300 x $30K ASP = $9.9B GPU spend per GW",
      "baseCase": { "demand": "15 GW by 2027", "tam": 148500000000 },
      "bullCase": { "demand": "25 GW by 2027", "tam": 247500000000 },
      "bearCase": { "demand": "8 GW by 2027", "tam": 79200000000 },
      "sensitivityTable": [
        { "variable": "GPU ASP", "lowCase": 25000, "baseCase": 30000, "highCase": 40000, "tamImpact": "-17% / base / +33%" }
      ],
      "multiplierChain": "GPUs -> CoWoS packaging -> HBM memory -> power delivery -> cooling"
    }
  ]
}
```

---

### Get Validation Results
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/validation`
- **Description:** Get external validation results for claims (via Claude web_search tool).

**Response (200 OK):**
```json
{
  "screenId": 1,
  "validations": [
    {
      "id": 1,
      "claimId": 1,
      "claimText": "Each 1 GW AI cluster requires 330,000 GB300 GPUs",
      "verdict": "confirmed",
      "confidence": 0.9,
      "evidence": "NVIDIA CEO Jensen Huang confirmed similar figures at GTC 2025",
      "sources": [
        { "url": "https://example.com/nvidia-gtc-2025", "title": "NVIDIA GTC 2025 Keynote Summary" }
      ],
      "searchQueries": ["NVIDIA GB300 GPUs per GW cluster", "AI data center GPU density requirements"],
      "validatedAt": "2026-02-07T10:15:00Z"
    }
  ],
  "summary": {
    "confirmed": 14,
    "partiallyConfirmed": 5,
    "contradicted": 1,
    "unvalidatable": 4,
    "total": 24
  }
}
```

---

### Get Equity Candidates
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/candidates`
- **Description:** Get identified equity candidates with scarcity scores and moat evidence.

**Query Parameters:**
- `tier` (optional): Filter by tier (1, 2, 3)
- `bottleneckId` (optional): Filter by associated bottleneck

**Response (200 OK):**
```json
{
  "screenId": 1,
  "candidates": [
    {
      "id": 1,
      "ticker": "NVDA",
      "companyName": "NVIDIA Corporation",
      "bottleneckId": 1,
      "bottleneckName": "GPU Supply Scarcity",
      "scarcityScore": {
        "overall": 4.6,
        "dimensions": {
          "supplyConstraint": 5.0,
          "demandVisibility": 4.5,
          "substitutionDifficulty": 4.8,
          "pricingPower": 4.5,
          "temporalUrgency": 4.2
        }
      },
      "moatType": "Scale + IP + Ecosystem",
      "moatEvidence": "CUDA ecosystem lock-in, 90%+ AI training GPU share, TSMC priority allocation",
      "catalyst": "GB300 ramp Q2 2026",
      "tier": 1,
      "phase": 1,
      "conviction": "HIGH"
    }
  ],
  "tierBreakdown": { "tier1": 6, "tier2": 7, "tier3": 5 },
  "totalCount": 18
}
```

---

### Get Tier Classification
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/tiers`
- **Description:** Get tier classification grouped view with classification rationale.

**Response (200 OK):**
```json
{
  "screenId": 1,
  "tiers": {
    "tier1": {
      "label": "High Conviction",
      "criteria": "Scarcity >= 4.0, valuation data present, moat verified, multi-source",
      "candidates": [
        { "ticker": "NVDA", "companyName": "NVIDIA", "scarcityScore": 4.6, "catalyst": "GB300 ramp" }
      ],
      "count": 6
    },
    "tier2": {
      "label": "Watchlist",
      "criteria": "Scarcity 3.0-3.9 or missing one Tier 1 criterion",
      "candidates": [],
      "count": 7
    },
    "tier3": {
      "label": "Speculative",
      "criteria": "Below Tier 2 thresholds",
      "candidates": [],
      "count": 5
    }
  }
}
```

---

### Get Effects Map
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/effects`
- **Description:** Get multi-order effects chains (1st, 2nd, 3rd order downstream effects).

**Response (200 OK):**
```json
{
  "screenId": 1,
  "effectsChains": [
    {
      "id": 1,
      "thesis": "GPU scarcity persists through 2027",
      "order": 1,
      "effectDescription": "NVIDIA revenue exceeds $200B, margin expansion continues",
      "equityCandidateId": 1,
      "equityTicker": "NVDA"
    },
    {
      "id": 2,
      "thesis": "GPU scarcity persists through 2027",
      "order": 2,
      "effectDescription": "Liquid cooling becomes mandatory for all new builds, TAM expands 5x",
      "equityCandidateId": 5,
      "equityTicker": "VRT"
    }
  ]
}
```

---

### Check Invariants
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/invariants`
- **Description:** Run all 8 IST screening invariants and return pass/fail status for each.

**Response (200 OK):**
```json
{
  "screenId": 1,
  "invariants": [
    { "id": "INV-1", "name": "Source Citation Required", "status": "PASS", "details": "All 24 claims have source citations" },
    { "id": "INV-2", "name": "Quantitative Anchor Required", "status": "PASS", "details": "18/24 claims have quantitative anchors (75%, threshold: 50%)" },
    { "id": "INV-3", "name": "Temporal Marker Required", "status": "PASS", "details": "12/24 claims have temporal markers" },
    { "id": "INV-4", "name": "No Orphan Equities", "status": "PASS", "details": "All 18 candidates linked to at least one bottleneck" },
    { "id": "INV-5", "name": "Tier Justification Required", "status": "PASS", "details": "All tier assignments have scarcity score backing" },
    { "id": "INV-6", "name": "Dialectic Isolation", "status": "PASS", "details": "Optimist and Pessimist outputs generated independently" },
    { "id": "INV-7", "name": "Anti-Hallucination Compliance", "status": "PASS", "details": "No new figures in synthesis that are not in prior phases" },
    { "id": "INV-8", "name": "Report Completeness", "status": "PASS", "details": "All required sections present in Investment Thesis Report" }
  ],
  "allPassed": true,
  "passCount": 8,
  "failCount": 0
}
```

---

### Trigger Dialectic
- **Method:** `POST`
- **Path:** `/api/ist/screens/{id}/dialectic`
- **Description:** Trigger dialectic scrutiny. Runs optimist and pessimist analyses in parallel (asyncio.gather), then runs synthesis. Returns 202 Accepted because execution happens as part of the workflow background task.

**Response (202 Accepted):**
```json
{
  "screenId": 1,
  "message": "Dialectic analysis started: optimist and pessimist running in parallel",
  "status": "RUNNING"
}
```

**Error Responses:**
- `404 SCREEN_NOT_FOUND`
- `409 WORKFLOW_INVALID_STATE`: Screen has not completed Phase 3 (prerequisite)

---

### Get Dialectic Review
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/dialectic/{side}`
- **Description:** Get a specific dialectic review (optimist, pessimist, or synthesis).

**Path Parameters:**
- `side`: One of `optimist`, `pessimist`, `synthesis`

**Response (200 OK):**
```json
{
  "screenId": 1,
  "side": "optimist",
  "content": {
    "narrative": "Full optimist analysis markdown...",
    "keyArguments": [
      "GPU scarcity persists 3+ years due to physics constraints, not just demand",
      "Cooling TAM 5x expansion is underappreciated by market"
    ],
    "tierAdjustments": [
      { "ticker": "VRT", "currentTier": 2, "proposedTier": 1, "rationale": "Cooling monopoly position stronger than scarcity score suggests" }
    ],
    "convictionLevel": "HIGH",
    "riskDiscount": 0.15
  },
  "createdAt": "2026-02-07T12:00:00Z"
}
```

**Error Responses:**
- `404`: Screen or dialectic review not found

---

### Get Synthesis
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/synthesis`
- **Description:** Get the dialectic synthesis report that reconciles optimist and pessimist views.

**Response (200 OK):**
```json
{
  "screenId": 1,
  "synthesis": {
    "narrative": "Full synthesis markdown...",
    "disagreements": [
      {
        "topic": "GPU scarcity duration",
        "optimistView": "3+ years due to physics constraints",
        "pessimistView": "18 months, AMD MI400 closes gap",
        "resolution": "Partial agreement: 2+ years for training GPUs, inference diversifies sooner",
        "impactOnTiers": "No tier changes"
      }
    ],
    "finalTierAdjustments": [
      { "ticker": "VRT", "originalTier": 2, "finalTier": 1, "rationale": "Both sides agree on cooling criticality" }
    ],
    "overallConviction": "HIGH",
    "keyRisks": ["TSMC capacity expansion faster than modeled", "Inference shift to custom silicon"]
  },
  "createdAt": "2026-02-07T12:15:00Z"
}
```

---

### Get Master Screen
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/master-screen`
- **Description:** Get the final ranked equity screen with conviction scores and invariant compliance.

**Response (200 OK):**
```json
{
  "screenId": 1,
  "rankedEquities": [
    {
      "rank": 1,
      "ticker": "NVDA",
      "companyName": "NVIDIA Corporation",
      "tier": 1,
      "scarcityScore": 4.6,
      "convictionScore": 92,
      "pillar": "GPU Supply",
      "catalyst": "GB300 ramp Q2 2026",
      "priceAtScreen": 145.50,
      "peRatio": 35.2,
      "marketCap": 3500000000000
    }
  ],
  "invariantCompliance": {
    "allPassed": true,
    "checkedAt": "2026-02-07T13:00:00Z"
  },
  "totalEquities": 18,
  "tier1Count": 6
}
```

---

### Get Rotation Strategy
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/rotation`
- **Description:** Get the phase-based rotation strategy with allocation percentages and triggers.

**Response (200 OK):**
```json
{
  "screenId": 1,
  "phaseAllocations": [
    {
      "phase": 1,
      "phaseLabel": "Near-term (0-18 months)",
      "allocationPercent": 50,
      "tickers": ["NVDA", "AVGO", "TSM"],
      "rationale": "Highest conviction, most imminent catalysts"
    },
    {
      "phase": 2,
      "phaseLabel": "Mid-term (18-36 months)",
      "allocationPercent": 35,
      "tickers": ["VRT", "EQIX", "PWR"],
      "rationale": "Infrastructure buildout beneficiaries"
    }
  ],
  "rotationTriggers": [
    {
      "trigger": "TSMC CoWoS capacity doubles",
      "action": "Reduce Phase 1 GPU names by 20%, rotate to Phase 2 infra",
      "monitorMetric": "TSMC quarterly CoWoS wafer output"
    }
  ],
  "riskLimits": {
    "maxSingleName": 10,
    "maxSinglePillar": 30,
    "maxTier3Allocation": 15
  }
}
```

---

### Get Catalyst Calendar
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/catalysts`
- **Description:** Get the dated catalyst calendar with associated tickers and expected impact.

**Response (200 OK):**
```json
{
  "screenId": 1,
  "catalysts": [
    {
      "date": "2026-03-15",
      "dateType": "approximate",
      "event": "NVIDIA GTC 2026 - GB300 production update",
      "tickers": ["NVDA"],
      "expectedImpact": "Confirmation of supply timeline, potential upside to GPU ASP guidance",
      "pillar": "GPU Supply",
      "importance": "HIGH"
    },
    {
      "date": "2026-06-01",
      "dateType": "quarter",
      "event": "TSMC CoWoS capacity expansion completion",
      "tickers": ["TSM", "NVDA", "AVGO"],
      "expectedImpact": "Eases packaging bottleneck, watch for GPU supply acceleration",
      "pillar": "GPU Supply",
      "importance": "HIGH"
    }
  ],
  "totalCatalysts": 12,
  "nextCatalyst": {
    "date": "2026-03-15",
    "event": "NVIDIA GTC 2026",
    "daysUntil": 36
  }
}
```

---

### Get Stress Tests
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/stress-tests`
- **Description:** Get framework-level and name-level stress test results with survival scores.

**Response (200 OK):**
```json
{
  "screenId": 1,
  "frameworkTests": [
    {
      "framework": "Thesis Inversion",
      "scenario": "AI investment cycle peaks in 2026, capex cuts by 30%",
      "impact": "Phase 1 names drop 40-50%, Phase 2 names delayed but resilient",
      "survivorTickers": ["EQIX", "VRT"],
      "casualtyTickers": ["NVDA", "AVGO"]
    }
  ],
  "nameTests": [
    {
      "ticker": "NVDA",
      "companyName": "NVIDIA",
      "scenarios": [
        { "scenario": "AMD MI400 achieves performance parity", "impactSeverity": "HIGH", "survivalScore": 3.5 },
        { "scenario": "China export restrictions tighten further", "impactSeverity": "MEDIUM", "survivalScore": 4.0 }
      ],
      "overallSurvivalScore": 3.8
    }
  ],
  "survivalScores": {
    "averageTier1": 4.1,
    "averageTier2": 3.5,
    "lowestSurvivor": { "ticker": "SMCI", "score": 2.8 }
  }
}
```

---

### Get Investment Thesis Report (PRIMARY DELIVERABLE)
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/report`
- **Description:** Get the Investment Thesis Report -- the primary deliverable of the IST pipeline. This is a unified narrative markdown document synthesizing all analysis phases into a self-contained research report.

**Response (200 OK):**
```json
{
  "screenId": 1,
  "report": {
    "id": 1,
    "title": "AI Infrastructure Scarcity: A Multi-Year Investment Thesis",
    "content": "# AI Infrastructure Scarcity: A Multi-Year Investment Thesis\n\n## I. Executive Summary\n\n...\n\n## II. Pillar-by-Pillar Analysis\n\n### Pillar 1: GPU Supply Scarcity\n\n...\n\n> **SKEPTIC'S STRESS TEST:** ...\n\n## III. Second & Third-Order Effects\n\n...\n\n## V. Portfolio Construction Guidance\n\n...\n\n## VI. Disclaimer\n\n...",
    "metadata": {
      "pillarCount": 4,
      "equityCount": 18,
      "tier1Count": 6,
      "tier2Count": 7,
      "tier3Count": 5,
      "wordCount": 8500,
      "generatedAt": "2026-02-07T13:30:00Z",
      "model": "claude-sonnet-4-20250514"
    }
  },
  "createdAt": "2026-02-07T13:30:00Z"
}
```

**Error Responses:**
- `404 SCREEN_NOT_FOUND`
- `404`: Report not yet generated (workflow has not reached Phase 5, Step 5.5)

---

### Get HFRT Handoff Data
- **Method:** `GET`
- **Path:** `/api/ist/screens/{id}/handoff`
- **Description:** Get handoff data for bridging Tier 1 equity candidates to HFRT deep research projects.

**Response (200 OK):**
```json
{
  "screenId": 1,
  "screenName": "AI Data Center Scarcity Screen",
  "tier1Candidates": [
    {
      "ticker": "NVDA",
      "companyName": "NVIDIA Corporation",
      "thesis": "Dominant GPU supplier for AI training, GB300 cycle drives multi-year revenue growth",
      "bottleneckExposure": "GPU Supply Scarcity (Phase 1)",
      "scarcityScore": 4.6,
      "catalyst": "GB300 ramp Q2 2026",
      "tierRationale": "Highest scarcity score, verified moat, multi-source validation"
    }
  ],
  "totalTier1": 6,
  "screenCompletedAt": "2026-02-07T14:00:00Z"
}
```

---

## Framework Endpoints (New)

### List IST Frameworks
- **Method:** `GET`
- **Path:** `/api/frameworks/ist`
- **Description:** List available IST framework summaries.

**Response (200 OK):**
```json
{
  "frameworks": [
    {
      "name": "scarcity_scoring",
      "displayName": "Scarcity Scoring Framework",
      "description": "5-dimension scarcity assessment: supply constraint, demand visibility, substitution difficulty, pricing power, temporal urgency",
      "category": "equity_analysis"
    },
    {
      "name": "bottleneck_cascade",
      "displayName": "Temporal Bottleneck Cascade",
      "description": "Phase 1 (near-term) / Phase 2 (mid-term) / Phase 3 (secular) bottleneck mapping with causal dependencies",
      "category": "thematic_analysis"
    }
  ],
  "totalCount": 7
}
```

---

### Get IST Framework Detail
- **Method:** `GET`
- **Path:** `/api/frameworks/ist/{name}`
- **Description:** Get full framework content (rendered markdown).

**Path Parameters:**
- `name`: Framework identifier (e.g., `scarcity_scoring`, `bottleneck_cascade`)

**Response (200 OK):**
```json
{
  "name": "scarcity_scoring",
  "displayName": "Scarcity Scoring Framework",
  "content": "# Scarcity Scoring Framework\n\n## Dimensions\n\n### 1. Supply Constraint (1-5)\n...",
  "scoringSchema": {
    "dimensions": ["supplyConstraint", "demandVisibility", "substitutionDifficulty", "pricingPower", "temporalUrgency"],
    "scale": { "min": 1, "max": 5 },
    "tierThresholds": { "tier1": 4.0, "tier2": 3.0 }
  }
}
```

**Error Responses:**
- `404`: Framework not found

---

## Alpaca Paper Trading Integration (Existing)

**Base URL:** `https://paper-api.alpaca.markets`

**Headers:**
```
APCA-API-KEY-ID: {ALPACA_API_KEY}
APCA-API-SECRET-KEY: {ALPACA_SECRET_KEY}
```

**Endpoints Used:**
- `GET /v2/account` -- Account info and buying power
- `GET /v2/positions` -- Current positions
- `GET /v1/bars/{timeframe}?symbols={symbols}` -- Historical price bars
- `GET /v2/assets/{symbol}` -- Asset info and current price

---

**Created:** 2026-01-30
**Last Updated:** 2026-02-07
**Owner:** @Chief_Architect
