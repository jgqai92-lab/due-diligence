"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { getBottlenecks } from "@/lib/api/ist";
import type { Bottleneck, BottleneckMapResponse } from "@/types/ist";
import { AlertCircle, Loader2, Clock, Zap, TrendingUp, Layers } from "lucide-react";

// ─── Phase Config ───────────────────────────────────────────────────

const PHASE_CONFIG: Record<
  number,
  { label: string; timeframe: string; color: string; bg: string; icon: typeof Clock }
> = {
  1: {
    label: "Phase 1",
    timeframe: "Near-term (0-18mo)",
    color: "text-sky-400",
    bg: "bg-sky-500/10",
    icon: Clock,
  },
  2: {
    label: "Phase 2",
    timeframe: "Mid-term (18-36mo)",
    color: "text-violet-400",
    bg: "bg-violet-500/10",
    icon: TrendingUp,
  },
  3: {
    label: "Phase 3",
    timeframe: "Secular (3+ years)",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    icon: Zap,
  },
  0: {
    label: "Cross-cutting",
    timeframe: "All phases",
    color: "text-text-secondary",
    bg: "bg-white/10",
    icon: Layers,
  },
};

// ─── Skeleton Card ──────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-4 space-y-3">
      <div className="h-4 w-40 bg-white/10 rounded animate-pulse" />
      <div className="h-3 w-full bg-white/10 rounded animate-pulse" />
      <div className="h-3 w-3/4 bg-white/10 rounded animate-pulse" />
      <div className="flex gap-2">
        <div className="h-5 w-20 bg-white/10 rounded-full animate-pulse" />
        <div className="h-5 w-16 bg-white/10 rounded-full animate-pulse" />
      </div>
    </div>
  );
}

// ─── Bottleneck Card ────────────────────────────────────────────────

function BottleneckCard({ bottleneck }: { bottleneck: Bottleneck }) {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-4 hover:bg-white/5 transition-colors duration-200">
      <h4 className="text-sm font-semibold text-text-primary mb-1.5">
        {bottleneck.name}
      </h4>
      <p className="text-xs text-text-secondary leading-relaxed mb-3">
        {bottleneck.description}
      </p>

      {/* Badges */}
      <div className="flex flex-wrap gap-1.5">
        {bottleneck.quantitativeEvidence && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono bg-violet-500/10 text-violet-400">
            {bottleneck.quantitativeEvidence}
          </span>
        )}
        {bottleneck.temporalMarker && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-sky-500/10 text-sky-400">
            {bottleneck.temporalMarker}
          </span>
        )}
      </div>

      {/* Resolution trigger */}
      {bottleneck.resolutionTrigger && (
        <div className="mt-3 pt-2.5 border-t border-border">
          <p className="text-[11px] text-text-secondary">
            <span className="font-medium text-text-secondary">Resolution:</span>{" "}
            {bottleneck.resolutionTrigger}
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Phase Section ──────────────────────────────────────────────────

function PhaseSection({
  phase,
  bottlenecks,
  isLast,
}: {
  phase: number;
  bottlenecks: Bottleneck[];
  isLast: boolean;
}) {
  const config = PHASE_CONFIG[phase] ?? PHASE_CONFIG[0];
  const PhaseIcon = config.icon;

  return (
    <div className="relative">
      {/* Connecting line (not on last phase) */}
      {!isLast && (
        <div
          className="absolute left-5 top-[52px] bottom-0 w-px bg-border"
          aria-hidden="true"
        />
      )}

      {/* Phase header */}
      <div className="flex items-center gap-3 mb-3">
        <div
          className={cn(
            "w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 relative z-10",
            config.bg
          )}
        >
          <PhaseIcon size={18} className={config.color} />
        </div>
        <div>
          <h3 className={cn("text-sm font-semibold", config.color)}>
            {config.label}
          </h3>
          <p className="text-xs text-text-secondary">{config.timeframe}</p>
        </div>
        <span className="ml-auto inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-white/10 text-text-secondary">
          {bottlenecks.length} bottleneck{bottlenecks.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Bottleneck cards grid */}
      <div className="ml-[52px] grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
        {bottlenecks.map((b) => (
          <BottleneckCard key={b.id} bottleneck={b} />
        ))}
      </div>
    </div>
  );
}

// ─── Props ──────────────────────────────────────────────────────────

interface BottleneckMapProps {
  screenId: number;
}

// ─── Component ──────────────────────────────────────────────────────

export default function BottleneckMap({ screenId }: BottleneckMapProps) {
  const [data, setData] = useState<BottleneckMapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getBottlenecks(screenId);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load bottlenecks");
    } finally {
      setLoading(false);
    }
  }, [screenId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ─── Loading State ────────────────────────────────────────────

  if (loading) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="h-5 w-40 bg-white/10 rounded animate-pulse" />
          <div className="flex gap-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-6 w-16 bg-white/10 rounded-full animate-pulse" />
            ))}
          </div>
        </div>
        <div className="space-y-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white/10 rounded-full animate-pulse" />
                <div className="h-4 w-32 bg-white/10 rounded animate-pulse" />
              </div>
              <div className="ml-[52px] grid grid-cols-1 md:grid-cols-2 gap-3">
                <SkeletonCard />
                <SkeletonCard />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
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

  if (!data || data.bottlenecks.length === 0) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <Loader2 size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">No bottlenecks mapped yet</p>
        <p className="text-xs text-text-secondary mt-1">
          Bottlenecks will appear here once the analysis phase completes.
        </p>
      </div>
    );
  }

  // ─── Group bottlenecks by phase ───────────────────────────────

  const grouped: Record<number, Bottleneck[]> = {};
  for (const b of data.bottlenecks) {
    const phase = b.phase;
    if (!grouped[phase]) grouped[phase] = [];
    grouped[phase].push(b);
  }

  // Sort phases: 1, 2, 3, then 0 (cross-cutting)
  const phaseOrder = [1, 2, 3, 0].filter((p) => grouped[p]?.length > 0);

  // ─── Render ───────────────────────────────────────────────────

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
      {/* Header + phase count summary */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-3">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Bottleneck Map</h3>
          <p className="text-xs text-text-secondary mt-0.5">
            {data.bottlenecks.length} bottleneck{data.bottlenecks.length !== 1 ? "s" : ""} across the temporal cascade
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {data.phaseCount.phase1 > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-sky-500/10 text-sky-400">
              P1: {data.phaseCount.phase1}
            </span>
          )}
          {data.phaseCount.phase2 > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-violet-500/10 text-violet-400">
              P2: {data.phaseCount.phase2}
            </span>
          )}
          {data.phaseCount.phase3 > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400">
              P3: {data.phaseCount.phase3}
            </span>
          )}
          {data.phaseCount.crossCutting > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-white/10 text-text-secondary">
              Cross: {data.phaseCount.crossCutting}
            </span>
          )}
        </div>
      </div>

      {/* Temporal cascade */}
      <div className="space-y-2" role="list" aria-label="Bottleneck phases">
        {phaseOrder.map((phase, idx) => (
          <PhaseSection
            key={phase}
            phase={phase}
            bottlenecks={grouped[phase]}
            isLast={idx === phaseOrder.length - 1}
          />
        ))}
      </div>
    </div>
  );
}
