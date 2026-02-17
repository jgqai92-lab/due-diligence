export interface Citation {
  line_item: string;
  filing_type: string;
  period: string;
  raw_value: number | null;
  source: string;
  formula: string;  // Mathematical formula for the metric
  description: string;  // Plain-English explanation of what the metric measures
}

export interface MetricComponent {
  value: number | null;
  citation: Citation;
}

export interface BeneishMScoreComponents {
  dsri: MetricComponent;
  gmi: MetricComponent;
  aqi: MetricComponent;
  sgi: MetricComponent;
  depi: MetricComponent;
  sgai: MetricComponent;
  lvgi: MetricComponent;
  tata: MetricComponent;
}

export interface BeneishMScore {
  composite: number | null;
  interpretation: string | null;
  components: BeneishMScoreComponents;
  thresholds: { likely_manipulator: number; grey_zone: number[] };
}

export interface AltmanZScoreVariant {
  score: number | null;
  zone: string | null;
  components: Record<string, MetricComponent>;
  disclaimer?: string;
}

export interface AltmanZScore {
  standard: AltmanZScoreVariant;
  saas_modified: AltmanZScoreVariant;
}

export interface RuleOf40 {
  score: number | null;
  revenue_growth_percent: number | null;
  fcf_margin_percent: number | null;
  interpretation: string | null;
  citations: Record<string, Citation>;
}

export interface MagicNumber {
  score: number | null;
  net_new_arr: number | null;
  sales_and_marketing_spend: number | null;
  interpretation: string | null;
  citations: Record<string, Citation>;
}

export interface ForensicMetrics {
  beneish_m_score: BeneishMScore;
  altman_z_score: AltmanZScore;
  rule_of_40: RuleOf40;
  magic_number: MagicNumber;
}

// ─── New General Metric Interfaces ─────────────────────────────────

export interface ProfitabilityMetrics {
  gross_margin: MetricComponent;
  operating_margin: MetricComponent;
  net_margin: MetricComponent;
  roe: MetricComponent;
  roa: MetricComponent;
  roic: MetricComponent;
}

export interface LeverageMetrics {
  debt_to_equity: MetricComponent;
  interest_coverage: MetricComponent;
  current_ratio: MetricComponent;
  quick_ratio: MetricComponent;
  net_debt_to_ebitda: MetricComponent;
}

export interface CashFlowMetrics {
  fcf_yield: MetricComponent;
  ocf_to_net_income: MetricComponent;
  fcf_margin: MetricComponent;
  capex_to_revenue: MetricComponent;
}

export interface GrowthMetrics {
  revenue_growth_yoy: MetricComponent;
  earnings_growth_yoy: MetricComponent;
  fcf_growth_yoy: MetricComponent;
  revenue_cagr_3y: MetricComponent;
}

export interface ValuationMetrics {
  pe_trailing: MetricComponent;
  pe_forward: MetricComponent;
  ev_to_ebitda: MetricComponent;
  price_to_fcf: MetricComponent;
  price_to_sales: MetricComponent;
  peg_ratio: MetricComponent;
}

export interface ShareholderMetrics {
  dividend_yield: MetricComponent;
  payout_ratio: MetricComponent;
}

export interface SentimentMetrics {
  analyst_rating: MetricComponent;
  analyst_count: number | null;
  analyst_recommendation: string | null;
  short_ratio: MetricComponent;
  short_percent_float: MetricComponent;
  institutional_pct: MetricComponent;
  insider_pct: MetricComponent;
}

export interface SectorSpecificMetrics {
  sector_category: string;
  label: string;
  metrics: Record<string, MetricComponent>;
  interpretations: Record<string, string | null>;
}

export interface ComprehensiveAnalysis {
  // Forensic (existing, unchanged)
  beneish_m_score: BeneishMScore;
  altman_z_score: AltmanZScore;
  // General financial health (new)
  profitability: ProfitabilityMetrics;
  leverage: LeverageMetrics;
  cash_flow: CashFlowMetrics;
  growth: GrowthMetrics;
  valuation: ValuationMetrics;
  shareholder_returns: ShareholderMetrics;
  sentiment: SentimentMetrics;
  // Sector-specific (conditional)
  sector_category: string;
  sector_specific: SectorSpecificMetrics | null;
}

// ─── Classification Types ──────────────────────────────────────────

export type LeverageZone = "safe" | "warning" | "danger";
export type ProfitabilityZone = "strong" | "moderate" | "weak";
export type CashFlowZone = "strong" | "moderate" | "weak";
export type GrowthZone = "high" | "moderate" | "low" | "negative";
export type ValuationZone = "cheap" | "fair" | "expensive";
export type SentimentZone = "bullish" | "neutral" | "bearish";
export type HealthScore = "STRONG" | "MODERATE" | "WEAK";
export type ForensicRisk = "LOW" | "MEDIUM" | "HIGH";

export interface CompanyProfile {
  name: string;
  sector: string;
  industry: string;
  market_cap: number | null;
  full_time_employees: number | null;
}

export interface ForensicReport {
  markdown: string;
  generated_at: string;
  model: string;
}

export interface DataSources {
  provider: string;
  periods: string[];
  fetched_at: string;
  cache_hit: boolean;
}

// ─── Financial Statement Interfaces ─────────────────────────────────

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

// ─── Analysis Response ──────────────────────────────────────────────

export interface AnalysisResponse {
  ticker: string;
  company_profile: CompanyProfile;
  forensic_metrics: ForensicMetrics;
  comprehensive_analysis: ComprehensiveAnalysis;
  report: ForensicReport;
  data_sources: DataSources;
  financial_statements?: FinancialStatements;
}

export interface SearchResult {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  count: number;
}

export type ZoneType = "safe" | "warning" | "danger" | null;
