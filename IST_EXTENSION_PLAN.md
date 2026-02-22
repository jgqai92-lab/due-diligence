# IST Extension Plan: Cross-Screen Synthesis + Screen Refresh

> **Author:** Claude Code (CC)
> **Date:** 2026-02-21
> **Target:** Financial Due Diligence Application (FastAPI + Next.js)
> **Status:** IMPLEMENTATION PLAN FOR CODEX

---

## Overview

Two new features for the IST module of the Financial Due Diligence Application:

1. **Cross-Screen Synthesis** — Combine 2+ completed IST screens into a unified meta-analysis that re-evaluates tier classifications based on combined thesis interactions.
2. **Screen Refresh** — Update an existing completed screen with new content without re-running the entire 22-step pipeline.

Both features are additive. No behavioral regressions to existing IST flows; targeted additive modifications are required in listed files (see Part 4: File Inventory for the complete list).

---

## Current Architecture (Reference)

### Database (13 IST tables)
- `ist_screens` — screen metadata, status enum (PENDING → COMPLETED), raw_content, screening_brief/content_extraction/source_bias/certification/hfrt_handoff as JSON columns
- `ist_claims` — extracted claims with quantitative_anchor, temporal_marker, confidence
- `ist_bottlenecks` — temporal bottlenecks with phase (0-3), causal_parent_id self-ref
- `ist_demand_models` — TAM models per bottleneck (base/bull/bear JSON)
- `ist_validations` — external validation per claim (verdict: confirmed/contradicted/etc.)
- `ist_equity_candidates` — tickers with scarcity_score JSON, tier (1-3), bottleneck_id FK
- `ist_effects_chains` — multi-order effects (order 1-3) linked to equity_candidate_id
- `ist_dialectic_reviews` — OPTIMIST/PESSIMIST/SYNTHESIS reviews (unique per screen+side)
- `ist_master_screens` — ranked_equities JSON, invariant_compliance, tier1_count
- `ist_rotation_strategies` — phase_allocations, rotation_triggers, risk_limits JSON
- `ist_catalyst_calendars` — catalysts JSON, next_catalyst_date
- `ist_stress_tests` — framework_tests, name_tests, survival_scores JSON
- `ist_reports` — Investment Thesis Report (title, content markdown, metadata JSON)

### Backend
- Models: `backend/app/models/ist.py`
- Router: `backend/app/routers/ist.py` (25 endpoints under `/api/ist`)
- Schemas: `backend/app/schemas/ist.py`
- Services: `backend/app/services/ist/` (content_extraction.py, thematic_analysis.py, equity_identification.py, dialectic.py, final_synthesis.py, claude_client.py)
- Workflow engine: `backend/app/services/workflow_engine.py` (register_step decorator, SSE, DAG scheduler)
- Migrations: `backend/alembic/versions/` (currently 001-014)

### Frontend
- Pages: `frontend/app/screens/page.tsx` (list), `new/page.tsx` (create), `[id]/page.tsx` (detail)
- Components: `frontend/components/ist/` (23 components)
- API client: `frontend/lib/api/ist.ts` (35+ functions)
- Types: `frontend/types/ist.ts` (40+ type definitions)

### Workflow Engine
- 22 steps across 5 phases, registered via `@register_step("IST", "step_name")`
- DAG-based dependency resolution with asyncio
- SSE streaming for real-time progress
- Phase boundary pausing for user approval
- Step definitions in `IST_WORKFLOW_STEPS` list in `routers/ist.py`

---

## Part 1: Cross-Screen Synthesis

### 1.1 Concept

When two or more independent IST screens are complete, their theses may interact in ways invisible within either screen alone. A "synthesis" ingests the final data from 2+ completed screens, identifies overlapping equities and reinforcing/contradicting theses, re-evaluates tier classifications, and produces a combined investment thesis.

### 1.2 Data Model Changes

#### New Table: `ist_syntheses`

```python
class ISTSynthesis(Base):
    """Cross-screen synthesis combining 2+ completed IST screens."""
    __tablename__ = "ist_syntheses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="PENDING")
    # Status enum: PENDING, INGESTING, ANALYZING, DIALECTIC, SYNTHESIZING, COMPLETED, FAILED
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)

    # Results (JSON columns)
    overlap_matrix = Column(Text, nullable=True)       # JSON: equity overlap across source screens
    thesis_interactions = Column(Text, nullable=True)   # JSON: reinforcing/contradicting thesis pairs
    tier_changes = Column(Text, nullable=True)          # JSON: array of {ticker, sourceScreenId, originalTier, newTier, rationale}
    combined_brief = Column(Text, nullable=True)        # JSON: merged screening brief
    combined_report = Column(Text, nullable=True)       # Combined Investment Thesis Report (markdown)
    report_metadata = Column(Text, nullable=True)       # JSON: pillar_count, equity_count, tier_breakdown
    certification = Column(Text, nullable=True)         # JSON: gate results
    hfrt_handoff = Column(Text, nullable=True)          # JSON: combined Tier 1 candidates

    is_certified = Column(Integer, nullable=False, default=0)
    certified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    workflow_run = relationship("WorkflowRun", backref="ist_synthesis")
    source_links = relationship("ISTSynthesisSource", back_populates="synthesis", cascade="all, delete-orphan")
    # Combined equities stored in ist_synthesis_equities
    equities = relationship("ISTSynthesisEquity", back_populates="synthesis", cascade="all, delete-orphan")
    dialectic_reviews = relationship("ISTSynthesisDialectic", back_populates="synthesis", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'INGESTING', 'ANALYZING', 'DIALECTIC', 'SYNTHESIZING', 'COMPLETED', 'FAILED')",
            name="ck_ist_synthesis_status",
        ),
        Index("ix_ist_syntheses_status", "status", "created_at"),
    )
```

#### New Table: `ist_synthesis_sources`

```python
class ISTSynthesisSource(Base):
    """Link table: which screens are inputs to a synthesis."""
    __tablename__ = "ist_synthesis_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    synthesis_id = Column(Integer, ForeignKey("ist_syntheses.id", ondelete="CASCADE"), nullable=False)
    screen_id = Column(Integer, ForeignKey("ist_screens.id", ondelete="CASCADE"), nullable=False)
    screen_name = Column(Text, nullable=False)  # Denormalized for convenience
    tier1_count = Column(Integer, nullable=False, default=0)
    tier2_count = Column(Integer, nullable=False, default=0)
    tier3_count = Column(Integer, nullable=False, default=0)
    primary_theme = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    synthesis = relationship("ISTSynthesis", back_populates="source_links")
    screen = relationship("ISTScreen")

    __table_args__ = (
        Index("ix_ist_synth_sources_synth", "synthesis_id"),
        Index("ix_ist_synth_sources_screen", "screen_id"),
        Index("ix_ist_synth_sources_unique", "synthesis_id", "screen_id", unique=True),
    )
```

#### New Table: `ist_synthesis_equities`

