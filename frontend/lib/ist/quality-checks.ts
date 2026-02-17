// IST Content Quality Pre-Screen — Pure TypeScript (no React)
// Provides quality analysis, gate definitions, templates, and examples
// for the Investment Screening Team content input pipeline.

// ---------------------------------------------------------------------------
// Types / Interfaces
// ---------------------------------------------------------------------------

export interface ContentQualityCheck {
  id: string;
  label: string;
  passed: boolean;
  count: number;
  required: number;
  matches: string[];
  severity: "required" | "advisory";
}

export interface ContentQualityResult {
  wordCount: ContentQualityCheck;
  quantitativeAnchors: ContentQualityCheck;
  temporalMarkers: ContentQualityCheck;
  namedEntities: ContentQualityCheck;
  overallReady: boolean;
}

export interface GateCriterion {
  label: string;
  description: string;
  source: "user_input" | "workflow";
}

export interface GateDefinition {
  id: string;
  name: string;
  phase: number;
  phaseLabel: string;
  description: string;
  criteria: GateCriterion[];
}

export type ContentType = "podcast_transcript" | "article" | "earnings_call" | "research_note" | "text";

export interface ContentTemplate {
  label: string;
  template: string;
}

export interface ContentExample {
  title: string;
  snippet: string;
}

// ---------------------------------------------------------------------------
// Constants — Quality Thresholds
// ---------------------------------------------------------------------------

export const QUALITY_THRESHOLDS = {
  minWordCount: 200,
  minQuantitativeAnchors: 3,
  minTemporalMarkers: 1,
} as const;

// ---------------------------------------------------------------------------
// Regex Patterns
// ---------------------------------------------------------------------------

// Matches: $60B, $1.2M, 24%, 3x, 180 billion, 1,000,000, $500M, 2.5 trillion
export const QUANTITATIVE_ANCHOR_PATTERN =
  /(?:\$[\d,.]+\s*[BMTKbmtk](?:illion|illion)?|\$[\d,.]+(?:\s+(?:billion|million|trillion|thousand))?|[\d,.]+\s*%|[\d,.]+\s*x\b|[\d,.]+\s+(?:billion|million|trillion|thousand)|€[\d,.]+\s*[BMTKbmtk]?)/gi;

// Matches: Q1 2025, by 2028, YoY, H2 '26, March 2025, 2025-2030, CY2025, FY2026, over the next 3 years
export const TEMPORAL_MARKER_PATTERN =
  /(?:Q[1-4]\s*[''\u2019]?\d{2,4}|[HhSs][12]\s*[''\u2019]?\d{2,4}|(?:by|through|until|before|after|in)\s+\d{4}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|(?:CY|FY|YE)\s*\d{2,4}|YoY|year[- ]over[- ]year|\d{4}\s*[-\u2013]\s*\d{4}|over the next \d+ years?|next \d+ (?:years?|quarters?|months?))/gi;

// Matches: $AAPL, company names with suffixes like Inc, Corp, Ltd, etc.
export const ENTITY_PATTERN =
  /(?:\$[A-Z]{1,5}\b|(?:[A-Z][a-zA-Z&'-]+(?:\s+[A-Z][a-zA-Z&'-]+){0,5})\s+(?:Inc\.?|Corp\.?|Ltd\.?|LLC|LP|plc|Group|Holdings|Co\.?|Technologies|Semiconductor|Therapeutics|Pharmaceuticals|Partners))/g;

// ---------------------------------------------------------------------------
// analyzeContentQuality
// ---------------------------------------------------------------------------

export function analyzeContentQuality(content: string): ContentQualityResult {
  const words = content.trim().split(/\s+/).filter(Boolean);
  const wordCount = words.length;

  // Deduplicate matches using Array.from(Set) for compatibility
  const quantMatches = Array.from(
    new Set(
      (content.match(QUANTITATIVE_ANCHOR_PATTERN) || []).map((m) => m.trim())
    )
  );
  const tempMatches = Array.from(
    new Set(
      (content.match(TEMPORAL_MARKER_PATTERN) || []).map((m) => m.trim())
    )
  );
  const entityMatches = Array.from(
    new Set(
      (content.match(ENTITY_PATTERN) || []).map((m) => m.trim())
    )
  );

  const wcCheck: ContentQualityCheck = {
    id: "word_count",
    label: "Word count",
    passed: wordCount >= QUALITY_THRESHOLDS.minWordCount,
    count: wordCount,
    required: QUALITY_THRESHOLDS.minWordCount,
    matches: [],
    severity: "required",
  };

  const qaCheck: ContentQualityCheck = {
    id: "quantitative_anchors",
    label: "Quantitative anchors",
    passed: quantMatches.length >= QUALITY_THRESHOLDS.minQuantitativeAnchors,
    count: quantMatches.length,
    required: QUALITY_THRESHOLDS.minQuantitativeAnchors,
    matches: quantMatches.slice(0, 5), // Show up to 5 examples
    severity: "required",
  };

  const tmCheck: ContentQualityCheck = {
    id: "temporal_markers",
    label: "Temporal markers",
    passed: tempMatches.length >= QUALITY_THRESHOLDS.minTemporalMarkers,
    count: tempMatches.length,
    required: QUALITY_THRESHOLDS.minTemporalMarkers,
    matches: tempMatches.slice(0, 5),
    severity: "required",
  };

  const neCheck: ContentQualityCheck = {
    id: "named_entities",
    label: "Named entities",
    passed: true, // Advisory only -- always passes
    count: entityMatches.length,
    required: 0,
    matches: entityMatches.slice(0, 5),
    severity: "advisory",
  };

  return {
    wordCount: wcCheck,
    quantitativeAnchors: qaCheck,
    temporalMarkers: tmCheck,
    namedEntities: neCheck,
    overallReady: wcCheck.passed && qaCheck.passed && tmCheck.passed,
  };
}

