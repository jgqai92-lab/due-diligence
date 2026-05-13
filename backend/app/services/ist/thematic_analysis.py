"""IST Phase 2: thematic analysis and quality gating."""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.ist import ISTBottleneck, ISTClaim, ISTDemandModel, ISTScreen, ISTValidation
from app.services.ist.claude_client import call_claude, call_claude_raw, get_step_model_tier
from app.services.perplexity_client import is_available as perplexity_available, search_and_analyze
from app.services.workflow_engine import emit_sse_event, register_step

logger = logging.getLogger(__name__)


class BottleneckItem(BaseModel):
    """A single temporal bottleneck identified from claims."""

    name: str
    phase: int = Field(ge=0, le=3)
    phase_label: str
    description: str
    quantitative_evidence: Optional[str] = None
    temporal_marker: Optional[str] = None
    resolution_trigger: Optional[str] = None
    claim_indices: list[int]
    causal_parent_name: Optional[str] = None


class BottleneckResult(BaseModel):
    """Structured output from bottleneck mapping."""

    bottlenecks: list[BottleneckItem]


class DemandModelItem(BaseModel):
    """A single demand model for a bottleneck."""

    bottleneck_name: str
    formula: str
    base_case: dict
    bull_case: dict
    bear_case: dict
    sensitivity_table: list[dict]
    multiplier_chain: Optional[str] = None
    methodology: Optional[str] = None
    sources: list[str] = Field(default_factory=list)


class DemandModelResult(BaseModel):
    """Structured output from demand modeling."""

    models: list[DemandModelItem]


class ValidationItem(BaseModel):
    """Validation result for one claim."""

    claim_index: int
    verdict: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    sources: list[dict]
    search_queries: list[str]
    reasoning: Optional[str] = Field(
        default=None,
        description=(
            "Step-by-step reasoning trace: what data was looked up, what values were found, "
            "what calculation was performed, and how the verdict/confidence were derived."
        ),
    )


class ValidationResult(BaseModel):
    """Structured output from external validation."""

    validations: list[ValidationItem]


class DataLookup(BaseModel):
    """A specific data point to look up for claim verification."""

    query: str = Field(description="Targeted search query (e.g., 'XLU utilities ETF YTD return 2026')")
    data_type: str = Field(description="What type of data: price, return, ratio, volume, market_cap, rate, other")
    instrument: Optional[str] = Field(default=None, description="Ticker/index/instrument if applicable (e.g., 'XLU', 'SPX', 'VIX')")
    time_period: Optional[str] = Field(default=None, description="Relevant time period (e.g., 'Q1 2026', 'YTD 2026', '2025')")


class ClaimDecomposition(BaseModel):
    """Decomposition of a claim into verifiable data lookups."""

    claim_index: int
    claim_text: str
    is_quantitative: bool = Field(description="True if claim makes a specific numerical/measurable assertion")
    data_lookups: list[DataLookup] = Field(description="Specific data points needed to verify this claim")
    verification_logic: str = Field(description="How to use the data to verify: e.g., 'Compare XLU return minus XLF return to claimed 9%'")


class ClaimDecompositionResult(BaseModel):
    """Structured output from claim decomposition step."""

    decompositions: list[ClaimDecomposition]


CLAIM_DECOMPOSITION_SYSTEM_PROMPT = """You are an investment research analyst preparing claims for quantitative verification.

Your task: For each claim, determine whether it makes a quantitative/measurable assertion, and if so, decompose it into the SPECIFIC data points needed to verify it.

CRITICAL: For sector/asset class comparisons, ALWAYS use the standard SPDR Select Sector ETFs or well-known benchmark instruments. Common mappings:
- Utilities sector → XLU (Utilities Select Sector SPDR)
- Financials sector → XLF (Financial Select Sector SPDR)
- Technology sector → XLK (Technology Select Sector SPDR)
- Energy sector → XLE (Energy Select Sector SPDR)
- Healthcare sector → XLV (Health Care Select Sector SPDR)
- Consumer Discretionary → XLY, Consumer Staples → XLP
- Industrials → XLI, Materials → XLB, Real Estate → XLRE
- S&P 500 → SPY or ^GSPC, Nasdaq → QQQ or ^IXIC
- VIX → ^VIX, 10-Year Treasury → ^TNX
- Gold → GLD, Oil → USO/CL
- Bitcoin → BTC-USD

Each data_lookup query MUST be specific enough for a web search to return an exact number.

Examples:
- Claim: "Utilities outperforming financials by 9% QTD"
  → is_quantitative: true
  → data_lookups: [
      {query: "XLU ETF quarter-to-date performance percentage return 2026", data_type: "return", instrument: "XLU", time_period: "Q1 2026"},
      {query: "XLF ETF quarter-to-date performance percentage return 2026", data_type: "return", instrument: "XLF", time_period: "Q1 2026"}
    ]
  → verification_logic: "Calculate XLU QTD return minus XLF QTD return. Compare to claimed 9% outperformance."

- Claim: "S&P 500 is flat year-to-date"
  → is_quantitative: true
  → data_lookups: [{query: "S&P 500 SPY ETF YTD return percentage 2026", data_type: "return", instrument: "SPY", time_period: "YTD 2026"}]
  → verification_logic: "Check if S&P 500 YTD return is near 0% (within +/- 2%)"

- Claim: "VIX spiked above 30"
  → is_quantitative: true
  → data_lookups: [{query: "VIX index current level February 2026", data_type: "price", instrument: "^VIX", time_period: "current"}]
  → verification_logic: "Check if VIX reached or exceeded 30"

- Claim: "AI infrastructure spending is accelerating"
  → is_quantitative: false
  → data_lookups: [{query: "AI infrastructure capex spending growth 2025 2026", data_type: "other"}]
  → verification_logic: "Look for evidence of increasing AI infrastructure spend"

For QUALITATIVE claims (opinions, predictions, trends without specific numbers), set is_quantitative to false but still provide helpful search queries.

Return ONLY valid JSON matching the schema provided."""


