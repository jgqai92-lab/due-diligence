"use client";

import { cn } from "@/lib/utils";
import { BarChart3, AlertTriangle, TrendingUp, ShieldCheck, ShieldAlert } from "lucide-react";

/* ── Data shape from FinancialAnalysisResult (Template 05) ────────── */

interface DuPontDecomposition {
  roe: number | null;
  net_margin: number | null;
  asset_turnover: number | null;
  equity_multiplier: number | null;
  tax_burden: number | null;
  interest_burden: number | null;
  operating_margin: number | null;
  interpretation: string;
}

interface FinancialAnalysisData {
  dupont: DuPontDecomposition;
  profitability: Record<string, unknown>;
  leverage: Record<string, unknown>;
  liquidity: Record<string, unknown>;
  efficiency: Record<string, unknown>;
  cash_flow_quality: Record<string, unknown>;
  growth_metrics: Record<string, unknown>;
  altman_z_score: Record<string, unknown> | null;
  beneish_m_score: Record<string, unknown> | null;
  key_trends: string[];
  red_flags: string[];
}

interface FinancialAnalysisProps {
  data: Record<string, unknown>;
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatMetric(val: unknown): string {
  if (val == null) return "N/A";
  if (typeof val === "number") {
    // If value looks like a ratio or percentage (small number between -5 and 5 exclusive)
    if (Math.abs(val) < 5 && val !== 0) {
      return (val * 100).toFixed(2) + "%";
    }
    return val.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(val);
}

function formatPct(val: number | null): string {
  if (val == null) return "N/A";
  return (val * 100).toFixed(2) + "%";
}

function formatRatio(val: number | null): string {
  if (val == null) return "N/A";
  return val.toFixed(2) + "x";
}

/* ── Ratio grid for a category of key-value pairs ─────────────────── */
function RatioGrid({ title, data }: { title: string; data: Record<string, unknown> | null | undefined }) {
  if (!data || Object.keys(data).length === 0) return null;
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-3">{title}</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {Object.entries(data).map(([key, value]) => (
          <div key={key} className="bg-white/5 rounded-lg px-3 py-2">
            <p className="text-xs text-text-secondary">{humanizeKey(key)}</p>
            <p className="text-sm font-mono text-text-primary">{formatMetric(value)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Z-Score / M-Score card ───────────────────────────────────────── */
function ScoreCard({
  title,
  data,
  colorFn,
  icon: Icon,
}: {
  title: string;
  data: Record<string, unknown> | null;
  colorFn: (score: number) => { bg: string; text: string; label: string };
  icon: typeof ShieldCheck;
}) {
  if (!data) return null;

  const scoreVal = (data.score ?? data.composite ?? data.value) as number | null;
  const interpretation = data.interpretation ?? data.zone ?? data.label;
  const colors = scoreVal != null ? colorFn(scoreVal) : { bg: "bg-white/5", text: "text-text-primary", label: "N/A" };

  return (
    <div className={cn("rounded-xl border px-5 py-4", colors.bg, `border-${colors.text.replace("text-", "")}/20`)}>
      <div className="flex items-center gap-3 mb-2">
        <Icon size={20} className={colors.text} />
        <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
      </div>
      <div className="flex items-baseline gap-3">
        <span className={cn("text-2xl font-bold font-mono", colors.text)}>
          {scoreVal != null ? scoreVal.toFixed(2) : "N/A"}
        </span>
        <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full", colors.bg, colors.text)}>
          {colors.label}
        </span>
      </div>
      {typeof interpretation === "string" && interpretation && (
        <p className="text-xs text-text-secondary mt-2">{interpretation}</p>
      )}
    </div>
  );
}

export default function FinancialAnalysis({ data }: FinancialAnalysisProps) {
  const d = data as unknown as FinancialAnalysisData;

  if (!d || (!d.dupont && !d.profitability)) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 text-center py-12 text-text-tertiary">
        <BarChart3 size={32} className="mx-auto mb-3" />
        <p className="text-sm">Financial analysis not yet available.</p>
      </div>
    );
  }

  const dupont = d.dupont;

  return (
    <div className="space-y-4">
      {/* DuPont Decomposition */}
      {dupont && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-4">DuPont Decomposition</h3>

          {/* 3-factor visual breakdown */}
          <div className="flex flex-wrap items-center justify-center gap-2 mb-4">
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg px-4 py-3 text-center min-w-[100px]">
              <p className="text-xs text-blue-400 mb-0.5">ROE</p>
              <p className="text-xl font-bold font-mono text-blue-300">{formatPct(dupont.roe)}</p>
            </div>
            <span className="text-text-tertiary text-lg font-light">=</span>
            <div className="bg-white/5 rounded-lg px-4 py-3 text-center min-w-[100px]">
              <p className="text-xs text-text-secondary mb-0.5">Net Margin</p>
              <p className="text-lg font-bold font-mono text-text-primary">{formatPct(dupont.net_margin)}</p>
            </div>
            <span className="text-text-tertiary text-lg font-light">&times;</span>
            <div className="bg-white/5 rounded-lg px-4 py-3 text-center min-w-[100px]">
              <p className="text-xs text-text-secondary mb-0.5">Asset Turnover</p>
              <p className="text-lg font-bold font-mono text-text-primary">{formatRatio(dupont.asset_turnover)}</p>
            </div>
            <span className="text-text-tertiary text-lg font-light">&times;</span>
            <div className="bg-white/5 rounded-lg px-4 py-3 text-center min-w-[100px]">
              <p className="text-xs text-text-secondary mb-0.5">Equity Multiplier</p>
              <p className="text-lg font-bold font-mono text-text-primary">{formatRatio(dupont.equity_multiplier)}</p>
            </div>
          </div>

          {/* 5-factor components */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <div className="bg-white/5 rounded-lg px-3 py-2">
              <p className="text-xs text-text-secondary">Tax Burden</p>
              <p className="text-sm font-mono text-text-primary">{formatPct(dupont.tax_burden)}</p>
            </div>
            <div className="bg-white/5 rounded-lg px-3 py-2">
              <p className="text-xs text-text-secondary">Interest Burden</p>
              <p className="text-sm font-mono text-text-primary">{formatPct(dupont.interest_burden)}</p>
            </div>
            <div className="bg-white/5 rounded-lg px-3 py-2">
              <p className="text-xs text-text-secondary">Operating Margin</p>
              <p className="text-sm font-mono text-text-primary">{formatPct(dupont.operating_margin)}</p>
            </div>
          </div>

          {/* DuPont interpretation */}
          {dupont.interpretation && (
            <p className="text-sm text-text-primary leading-relaxed bg-blue-500/10 border border-blue-500/30 rounded-lg px-4 py-3">
              {dupont.interpretation}
            </p>
          )}
        </div>
      )}

      {/* Ratio tables */}
      <RatioGrid title="Profitability" data={d.profitability} />
      <RatioGrid title="Leverage" data={d.leverage} />
      <RatioGrid title="Liquidity" data={d.liquidity} />
      <RatioGrid title="Efficiency" data={d.efficiency} />
      <RatioGrid title="Cash Flow Quality" data={d.cash_flow_quality} />
      <RatioGrid title="Growth Metrics" data={d.growth_metrics} />

      {/* Altman Z-Score & Beneish M-Score */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ScoreCard
          title="Altman Z-Score"
          data={d.altman_z_score}
          icon={ShieldCheck}
          colorFn={(score) => {
            if (score > 2.99) return { bg: "bg-emerald-500/10", text: "text-emerald-300", label: "Safe Zone" };
            if (score >= 1.81) return { bg: "bg-amber-500/10", text: "text-amber-300", label: "Gray Zone" };
            return { bg: "bg-red-500/10", text: "text-red-300", label: "Distress Zone" };
          }}
        />
        <ScoreCard
          title="Beneish M-Score"
          data={d.beneish_m_score}
          icon={ShieldAlert}
          colorFn={(score) => {
            if (score < -2.22) return { bg: "bg-emerald-500/10", text: "text-emerald-300", label: "Low Manipulation Risk" };
            return { bg: "bg-red-500/10", text: "text-red-300", label: "High Manipulation Risk" };
          }}
        />
      </div>

      {/* Key Trends */}
      {d.key_trends?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            <span className="inline-flex items-center gap-1.5">
              <TrendingUp size={14} className="text-text-tertiary" />
              Key Trends
            </span>
          </h3>
          <ul className="space-y-2">
            {d.key_trends.map((trend, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-text-primary">
                <span className="text-text-tertiary mt-0.5 flex-shrink-0">&#8226;</span>
                <span>{trend}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Red Flags */}
      {d.red_flags?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-red-500/30 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-red-300 mb-3">
            <span className="inline-flex items-center gap-1.5">
              <AlertTriangle size={14} className="text-red-500" />
              Red Flags ({d.red_flags.length})
            </span>
          </h3>
          <ul className="space-y-2">
            {d.red_flags.map((flag, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-text-primary">
                <AlertTriangle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
                <span>{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
