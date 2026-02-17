"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { getRotation } from "@/lib/api/ist";
import type { RotationResponse, PhaseAllocation, RotationTrigger } from "@/types/ist";
import {
  AlertCircle,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";

// ─── Phase Colors ────────────────────────────────────────────────

const PHASE_COLORS: Record<number, { bg: string; text: string; bar: string; border: string }> = {
  1: { bg: "bg-sky-500/10", text: "text-sky-400", bar: "bg-sky-500", border: "border-sky-500/30" },
  2: { bg: "bg-violet-500/10", text: "text-violet-400", bar: "bg-violet-500", border: "border-violet-500/30" },
  3: { bg: "bg-emerald-500/10", text: "text-emerald-400", bar: "bg-emerald-500", border: "border-emerald-500/30" },
  4: { bg: "bg-amber-500/10", text: "text-amber-400", bar: "bg-amber-500", border: "border-amber-500/30" },
  5: { bg: "bg-rose-500/10", text: "text-rose-400", bar: "bg-rose-500", border: "border-rose-500/30" },
};

function getPhaseColor(phase: number) {
  return PHASE_COLORS[phase] ?? PHASE_COLORS[1];
}

// ─── Allocation Bar ──────────────────────────────────────────────

function AllocationBar({ phases }: { phases: PhaseAllocation[] }) {
  return (
    <div className="mb-6">
      <p className="text-[11px] font-medium text-text-secondary mb-2">Portfolio Allocation</p>
      <div className="flex h-6 rounded-full overflow-hidden bg-white/10" role="img" aria-label="Portfolio allocation bar">
        {phases.map((phase) => {
          const colors = getPhaseColor(phase.phase);
          const widthPct = Math.max(phase.allocationPercent, 2); // minimum 2% for visibility
          return (
            <div
              key={phase.phase}
              className={cn("flex items-center justify-center transition-all duration-300", colors.bar)}
              style={{ width: `${widthPct}%` }}
              title={`${phase.phaseLabel}: ${phase.allocationPercent}%`}
            >
              {phase.allocationPercent >= 10 && (
                <span className="text-[10px] font-medium text-white">
                  {phase.allocationPercent}%
                </span>
              )}
            </div>
          );
        })}
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-2">
        {phases.map((phase) => {
          const colors = getPhaseColor(phase.phase);
          return (
            <div key={phase.phase} className="flex items-center gap-1.5">
              <div className={cn("w-2.5 h-2.5 rounded-full", colors.bar)} />
              <span className="text-[10px] text-text-secondary">
                {phase.phaseLabel} ({phase.allocationPercent}%)
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Phase Allocation Card ──────────────────────────────────────

function PhaseCard({ allocation }: { allocation: PhaseAllocation }) {
  const colors = getPhaseColor(allocation.phase);

  return (
    <div
      className={cn(
        "bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5",
        "hover:bg-white/5 transition-colors duration-200",
        colors.border
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
              colors.bg,
              colors.text
            )}
          >
            Phase {allocation.phase}
          </span>
          <span className="text-xs font-medium text-text-primary">
            {allocation.phaseLabel}
          </span>
        </div>
        <span className={cn("text-lg font-bold font-mono", colors.text)}>
          {allocation.allocationPercent}%
        </span>
      </div>

      {/* Tickers */}
      {allocation.tickers.length > 0 && (
        <div className="mb-3">
          <p className="text-[11px] font-medium text-text-secondary mb-1.5">Tickers</p>
          <div className="flex flex-wrap gap-1.5">
            {allocation.tickers.map((ticker) => (
              <span
                key={ticker}
                className="inline-flex items-center px-2 py-0.5 rounded bg-white/10 text-xs font-mono font-medium text-text-primary"
              >
                {ticker}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Rationale */}
      <p className="text-xs text-text-secondary leading-relaxed">
        {allocation.rationale}
      </p>
    </div>
  );
}

// ─── Rotation Triggers Table ────────────────────────────────────

function TriggersTable({ triggers }: { triggers: RotationTrigger[] }) {
  if (triggers.length === 0) return null;

  return (
    <div className="mb-6">
      <p className="text-[11px] font-medium text-text-secondary mb-2">Rotation Triggers</p>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left" role="table">
          <thead>
            <tr className="bg-white/5 border-b border-border">
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Trigger
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Action
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Monitor Metric
              </th>
            </tr>
          </thead>
          <tbody>
            {triggers.map((trigger, idx) => (
              <tr
                key={idx}
                className={cn(
                  "border-b border-border",
                  idx % 2 === 1 && "bg-white/5"
                )}
              >
                <td className="px-3 py-2 text-xs text-text-primary leading-relaxed">
                  {trigger.trigger}
                </td>
                <td className="px-3 py-2 text-xs text-text-primary leading-relaxed">
                  {trigger.action}
                </td>
                <td className="px-3 py-2">
                  <span className="inline-flex items-center px-2 py-0.5 rounded bg-violet-500/10 text-[11px] font-mono text-violet-400">
                    {trigger.monitorMetric}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Risk Limits ────────────────────────────────────────────────

function RiskLimits({
  limits,
}: {
  limits: RotationResponse["riskLimits"];
}) {
  return (
    <div>
      <p className="text-[11px] font-medium text-text-secondary mb-2">Risk Limits</p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="bg-white/5 rounded-lg border border-border px-4 py-3 text-center">
          <p className="text-lg font-bold font-mono text-text-primary">
            {limits.maxSingleName}%
          </p>
          <p className="text-[10px] text-text-secondary">Max Single Name</p>
        </div>
        <div className="bg-white/5 rounded-lg border border-border px-4 py-3 text-center">
          <p className="text-lg font-bold font-mono text-text-primary">
            {limits.maxSinglePillar}%
          </p>
          <p className="text-[10px] text-text-secondary">Max Single Pillar</p>
        </div>
        <div className="bg-white/5 rounded-lg border border-border px-4 py-3 text-center">
          <p className="text-lg font-bold font-mono text-text-primary">
            {limits.maxTier3Allocation}%
          </p>
          <p className="text-[10px] text-text-secondary">Max Tier 3 Allocation</p>
        </div>
      </div>
    </div>
  );
}

// ─── Skeleton ────────────────────────────────────────────────────

function RotationSkeleton() {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div className="h-5 w-40 bg-white/10 rounded animate-pulse" />
      </div>
      <div className="h-6 w-full bg-white/10 rounded-full animate-pulse" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-32 bg-white/10 rounded-xl animate-pulse" />
        ))}
      </div>
      <div className="h-24 w-full bg-white/10 rounded animate-pulse" />
      <div className="grid grid-cols-3 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-16 bg-white/10 rounded-lg animate-pulse" />
        ))}
      </div>
    </div>
  );
}

// ─── Props ──────────────────────────────────────────────────────

interface RotationStrategyProps {
  screenId: number;
}

// ─── Component ──────────────────────────────────────────────────

export default function RotationStrategy({ screenId }: RotationStrategyProps) {
  const [data, setData] = useState<RotationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getRotation(screenId);
      setData(result);
    } catch (err) {
      if ((err as any).status === 404) {
        setData(null);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load rotation strategy");
      }
    } finally {
      setLoading(false);
    }
  }, [screenId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ─── Loading State ──────────────────────────────────────────

  if (loading) {
    return <RotationSkeleton />;
  }

  // ─── Error State ──────────────────────────────────────────────

  if (error) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-8 text-center">
        <AlertCircle size={24} className="mx-auto text-red-400 mb-2" />
        <p className="text-sm text-red-400">{error}</p>
        <button
          onClick={fetchData}
          className="mt-3 text-xs font-medium text-primary hover:text-primary-hover transition-colors duration-200"
        >
          Try again
        </button>
      </div>
    );
  }

  // ─── Empty State ──────────────────────────────────────────────

  if (!data || data.phaseAllocations.length === 0) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <RefreshCw size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">No rotation strategy yet</p>
        <p className="text-xs text-text-secondary mt-1">
          The rotation strategy will appear here once the synthesis phase completes.
        </p>
      </div>
    );
  }

  // ─── Render ───────────────────────────────────────────────────

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-sm font-semibold text-text-primary">Rotation Strategy</h3>
        <p className="text-xs text-text-secondary mt-0.5">
          Phase-based allocation with rotation triggers and risk limits
        </p>
      </div>

      {/* Allocation Bar */}
      <AllocationBar phases={data.phaseAllocations} />

      {/* Phase Allocation Cards */}
      <div>
        <p className="text-[11px] font-medium text-text-secondary mb-3">Phase Allocations</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {data.phaseAllocations.map((allocation) => (
            <PhaseCard key={allocation.phase} allocation={allocation} />
          ))}
        </div>
      </div>

      {/* Rotation Triggers */}
      <TriggersTable triggers={data.rotationTriggers} />

      {/* Risk Limits */}
      <RiskLimits limits={data.riskLimits} />
    </div>
  );
}
