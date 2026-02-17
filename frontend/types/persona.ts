// ─── Persona Name & Target Type Unions ─────────────────────────────

export type PersonaName = 'visser' | 'meldrum' | 'wissner_gross' | 'trio_summary';
export type TargetType = 'ist_screen' | 'hfrt_project' | 'standalone';
export type AnalysisMode = 'structured' | 'freeform';

// ─── Persona Analysis Record ───────────────────────────────────────

export interface PersonaAnalysis {
  id: number;
  personaName: PersonaName;
  targetType: TargetType;
  targetId: number | null;
  analysisResult: Record<string, unknown> | null;
  rawResponse: string | null;
  modelUsed: string | null;
  tokensUsed: number | null;
  createdAt: string;
}

// ─── Request Types ─────────────────────────────────────────────────

export interface PersonaAnalysisRequest {
  personaName: PersonaName;
  targetType: TargetType;
  targetId?: number | null;
  userPrompt: string;
  additionalContext?: string;
  mode?: AnalysisMode;
}

export interface TrioAnalysisRequest {
  targetType: TargetType;
  targetId?: number | null;
  userPrompt: string;
  additionalContext?: string;
  mode?: AnalysisMode;
}

// ─── Response Types ────────────────────────────────────────────────

export interface PersonaAnalysisListResponse {
  analyses: PersonaAnalysis[];
  total: number;
}

export interface PersonaAnalysisByTargetResponse {
  targetType: string;
  targetId: number;
  analyses: PersonaAnalysis[];
  total: number;
}

export interface PersonaSubmitResponse {
  id: number;
  personaName: string;
  targetType: string;
  targetId: number | null;
  status: string;
  message: string;
}

// ─── Visser Analysis Result ────────────────────────────────────────

export interface VisserOpportunity {
  name: string;
  description: string;
  regime_alignment: string;
  conviction: string;
}

export interface VisserKillCondition {
  condition: string;
  severity: string;
  explanation: string;
}

export interface VisserResult {
  regime_classification: {
    current_regime: string;
    confidence: string;
    description: string;
  };
  opportunity_map: VisserOpportunity[];
  kill_conditions: VisserKillCondition[];
  green_marbles: {
    count: number;
    max: number;
    assessment: string;
  };
  overall_verdict: string;
  verdict_reasoning: string;
}

// ─── Meldrum Analysis Result ───────────────────────────────────────

export interface MeldrumFinancialFlag {
  flag: string;
  severity: string;
  explanation: string;
}

export interface MeldrumKillCondition {
  condition: string;
  severity: string;
  explanation: string;
}

export interface MeldrumResult {
  fundamental_assessment: {
    summary: string;
    strengths: string[];
    weaknesses: string[];
  };
  valuation_reality_check: {
    assessment: string;
    fair_value_range: string;
    current_vs_fair: string;
  };
  financial_model_flags: MeldrumFinancialFlag[];
  duration_classification: {
    duration: string;
    reasoning: string;
  };
  kill_conditions: MeldrumKillCondition[];
  overall_verdict: string;
  verdict_reasoning: string;
}

// ─── Wissner-Gross Analysis Result ─────────────────────────────────

export interface WissnerGrossKillCondition {
  condition: string;
  severity: string;
  explanation: string;
}

export interface WissnerGrossResult {
  exponential_score: {
    score: number;
    max: number;
    reasoning: string;
  };
  phase_transition_probability: {
    probability: number;
    description: string;
  };
  dataset_moat: {
    strength: string;
    description: string;
  };
  causal_entropy: {
    assessment: string;
    description: string;
  };
  recursive_improvement: {
    present: boolean;
    description: string;
  };
  kill_conditions: WissnerGrossKillCondition[];
  overall_verdict: string;
  verdict_reasoning: string;
}

// ─── Trio Summary Result ───────────────────────────────────────────

export interface TrioDisagreement {
  persona: string;
  position: string;
  reasoning: string;
}

export interface TrioRiskCondition {
  source: string;
  condition: string;
  severity: string;
}

export interface TrioSummaryResult {
  consensus_verdict: string;
  disagreements: TrioDisagreement[];
  composite_conviction_score: number;
  action_recommendation: string;
  unified_kill_conditions: TrioRiskCondition[];
  summary_narrative: string;
}

// ─── Display Label Maps ────────────────────────────────────────────

export const PERSONA_DISPLAY_NAMES: Record<PersonaName, string> = {
  visser: 'Jordi Visser',
  meldrum: 'Mark Meldrum',
  wissner_gross: 'Alex Wissner-Gross',
  trio_summary: 'Trio Summary',
};

export const PERSONA_COLORS: Record<PersonaName, { bg: string; text: string; border: string; accent: string }> = {
  visser: {
    bg: 'bg-purple-50',
    text: 'text-purple-700',
    border: 'border-purple-200',
    accent: 'bg-purple-100',
  },
  meldrum: {
    bg: 'bg-sky-50',
    text: 'text-sky-700',
    border: 'border-sky-200',
    accent: 'bg-sky-100',
  },
  wissner_gross: {
    bg: 'bg-orange-50',
    text: 'text-orange-700',
    border: 'border-orange-200',
    accent: 'bg-orange-100',
  },
  trio_summary: {
    bg: 'bg-indigo-50',
    text: 'text-indigo-700',
    border: 'border-indigo-200',
    accent: 'bg-indigo-100',
  },
};
