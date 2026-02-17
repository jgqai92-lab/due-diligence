"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { getInvariants } from "@/lib/api/hfrt";
import type { HFRTInvariantResult, HFRTInvariantsResponse } from "@/types/hfrt";
import {
  AlertCircle,
  Loader2,
  CheckCircle,
  XCircle,
  ShieldCheck,
  ShieldAlert,
} from "lucide-react";

// ─── Skeleton ───────────────────────────────────────────────────────

function SkeletonInvariantItem() {
  return (
    <div className="flex items-start gap-3 py-3 px-4">
      <div className="w-5 h-5 bg-white/10 rounded-full animate-pulse flex-shrink-0" />
      <div className="flex-1 space-y-1.5">
        <div className="flex items-center gap-2">
          <div className="h-3 w-12 bg-white/10 rounded animate-pulse" />
          <div className="h-3 w-40 bg-white/10 rounded animate-pulse" />
        </div>
        <div className="h-3 w-full bg-white/10 rounded animate-pulse" />
      </div>
    </div>
  );
}

// ─── Invariant Item ─────────────────────────────────────────────────

function InvariantItem({ invariant }: { invariant: HFRTInvariantResult }) {
  const isPassed = invariant.status === "PASS";

  return (
    <div
      className={cn(
        "flex items-start gap-3 py-3 px-4 rounded-lg transition-colors duration-150",
        isPassed ? "hover:bg-emerald-500/5" : "hover:bg-red-500/10 bg-red-500/5"
      )}
    >
      {/* Status icon */}
      {isPassed ? (
        <CheckCircle size={18} className="text-emerald-500 flex-shrink-0 mt-0.5" aria-label="Passed" />
      ) : (
        <XCircle size={18} className="text-red-500 flex-shrink-0 mt-0.5" aria-label="Failed" />
      )}

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-xs font-mono font-medium text-text-secondary">
            {invariant.id}
          </span>
          <span className={cn(
            "text-xs font-medium",
            isPassed ? "text-text-primary" : "text-red-300"
          )}>
            {invariant.name}
          </span>
        </div>
        <p className={cn(
          "text-[11px] leading-relaxed",
          isPassed ? "text-text-secondary" : "text-red-400"
        )}>
          {invariant.details}
        </p>
      </div>
    </div>
  );
}

// ─── Props ──────────────────────────────────────────────────────────

interface InvariantChecklistProps {
  projectId: number;
}

// ─── Component ──────────────────────────────────────────────────────

export default function InvariantChecklist({ projectId }: InvariantChecklistProps) {
  const [data, setData] = useState<HFRTInvariantsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getInvariants(projectId);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load invariants");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ─── Loading State ────────────────────────────────────────────

  if (loading) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-1">
        <div className="flex items-center justify-between mb-4">
          <div className="h-5 w-40 bg-white/10 rounded animate-pulse" />
          <div className="h-7 w-48 bg-white/10 rounded-full animate-pulse" />
        </div>
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonInvariantItem key={i} />
        ))}
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

  if (!data || data.invariants.length === 0) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <Loader2 size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">No invariant checks yet</p>
        <p className="text-xs text-text-secondary mt-1">
          Invariant checks will appear here once the synthesis phase completes.
        </p>
      </div>
    );
  }

  // ─── Render ───────────────────────────────────────────────────

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
      {/* Header + status banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-5 gap-3">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Invariant Checks</h3>
          <p className="text-xs text-text-secondary mt-0.5">
            Quality gates for research integrity
          </p>
        </div>

        {/* Overall status banner */}
        {data.allPassed ? (
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30">
            <ShieldCheck size={16} className="text-emerald-400" />
            <span className="text-xs font-medium text-emerald-300">
              All {data.passCount} Invariant{data.passCount !== 1 ? "s" : ""} Passed
            </span>
          </div>
        ) : (
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/10 border border-red-500/30">
            <ShieldAlert size={16} className="text-red-400" />
            <span className="text-xs font-medium text-red-300">
              {data.failCount} Invariant{data.failCount !== 1 ? "s" : ""} Failed
            </span>
          </div>
        )}
      </div>

      {/* Invariant list */}
      <div className="divide-y divide-border" role="list" aria-label="Invariant checks">
        {data.invariants.map((invariant) => (
          <div key={invariant.id} role="listitem">
            <InvariantItem invariant={invariant} />
          </div>
        ))}
      </div>
    </div>
  );
}