BOTTLENECK_MAPPING_SYSTEM_PROMPT = """You are an investment research analyst specializing in temporal bottleneck analysis.

Your task:
1. Read the provided claims carefully
2. Map claims into a temporal bottleneck cascade with these phases:
   - Phase 1 (near-term, 0-18 months): Immediate supply/demand bottlenecks
   - Phase 2 (mid-term, 18-36 months): Emerging structural bottlenecks
   - Phase 3 (secular, 3+ years): Long-term systemic bottlenecks
   - Phase 0 (cross-cutting): Bottlenecks that span multiple time horizons
3. Identify sequential dependencies between bottlenecks (causal chains) using causal_parent_name
4. Each bottleneck MUST cite quantitative evidence from the claims
5. Map each claim to at least one bottleneck via claim_indices (0-based index)

NEVER fabricate data, statistics, or financial figures. Only cite information found in the provided claims. If a bottleneck lacks quantitative evidence from the claims, set quantitative_evidence to null.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""

DEMAND_MODELING_SYSTEM_PROMPT = """You are a quantitative investment analyst building demand models from bottleneck analysis.

Your task:
1. For each bottleneck provided, build a quantitative demand model
2. Create base, bull, and bear case scenarios with demand estimates and TAM
3. Define the demand formula showing how inputs drive the output
4. Build a sensitivity table with 2-3 key variables showing how they impact TAM
5. If applicable, describe the multiplier chain in one sentence
6. Provide a "methodology" field explaining HOW you arrived at the TAM figure: what market sizing approach you used (top-down, bottom-up, analogy-based), what the key input variables are, and any derivation steps
7. Provide a "sources" array listing the publications, databases, or data sources that inform your TAM estimate. For each source, include the name, publisher/organization, and approximate date or year if known. If a TAM is your own estimate based on reasoning from the bottleneck evidence (not from a specific publication), say "Author estimate based on [reasoning]". NEVER cite a source you are not confident exists.

IMPORTANT: Keep each model CONCISE. Use short strings for assumptions (not nested objects).
Structure each scenario with keys: demand, tam, assumptions (as a short string).
Structure sensitivity_table entries with keys: variable, low, base, high, tamImpact.
Limit sensitivity_table to 3 rows max per model.

NEVER fabricate specific company revenue or earnings data. You may estimate market-level TAM ranges based on the bottleneck evidence provided. If insufficient data exists for a credible model, state that explicitly in the formula field.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""

EXTERNAL_VALIDATION_SYSTEM_PROMPT = """You are a fact-checking analyst validating investment claims against your knowledge base.

Your task:
1. For each claim provided, assess whether it is:
   - confirmed: Claim is well-supported by widely available evidence
   - partially_confirmed: Claim has some support but key details may differ
   - contradicted: Claim conflicts with widely available evidence
   - unvalidatable: Insufficient information to assess the claim
2. Provide specific evidence for your verdict
3. List sources (with url and title) where possible -- use real, well-known sources
4. List the search queries you would use to validate each claim

NEVER fabricate source URLs. If you cannot identify a real source, use a descriptive placeholder URL like \"https://example.com/industry-report\" and note it is illustrative. Verdicts must be honest -- do not confirm claims you cannot verify.

Return ONLY valid JSON matching the schema provided. Do NOT include any text outside the JSON."""


PERPLEXITY_BATCH_SIZE = 10  # Claims per batch for decomposition + search