```python
class ISTSynthesisEquity(Base):
    """Re-tiered equity in a synthesis — tracks tier changes from source screens."""
    __tablename__ = "ist_synthesis_equities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    synthesis_id = Column(Integer, ForeignKey("ist_syntheses.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(Text, nullable=False)
    company_name = Column(Text, nullable=False)

    # Tier change tracking
    original_tier = Column(Integer, nullable=False)  # Best tier from any source screen
    new_tier = Column(Integer, nullable=False)        # Re-evaluated tier after synthesis
    tier_changed = Column(Integer, nullable=False, default=0)  # Boolean: 1 if changed
    tier_change_rationale = Column(Text, nullable=True)

    # Aggregated data from source screens
    source_screen_count = Column(Integer, nullable=False, default=1)  # How many source screens contain this equity
    source_screen_ids = Column(Text, nullable=False)  # JSON array of screen IDs
    combined_scarcity_score = Column(Text, nullable=True)  # JSON: re-evaluated scarcity score
    combined_thesis = Column(Text, nullable=True)  # Combined thesis narrative
    combined_catalyst = Column(Text, nullable=True)
    conviction = Column(Text, nullable=True)  # HIGH/MEDIUM/LOW

    # Market data (latest from source screens)
    price_at_synthesis = Column(Float, nullable=True)
    pe_ratio = Column(Float, nullable=True)
    market_cap = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    synthesis = relationship("ISTSynthesis", back_populates="equities")

    __table_args__ = (
        CheckConstraint("original_tier IN (1, 2, 3)", name="ck_synth_eq_orig_tier"),
        CheckConstraint("new_tier IN (1, 2, 3)", name="ck_synth_eq_new_tier"),
        Index("ix_ist_synth_eq_synth", "synthesis_id", "new_tier"),
        Index("ix_ist_synth_eq_ticker", "ticker"),
        Index("ix_ist_synth_eq_unique", "synthesis_id", "ticker", unique=True),
    )
```

#### New Table: `ist_synthesis_dialectics`

```python
class ISTSynthesisDialectic(Base):
    """Dialectic reviews for a synthesis (same pattern as ist_dialectic_reviews)."""
    __tablename__ = "ist_synthesis_dialectics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    synthesis_id = Column(Integer, ForeignKey("ist_syntheses.id", ondelete="CASCADE"), nullable=False)
    side = Column(Text, nullable=False)  # OPTIMIST, PESSIMIST, SYNTHESIS
    content = Column(Text, nullable=False)  # JSON
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    synthesis = relationship("ISTSynthesis", back_populates="dialectic_reviews")

    __table_args__ = (
        CheckConstraint("side IN ('OPTIMIST', 'PESSIMIST', 'SYNTHESIS')", name="ck_synth_dialectic_side"),
        Index("ix_ist_synth_dialectic_unique", "synthesis_id", "side", unique=True),
    )
```

### 1.3 Synthesis Workflow (10 Steps, 3 Phases)

The synthesis uses the same workflow engine (`@register_step`) but with workflow_type `"IST_SYNTHESIS"` and a shorter step list.

```python
IST_SYNTHESIS_WORKFLOW_STEPS = [
    # Phase S1: Screen Ingestion & Cross-Mapping
    {"step_name": "screen_ingestion", "phase": 1, "phase_name": "Screen Ingestion", "step_order": 1, "depends_on": [], "model": "opus"},
    {"step_name": "overlap_matrix", "phase": 1, "phase_name": "Screen Ingestion", "step_order": 2, "depends_on": ["screen_ingestion"], "model": "opus"},
    {"step_name": "thesis_interactions", "phase": 1, "phase_name": "Screen Ingestion", "step_order": 3, "depends_on": ["overlap_matrix"], "model": "opus"},
    {"step_name": "synthesis_readiness_gate", "phase": 1, "phase_name": "Screen Ingestion", "step_order": 4, "depends_on": ["thesis_interactions"], "model": "none"},
    # Phase S2: Re-Analysis & Re-Tiering
    {"step_name": "combined_bottleneck_analysis", "phase": 2, "phase_name": "Re-Analysis", "step_order": 5, "depends_on": ["synthesis_readiness_gate"], "model": "opus"},
    {"step_name": "cross_screen_effects", "phase": 2, "phase_name": "Re-Analysis", "step_order": 6, "depends_on": ["combined_bottleneck_analysis"], "model": "opus"},
    {"step_name": "re_tiering", "phase": 2, "phase_name": "Re-Analysis", "step_order": 7, "depends_on": ["cross_screen_effects"], "model": "opus"},
    # Phase S3: Dialectic & Final Synthesis
    {"step_name": "synthesis_dialectic_optimist", "phase": 3, "phase_name": "Synthesis", "step_order": 8, "depends_on": ["re_tiering"], "model": "opus"},
    {"step_name": "synthesis_dialectic_pessimist", "phase": 3, "phase_name": "Synthesis", "step_order": 9, "depends_on": ["re_tiering"], "model": "opus"},
    {"step_name": "synthesis_final", "phase": 3, "phase_name": "Synthesis", "step_order": 10, "depends_on": ["synthesis_dialectic_optimist", "synthesis_dialectic_pessimist"], "model": "opus"},
]
```

### 1.4 API Endpoints (under `/api/ist/syntheses`)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/ist/syntheses` | Create synthesis from 2+ screen IDs |
| `GET` | `/api/ist/syntheses` | List all syntheses (paginated, filterable by status) |
| `GET` | `/api/ist/syntheses/{id}` | Get synthesis detail (including overlap matrix, tier changes) |
| `DELETE` | `/api/ist/syntheses/{id}` | Delete synthesis |
| `GET` | `/api/ist/syntheses/{id}/sources` | Get source screens summary |
| `GET` | `/api/ist/syntheses/{id}/overlap` | Get equity overlap matrix |
| `GET` | `/api/ist/syntheses/{id}/interactions` | Get thesis interactions |
| `GET` | `/api/ist/syntheses/{id}/tier-changes` | Get all tier changes with rationale |
| `GET` | `/api/ist/syntheses/{id}/equities` | Get combined re-tiered equity list |
| `GET` | `/api/ist/syntheses/{id}/dialectic/{side}` | Get dialectic review |
| `GET` | `/api/ist/syntheses/{id}/report` | Get combined Investment Thesis Report |
| `GET` | `/api/ist/syntheses/{id}/handoff` | Get combined HFRT handoff |

#### `POST /api/ist/syntheses` Request Schema

```python
class ISTSynthesisCreate(BaseModel):
    name: str = Field(..., max_length=200)
    screen_ids: list[int] = Field(..., alias="screenIds", min_length=2, max_length=10)
    auto_advance: bool = Field(default=False, alias="autoAdvance")
```

Validation on create:
- All screen_ids must exist and have status `COMPLETED`
- All screens must be certified (`is_certified = 1`)
- At least 2 screens required

### 1.5 Backend Service: `backend/app/services/ist/synthesis.py` (NEW)

This is a new service file containing all 10 step handlers registered as `@register_step("IST_SYNTHESIS", "step_name")`.

**Key step implementations:**

**`screen_ingestion`**: Read all source screens' equity_candidates, bottlenecks, effects_chains, claims. Build denormalized data structures for downstream steps. Populate `ist_synthesis_sources` rows.

**`overlap_matrix`**: For each unique ticker across all source screens, record which screens it appears in and at what tier. Store as JSON in `ist_syntheses.overlap_matrix`. Structure:
```json
[
  {"ticker": "VRT", "companyName": "Vertiv", "appearances": [
    {"screenId": 1, "screenName": "Energy Scarcity", "tier": 2, "scarcityScore": 3.8, "bottleneck": "Cooling Infrastructure"},
    {"screenId": 3, "screenName": "AI Agent Adoption", "tier": 3, "scarcityScore": 3.2, "bottleneck": "AI Compute Scaling"}
  ]}
]
```

