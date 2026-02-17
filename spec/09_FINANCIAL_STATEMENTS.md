# 09 - Financial Statements Feature Architecture

## Overview

Add three new tabs to the analysis page -- **Income Stmt**, **Balance Sheet**, **Cash Flow** -- that display raw financial statement line items from 10-K filings over the last 4-5 fiscal years. The data already exists in the yfinance DataFrames (`ticker.financials`, `ticker.balance_sheet`, `ticker.cashflow`) and is already being fetched and cached by `yfinance_service.py`. This feature pipes that raw data through to the frontend with minimal transformation.

This is a **read-through feature**, not a computation engine. No new calculations. No new AI prompts. Just serialize the DataFrames the backend already has and render them in Bloomberg-style tables.

---

## 1. Data Format: yfinance DataFrame to JSON

### Current State

`yfinance_service.py` already fetches annual `financials`, `balance_sheet`, and `cashflow` DataFrames and serializes them via `df.to_json(date_format="iso")`. The resulting JSON shape (stored in cache and returned by `fetch_financial_data()`) is:

```json
{
  "financials": {
    "2024-09-28T00:00:00.000Z": {
      "Total Revenue": 391035000000,
      "Cost Of Revenue": 210352000000,
      "Gross Profit": 180683000000,
      ...
    },
    "2023-09-30T00:00:00.000Z": { ... },
    "2022-10-01T00:00:00.000Z": { ... },
    "2021-09-25T00:00:00.000Z": { ... }
  }
}
```

The structure is `{ [isoDateColumn]: { [lineItemRow]: numberOrNull } }`. Columns are fiscal period end dates (typically 4 annual periods). Rows are line item names as strings. Values are raw dollar amounts (not scaled) or null.

### Target JSON Format for the Frontend

The raw yfinance format is column-oriented (period -> line items). For table rendering, the frontend needs a row-oriented structure with explicit metadata. The backend will transform each DataFrame into a `FinancialStatement` object:

```json
{
  "periods": ["2024-09-28", "2023-09-30", "2022-10-01", "2021-09-25"],
  "line_items": [
    {
      "label": "Total Revenue",
      "values": [391035000000, 383285000000, 394328000000, 365817000000]
    },
    {
      "label": "Cost Of Revenue",
      "values": [210352000000, 214137000000, 223546000000, 212981000000]
    },
    {
      "label": "Gross Profit",
      "values": [180683000000, 169148000000, 170782000000, 152836000000]
    }
  ]
}
```

**Design decisions:**

1. **Row-oriented, not column-oriented.** The frontend renders rows as table `<tr>` elements. Row-oriented JSON maps directly to the render loop with no client-side transposition.

2. **Periods as a separate ordered array.** The frontend uses `periods` as table column headers. Ordering is most-recent-first (descending by date). The backend handles this sort, not the frontend.

3. **Values array is positionally aligned with periods.** `line_items[i].values[j]` corresponds to `periods[j]`. No key lookups needed in the render loop.

4. **Raw numbers, not formatted strings.** The frontend owns formatting (commas, units, negative display). The backend sends raw `number | null` values.

5. **Line item order preserved from yfinance.** yfinance returns line items in a logical financial statement order (Revenue -> COGS -> Gross Profit -> ... -> Net Income). We preserve that order rather than alphabetizing, because the accounting hierarchy matters.

6. **Null values for missing data.** If a line item does not exist for a given period, the value is `null`. The frontend renders this as "--" or a blank cell.

### Why Not Just Pass the Raw yfinance JSON?

The raw format (`{ period: { lineItem: value } }`) has problems:

- Column-oriented requires client-side transposition to render rows
- Period keys are ISO timestamps with timezone info that need parsing
- No guaranteed key ordering in JSON objects (though modern JS preserves insertion order, it is not a spec guarantee we should rely on)
- The frontend would need to compute the union of all line items across periods (not all periods have the same items)
- It mixes the data format concern with the presentation concern

