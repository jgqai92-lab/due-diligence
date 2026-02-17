import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type {
  ZoneType,
  LeverageZone,
  ProfitabilityZone,
  CashFlowZone,
  GrowthZone,
  ValuationZone,
  SentimentZone,
  HealthScore,
  ForensicRisk,
} from "@/types/analysis";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatScore(value: number | null): string {
  if (value == null) return "N/A";
  return value.toFixed(2);
}

export function formatLargeNumber(value: number | null): string {
  if (value == null) return "N/A";
  const abs = Math.abs(value);
  if (abs >= 1e12) return "$" + (value / 1e12).toFixed(2) + "T";
  if (abs >= 1e9) return "$" + (value / 1e9).toFixed(2) + "B";
  if (abs >= 1e6) return "$" + (value / 1e6).toFixed(2) + "M";
  return "$" + value.toFixed(2);
}

export function formatPercent(value: number | null): string {
  if (value == null) return "N/A";
  return (value >= 0 ? "+" : "") + value.toFixed(2) + "%";
}

export function getZoneColor(zone: ZoneType): string {
  switch (zone) {
    case "safe": return "text-bull";
    case "warning": return "text-warning";
    case "danger": return "text-bear";
    default: return "text-text-secondary";
  }
}

export function getZoneBorder(zone: ZoneType): string {
  switch (zone) {
    case "safe": return "border-l-bull";
    case "warning": return "border-l-warning";
    case "danger": return "border-l-bear";
    default: return "border-l-border-strong";
  }
}

export function classifyMScore(score: number | null): ZoneType {
  if (score == null) return null;
  if (score < -2.22) return "safe";
  if (score <= -1.78) return "warning";
  return "danger";
}

export function classifyZScore(score: number | null): ZoneType {
  if (score == null) return null;
  if (score > 2.99) return "safe";
  if (score >= 1.81) return "warning";
  return "danger";
}

export function timeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

// ─── Financial Statement Formatting Helpers ──────────────────────────

/**
 * Format a raw dollar amount for display in financial statement tables.
 * Divides by 1,000,000 to show values in millions with one decimal place.
 * Negative values are shown in parentheses.
 *
 * Examples:
 *   391035000000  -> "391,035.0"
 *   -5234000000   -> "(5,234.0)"
 *   null          -> "\u2014"
 *   0             -> "0.0"
 */
export function formatStatementValue(value: number | null): string {
  if (value == null) return "\u2014";
  const inMillions = value / 1_000_000;
  const abs = Math.abs(inMillions);
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(abs);
  if (inMillions < 0) return `(${formatted})`;
  return formatted;
}

/**
 * Format a fiscal period date string (YYYY-MM-DD) into a display header.
 * Returns "FY 'YY" format, e.g. "2024-09-28" -> "FY '24"
 */
export function formatFiscalPeriod(dateStr: string): string {
  if (!dateStr || dateStr.length < 4) return dateStr;
  const year = dateStr.substring(2, 4);
  return `FY '${year}`;
}

// ─── New Classification Helpers ──────────────────────────────────────

/**
 * Classify leverage risk based on debt-to-equity ratio.
 * safe: D/E < 1.0 | warning: D/E < 2.0 | danger: D/E >= 2.0
 * Returns "safe" for null values (graceful default).
 */
export function classifyLeverage(debtToEquity: number | null): LeverageZone {
  if (debtToEquity == null) return "safe";
  if (debtToEquity < 1.0) return "safe";
  if (debtToEquity < 2.0) return "warning";
  return "danger";
}

/**
 * Classify profitability strength based on net margin.
 * strong: > 15% | moderate: > 5% | weak: <= 5%
 * Returns "moderate" for null values (graceful default).
 */
export function classifyProfitability(netMargin: number | null): ProfitabilityZone {
  if (netMargin == null) return "moderate";
  if (netMargin > 0.15) return "strong";
  if (netMargin > 0.05) return "moderate";
  return "weak";
}