**`thesis_interactions`**: Use Claude to analyze how thesis A from Screen 1 interacts with thesis B from Screen 2. Classification: `reinforcing`, `contradicting`, `orthogonal`. Store as JSON in `ist_syntheses.thesis_interactions`.

**`synthesis_readiness_gate`**: Validate at least one of:
- 1+ equity appears in 2+ source screens, OR
- 1+ thesis interaction classified as `reinforcing`
If neither: fail gate with message "No meaningful intersection found."

**`combined_bottleneck_analysis`**: Use Claude to build a unified bottleneck cascade from all source screens' bottleneck maps. Identify NEW bottleneck dependencies that only emerge from the combination.

**`cross_screen_effects`**: Use Claude to map cross-screen effects chains. Screen A's 3rd-order effect may feed into Screen B's 1st-order — creating reinforcing loops.

**`re_tiering`**: For each equity in the combined list, use Claude + deterministic rules to re-evaluate tier:
- Equity in 2+ screens with reinforcing theses → tier upgrade candidate
- Equity contradicted across screens → tier downgrade candidate
- Multi-source validation gained from combined screens → may satisfy Tier 1 criteria
- Write all results to `ist_synthesis_equities` table
- Write tier change summary to `ist_syntheses.tier_changes` JSON column

**`synthesis_dialectic_optimist/pessimist`**: Same pattern as existing IST dialectic but operating on the combined screen data. Write to `ist_synthesis_dialectics` table.

**`synthesis_final`**: Produce combined report (markdown), certification, HFRT handoff. Write to `ist_syntheses` JSON columns.

### 1.6 Frontend Changes

#### New Page: `frontend/app/screens/syntheses/page.tsx`
- List all syntheses with source screen names, tier change count, status
- "New Synthesis" button

#### New Page: `frontend/app/screens/syntheses/new/page.tsx`
- Multi-select from completed screens (checkboxes)
- Show preview of equity overlap before creating
- Name input, auto_advance toggle
- Minimum 2 screens required

#### New Page: `frontend/app/screens/syntheses/[id]/page.tsx`
- Workflow progress bar (3 phases instead of 5)
- Tabs: Report, Overlap Matrix, Thesis Interactions, Tier Changes, Equities, Dialectic, Handoff
- Real-time SSE updates (same pattern as screen detail page)

#### New Components: `frontend/components/ist/synthesis/`

| Component | Purpose |
|-----------|---------|
| `OverlapMatrix.tsx` | Visual matrix showing which equities appear in which screens, with tier-by-screen color coding |
| `ThesisInteractions.tsx` | Card-based display of reinforcing/contradicting/orthogonal thesis pairs |
| `TierChanges.tsx` | Table of all tier changes with before/after comparison and rationale. Upgrades in green, downgrades in red |
| `SynthesisEquities.tsx` | Combined equity table with source screen badges and combined scarcity scores |
| `SynthesisReport.tsx` | Combined Investment Thesis Report (reuse `InvestmentThesisReport.tsx` pattern) |
| `SynthesisHandoff.tsx` | Combined HFRT handoff panel (reuse `HandoffPanel.tsx` pattern) |
| `ScreenSelector.tsx` | Multi-select component for picking source screens (used on create page) |

#### Updated Components

| Component | Change |
|-----------|--------|
| `frontend/app/screens/page.tsx` | Add "Syntheses" tab or link to the syntheses list page |

#### New API Client Functions: `frontend/lib/api/ist-synthesis.ts` (NEW)

```typescript
export async function createSynthesis(data: { name: string; screenIds: number[]; autoAdvance?: boolean }): Promise<...>
export async function listSyntheses(params?: { status?: string; page?: number; pageSize?: number }): Promise<...>
export async function getSynthesis(id: number): Promise<...>
export async function deleteSynthesis(id: number): Promise<void>
export async function getSynthesisSources(id: number): Promise<...>
export async function getSynthesisOverlap(id: number): Promise<...>
export async function getSynthesisInteractions(id: number): Promise<...>
export async function getSynthesisTierChanges(id: number): Promise<...>
export async function getSynthesisEquities(id: number): Promise<...>
export async function getSynthesisDialectic(id: number, side: string): Promise<...>
export async function getSynthesisReport(id: number): Promise<...>
export async function getSynthesisHandoff(id: number): Promise<...>
```

#### New Types: `frontend/types/ist-synthesis.ts` (NEW)

```typescript
export type SynthesisStatus = 'PENDING' | 'INGESTING' | 'ANALYZING' | 'DIALECTIC' | 'SYNTHESIZING' | 'COMPLETED' | 'FAILED';

export interface SynthesisListItem { id: number; name: string; status: SynthesisStatus; sourceScreenCount: number; tierChangeCount: number; createdAt: string; }
export interface SynthesisDetail { id: number; name: string; status: SynthesisStatus; workflowRunId: number; overlapMatrix: OverlapEntry[]; thesisInteractions: ThesisInteraction[]; tierChanges: TierChange[]; ... }
export interface OverlapEntry { ticker: string; companyName: string; appearances: Array<{ screenId: number; screenName: string; tier: number; scarcityScore: number; bottleneck: string }>; }
export interface ThesisInteraction { screenAId: number; screenAName: string; thesisA: string; screenBId: number; screenBName: string; thesisB: string; interactionType: 'reinforcing' | 'contradicting' | 'orthogonal'; impact: string; }
export interface TierChange { ticker: string; companyName: string; originalTier: number; newTier: number; direction: 'upgrade' | 'downgrade' | 'unchanged'; rationale: string; sourceScreenIds: number[]; }
export interface SynthesisEquity { id: number; ticker: string; companyName: string; originalTier: number; newTier: number; tierChanged: boolean; sourceScreenCount: number; combinedScarcityScore: ScarcityScore; combinedThesis: string; conviction: string; priceAtSynthesis: number | null; peRatio: number | null; marketCap: number | null; }
```

---

## Part 2: Screen Refresh

### 2.1 Concept

A completed screen can be updated with new content. The existing screen's analysis serves as a baseline. Only new content is extracted, impacted steps are re-run, and the screen is re-certified.

### 2.2 Data Model Changes

#### New Table: `ist_screen_refreshes`

```python
class ISTScreenRefresh(Base):
    """Tracks each refresh operation on a completed screen."""
    __tablename__ = "ist_screen_refreshes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    screen_id = Column(Integer, ForeignKey("ist_screens.id", ondelete="CASCADE"), nullable=False)
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)

    # New content
    new_content = Column(Text, nullable=False)
    new_content_type = Column(Text, nullable=False, default="text")

    # Delta results
    new_claims_count = Column(Integer, nullable=False, default=0)
    new_claims = Column(Text, nullable=True)  # JSON: array of extracted claims from new content
    new_source_bias = Column(Text, nullable=True)  # JSON: bias assessment for new source

    # Impact assessment
    impact_assessment = Column(Text, nullable=True)  # JSON: which steps need re-run
    steps_rerun = Column(Text, nullable=True)  # JSON: list of step names that were re-executed

    # Tier changes from this refresh
    tier_changes = Column(Text, nullable=True)  # JSON: array of {ticker, oldTier, newTier, rationale}
    tier_change_count = Column(Integer, nullable=False, default=0)

    # Status
    status = Column(Text, nullable=False, default="PENDING")
    # PENDING, EXTRACTING, ASSESSING, RE_ANALYZING, RE_SYNTHESIZING, COMPLETED, FAILED

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    screen = relationship("ISTScreen", backref="refreshes")
    workflow_run = relationship("WorkflowRun", backref="ist_refresh")

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'EXTRACTING', 'ASSESSING', 'RE_ANALYZING', 'RE_SYNTHESIZING', 'COMPLETED', 'FAILED')",
            name="ck_ist_refresh_status",
        ),
        Index("ix_ist_refreshes_screen", "screen_id"),
        Index("ix_ist_refreshes_status", "status"),
    )
```