async def _decompose_claims_for_search(
    batch_text: str,
    batch_size: int,
    *,
    model: str | None = None,
    source_date: str | None = None,
) -> ClaimDecompositionResult:
    """Step 1: Claude decomposes claims into specific, searchable data lookups.

    For quantitative claims (e.g., "utilities outperforming financials by 9% QTD"),
    this identifies the exact instruments, metrics, and time periods needed to verify.
    """
    temporal_context = ""
    if source_date:
        temporal_context = (
            f"<temporal_context>\n"
            f"This content was published/processed on {source_date}. When claims reference "
            f"dates without an explicit year (e.g., 'February 3rd', 'last Monday', 'this quarter'), "
            f"interpret them relative to this date. The current year is {source_date[:4]}.\n"
            f"</temporal_context>\n\n"
        )

    user_prompt = (
        f"{temporal_context}"
        f"<claims>\n{batch_text}\n</claims>\n\n"
        f"Decompose each of these {batch_size} claims into specific data lookups.\n"
        f"For quantitative claims, identify exact tickers/indices, metrics, and time periods.\n"
        f"Return JSON matching this schema: {ClaimDecompositionResult.model_json_schema()}"
    )

    return await call_claude(
        system_prompt=CLAIM_DECOMPOSITION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=ClaimDecompositionResult,
        model="sonnet",  # Fast decomposition — doesn't need opus
        max_tokens=8192,
    )


async def _search_with_targeted_queries(
    decompositions: list[ClaimDecomposition],
    workflow_run_id: int,
    batch_idx: int,
) -> tuple[str, list[str]]:
    """Step 2: Perplexity searches for specific data using decomposed queries.

    Returns (combined_search_results, all_citations).
    Merges results from quantitative-targeted searches and a general search.
    """
    # Collect all targeted queries from quantitative claims
    targeted_queries: list[str] = []
    for decomp in decompositions:
        if decomp.is_quantitative and decomp.data_lookups:
            for lookup in decomp.data_lookups:
                targeted_queries.append(lookup.query)

    all_search_text: list[str] = []
    all_citations: list[str] = []

    # Run targeted searches for quantitative data (batched into groups)
    if targeted_queries:
        # Group queries into manageable search requests (max ~5 per call)
        query_groups: list[list[str]] = []
        for i in range(0, len(targeted_queries), 5):
            query_groups.append(targeted_queries[i : i + 5])

        for qg_idx, query_group in enumerate(query_groups):
            queries_text = "\n".join(f"- {q}" for q in query_group)
            try:
                pplx = await search_and_analyze(
                    system_prompt=(
                        "You are a financial data research assistant. Search for the SPECIFIC "
                        "data points requested below. Return exact numbers, percentages, prices, "
                        "and dates. Be precise and cite your sources."
                    ),
                    user_prompt=(
                        f"Find the following specific financial data points:\n\n{queries_text}\n\n"
                        "For each data point, provide the exact value, date/period, and source."
                    ),
                    model="sonar-pro",
                    max_tokens=4096,
                    workflow_run_id=workflow_run_id,
                )
                all_search_text.append(
                    f"=== Targeted Data Search (group {qg_idx + 1}) ===\n"
                    f"Queries: {queries_text}\n\n{pplx.content}"
                )
                all_citations.extend(pplx.citations)
                logger.info(
                    "Targeted search group %d/%d: %d citations",
                    qg_idx + 1, len(query_groups), len(pplx.citations),
                )
            except Exception:
                logger.warning(
                    "Targeted search group %d failed, continuing",
                    qg_idx + 1, exc_info=True,
                )

    # Also run a general fact-check search for qualitative claims
    qualitative_claims = [
        d for d in decompositions if not d.is_quantitative
    ]
    if qualitative_claims:
        qual_text = "\n".join(
            f"[{d.claim_index}] {d.claim_text}" for d in qualitative_claims
        )
        try:
            pplx = await search_and_analyze(
                system_prompt=(
                    "You are a fact-checking research assistant. For each claim below, "
                    "search for evidence that confirms, contradicts, or qualifies it. "
                    "Provide specific data points and source references."
                ),
                user_prompt=(
                    f"Validate each of these investment claims against current data:\n\n{qual_text}"
                ),
                model="sonar-pro",
                max_tokens=4096,
                workflow_run_id=workflow_run_id,
            )
            all_search_text.append(
                f"=== General Fact-Check Search ===\n{pplx.content}"
            )
            all_citations.extend(pplx.citations)
        except Exception:
            logger.warning("General fact-check search failed, continuing", exc_info=True)

    combined_results = "\n\n".join(all_search_text) if all_search_text else "No search results available."
    return combined_results, all_citations


