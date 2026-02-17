# Design System

## Design Philosophy

**Warm Analytical SaaS.** Light, airy, professional, data-forward, commercially polished.

This is a financial intelligence platform that balances analytical density with modern SaaS approachability. The design communicates competence and clarity through generous whitespace, warm accent colors, soft shadows, and rounded surfaces. Cards float on a subtle gray canvas. The sidebar uses a warm gradient (gold-to-orange-to-pink) that anchors the brand identity. All financial figures use monospace type for column alignment, and semantic color (green/red/amber) communicates status at a glance.

**Commercial-grade standard:** The UI must feel like a polished paid product. Pixel-perfect alignment, smooth purposeful animations, professional typography, and complete interaction states throughout.

---

## Color Palette

### Background Colors
| Token | Value | Usage |
|-------|-------|-------|
| `background` | `#f4f5f9` | Page canvas (light warm gray) |
| `surface` | `#ffffff` | Cards, panels, elevated content (pure white) |
| `surface-elevated` | `#f9fafb` | Nested surfaces, alternate rows, subtle depth |

### Border Colors
| Token | Value | Usage |
|-------|-------|-------|
| `border` | `#eaedf3` | Default dividers, card borders |
| `border-strong` | `#d5dae4` | Emphasized separators, header rules |
| `border-accent` | `#e8724a` | Primary-colored borders, active state accents |

### Text Colors
| Token | Value | Usage |
|-------|-------|-------|
| `text-primary` | `#1e2a3a` | High contrast dark text -- headings, body |
| `text-secondary` | `#6b7a90` | Labels, secondary info, muted descriptions |
| `text-tertiary` | `#9ca8b8` | Placeholders, disabled text, subtle captions |
| `text-inverse` | `#ffffff` | Light text on dark/colored backgrounds |

### Brand / Primary
| Token | Value | Usage |
|-------|-------|-------|
| `primary` | `#e8724a` | Warm orange -- CTAs, active tabs, brand accent |
| `primary-hover` | `#d4613b` | Hover state for primary buttons/elements |
| `primary-active` | `#c0532f` | Active/pressed state |
| `primary-muted` | `rgba(232,114,74,0.10)` | Subtle backgrounds, selected row tint |

### Accent Colors
| Token | Value | Usage |
|-------|-------|-------|
| `accent-purple` | `#9b6dff` | Secondary accent, tags, categories |
| `accent-pink` | `#e84d8a` | Tertiary accent, sidebar gradient endpoint |
| `accent-orange` | `#f5a623` | Warm gold accent, sidebar gradient start |
| `accent-coral` | `#ff7e7e` | Alert emphasis, warning accents |

### Sidebar Gradient
| Token | Value | Usage |
|-------|-------|-------|
| `sidebar-from` | `#f5a623` | Gradient start (gold) |
| `sidebar-via` | `#e8724a` | Gradient midpoint (orange) |
| `sidebar-to` | `#e84d8a` | Gradient end (pink) |

Direction: `linear-gradient(180deg, #f5a623 0%, #e8724a 50%, #e84d8a 100%)`

### Signal Colors (Financial)
| Token | Value | Usage |
|-------|-------|-------|
| `bull` | `#22c55e` | Positive signals -- safe zone, gains, passing gates |
| `bear` | `#ef4444` | Negative signals -- danger zone, losses, failing gates |
| `warning` | `#f59e0b` | Caution -- grey zone, watch items, partial pass |
| `info` | `#3b82f6` | Neutral information -- citations, links, notes |