#### Modification to `ist_screens` table

Add two columns via migration:

```python
# Track refresh history
refresh_count = Column(Integer, nullable=False, default=0)
last_refreshed_at = Column(DateTime, nullable=True)
```

#### Modification to `ist_claims` table

Add one column via migration:

```python
# Tag claims from refresh operations
source_refresh_id = Column(Integer, ForeignKey("ist_screen_refreshes.id", ondelete="SET NULL"), nullable=True)
```

Claims from the original screen have `source_refresh_id = NULL`. Claims added during a refresh have `source_refresh_id` set to the refresh record's ID. This enables distinguishing original vs. refreshed claims.

### 2.3 Refresh Workflow (8 Steps, 3 Phases)

Registered as workflow_type `"IST_REFRESH"`.

```python
IST_REFRESH_WORKFLOW_STEPS = [
    # Phase R1: Delta Content Extraction
    {"step_name": "delta_extraction", "phase": 1, "phase_name": "Delta Extraction", "step_order": 1, "depends_on": [], "model": "opus"},
    {"step_name": "delta_bias_assessment", "phase": 1, "phase_name": "Delta Extraction", "step_order": 2, "depends_on": ["delta_extraction"], "model": "sonnet"},
    {"step_name": "delta_sufficiency_gate", "phase": 1, "phase_name": "Delta Extraction", "step_order": 3, "depends_on": ["delta_bias_assessment"], "model": "none"},
    # Phase R2: Impact Assessment & Selective Re-Analysis
    {"step_name": "impact_assessment", "phase": 2, "phase_name": "Re-Analysis", "step_order": 4, "depends_on": ["delta_sufficiency_gate"], "model": "opus"},
    {"step_name": "selective_reanalysis", "phase": 2, "phase_name": "Re-Analysis", "step_order": 5, "depends_on": ["impact_assessment"], "model": "opus"},
    {"step_name": "refresh_invariant_check", "phase": 2, "phase_name": "Re-Analysis", "step_order": 6, "depends_on": ["selective_reanalysis"], "model": "none"},
    # Phase R3: Conditional Re-Synthesis
    {"step_name": "conditional_resynthesis", "phase": 3, "phase_name": "Re-Synthesis", "step_order": 7, "depends_on": ["refresh_invariant_check"], "model": "opus"},
    {"step_name": "refresh_certification", "phase": 3, "phase_name": "Re-Synthesis", "step_order": 8, "depends_on": ["conditional_resynthesis"], "model": "sonnet"},
]
```

### 2.4 Step Implementations