The transformation is trivial (10 lines of Python) and belongs in the backend.

---

## 2. Backend Changes

### 2A. New Schema Models

**File:** `backend/app/schemas/analysis.py`

Add three models at the bottom of the file, before `AnalysisResponse`:

```python
class FinancialStatementLineItem(BaseModel):
    label: str
    values: list[float | None]


class FinancialStatement(BaseModel):
    periods: list[str] = []
    line_items: list[FinancialStatementLineItem] = []


class FinancialStatements(BaseModel):
    income_statement: FinancialStatement = FinancialStatement()
    balance_sheet: FinancialStatement = FinancialStatement()
    cash_flow: FinancialStatement = FinancialStatement()
```

Update `AnalysisResponse` to include the new field:

```python
class AnalysisResponse(BaseModel):
    ticker: str
    company_profile: CompanyProfile = CompanyProfile()
    forensic_metrics: ForensicMetrics = ForensicMetrics()
    comprehensive_analysis: ComprehensiveAnalysis = ComprehensiveAnalysis()
    report: ForensicReport = ForensicReport()
    data_sources: DataSources = DataSources()
    financial_statements: FinancialStatements = FinancialStatements()  # NEW

    model_config = {"populate_by_name": True}
```

**Rationale for adding to the existing response rather than a separate endpoint:**

- The data is already fetched by the same `fetch_financial_data()` call. A separate endpoint would either duplicate the fetch or require a cache lookup.
- The payload increase is modest. Each statement has ~30-50 line items x 4 periods = ~200 numbers per statement, ~600 total. At ~15 bytes per number, that is ~9KB of additional JSON. The current response is already 50-100KB with the Claude report. This is negligible.
- A separate endpoint would add latency for the user (two sequential API calls) and complexity for no benefit.

### 2B. DataFrame Transformation Utility

**File:** `backend/app/services/yfinance_service.py`

Add a new function alongside the existing `_df_to_json`:

```python
def transform_statement(raw_dict: dict) -> dict:
    """Transform column-oriented yfinance dict to row-oriented FinancialStatement format.

    Input:  { "2024-09-28T00:00:00.000Z": { "Total Revenue": 391035000000, ... }, ... }
    Output: { "periods": ["2024-09-28", ...], "line_items": [{ "label": "...", "values": [...] }, ...] }
    """
    if not raw_dict:
        return {"periods": [], "line_items": []}

    # Sort periods descending (most recent first)
    sorted_periods = sorted(raw_dict.keys(), reverse=True)

    # Truncate period keys to date-only (YYYY-MM-DD)
    periods = [p[:10] for p in sorted_periods]

    # Collect the union of all line item labels, preserving first-seen order
    seen_labels = {}
    for period_key in sorted_periods:
        items = raw_dict.get(period_key, {})
        if isinstance(items, dict):
            for label in items:
                if label not in seen_labels:
                    seen_labels[label] = True

    # Build row-oriented line items
    line_items = []
    for label in seen_labels:
        values = []
        for period_key in sorted_periods:
            items = raw_dict.get(period_key, {})
            val = items.get(label) if isinstance(items, dict) else None
            # Convert NaN-like values to None for clean JSON serialization
            if val is not None:
                try:
                    float_val = float(val)
                    values.append(None if float_val != float_val else float_val)  # NaN check
                except (ValueError, TypeError):
                    values.append(None)
            else:
                values.append(None)
        line_items.append({"label": label, "values": values})

    return {"periods": periods, "line_items": line_items}
```

This function operates on the already-parsed dict (from `json.loads(raw_json)`), not the raw DataFrame. This is important because the data may come from cache (already JSON) rather than a fresh yfinance fetch.

### 2C. Router Changes

**File:** `backend/app/routers/analyze.py`

In `_build_response()`, after building `sources` and before the `return`, add:

```python
from app.services.yfinance_service import transform_statement
from app.schemas.analysis import FinancialStatements, FinancialStatement

# Build financial statements from raw cached data
financial_statements = FinancialStatements(
    income_statement=FinancialStatement(**transform_statement(data.get("financials", {}))),
    balance_sheet=FinancialStatement(**transform_statement(data.get("balance_sheet", {}))),
    cash_flow=FinancialStatement(**transform_statement(data.get("cashflow", {}))),
)
```

And pass it into the `AnalysisResponse` constructor:

```python
return AnalysisResponse(
    ticker=ticker,
    company_profile=profile,
    forensic_metrics=forensic_metrics,
    comprehensive_analysis=comprehensive,
    report=report,
    data_sources=sources,
    financial_statements=financial_statements,  # NEW
)
```

### 2D. No Database Changes Needed

The financial statement data is derived from the already-cached yfinance DataFrames. There is no need to add a column to `analysis_reports`. The `FinancialStatements` object is computed on-the-fly from the cached raw data each time the analysis endpoint is called. This avoids schema migration overhead and data duplication.

### 2E. No Changes to yfinance_service.py Fetch Logic

The existing `fetch_financial_data()` already fetches `financials`, `balance_sheet`, and `cashflow` for every ticker. It already caches them for 24 hours. yfinance typically returns 4 annual periods. No changes needed to the fetch logic.

---

## 3. Frontend Changes

### 3A. New TypeScript Interfaces

**File:** `frontend/types/analysis.ts`

Add at the bottom, before the `AnalysisResponse` interface:

```typescript
export interface FinancialStatementLineItem {
  label: string;
  values: (number | null)[];
}

export interface FinancialStatement {
  periods: string[];
  line_items: FinancialStatementLineItem[];
}

export interface FinancialStatements {
  income_statement: FinancialStatement;
  balance_sheet: FinancialStatement;
  cash_flow: FinancialStatement;
}
```

Update `AnalysisResponse`:

```typescript
export interface AnalysisResponse {
  ticker: string;
  company_profile: CompanyProfile;
  forensic_metrics: ForensicMetrics;
  comprehensive_analysis: ComprehensiveAnalysis;
  report: ForensicReport;
  data_sources: DataSources;
  financial_statements: FinancialStatements;  // NEW
}
```

### 3B. New Component: FinancialStatementTable

**File:** `frontend/components/FinancialStatementTable.tsx` (NEW)

A reusable Bloomberg-style data table component that renders a single `FinancialStatement` object. This is the core visual component for all three tabs.

**Props:**

```typescript
interface FinancialStatementTableProps {
  statement: FinancialStatement;
  title: string;  // "Income Statement", "Balance Sheet", "Cash Flow Statement"
}
```

**Behavior and design requirements:**

1. **Table structure:**
   - First column: line item labels (left-aligned, sticky on horizontal scroll)
   - Subsequent columns: one per fiscal period (right-aligned, monospace numbers)
   - Column headers: fiscal year formatted as "FY 2024" or "Sep 2024" (derived from period date)