async def _run_perplexity_validation(
    claims_text: str,
    claim_count: int,
    workflow_run_id: int,
    *,
    model: str | None = None,
    source_date: str | None = None,
) -> ValidationResult:
    """Three-step Perplexity-grounded validation with quantitative decomposition.

    For each batch of claims:
    1. DECOMPOSE: Claude identifies what specific data is needed to verify each claim
       (ETF tickers, indices, metrics, time periods, calculation logic)
    2. SEARCH: Perplexity searches for that specific data with targeted queries
    3. VERIFY: Claude calculates and compares actual data against claimed values

    This approach is critical for quantitative market claims like "utilities
    outperforming financials by 9% QTD" — instead of generic fact-checking,
    Perplexity searches for XLU and XLF QTD returns, and Claude does the math.
    """
    claim_lines = [line for line in claims_text.strip().split("\n") if line.strip()]
    batches: list[list[str]] = []
    for i in range(0, len(claim_lines), PERPLEXITY_BATCH_SIZE):
        batches.append(claim_lines[i : i + PERPLEXITY_BATCH_SIZE])

    logger.info(
        "Three-step Perplexity validation: %d claims in %d batches of ~%d",
        claim_count, len(batches), PERPLEXITY_BATCH_SIZE,
    )

    all_validations: list[ValidationItem] = []
    total_citations = 0

    for batch_idx, batch_lines in enumerate(batches):
        batch_text = "\n".join(batch_lines)
        batch_size = len(batch_lines)

        # ── Step 1: Decompose claims into data lookups ────────────────────
        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "external_validation",
                "message": f"Batch {batch_idx + 1}/{len(batches)}: Decomposing {batch_size} claims into data lookups...",
                "percent": int(10 + (80 * batch_idx / len(batches))),
            },
        )

        try:
            decomposition = await _decompose_claims_for_search(
                batch_text, batch_size, model=model, source_date=source_date,
            )
            quant_count = sum(1 for d in decomposition.decompositions if d.is_quantitative)
            total_lookups = sum(len(d.data_lookups) for d in decomposition.decompositions)
            logger.info(
                "Batch %d decomposition: %d/%d quantitative claims, %d total data lookups",
                batch_idx, quant_count, batch_size, total_lookups,
            )
        except Exception:
            logger.warning(
                "Claim decomposition failed for batch %d, falling back to generic search",
                batch_idx, exc_info=True,
            )
            # Fall back: create generic decompositions
            decomposition = None

        # ── Step 2: Targeted Perplexity search ────────────────────────────
        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "external_validation",
                "message": f"Batch {batch_idx + 1}/{len(batches)}: Searching for specific data...",
                "percent": int(15 + (80 * batch_idx / len(batches))),
            },
        )

        if decomposition and decomposition.decompositions:
            try:
                search_results, citations = await _search_with_targeted_queries(
                    decomposition.decompositions, workflow_run_id, batch_idx,
                )
                total_citations += len(citations)
            except Exception:
                logger.warning(
                    "Targeted search failed for batch %d, claims will be unvalidatable",
                    batch_idx, exc_info=True,
                )
                for line in batch_lines:
                    idx_match = re.match(r"\[(\d+)\]", line.strip())
                    idx = int(idx_match.group(1)) if idx_match else 0
                    all_validations.append(ValidationItem(
                        claim_index=idx, verdict="unvalidatable", confidence=0.05,
                        evidence="Search failed for this batch.",
                        sources=[], search_queries=[],
                    ))
                continue
        else:
            # Fallback: generic Perplexity search (no decomposition available)
            try:
                pplx = await search_and_analyze(
                    system_prompt=(
                        "You are a fact-checking research assistant. For each claim, "
                        "search for evidence. Provide specific data points and sources."
                    ),
                    user_prompt=f"Validate these claims:\n\n{batch_text}",
                    model="sonar-pro",
                    max_tokens=8192,
                    workflow_run_id=workflow_run_id,
                )
                search_results = pplx.content
                citations = pplx.citations
                total_citations += len(citations)
            except Exception:
                logger.warning("Fallback search failed for batch %d", batch_idx, exc_info=True)
                for line in batch_lines:
                    idx_match = re.match(r"\[(\d+)\]", line.strip())
                    idx = int(idx_match.group(1)) if idx_match else 0
                    all_validations.append(ValidationItem(
                        claim_index=idx, verdict="unvalidatable", confidence=0.05,
                        evidence="Search failed for this batch.",
                        sources=[], search_queries=[],
                    ))
                continue

        # ── Step 3: Claude calculates and verifies ────────────────────────
        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "external_validation",
                "message": f"Batch {batch_idx + 1}/{len(batches)}: Calculating and verifying claims...",
                "percent": int(25 + (70 * batch_idx / len(batches))),
            },
        )

        citation_list = "\n".join(
            f"[{i+1}] {url}" for i, url in enumerate(citations)
        )

        # Build decomposition context for Claude if available
        decomp_context = ""
        if decomposition and decomposition.decompositions:
            decomp_lines = []
            for d in decomposition.decompositions:
                if d.is_quantitative:
                    decomp_lines.append(
                        f"Claim [{d.claim_index}] (QUANTITATIVE): {d.verification_logic}"
                    )
                else:
                    decomp_lines.append(
                        f"Claim [{d.claim_index}] (QUALITATIVE): {d.verification_logic}"
                    )
            decomp_context = (
                "<verification_instructions>\n"
                + "\n".join(decomp_lines)
                + "\n</verification_instructions>\n\n"
            )

        temporal_note = ""
        if source_date:
            temporal_note = (
                f"4. TEMPORAL CONTEXT: The source content was published/processed on {source_date}. "
                f"The current year is {source_date[:4]}. When claims reference dates without an "
                f"explicit year (e.g., 'February 3rd', 'last Monday', 'this quarter'), interpret "
                f"them relative to {source_date}. Do NOT default to an earlier year.\n\n"
            )

        verification_system = (
            "You are a quantitative fact-checker verifying investment claims against real data.\n\n"
            "CRITICAL RULES:\n"
            "1. For QUANTITATIVE claims: You MUST perform the actual calculation using the data "
            "from the search results. Show your math. Compare the calculated result to what "
            "was claimed. If the data supports the claim within a reasonable margin (~10%), "
            "mark as confirmed. If directionally correct but off by more, mark partially_confirmed. "
            "If the calculation contradicts the claim, mark contradicted.\n\n"
            "2. For QUALITATIVE claims: Assess based on the evidence found.\n\n"
            "3. URLS: You are provided with VERIFIED source URLs below. When populating the "
            "'sources' field, use ONLY URLs from this list. Do NOT invent URLs.\n\n"
            f"{temporal_note}"
            f"<verified_urls>\n{citation_list}\n</verified_urls>\n\n"
            "For each claim, provide ALL of these fields:\n"
            "- verdict: confirmed, partially_confirmed, contradicted, or unvalidatable\n"
            "- confidence: 0.0 to 1.0\n"
            "- evidence: A concise summary of what the data shows\n"
            "- sources: list of {url, title} using ONLY verified URLs above\n"
            "- search_queries: queries used to find the data\n"
            "- reasoning: A DETAILED step-by-step trace showing:\n"
            "  (a) DATA SOUGHT: What specific data points were needed\n"
            "  (b) DATA FOUND: Exact values found in search results (with source)\n"
            "  (c) CALCULATION: For quantitative claims, show the math step-by-step\n"
            "  (d) COMPARISON: How the calculated result compares to the claim\n"
            "  (e) VERDICT RATIONALE: Why this verdict and confidence level were assigned\n"
            "  Example: 'DATA SOUGHT: XLU QTD return, XLF QTD return. "
            "DATA FOUND: XLU QTD: +8.2% (source: Yahoo Finance), XLF QTD: -0.5% (source: Yahoo Finance). "
            "CALCULATION: 8.2% - (-0.5%) = 8.7% outperformance. "
            "COMPARISON: Claimed ~9%, actual 8.7% — within 3% margin. "
            "VERDICT: confirmed at 0.85 confidence — close match with minor rounding difference.'\n\n"
            "Return ONLY valid JSON matching the schema provided."
        )

        verification_user = (
            f"{decomp_context}"
            f"<claims>\n{batch_text}\n</claims>\n\n"
            f"<search_results>\n{search_results}\n</search_results>\n\n"
            f"Verify each of the {batch_size} claims using the search results above. "
            f"For quantitative claims, CALCULATE and COMPARE. Use the original claim indices.\n"
            f"Return JSON matching this schema: {ValidationResult.model_json_schema()}"
        )

        batch_result = await call_claude(
            system_prompt=verification_system,
            user_prompt=verification_user,
            response_model=ValidationResult,
            model=model,
            max_tokens=8192,
        )

        all_validations.extend(batch_result.validations)

    logger.info(
        "Three-step validation complete: %d claims, %d batches, %d total citations",
        claim_count, len(batches), total_citations,
    )

    return ValidationResult(validations=all_validations)