**`delta_extraction`**: Same Claude prompt pattern as existing `content_extraction`, but:
1. Reads existing claims from the screen first (passed as context so Claude doesn't re-extract known claims)
2. Extracts only NEW claims from the new content
3. Inserts new `ISTClaim` rows with `source_refresh_id` set to the refresh ID
4. Updates `ist_screen_refreshes.new_claims_count` and `new_claims` JSON

**`delta_bias_assessment`**: Same as existing `source_bias_assessment` but only for the new content source. Writes to `ist_screen_refreshes.new_source_bias`.

**`delta_sufficiency_gate`**: Checks if 1+ new investable claim was extracted with a quantitative anchor. If zero: fail with "New content adds no investable claims."

**`impact_assessment`**: Uses Claude to assess which downstream artifacts are affected by the new claims:
- New bottleneck identified → flag bottleneck_mapping for re-run
- Existing bottleneck timeline changed → flag bottleneck_mapping for re-run
- New equity candidate → flag equity_scanning for re-run
- Existing equity thesis strengthened/weakened → flag tier_classification for re-run
- New causal chain → flag effects_analysis for re-run
- Contradiction with existing thesis → flag external_validation for re-run
- Purely corroborating → no re-run needed

Stores impact assessment as JSON in `ist_screen_refreshes.impact_assessment`:
```json
{
    "bottleneck_mapping": {"needed": true, "reason": "New nuclear policy bottleneck identified"},
    "demand_modeling": {"needed": true, "reason": "Updated demand multiplier from new data"},
    "external_validation": {"needed": false, "reason": null},
    "equity_scanning": {"needed": true, "reason": "New equity candidates from nuclear thesis"},
    "tier_classification": {"needed": true, "reason": "Existing candidates may re-tier with new evidence"},
    "effects_analysis": {"needed": false, "reason": null},
    "dialectic": {"needed": true, "reason": "Tier changes detected — full re-dialectic required"}
}
```

**`selective_reanalysis`**: Re-runs ONLY the flagged steps. For each flagged step:
1. Calls the EXISTING step handler function (e.g., `handle_bottleneck_mapping`) but with a `refresh_context` parameter that includes both original + new claims
2. The existing handlers UPDATE the screen's data in-place (delete old rows, insert updated rows — same pattern as the existing `rerun_screen` endpoint)
3. Records which steps were re-run in `ist_screen_refreshes.steps_rerun`

**Important implementation detail:** The selective re-analysis reuses the existing service functions (`handle_bottleneck_mapping`, `handle_equity_scanning`, etc.) rather than duplicating them. It calls them with the full claim set (original + delta) so they produce updated results. This is the same behavior as the existing "rerun" endpoint, but targeted to specific steps.

**`refresh_invariant_check`**: Runs the same invariant check as the standard pipeline (INV-1 through INV-8) on the updated screen data.

**`conditional_resynthesis`**: If the impact assessment flagged `tier_classification` or `equity_scanning` as needing re-run (i.e., tier changes occurred), re-run the full dialectic + final synthesis (master_screen, rotation_strategy, catalyst_calendar, stress_tests, report_generation). If NOT, only update the report's metadata to note the refresh. Calls the EXISTING service functions.

**`refresh_certification`**: Re-certify the screen. Updates `ist_screens.is_certified`, `certified_at`, `certification` JSON. Updates `ist_screens.refresh_count` and `last_refreshed_at`.

### 2.5 API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/ist/screens/{id}/refresh` | Start a refresh with new content |
| `GET` | `/api/ist/screens/{id}/refreshes` | List all refresh operations for a screen |
| `GET` | `/api/ist/screens/{id}/refreshes/{refreshId}` | Get refresh detail (delta claims, impact, tier changes) |
| `GET` | `/api/ist/screens/{id}/refreshes/{refreshId}/claims` | Get only the delta claims from a specific refresh |

#### `POST /api/ist/screens/{id}/refresh` Request Schema

```python
class ISTScreenRefreshCreate(BaseModel):
    content: str = Field(..., min_length=100, max_length=512000)
    content_type: Optional[str] = Field(default="text", alias="contentType")
    auto_advance: bool = Field(default=False, alias="autoAdvance")
```

Validation on create:
- Screen must exist and have status `COMPLETED`
- Screen must be certified
- Warning (non-blocking) if `refresh_count >= 3`: include `"warning": "This screen has been refreshed 3+ times. Consider creating a fresh screen."` in response

### 2.6 Backend Service: `backend/app/services/ist/refresh.py` (NEW)

Contains 8 step handlers registered as `@register_step("IST_REFRESH", "step_name")`.

### 2.7 Frontend Changes

#### Modified Page: `frontend/app/screens/[id]/page.tsx`
- Add "Refresh" button in the screen actions bar (only visible when status is `COMPLETED`)
- Opens a modal or drawer with a content input area (text, content type selector)
- Shows refresh count badge if screen has been refreshed before
- After submission, shows refresh workflow progress

#### New Components

| Component | Purpose |
|-----------|---------|
| `RefreshModal.tsx` | Modal with content textarea + content type selector + submit button. Shows warning if 3+ refreshes. |
| `RefreshHistory.tsx` | Timeline/list of all refreshes for a screen, showing date, new claims count, tier changes, re-run scope |
| `RefreshDelta.tsx` | Side-by-side view of new claims added by a refresh, with impact assessment visualization |

#### Modified Components

| Component | Change |
|-----------|--------|
| `ClaimsTable.tsx` | Add optional "Source" column showing "Original" vs "Refresh #N" badge per claim |

#### New API Client Functions (add to `frontend/lib/api/ist.ts`)

```typescript
export async function refreshScreen(screenId: number, data: { content: string; contentType?: string; autoAdvance?: boolean }): Promise<...>
export async function listRefreshes(screenId: number): Promise<...>
export async function getRefresh(screenId: number, refreshId: number): Promise<...>
export async function getRefreshClaims(screenId: number, refreshId: number): Promise<...>
```

#### New Types (add to `frontend/types/ist.ts`)

```typescript
export type RefreshStatus = 'PENDING' | 'EXTRACTING' | 'ASSESSING' | 'RE_ANALYZING' | 'RE_SYNTHESIZING' | 'COMPLETED' | 'FAILED';

export interface ScreenRefreshListItem { id: number; status: RefreshStatus; newClaimsCount: number; tierChangeCount: number; stepsRerun: string[]; createdAt: string; completedAt: string | null; }
export interface ScreenRefreshDetail { id: number; status: RefreshStatus; newContent: string; newContentType: string; newClaimsCount: number; newClaims: ISTClaim[]; newSourceBias: { rating: string; notes: string } | null; impactAssessment: Record<string, { needed: boolean; reason: string | null }>; stepsRerun: string[]; tierChanges: TierChange[]; tierChangeCount: number; createdAt: string; completedAt: string | null; }
```

---

## Part 3: Database Migration

### Migration File: `backend/alembic/versions/015_ist_synthesis_and_refresh.py`

Single migration that creates all new tables and adds new columns:

**New tables:**
1. `ist_syntheses`
2. `ist_synthesis_sources`
3. `ist_synthesis_equities`
4. `ist_synthesis_dialectics`
5. `ist_screen_refreshes`

**Column additions:**
1. `ist_screens.refresh_count` (Integer, default 0)
2. `ist_screens.last_refreshed_at` (DateTime, nullable)
3. `ist_claims.source_refresh_id` (Integer FK → ist_screen_refreshes.id, nullable)

**Downgrade:** Drop all 5 tables and 3 columns.

---

## Part 4: File Inventory

### Files to CREATE

| # | Path | Purpose |
|---|------|---------|
| 1 | `backend/alembic/versions/015_ist_synthesis_and_refresh.py` | Migration for 5 new tables + 3 new columns |
| 2 | `backend/app/models/ist_synthesis.py` | 4 new SQLAlchemy models (ISTSynthesis, ISTSynthesisSource, ISTSynthesisEquity, ISTSynthesisDialectic) |
| 3 | `backend/app/models/ist_refresh.py` | 1 new model (ISTScreenRefresh) |
| 4 | `backend/app/services/ist/synthesis.py` | 10 synthesis step handlers |
| 5 | `backend/app/services/ist/refresh.py` | 8 refresh step handlers |
| 6 | `backend/app/routers/ist_synthesis.py` | 12 synthesis API endpoints |
| 7 | `backend/app/schemas/ist_synthesis.py` | Request/response Pydantic schemas for synthesis |
| 8 | `frontend/app/screens/syntheses/page.tsx` | Synthesis list page |
| 9 | `frontend/app/screens/syntheses/new/page.tsx` | Create synthesis page |
| 10 | `frontend/app/screens/syntheses/[id]/page.tsx` | Synthesis detail page |
| 11 | `frontend/components/ist/synthesis/OverlapMatrix.tsx` | Equity overlap visualization |
| 12 | `frontend/components/ist/synthesis/ThesisInteractions.tsx` | Thesis interaction cards |
| 13 | `frontend/components/ist/synthesis/TierChanges.tsx` | Tier change comparison table |
| 14 | `frontend/components/ist/synthesis/SynthesisEquities.tsx` | Combined equity table |
| 15 | `frontend/components/ist/synthesis/SynthesisReport.tsx` | Combined report display |
| 16 | `frontend/components/ist/synthesis/SynthesisHandoff.tsx` | Combined HFRT handoff |
| 17 | `frontend/components/ist/synthesis/ScreenSelector.tsx` | Multi-select for source screens |
| 18 | `frontend/components/ist/RefreshModal.tsx` | Refresh content input modal |
| 19 | `frontend/components/ist/RefreshHistory.tsx` | Refresh history timeline |
| 20 | `frontend/components/ist/RefreshDelta.tsx` | Delta claims and impact view |
| 21 | `frontend/lib/api/ist-synthesis.ts` | Synthesis API client functions |
| 22 | `frontend/types/ist-synthesis.ts` | Synthesis TypeScript types |

### Files to MODIFY

| # | Path | Changes |
|---|------|---------|
| 1 | `backend/app/models/__init__.py` | Import new models so Alembic sees them |
| 2 | `backend/app/models/ist.py` | Add `refresh_count`, `last_refreshed_at` to ISTScreen; add `source_refresh_id` to ISTClaim; add relationship `refreshes` to ISTScreen |
| 3 | `backend/app/routers/ist.py` | Add 4 refresh endpoints (POST refresh, GET refreshes list, GET refresh detail, GET refresh claims); import new schemas |
| 4 | `backend/app/schemas/ist.py` | Add ISTScreenRefreshCreate, ScreenRefreshListItem, ScreenRefreshDetail schemas; update ISTScreenListItem/DetailResponse to include refreshCount |
| 5 | `backend/app/main.py` | Register the new `ist_synthesis` router |
| 6 | `frontend/app/screens/page.tsx` | Add navigation link/tab to Syntheses list |
| 7 | `frontend/app/screens/[id]/page.tsx` | Add Refresh button (COMPLETED screens only), RefreshModal integration, RefreshHistory tab |
| 8 | `frontend/components/ist/ClaimsTable.tsx` | Add optional "Source" column (Original vs Refresh #N badge) |
| 9 | `frontend/lib/api/ist.ts` | Add 4 refresh API client functions |
| 10 | `frontend/types/ist.ts` | Add RefreshStatus, ScreenRefreshListItem, ScreenRefreshDetail types; update ISTScreenListItem with refreshCount field |

### Files NOT to Modify

| File | Reason |
|------|--------|
| Existing service files (content_extraction.py, thematic_analysis.py, etc.) | Refresh calls existing handlers; does not modify them |
| `backend/app/services/workflow_engine.py` | Already supports multiple workflow types via the registry pattern |
| Existing IST components (except ClaimsTable.tsx) | Synthesis has its own components; refresh adds minimal UI to existing pages |

---

## Part 5: Implementation Order

### Phase A: Database + Models (do first)
1. Create migration `015_ist_synthesis_and_refresh.py`
2. Create `backend/app/models/ist_synthesis.py` and `backend/app/models/ist_refresh.py`
3. Update `backend/app/models/ist.py` (add columns + relationship)
4. Update `backend/app/models/__init__.py` (imports)
5. Run migration: `alembic upgrade head`

### Phase B: Screen Refresh Backend (simpler, do second)
6. Create `backend/app/schemas/ist.py` additions (refresh schemas)
7. Create `backend/app/services/ist/refresh.py` (8 step handlers)
8. Add refresh endpoints to `backend/app/routers/ist.py`

### Phase C: Screen Refresh Frontend
9. Create `RefreshModal.tsx`, `RefreshHistory.tsx`, `RefreshDelta.tsx`
10. Update `frontend/app/screens/[id]/page.tsx` (Refresh button + modal + history tab)
11. Update `frontend/components/ist/ClaimsTable.tsx` (source badge column)
12. Add refresh API functions and types to existing files

### Phase D: Cross-Screen Synthesis Backend
13. Create `backend/app/schemas/ist_synthesis.py`
14. Create `backend/app/services/ist/synthesis.py` (10 step handlers)
15. Create `backend/app/routers/ist_synthesis.py` (12 endpoints)
16. Register router in `backend/app/main.py`

### Phase E: Cross-Screen Synthesis Frontend
17. Create `frontend/types/ist-synthesis.ts`
18. Create `frontend/lib/api/ist-synthesis.ts`
19. Create all 7 synthesis components in `frontend/components/ist/synthesis/`
20. Create 3 synthesis pages (`page.tsx`, `new/page.tsx`, `[id]/page.tsx`)
21. Update `frontend/app/screens/page.tsx` (add Syntheses navigation link)

### Phase F: Testing & Verification
22. Verify migration runs cleanly
23. Test refresh endpoint with a completed screen
24. Test synthesis endpoint with 2+ completed screens
25. Verify SSE streaming works for both new workflow types
26. Verify existing IST functionality is unaffected

---

## Part 6: Design Decisions & Rationale

### Why separate tables for synthesis (not reusing ist_screens)?
Syntheses are fundamentally different from screens — they don't have raw_content, they have source screens. Overloading `ist_screens` with a "mode" column would pollute the existing data model and make queries more complex. Separate tables keep the existing IST feature clean.

### Why in-place refresh (not creating a new screen)?
The user explicitly asked to "update a previously used screen." A refresh preserves the screen's identity, history, and URL. It's conceptually "the same analysis, evolved with new data." Creating a new screen would lose that continuity.

### Why reuse existing step handlers for refresh?
The existing handlers (`handle_bottleneck_mapping`, etc.) already know how to analyze claims and produce bottlenecks/equities. Refresh feeds them the combined claim set (original + delta), and they produce updated results. This avoids duplicating complex Claude-calling logic.

### Why a readiness gate for synthesis?
If two screens share zero equity overlap AND zero thesis interactions, combining them produces no new insight. The gate prevents wasted API calls and user confusion.

---

**End of Implementation Plan**

---

## CODEX Critique and Recommendations

> **Addendum (Non-Normative):** This section is an implementation critique intended for review.  
> It does not alter the original plan structure, scope, or sequencing above.

### A. Critical integration gaps to resolve before execution

1. **Workflow type constraints must be expanded first.**  
   The plan introduces `IST_SYNTHESIS` and `IST_REFRESH`, but current workflow constraints and validators only allow `IST` and `HFRT`.  
   **Recommendation:** Add compatibility updates up front in migration/model/schema/router validation for workflow type handling before any new runs are created.

2. **Refresh step reuse conflicts with current step handler contract.**  
   Existing IST handlers accept only `workflow_run_id` and resolve one screen from `ISTScreen.workflow_run_id`.  
   **Recommendation:** Add an explicit refresh context resolution layer (or wrapper handlers) so refresh runs can target an existing screen safely without changing baseline semantics.

3. **Selective re-analysis must define deterministic write strategy.**  
   Current handlers primarily append/insert and some target tables enforce uniqueness by `(screen_id, ticker)` or `(screen_id, side)`.  
   **Recommendation:** For each rerun step, define one of two explicit policies:  
   `replace_artifact` (delete/rebuild step-owned rows) or `merge_artifact` (upsert by deterministic key).  
   This should be specified step-by-step in the refresh design.

### B. High-priority design clarifications

1. **Screen detail page workflow binding is currently single-run.**  
   Existing UI binds controls/progress to `screen.workflowRunId`. Refresh introduces a separate run ID.  
   **Recommendation:** Add a clear "active run selection" rule for the screen detail page (base run vs latest refresh run), including SSE subscription behavior.

2. **Status semantics should be separated for screen lifecycle vs refresh lifecycle.**  
   Reusing existing handlers may mutate `ist_screens.status` during refresh processing.  
   **Recommendation:** Define whether refresh should mutate screen status directly or remain isolated to `ist_screen_refreshes.status`, with a final reconciliation step.

3. **Scope statement should be tightened for consistency.**  
   The plan states existing IST structures remain untouched, but later lists targeted core file changes.  
   **Recommendation:** Reword the overview to clarify: "No behavioral regressions to existing flows; targeted additive modifications are required in listed files."

### C. Implementation hardening recommendations

1. **Add explicit guardrails for synthesis input quality.**  
   Beyond completion/certification checks, require minimum source diversity metadata (e.g., at least two distinct primary themes or explicit overlap rationale) to reduce low-signal syntheses.

2. **Add idempotency keys for create endpoints.**  
   For `POST /api/ist/syntheses` and `POST /api/ist/screens/{id}/refresh`, idempotency support prevents duplicate runs from repeated UI submits.

3. **Define artifact ownership matrix for refresh.**  
   Document which tables are authoritative outputs of each rerunnable step to prevent hidden coupling and accidental stale data.

4. **Testing strategy should include regression gates.**  
   Add mandatory regression checks for existing IST screen creation, rerun, report retrieval, certification, and HFRT handoff after introducing synthesis/refresh workflows.

### D. Suggested pre-implementation checklist

1. Confirm workflow type compatibility changes are merged and tested first.
2. Finalize refresh context contract (wrapper vs direct handler extension).
3. Finalize per-step replace/merge data policy for selective re-analysis.
4. Finalize UI run-selection behavior on `/screens/[id]`.
5. Add integration tests for `IST`, `IST_REFRESH`, and `IST_SYNTHESIS` coexistence.

---

## CC Resolution of CODEX Critique

> **Author:** Claude Code (CC)
> **Date:** 2026-02-21
> **Status:** All points addressed. Plan amendments below are NORMATIVE — they override the original plan where they conflict.

Codex's critique is well-grounded. Every point A1-A3, B1-B3, C1-C4, and D1-D5 is addressed below with concrete design decisions. These resolutions amend the original plan.

---

### Resolution A1: Workflow Type Constraint Expansion

**Codex is correct.** The `workflow_runs` table has a CHECK constraint:
```sql
CHECK (workflow_type IN ('IST', 'HFRT'))
```
This will reject any row with `IST_SYNTHESIS` or `IST_REFRESH`.

**Resolution:** The migration `015_ist_synthesis_and_refresh.py` MUST include a constraint replacement as its FIRST operation:

```python
# Step 0: Expand workflow_type CHECK constraint BEFORE creating any new tables
op.drop_constraint("ck_workflow_type", "workflow_runs", type_="check")
op.create_check_constraint(
    "ck_workflow_type",
    "workflow_runs",
    "workflow_type IN ('IST', 'HFRT', 'IST_SYNTHESIS', 'IST_REFRESH')",
)
```

**Downgrade** must restore the original constraint (after verifying no IST_SYNTHESIS/IST_REFRESH rows exist).

This is a prerequisite for everything else. Add to Phase A (Database + Models) as step 0.

---

### Resolution A2: Refresh Step Reuse — Handler Contract

**Codex is correct.** Every existing IST handler follows this contract:
```python
@register_step("IST", "content_extraction")
async def handle_content_extraction(workflow_run_id: int) -> dict | None:
    screen = db.query(ISTScreen).filter(ISTScreen.workflow_run_id == workflow_run_id).first()
```

The handler resolves the screen via `ISTScreen.workflow_run_id`. A refresh workflow run has a DIFFERENT `workflow_run_id` than the original screen's run — so calling the existing handler directly would fail to find the screen.

**Resolution: Wrapper handlers, not direct reuse.** The refresh service (`refresh.py`) will implement its own step handlers registered as `@register_step("IST_REFRESH", ...)`. These wrappers will:

1. Resolve the screen via `ISTScreenRefresh.workflow_run_id → refresh.screen_id → ISTScreen`
2. Prepare the combined context (original claims + delta claims)
3. Call the CORE LOGIC functions extracted from the existing handlers (not the registered step functions themselves)

This means a minor refactor of the existing service files: extract the core analysis logic into standalone functions that accept a `screen` object + claims list, separate from the `@register_step` wrapper that does the `workflow_run_id → screen` lookup. For example:

```python
# In thematic_analysis.py — extract core logic:
async def _run_bottleneck_mapping(screen: ISTScreen, claims: list[ISTClaim], db: Session) -> list[ISTBottleneck]:
    """Core bottleneck mapping logic — callable from both IST and IST_REFRESH handlers."""
    ...

# Existing handler becomes a thin wrapper:
@register_step("IST", "bottleneck_mapping")
async def handle_bottleneck_mapping(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    screen = db.query(ISTScreen).filter(ISTScreen.workflow_run_id == workflow_run_id).first()
    claims = db.query(ISTClaim).filter(ISTClaim.screen_id == screen.id).all()
    return await _run_bottleneck_mapping(screen, claims, db)
```

Then the refresh handler calls the same `_run_bottleneck_mapping()` with the same screen but the combined claim set.

**Scope of refactor:** Extract `_run_*` functions from these 5 service files:
- `content_extraction.py` → `_run_content_extraction`, `_run_source_bias`
- `thematic_analysis.py` → `_run_bottleneck_mapping`, `_run_demand_modeling`, `_run_external_validation`
- `equity_identification.py` → `_run_equity_scanning`, `_run_tier_classification`, `_run_effects_analysis`
- `dialectic.py` → `_run_dialectic_optimist`, `_run_dialectic_pessimist`, `_run_dialectic_synthesis`
- `final_synthesis.py` → `_run_master_screen`, `_run_rotation_strategy`, `_run_catalyst_calendar`, `_run_stress_tests`, `_run_report_generation`

Each existing `@register_step` handler becomes a 5-line wrapper that resolves the screen then calls the extracted function. This is a safe refactor — it changes no behavior, only code organization.

**Update to File Inventory:** Add these 5 existing service files to the MODIFY list with note: "Extract core logic into `_run_*` functions; existing handlers become thin wrappers."

---

### Resolution A3: Per-Step Write Strategy for Selective Re-Analysis

**Codex is correct.** The plan must define exactly how each step handles existing data during refresh.

**Resolution: `replace_artifact` for all rerunnable steps.** This matches the existing `rerun_screen` pattern (lines 312-324 of `ist.py`) which deletes all child rows before rebuilding. For refresh, only step-owned rows are deleted before the step re-runs:

| Step | Tables Owned | Write Strategy | Delete Before Re-Run |
|------|-------------|---------------|---------------------|
| `bottleneck_mapping` | `ist_bottlenecks` | `replace_artifact` | `DELETE FROM ist_bottlenecks WHERE screen_id = ?` (cascades to demand_models, equity_candidate bottleneck FKs set NULL) |
| `demand_modeling` | `ist_demand_models` | `replace_artifact` | `DELETE FROM ist_demand_models WHERE screen_id = ?` |
| `external_validation` | `ist_validations` | `replace_artifact` | `DELETE FROM ist_validations WHERE screen_id = ?` |
| `equity_scanning` | `ist_equity_candidates` | `replace_artifact` | `DELETE FROM ist_equity_candidates WHERE screen_id = ?` (cascades to effects_chains FK set NULL) |
| `tier_classification` | (updates `ist_equity_candidates.tier`) | `replace_artifact` | Re-evaluates tier on all existing candidates |
| `effects_analysis` | `ist_effects_chains` | `replace_artifact` | `DELETE FROM ist_effects_chains WHERE screen_id = ?` |
| `dialectic_*` | `ist_dialectic_reviews` | `replace_artifact` | `DELETE FROM ist_dialectic_reviews WHERE screen_id = ?` |
| `master_screen` | `ist_master_screens` | `replace_artifact` | `DELETE FROM ist_master_screens WHERE screen_id = ?` |
| `rotation_strategy` | `ist_rotation_strategies` | `replace_artifact` | Same pattern |
| `catalyst_calendar` | `ist_catalyst_calendars` | `replace_artifact` | Same pattern |
| `stress_tests` | `ist_stress_tests` | `replace_artifact` | Same pattern |
| `report_generation` | `ist_reports` | `replace_artifact` | Same pattern |

**Claims are NOT deleted during refresh** — original claims are preserved, delta claims are appended with `source_refresh_id` set. The combined claim set is passed to downstream steps.

**Dependency cascade:** When `bottleneck_mapping` is re-run, `demand_modeling`, `equity_scanning`, `tier_classification`, and `effects_analysis` must also be re-run (they depend on bottleneck data). The `impact_assessment` step in the refresh workflow must enforce this cascade — if bottleneck_mapping is flagged, all downstream steps are automatically flagged too.

---

### Resolution B1: Screen Detail Page — Active Run Selection

**Codex is correct.** The screen detail page binds workflow controls and SSE to `screen.workflowRunId`, which is the ORIGINAL workflow run. A refresh creates a SEPARATE workflow run.

**Resolution:**

1. **`ist_screens` gets a new column: `active_workflow_run_id`** (nullable Integer FK). Defaults to the original `workflow_run_id`. During a refresh, this is updated to point to the refresh's workflow_run_id. On refresh completion, it reverts to the original `workflow_run_id`.

2. **The screen detail page** uses `active_workflow_run_id` (falling back to `workflow_run_id` if null) for:
   - SSE subscription
   - Workflow progress bar
   - Pause/Resume/Cancel controls

3. **A "Refresh in Progress" banner** appears at the top of the screen detail page when `active_workflow_run_id != workflow_run_id`, showing: "Refreshing with new content... [progress] [Cancel]"

4. **After refresh completes**, `active_workflow_run_id` resets to the original `workflow_run_id`. The refresh history is accessible via a "Refresh History" tab.

**Update to migration:** Add `active_workflow_run_id` column to `ist_screens`.

---

### Resolution B2: Screen Status During Refresh

**Codex is correct.** If refresh handlers mutate `ist_screens.status`, a COMPLETED screen would temporarily show as EXTRACTING/ANALYZING, confusing the user.

**Resolution: Refresh lifecycle is isolated to `ist_screen_refreshes.status`.** The parent `ist_screens.status` remains `COMPLETED` throughout the refresh. This means:

1. Refresh step handlers do NOT call `screen.status = "EXTRACTING"` etc. They update `refresh.status` instead.
2. The `ist_screen_refreshes.status` column tracks: `PENDING → EXTRACTING → ASSESSING → RE_ANALYZING → RE_SYNTHESIZING → COMPLETED`
3. The screen list page shows a "Refreshing" badge NEXT TO the "Completed" badge (not replacing it) when a refresh is in progress.
4. On refresh failure: `ist_screen_refreshes.status = FAILED`, parent screen remains `COMPLETED` with all original data intact.
5. On refresh completion: `ist_screen_refreshes.status = COMPLETED`, parent screen remains `COMPLETED` (with updated child data).

This is a key invariant: **refresh never breaks a completed screen**. If a refresh fails, you still have the pre-refresh data.

---

### Resolution B3: Scope Statement

**Addressed** — the overview has been updated to: "No behavioral regressions to existing flows; targeted additive modifications are required in listed files."

---

### Resolution C1: Synthesis Input Quality Guardrails

**Accepted.** Add a validation check on `POST /api/ist/syntheses`:

```python
# After confirming all screens are COMPLETED + certified:
# Check for minimum thematic diversity
themes = set()
for screen in source_screens:
    brief = json.loads(screen.screening_brief) if screen.screening_brief else {}
    if brief.get("hypothesis"):
        themes.add(brief["hypothesis"][:50])  # First 50 chars as rough theme key
    extraction = json.loads(screen.content_extraction) if screen.content_extraction else {}
    themes.update(extraction.get("themes", []))

if len(themes) < 2:
    # Non-blocking warning, not a hard block — user may know screens share themes intentionally
    response["warning"] = "Source screens appear to share similar themes. Synthesis works best with thematically diverse screens."
```

This is a soft warning, not a hard block — per Rule 9 (User Authority), the user decides.

---

### Resolution C2: Idempotency Keys

**Accepted.** Add optional `idempotency_key` field to both create schemas:

```python
class ISTSynthesisCreate(BaseModel):
    name: str = Field(..., max_length=200)
    screen_ids: list[int] = Field(..., alias="screenIds", min_length=2, max_length=10)
    auto_advance: bool = Field(default=False, alias="autoAdvance")
    idempotency_key: Optional[str] = Field(default=None, alias="idempotencyKey", max_length=64)

class ISTScreenRefreshCreate(BaseModel):
    content: str = Field(..., min_length=100, max_length=512000)
    content_type: Optional[str] = Field(default="text", alias="contentType")
    auto_advance: bool = Field(default=False, alias="autoAdvance")
    idempotency_key: Optional[str] = Field(default=None, alias="idempotencyKey", max_length=64)
```

Implementation: If `idempotency_key` is provided, check for an existing synthesis/refresh with the same key. If found and not FAILED, return the existing record instead of creating a new one. Store the key in the respective table.

**Update to migration:** Add `idempotency_key` column (nullable, indexed) to both `ist_syntheses` and `ist_screen_refreshes`.

---

### Resolution C3: Artifact Ownership Matrix

**Addressed in Resolution A3** — the per-step write strategy table now serves as the artifact ownership matrix. Each step owns specific tables, and the `replace_artifact` policy is defined for each.

---

### Resolution C4: Regression Testing

**Accepted.** Add to Phase F (Testing & Verification):

```
Regression test suite (run after all implementation):
1. Create a new IST screen → verify full 22-step pipeline completes → PASS
2. Rerun an existing screen → verify data is properly reset and re-generated → PASS
3. Retrieve report from a COMPLETED screen → verify report endpoint works → PASS
4. Verify certification endpoint on a completed screen → PASS
5. Verify HFRT handoff endpoint returns Tier 1 candidates → PASS
6. Create a refresh on a completed screen → verify original screen remains COMPLETED → PASS
7. Create a synthesis from 2 completed screens → verify new workflow runs → PASS
8. Verify screen list page still loads correctly with mix of standard/refreshed screens → PASS
```

---

### Resolution D: Pre-Implementation Checklist (Updated)

The original 5 items are all resolved:

| # | Item | Resolution |
|---|------|-----------|
| D1 | Workflow type compatibility | Resolution A1: CHECK constraint expansion is step 0 of migration |
| D2 | Refresh context contract | Resolution A2: Wrapper handlers + extracted `_run_*` functions |
| D3 | Per-step replace/merge policy | Resolution A3: `replace_artifact` for all steps, claims preserved |
| D4 | UI run-selection behavior | Resolution B1: `active_workflow_run_id` column + banner |
| D5 | Integration test coexistence | Resolution C4: 8-point regression suite |

---

### Summary of Plan Amendments

| Amendment | Source | Impact on Original Plan |
|-----------|--------|------------------------|
| Expand `ck_workflow_type` constraint | A1 | Add step 0 to migration |
| Add `active_workflow_run_id` to `ist_screens` | B1 | Add column to migration, update schema/frontend |
| Add `idempotency_key` to synthesis + refresh tables | C2 | Add column to migration, update schemas |
| Extract `_run_*` functions from 5 service files | A2 | Add 5 files to MODIFY list |
| `replace_artifact` write strategy for all steps | A3 | Clarifies refresh service implementation |
| Refresh never mutates `ist_screens.status` | B2 | Constrains refresh handler implementation |
| Soft theme-diversity warning for synthesis | C1 | Add validation logic to POST endpoint |
| 8-point regression test suite | C4 | Add to Phase F |
| Reworded scope statement | B3 | Overview text updated |

### Updated File Inventory (Additions from Amendments)

**Additional columns in migration 015:**
- `ist_screens.active_workflow_run_id` (Integer FK → workflow_runs.id, nullable)
- `ist_syntheses.idempotency_key` (Text, nullable, indexed)
- `ist_screen_refreshes.idempotency_key` (Text, nullable, indexed)
- Expanded CHECK constraint on `workflow_runs.workflow_type`

**Additional files to MODIFY:**
- `backend/app/services/ist/content_extraction.py` — extract `_run_*` functions
- `backend/app/services/ist/thematic_analysis.py` — extract `_run_*` functions
- `backend/app/services/ist/equity_identification.py` — extract `_run_*` functions
- `backend/app/services/ist/dialectic.py` — extract `_run_*` functions
- `backend/app/services/ist/final_synthesis.py` — extract `_run_*` functions

**Total files to MODIFY (updated): 15** (was 10, +5 service file refactors)

---

**End of CC Resolution**
