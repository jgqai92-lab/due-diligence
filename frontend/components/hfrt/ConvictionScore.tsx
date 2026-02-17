"use client";

import { cn } from "@/lib/utils";
import { Gauge } from "lucide-react";

// ─── Factor Definitions ─────────────────────────────────────────────

interface ConvictionFactor {
  score: number;
  rationale: string;
}

const FACTOR_META: Record<string, { label: string; weight: number }> = {
  catalyst_clarity: { label: "Catalyst Clarity", weight: 0.2 },
  downside_quantification: { label: "Downside Quantification", weight: 0.2 },
  moat_durability: { label: "Moat Durability", weight: 0.15 },
  management_quality: { label: "Management Quality", weight: 0.15 },
  earnings_quality: { label: "Earnings Quality", weight: 0.15 },
  valuation_margin: { label: "Valuation Margin", weight: 0.15 },
};

// ─── Helpers ────────────────────────────────────────────────────────

function barColor(score: number): string {
  if (score >= 0.7) return "bg-emerald-500";
  if (score >= 0.4) return "bg-amber-500";
  return "bg-red-500";
}

function textColor(score: number): string {
  if (score >= 0.7) return "text-emerald-400";
  if (score >= 0.4) return "text-amber-400";
  return "text-red-400";
}

// ─── Props ──────────────────────────────────────────────────────────

interface ConvictionScoreProps {
  overallScore: number;
  factors: Record<string, ConvictionFactor>;
  compact?: boolean;
}

// ─── Component ──────────────────────────────────────────────────────

export default function ConvictionScore({
  overallScore,
  factors,
  compact = false,
}: ConvictionScoreProps) {
  const pct = Math.round(overallScore * 100);

  // Sort factors by weight descending
  const sortedFactors = Object.entries(factors)
    .map(([key, factor]) => ({
      key,
      factor,
      meta: FACTOR_META[key] ?? {
        label: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        weight: 0,
      },
    }))
    .sort((a, b) => b.meta.weight - a.meta.weight);

  if (compact) {
    return (
      <div className="flex items-center gap-3">
        <Gauge size={16} className={textColor(overallScore)} />
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-text-secondary">Conviction</span>
            <span className={cn("text-sm font-bold font-mono", textColor(overallScore))}>
              {pct}%
            </span>
          </div>
          <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all duration-500", barColor(overallScore))}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <Gauge size={14} className="text-text-tertiary" />
          Conviction Score
        </h3>
        <span className={cn("text-2xl font-bold font-mono", textColor(overallScore))}>
          {pct}%
        </span>
      </div>

      {/* Overall bar */}
      <div className="w-full h-3 bg-white/10 rounded-full overflow-hidden mb-6">
        <div
          className={cn("h-full rounded-full transition-all duration-500", barColor(overallScore))}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Overall conviction: ${pct}%`}
        />
      </div>

      {/* Factor breakdown */}
      <div className="space-y-3">
        {sortedFactors.map(({ key, factor, meta }) => {
          const factorPct = Math.round((factor?.score ?? 0) * 100);
          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-text-primary">
                    {meta.label}
                  </span>
                  {meta.weight > 0 && (
                    <span className="text-[10px] text-text-tertiary font-mono">
                      {Math.round(meta.weight * 100)}%
                    </span>
                  )}
                </div>
                <span
                  className={cn(
                    "text-xs font-mono font-medium",
                    textColor(factor?.score ?? 0)
                  )}
                >
                  {factorPct}%
                </span>
              </div>
              <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-300",
                    barColor(factor?.score ?? 0)
                  )}
                  style={{ width: `${factorPct}%` }}
                />
              </div>
              {factor?.rationale && (
                <p className="text-[11px] text-text-secondary mt-0.5 leading-relaxed">
                  {factor.rationale}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