async def _run_bottleneck_mapping(
    screen: ISTScreen,
    claims: list[ISTClaim],
    db: Session,
    workflow_run_id: int,
    *,
    update_screen_status: bool = True,
    replace_artifact: bool = False,
    model: str | None = None,
) -> dict | None:
    """Core bottleneck-mapping logic for IST and IST_REFRESH."""
    if update_screen_status:
        screen.status = "ANALYZING"
        screen.updated_at = datetime.now(timezone.utc)
        db.commit()

    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "bottleneck_mapping",
            "message": "Mapping claims into temporal bottleneck cascade...",
            "percent": 10,
        },
    )

    if not claims:
        raise ValueError("No claims found for bottleneck mapping. Run content_extraction first.")

    if replace_artifact:
        db.query(ISTBottleneck).filter(ISTBottleneck.screen_id == screen.id).delete()
        db.query(ISTClaim).filter(ISTClaim.screen_id == screen.id).update({"bottleneck_name": None})

    claims_text = "\n".join(
        f"[{i}] {c.claim_text}"
        + (f" | Quant: {c.quantitative_anchor}" if c.quantitative_anchor else "")
        + (f" | Time: {c.temporal_marker}" if c.temporal_marker else "")
        for i, c in enumerate(claims)
    )

    user_prompt = (
        f"<claims>\n{claims_text}\n</claims>\n\n"
        f"Map these {len(claims)} claims into temporal bottlenecks.\n"
        f"Return JSON matching this schema: {BottleneckResult.model_json_schema()}"
    )

    result = await call_claude(
        system_prompt=BOTTLENECK_MAPPING_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=BottleneckResult,
        model=model,
    )

    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "bottleneck_mapping",
            "message": f"Identified {len(result.bottlenecks)} bottlenecks, storing...",
            "percent": 70,
        },
    )

    name_to_bottleneck: dict[str, ISTBottleneck] = {}
    for bn_data in result.bottlenecks:
        bottleneck = ISTBottleneck(
            screen_id=screen.id,
            name=bn_data.name,
            phase=bn_data.phase,
            phase_label=bn_data.phase_label,
            description=bn_data.description,
            quantitative_evidence=bn_data.quantitative_evidence,
            temporal_marker=bn_data.temporal_marker,
            resolution_trigger=bn_data.resolution_trigger,
        )
        db.add(bottleneck)
        name_to_bottleneck[bn_data.name] = bottleneck

    db.flush()

    for bn_data in result.bottlenecks:
        if bn_data.causal_parent_name and bn_data.causal_parent_name in name_to_bottleneck:
            child = name_to_bottleneck[bn_data.name]
            parent = name_to_bottleneck[bn_data.causal_parent_name]
            child.causal_parent_id = parent.id

    for bn_data in result.bottlenecks:
        for idx in bn_data.claim_indices:
            if 0 <= idx < len(claims):
                claims[idx].bottleneck_name = bn_data.name

    screen.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "bottlenecksIdentified": len(result.bottlenecks),
        "phaseBreakdown": {
            "phase0": sum(1 for b in result.bottlenecks if b.phase == 0),
            "phase1": sum(1 for b in result.bottlenecks if b.phase == 1),
            "phase2": sum(1 for b in result.bottlenecks if b.phase == 2),
            "phase3": sum(1 for b in result.bottlenecks if b.phase == 3),
        },
    }


