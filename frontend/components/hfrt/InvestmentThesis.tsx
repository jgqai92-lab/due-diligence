"use client";

import { cn } from "@/lib/utils";
import { Target, AlertOctagon, TrendingUp } from "lucide-react";

// ─── Data Shape ─────────────────────────────────────────────────────

interface ConvictionFactor {
  score: number; // 0-1
  rationale: string;
}

interface InvestmentThesisData {
  thesis_statement: string;
  conviction_factors: Record<string, ConvictionFactor>;
  overall_conviction_score: number; // 0-1
  recommendation: string; // BUY, HOLD, SELL, PASS
  position_tier: string; // FULL, HALF, QUARTER, WATCH
  price_target: number | null;
  risk_reward_ratio: string | null;
  key_assumption: string;
  thesis_kill_conditions: string[];
}

// ─── Props ──────────────────────────────────────────────────────────

interface InvestmentThesisProps {
  data: Record<string, unknown>;
}

// ─── Helpers ────────────────────────────────────────────────────────

function recBadgeConfig(rec: string): { bg: string; text: string } {
  switch (rec?.toUpperCase()) {
    case "BUY":
      return { bg: "bg-emerald-500/10", text: "text-emerald-300" };
    case "HOLD":
      return { bg: "bg-amber-500/10", text: "text-amber-300" };
    case "SELL":
      return { bg: "bg-red-500/10", text: "text-red-300" };
    case "PASS":
    default:
      return { bg: "bg-white/10", text: "text-text-primary" };
  }
}

function tierBadgeConfig(tier: string): { bg: string; text: string } {
  switch (tier?.toUpperCase()) {
    case "FULL":
      return { bg: "bg-emerald-500/10", text: "text-emerald-400" };
    case "HALF":
      return { bg: "bg-sky-500/10", text: "text-sky-400" };
    case "QUARTER":
      return { bg: "bg-amber-500/10", text: "text-amber-400" };
    case "WATCH":
    default:
      return { bg: "bg-white/5", text: "text-text-secondary" };
  }
}

function convictionBarColor(score: number): string {
  if (score >= 0.7) return "bg-emerald-500";
  if (score >= 0.4) return "bg-amber-500";
  return "bg-red-500";
}

function convictionTextColor(score: number): string {
  if (score >= 0.7) return "text-emerald-400";
  if (score >= 0.4) return "text-amber-400";
  return "text-red-400";
}

// ─── Conviction Factor Definitions ──────────────────────────────────

const CONVICTION_FACTOR_META: Record<string, { label: string; weight: string }> = {
  catalyst_clarity: { label: "Catalyst Clarity", weight: "20%" },
  downside_quantification: { label: "Downside Quantification", weight: "20%" },
  moat_durability: { label: "Moat Durability", weight: "15%" },
  management_quality: { label: "Management Quality", weight: "15%" },
  earnings_quality: { label: "Earnings Quality", weight: "15%" },
  valuation_margin: { label: "Valuation Margin", weight: "15%" },
  // Legacy factor keys (backwards-compatible rendering)
  thesis_clarity: { label: "Thesis Clarity", weight: "20%" },
  moat_strength: { label: "Moat Strength", weight: "20%" },
  risk_reward: { label: "Risk/Reward", weight: "20%" },
  data_quality: { label: "Data Quality", weight: "10%" },
};

// ─── Component ──────────────────────────────────────────────────────

