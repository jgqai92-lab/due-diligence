// ─── IST Screen Status ──────────────────────────────────────────────

export type ISTScreenStatus =
  | 'PENDING'
  | 'EXTRACTING'
  | 'ANALYZING'
  | 'SCANNING'
  | 'DIALECTIC'
  | 'SYNTHESIZING'
  | 'COMPLETED'
  | 'FAILED';

// ─── Content Type ───────────────────────────────────────────────────

export type ContentType =
  | 'podcast_transcript'
  | 'article'
  | 'earnings_call'
  | 'research_note'
  | 'text';

// ─── Validation Verdict ─────────────────────────────────────────────

export type ValidationVerdict =
  | 'confirmed'
  | 'partially_confirmed'
  | 'contradicted'
  | 'unvalidatable';

// ─── List Item (summary for index page) ─────────────────────────────

export interface ISTScreenListItem {
  id: number;
  name: string;
  status: ISTScreenStatus;
  workflowRunId: number;
  activeWorkflowRunId: number | null;
  claimCount: number;
  candidateCount: number;
  tier1Count: number;
  refreshCount: number;
  isRefreshing: boolean;
  lastRefreshedAt: string | null;
  currentPhase: number;
  createdAt: string;
  updatedAt: string;
}

// ─── Full Detail ────────────────────────────────────────────────────

export interface ISTScreenDetail {
  id: number;
  workflowRunId: number;
  activeWorkflowRunId: number | null;
  name: string;
  status: ISTScreenStatus;
  contentType: ContentType;
  screeningBrief: {
    hypothesis: string;
    contentType: string;
    constraints: Record<string, unknown>;
    frameworks: string[];
  } | null;
  contentExtraction: {
    totalClaims: number;
    claimsWithQuantAnchors: number;
    claimsWithTemporalMarkers: number;
    summary?: string;
    themes?: string[];
  } | null;
  sourceBias: {
    rating: string;
    notes: string;
    sourceCredibility: string;
    potentialBlindSpots: string[];
  } | null;
  refreshCount: number;
  isRefreshing: boolean;
  lastRefreshedAt: string | null;
  currentPhase: number;
  isCertified: boolean;
  certifiedAt: string | null;
  certification: CertificationData | null;
  hfrtHandoff: HandoffData | null;
  createdAt: string;
  updatedAt: string;
}

export interface ISTRefreshListItem {
  id: number;
  workflowRunId: number;
  refreshNumber: number;
  status: string;
  contentType: ContentType;
  deltaClaimCount: number;
  stepsReexecuted: string[] | null;
  impactAssessment: Record<string, unknown> | null;
  errorMessage: string | null;
  isActive: boolean;
  startedAt: string | null;
  completedAt: string | null;
  createdAt: string | null;
}

export interface ISTRefreshDetail extends ISTRefreshListItem {
  screenId: number;
  deltaContent: string;
  refreshNotes: Record<string, unknown> | null;
}

export interface ISTRefreshClaimsResponse {
  screenId: number;
  refreshId: number;
  claims: ISTClaim[];
  totalCount: number;
}

// ─── Claim ──────────────────────────────────────────────────────────

export interface ISTClaim {
  id: number;
  claimText: string;
  sourceCitation: string;
  quantitativeAnchor: string | null;
  temporalMarker: string | null;
  bottleneckName: string | null;
  confidence: number;
  isValidated: boolean;
  validationVerdict: ValidationVerdict | null;
  validationSource: string | null;
  sourceRefreshId?: number | null;
  sourceRefreshNumber?: number | null;
}

// ─── Bottleneck Map ────────────────────────────────────────────────

export interface Bottleneck {
  id: number;
  name: string;
  phase: number;
  phaseLabel: string;
  description: string;
  quantitativeEvidence: string | null;
  temporalMarker: string | null;
  resolutionTrigger: string | null;
}

export interface BottleneckMapResponse {
  screenId: number;
  bottlenecks: Bottleneck[];
  phaseCount: {
    phase1: number;
    phase2: number;
    phase3: number;
    crossCutting: number;
  };
}

// ─── Demand Models ─────────────────────────────────────────────────

export interface DemandModel {
  id: number;
  bottleneckId: number;
  bottleneckName: string;
  formula: string;
  baseCase: { demand: string; tam: number };
  bullCase: { demand: string; tam: number };
  bearCase: { demand: string; tam: number };
  sensitivityTable: Array<{
    variable: string;
    lowCase: number;
    baseCase: number;
    highCase: number;
    tamImpact: string;
  }>;
  multiplierChain: string | null;
}