async def _run_demand_modeling(
    screen: ISTScreen,
    bottlenecks: list[ISTBottleneck],
    db: Session,
    workflow_run_id: int,
    *,
    replace_artifact: bool = False,
    model: str | None = None,
) -> dict | None:
    """Core demand-modeling logic for IST and IST_REFRESH."""
    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "demand_modeling",
            "message": "Building quantitative demand models...",
            "percent": 10,
        },
    )

    if not bottlenecks:
        raise ValueError("No bottlenecks found for demand modeling. Run bottleneck_mapping first.")

    if replace_artifact:
        db.query(ISTDemandModel).filter(ISTDemandModel.screen_id == screen.id).delete()

    bottleneck_text = "\n".join(
        f"- {bn.name} (Phase {bn.phase}: {bn.phase_label}): {bn.description}"
        + (f" | Evidence: {bn.quantitative_evidence}" if bn.quantitative_evidence else "")
        + (f" | Temporal: {bn.temporal_marker}" if bn.temporal_marker else "")
        for bn in bottlenecks
    )

    # Optionally enrich with current market/TAM data from Perplexity
    market_data_block = ""
    if perplexity_available():
        try:
            bn_names = ", ".join(bn.name for bn in bottlenecks[:5])
            pplx = await search_and_analyze(
                system_prompt=(
                    "You are a market research analyst. For each bottleneck topic, "
                    "find the current total addressable market (TAM), market size, "
                    "growth rate, and key demand drivers. Provide specific numbers."
                ),
                user_prompt=f"Find current market size and TAM data for: {bn_names}",
                model="sonar",
                max_tokens=4096,
                workflow_run_id=workflow_run_id,
            )
            market_data_block = (
                f"<current_market_data>\n{pplx.content}\n</current_market_data>\n\n"
            )
            logger.info("Perplexity market data enrichment: %d citations", len(pplx.citations))
        except Exception:
            logger.warning("Perplexity market data enrichment failed, continuing without", exc_info=True)

    user_prompt = (
        f"{market_data_block}"
        f"<bottlenecks>\n{bottleneck_text}\n</bottlenecks>\n\n"
        f"Build quantitative demand models for each of these {len(bottlenecks)} bottlenecks.\n"
        f"Return JSON matching this schema: {DemandModelResult.model_json_schema()}"
    )

    result = await call_claude(
        system_prompt=DEMAND_MODELING_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=DemandModelResult,
        model=model,
        max_tokens=16384,
    )

    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "demand_modeling",
            "message": f"Created {len(result.models)} demand models, storing...",
            "percent": 70,
        },
    )

    name_to_id: dict[str, int] = {bn.name: bn.id for bn in bottlenecks}

    for model_data in result.models:
        bottleneck_id = name_to_id.get(model_data.bottleneck_name)
        if bottleneck_id is None:
            logger.warning(
                "Demand model references unknown bottleneck '%s', skipping",
                model_data.bottleneck_name,
            )
            continue

        db.add(
            ISTDemandModel(
                screen_id=screen.id,
                bottleneck_id=bottleneck_id,
                formula=model_data.formula,
                base_case=json.dumps(model_data.base_case),
                bull_case=json.dumps(model_data.bull_case),
                bear_case=json.dumps(model_data.bear_case),
                sensitivity_table=json.dumps(model_data.sensitivity_table),
                multiplier_chain=model_data.multiplier_chain,
                methodology=model_data.methodology,
                sources=json.dumps(model_data.sources) if model_data.sources else None,
            )
        )

    screen.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"modelsCreated": len(result.models)}