export default function InvestmentThesis({ data }: InvestmentThesisProps) {
  const d = data as unknown as InvestmentThesisData;

  const rec = recBadgeConfig(d.recommendation);
  const tier = tierBadgeConfig(d.position_tier);
  const convictionPct = d.overall_conviction_score != null
    ? Math.round(d.overall_conviction_score * 100)
    : null;

  return (
    <div className="space-y-4">
      {/* Header: Recommendation + Position Tier + Conviction */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          {/* Recommendation Badge */}
          <span
            className={cn(
              "inline-flex items-center px-4 py-1.5 rounded-full text-sm font-bold",
              rec.bg,
              rec.text
            )}
          >
            {d.recommendation || "N/A"}
          </span>

          {/* Position Tier Badge */}
          {d.position_tier && (
            <span
              className={cn(
                "inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border border-border",
                tier.bg,
                tier.text
              )}
            >
              {d.position_tier} Position
            </span>
          )}

          {/* Metrics */}
          <div className="ml-auto flex items-center gap-4">
            {d.price_target != null && (
              <div className="text-right">
                <p className="text-xs text-text-secondary">Price Target</p>
                <p className="text-sm font-mono font-bold text-text-primary">
                  ${d.price_target.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </p>
              </div>
            )}
            {d.risk_reward_ratio && (
              <div className="text-right">
                <p className="text-xs text-text-secondary">Risk/Reward</p>
                <p className="text-sm font-mono font-bold text-text-primary">
                  {d.risk_reward_ratio}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Overall Conviction Score */}
        {convictionPct != null && (
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <p className="text-xs text-text-secondary">Overall Conviction</p>
              <span
                className={cn(
                  "text-lg font-bold font-mono",
                  convictionTextColor(d.overall_conviction_score)
                )}
              >
                {convictionPct}%
              </span>
            </div>
            <div className="w-full h-2.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-500",
                  convictionBarColor(d.overall_conviction_score)
                )}
                style={{ width: `${convictionPct}%` }}
                role="progressbar"
                aria-valuenow={convictionPct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`Conviction score: ${convictionPct}%`}
              />
            </div>
          </div>
        )}
      </div>

      {/* Thesis Statement */}
      {d.thesis_statement && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <Target size={14} className="text-text-tertiary" />
            Investment Thesis
          </h3>
          <p className="text-base text-text-primary leading-relaxed font-medium">
            {d.thesis_statement}
          </p>
        </div>
      )}

      {/* Conviction Factors */}
      {d.conviction_factors &&
        Object.keys(d.conviction_factors).length > 0 && (
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-text-primary mb-4">
              Conviction Factors
            </h3>
            <div className="space-y-4">
              {Object.entries(d.conviction_factors).map(([key, factor]) => {
                const meta = CONVICTION_FACTOR_META[key] ?? {
                  label: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
                  weight: "",
                };
                const pct = Math.round((factor?.score ?? 0) * 100);

                return (
                  <div key={key}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-text-primary">
                          {meta.label}
                        </span>
                        {meta.weight && (
                          <span className="text-[11px] text-text-tertiary font-mono">
                            ({meta.weight})
                          </span>
                        )}
                      </div>
                      <span
                        className={cn(
                          "text-sm font-mono font-medium",
                          convictionTextColor(factor?.score ?? 0)
                        )}
                      >
                        {pct}%
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden mb-1">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all duration-300",
                          convictionBarColor(factor?.score ?? 0)
                        )}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    {factor?.rationale && (
                      <p className="text-xs text-text-secondary leading-relaxed">
                        {factor.rationale}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

      {/* Key Assumption */}
      {d.key_assumption && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <TrendingUp size={14} className="text-text-tertiary" />
            Key Assumption
          </h3>
          <p className="text-sm text-text-primary leading-relaxed">
            {d.key_assumption}
          </p>
        </div>
      )}

      {/* Thesis Kill Conditions */}
      {d.thesis_kill_conditions && d.thesis_kill_conditions.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border-2 border-red-500/30 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-red-300 mb-3 flex items-center gap-2">
            <AlertOctagon size={14} className="text-red-500" />
            Thesis Kill Conditions
          </h3>
          <p className="text-xs text-red-400 mb-3">
            If any of these conditions occur, the thesis should be re-evaluated
            or abandoned.
          </p>
          <ul className="space-y-2">
            {d.thesis_kill_conditions.map((condition, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <span className="text-red-400 mt-0.5 flex-shrink-0 font-bold">
                  &#x2717;
                </span>
                <span className="text-red-300">{condition}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