// ---------------------------------------------------------------------------
// IST_GATES — Static gate definitions for the 3-gate pipeline
// ---------------------------------------------------------------------------

export const IST_GATES: GateDefinition[] = [
  {
    id: "content_sufficiency",
    name: "Content Sufficiency",
    phase: 2,
    phaseLabel: "Extraction",
    description:
      "Validates that extracted content has enough substance for meaningful analysis.",
    criteria: [
      {
        label: "3+ quantitative anchors",
        description:
          'Claims with numbers, $, or % (e.g., "$60B market", "24% CAGR")',
        source: "user_input",
      },
      {
        label: "1+ temporal marker",
        description: 'Time references (e.g., "by 2028", "Q3 2025")',
        source: "user_input",
      },
      {
        label: "Source bias assessed",
        description: "Automatically completed by the extraction phase",
        source: "workflow",
      },
      {
        label: "1+ bottleneck identified",
        description: "At least one supply-demand bottleneck mapped",
        source: "workflow",
      },
    ],
  },
  {
    id: "research_sufficiency",
    name: "Research Sufficiency",
    phase: 3,
    phaseLabel: "Research",
    description:
      "Ensures enough equity candidates were found for meaningful screening.",
    criteria: [
      {
        label: "3+ equity candidates",
        description: "Companies identified across bottleneck categories",
        source: "workflow",
      },
      {
        label: "2+ tier-1 candidates",
        description: "High-conviction picks with strong moat scores",
        source: "workflow",
      },
      {
        label: "External validation",
        description:
          "Key claims cross-referenced against independent data",
        source: "workflow",
      },
    ],
  },
  {
    id: "screen_coherence",
    name: "Screen Coherence",
    phase: 5,
    phaseLabel: "Synthesis",
    description:
      "Final quality check ensuring the screen is complete, balanced, and internally consistent.",
    criteria: [
      {
        label: "Report word count",
        description:
          "Synthesis report meets minimum length requirements",
        source: "workflow",
      },
      {
        label: "Ticker coverage",
        description:
          "All identified equities appear in the final screen",
        source: "workflow",
      },
      {
        label: "Dialectic completeness",
        description:
          "Both bull and bear cases are adequately represented",
        source: "workflow",
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// CONTENT_TEMPLATES — Skeleton templates per content type
// ---------------------------------------------------------------------------

export const CONTENT_TEMPLATES: Record<ContentType, ContentTemplate> = {
  podcast_transcript: {
    label: "Podcast Transcript",
    template: `[Speaker Name]: Welcome to [Podcast Name]. Today we're discussing [Topic].

[Speaker Name]: The key thesis here is that [describe the investment thesis]. We're seeing [quantitative claim, e.g., "$60B in capital expenditure by 2028"]. The growth rate has been [percentage, e.g., "24% CAGR over the last 3 years"].

[Speaker Name]: The companies best positioned include [Company Name (Ticker)]. Their advantage is [competitive moat].

[Speaker Name]: The timeline for this to play out is [temporal marker, e.g., "over the next 3-5 years"]. Key risks include [risk factors].

[Speaker Name]: On the supply side, the bottleneck is [describe scarcity]. Demand is being driven by [demand drivers with numbers].`,
  },
  article: {
    label: "Article",
    template: `# [Article Title]

## Thesis
[Describe the core investment thesis with specific claims]

## Market Size & Growth
The [market/sector] represents approximately $[X]B in annual revenue, growing at [X]% CAGR through [year]. Key drivers include [list with quantitative backing].

## Key Players
- [Company Name] ($TICKER) \u2014 [brief description with relevant metrics]
- [Company Name] ($TICKER) \u2014 [brief description with relevant metrics]

## Supply-Demand Dynamics
[Describe bottlenecks, scarcity, and supply constraints with numbers]

## Timeline & Catalysts
- [Q/Year]: [Expected catalyst]
- [Q/Year]: [Expected catalyst]

## Risks
[Key risk factors that could invalidate the thesis]`,
  },
  earnings_call: {
    label: "Earnings Call",
    template: `[Company Name] ($TICKER) \u2014 [Quarter] [Year] Earnings Call Transcript

## Management Commentary
CEO [Name]: "We delivered revenue of $[X]B, up [X]% year-over-year. Our [segment] business grew [X]% driven by [factors]."

CFO [Name]: "Operating margin expanded [X] basis points to [X]%. We expect [guidance for next quarter/year]."

## Forward Guidance
- Revenue guidance: $[X]B-$[X]B for [period]
- Margin target: [X]% by [year]
- CapEx plans: $[X]B in [year] for [purpose]

## Q&A Highlights
Analyst: [Question about key topic]
Management: [Response with quantitative detail]`,
  },
  research_note: {
    label: "Research Note",
    template: `# [Research Title]
## Author: [Analyst/Firm Name]

## Investment Thesis
[Core thesis with conviction level]. Price target: $[X] (upside/downside: [X]%).

## Key Metrics
- Market cap: $[X]B
- Revenue (TTM): $[X]B, growing [X]% YoY
- Gross margin: [X]%
- P/E (forward): [X]x

## Catalysts
1. [Near-term catalyst] \u2014 expected [timeframe]
2. [Medium-term catalyst] \u2014 expected [timeframe]

## Comparable Companies
| Company | Ticker | EV/Revenue | Growth |
|---------|--------|-----------|--------|
| [Name]  | $[X]   | [X]x      | [X]%   |

## Risks
[Key risks with probability/impact assessment]`,
  },
  text: {
    label: "General Text",
    template: `## Investment Theme: [Topic]

### Core Thesis
[Describe the investment thesis. Include specific dollar amounts, percentages, and growth rates.]

### Market Opportunity
The total addressable market is approximately $[X]B, expected to reach $[X]B by [year] ([X]% CAGR).

### Key Companies
- [Company Name] ($TICKER) \u2014 [why they benefit]
- [Company Name] ($TICKER) \u2014 [why they benefit]

### Timeline
[When will this thesis play out? Include specific quarters/years.]

### Supporting Data
[Include 3+ quantitative claims: dollar figures, percentages, multiples, or growth rates.]`,
  },
};

// ---------------------------------------------------------------------------
// CONTENT_EXAMPLES — Short example snippets per content type
// ---------------------------------------------------------------------------

export const CONTENT_EXAMPLES: Record<ContentType, ContentExample[]> = {
  podcast_transcript: [
    {
      title: "AI Infrastructure Discussion",
      snippet: `"...the hyperscalers alone are spending $180 billion in capex this year, up 40% YoY. By 2028, we think data center power demand hits 35 gigawatts in the US alone. Companies like Vertiv and Eaton are seeing 2-3x their normal order books..."`,
    },
  ],
  article: [
    {
      title: "Semiconductor Supply Chain",
      snippet: `The global semiconductor market reached $574B in 2024, with AI accelerators growing at 68% CAGR. TSMC's advanced node capacity (3nm/2nm) is booked through Q2 2026, creating a structural bottleneck for companies like NVIDIA and AMD.`,
    },
  ],
  earnings_call: [
    {
      title: "Cloud Infrastructure Growth",
      snippet: `CEO: "Cloud revenue grew 29% to $24.1B. We're investing $13B in capex this quarter, primarily in AI infrastructure. We expect AI-related revenue to exceed $10B annually by FY2026."`,
    },
  ],
  research_note: [
    {
      title: "Energy Transition Thesis",
      snippet: `We initiate coverage of the US power grid modernization theme with a $2.3T total investment estimate through 2035. Grid-edge companies trading at 12-18x forward earnings vs. historical 8-10x, justified by 15%+ EPS growth through 2028.`,
    },
  ],
  text: [
    {
      title: "General Investment Thesis",
      snippet: `The defense sector faces a structural spending increase, with NATO countries targeting 3.5% GDP by 2030 (up from 2%). This represents $400B+ in incremental annual spending, benefiting companies like Rheinmetall, BAE Systems, and L3Harris.`,
    },
  ],
};

// ---------------------------------------------------------------------------
// buildWarningMessage
// ---------------------------------------------------------------------------

export function buildWarningMessage(quality: ContentQualityResult): string {
  const issues: string[] = [];

  if (!quality.wordCount.passed) {
    issues.push(
      `Word count: ${quality.wordCount.count} words (${quality.wordCount.required} recommended)`
    );
  }
  if (!quality.quantitativeAnchors.passed) {
    issues.push(
      `Quantitative anchors: ${quality.quantitativeAnchors.count} found (${quality.quantitativeAnchors.required} recommended \u2014 include dollar figures, percentages, or multiples)`
    );
  }
  if (!quality.temporalMarkers.passed) {
    issues.push(
      `Temporal markers: ${quality.temporalMarkers.count} found (${quality.temporalMarkers.required} recommended \u2014 include dates, quarters, or timeframes)`
    );
  }

  if (issues.length === 0) return "";

  return `Your content may not pass the pipeline's Content Sufficiency gate (Phase 2, Step 6). The following criteria are not yet met:\n\n${issues.map((i) => `\u2022 ${i}`).join("\n")}\n\nYou can still run the screen, but it may be rejected at the gate.`;
}