/**
 * Classify cash flow quality based on OCF-to-Net-Income ratio.
 * strong: > 1.0 | moderate: > 0.5 | weak: <= 0.5
 * Returns "moderate" for null values (graceful default).
 */
export function classifyCashFlow(ocfToNetIncome: number | null): CashFlowZone {
  if (ocfToNetIncome == null) return "moderate";
  if (ocfToNetIncome > 1.0) return "strong";
  if (ocfToNetIncome > 0.5) return "moderate";
  return "weak";
}

/**
 * Classify growth profile based on revenue growth YoY.
 * high: > 20% | moderate: > 5% | low: >= 0% | negative: < 0%
 * Returns "low" for null values (graceful default).
 */
export function classifyGrowth(revenueGrowth: number | null): GrowthZone {
  if (revenueGrowth == null) return "low";
  if (revenueGrowth > 0.20) return "high";
  if (revenueGrowth > 0.05) return "moderate";
  if (revenueGrowth >= 0) return "low";
  return "negative";
}

/**
 * Classify valuation based on P/E trailing ratio.
 * cheap: < 15 | fair: < 30 | expensive: >= 30
 * Returns "fair" for null values (graceful default).
 */
export function classifyValuation(peRatio: number | null): ValuationZone {
  if (peRatio == null) return "fair";
  if (peRatio < 15) return "cheap";
  if (peRatio < 30) return "fair";
  return "expensive";
}

/**
 * Classify analyst sentiment based on mean analyst rating.
 * Analyst ratings: 1 = Strong Buy, 5 = Strong Sell
 * bullish: < 2.0 | neutral: < 3.5 | bearish: >= 3.5
 * Returns "neutral" for null values (graceful default).
 */
export function classifySentiment(analystRating: number | null): SentimentZone {
  if (analystRating == null) return "neutral";
  if (analystRating < 2.0) return "bullish";
  if (analystRating < 3.5) return "neutral";
  return "bearish";
}

// ─── New Formatting Helpers ──────────────────────────────────────────

/**
 * Format a ratio value with "x" suffix (e.g., 2.4x).
 * Returns "N/A" for null/undefined values.
 */
export function formatRatio(value: number | null): string {
  if (value == null) return "N/A";
  return value.toFixed(1) + "x";
}

/**
 * Format a valuation multiple with "x" suffix (e.g., 12.5x).
 * Returns "N/A" for null/undefined values.
 */
export function formatMultiple(value: number | null): string {
  if (value == null) return "N/A";
  return value.toFixed(1) + "x";
}

/**
 * Format a decimal as a percentage with sign (e.g., 0.152 -> "+15.2%").
 * Differs from formatPercent: takes a decimal ratio (0.15) not a percentage (15).
 * Returns "N/A" for null/undefined values.
 */
export function formatPercentFromDecimal(value: number | null): string {
  if (value == null) return "N/A";
  const pct = value * 100;
  return (pct >= 0 ? "+" : "") + pct.toFixed(1) + "%";
}

// ─── Composite Score Helpers ─────────────────────────────────────────

/**
 * Compute a composite financial health score from profitability, leverage,
 * and cash flow classifications.
 *
 * Scoring: strong=2, moderate=1, weak/danger=0
 * STRONG: total >= 5 | MODERATE: total >= 3 | WEAK: total < 3
 *
 * @param profitability - net margin value (decimal, e.g. 0.15 = 15%)
 * @param leverage - debt-to-equity ratio value
 * @param cashFlow - OCF-to-net-income ratio value
 */
export function getHealthScore(
  profitability: number | null,
  leverage: number | null,
  cashFlow: number | null
): HealthScore {
  const profScore = ({ strong: 2, moderate: 1, weak: 0 } as const)[
    classifyProfitability(profitability)
  ];
  const levScore = ({ safe: 2, warning: 1, danger: 0 } as const)[
    classifyLeverage(leverage)
  ];
  const cfScore = ({ strong: 2, moderate: 1, weak: 0 } as const)[
    classifyCashFlow(cashFlow)
  ];

  const total = profScore + levScore + cfScore;
  if (total >= 5) return "STRONG";
  if (total >= 3) return "MODERATE";
  return "WEAK";
}

