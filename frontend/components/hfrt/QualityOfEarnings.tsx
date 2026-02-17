"use client";

import { cn } from "@/lib/utils";
import { AlertTriangle, TrendingUp, FileWarning } from "lucide-react";

// ─── Data Shape ─────────────────────────────────────────────────────

interface QualityOfEarningsData {
  accrual_ratio: number | null;
  operating_cf_to_net_income: number | null;
  revenue_quality: Record<string, unknown>;
  expense_quality: Record<string, unknown>;
  one_time_items: string[];
  accounting_red_flags: string[];
  cash_flow_quality_score: number | null; // 1-10
  earnings_sustainability: string;
  footnote_concerns: string[];
}

// ─── Props ──────────────────────────────────────────────────────────

interface QualityOfEarningsProps {
  data: Record<string, unknown>;
}

// ─── Helpers ────────────────────────────────────────────────────────

function scoreColor(score: number | null): string {
  if (score == null) return "text-text-tertiary";
  if (score >= 8) return "text-emerald-400";
  if (score >= 5) return "text-amber-400";
  return "text-red-400";
}

function scoreBg(score: number | null): string {
  if (score == null) return "bg-white/5";
  if (score >= 8) return "bg-emerald-500/10";
  if (score >= 5) return "bg-amber-500/10";
  return "bg-red-500/10";
}

function scoreBorder(score: number | null): string {
  if (score == null) return "border-border";
  if (score >= 8) return "border-emerald-500/30";
  if (score >= 5) return "border-amber-500/30";
  return "border-red-500/30";
}

function cfNiColor(ratio: number | null): string {
  if (ratio == null) return "text-text-tertiary";
  return ratio >= 1.0 ? "text-emerald-400" : "text-red-400";
}

function cfNiBg(ratio: number | null): string {
  if (ratio == null) return "bg-white/5 border-border";
  return ratio >= 1.0
    ? "bg-emerald-500/10 border-emerald-500/30"
    : "bg-red-500/10 border-red-500/30";
}

function formatKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(value: unknown): string {
  if (value == null) return "N/A";
  if (typeof value === "number") {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value);
}

function formatRatio(value: number | null): string {
  if (value == null) return "N/A";
  return value.toFixed(2);
}

// ─── Component ──────────────────────────────────────────────────────

export default function QualityOfEarnings({ data }: QualityOfEarningsProps) {
  const d = data as unknown as QualityOfEarningsData;

  return (
    <div className="space-y-4">
      {/* Cash Flow Quality Score Banner */}
      <div
        className={cn(
          "rounded-xl border px-6 py-5 flex items-center gap-4",
          scoreBg(d.cash_flow_quality_score),
          scoreBorder(d.cash_flow_quality_score)
        )}
      >
        <TrendingUp size={24} className={scoreColor(d.cash_flow_quality_score)} />
        <div className="flex-1">
          <p className="text-xs text-text-secondary mb-1">Cash Flow Quality Score</p>
          <div className="flex items-baseline gap-1">
            <span
              className={cn(
                "text-3xl font-bold font-mono",
                scoreColor(d.cash_flow_quality_score)
              )}
            >
              {d.cash_flow_quality_score != null
                ? d.cash_flow_quality_score
                : "N/A"}
            </span>
            {d.cash_flow_quality_score != null && (
              <span className="text-sm text-text-secondary">/10</span>
            )}
          </div>
        </div>
      </div>

      {/* Key Ratios */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-3">Key Ratios</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Accrual Ratio */}
          <div className="bg-white/5 rounded-lg px-3 py-2 border border-border">
            <p className="text-xs text-text-secondary">Accrual Ratio</p>
            <p className="text-lg font-mono font-medium text-text-primary">
              {formatRatio(d.accrual_ratio)}
            </p>
            <p className="text-[11px] text-text-tertiary mt-0.5">
              Lower is better (closer to cash earnings)
            </p>
          </div>

          {/* Operating CF / Net Income */}
          <div
            className={cn(
              "rounded-lg px-3 py-2 border",
              cfNiBg(d.operating_cf_to_net_income)
            )}
          >
            <p className="text-xs text-text-secondary">Operating CF / Net Income</p>
            <p
              className={cn(
                "text-lg font-mono font-medium",
                cfNiColor(d.operating_cf_to_net_income)
              )}
            >
              {formatRatio(d.operating_cf_to_net_income)}
              {d.operating_cf_to_net_income != null && "x"}
            </p>
            <p className="text-[11px] text-text-tertiary mt-0.5">
              {d.operating_cf_to_net_income != null && d.operating_cf_to_net_income >= 1.0
                ? "Good: CF exceeds reported earnings"
                : d.operating_cf_to_net_income != null
                ? "Caution: CF below reported earnings"
                : ""}
            </p>
          </div>
        </div>
      </div>

      {/* Revenue Quality */}
      {d.revenue_quality && Object.keys(d.revenue_quality).length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Revenue Quality
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(d.revenue_quality).map(([key, value]) => (
              <div key={key} className="bg-white/5 rounded-lg px-3 py-2">
                <p className="text-xs text-text-secondary">{formatKey(key)}</p>
                <p className="text-sm font-mono text-text-primary">
                  {formatValue(value)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Expense Quality */}
      {d.expense_quality && Object.keys(d.expense_quality).length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Expense Quality
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(d.expense_quality).map(([key, value]) => (
              <div key={key} className="bg-white/5 rounded-lg px-3 py-2">
                <p className="text-xs text-text-secondary">{formatKey(key)}</p>
                <p className="text-sm font-mono text-text-primary">
                  {formatValue(value)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* One-Time Items */}
      {d.one_time_items && d.one_time_items.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            One-Time Items ({d.one_time_items.length})
          </h3>
          <ul className="space-y-2">
            {d.one_time_items.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <span className="text-text-tertiary mt-0.5 flex-shrink-0">
                  &#x2022;
                </span>
                <span className="text-text-primary">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Accounting Red Flags */}
      {d.accounting_red_flags && d.accounting_red_flags.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Accounting Red Flags ({d.accounting_red_flags.length})
          </h3>
          <ul className="space-y-2">
            {d.accounting_red_flags.map((flag, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <AlertTriangle
                  size={14}
                  className="text-red-500 mt-0.5 flex-shrink-0"
                />
                <span className="text-red-300">{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Earnings Sustainability */}
      {d.earnings_sustainability && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Earnings Sustainability
          </h3>
          <p className="text-sm text-text-primary leading-relaxed">
            {d.earnings_sustainability}
          </p>
        </div>
      )}

      {/* Footnote Concerns */}
      {d.footnote_concerns && d.footnote_concerns.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <FileWarning size={14} className="text-amber-500" />
            Footnote Concerns ({d.footnote_concerns.length})
          </h3>
          <ul className="space-y-2">
            {d.footnote_concerns.map((concern, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <span className="text-amber-400 mt-0.5 flex-shrink-0">
                  &#x2022;
                </span>
                <span className="text-text-primary">{concern}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