async def _run_external_validation(
    screen: ISTScreen,
    claims: list[ISTClaim],
    db: Session,
    workflow_run_id: int,
    *,
    replace_artifact: bool = False,
    model: str | None = None,
) -> dict | None:
    """Core external-validation logic for IST and IST_REFRESH.

    When Perplexity is available, uses web-search-grounded validation:
    1. Perplexity searches the web for evidence on each claim
    2. Claude structures the Perplexity output + real citations into ValidationResult
    This produces real, clickable source URLs instead of hallucinated ones.

    Falls back to Claude-only validation when Perplexity is not configured.
    """
    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "external_validation",
            "message": "Validating claims against external sources...",
            "percent": 10,
        },
    )

    if not claims:
        raise ValueError("No claims found for validation. Run content_extraction first.")

    if replace_artifact:
        db.query(ISTValidation).filter(ISTValidation.screen_id == screen.id).delete()
        for claim in claims:
            claim.is_validated = 0
            claim.validation_verdict = None
            claim.validation_source = None

    claims_text = "\n".join(
        f"[{i}] {c.claim_text}"
        + (f" | Quant: {c.quantitative_anchor}" if c.quantitative_anchor else "")
        + (f" | Time: {c.temporal_marker}" if c.temporal_marker else "")
        for i, c in enumerate(claims)
    )

    # Derive source date from screen creation time for temporal context
    source_date = screen.created_at.strftime("%Y-%m-%d") if screen.created_at else None

    if perplexity_available():
        # Perplexity-grounded validation: real web search + real citations
        result = await _run_perplexity_validation(
            claims_text, len(claims), workflow_run_id, model=model,
            source_date=source_date,
        )
    else:
        # Claude-only fallback
        logger.info("Perplexity not available, using Claude-only validation")
        temporal_context = ""
        if source_date:
            temporal_context = (
                f"<temporal_context>\n"
                f"This content was published/processed on {source_date}. When claims reference "
                f"dates without an explicit year, interpret them relative to this date. "
                f"The current year is {source_date[:4]}.\n"
                f"</temporal_context>\n\n"
            )
        user_prompt = (
            f"{temporal_context}"
            f"<claims>\n{claims_text}\n</claims>\n\n"
            f"Validate each of these {len(claims)} claims.\n"
            f"Return JSON matching this schema: {ValidationResult.model_json_schema()}"
        )

        result = await call_claude(
            system_prompt=EXTERNAL_VALIDATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=ValidationResult,
            model=model,
        )

    await emit_sse_event(
        workflow_run_id,
        "step_progress",
        {
            "stepName": "external_validation",
            "message": f"Validated {len(result.validations)} claims, storing...",
            "percent": 70,
        },
    )

    verdict_counts: dict[str, int] = {
        "confirmed": 0,
        "partially_confirmed": 0,
        "contradicted": 0,
        "unvalidatable": 0,
    }

    for val_data in result.validations:
        idx = val_data.claim_index
        if idx < 0 or idx >= len(claims):
            logger.warning(
                "Validation references out-of-range claim index %d, skipping",
                idx,
            )
            continue

        claim = claims[idx]
        db.add(
            ISTValidation(
                screen_id=screen.id,
                claim_id=claim.id,
                verdict=val_data.verdict,
                confidence=val_data.confidence,
                evidence=val_data.evidence,
                sources=json.dumps(val_data.sources),
                search_queries=json.dumps(val_data.search_queries),
                reasoning=val_data.reasoning,
            )
        )

        claim.is_validated = 1
        claim.validation_verdict = val_data.verdict
        claim.validation_source = json.dumps(val_data.sources)
        verdict_counts[val_data.verdict] = verdict_counts.get(val_data.verdict, 0) + 1

    screen.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "claimsValidated": len(result.validations),
        "verdictBreakdown": verdict_counts,
    }