/**
 * Compute a composite forensic risk assessment from Beneish M-Score and
 * Altman Z-Score.
 *
 * Scoring: safe=0, warning=1, danger=2
 * LOW: total = 0 | MEDIUM: total <= 2 | HIGH: total > 2
 *
 * @param beneishComposite - Beneish M-Score composite value
 * @param altmanScore - Altman Z-Score standard score value
 */
export function getForensicRisk(
  beneishComposite: number | null,
  altmanScore: number | null
): ForensicRisk {
  const mZone = classifyMScore(beneishComposite);
  const zZone = classifyZScore(altmanScore);

  const mRisk = ({ safe: 0, warning: 1, danger: 2 } as const)[mZone ?? "safe"];
  const zRisk = ({ safe: 0, warning: 1, danger: 2 } as const)[zZone ?? "safe"];

  const total = (mRisk ?? 0) + (zRisk ?? 0);
  if (total === 0) return "LOW";
  if (total <= 2) return "MEDIUM";
  return "HIGH";
}

// ─── Zone-to-Color Mapping Helpers for New Classifications ───────────

/**
 * Map leverage zone to design system color class.
 */
export function getLeverageZoneColor(zone: LeverageZone): string {
  switch (zone) {
    case "safe": return "text-bull";
    case "warning": return "text-warning";
    case "danger": return "text-bear";
  }
}

/**
 * Map profitability zone to design system color class.
 */
export function getProfitabilityZoneColor(zone: ProfitabilityZone): string {
  switch (zone) {
    case "strong": return "text-bull";
    case "moderate": return "text-warning";
    case "weak": return "text-bear";
  }
}

/**
 * Map cash flow zone to design system color class.
 */
export function getCashFlowZoneColor(zone: CashFlowZone): string {
  switch (zone) {
    case "strong": return "text-bull";
    case "moderate": return "text-warning";
    case "weak": return "text-bear";
  }
}

/**
 * Map growth zone to design system color class.
 */
export function getGrowthZoneColor(zone: GrowthZone): string {
  switch (zone) {
    case "high": return "text-bull";
    case "moderate": return "text-warning";
    case "low": return "text-text-secondary";
    case "negative": return "text-bear";
  }
}

/**
 * Map valuation zone to design system color class.
 */
export function getValuationZoneColor(zone: ValuationZone): string {
  switch (zone) {
    case "cheap": return "text-bull";
    case "fair": return "text-warning";
    case "expensive": return "text-bear";
  }
}

/**
 * Map sentiment zone to design system color class.
 */
export function getSentimentZoneColor(zone: SentimentZone): string {
  switch (zone) {
    case "bullish": return "text-bull";
    case "neutral": return "text-warning";
    case "bearish": return "text-bear";
  }
}

/**
 * Map health score to design system color class.
 */
export function getHealthScoreColor(score: HealthScore): string {
  switch (score) {
    case "STRONG": return "text-bull";
    case "MODERATE": return "text-warning";
    case "WEAK": return "text-bear";
  }
}

/**
 * Map forensic risk to design system color class.
 */
export function getForensicRiskColor(risk: ForensicRisk): string {
  switch (risk) {
    case "LOW": return "text-bull";
    case "MEDIUM": return "text-warning";
    case "HIGH": return "text-bear";
  }
}

/**
 * Map health score to design system border class (for zone cards).
 */
export function getHealthScoreBorder(score: HealthScore): string {
  switch (score) {
    case "STRONG": return "border-l-bull";
    case "MODERATE": return "border-l-warning";
    case "WEAK": return "border-l-bear";
  }
}

/**
 * Map forensic risk to design system border class (for zone cards).
 */
export function getForensicRiskBorder(risk: ForensicRisk): string {
  switch (risk) {
    case "LOW": return "border-l-bull";
    case "MEDIUM": return "border-l-warning";
    case "HIGH": return "border-l-bear";
  }
}
