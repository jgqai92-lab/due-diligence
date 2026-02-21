export type SynthesisStatus =
  | "PENDING"
  | "INGESTING"
  | "ANALYZING"
  | "DIALECTIC"
  | "SYNTHESIZING"
  | "COMPLETED"
  | "FAILED";

export interface SynthesisSource {
  id: number;
  screenId: number;
  screenName: string;
  tier1Count: number;
  tier2Count: number;
  tier3Count: number;
  primaryTheme: string | null;
}

export interface OverlapAppearance {
  screenId: number;
  tier: number;
  scarcityScore: number | null;
  bottleneck: string | null;
}

export interface OverlapEntry {
  ticker: string;
  companyName: string;
  appearances: OverlapAppearance[];
}

export interface ThesisInteraction {
  screenA: { id: number; name: string; theme?: string | null };
  screenB: { id: number; name: string; theme?: string | null };
  classification: "reinforcing" | "contradicting" | "orthogonal" | string;
  rationale: string;
}

export interface SynthesisTierChange {
  ticker: string;
  originalTier: number;
  newTier: number;
  rationale: string;
}

export interface SynthesisEquity {
  id: number;
  ticker: string;
  companyName: string;
  originalTier: number;
  newTier: number;
  tierChanged: boolean;
  tierChangeRationale: string | null;
  sourceScreenCount: number;
  sourceScreenIds: number[];
  combinedScarcityScore: Record<string, unknown> | null;
  combinedThesis: string | null;
  combinedCatalyst: string | null;
  conviction: string | null;
}

export interface SynthesisListItem {
  id: number;
  name: string;
  status: SynthesisStatus;
  workflowRunId: number;
  sourceScreenCount: number;
  tierChangeCount: number;
  createdAt: string;
  updatedAt: string | null;
}

export interface SynthesisDetail {
  id: number;
  name: string;
  status: SynthesisStatus;
  workflowRunId: number;
  overlapMatrix: OverlapEntry[];
  thesisInteractions: ThesisInteraction[];
  tierChanges: SynthesisTierChange[];
  combinedBrief: Record<string, unknown> | null;
  report: string | null;
  reportMetadata: Record<string, unknown> | null;
  certification: Record<string, unknown> | null;
  hfrtHandoff: Record<string, unknown> | null;
  isCertified: boolean;
  certifiedAt: string | null;
  createdAt: string;
  updatedAt: string | null;
}

export interface SynthesisDialectic {
  synthesisId: number;
  side: "OPTIMIST" | "PESSIMIST" | "SYNTHESIS";
  content: Record<string, unknown>;
  createdAt: string | null;
}