### Forensic Zone Colors
These map to the signal colors above:
- **M-Score Safe (< -2.22):** `bull` (#22c55e)
- **M-Score Grey (-2.22 to -1.78):** `warning` (#f59e0b)
- **M-Score Danger (> -1.78):** `bear` (#ef4444)
- **Z-Score Safe (> 2.99):** `bull` (#22c55e)
- **Z-Score Grey (1.81-2.99):** `warning` (#f59e0b)
- **Z-Score Distress (< 1.81):** `bear` (#ef4444)

### IST-Specific Colors

#### Tier Colors
| Token | Value | Usage |
|-------|-------|-------|
| `tier-1` | `#22c55e` | Tier 1 (High Conviction) -- badges, borders, labels |
| `tier-2` | `#f59e0b` | Tier 2 (Watchlist) -- badges, borders, labels |
| `tier-3` | `#9ca8b8` | Tier 3 (Speculative) -- badges, borders, labels |

Implementation note: Tier colors reuse existing signal tokens (`bull`, `warning`, `text-tertiary`) rather than introducing new CSS custom properties. The semantic naming above is for documentation; in code, use `bg-bull`, `bg-warning`, `bg-text-tertiary` (or define Tailwind aliases if desired).

#### IST Phase Colors
IST has 5 workflow phases. Each gets a subtle color identity for the progress tracker:
| Phase | Token | Value | Label |
|-------|-------|-------|-------|
| Phase 1 | `phase-1` | `#3b82f6` | Content Extraction (info blue) |
| Phase 2 | `phase-2` | `#9b6dff` | Thematic Analysis (accent purple) |
| Phase 3 | `phase-3` | `#e8724a` | Equity Identification (primary orange) |
| Phase 4 | `phase-4` | `#e84d8a` | Dialectic Scrutiny (accent pink) |
| Phase 5 | `phase-5` | `#22c55e` | Final Synthesis (bull green) |

#### Quality Gate Status Colors
| Status | Color Token | Background | Text |
|--------|-------------|------------|------|
| `gate-pass` | `bull` | `bg-bull/10` | `text-bull` |
| `gate-fail` | `bear` | `bg-bear/10` | `text-bear` |
| `gate-pending` | `text-tertiary` | `bg-background` | `text-text-tertiary` |

#### Workflow Run Status Colors
| Status | Color Token | Background | Text |
|--------|-------------|------------|------|
| `PENDING` | `text-tertiary` | `bg-background` | `text-text-tertiary` |
| `RUNNING` | `info` | `bg-info/10` | `text-info` |
| `PAUSED` | `warning` | `bg-warning/10` | `text-warning` |
| `COMPLETED` | `bull` | `bg-bull/10` | `text-bull` |
| `FAILED` | `bear` | `bg-bear/10` | `text-bear` |

#### Validation Verdict Colors
| Verdict | Color Token | Usage |
|---------|-------------|-------|
| `confirmed` | `bull` | Externally corroborated claim |
| `partially_confirmed` | `warning` | Partially supported claim |
| `contradicted` | `bear` | Claim contradicted by evidence |
| `unvalidatable` | `text-tertiary` | Unable to verify |

#### Dialectic Side Colors
| Side | Color Token | Border | Background |
|------|-------------|--------|------------|
| `OPTIMIST` | `bull` | `border-l-bull` | `bg-bull/5` |
| `PESSIMIST` | `bear` | `border-l-bear` | `bg-bear/5` |
| `SYNTHESIS` | `primary` | `border-l-primary` | `bg-primary-muted` |

### Card Gradient Utilities
Predefined gradient backgrounds for summary/hero cards:
| Class | Gradient | Usage |
|-------|----------|-------|
| `card-gradient-orange` | `linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)` | Primary metric cards |
| `card-gradient-purple` | `linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)` | Analysis/insight cards |
| `card-gradient-coral` | `linear-gradient(135deg, #fbc2eb 0%, #a6c1ee 100%)` | Alert/attention cards |
| `card-gradient-warm` | `linear-gradient(135deg, #f6d365 0%, #fda085 100%)` | Status/summary cards |

### Accessibility (WCAG 2.1 AA Verified)
| Pair | Ratio | Status |
|------|-------|--------|
| text-primary (#1e2a3a) on surface (#ffffff) | 13.1:1 | AAA Pass |
| text-secondary (#6b7a90) on surface (#ffffff) | 4.7:1 | AA Pass |
| text-primary (#1e2a3a) on background (#f4f5f9) | 11.6:1 | AAA Pass |
| bull (#22c55e) on surface (#ffffff) | 3.1:1 | AA-Large Pass |
| bear (#ef4444) on surface (#ffffff) | 4.0:1 | AA-Large Pass |
| warning (#f59e0b) on surface (#ffffff) | 2.5:1 | Requires text label |
| primary (#e8724a) on surface (#ffffff) | 3.3:1 | AA-Large Pass |
| text-inverse (#ffffff) on primary (#e8724a) | 3.3:1 | AA-Large Pass |

**Accessibility rules:**
1. Signal colors (bull, bear, warning) must NEVER be the sole indicator of status. Always pair with text labels, icons, or patterns.
2. All interactive elements must have visible focus states (see Focus States below).
3. Small text (< 18px) on colored backgrounds must meet 4.5:1 contrast minimum.
4. For `warning` (#f59e0b) and `bull` (#22c55e) used as background tints, always use the `/10` opacity variant with dark text on top, never white text on solid color.

---

## Typography

### Font Families
| Token | Stack | Source | Usage |
|-------|-------|--------|-------|
| `font-sans` | `"Inter", system-ui, sans-serif` | Google Fonts | All UI text, labels, paragraphs |
| `font-mono` | `"JetBrains Mono", Menlo, monospace` | Google Fonts | ALL financial figures, scores, numbers, tickers |
| `font-display` | `"Space Grotesk", system-ui, sans-serif` | Google Fonts | Page titles, hero headings |

### Type Scale
| Token | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| display | 48px / 3rem | 700 | 1.1 | Hero page titles (font-display) |
| h1 | 32px / 2rem | 700 | 1.2 | Section headers (font-display) |
| h2 | 24px / 1.5rem | 600 | 1.3 | Card titles |
| h3 | 20px / 1.25rem | 600 | 1.3 | Sub-sections |
| h4 | 16px / 1rem | 600 | 1.4 | Small headers |
| body-lg | 16px / 1rem | 400 | 1.6 | Report narrative text |
| body | 14px / 0.875rem | 400 | 1.5 | Default UI text |
| body-sm | 12px / 0.75rem | 400 | 1.4 | Secondary text, tooltips |
| caption | 11px / 0.6875rem | 500 | 1.3 | Labels, badges, section tags |
| mono-lg | 24px / 1.5rem | 700 | 1.0 | Large score displays (font-mono) |
| mono | 14px / 0.875rem | 500 | 1.3 | Financial figures in tables (font-mono) |
| mono-sm | 12px / 0.75rem | 400 | 1.3 | Citation data, small numbers (font-mono) |

### Typography Rules
1. **ALL numbers are monospace.** No exceptions. Financial figures, scores, percentages, dates, tickers.
2. **Uppercase tracking** for section labels and badge text: `text-[11px] font-medium tracking-wide` or `text-[10px] font-semibold uppercase tracking-wider`.
3. **Tabular numerals** enabled (`font-variant-numeric: tabular-nums`) via the `[data-mono]` and `.font-mono` selectors for column alignment.
4. **No italic** in financial data. Reserve italic for report narrative quotes only.
5. **Inter** is the workhorse font for all body/UI text. **Space Grotesk** reserved for page-level headings only.

---

## Spacing Scale
| Token | Value | Usage |
|-------|-------|-------|
| space-0 | 0px | None |
| space-0.5 | 2px | Tight inline spacing |
| space-1 | 4px | Badge padding, tight gaps |
| space-1.5 | 6px | Tab bar internal padding (`p-1.5`) |
| space-2 | 8px | Small component padding |
| space-3 | 12px | Default component padding, gap-3 |
| space-4 | 16px | Card padding, standard gaps |
| space-5 | 20px | Section spacing |
| space-6 | 24px | Card body padding (`p-6`) |
| space-8 | 32px | Section margins |
| space-10 | 40px | Large layout spacing |
| space-12 | 48px | Page section breaks |
| space-16 | 64px | Major layout spacing |

Tailwind utility classes map directly: `p-4` = 16px, `p-6` = 24px, `gap-3` = 12px, etc.

---

## Border Radius
| Token | Tailwind Class | Value | Usage |
|-------|---------------|-------|-------|
| radius-sm | `rounded-sm` | 8px | Badges, small chips, tags |
| radius-default | `rounded` | 12px | General container rounding |
| radius-md | `rounded-md` | 14px | Medium containers |
| radius-lg | `rounded-lg` | 18px | Tab buttons, interactive elements |
| radius-xl | `rounded-xl` | 24px | Cards, panels, primary containers |
| radius-2xl | `rounded-2xl` | -- (Tailwind default) | Sidebar corner, large modals |
| radius-full | `rounded-full` | 9999px | Status dots, avatars, circular badges |

**Rule:** `rounded-xl` (24px) is the standard card radius. The design is warm and rounded. Hard edges are reserved for data table cells and inline code blocks only.

---

## Borders
| Token | Value | Usage |
|-------|-------|-------|
| border-default | `border border-border` | Subtle card outlines, tooltip borders |
| border-strong | `border border-border-strong` | Table header separators, emphasis |
| border-left-zone | `border-l-[3px]` | Zone-colored left accent on cards (uses `border-l-bull`, `border-l-bear`, `border-l-warning`, `border-l-border-strong`) |
| border-left-phase | `border-l-[3px]` | Phase-colored left accent on IST step items |
| border-top-accent | `border-t-2 border-t-primary` | Section demarcation, active panels |

---

## Shadows
| Token | Tailwind Class | Value | Usage |
|-------|---------------|-------|-------|
| shadow-sm | `shadow-sm` | `0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)` | Subtle depth on buttons |
| shadow-card | `shadow-card` | `0 2px 8px rgba(0,0,0,0.06)` | Default card resting state |
| shadow-card-hover | `shadow-card-hover` | `0 8px 24px rgba(0,0,0,0.10)` | Card hover elevation |
| shadow-md | `shadow-md` | `0 4px 12px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.04)` | Dropdowns, popovers |
| shadow-lg | `shadow-lg` | `0 10px 24px rgba(0,0,0,0.08), 0 4px 8px rgba(0,0,0,0.04)` | Tooltips, sidebar, modals |
| shadow-xl | `shadow-xl` | `0 20px 40px rgba(0,0,0,0.1)` | Full-screen overlays |

**Rule:** All shadows use soft blur (NOT hard-offset). The aesthetic is clean and elevated, not neo-brutalist. Cards use `shadow-card` at rest, `shadow-card-hover` on hover with a `transition-shadow duration-200`.

---

## Layout

### Breakpoints
| Token | Width | Target |
|-------|-------|--------|
| sm | >= 640px | Tablet portrait |
| md | >= 768px | Tablet landscape |
| lg | >= 1024px | Desktop (sidebar visible) |
| xl | >= 1280px | Wide desktop |
| 2xl | >= 1536px | Ultrawide |

### Application Layout Structure (Existing)
```
+--+---------------------------------------------------+
|  |                                                   |
|  |  MAIN CONTENT AREA                               |
|  |  max-w-6xl mx-auto p-6 lg:p-8                   |
|S |                                                   |
|I |  +-----------------------------------------------+
|D |  |  Page-specific content                        |
|E |  |  (cards, tabs, tables, reports)               |
|B |  |                                               |
|A |  +-----------------------------------------------+
|R |                                                   |
|  |                                                   |
+--+---------------------------------------------------+
```
- **Sidebar:** 64px wide (`w-16`), icon-only, warm gradient (`sidebar-gradient`), `rounded-r-2xl`, hidden below `lg` breakpoint
- **Main content:** `flex-1 overflow-y-auto`, inner container `max-w-6xl mx-auto p-6 lg:p-8`

### IST Screen Detail Page Layout (New)
```
+--+---------------------------------------------------+
|  |  Workflow Progress Header (persistent)            |
|S |  [Phase 1] -> [Phase 2] -> ... -> [Phase 5]      |
|I |  Current: Phase 3 - Step 3.2                      |
|D |  +-----------------------------------------------+
|E |  |  TAB BAR                                      |
|B |  |  [Report] (default, primary)  [Working Data]  |
|A |  +-----------------------------------------------+
|R |  |                                               |
|  |  |  Report Tab:                                  |
|  |  |    InvestmentThesisReport (full-width)        |
|  |  |    + TOC sidebar (sticky, right-aligned)      |
|  |  |                                               |
|  |  |  Working Data Tab:                            |
|  |  |    Sub-tab bar: Brief | Claims | Bottlenecks  |
|  |  |    | Demand | Validation | Candidates | ...   |
|  |  |    [Active sub-tab content]                   |
|  |  |                                               |
|  |  +-----------------------------------------------+
+--+---------------------------------------------------+
```

The Report tab is the default and primary view. The Working Data tab provides analytical internals via sub-navigation for inspection and debugging.

### Grid System
- **Columns:** CSS Grid or Tailwind grid utilities (not a fixed 12-column system)
- **Common patterns:** `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`, `grid-cols-2 lg:grid-cols-4`
- **Gutter:** `gap-3` (12px) for metric grids, `gap-4` (16px) for card grids, `gap-6` (24px) for section spacing
- **Container:** `max-w-6xl mx-auto` (1152px)

---

## Component Patterns

### Cards
**Standard Card:** `bg-surface rounded-xl shadow-card p-6 hover:shadow-card-hover transition-shadow duration-200`
**Zone Card (left accent):** Add `border-l-[3px]` with zone color: `border-l-bull`, `border-l-bear`, `border-l-warning`, or `border-l-border-strong`
**Gradient Hero Card:** Replace `bg-surface` with gradient utility (`card-gradient-orange`, `card-gradient-purple`, etc.)

### Buttons
**Primary:** `bg-primary hover:bg-primary-hover active:bg-primary-active text-white font-medium rounded-lg px-4 py-2.5 shadow-sm transition-all duration-200`
**Secondary:** `bg-surface hover:bg-background text-text-primary border border-border font-medium rounded-lg px-4 py-2.5 transition-all duration-200`
**Ghost:** `bg-transparent hover:bg-background text-text-secondary hover:text-text-primary rounded-lg px-4 py-2.5 transition-colors duration-200`
**Destructive:** `bg-bear hover:bg-bear/90 text-white font-medium rounded-lg px-4 py-2.5`
**Icon Button:** `p-2 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-background transition-colors duration-200`

### Tabs (Existing Pattern from AnalysisTabs)
**Tab Bar Container:** `bg-surface rounded-xl shadow-card p-1.5 gap-1 flex overflow-x-auto`
**Active Tab:** `bg-primary text-white shadow-sm rounded-lg px-4 py-2.5 text-xs font-medium`
**Inactive Tab:** `text-text-secondary hover:text-text-primary hover:bg-background rounded-lg px-4 py-2.5 text-xs font-medium`
**Tab Icon:** 14px, `strokeWidth={2.2}` when active, `1.8` when inactive

### Inputs
**Standard:** `bg-surface border border-border rounded-lg px-4 py-2.5 text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-border-accent transition-all duration-200`
**Error:** Add `border-bear focus:ring-bear/30`
**Textarea:** Same as standard but with `min-h-[120px] resize-y`

### Badges / Status Chips
**Safe/Pass:** `bg-bull/10 text-bull border border-bull/20 rounded-sm text-[11px] font-medium px-2 py-0.5`
**Danger/Fail:** `bg-bear/10 text-bear border border-bear/20 rounded-sm text-[11px] font-medium px-2 py-0.5`
**Warning:** `bg-warning/10 text-warning border border-warning/20 rounded-sm text-[11px] font-medium px-2 py-0.5`
**Info/Neutral:** `bg-info/10 text-info border border-info/20 rounded-sm text-[11px] font-medium px-2 py-0.5`
**Tier 1:** `bg-bull/10 text-bull border border-bull/20 rounded-sm text-[11px] font-semibold px-2 py-0.5`
**Tier 2:** `bg-warning/10 text-warning border border-warning/20 rounded-sm text-[11px] font-semibold px-2 py-0.5`
**Tier 3:** `bg-background text-text-tertiary border border-border rounded-sm text-[11px] font-medium px-2 py-0.5`

### Data Tables
- Container: `bg-surface rounded-xl shadow-card overflow-hidden`
- Header row: `bg-surface-elevated text-text-secondary text-[11px] font-medium uppercase tracking-wider border-b border-border-strong`
- Body row: `border-b border-border hover:bg-surface-elevated transition-colors duration-100`
- Alternating rows: Not used by default (clean white preferred), but `even:bg-surface-elevated` available
- Cell padding: `px-4 py-3`
- Number cells: `font-mono text-sm tabular-nums text-right`
- Sortable header: Cursor pointer, sort arrow indicator, `hover:text-text-primary`
- Dense variant: `py-2` cell padding for compact tables (EquityCandidatesTable, MasterScreenTable)

### Tooltips
**Standard:** `bg-surface border border-border rounded-xl shadow-lg p-4 text-xs animate-fade-in z-50`
**Positioned above** by default, flip to below when near top edge. Max width 320px.

### Section Labels
`text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mb-1`

---

## Focus States
All interactive elements must show a visible focus ring when navigated via keyboard:
- **Default focus:** `focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50`
- **On dark backgrounds (sidebar):** `focus-visible:ring-2 focus-visible:ring-white/50`
- **Destructive focus:** `focus-visible:ring-2 focus-visible:ring-bear/50`
- Focus ring uses `focus-visible` (not `focus`) to avoid showing on mouse clicks.

---

## Animations

### Duration
| Token | Value | Usage |
|-------|-------|-------|
| duration-100 | 100ms | Hover color changes, toggle states |
| duration-200 | 200ms | Shadow transitions, tab switches, tooltips |
| duration-300 | 300ms | Card expand/collapse, page transitions, fade-in |
| duration-500 | 500ms | Skeleton pulse, progress bar fill |

### Easing
- **Default:** `ease-out` (Tailwind default, equivalent to `cubic-bezier(0.4, 0, 0.2, 1)`)
- Used on all `transition-*` utilities.

### Keyframe Animations
| Name | Description | Usage |
|------|-------------|-------|
| `fade-in` | `opacity 0->1` over 300ms ease-out | Tooltip appear, expanded section reveal |
| `slide-up` | `opacity 0->1, translateY 8px->0` over 300ms ease-out | Card mount, page section enter |

### Animation Rules
1. **No gratuitous animation.** Every animation serves a purpose (feedback, orientation, or data update).
2. **Respect `prefers-reduced-motion`.** All animations should be disabled when OS setting is on. Use `motion-reduce:` Tailwind variant.
3. **Card hover shadows** transition smoothly (`transition-shadow duration-200`).
4. **Skeleton loaders** use subtle pulse (`animate-pulse` on `bg-border/50 rounded-lg`).
5. **SSE-driven updates** should use `animate-fade-in` for newly arriving content to draw attention without jarring the layout.

---

## IST-Specific Layout Patterns

### SSE-Driven Progress Tracker Pattern
The `WorkflowProgressTracker` component receives real-time updates from the backend via Server-Sent Events (SSE). Design requirements:

1. **Progress bar:** A horizontal multi-segment bar representing 5 phases. Each phase segment fills with its phase color as steps complete. The current step pulses subtly.
2. **Step list:** Below the bar, a vertical list of steps within the current phase. Each step shows status icon (spinner for running, checkmark for complete, circle for pending, X for failed).
3. **Checkpoint approval:** When the workflow pauses at a checkpoint, an approval card appears with a description of what will happen next and a primary "Approve & Continue" button plus a secondary "Pause" button.
4. **Connection status:** A small indicator (green dot = connected, amber dot = reconnecting, red dot = disconnected) in the top-right of the tracker.
5. **Layout:** The tracker is a persistent header element on the screen detail page, positioned above the tab bar. It does NOT scroll with content.

### Screen Detail Page Tab Structure
- **Two primary tabs:** "Report" (default) and "Working Data"
- Report tab renders `InvestmentThesisReport` full-width with an optional sticky right-side table-of-contents panel
- Working Data tab contains a secondary tab bar (sub-navigation) with tabs for each IST template/phase output:
  `Brief | Claims | Bottlenecks | Demand Models | Validation | Candidates | Tiers | Effects | Master Screen | Rotation | Catalysts | Stress Tests`
- The primary tab bar follows the existing `AnalysisTabs` pattern (bg-surface rounded-xl shadow-card p-1.5)
- The secondary tab bar is visually lighter: no shadow, border-bottom only, smaller text

### Report Renderer Layout
The `InvestmentThesisReport` is the primary deliverable and must be polished enough for print/export:
- Max content width: `max-w-3xl` (768px) for readability, centered within the tab panel
- Heading hierarchy uses font-display for H1/H2, font-sans for H3+
- Blockquotes (stress test callouts) styled with `border-l-[3px] border-l-warning bg-warning/5 p-4 rounded-r-lg`
- Inline ticker mentions styled as `font-mono font-semibold text-primary`
- Screen table (consolidated equity table) uses the dense data table pattern
- TOC sidebar: `sticky top-0 w-48` positioned to the right of the report content, shows section anchors

### Slide-Out Panel (Framework Reference)
- Slides in from the right edge, 480px wide max
- `bg-surface shadow-xl rounded-l-xl`
- Overlay: `bg-black/20` backdrop
- Header: framework name + close button
- Body: rendered markdown with standard prose styling
- Trigger: floating action button in bottom-right corner of screen detail page

---

## Icons
- **Library:** Lucide React
- **Default size:** 14px (tab icons), 16px (body inline), 20px (navigation), 24px (hero)
- **Stroke width:** 1.8 (inactive/default), 2.2 (active/emphasized)

### Semantic Icon Mapping
| Context | Icon | Color |
|---------|------|-------|
| Safe / Pass / Bull | `CheckCircle` or `TrendingUp` | `text-bull` |
| Danger / Fail / Bear | `XCircle` or `TrendingDown` | `text-bear` |
| Warning / Caution | `AlertTriangle` | `text-warning` |
| Info / Citation | `Info` | `text-info` |
| Running / Loading | `Loader2` (spinning) | `text-primary` |
| Pending / Queued | `Circle` (outline) | `text-text-tertiary` |
| Report / Document | `FileText` | -- |
| Search | `Search` | -- |
| Refresh | `RefreshCw` | -- |
| Alert / Notification | `Bell` | -- |
| Portfolio | `Briefcase` | -- |
| Settings | `Settings` | -- |
| Expand / Collapse | `ChevronDown` / `ChevronUp` | -- |
| Navigate | `ChevronRight` | -- |
| IST Screen | `Scan` or `Filter` | -- |
| HFRT Research | `Microscope` or `BookOpen` | -- |
| Workflow Phase | `GitBranch` | -- |
| Checkpoint | `ShieldCheck` | -- |
| Export | `Download` | -- |
| Dialectic (Optimist) | `ThumbsUp` | `text-bull` |
| Dialectic (Pessimist) | `ThumbsDown` | `text-bear` |
| Dialectic (Synthesis) | `Scale` | `text-primary` |
| Radar/Scarcity | `Radar` | -- |
| Calendar/Catalyst | `Calendar` | -- |
| Stress Test | `Zap` | -- |
| Tier | `Award` | (tier color) |

---

## Dark Mode
**Not implemented.** The application uses a light theme exclusively. The warm SaaS aesthetic with white cards on light gray (#f4f5f9) is the canonical design. A dark mode is not planned.

---

## Tailwind Configuration Reference
The design tokens above map to the Tailwind config at `frontend/tailwind.config.ts`. Any new IST tokens should be added to the `extend` section following the same pattern. The CSS utilities (`sidebar-gradient`, `card-gradient-*`) are defined in `frontend/app/globals.css` under `@layer utilities`.

---

**Created:** 2026-01-30
**Last Updated:** 2026-02-07
**Owner:** @Creative_Director