@register_step("IST", "bottleneck_mapping")
async def handle_bottleneck_mapping(workflow_run_id: int) -> dict | None:
    """Map extracted claims into a temporal bottleneck cascade."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        claims = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .order_by(ISTClaim.id)
            .all()
        )

        model = await get_step_model_tier(workflow_run_id, "bottleneck_mapping")
        return await _run_bottleneck_mapping(screen, claims, db, workflow_run_id, model=model)
    finally:
        db.close()


@register_step("IST", "demand_modeling")
async def handle_demand_modeling(workflow_run_id: int) -> dict | None:
    """Build quantitative demand models per bottleneck."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        bottlenecks = (
            db.query(ISTBottleneck)
            .filter(ISTBottleneck.screen_id == screen.id)
            .order_by(ISTBottleneck.id)
            .all()
        )

        model = await get_step_model_tier(workflow_run_id, "demand_modeling")
        return await _run_demand_modeling(screen, bottlenecks, db, workflow_run_id, model=model)
    finally:
        db.close()


@register_step("IST", "external_validation")
async def handle_external_validation(workflow_run_id: int) -> dict | None:
    """Validate claims against external sources."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        claims = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .order_by(ISTClaim.id)
            .all()
        )

        model = await get_step_model_tier(workflow_run_id, "external_validation")
        return await _run_external_validation(screen, claims, db, workflow_run_id, model=model)
    finally:
        db.close()


@register_step("IST", "content_sufficiency_gate")
async def handle_content_sufficiency_gate(workflow_run_id: int) -> dict | None:
    """Content sufficiency quality gate (deterministic server-side)."""
    db = SessionLocal()
    try:
        screen = (
            db.query(ISTScreen)
            .filter(ISTScreen.workflow_run_id == workflow_run_id)
            .first()
        )
        if not screen:
            raise ValueError(f"No IST screen found for workflow {workflow_run_id}")

        await emit_sse_event(
            workflow_run_id,
            "step_progress",
            {
                "stepName": "content_sufficiency_gate",
                "message": "Running content sufficiency checks...",
                "percent": 20,
            },
        )

        deficiencies: list[str] = []

        quant_anchor_count = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .filter(ISTClaim.quantitative_anchor.isnot(None))
            .count()
        )
        if quant_anchor_count < 3:
            deficiencies.append(
                f"Insufficient quantitative anchors: {quant_anchor_count}/3 minimum"
            )

        temporal_marker_count = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .filter(ISTClaim.temporal_marker.isnot(None))
            .count()
        )
        if temporal_marker_count < 1:
            deficiencies.append("No temporal markers found across claims (need 1+ minimum)")

        if not screen.source_bias:
            deficiencies.append("Source bias assessment has not been completed")

        bottleneck_count = (
            db.query(ISTBottleneck)
            .filter(ISTBottleneck.screen_id == screen.id)
            .count()
        )
        if bottleneck_count < 1:
            deficiencies.append("No bottlenecks identified (need 1+ minimum)")

        if deficiencies:
            await emit_sse_event(
                workflow_run_id,
                "gate_failed",
                {
                    "stepName": "content_sufficiency_gate",
                    "deficiencies": deficiencies,
                },
            )
            raise ValueError("Content sufficiency gate FAILED: " + "; ".join(deficiencies))

        gate_details = {
            "quantitativeAnchors": quant_anchor_count,
            "temporalMarkers": temporal_marker_count,
            "sourceBiasAssessed": True,
            "bottleneckCount": bottleneck_count,
        }

        await emit_sse_event(
            workflow_run_id,
            "gate_passed",
            {
                "stepName": "content_sufficiency_gate",
                "details": gate_details,
            },
        )

        return {
            "gateResult": "PASSED",
            **gate_details,
        }
    finally:
        db.close()
