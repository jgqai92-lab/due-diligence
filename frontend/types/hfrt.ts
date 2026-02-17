// ─── HFRT Project Status ──────────────────────────────────────────────

export type HFRTProjectStatus =
  | 'PENDING'
  | 'SCREENING'
  | 'RESEARCHING'
  | 'DUE_DILIGENCE'
  | 'DIALECTIC'
  | 'SYNTHESIZING'
  | 'COMPLETED'
  | 'FAILED'
  | 'NOT_INVESTABLE';

// ─── Template Status ──────────────────────────────────────────────────

export type HFRTTemplateStatus = 'EMPTY' | 'POPULATING' | 'POPULATED' | 'FAILED';

// ─── List Item (summary for index page) ───────────────────────────────

export interface HFRTProjectListItem {
  id: number;
  ticker: string;
  companyName: string | null;
  status: HFRTProjectStatus;
  workflowRunId: number;
  sector: string | null;
  marketCap: number | null;
  investable: boolean;
  convictionScore: number | null;
  recommendation: string | null;
  currentPhase: number;
  templatesPopulated: number;
  source: string | null;
  istScreenId: number | null;
  createdAt: string;
  updatedAt: string;
}

// ─── Full Detail ──────────────────────────────────────────────────────

export interface HFRTProjectDetail {
  id: number;
  workflowRunId: number;
  ticker: string;
  companyName: string | null;
  status: HFRTProjectStatus;
  sector: string | null;
  exchange: string | null;
  marketCap: number | null;
  investable: boolean;
  investableVerdict: string | null;
  convictionScore: number | null;
  positionTier: string | null;
  recommendation: string | null;
  isCertified: boolean;
  certifiedAt: string | null;
  invariantResults: HFRTInvariantResult[] | null;
  source: string | null;
  istScreenId: number | null;
  currentPhase: number;
  createdAt: string;
  updatedAt: string;
}

// ─── Template ─────────────────────────────────────────────────────────

export interface HFRTTemplate {
  templateNumber: number;
  templateName: string;
  status: HFRTTemplateStatus;
  data: Record<string, unknown> | null;
  updatedAt: string;
}

// ─── Template List ────────────────────────────────────────────────────

export interface HFRTTemplateListResponse {
  projectId: number;
  templates: HFRTTemplate[];
}

// ─── Idea Screen (Template 00) ────────────────────────────────────────

export interface LiquidityCheck {
  avg_daily_volume: number | null;
  market_cap_billions: number | null;
  bid_ask_spread: string | null;
  passes: boolean;
  notes: string;
}

export interface IdeaScreenData {
  ticker: string;
  companyName: string;
  verdict: 'PASS' | 'FAIL' | 'CONDITIONAL';
  investable: boolean;
  sector: string;
  exchange: string;
  marketCapBillions: number | null;
  liquidityCheck: LiquidityCheck;
  redFlags: string[];
  rationale: string;
  keyMetrics: Record<string, unknown>;
}

// ─── SEC Filing ───────────────────────────────────────────────────────

export interface SECFiling {
  id: number;
  ticker: string;
  filingType: string;
  filingDate: string | null;
  accessionNumber: string | null;
  url: string | null;
  sections: string[];
  fetchedAt: string;
}

// ─── Dialectic Review ─────────────────────────────────────────────────

export interface HFRTDialecticReview {
  projectId: number;
  side: 'BULL' | 'BEAR';
  content: {
    narrative: string;
    keyArguments: string[];
    catalysts: string[];
    risks: string[];
    convictionLevel: string;
    priceTarget: number | null;
  } | null;
  createdAt: string;
}

// ─── Invariant Results ────────────────────────────────────────────────

export interface HFRTInvariantResult {
  id: string;
  name: string;
  status: 'PASS' | 'FAIL';
  details: string;
}

export interface HFRTInvariantsResponse {
  projectId: number;
  invariants: HFRTInvariantResult[];
  allPassed: boolean;
  passCount: number;
  failCount: number;
}

// ─── Investment Memo ──────────────────────────────────────────────────

export interface HFRTMemoResponse {
  projectId: number;
  memo: {
    title: string;
    content: string;
    convictionScore: number;
    recommendation: string;
    positionTier: string;
    invariants: HFRTInvariantResult[];
    metadata: Record<string, unknown>;
  } | null;
  createdAt: string;
}

// ─── Framework Types ─────────────────────────────────────────────

export interface HFRTFrameworkSummary {
  name: string;
  displayName: string;
  description: string;
  category: string;
}

export interface HFRTFrameworkDetail extends HFRTFrameworkSummary {
  content: string;
  scoringSchema: unknown;
}

export interface HFRTFrameworkListResponse {
  frameworks: HFRTFrameworkSummary[];
  total: number;
}

// ─── Readiness Check (Gap B1) ────────────────────────────────────────

export interface HFRTReadinessResponse {
  ready: boolean;
  issues: string[];
  checks: Record<string, boolean>;
}

// ─── Citation Validation (Gap B5) ───────────────────────────────────

export interface HFRTCitationResponse {
  projectId: number;
  templateNumber: number;
  total_claims: number;
  cited_claims: number;
  uncited_claims: string[];
  coverage_pct: number;
  error?: string;
}

// ─── Dialectic Isolation Audit (Gap B6) ─────────────────────────────

export interface HFRTIsolationAuditResponse {
  projectId: number;
  isIsolated: boolean;
  contaminationEvidence: string[];
}

// ─── Template Names Lookup ────────────────────────────────────────────

export const HFRT_TEMPLATE_NAMES: Record<number, string> = {
  0: 'Idea Screen',
  1: 'Company Overview',
  2: 'Business Model',
  3: 'Competitive Position',
  4: 'Industry Analysis',
  5: 'Financial Analysis',
  6: 'Valuation',
  7: 'Management Assessment',
  8: 'Risk Analysis',
  9: 'Quality of Earnings',
  10: 'Catalyst Analysis',
  11: 'Investment Thesis',
  12: 'Bull Synthesis',
  13: 'Bear Synthesis',
  14: 'Investment Memo',
};

// ─── Phase Names ──────────────────────────────────────────────────────

export const HFRT_PHASE_NAMES: Record<number, string> = {
  0: 'Not Started',
  1: 'Screening',
  2: 'Deep Research',
  3: 'Risk & Due Diligence',
  4: 'Dialectic',
  5: 'Synthesis',
};