2. **Number formatting:**
   - Values are raw dollar amounts. Display in millions: divide by 1,000,000 and show one decimal place
   - Add a "($ in millions)" subtitle below the table title
   - Use `Intl.NumberFormat` or the existing `formatLargeNumber` utility, but adapted for table density
   - Commas as thousands separators: `180,683.0`
   - Negative values displayed in parentheses: `(5,234.1)` and colored with `text-bear` (#FF1744)
   - Null/missing values displayed as `--` in `text-text-tertiary`

3. **Styling (per design system spec/05_DESIGN_SYSTEM.md):**
   - Dense row height: 36px (matches "Bloomberg Style" data table spec)
   - Alternating row backgrounds: `bg-surface` / `bg-background`
   - Header row: `bg-surface-elevated`, `text-text-secondary`, uppercase, 11px caption font, `border-b-2`
   - All number cells: `font-mono`, `tabular-nums`, `text-sm` (14px)
   - Label cells: `text-sm`, `font-medium`, `text-text-primary`
   - Hover row: `bg-surface-elevated` transition
   - Table border: `border-2 border-border-strong` (Neo-Brutalism)
   - No rounded corners (`radius-none`)

4. **Scrolling:**
   - Vertical: natural page scroll (no inner scroll container)
   - Horizontal: `overflow-x-auto` on a wrapper div for narrow viewports
   - First column (labels): `sticky left-0` with `bg-surface` to remain visible during horizontal scroll

5. **Sort toggle (stretch goal):**
   - Clicking a period column header sorts all rows by that column's values (desc then asc toggle)
   - Default sort: preserve yfinance order (logical accounting hierarchy)
   - Sort indicator: small arrow in column header

6. **Empty state:**
   - If `statement.line_items` is empty or `statement.periods` is empty, show: "No data available for this statement."

### 3C. New Tab Panel Components

Three thin wrapper components, one per tab. Each simply renders `FinancialStatementTable` with the correct data slice. These are intentionally thin -- the table component does the heavy lifting.

**File:** `frontend/components/IncomeStatementPanel.tsx` (NEW)

```typescript
interface IncomeStatementPanelProps {
  statement: FinancialStatement;
}

export default function IncomeStatementPanel({ statement }: IncomeStatementPanelProps) {
  return (
    <FinancialStatementTable
      statement={statement}
      title="Income Statement"
    />
  );
}
```

**File:** `frontend/components/BalanceSheetPanel.tsx` (NEW)

```typescript
interface BalanceSheetPanelProps {
  statement: FinancialStatement;
}

export default function BalanceSheetPanel({ statement }: BalanceSheetPanelProps) {
  return (
    <FinancialStatementTable
      statement={statement}
      title="Balance Sheet"
    />
  );
}
```

**File:** `frontend/components/CashFlowPanel.tsx` (NEW)

```typescript
interface CashFlowPanelProps {
  statement: FinancialStatement;
}

export default function CashFlowPanel({ statement }: CashFlowPanelProps) {
  return (
    <FinancialStatementTable
      statement={statement}
      title="Cash Flow Statement"
    />
  );
}
```

**Why three separate panel components instead of just using FinancialStatementTable directly?**

Consistency with the existing architecture. Every tab has a dedicated panel component (`MacroContextPanel`, `FundamentalsPanel`, `ForensicPanel`, etc.). The panel components are the unit of composition in the page layout. Even if they are thin wrappers today, they provide a natural place to add statement-specific features later (e.g., a "Key Metrics" summary card above the income statement table, or a "Working Capital" callout on the balance sheet).

### 3D. Tab Bar Changes

**File:** `frontend/components/AnalysisTabs.tsx` (MODIFY)

Add three new entries to the `TABS` array. Use icons from the existing Lucide React library:

```typescript
import {
  Globe,
  BarChart3,
  Search,
  DollarSign,
  Users,
  FileText,
  Table2,         // NEW - for Income Stmt
  Landmark,       // NEW - for Balance Sheet
  ArrowLeftRight, // NEW - for Cash Flow
} from "lucide-react";

const TABS = [
  { id: "macro", label: "Macro", icon: Globe },
  { id: "fundamentals", label: "Fundamentals", icon: BarChart3 },
  { id: "forensic", label: "Forensic", icon: Search },
  { id: "valuation", label: "Valuation", icon: DollarSign },
  { id: "sentiment", label: "Sentiment", icon: Users },
  { id: "income-stmt", label: "Income Stmt", icon: Table2 },           // NEW
  { id: "balance-sheet", label: "Balance Sheet", icon: Landmark },      // NEW
  { id: "cash-flow", label: "Cash Flow", icon: ArrowLeftRight },        // NEW
  { id: "ai-brief", label: "AI Brief", icon: FileText },
] as const;
```

**Tab ordering rationale:** The three financial statement tabs are grouped together after the computed-metric tabs (Valuation, Sentiment) and before the AI Brief. This creates a logical flow: computed analysis first, then raw supporting data, then the AI synthesis. The AI Brief remains last because it is the "conclusion" of the due diligence workflow. The financial statements serve as the "appendix" that supports everything above.

### 3E. Page Layout Changes

**File:** `frontend/app/analyze/[ticker]/page.tsx` (MODIFY)

1. Update the `TabId` type to include the three new tab IDs:

```typescript
type TabId = "macro" | "fundamentals" | "forensic" | "valuation" | "sentiment"
  | "income-stmt" | "balance-sheet" | "cash-flow" | "ai-brief";
```

2. Import the new panel components:

```typescript
import IncomeStatementPanel from "@/components/IncomeStatementPanel";
import BalanceSheetPanel from "@/components/BalanceSheetPanel";
import CashFlowPanel from "@/components/CashFlowPanel";
```

3. Add cases to `renderActivePanel()`:

```typescript
case "income-stmt":
  return (
    <IncomeStatementPanel
      statement={data.financial_statements?.income_statement ?? { periods: [], line_items: [] }}
    />
  );

case "balance-sheet":
  return (
    <BalanceSheetPanel
      statement={data.financial_statements?.balance_sheet ?? { periods: [], line_items: [] }}
    />
  );

case "cash-flow":
  return (
    <CashFlowPanel
      statement={data.financial_statements?.cash_flow ?? { periods: [], line_items: [] }}
    />
  );
```

Note the null-safe access with fallback. This handles backward compatibility with old cached responses that do not include `financial_statements`.

### 3F. Formatting Utility

**File:** `frontend/lib/utils.ts` (MODIFY)

Add a new formatting function specifically for financial statement table cells:

```typescript
/**
 * Format a raw dollar amount for display in financial statement tables.
 * Divides by 1,000,000 to show values in millions with one decimal place.
 * Negative values are shown in parentheses.
 *
 * Examples:
 *   391035000000  -> "391,035.0"
 *   -5234000000   -> "(5,234.0)"
 *   null          -> "--"
 *   0             -> "0.0"
 */
export function formatStatementValue(value: number | null): string {
  if (value == null) return "--";
  const inMillions = value / 1_000_000;
  const abs = Math.abs(inMillions);
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(abs);
  if (inMillions < 0) return `(${formatted})`;
  return formatted;
}

/**
 * Format a fiscal period date string (YYYY-MM-DD) into a display header.
 * Returns "FY 'YY" format, e.g. "2024-09-28" -> "FY '24"
 */
export function formatFiscalPeriod(dateStr: string): string {
  if (!dateStr || dateStr.length < 4) return dateStr;
  const year = dateStr.substring(2, 4);
  return `FY '${year}`;
}
```

---

## 4. Complete File Change List

### Files to Create (4 new files)

| File | Purpose |
|------|---------|
| `frontend/components/FinancialStatementTable.tsx` | Reusable Bloomberg-style table for rendering a FinancialStatement |
| `frontend/components/IncomeStatementPanel.tsx` | Income Statement tab panel (thin wrapper) |
| `frontend/components/BalanceSheetPanel.tsx` | Balance Sheet tab panel (thin wrapper) |
| `frontend/components/CashFlowPanel.tsx` | Cash Flow tab panel (thin wrapper) |

### Files to Modify (6 existing files)

| File | Changes |
|------|---------|
| `backend/app/schemas/analysis.py` | Add `FinancialStatementLineItem`, `FinancialStatement`, `FinancialStatements` models; add `financial_statements` field to `AnalysisResponse` |
| `backend/app/services/yfinance_service.py` | Add `transform_statement()` function |
| `backend/app/routers/analyze.py` | Call `transform_statement()` in `_build_response()`, pass `financial_statements` to response |
| `frontend/types/analysis.ts` | Add `FinancialStatementLineItem`, `FinancialStatement`, `FinancialStatements` interfaces; update `AnalysisResponse` |
| `frontend/components/AnalysisTabs.tsx` | Add 3 new tab entries with icons |
| `frontend/app/analyze/[ticker]/page.tsx` | Update `TabId` type, import 3 new panels, add 3 cases to `renderActivePanel()` |
| `frontend/lib/utils.ts` | Add `formatStatementValue()` and `formatFiscalPeriod()` helpers |

### Files NOT Changed

| File | Reason |
|------|--------|
| `backend/app/services/yfinance_service.py` fetch logic | Already fetches all needed data |
| `backend/app/models/analysis_reports.py` | No new DB columns needed |
| `backend/app/services/forensic_engine.py` | No new calculations |
| `backend/app/services/claude_service.py` | No new AI prompts |
| `frontend/lib/api.ts` | Response shape is additive (new optional field), no changes needed |
| All existing panel components | Untouched |

---

## 5. Risk Assessment

### Risk: yfinance line item labels are inconsistent across companies or over time

- **Impact:** Medium. If yfinance renames a line item (e.g., "Total Revenue" vs "Revenue" vs "Total Revenue And Other Operating Revenue"), the table will show whatever label yfinance provides. Some labels may be verbose or inconsistent.
- **Mitigation:** Accept the raw labels for v1. Do not attempt to normalize or map them. The feature goal is to show what yfinance provides. If label normalization becomes necessary, add a `LABEL_MAP` dictionary as a future enhancement, but do not block the initial implementation on it.

### Risk: Some companies have fewer than 4 annual periods

- **Impact:** Low. Newer public companies or companies with fiscal year changes may have fewer periods.
- **Mitigation:** Already handled. The `transform_statement()` function works with any number of periods. The table renders however many columns exist. Empty state handles zero periods.

### Risk: Large balance sheets with 80+ line items make the table long

- **Impact:** Low (cosmetic). yfinance balance sheets for large companies can have 60-80 line items.
- **Mitigation:** Natural page scroll handles this. Consider adding a "collapse minor items" toggle as a future enhancement. For v1, show all items -- this is a professional tool for analysts who want to see everything.

### Risk: Payload size increase

- **Impact:** Low. As calculated above, roughly 9KB additional per response. The Claude report alone is 20-40KB of markdown.
- **Mitigation:** None needed. If payload size becomes a concern in the future, the financial statements could be moved to a separate lazy-loaded endpoint. But this is premature optimization for a 9KB delta.

### Risk: NaN / Infinity values in yfinance data

- **Impact:** Medium. Some line items may contain NaN or Infinity values that break JSON serialization.
- **Mitigation:** The `transform_statement()` function explicitly checks for NaN (`float_val != float_val`) and converts to `null`. The existing `_df_to_json()` in yfinance_service already handles this at the DataFrame serialization level via pandas' built-in JSON serializer. Belt and suspenders.

---

## 6. Implementation Order

This feature is self-contained and can be implemented in a single wave:

1. **Backend schema + transform function** (30 min)
   - Add Pydantic models to `analysis.py`
   - Add `transform_statement()` to `yfinance_service.py`
   - Wire up in `analyze.py` router

2. **Frontend types + utilities** (15 min)
   - Add TypeScript interfaces to `analysis.ts`
   - Add formatting functions to `utils.ts`

3. **FinancialStatementTable component** (45 min)
   - This is the bulk of the work: the table layout, sticky columns, number formatting, alternating rows, hover states, negative value styling

4. **Panel components + tab integration** (20 min)
   - Create 3 thin panel wrappers
   - Add tabs to `AnalysisTabs.tsx`
   - Add cases to `page.tsx`

5. **Testing** (30 min)
   - Backend: unit test for `transform_statement()` with edge cases (empty dict, missing periods, NaN values)
   - Frontend: render test for `FinancialStatementTable` with mock data
   - E2E: verify tabs render for a real ticker (e.g., AAPL)

**Total estimated effort:** ~2.5 hours

---

**Created:** 2026-01-31
**Owner:** @Chief_Architect
