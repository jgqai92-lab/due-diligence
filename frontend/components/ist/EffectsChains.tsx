"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { cn } from "@/lib/utils";
import { getEffects } from "@/lib/api/ist";
import type { EffectChain, EffectsResponse } from "@/types/ist";
import { AlertCircle, Loader2, ArrowRight } from "lucide-react";

// ─── Order Config ────────────────────────────────────────────────────

const ORDER_CONFIG: Record<1 | 2 | 3, { bg: string; text: string; label: string; border: string }> = {
  1: { bg: "bg-sky-500/10", text: "text-sky-400", label: "1st", border: "border-l-sky-400" },
  2: { bg: "bg-violet-500/10", text: "text-violet-400", label: "2nd", border: "border-l-violet-400" },
  3: { bg: "bg-amber-500/10", text: "text-amber-400", label: "3rd", border: "border-l-amber-400" },
};

// ─── Skeleton ───────────────────────────────────────────────────────

function SkeletonThesisGroup() {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5 space-y-4">
      <div className="h-4 w-64 bg-white/10 rounded animate-pulse" />
      <div className="space-y-3 ml-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-start gap-3">
            <div className="h-5 w-10 bg-white/10 rounded-full animate-pulse flex-shrink-0" />
            <div className="flex-1 space-y-1.5">
              <div className="h-3 w-full bg-white/10 rounded animate-pulse" />
              <div className="h-3 w-2/3 bg-white/10 rounded animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Effect Node ────────────────────────────────────────────────────

function EffectNode({ effect, isLast }: { effect: EffectChain; isLast: boolean }) {
  const config = ORDER_CONFIG[effect.order] ?? ORDER_CONFIG[1];

  return (
    <div className="relative flex items-start gap-3">
      {/* Connecting line */}
      {!isLast && (
        <div
          className="absolute left-[18px] top-[28px] bottom-[-12px] w-px bg-white/10"
          aria-hidden="true"
        />
      )}

      {/* Order badge */}
      <div className="flex-shrink-0 relative z-10">
        <span
          className={cn(
            "inline-flex items-center justify-center w-9 h-6 rounded-full text-[10px] font-bold",
            config.bg,
            config.text
          )}
        >
          {config.label}
        </span>
      </div>

      {/* Effect content */}
      <div
        className={cn(
          "flex-1 bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-lg border-l-4 px-4 py-3",
          config.border,
          "hover:bg-white/5 transition-colors duration-200"
        )}
      >
        <p className="text-xs text-text-primary leading-relaxed">
          {effect.effectDescription}
        </p>
        {effect.equityTicker && (
          <span className="inline-flex items-center mt-2 px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-violet-500/10 text-violet-400">
            {effect.equityTicker}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Thesis Group ──────────────────────────────────────────────────

function ThesisGroup({ thesis, effects }: { thesis: string; effects: EffectChain[] }) {
  // Sort by order within the group
  const sorted = useMemo(
    () => [...effects].sort((a, b) => a.order - b.order),
    [effects]
  );

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5 hover:bg-white/5 transition-colors duration-200">
      {/* Thesis header */}
      <h4 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
        <ArrowRight size={14} className="text-primary flex-shrink-0" aria-hidden="true" />
        {thesis}
      </h4>

      {/* Effects cascade */}
      <div className="space-y-3 ml-1">
        {sorted.map((effect, idx) => (
          <EffectNode
            key={effect.id}
            effect={effect}
            isLast={idx === sorted.length - 1}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Props ──────────────────────────────────────────────────────────

interface EffectsChainsProps {
  screenId: number;
}

// ─── Component ──────────────────────────────────────────────────────

export default function EffectsChains({ screenId }: EffectsChainsProps) {
  const [data, setData] = useState<EffectsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getEffects(screenId);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load effects chains");
    } finally {
      setLoading(false);
    }
  }, [screenId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Group effects by thesis
  const groupedByThesis = useMemo(() => {
    if (!data) return new Map<string, EffectChain[]>();
    const map = new Map<string, EffectChain[]>();
    for (const effect of data.effectsChains) {
      const existing = map.get(effect.thesis);
      if (existing) {
        existing.push(effect);
      } else {
        map.set(effect.thesis, [effect]);
      }
    }
    return map;
  }, [data]);

  // ─── Loading State ────────────────────────────────────────────

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="h-5 w-40 bg-white/10 rounded animate-pulse" />
          <div className="h-5 w-24 bg-white/10 rounded animate-pulse" />
        </div>
        <SkeletonThesisGroup />
        <SkeletonThesisGroup />
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

  if (!data || data.effectsChains.length === 0) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <Loader2 size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">No effects chains yet</p>
        <p className="text-xs text-text-secondary mt-1">
          Effects chains will appear here once the scanning phase completes.
        </p>
      </div>
    );
  }

  // ─── Render ───────────────────────────────────────────────────

  const thesisKeys = Array.from(groupedByThesis.keys());

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Effects Chains</h3>
          <p className="text-xs text-text-secondary mt-0.5">
            {data.effectsChains.length} effect{data.effectsChains.length !== 1 ? "s" : ""} across{" "}
            {thesisKeys.length} thesis group{thesisKeys.length !== 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-sky-500/10 text-sky-400">
            1st Order
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-violet-500/10 text-violet-400">
            2nd Order
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 text-amber-400">
            3rd Order
          </span>
        </div>
      </div>

      {/* Thesis groups */}
      <div className="space-y-4" role="list" aria-label="Effects by thesis">
        {thesisKeys.map((thesis) => (
          <div key={thesis} role="listitem">
            <ThesisGroup
              thesis={thesis}
              effects={groupedByThesis.get(thesis)!}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