export interface DemandModelsResponse {
  screenId: number;
  demandModels: DemandModel[];
}

// ─── Validation Results ────────────────────────────────────────────

export interface ValidationItem {
  id: number;
  claimId: number;
  claimText: string;
  verdict: ValidationVerdict;
  confidence: number;
  evidence: string;
  sources: Array<{ url: string; title: string }>;
  searchQueries: string[];
  validatedAt: string;
}

export interface ValidationResponse {
  screenId: number;
  validations: ValidationItem[];
  summary: {
    confirmed: number;
    partiallyConfirmed: number;
    contradicted: number;
    unvalidatable: number;
    total: number;
  };
}

// ─── Scarcity Score ──────────────────────────────────────────────────

export interface ScarcityScore {
  overall: number;
  dimensions: {
    supplyConstraint: number;
    demandVisibility: number;
    substitutionDifficulty: number;
    pricingPower: number;
    temporalUrgency: number;
  };
}

// ─── Equity Candidates ──────────────────────────────────────────────

export interface EquityCandidate {
  id: number;
  ticker: string;
  companyName: string;
  bottleneckId: number | null;
  bottleneckName: string;
  scarcityScore: ScarcityScore;
  moatType: string | null;
  moatEvidence: string | null;
  catalyst: string | null;
  tier: 1 | 2 | 3;
  tierRationale: string | null;
  phase: number | null;
  conviction: "HIGH" | "MEDIUM" | "LOW";
  priceAtScreen: number | null;
  peRatio: number | null;
  marketCap: number | null;
}

export interface CandidatesResponse {
  screenId: number;
  candidates: EquityCandidate[];
  tierBreakdown: { tier1: number; tier2: number; tier3: number };
  totalCount: number;
}

// ─── Tier Groups ────────────────────────────────────────────────────

export interface TierGroup {
  label: string;
  criteria: string;
  candidates: Array<{ ticker: string; companyName: string; scarcityScore: number; catalyst: string | null }>;
  count: number;
}

export interface TiersResponse {
  screenId: number;
  tiers: {
    tier1: TierGroup;
    tier2: TierGroup;
    tier3: TierGroup;
  };
}

// ─── Effects Chains ─────────────────────────────────────────────────

export interface EffectChain {
  id: number;
  thesis: string;
  order: 1 | 2 | 3;
  effectDescription: string;
  equityCandidateId: number | null;
  equityTicker: string | null;
}

export interface EffectsResponse {
  screenId: number;
  effectsChains: EffectChain[];
}

// ─── Invariant Results ──────────────────────────────────────────────

export interface InvariantResult {
  id: string;
  name: string;
  status: "PASS" | "FAIL";
  details: string;
}

export interface InvariantsResponse {
  screenId: number;
  invariants: InvariantResult[];
  allPassed: boolean;
  passCount: number;
  failCount: number;
}

// ─── Dialectic Review ──────────────────────────────────────────────

export interface TierAdjustment {
  ticker: string;
  currentTier: number;
  proposedTier: number;
  rationale: string;
}

export interface DialecticReview {
  screenId: number;
  side: "optimist" | "pessimist" | "synthesis";
  content: {
    narrative: string;
    keyArguments: string[];
    tierAdjustments: TierAdjustment[];
    convictionLevel: string;
    riskDiscount: number;
  };
  createdAt: string;
}

// ─── Synthesis ─────────────────────────────────────────────────────

export interface Disagreement {
  topic: string;
  optimistView: string;
  pessimistView: string;
  resolution: string;
  impactOnTiers: string;
}

export interface SynthesisReview {
  screenId: number;
  synthesis: {
    narrative: string;
    disagreements: Disagreement[];
    finalTierAdjustments: TierAdjustment[];
    overallConviction: string;
    keyRisks: string[];
  };
  createdAt: string;
}

// ─── Master Screen (Ranked Equities) ──────────────────────────────

export interface RankedEquity {
  rank: number;
  ticker: string;
  companyName: string;
  tier: number;
  scarcityScore: number;
  convictionScore: number;
  pillar: string;
  catalyst: string | null;
  priceAtScreen: number | null;
  peRatio: number | null;
  marketCap: number | null;
}

