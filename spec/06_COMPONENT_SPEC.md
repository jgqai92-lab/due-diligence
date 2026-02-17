# Component Specification

## Component Library

All components follow the Warm Analytical SaaS design system (see 05_DESIGN_SYSTEM.md). Every component must meet commercial-grade quality standards: polished interactions, precise alignment, professional typography, smooth animations, and complete state coverage (loading, empty, error, data).

---

## Table of Contents

### Existing Components (Forensic / Core)
1. [TickerSearchInput](#tickersearchinput)
2. [ForensicScoreCard](#forensicscorecard)
3. [BeneishMScorePanel](#beneishmscorePanel)
4. [AltmanZScorePanel](#altmanzscorePanel)
5. [SaaSMetricsPanel](#saasmetricspanel)
6. [CitationTooltip](#citationtooltip)
7. [ForensicReport](#forensicreport)
8. [PortfolioTable](#portfoliotable)
9. [AlertBanner](#alertbanner)
10. [DashboardLayout](#dashboardlayout)
11. [RedFlagBadge](#redflagbadge)
12. [DataFreshnessIndicator](#datafreshnessindicator)
13. [SkeletonLoader](#skeletonloader)
14. [MetricGrid](#metricgrid)
15. [AnalysisTabs](#analysistabs)
16. [AnalysisSummaryCards](#analysissummarycards)

### New Components: Workflow Engine
17. [WorkflowProgressTracker](#workflowprogresstracker)
18. [WorkflowCard](#workflowcard)

### New Components: IST Content (Phase 1-2)
19. [ContentInput](#contentinput)
20. [ClaimsTable](#claimstable)
21. [ScreeningBriefEditor](#screeningbriefeditor)
22. [BottleneckMap](#bottleneckmap)
23. [DemandModelPanel](#demandmodelpanel)
24. [ValidationStatus](#validationstatus)
25. [QualityGate](#qualitygate)

### New Components: IST Analysis (Phase 3-4)
26. [EquityCandidatesTable](#equitycandidatestable)
27. [ScarcityRadar](#scarcityradar)
28. [TierClassification](#tierclassification)
29. [EffectsMap](#effectsmap)
30. [InvariantChecklist](#invariantchecklist)
31. [DialecticView](#dialecticview)
32. [SynthesisReport](#synthesisreport)

### New Components: IST Output (Phase 5)
33. [MasterScreenTable](#masterscreentable)
34. [RotationStrategy](#rotationstrategy)
35. [CatalystCalendar](#catalystcalendar)
36. [StressTestResults](#stresstestresults)
37. [InvestmentThesisReport](#investmentthesisreport)
38. [ScreenCertification](#screencertification)

### New Components: Frameworks
39. [FrameworkPanel](#frameworkpanel)
40. [FrameworkRenderer](#frameworkrenderer)

---

## Existing Components (Forensic / Core)

### TickerSearchInput
**File:** `frontend/components/TickerSearchInput.tsx`
**Purpose:** Primary entry point for forensic analysis. Autocomplete search with keyboard support.

**Props:**
```typescript
interface TickerSearchInputProps {
  onSelect: (ticker: string, name: string) => void;
  placeholder?: string; // default: "Search ticker... (Ctrl+K)"
  autoFocus?: boolean;
}
```

**Behavior:**
- Global keyboard shortcut: `Ctrl+K` or `/` focuses the input
- Debounced search (300ms) calls `/api/search?q={query}`
- Dropdown shows: `TICKER -- Company Name (Sector)`
- Keyboard: Arrow keys navigate, Enter selects, Escape closes
- Recent searches stored in localStorage, shown when input focused with empty query
- Loading spinner in dropdown while fetching

**Styling:**
- Full-width input with monospace ticker display
- Dropdown: `bg-surface border border-border rounded-xl shadow-lg`
- Active item: `bg-primary-muted border-l-2 border-l-primary`

**Accessibility:**
- Role: `combobox` with `aria-expanded`, `aria-activedescendant`
- Results: `role="listbox"` with `role="option"` items
- Screen reader announces result count

---

### ForensicScoreCard
**File:** `frontend/components/ForensicScoreCard.tsx`
**Purpose:** Displays a single forensic metric with zone indicator and expandable component detail.

**Props:**
```typescript
interface ForensicScoreCardProps {
  title: string;           // e.g., "BENEISH M-SCORE"
  score: number | null;
  zone: ZoneType;          // "safe" | "warning" | "danger" | null
  interpretation: string;  // e.g., "UNLIKELY MANIPULATOR"
  components?: { name: string; value: number | null; citation: Citation }[];
}
```

**Styling:**
- Card: `bg-surface rounded-xl shadow-card border-l-[3px] hover:shadow-card-hover transition-shadow duration-200`
- Left border colored by zone via `getZoneBorder(zone)`
- Score: `text-3xl font-mono font-bold` with zone color via `getZoneColor(zone)`
- Label: `text-xs font-medium tracking-wide text-text-secondary`
- Components grid: `grid-cols-2 gap-3` in expandable section with `animate-fade-in`

**States:**
- Data: Full score display with expandable components
- Null score: Shows "N/A" in `text-text-tertiary`
- No components: Expand button hidden

**Accessibility:**
- Score announced with interpretation text
- Zone communicated via text label, not just color
- Expand/collapse button has `aria-label`

---

### BeneishMScorePanel
**File:** `frontend/components/BeneishMScorePanel.tsx`
**Purpose:** Full M-Score display with all 8 components, using ForensicScoreCard.

**Props:**
```typescript
interface BeneishMScorePanelProps {
  data: BeneishMScoreData; // composite + components + citations
}
```

**Sections:**
1. Composite score card (ForensicScoreCard)
2. 8-component grid (4x2), each with value + citation tooltip

---

### AltmanZScorePanel
**File:** `frontend/components/AltmanZScorePanel.tsx`
**Purpose:** Z-Score display with zone bar visualization.

**Props:**
```typescript
interface AltmanZScorePanelProps {
  data: AltmanZScoreData; // standard + SaaS-modified + components + citations
}
```

**Layout:** Dual scores (standard + SaaS-modified), horizontal zone bar with marker, expandable components.

---

### SaaSMetricsPanel
**File:** `frontend/components/SaaSMetricsPanel.tsx`
**Purpose:** Rule of 40 and Magic Number side-by-side.

**Props:**
```typescript
interface SaaSMetricsPanelProps {
  ruleOf40: RuleOf40Data;
  magicNumber: MagicNumberData;
}
```

---

### CitationTooltip
**File:** `frontend/components/CitationTooltip.tsx`
**Purpose:** Hover/focus tooltip showing data source for any financial figure.

**Props:**
```typescript
interface CitationTooltipProps {
  citation: Citation; // { source, formula, description, period, line_item, raw_value }
  children: React.ReactNode;
}
```

**Behavior:**
- Shows on hover and keyboard focus via state toggle
- Renders no tooltip wrapper if citation has no meaningful data (source, formula, description all empty)
- Sections: Formula (monospace, bg-background), Description, Data Source grid

**Styling:**
- Container: `relative inline-flex items-center gap-1 cursor-help`
- Indicator: `text-info text-[10px] opacity-60 hover:opacity-100` (small "i")
- Tooltip: `bg-surface border border-border rounded-xl shadow-lg p-4 text-xs animate-fade-in w-80 z-50`
- Labels: `text-[10px] font-semibold text-text-tertiary uppercase tracking-wider`

**Accessibility:**
- `aria-describedby` linking to tooltip content
- Tooltip reachable via tab focus (`tabIndex={0}`)

---

### ForensicReport
**File:** `frontend/components/ForensicReport.tsx`
**Purpose:** Full-page markdown report renderer with bear case highlighting.

**Props:**
```typescript
interface ForensicReportProps {
  markdown: string;
  bearCase: string;
  redFlags: { description: string; severity: string }[];
  generatedAt: string;
  onRegenerate: () => void;
  onExport: () => void;
}
```

**Styling:**
- Report body: `body-lg font, text-text-primary, max-w-3xl`
- Bear case: `border-l-[3px] border-l-bear bg-bear/5 p-4 rounded-r-lg`

---

### PortfolioTable
**File:** `frontend/components/PortfolioTable.tsx`
**Purpose:** Sortable data table with inline forensic status badges.

**Props:**
```typescript
interface PortfolioTableProps {
  holdings: Holding[];
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
  onAnalyze: (ticker: string) => void;
}
```

**Styling:**
- Dense rows with monospace number cells
- P&L colored green/red based on sign
- Status badges use zone badge pattern

---

### AlertBanner
**File:** `frontend/components/AlertBanner.tsx`
**Purpose:** Alert notification for forensic deterioration.

**Props:**
```typescript
interface AlertBannerProps {
  alert: { ticker: string; alertType: string; severity: "info" | "warning" | "critical"; message: string };
  onDismiss: () => void;
  onViewTicker: (ticker: string) => void;
}
```

**Styling:**
- Info: `border-l-[3px] border-l-info bg-info/5`
- Warning: `border-l-[3px] border-l-warning bg-warning/5`
- Critical: `border-l-[3px] border-l-bear bg-bear/5`

---

### DashboardLayout
**File:** `frontend/components/DashboardLayout.tsx`
**Purpose:** Application shell with icon-only gradient sidebar and main content area.

**Props:**
```typescript
interface DashboardLayoutProps {
  children: React.ReactNode;
}
```

**Structure:**
- Sidebar: `w-16 sidebar-gradient flex-shrink-0 hidden lg:flex flex-col items-center py-6 gap-6 rounded-r-2xl shadow-lg`
- Nav items: `w-10 h-10 rounded-xl flex items-center justify-center`, active = `bg-white/30 shadow-sm`, inactive = `hover:bg-white/20`
- Icons: white, 20px
- Main: `flex-1 overflow-y-auto` with `max-w-6xl mx-auto p-6 lg:p-8`
- Will be extended with "Screens" (IST) and "Research" (HFRT) nav items in Wave C2

---

### RedFlagBadge
**File:** `frontend/components/RedFlagBadge.tsx`
**Purpose:** Compact inline badge for flagged items.

**Props:**
```typescript
interface RedFlagBadgeProps {
  flag: string;
  severity: "low" | "medium" | "high" | "critical";
}
```

**Styling:**
- Low: `bg-info/10 text-info border border-info/20 rounded-sm text-[11px] font-medium px-2 py-0.5`
- Medium: `bg-warning/10 text-warning border border-warning/20`
- High: `bg-bear/10 text-bear border border-bear/20`
- Critical: `bg-bear text-white border border-bear font-bold`

---

### DataFreshnessIndicator
**File:** `frontend/components/DataFreshnessIndicator.tsx`
**Purpose:** Shows when data was last fetched with color-coded freshness dot.

**Props:**
```typescript
interface DataFreshnessIndicatorProps {
  fetchedAt: string; // ISO timestamp
}
```

**Display:**
- Fresh (< 1 hour): green dot + "Just updated"
- Recent (1-24 hours): amber dot + "Updated Xh ago"
- Stale (> 24 hours): red dot + "Stale -- X days ago"

---

### SkeletonLoader
**File:** `frontend/components/SkeletonLoader.tsx`
**Purpose:** Loading placeholder matching component shapes.

**Props:**
```typescript
interface SkeletonLoaderProps {
  variant?: "card" | "table-row" | "score" | "report" | "text";
  count?: number;
}
```

**Styling:** `animate-pulse bg-border/50 rounded-lg` blocks within `bg-surface rounded-xl shadow-card` containers.

---

### MetricGrid
**File:** `frontend/components/MetricGrid.tsx`
**Purpose:** Responsive grid of metric cards with zone-colored left borders and citation tooltips.

**Props:**
```typescript
interface MetricGridItem {
  label: string;
  value: number | null;
  format: "percent" | "ratio" | "currency" | "number" | "multiple";
  citation?: Citation;
  zone?: string;
  interpretation?: string;
}

interface MetricGridProps {
  metrics: MetricGridItem[];
  columns?: 2 | 3 | 4;
}
```

**Styling:**
- Grid: `grid gap-3` with responsive column classes
- Each cell: `bg-surface rounded-xl border-l-[3px] p-4 shadow-card hover:shadow-card-hover transition-shadow duration-200`
- Label: `text-[11px] font-medium tracking-wide text-text-secondary`
- Value: `font-mono text-lg font-bold tabular-nums` with zone color

---

### AnalysisTabs
**File:** `frontend/components/AnalysisTabs.tsx`
**Purpose:** Primary tab navigation for the analysis page.

**Props:**
```typescript
interface AnalysisTabsProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}
```

**Styling:**
- Container: `flex overflow-x-auto bg-surface rounded-xl shadow-card p-1.5 gap-1`
- Active: `bg-primary text-white shadow-sm rounded-lg px-4 py-2.5 text-xs font-medium`
- Inactive: `text-text-secondary hover:text-text-primary hover:bg-background rounded-lg`
- Icons: `size={14}`, `strokeWidth` varies by active state

**Accessibility:**
- Container: `role="tablist" aria-label="Analysis sections"`
- Each tab: `role="tab" aria-selected aria-controls id`
- Focus: `focus-visible:ring-2 focus-visible:ring-primary/50`

---

### AnalysisSummaryCards
**File:** `frontend/components/AnalysisSummaryCards.tsx`
**Purpose:** Hero summary cards with gradient backgrounds at the top of the analysis page.

---

## New Components: Workflow Engine

### WorkflowProgressTracker
**File:** `frontend/components/workflow/WorkflowProgressTracker.tsx`
**Purpose:** Persistent phase/step progress display with live SSE updates and checkpoint approval controls. This is the primary real-time feedback mechanism for long-running IST/HFRT workflows.

**Props:**
```typescript
interface WorkflowProgressTrackerProps {
  workflowId: number;
  workflowType: "IST" | "HFRT";
  phases: PhaseDefinition[];        // Static phase/step definitions
  currentPhase: number;             // 1-indexed current phase
  currentStep: string;              // Current step identifier
  status: WorkflowStatus;           // PENDING | RUNNING | PAUSED | COMPLETED | FAILED
  steps: WorkflowStepState[];       // Live step states from SSE
  checkpoint?: CheckpointInfo;      // Present when workflow is paused at checkpoint
  onApprove: () => void;            // Approve checkpoint and advance
  onPause: () => void;              // Pause workflow
  onCancel: () => void;             // Cancel workflow
  connectionStatus: "connected" | "reconnecting" | "disconnected";
}

interface PhaseDefinition {
  phase: number;
  label: string;                    // e.g., "Content Extraction"
  color: string;                    // Phase color token
  steps: string[];                  // Step identifiers in order
}

interface WorkflowStepState {
  stepName: string;
  phase: number;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  startedAt?: string;
  completedAt?: string;
  errorMessage?: string;
}

interface CheckpointInfo {
  phaseName: string;
  description: string;              // What happens when user approves
  requiresApproval: boolean;
}
```

**Layout:**
```
+-------------------------------------------------------------------+
| [=====Phase 1=====][====Phase 2====][==Phase 3 (active)==][4 ][5 ]|
| Phase 3: Equity Identification                     [*] Connected  |
+-------------------------------------------------------------------+
| Step 3.1: Equity Scanning .............. [checkmark] 2m 14s       |
| Step 3.2: Tier Classification .......... [spinner] Running...     |
| Step 3.3: Effects Mapping .............. [circle] Pending         |
| Step 3.4: Invariant Check .............. [circle] Pending         |
+-------------------------------------------------------------------+
| (if checkpoint paused:)                                           |
| +---------------------------------------------------------------+|
| | CHECKPOINT: Phase 3 complete. Review candidates before        ||
| | proceeding to Dialectic Scrutiny.                             ||
| | [Approve & Continue]  [Stay Paused]                           ||
| +---------------------------------------------------------------+|
+-------------------------------------------------------------------+
```

**Visual Description:**
1. **Phase progress bar:** A horizontal segmented bar spanning the full width. Each of the 5 phases gets a proportional segment. Completed phases are filled with their phase color. The active phase segment has a subtle pulse animation. Future phases are `bg-background` with `border border-border`. Phase labels appear inside or below segments depending on width.
2. **Current phase header:** Below the bar, the current phase name and step displayed as `text-sm font-medium text-text-primary`.
3. **Connection indicator:** Top-right corner, small dot: green (`bg-bull`) = connected, amber (`bg-warning`) + pulse = reconnecting, red (`bg-bear`) = disconnected. Include `aria-live="polite"` region.
4. **Step list:** Vertical list of steps within the active phase. Each step shows: status icon (from icon mapping), step name, and elapsed time or "Pending". Running step has `Loader2` icon with `animate-spin`.
5. **Checkpoint card:** When `checkpoint` prop is present: `bg-warning/5 border border-warning/20 rounded-xl p-4` card with description text and two buttons. "Approve & Continue" is primary style. "Stay Paused" is secondary style.

**States:**
- **Loading:** SkeletonLoader variant="card" count=1
- **Running:** Progress bar fills, step list updates in real-time via SSE
- **Paused (checkpoint):** Checkpoint card visible, progress bar paused
- **Completed:** All phases filled green, completion summary shown
- **Failed:** Failed step highlighted in red, error message shown, remaining steps greyed out
- **Disconnected:** Amber connection dot, banner below steps: "Connection lost. Reconnecting..."

**Styling:**
- Container: `bg-surface rounded-xl shadow-card p-4`
- Phase bar segments: `h-2 rounded-full` within `flex gap-1`
- Active segment: phase color with `animate-pulse` (subtle)
- Step row: `flex items-center gap-3 py-2 border-b border-border last:border-b-0`
- Step icon: 16px Lucide icon
- Step name: `text-sm text-text-primary`
- Step time: `text-xs text-text-tertiary font-mono`

**Accessibility:**
- Phase bar: `role="progressbar" aria-valuenow aria-valuemin aria-valuemax aria-label`
- Step list: `role="list"` with `role="listitem"` items
- Status icons paired with `aria-label` text (not just visual)
- Connection status: `aria-live="polite"` region
- Checkpoint: autofocus on "Approve & Continue" button when it appears

---

### WorkflowCard
**File:** `frontend/components/workflow/WorkflowCard.tsx`
**Purpose:** Summary card for a workflow run, displayed in the screens/research list pages. Shows workflow name, type, status, progress percentage, and last update time.

**Props:**
```typescript
interface WorkflowCardProps {
  id: number;
  name: string;
  workflowType: "IST" | "HFRT";
  status: WorkflowStatus;
  currentPhase: number;
  totalPhases: number;
  completedSteps: number;
  totalSteps: number;
  createdAt: string;
  updatedAt: string;
  onClick: (id: number) => void;
}
```

**Layout:**
```
+-----------------------------------------------------------+
| [Scan icon]  Energy Scarcity Screen        [RUNNING badge] |
| IST Screen   Phase 3 of 5                                 |
| [============60%===========............]                   |
| Created 2h ago   Last update: 3m ago                      |
+-----------------------------------------------------------+
```

**Visual Description:**
- Standard card: `bg-surface rounded-xl shadow-card hover:shadow-card-hover transition-shadow duration-200 p-5 cursor-pointer`
- Top row: Icon (type-specific) + name (h4 weight) + status badge (right-aligned)
- Middle row: Workflow type label + "Phase X of Y"
- Progress bar: `bg-background rounded-full h-1.5` track, `bg-primary rounded-full h-1.5` fill
- Bottom row: `text-xs text-text-tertiary` timestamps

**States:**
- **PENDING:** Gray badge, empty progress bar
- **RUNNING:** Blue badge, progress bar filling, pulse on active segment
- **PAUSED:** Amber badge, "Checkpoint awaiting approval" text
- **COMPLETED:** Green badge, full progress bar
- **FAILED:** Red badge, progress bar stops at failure point

**Accessibility:**
- Entire card is clickable: `role="article"` with click handler
- Status communicated via badge text, not color alone
- Focus: `focus-visible:ring-2 focus-visible:ring-primary/50 rounded-xl`

---

## New Components: IST Content (Phase 1-2)

### ContentInput
**File:** `frontend/components/ist/ContentInput.tsx`
**Purpose:** Rich text input for pasting unstructured content (podcast transcripts, articles, earnings call transcripts) to be processed by the IST content extraction pipeline.

**Props:**
```typescript
interface ContentInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isProcessing: boolean;
  maxLength?: number;            // default: 50000
  placeholder?: string;
  sources?: ContentSource[];     // Already submitted sources
  onRemoveSource?: (index: number) => void;
}

interface ContentSource {
  id: number;
  title: string;
  type: "transcript" | "article" | "report" | "other";
  wordCount: number;
  addedAt: string;
}
```

**Layout:**
```
+-----------------------------------------------------------+
| CONTENT SOURCES                                           |
| +-----------------------------------------------------+ |
| | [Doc] "BG2Pod Episode 42"  (transcript, 8,240 words)|x||
| | [Doc] "WSJ Article on..."  (article, 2,100 words)   |x||
| +-----------------------------------------------------+ |
|                                                           |
| Add Content                                               |
| +-----------------------------------------------------+ |
| | Paste transcript, article, or other content here... | |
| |                                                     | |
| |                                                     | |
| | (min-h 200px textarea)                              | |
| +-----------------------------------------------------+ |
| 0 / 50,000 characters                                    |
|                                                           |
| Content Type: [transcript v]  Title: [________________]   |
|                                                           |
| [Add Source]  (secondary)    [Extract Claims] (primary)   |
+-----------------------------------------------------------+
```

**Visual Description:**
- Existing sources list: Each source is a row with icon, title, type badge, word count, and remove button
- Textarea: Standard input styling, `min-h-[200px] resize-y font-mono text-sm` for pasted content
- Character counter: `text-xs text-text-tertiary` below textarea, turns `text-bear` at 90% capacity
- Content type selector: Small dropdown (transcript/article/report/other)
- Title input: Standard text input for naming the source
- Action buttons: "Add Source" (secondary, adds to list without extracting) and "Extract Claims" (primary, submits all sources for extraction)

**States:**
- **Empty:** Placeholder text visible, "Extract Claims" button disabled
- **Has content:** Character counter active, buttons enabled
- **Processing:** Textarea disabled, "Extract Claims" shows spinner, overlay with progress text
- **Sources added:** Source list visible above textarea
- **Error:** Error banner above textarea with retry button

**Accessibility:**
- Textarea: `aria-label="Content input for IST extraction"` with `aria-describedby` pointing to character counter
- Source list: `role="list"` with remove buttons having `aria-label="Remove source: {title}"`
- Processing state: `aria-busy="true"` on the form container

---

### ClaimsTable
**File:** `frontend/components/ist/ClaimsTable.tsx`
**Purpose:** Displays extracted claims from content sources with source attribution tags, quantitative anchors, temporal markers, and confidence badges.

**Props:**
```typescript
interface ClaimsTableProps {
  claims: ISTClaim[];
  isLoading: boolean;
  onClaimSelect?: (claim: ISTClaim) => void;
  selectedClaimId?: number;
  showValidation?: boolean;       // Show validation status column (after Phase 2)
}

interface ISTClaim {
  id: number;
  claimText: string;
  sourceCitation: string;         // Which content source
  quantitativeAnchor?: string;    // e.g., "$50B TAM by 2028"
  temporalMarker?: string;        // e.g., "by 2027", "next 18 months"
  bottleneckName?: string;        // Assigned after bottleneck mapping
  confidence: number;             // 0-1 extraction confidence
  isValidated: boolean;
  validationVerdict?: "confirmed" | "partially_confirmed" | "contradicted" | "unvalidatable";
}
```

**Layout:**
```
+--------+------------------+----------+----------+--------+-----------+
| #      | Claim            | Source   | Quant    | Time   | Conf.     |
+--------+------------------+----------+----------+--------+-----------+
| 1      | "Global data     | BG2Pod   | $50B TAM | 2028   | [===] 92% |
|        |  center power    | Ep. 42   |          |        |           |
|        |  demand will..." |          |          |        |           |
+--------+------------------+----------+----------+--------+-----------+
| 2      | ...              | ...      | ...      | ...    | ...       |
+--------+------------------+----------+----------+--------+-----------+
```

**Visual Description:**
- Data table pattern: `bg-surface rounded-xl shadow-card overflow-hidden`
- Claim text column: Widest column, truncated with ellipsis at 2 lines, full text on row click/expand
- Source column: Badge style with source icon
- Quantitative anchor: `font-mono text-sm` with info-blue background tint
- Temporal marker: `text-xs text-text-secondary` with calendar icon
- Confidence: Mini progress bar (`h-1.5 rounded-full bg-background` track, fill color by confidence: >0.8 bull, 0.5-0.8 warning, <0.5 bear) plus percentage in mono
- Validation column (when `showValidation=true`): Verdict badge using validation verdict colors

**States:**
- **Loading:** SkeletonLoader variant="table-row" count=5
- **Empty:** "No claims extracted yet. Submit content to begin." centered message with illustration
- **Data:** Full table with row selection highlight (`bg-primary-muted`)
- **Error:** Error banner above table

**Accessibility:**
- Table: `role="table"` with proper `th` scope attributes
- Sortable headers: `aria-sort` attribute
- Row selection: `aria-selected` on selected row
- Confidence: `aria-label="Confidence: 92 percent"` on the visual bar

---

### ScreeningBriefEditor
**File:** `frontend/components/ist/ScreeningBriefEditor.tsx`
**Purpose:** Editable form for the IST screening brief -- the document that frames the investment thesis, constraints, and hypothesis before screening begins.

**Props:**
```typescript
interface ScreeningBriefEditorProps {
  brief: ScreeningBrief;
  onChange: (brief: ScreeningBrief) => void;
  onSave: () => void;
  isSaving: boolean;
  isReadOnly?: boolean;           // After extraction, brief becomes read-only summary
}

interface ScreeningBrief {
  hypothesis: string;             // Primary investment hypothesis
  constraints: string[];          // Investment constraints (market cap, geography, etc.)
  frameworks: string[];           // Selected IST frameworks to apply
  timeHorizon: string;            // e.g., "12-18 months"
  riskTolerance: "conservative" | "moderate" | "aggressive";
  notes: string;                  // Free-form analyst notes
}
```

**Layout:**
```
+-----------------------------------------------------------+
| SCREENING BRIEF                                           |
|                                                           |
| Hypothesis                                                |
| +-----------------------------------------------------+ |
| | AI infrastructure buildout will create sustained     | |
| | demand for power, cooling, and networking...         | |
| +-----------------------------------------------------+ |
|                                                           |
| Constraints                                               |
| [+ Add constraint]                                        |
| * Market cap > $1B                                [x]    |
| * US-listed equities only                         [x]    |
|                                                           |
| Frameworks       [Scarcity Scoring v] [Add]               |
| [Temporal Phase Mapping] [Scarcity Scoring]               |
|                                                           |
| Time Horizon     [12-18 months_____]                      |
| Risk Tolerance   (o) Conservative  (*) Moderate  ( ) Aggressive |
|                                                           |
| Notes                                                     |
| +-----------------------------------------------------+ |
| |                                                     | |
| +-----------------------------------------------------+ |
|                                                           |
| [Save Brief]                                              |
+-----------------------------------------------------------+
```

**Visual Description:**
- Card container: `bg-surface rounded-xl shadow-card p-6`
- Section labels: `text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mb-2`
- Hypothesis textarea: Standard textarea, `min-h-[80px]`
- Constraints: Tag list with remove buttons, "Add constraint" text input below
- Frameworks: Dropdown selector + tag display, can add multiple
- Radio group: Standard radio buttons for risk tolerance
- Read-only mode: All inputs replaced with styled text display

**States:**
- **Editing:** All fields editable, Save button active
- **Saving:** Save button shows spinner
- **Read-only:** Clean display with no input styling, "Edit" button to re-enable
- **Validation error:** Red border on invalid fields, error message below

**Accessibility:**
- All inputs have associated `label` elements
- Constraint tags: `role="listitem"` within `role="list"`, remove buttons have `aria-label="Remove constraint: {text}"`
- Radio group: `role="radiogroup"` with `aria-label="Risk tolerance"`

---

### BottleneckMap
**File:** `frontend/components/ist/BottleneckMap.tsx`
**Purpose:** Visual display of the temporal bottleneck cascade showing Phase 1 (near-term), Phase 2 (mid-term), and Phase 3 (structural) bottlenecks with causal connections.

**Props:**
```typescript
interface BottleneckMapProps {
  bottlenecks: ISTBottleneck[];
  isLoading: boolean;
  onBottleneckSelect?: (bottleneck: ISTBottleneck) => void;
  selectedBottleneckId?: number;
}

interface ISTBottleneck {
  id: number;
  name: string;
  phase: 1 | 2 | 3 | "cross-cutting";
  description: string;
  quantitativeEvidence: string;
  temporalMarker: string;
  resolutionTrigger: string;
  claimIds: number[];              // Claims that support this bottleneck
}
```

**Layout:**
```
+-----------------------------------------------------------+
| BOTTLENECK MAP                                            |
|                                                           |
| Phase 1 (Near-Term)    Phase 2 (Mid-Term)   Phase 3      |
| 0-12 months            12-36 months         (Structural) |
|                                                           |
| +-------------+       +-------------+     +-------------+ |
| | GPU Supply  |------>| Power Grid  |---->| Workforce   | |
| | Constraint  |       | Bottleneck  |     | Pipeline    | |
| | 5 claims    |       | 3 claims    |     | 2 claims    | |
| +-------------+       +-------------+     +-------------+ |
|                              |                             |
| +-------------+       +-----v-------+                     |
| | Cooling     |------>| Data Center |                     |
| | Technology  |       | Land/Permits|                     |
| | 4 claims    |       | 2 claims    |                     |
| +-------------+       +-------------+                     |
|                                                           |
| Cross-cutting                                             |
| +-----------------------------------------------------+ |
| | Regulatory Environment (4 claims)                    | |
| +-----------------------------------------------------+ |
+-----------------------------------------------------------+
```

**Visual Description:**
- Three-column layout for Phase 1/2/3, with "Cross-cutting" section below spanning full width
- Each bottleneck is a card: `bg-surface border border-border rounded-xl p-4 cursor-pointer hover:shadow-card-hover transition-shadow duration-200`
- Phase column headers: `text-xs font-semibold uppercase tracking-wider` with phase color dot
- Bottleneck card: Name (bold), claim count badge, temporal marker subtitle
- Connections: CSS borders or SVG lines connecting related bottlenecks across phases (simple left-to-right arrows)
- Selected bottleneck: `border-primary shadow-md` with expanded detail panel below the map showing full description, evidence, and resolution trigger
- Phase column background: Very subtle phase color tint (`bg-{phase-color}/5`)

**States:**
- **Loading:** Three skeleton card columns
- **Empty:** "No bottlenecks mapped yet. Run thematic analysis to begin." centered
- **Data:** Full map with clickable cards
- **Selected:** Selected card highlighted, detail panel expands below

**Accessibility:**
- Bottleneck cards: `role="button"` with `aria-pressed` for selection
- Phase groups: `role="group" aria-label="Phase 1 bottlenecks - Near-term"`
- Connections: `aria-hidden="true"` (decorative, relationship described in text)

---

### DemandModelPanel
**File:** `frontend/components/ist/DemandModelPanel.tsx`
**Purpose:** Displays quantitative demand models for each bottleneck, including the 1 GW Cluster Formula pattern, multiplier calculations, and sensitivity analysis tables.

**Props:**
```typescript
interface DemandModelPanelProps {
  models: ISTDemandModel[];
  isLoading: boolean;
}

interface ISTDemandModel {
  id: number;
  bottleneckName: string;
  baseFormula: string;             // e.g., "1 GW = 330K GB300s x 1.4 cooling x 1.25 maintenance"
  multipliers: { name: string; value: number; unit: string }[];
  sensitivityTable: SensitivityRow[];
  tamEstimate: string;             // e.g., "$120B by 2027"
  assumptions: string[];
  confidence: number;
}

interface SensitivityRow {
  variable: string;
  lowCase: number;
  baseCase: number;
  highCase: number;
  unit: string;
}
```

**Layout:**
```
+-----------------------------------------------------------+
| DEMAND MODELS                                             |
|                                                           |
| GPU Supply Constraint                                     |
| +-----------------------------------------------------+ |
| | Formula: 1 GW = 330K GB300s x 1.4 cooling x 1.25   | |
| |                                                     | |
| | Multipliers:                                        | |
| | GPU per GW cluster    330,000  units                | |
| | Cooling multiplier    1.4x                          | |
| | Maintenance overhead  1.25x                         | |
| |                                                     | |
| | TAM: $120B by 2027                                  | |
| |                                                     | |
| | Sensitivity Analysis                                | |
| | Variable          Low    Base   High                | |
| | GPU price/unit    $25K   $30K   $40K                | |
| | Clusters 2027     80     120    200                  | |
| | Cooling cost/GW   $50M   $70M   $100M               | |
| +-----------------------------------------------------+ |
+-----------------------------------------------------------+
```

**Visual Description:**
- Accordion pattern: One expandable section per demand model (grouped by bottleneck)
- Formula display: `font-mono text-sm bg-background rounded-lg px-3 py-2`
- Multiplier grid: Two-column key-value with monospace values
- TAM: Prominent display in `text-lg font-mono font-bold text-primary`
- Sensitivity table: Standard data table with Low/Base/High columns, monospace numbers, column headers right-aligned

**States:**
- **Loading:** SkeletonLoader variant="card" count=2
- **Empty:** "Demand models will appear after bottleneck mapping." message
- **Data:** Accordion with first model expanded by default

**Accessibility:**
- Accordion: `aria-expanded` on triggers, `aria-controls` to panel, `role="region"` on panels
- Sensitivity table: Standard table ARIA with sortable headers

---

### ValidationStatus
**File:** `frontend/components/ist/ValidationStatus.tsx`
**Purpose:** Displays external validation results for extracted claims, showing which claims were confirmed, partially confirmed, contradicted, or unvalidatable by independent web sources.

**Props:**
```typescript
interface ValidationStatusProps {
  claims: ISTClaim[];             // Claims with validation data populated
  isValidating: boolean;          // Currently running validation
  validationProgress?: number;    // 0-100 if running
  summary?: ValidationSummary;
}

interface ValidationSummary {
  confirmed: number;
  partiallyConfirmed: number;
  contradicted: number;
  unvalidatable: number;
  total: number;
}
```

**Layout:**
```
+-----------------------------------------------------------+
| EXTERNAL VALIDATION                   [Validating... 60%] |
|                                                           |
| Summary: 8 of 12 claims validated                         |
| [===5 confirmed===][==2 partial==][1 contra][4 unval]    |
|                                                           |
| Claim                      Verdict        Source          |
| "GPU demand will reach..." [CONFIRMED]    Bloomberg, NVDA |
|                                            10-K filing    |
| "Cooling costs 40% of..."  [PARTIAL]     Partial: actual |
|                                            range is 30-45%|
| "No alternatives to..."    [CONTRADICTED] AMD MI300X is  |
|                                            competitive    |
+-----------------------------------------------------------+
```

**Visual Description:**
- Summary bar: Horizontal stacked bar showing distribution of verdicts using validation colors
- Validation progress: When running, animated progress bar with "Validating claim X of Y..." text
- Claim rows: Claim text (truncated), verdict badge (colored per validation verdict colors), and source URLs/text
- Contradicted claims: Row has subtle `bg-bear/5` background tint to draw attention
- Confirmed claims: Subtle `bg-bull/5` background

**States:**
- **Loading:** Skeleton loader
- **Validating:** Progress bar + claim-by-claim live update (claims update as each completes via SSE)
- **Complete:** Full summary + claim list
- **Empty:** "Submit content and extract claims before validation." message

**Accessibility:**
- Summary bar: `aria-label="Validation summary: X confirmed, Y partially confirmed..."` with `role="img"`
- Verdict badges: Text label always present (never color-only)

---

### QualityGate
**File:** `frontend/components/ist/QualityGate.tsx`
**Purpose:** Displays quality gate evaluation results showing pass/fail status with specific deficiency list. Used for Content Sufficiency Gate, Research Sufficiency Gate, and Screen Coherence Gate.

**Props:**
```typescript
interface QualityGateProps {
  gateName: string;               // e.g., "Content Sufficiency Gate"
  status: "pass" | "fail" | "pending" | "not_evaluated";
  criteria: GateCriterion[];
  evaluatedAt?: string;
  onEvaluate?: () => void;        // Trigger gate evaluation
  isEvaluating?: boolean;
}

interface GateCriterion {
  name: string;                   // e.g., "3+ claims with quantitative anchors"
  passed: boolean;
  detail?: string;                // Reason for pass/fail
}
```

**Layout:**
```
+-----------------------------------------------------------+
| CONTENT SUFFICIENCY GATE                    [PASS badge]  |
| Evaluated: 2 minutes ago                                  |
|                                                           |
| [checkmark] 3+ claims with quantitative anchors (5 found)|
| [checkmark] 1+ temporal marker present (3 found)         |
| [checkmark] Source bias assessed                          |
| [X mark]    1+ bottleneck identified (0 found)           |
|                                                           |
| (if fail:)                                                |
| Deficiencies must be resolved before proceeding.          |
+-----------------------------------------------------------+
```

**Visual Description:**
- Card with gate name as header and status badge (right-aligned, using gate status colors)
- Criteria list: Vertical list with pass/fail icons
  - Pass: `CheckCircle` icon in `text-bull` + criterion text + detail in `text-text-secondary`
  - Fail: `XCircle` icon in `text-bear` + criterion text in `font-medium` + detail in `text-bear`
- Failed gate: Card has `border-l-[3px] border-l-bear`, deficiency message below criteria list in `text-bear bg-bear/5 rounded-lg p-3`
- Passed gate: Card has `border-l-[3px] border-l-bull`
- Pending/not evaluated: Card has `border-l-[3px] border-l-border-strong`, "Evaluate Gate" button shown

**States:**
- **Not evaluated:** Neutral card with "Evaluate Gate" primary button
- **Evaluating:** Button shows spinner, criteria list skeleton
- **Pass:** Green accent, all criteria checked, gate badge green
- **Fail:** Red accent, failed criteria highlighted, deficiency message
- **Pending:** Gray accent, "Waiting for prerequisite data"

**Accessibility:**
- Gate status: announced as "Content Sufficiency Gate: Passed" or "Failed"
- Criteria: `role="list"` with pass/fail announced per item
- Deficiency message: `role="alert"` when gate fails

---

## New Components: IST Analysis (Phase 3-4)

### EquityCandidatesTable
**File:** `frontend/components/ist/EquityCandidatesTable.tsx`
**Purpose:** Sortable table of equity candidates identified from bottleneck analysis, showing scarcity scores, tier classification, moat type, and catalyst information.

**Props:**
```typescript
interface EquityCandidatesTableProps {
  candidates: ISTEquityCandidate[];
  isLoading: boolean;
  onCandidateSelect?: (candidate: ISTEquityCandidate) => void;
  selectedCandidateId?: number;
  sortField?: string;
  sortDirection?: "asc" | "desc";
  onSort?: (field: string) => void;
}

interface ISTEquityCandidate {
  id: number;
  ticker: string;
  companyName: string;
  bottleneckName: string;
  scarcityScore: ScarcityScore;    // 5 dimensions
  compositeScarcity: number;       // Average of 5 dimensions (1-5 scale)
  moatType: string;                // e.g., "switching costs", "network effects"
  moatEvidence: string;
  catalyst: string;
  tier: 1 | 2 | 3;
  phase: 1 | 2 | 3;
  conviction: number;              // 0-100
}

interface ScarcityScore {
  supplyConstraint: number;        // 1-5
  demandVisibility: number;        // 1-5
  substitutionDifficulty: number;  // 1-5
  pricingPower: number;            // 1-5
  timeToResolve: number;           // 1-5
}
```

**Columns:**
| Column | Font | Sortable | Alignment | Width |
|--------|------|----------|-----------|-------|
| Ticker | mono, bold | Yes | Left | 80px |
| Company | sans | Yes | Left | flex |
| Bottleneck | sans, sm | Yes | Left | 150px |
| Scarcity | mono, bold | Yes | Right | 80px |
| Tier | badge | Yes | Center | 60px |
| Moat | sans, sm | No | Left | 120px |
| Catalyst | sans, sm | No | Left | flex |
| Conviction | mono | Yes | Right | 80px |

**Visual Description:**
- Dense data table: `py-2` cell padding for compact display
- Ticker: `font-mono font-bold text-primary` (clickable)
- Scarcity score: Monospace with color coding (>4.0 bull, 3.0-4.0 warning, <3.0 text-secondary)
- Tier badge: Tier 1/2/3 badge using tier badge styles from design system
- Conviction: Percentage with mini bar
- Row hover: `bg-surface-elevated`
- Selected row: `bg-primary-muted`

**States:**
- **Loading:** SkeletonLoader variant="table-row" count=8
- **Empty:** "No equity candidates identified yet." centered with illustration
- **Data:** Full sortable table
- **Selected:** Expanded detail row below selected candidate showing moat evidence, scarcity radar (inline), and full catalyst text

**Accessibility:**
- Standard table ARIA: `role="table"`, `scope="col"` on headers
- Sort: `aria-sort="ascending"` / `"descending"` on sorted column
- Tier communicated via text ("Tier 1"), not color alone

---

### ScarcityRadar
**File:** `frontend/components/ist/ScarcityRadar.tsx`
**Purpose:** 5-dimension radar/spider chart visualizing the scarcity score for a single equity candidate. Dimensions: Supply Constraint, Demand Visibility, Substitution Difficulty, Pricing Power, Time to Resolve.

**Props:**
```typescript
interface ScarcityRadarProps {
  scores: ScarcityScore;
  candidateName: string;           // Displayed as chart title
  size?: "sm" | "md" | "lg";     // sm=120px, md=200px, lg=280px
  showLabels?: boolean;            // default: true for md/lg, false for sm
  showValues?: boolean;            // Show numeric values at each vertex
  className?: string;
}
```

**Visual Description:**
- SVG-based radar chart with 5 axes radiating from center
- Grid rings at 1, 2, 3, 4, 5 values: `stroke="#eaedf3" stroke-width="1"` (border color)
- Data polygon: `fill="rgba(232,114,74,0.15)" stroke="#e8724a" stroke-width="2"` (primary color)
- Axis labels: Positioned outside the chart at each vertex, `text-[10px] text-text-secondary`
- Value labels (when `showValues`): `font-mono text-[11px] text-text-primary` at data points
- Center point: Small primary-colored dot
- Sizes: sm (inline in table rows), md (detail panels), lg (standalone view)

**States:**
- **Loading:** Circular skeleton pulse
- **Data:** Rendered radar chart
- **All zeros:** Gray polygon, "Insufficient data" label

**Accessibility:**
- `role="img"` with `aria-label="Scarcity radar for {candidateName}: Supply Constraint {X}, Demand Visibility {Y}..."` -- full textual description of all 5 scores
- Provide a screen-reader-only table alternative below the chart

---

### TierClassification
**File:** `frontend/components/ist/TierClassification.tsx`
**Purpose:** Grouped display of equity candidates organized by tier (Tier 1 / Tier 2 / Tier 3) with summary statistics per tier.

**Props:**
```typescript
interface TierClassificationProps {
  candidates: ISTEquityCandidate[];
  isLoading: boolean;
  onCandidateClick?: (candidate: ISTEquityCandidate) => void;
}
```

**Layout:**
```
+-----------------------------------------------------------+
| TIER CLASSIFICATION                                       |
|                                                           |
| Tier 1 -- High Conviction (3 names)                      |
| +------+ +------+ +------+                               |
| | NVDA | | VRTX | | ANET |                               |
| | 4.6  | | 4.2  | | 4.1  |                               |
| | GPU   | | Drug | | Net  |                               |
| +------+ +------+ +------+                               |
|                                                           |
| Tier 2 -- Watchlist (5 names)                             |
| +------+ +------+ +------+ +------+ +------+             |
| | EQIX | | VRT  | | POWL | | AMZN | | MSFT |             |
| | 3.8  | | 3.5  | | 3.4  | | 3.2  | | 3.1  |             |
| +------+ +------+ +------+ +------+ +------+             |
|                                                           |
| Tier 3 -- Speculative (2 names)                           |
| ...                                                       |
+-----------------------------------------------------------+
```

**Visual Description:**
- Three sections, one per tier, stacked vertically
- Tier header: `text-sm font-semibold` with tier badge + count
- Tier 1 section: `border-l-[3px] border-l-bull` left accent
- Tier 2 section: `border-l-[3px] border-l-warning` left accent
- Tier 3 section: `border-l-[3px] border-l-border-strong` left accent
- Candidate cards within each tier: Compact cards in a flex-wrap row
  - Card: `bg-surface border border-border rounded-xl p-3 w-28 text-center cursor-pointer hover:shadow-card-hover`
  - Ticker: `font-mono font-bold text-sm`
  - Scarcity score: `font-mono text-xs` with zone color
  - Bottleneck tag: `text-[10px] text-text-tertiary truncate`

**States:**
- **Loading:** Skeleton cards in three groups
- **Empty:** "No candidates classified yet."
- **Data:** Full tier display
- **Single tier:** If only one tier has candidates, other tier sections show "No names in this tier" in muted text

**Accessibility:**
- Tier sections: `role="group" aria-label="Tier 1 - High Conviction: 3 names"`
- Candidate cards: `role="button"` for clickable cards
- Tier level communicated via text header, not just color

---

### EffectsMap
**File:** `frontend/components/ist/EffectsMap.tsx`
**Purpose:** Visual display of multi-order downstream effects (1st order -> 2nd order -> 3rd order) showing how primary bottleneck effects cascade into secondary and tertiary investment opportunities.

**Props:**
```typescript
interface EffectsMapProps {
  effectsChains: ISTEffectsChain[];
  isLoading: boolean;
  onEffectClick?: (effect: ISTEffectsChain) => void;
}

interface ISTEffectsChain {
  id: number;
  thesis: string;                  // The primary thesis driving effects
  order: 1 | 2 | 3;
  effectDescription: string;
  equityCandidateId?: number;      // Linked candidate if identified
  equityTicker?: string;
}
```

**Layout:**
```
+-----------------------------------------------------------+
| EFFECTS CASCADE                                           |
|                                                           |
| Thesis: "GPU supply constraint drives power demand"       |
|                                                           |
| 1st Order             2nd Order            3rd Order      |
| +----------------+    +----------------+   +-----------+  |
| | Direct GPU     |    | Power grid     |   | Land/     |  |
| | suppliers      |--->| infrastructure |--->| permitting|  |
| | [NVDA] [AMD]   |    | [EQIX] [VRT]  |   | [CBRE]   |  |
| +----------------+    +----------------+   +-----------+  |
|                       |                                   |
|                       +--+----------------+               |
|                          | Cooling tech   |               |
|                          | [VRTX]         |               |
|                          +----------------+               |
+-----------------------------------------------------------+
```

**Visual Description:**
- Tree/cascade layout: Three columns representing effect orders, connected by arrows
- Each thesis is a separate tree (if multiple theses, stacked vertically with dividers)
- Effect nodes: `bg-surface border border-border rounded-xl p-3` with effect description and linked tickers
- Linked tickers: `font-mono text-xs text-primary cursor-pointer` badges
- Arrows: CSS borders or SVG connecting nodes left-to-right
- Order column headers: `text-xs font-semibold uppercase tracking-wider` with numbered badge

**States:**
- **Loading:** Skeleton tree structure
- **Empty:** "Effects will be mapped after equity identification."
- **Data:** Full cascade visualization
- **No 3rd order:** Third column shows "No third-order effects identified" in muted text

**Accessibility:**
- Tree: Structured as nested lists (`ul > li > ul > li`) for screen readers
- Arrows: `aria-hidden="true"` (decorative)
- Thesis text: `role="heading" aria-level="3"` for each thesis group

---

### InvariantChecklist
**File:** `frontend/components/ist/InvariantChecklist.tsx`
**Purpose:** Displays the 8 IST screening invariants with pass/fail status, ensuring the screen meets all quality requirements.

**Props:**
```typescript
interface InvariantChecklistProps {
  invariants: InvariantResult[];
  isChecking: boolean;
  overallPass: boolean;
  onRecheck?: () => void;
}

interface InvariantResult {
  code: string;                    // "INV-1" through "INV-8"
  name: string;                    // e.g., "Quantitative Anchoring"
  description: string;             // What this invariant checks
  passed: boolean;
  detail: string;                  // Specific pass/fail evidence
  violations?: string[];           // List of specific violations if failed
}
```

**Layout:**
```
+-----------------------------------------------------------+
| INVARIANT COMPLIANCE              [6/8 PASSED] [Recheck]  |
|                                                           |
| [checkmark] INV-1: Quantitative Anchoring                 |
|   All claims have numeric support                         |
|                                                           |
| [checkmark] INV-2: Temporal Specificity                   |
|   All bottlenecks have dated resolution triggers          |
|                                                           |
| [X] INV-3: Source Diversity                               |
|   VIOLATION: Only 1 content source (minimum 2 required)   |
|                                                           |
| [X] INV-7: Anti-Hallucination                             |
|   VIOLATION: Claim #4 has no source attribution           |
|   VIOLATION: Demand model uses unverified $200B estimate  |
|                                                           |
| ...                                                       |
+-----------------------------------------------------------+
```

**Visual Description:**
- Card: `bg-surface rounded-xl shadow-card p-6`
- Header: Invariant name + pass count badge ("6/8 PASSED" -- green if all pass, amber if partial, red if <50%)
- Each invariant: Expandable row with status icon + code + name
  - Passed: `CheckCircle text-bull`, detail in `text-text-secondary text-sm`
  - Failed: `XCircle text-bear`, detail in `text-bear text-sm font-medium`, violations listed as bullet points in `bg-bear/5 rounded-lg p-3 mt-1`
- Failed invariants sorted to top for visibility

**States:**
- **Loading / Checking:** Skeleton checklist
- **All pass:** Green header badge, clean list
- **Partial pass:** Amber badge, failed items at top with red accent
- **Majority fail:** Red badge, prominent failure messaging

**Accessibility:**
- Checklist: `role="list"` with `aria-label="Invariant compliance checklist"`
- Overall status: `aria-live="polite"` on the pass count badge
- Violations: `role="alert"` on failed items

---

### DialecticView
**File:** `frontend/components/ist/DialecticView.tsx`
**Purpose:** Side-by-side display of the Optimist and Pessimist analyses from the IST dialectic scrutiny phase. Allows comparison of bull and bear cases on the same screen.

**Props:**
```typescript
interface DialecticViewProps {
  optimist?: DialecticReview;
  pessimist?: DialecticReview;
  isRunning: boolean;
  runningPhase?: "optimist" | "pessimist" | "both" | "synthesis";
}

interface DialecticReview {
  side: "OPTIMIST" | "PESSIMIST";
  keyArguments: string[];
  riskAssessment: string;
  tierAdjustments: { ticker: string; currentTier: number; proposedTier: number; reason: string }[];
  catalystOpinion: string;
  overallConviction: string;      // Summary paragraph
  createdAt: string;
}
```

**Layout:**
```
+-----------------------------------------------------------+
| DIALECTIC SCRUTINY                                        |
|                                                           |
| +-------------------------+  +-------------------------+  |
| | [ThumbsUp] OPTIMIST     |  | [ThumbsDown] PESSIMIST  |  |
| |                         |  |                         |  |
| | Key Arguments:          |  | Key Arguments:          |  |
| | * Market misperception  |  | * Demand deceleration   |  |
| |   on AI infrastructure  |  |   risk understated     |  |
| | * Cooling TAM underest. |  | * Competitor entry in   |  |
| |                         |  |   12-18 months         |  |
| |                         |  |                         |  |
| | Tier Adjustments:       |  | Tier Adjustments:       |  |
| | NVDA: T1 -> T1 (hold)   |  | NVDA: T1 -> T2 (risk)   |  |
| | VRT:  T2 -> T1 (upgrade)|  | VRT:  T2 -> T3 (caution)|  |
| |                         |  |                         |  |
| | Conviction: Bullish     |  | Conviction: Cautious    |  |
| +-------------------------+  +-------------------------+  |
+-----------------------------------------------------------+
```

**Visual Description:**
- Two-column layout on desktop (`grid grid-cols-1 lg:grid-cols-2 gap-4`), stacked on mobile
- Optimist panel: `bg-surface border border-border rounded-xl p-5 border-l-[3px] border-l-bull`
  - Header: `ThumbsUp` icon in `text-bull` + "OPTIMIST" in `text-sm font-semibold uppercase tracking-wider text-bull`
- Pessimist panel: `bg-surface border border-border rounded-xl p-5 border-l-[3px] border-l-bear`
  - Header: `ThumbsDown` icon in `text-bear` + "PESSIMIST" in `text-sm font-semibold uppercase tracking-wider text-bear`
- Key arguments: Bulleted list
- Tier adjustments: Mini table with ticker (mono), current/proposed tier badges, reason
- Conviction: Summary paragraph at bottom

**States:**
- **Loading (both running):** Both panels show skeleton with animated "Analyzing..." text
- **One running:** Completed panel shows data, running panel shows skeleton
- **Complete:** Both panels with full data
- **Not started:** Both panels empty with "Dialectic analysis has not been run" message and "Run Dialectic" button

**Accessibility:**
- Panels: `role="region" aria-label="Optimist analysis"` / `"Pessimist analysis"`
- Tier adjustments: Table with proper headers
- Running state: `aria-busy="true"` on running panel

---

### SynthesisReport
**File:** `frontend/components/ist/SynthesisReport.tsx`
**Purpose:** Displays the synthesis/reconciliation of the optimist and pessimist dialectic reviews, showing where they agreed, disagreed, and the final reconciled position.

**Props:**
```typescript
interface SynthesisReportProps {
  synthesis?: DialecticSynthesis;
  isLoading: boolean;
}

interface DialecticSynthesis {
  agreements: string[];
  disagreements: DisagreementResolution[];
  reconciledTiers: { ticker: string; optimistTier: number; pessimistTier: number; finalTier: number; rationale: string }[];
  overallAssessment: string;
  confidenceLevel: "high" | "moderate" | "low";
  createdAt: string;
}

interface DisagreementResolution {
  topic: string;
  optimistPosition: string;
  pessimistPosition: string;
  resolution: string;
  favoredSide: "optimist" | "pessimist" | "balanced";
}
```

**Layout:**
```
+-----------------------------------------------------------+
| SYNTHESIS                                    [Confidence:  |
| [Scale icon]                                  MODERATE]    |
|                                                           |
| Agreements                                                |
| * Both agree AI infrastructure demand is structural       |
| * Both agree cooling is a genuine bottleneck              |
|                                                           |
| Disagreements & Resolutions                               |
| +-----------------------------------------------------+ |
| | Topic: Demand deceleration risk                      | |
| | Optimist: "Hyperscaler capex guidance supports..."   | |
| | Pessimist: "Cyclical downturn could reduce..."       | |
| | Resolution: Moderate risk; base case intact but...   | |
| | Favored: Balanced                                    | |
| +-----------------------------------------------------+ |
|                                                           |
| Reconciled Tiers                                          |
| Ticker  Optimist  Pessimist  Final   Rationale            |
| NVDA    T1        T2         T1      ...                  |
| VRT     T1        T3         T2      ...                  |
|                                                           |
| Overall Assessment                                        |
| [summary paragraph]                                       |
+-----------------------------------------------------------+
```

**Visual Description:**
- Card: `bg-surface rounded-xl shadow-card p-6 border-l-[3px] border-l-primary`
- Header: `Scale` icon in primary color + "SYNTHESIS" + confidence badge (right-aligned)
- Agreements section: Bulleted list with `CheckCircle text-bull` icons
- Disagreements: Expandable cards per disagreement
  - Optimist position: `border-l-2 border-l-bull bg-bull/5 p-3 rounded-r-lg text-sm`
  - Pessimist position: `border-l-2 border-l-bear bg-bear/5 p-3 rounded-r-lg text-sm`
  - Resolution: `text-sm text-text-primary font-medium`
  - Favored badge: optimist=green, pessimist=red, balanced=primary
- Reconciled tiers table: Standard data table with tier badges showing before/after
- Overall assessment: `text-sm text-text-primary leading-relaxed` paragraph

**States:**
- **Loading:** Skeleton card
- **Data:** Full synthesis display
- **Not available:** "Synthesis will be generated after both dialectic reviews complete."

**Accessibility:**
- Disagreement cards: `role="article"` with structured headings
- Favored side: Communicated via text, not just color
- Confidence: `aria-label="Confidence level: moderate"`

---

## New Components: IST Output (Phase 5)

### MasterScreenTable
**File:** `frontend/components/ist/MasterScreenTable.tsx`
**Purpose:** The final ranked equity screen table showing all candidates with conviction scores, tier classifications, thesis summaries, and invariant compliance. This is the structured data companion to the narrative Investment Thesis Report.

**Props:**
```typescript
interface MasterScreenTableProps {
  equities: MasterScreenEquity[];
  isLoading: boolean;
  sortField?: string;
  sortDirection?: "asc" | "desc";
  onSort?: (field: string) => void;
  onEquityClick?: (ticker: string) => void;
}

interface MasterScreenEquity {
  rank: number;
  ticker: string;
  companyName: string;
  tier: 1 | 2 | 3;
  compositeScarcity: number;
  conviction: number;              // 0-100
  phase: 1 | 2 | 3;
  bottleneck: string;
  catalyst: string;
  moatType: string;
  thesisSummary: string;
  invariantCompliance: boolean;
}
```

**Columns:**
| Column | Font | Sortable | Alignment |
|--------|------|----------|-----------|
| Rank | mono | Yes | Center |
| Ticker | mono, bold, primary | Yes | Left |
| Company | sans | Yes | Left |
| Tier | badge | Yes | Center |
| Scarcity | mono | Yes | Right |
| Conviction | mono + mini bar | Yes | Right |
| Phase | badge | Yes | Center |
| Bottleneck | sans, sm | No | Left |
| Catalyst | sans, sm | No | Left |

**Visual Description:**
- Dense data table with `py-2.5` cell padding
- Rank column: `font-mono text-text-secondary text-center w-12`
- Ticker: `font-mono font-bold text-primary cursor-pointer hover:underline`
- Conviction: Percentage + horizontal mini bar (`h-1 rounded-full` with green/amber/red fill based on value)
- Row grouping: Visual gap between tiers (or a subtle tier divider row)
- Export button: Top-right of table header, downloads CSV

**States:**
- **Loading:** SkeletonLoader variant="table-row" count=10
- **Empty:** "Master screen will be generated in Phase 5."
- **Data:** Full ranked table, default sort by conviction descending

**Accessibility:**
- Standard table ARIA
- Rank changes: If re-sorted, rank column does not change (rank is the master order)
- Tier and phase communicated via text, not just badge color

---

### RotationStrategy
**File:** `frontend/components/ist/RotationStrategy.tsx`
**Purpose:** Phase-based allocation chart showing how portfolio exposure should rotate as bottleneck phases progress, with rotation triggers and risk limits.

**Props:**
```typescript
interface RotationStrategyProps {
  phaseAllocations: PhaseAllocation[];
  rotationTriggers: RotationTrigger[];
  riskLimits: RiskLimit[];
  isLoading: boolean;
}

interface PhaseAllocation {
  phase: 1 | 2 | 3;
  phaseLabel: string;
  allocationPercent: number;       // Percentage of portfolio
  topNames: { ticker: string; weight: number }[];
}

interface RotationTrigger {
  fromPhase: number;
  toPhase: number;
  trigger: string;                 // e.g., "GPU supply normalizes (ASPs decline >20%)"
  signalType: "leading" | "lagging" | "coincident";
}

interface RiskLimit {
  name: string;
  limit: string;
  rationale: string;
}
```

**Layout:**
```
+-----------------------------------------------------------+
| ROTATION STRATEGY                                         |
|                                                           |
| Phase Allocation                                          |
| [====Phase 1: 50%====][==Phase 2: 35%==][Phase 3: 15%]  |
|                                                           |
| Phase 1 (50%)          Phase 2 (35%)     Phase 3 (15%)   |
| NVDA  25%              EQIX  15%         CBRE  8%        |
| ANET  15%              VRT   12%         XYZ   7%        |
| AMD   10%              POWL   8%                         |
|                                                           |
| Rotation Triggers                                         |
| Phase 1 -> 2: GPU supply normalizes (ASP decline >20%)   |
| Phase 2 -> 3: Power permits accelerate (>50 approved)    |
|                                                           |
| Risk Limits                                               |
| * Single name max: 25%                                   |
| * Single phase max: 60%                                  |
| * Tier 3 max: 15%                                        |
+-----------------------------------------------------------+
```

**Visual Description:**
- Card: `bg-surface rounded-xl shadow-card p-6`
- Allocation bar: Horizontal stacked bar with phase colors, percentage labels inside segments
- Phase breakdown: Three-column grid showing top names per phase with weights in `font-mono`
- Rotation triggers: Timeline-style list with arrow connectors between phases
- Risk limits: Bulleted list with `font-mono` limit values

**States:**
- **Loading:** Skeleton bar + skeleton lists
- **Empty:** "Rotation strategy will be generated in Phase 5."
- **Data:** Full strategy display

**Accessibility:**
- Allocation bar: `role="img" aria-label="Phase allocation: Phase 1 50%, Phase 2 35%, Phase 3 15%"`
- Tables and lists with proper semantic markup

---

### CatalystCalendar
**File:** `frontend/components/ist/CatalystCalendar.tsx`
**Purpose:** Timeline/calendar view of dated catalysts for equity candidates, showing upcoming events that could trigger position changes.

**Props:**
```typescript
interface CatalystCalendarProps {
  catalysts: CatalystEvent[];
  isLoading: boolean;
  viewMode?: "timeline" | "list";  // default: "timeline"
  onCatalystClick?: (catalyst: CatalystEvent) => void;
}

interface CatalystEvent {
  id: number;
  date: string;                    // ISO date or "Q3 2026" or "H2 2026"
  dateType: "exact" | "quarter" | "half" | "year";
  ticker: string;
  event: string;                   // e.g., "NVDA earnings report"
  catalystType: "earnings" | "regulatory" | "product" | "macro" | "trigger";
  impact: "high" | "medium" | "low";
  thesis: string;                  // How this catalyst connects to the thesis
}
```

**Layout (Timeline View):**
```
+-----------------------------------------------------------+
| CATALYST CALENDAR                    [Timeline] [List]    |
|                                                           |
| 2026                                                      |
| Feb ----*---- Mar ----*---- Apr --------*---- May ------> |
|         |           |                   |                 |
|   NVDA Earnings  Regulatory    EQIX Expansion             |
|   [HIGH]         Review [MED]  Announcement [HIGH]        |
|                                                           |
| Q3 2026                                                   |
|   * GPU supply assessment due (NVDA, AMD)                 |
|                                                           |
| H2 2026                                                   |
|   * Power grid infrastructure permits (EQIX, VRT)        |
+-----------------------------------------------------------+
```

**Visual Description:**
- Timeline view: Horizontal timeline with months, events plotted as dots with cards below
  - High impact: Large primary-colored dot + card with `border-l-[3px] border-l-primary`
  - Medium impact: Medium info-colored dot + card with `border-l-[3px] border-l-info`
  - Low impact: Small muted dot + card with `border-l-[3px] border-l-border-strong`
- List view: Simple sortable table (Date, Ticker, Event, Type, Impact)
- Approximate dates (quarter/half/year): Grouped in sections below the exact-date timeline
- Catalyst type badges: Small colored chips (earnings=info, regulatory=warning, product=primary, macro=purple, trigger=bull)

**States:**
- **Loading:** Skeleton timeline
- **Empty:** "Catalysts will be generated in Phase 5."
- **Data:** Full timeline/list
- **No exact dates:** Only grouped approximate-date sections shown

**Accessibility:**
- Timeline: Described as a list for screen readers (visual timeline is `aria-hidden`, accessible list provided)
- Impact level communicated via text badge, not dot size alone
- View mode toggle: `role="radiogroup"`

---

### StressTestResults
**File:** `frontend/components/ist/StressTestResults.tsx`
**Purpose:** Displays stress test results including framework-level tests, name-level tests, and survival scores with expandable detail.

**Props:**
```typescript
interface StressTestResultsProps {
  frameworkTests: FrameworkStressTest[];
  nameTests: NameStressTest[];
  survivalScores: SurvivalScore[];
  isLoading: boolean;
}

interface FrameworkStressTest {
  frameworkName: string;
  scenario: string;
  result: string;
  severity: "survives" | "impaired" | "fails";
}

interface NameStressTest {
  ticker: string;
  scenario: string;
  impactDescription: string;
  priceImpact: string;            // e.g., "-30% to -50%"
  recoveryTimeline: string;       // e.g., "12-18 months"
  severity: "survives" | "impaired" | "fails";
}

interface SurvivalScore {
  ticker: string;
  score: number;                   // 0-100
  scenariosTested: number;
  survived: number;
  impaired: number;
  failed: number;
}
```

**Layout:**
```
+-----------------------------------------------------------+
| STRESS TESTS                                              |
|                                                           |
| Survival Scores                                           |
| Ticker  Score   Survived  Impaired  Failed                |
| NVDA    85/100  4         1         0                     |
| EQIX    72/100  3         1         1                     |
| VRT     60/100  2         2         1                     |
|                                                           |
| Framework-Level Tests                                     |
| +-----------------------------------------------------+ |
| | Scarcity Scoring: "What if GPU supply doubles?"      | |
| | Result: Thesis impaired for Phase 1 names, but...    | |
| | Severity: [IMPAIRED]                                 | |
| +-----------------------------------------------------+ |
|                                                           |
| Name-Level Tests (expand each)                            |
| > NVDA: 2 scenarios tested                               |
|   - "Demand drops 40%": -30% price, 12mo recovery       |
|   - "Competitor catch-up": -15% price, 6mo recovery     |
+-----------------------------------------------------------+
```

**Visual Description:**
- Three sections: Survival scores table, framework tests, name tests
- Survival score table: Standard data table, score column has mini bar (>70 bull, 40-70 warning, <40 bear)
- Framework tests: Card per test with severity badge
  - survives: `border-l-[3px] border-l-bull` + green badge
  - impaired: `border-l-[3px] border-l-warning` + amber badge
  - fails: `border-l-[3px] border-l-bear` + red badge
- Name tests: Accordion per ticker, expandable to show individual scenarios
- Price impact: `font-mono text-bear` for negative values

**States:**
- **Loading:** Skeleton table + skeleton cards
- **Empty:** "Stress tests will be generated in Phase 5."
- **Data:** Full display with first framework test expanded

**Accessibility:**
- Tables: Standard ARIA
- Severity communicated via text badges, not color alone
- Accordions: `aria-expanded` on triggers

---

### InvestmentThesisReport
**File:** `frontend/components/ist/InvestmentThesisReport.tsx`
**Purpose:** PRIMARY VIEW. Full Investment Thesis Report renderer. This is the main deliverable of the IST workflow -- a polished, printable narrative document synthesizing all analysis into a pillar-organized research report.

**Props:**
```typescript
interface InvestmentThesisReportProps {
  report?: ISTReport;
  isLoading: boolean;
  isGenerating: boolean;           // Report being generated (SSE progress)
  onExport: () => void;
  onPrint: () => void;
}

interface ISTReport {
  id: number;
  title: string;
  content: string;                 // Full markdown content
  metadata: {
    pillarCount: number;
    equityCount: number;
    tierBreakdown: { tier1: number; tier2: number; tier3: number };
  };
  createdAt: string;
}
```

**Layout:**
```
+-----------------------------------------------------------+
| [Sticky TOC sidebar]  REPORT CONTENT                      |
| +------------------+  +--------------------------------+  |
| | I. Executive     |  | INVESTMENT THESIS REPORT        |  |
| |    Summary       |  | Energy Scarcity & AI Infra      |  |
| | II. Pillar       |  | Generated: Feb 7, 2026          |  |
| |    Analysis      |  |                                 |  |
| |   a. GPU Supply  |  | I. EXECUTIVE SUMMARY             |  |
| |   b. Power Grid  |  |                                 |  |
| |   c. Cooling     |  | The convergence of accelerating |  |
| | III. Effects     |  | AI compute demand with physical |  |
| | IV. Framing      |  | infrastructure constraints...   |  |
| | V. Portfolio     |  |                                 |  |
| | VI. Disclaimer   |  | [Consolidated Screen Table]     |  |
| |                  |  |                                 |  |
| | [Export] [Print] |  | II. PILLAR-BY-PILLAR ANALYSIS   |  |
| +------------------+  |                                 |  |
|                        | A. GPU Supply Constraint        |  |
|                        | ...narrative prose...           |  |
|                        |                                 |  |
|                        | > SKEPTIC'S STRESS TEST:        |  |
|                        | > What if GPU supply doubles?   |  |
|                        |                                 |  |
|                        | NVDA ($130, P/E 35x, Tier 1)   |  |
|                        | [3-5 sentence equity thesis]   |  |
|                        +--------------------------------+  |
+-----------------------------------------------------------+
```

**Visual Description:**
- Two-column layout on desktop: Sticky TOC sidebar (left/right, `w-56 sticky top-6`) + report content (flex-1)
- Report content: `max-w-3xl mx-auto` for optimal reading width
- Title: `font-display text-2xl font-bold text-text-primary mb-1`
- Date: `text-xs text-text-tertiary`
- Section headings (I, II, III...): `font-display text-xl font-semibold text-text-primary mt-8 mb-4 border-b border-border pb-2`
- Sub-headings (A, B, C...): `text-lg font-semibold text-text-primary mt-6 mb-3`
- Body text: `text-sm leading-relaxed text-text-primary`
- Blockquotes (stress test callouts): `border-l-[3px] border-l-warning bg-warning/5 p-4 rounded-r-lg my-4 text-sm italic`
- Inline ticker mentions: `font-mono font-semibold text-primary`
- Consolidated screen table: Standard data table pattern (dense), embedded within executive summary section
- Equity thesis blocks: `bg-surface-elevated rounded-xl p-4 my-3` with ticker header in mono-bold, price/PE/tier badges, then thesis prose
- TOC sidebar:
  - Container: `bg-surface rounded-xl shadow-card p-4`
  - Section links: `text-xs text-text-secondary hover:text-primary cursor-pointer py-1`
  - Active section: `text-primary font-medium` (tracked via scroll position IntersectionObserver)
  - Export/Print buttons at bottom of TOC
- Generating state: Skeleton report with animated "Generating Investment Thesis Report..." banner and step progress

**States:**
- **Loading:** Skeleton report layout
- **Generating:** Animated progress with step indicator (e.g., "Synthesizing pillar analysis..."), partial content may stream in
- **Data:** Full rendered report with TOC
- **Empty (no report yet):** "The Investment Thesis Report will be generated in Phase 5 after all analysis is complete." centered with phase progress indicator
- **Export/Print:** Opens browser print dialog with print-optimized CSS (hide TOC, full-width content)

**Accessibility:**
- Report: Semantic HTML headings (`h1`, `h2`, `h3`) for document structure
- TOC: `nav role="navigation" aria-label="Table of contents"`
- Blockquotes: `role="note"` for stress test callouts
- Screen table: Full table ARIA
- Export/Print: Button labels include action ("Export report as PDF", "Print report")

---

### ScreenCertification
**File:** `frontend/components/ist/ScreenCertification.tsx`
**Purpose:** Final certification badge and summary displayed after a screen passes all quality gates and completes all phases. Shows certification status, summary stats, and HFRT handoff readiness.

**Props:**
```typescript
interface ScreenCertificationProps {
  certification?: Certification;
  isLoading: boolean;
}

interface Certification {
  certified: boolean;
  certifiedAt: string;
  screenName: string;
  summary: {
    totalCandidates: number;
    tier1Count: number;
    tier2Count: number;
    tier3Count: number;
    invariantsPassed: number;
    invariantsTotal: number;
    gatesPassed: number;
    gatesTotal: number;
  };
  hfrtReady: boolean;              // Whether Tier 1 names are ready for HFRT handoff
  tier1Names: string[];            // Tickers ready for deep research
}
```

**Layout:**
```
+-----------------------------------------------------------+
| +-----------------------------------------------------+ |
| | [ShieldCheck]  SCREEN CERTIFIED                      | |
| |                                                     | |
| | Energy Scarcity & AI Infrastructure                  | |
| | Certified: February 7, 2026 at 2:45 PM             | |
| |                                                     | |
| | 12 Candidates | 3 Tier 1 | 5 Tier 2 | 4 Tier 3    | |
| | 8/8 Invariants Passed | 3/3 Gates Passed           | |
| |                                                     | |
| | Ready for HFRT Deep Research:                       | |
| | [NVDA] [VRTX] [ANET]                               | |
| |                                                     | |
| | [Send to Deep Research ->]                          | |
| +-----------------------------------------------------+ |
+-----------------------------------------------------------+
```

**Visual Description:**
- Prominent card: `bg-bull/5 border-2 border-bull rounded-xl p-6` when certified, `bg-bear/5 border-2 border-bear` when not certified
- Header: `ShieldCheck` icon (36px) in `text-bull` + "SCREEN CERTIFIED" in `font-display text-lg font-bold text-bull`
- Stats: Horizontal row of stat items, each with monospace number + label
- Invariants/Gates: Badge showing "X/Y Passed" with green/red coloring
- Tier 1 names: Horizontal row of ticker badges in `font-mono font-bold bg-bull/10 text-bull rounded-lg px-3 py-1`
- HFRT handoff button: Primary button style, only shown when `hfrtReady` is true
- Not certified: Red theme, "SCREEN NOT CERTIFIED" with list of failures

**States:**
- **Loading:** Skeleton card
- **Certified:** Green theme celebration card
- **Not certified:** Red theme with failure reasons
- **Pending:** Gray card, "Certification will be evaluated after Phase 5 completes."

**Accessibility:**
- Certification status: `role="status" aria-label="Screen certified"` or `"Screen not certified"`
- Stats: Each stat announced clearly
- Handoff button: `aria-label="Send 3 Tier 1 names to HFRT deep research"`

---

## New Components: Frameworks

### FrameworkPanel
**File:** `frontend/components/frameworks/FrameworkPanel.tsx`
**Purpose:** Slide-out reference panel accessible from any IST (or HFRT) screen page, showing framework content for analyst reference.

**Props:**
```typescript
interface FrameworkPanelProps {
  isOpen: boolean;
  onClose: () => void;
  workflowType: "IST" | "HFRT";
  frameworks: FrameworkSummary[];
  selectedFramework?: string;
  onSelectFramework: (name: string) => void;
}

interface FrameworkSummary {
  name: string;                    // e.g., "scarcity_scoring"
  displayName: string;             // e.g., "Scarcity Scoring Framework"
  description: string;             // One-line summary
}
```

**Layout:**
```
+----+--------------------------------------------------+------+
|    |                                                  |      |
|    |  [Main page content]                             |FRAME |
|    |                                                  |WORK  |
|    |                                                  |PANEL |
|    |                                                  |      |
|    |                                                  | Name |
|    |                                                  | [...] |
|    |                                                  | Name |
|    |                                                  |      |
|    |                                                  |[cont]|
+----+--------------------------------------------------+------+
```

**Visual Description:**
- Panel: Fixed right side, `w-[480px] max-w-[90vw] h-full bg-surface shadow-xl rounded-l-xl` with smooth slide-in animation (`transition-transform duration-300`)
- Backdrop: `bg-black/20` overlay on the rest of the page, click to close
- Header: `border-b border-border p-4` with framework selector dropdown + close button (X icon)
- Body: Scrollable area with rendered framework content (uses FrameworkRenderer)
- Trigger button (not part of this component): Floating action button in bottom-right of screen detail page, `bg-primary text-white rounded-full w-12 h-12 shadow-lg hover:shadow-xl`

**States:**
- **Closed:** Panel not visible, only trigger button shown
- **Open, loading:** Panel visible with skeleton content
- **Open, framework selected:** Full framework content rendered
- **Open, no selection:** Framework list with descriptions, click to select

**Accessibility:**
- Panel: `role="dialog" aria-label="Framework reference panel" aria-modal="false"` (not truly modal, page still scrollable)
- Close: `aria-label="Close framework panel"`, Escape key closes
- Focus trapped within panel when open via keyboard navigation
- Framework selector: Standard select ARIA

---

### FrameworkRenderer
**File:** `frontend/components/frameworks/FrameworkRenderer.tsx`
**Purpose:** Renders framework markdown content with polished typography and section navigation.

**Props:**
```typescript
interface FrameworkRendererProps {
  content: string;                 // Markdown content
  frameworkName: string;
  isLoading: boolean;
}
```

**Visual Description:**
- Prose-styled markdown rendering using Tailwind Typography-like styles:
  - Headings: `font-display font-semibold text-text-primary` with appropriate size scale
  - Body: `text-sm text-text-primary leading-relaxed`
  - Code blocks: `bg-background rounded-lg p-3 font-mono text-sm border border-border`
  - Lists: Standard bullet/number styling with proper indentation
  - Tables: Standard data table pattern
  - Blockquotes: `border-l-[3px] border-l-info bg-info/5 p-3 rounded-r-lg text-sm`
  - Links: `text-primary hover:underline`
- Sections auto-generate anchor IDs for scrolling

**States:**
- **Loading:** Skeleton text blocks
- **Data:** Full rendered markdown
- **Error:** "Failed to load framework content" error message with retry

**Accessibility:**
- Rendered HTML uses semantic heading hierarchy
- Tables have proper headers
- Code blocks have `aria-label="Code example"`

---

## Skeleton Loader Extensions

The existing `SkeletonLoader` component should be extended with new variants for IST components:

```typescript
interface SkeletonLoaderProps {
  variant?: "card" | "table-row" | "score" | "report" | "text"
           | "workflow-tracker" | "bottleneck-map" | "radar-chart"
           | "timeline" | "checklist";
  count?: number;
}
```

New variant specifications:
- **workflow-tracker:** Horizontal bar skeleton + 4 step row skeletons
- **bottleneck-map:** Three-column grid of card skeletons
- **radar-chart:** Circular skeleton (sized by parent container)
- **timeline:** Horizontal line with dot skeletons + card skeletons below
- **checklist:** 8 rows of icon + text skeletons

---

## Testing Requirements

Each component must have:
1. **Rendering test:** Component renders without errors in all states (loading, empty, error, data)
2. **Props test:** All prop variants and edge cases render correctly
3. **Interaction test:** Clicks, keyboard navigation, hover states, expand/collapse, sort
4. **Accessibility test:** axe-core automated scan, ARIA attribute verification, keyboard focus order
5. **Loading/error/empty state tests:** Each state renders the correct UI
6. **Snapshot test:** Visual regression for key states (data, loading, error)

IST-specific test requirements:
- **SSE integration test:** WorkflowProgressTracker correctly processes SSE events and updates UI
- **Report rendering test:** InvestmentThesisReport renders all markdown sections including tables, blockquotes, and embedded ticker references
- **Radar chart test:** ScarcityRadar renders correct SVG geometry for various score combinations
- **Sort test:** EquityCandidatesTable and MasterScreenTable sort correctly by all sortable columns
- **Responsive test:** All IST components render correctly at mobile (< 640px), tablet (640-1024px), and desktop (> 1024px) breakpoints

---

**Created:** 2026-01-30
**Last Updated:** 2026-02-07
**Owner:** @Creative_Director