export interface MasterScreenResponse {
  screenId: number;
  rankedEquities: RankedEquity[];
  invariantCompliance: { allPassed: boolean; checkedAt: string };
  totalEquities: number;
  tier1Count: number;
}

// ─── Rotation Strategy ────────────────────────────────────────────

export interface PhaseAllocation {
  phase: number;
  phaseLabel: string;
  allocationPercent: number;
  tickers: string[];
  rationale: string;
}

export interface RotationTrigger {
  trigger: string;
  action: string;
  monitorMetric: string;
}

export interface RotationResponse {
  screenId: number;
  phaseAllocations: PhaseAllocation[];
  rotationTriggers: RotationTrigger[];
  riskLimits: { maxSingleName: number; maxSinglePillar: number; maxTier3Allocation: number };
}

// ─── Catalyst Calendar ────────────────────────────────────────────

export interface CatalystEvent {
  date: string;
  dateType: string;
  event: string;
  tickers: string[];
  expectedImpact: string;
  pillar: string;
  importance: "HIGH" | "MEDIUM" | "LOW";
}

export interface CatalystResponse {
  screenId: number;
  catalysts: CatalystEvent[];
  totalCatalysts: number;
  nextCatalyst: string | null;
  nextCatalystDetails: { date: string; event: string; daysUntil: number } | null;
}

// ─── Stress Tests ─────────────────────────────────────────────────

export interface StressTestResponse {
  screenId: number;
  frameworkTests: Array<{
    framework: string;
    scenario: string;
    impact: string;
    survivorTickers: string[];
    casualtyTickers: string[];
  }>;
  nameTests: Array<{
    ticker: string;
    companyName: string;
    scenarios: Array<{ scenario: string; impactSeverity: string; survivalScore: number }>;
    overallSurvivalScore: number;
  }>;
  survivalScores: Array<Record<string, unknown>>;
  survivalSummary: {
    averageTier1: number;
    averageTier2: number;
    lowestSurvivor: { ticker: string; score: number };
  };
}

// ─── Framework Reference ──────────────────────────────────────────

export interface FrameworkSummary {
  name: string;
  displayName: string;
  description: string;
  category: string;
}

export interface FrameworkDetail {
  name: string;
  displayName: string;
  content: string;
  scoringSchema: {
    dimensions: string[];
    scale: { min: number; max: number };
    tierThresholds: { tier1: number; tier2: number };
  } | null;
}

export interface FrameworkListResponse {
  frameworks: FrameworkSummary[];
  totalCount: number;
}

// ─── Investment Thesis Report ─────────────────────────────────────

export interface ReportResponse {
  screenId: number;
  title: string;
  content: string;
  metadata: {
    pillarCount: number;
    equityCount: number;
    tier1Count: number;
    tier2Count: number;
    tier3Count: number;
    wordCount: number;
    generatedAt?: string;
    model: string;
  };
  report: {
    id: number;
    title: string;
    content: string;
    metadata: {
      pillarCount: number;
      equityCount: number;
      tier1Count: number;
      tier2Count: number;
      tier3Count: number;
      wordCount: number;
      generatedAt: string;
      model: string;
    };
  };
  createdAt: string;
}

// ─── Certification ──────────────────────────────────────────────────

export interface CertificationInvariant {
  id: string;
  name: string;
  status: 'PASS' | 'FAIL';
  details: string;
}

export interface CertificationData {
  certifiedAt: string;
  gate3Passed: boolean;
  invariantsPassed: number;
  invariantsFailed: number;
  invariantResults: CertificationInvariant[];
  reportWordCount: number;
  pillarCount: number;
  equityCount: number;
  tierBreakdown: { tier1: number; tier2: number; tier3: number };
  totalRankedEquities: number;
  model: string;
}

export interface CertificationResponse {
  screenId: number;
  screenName: string;
  certified: boolean;
  certification: CertificationData;
}

// ─── HFRT Handoff ───────────────────────────────────────────────────

export interface HandoffCandidate {
  ticker: string;
  companyName: string;
  tier: number;
  conviction: string;
  pillar: string;
  catalyst: string | null;
  scarcityScore: number | null;
}

export interface HandoffData {
  screenName: string;
  screenId: number;
  certifiedAt: string | null;
  tier1Count: number;
  candidates: HandoffCandidate[];
}

export interface HandoffResponse {
  screenId: number;
  screenName: string;
  certified: boolean;
  certifiedAt: string | null;
  tier1Count: number;
  candidates: HandoffCandidate[];
}
