"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { cn } from "@/lib/utils";
import { formatLargeNumber } from "@/lib/utils";
import { getMasterScreen } from "@/lib/api/ist";
import type { MasterScreenResponse, RankedEquity } from "@/types/ist";
import {
  AlertCircle,
  Loader2,
  Trophy,
  ShieldCheck,
  ShieldAlert,
  ArrowUpDown,
} from "lucide-react";

// ─── Tier Config ──────────────────────────────────────────────────

const TIER_CONFIG: Record<number, { bg: string; text: string; label: string }> = {
  1: { bg: "bg-emerald-500/10", text: "text-emerald-400", label: "Tier 1" },
  2: { bg: "bg-amber-500/10", text: "text-amber-400", label: "Tier 2" },
  3: { bg: "bg-white/10", text: "text-text-secondary", label: "Tier 3" },
};

// ─── Sort Config ──────────────────────────────────────────────────

type SortKey = "rank" | "ticker" | "tier" | "scarcityScore" | "convictionScore";

// ─── Conviction Progress Bar ──────────────────────────────────────

function ConvictionBar({ score }: { score: number }) {
  const pct = Math.min(Math.max(score, 0), 100);
  const color =
    pct >= 70 ? "bg-emerald-500" :
    pct >= 40 ? "bg-amber-500" :
    "bg-red-400";

  return (
    <div className="flex items-center gap-2">
      <div
        className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden max-w-[80px]"
        aria-hidden="true"
      >
        <div
          className={cn("h-full rounded-full transition-all duration-300", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-text-secondary w-8 text-right">
        {pct}
      </span>
    </div>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr>
      <td className="px-3 py-3"><div className="h-4 w-8 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-14 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-32 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-5 w-14 bg-white/10 rounded-full animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-12 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-24 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-20 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-24 bg-white/10 rounded animate-pulse" /></td>
    </tr>
  );
}

// ─── Props ────────────────────────────────────────────────────────

interface MasterScreenTableProps {
  screenId: number;
}

// ─── Component ────────────────────────────────────────────────────

export default function MasterScreenTable({ screenId }: MasterScreenTableProps) {
  const [data, setData] = useState<MasterScreenResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [sortAsc, setSortAsc] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getMasterScreen(screenId);
      setData(result);
    } catch (err) {
      if ((err as any).status === 404) {
        setData(null);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load master screen");
      }
    } finally {
      setLoading(false);
    }
  }, [screenId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Sort logic
  const handleSort = useCallback((key: SortKey) => {
    setSortKey((prev) => {
      if (prev === key) {
        setSortAsc((a) => !a);
        return key;
      }
      // defaults: rank asc, ticker asc, others desc
      setSortAsc(key === "rank" || key === "ticker");
      return key;
    });
  }, []);

  const sortedEquities = useMemo(() => {
    if (!data) return [];
    const sorted = [...data.rankedEquities];
    sorted.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "rank":
          cmp = a.rank - b.rank;
          break;
        case "ticker":
          cmp = a.ticker.localeCompare(b.ticker);
          break;
        case "tier":
          cmp = a.tier - b.tier;
          break;
        case "scarcityScore":
          cmp = a.scarcityScore - b.scarcityScore;
          break;
        case "convictionScore":
          cmp = a.convictionScore - b.convictionScore;
          break;
      }
      return sortAsc ? cmp : -cmp;
    });
    return sorted;
  }, [data, sortKey, sortAsc]);

  // ─── Loading State ──────────────────────────────────────────────

  if (loading) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="h-5 w-40 bg-white/10 rounded animate-pulse" />
          <div className="flex gap-2">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="h-6 w-20 bg-white/10 rounded-full animate-pulse" />
            ))}
          </div>
        </div>
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-white/5 border-b border-border">
                {["Rank", "Ticker", "Company", "Tier", "Scarcity", "Conviction", "Pillar", "Catalyst"].map((h) => (
                  <th key={h} className="px-3 py-2.5">
                    <div className="h-3 w-16 bg-white/10 rounded animate-pulse" />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonRow key={i} />
              ))}
            </tbody>
          </table>
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

  if (!data || data.rankedEquities.length === 0) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <Loader2 size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">No ranked equities yet</p>
        <p className="text-xs text-text-secondary mt-1">
          The master screen will appear here once the synthesis phase completes.
        </p>
      </div>
    );
  }

  // ─── Sort Header Helper ─────────────────────────────────────────

  function SortHeader({ label, sortKeyVal }: { label: string; sortKeyVal: SortKey }) {
    const isActive = sortKey === sortKeyVal;
    return (
      <button
        onClick={() => handleSort(sortKeyVal)}
        className={cn(
          "inline-flex items-center gap-1 text-[11px] font-medium transition-colors duration-200",
          isActive ? "text-primary" : "text-text-secondary hover:text-text-primary"
        )}
        aria-label={`Sort by ${label}`}
      >
        {label}
        <ArrowUpDown size={10} className={isActive ? "text-primary" : "text-text-tertiary"} />
      </button>
    );
  }

  // ─── Render ───────────────────────────────────────────────────

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-5 gap-3">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Master Screen</h3>
          <p className="text-xs text-text-secondary mt-0.5">
            {data.totalEquities} ranked equit{data.totalEquities !== 1 ? "ies" : "y"} --
            {" "}{data.tier1Count} Tier 1
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Tier 1 count badge */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400">
            <Trophy size={12} />
            {data.tier1Count} Tier 1
          </span>

          {/* Invariant compliance badge */}
          {data.invariantCompliance.allPassed ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <ShieldCheck size={12} />
              Compliant
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/30">
              <ShieldAlert size={12} />
              Violations
            </span>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left" role="table">
          <thead>
            <tr className="bg-white/5 border-b border-border">
              <th className="px-3 py-2.5" scope="col">
                <SortHeader label="Rank" sortKeyVal="rank" />
              </th>
              <th className="px-3 py-2.5" scope="col">
                <SortHeader label="Ticker" sortKeyVal="ticker" />
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Company
              </th>
              <th className="px-3 py-2.5" scope="col">
                <SortHeader label="Tier" sortKeyVal="tier" />
              </th>
              <th className="px-3 py-2.5" scope="col">
                <SortHeader label="Scarcity" sortKeyVal="scarcityScore" />
              </th>
              <th className="px-3 py-2.5" scope="col">
                <SortHeader label="Conviction" sortKeyVal="convictionScore" />
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Pillar
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Catalyst
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedEquities.map((eq) => {
              const tierCfg = TIER_CONFIG[eq.tier] ?? TIER_CONFIG[3];

              return (
                <tr
                  key={`${eq.rank}-${eq.ticker}`}
                  className="border-b border-border hover:bg-white/5 transition-colors duration-150"
                >
                  <td className="px-3 py-3">
                    <span className="text-xs font-mono font-bold text-text-tertiary">
                      #{eq.rank}
                    </span>
                  </td>
                  <td className="px-3 py-3">
                    <span className="text-xs font-bold font-mono text-text-primary">
                      {eq.ticker}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-xs text-text-primary">
                    {eq.companyName}
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={cn(
                        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
                        tierCfg.bg,
                        tierCfg.text
                      )}
                    >
                      {tierCfg.label}
                    </span>
                  </td>
                  <td className="px-3 py-3">
                    <span className="text-xs font-mono text-text-primary">
                      {eq.scarcityScore.toFixed(1)}
                    </span>
                  </td>
                  <td className="px-3 py-3">
                    <ConvictionBar score={eq.convictionScore} />
                  </td>
                  <td className="px-3 py-3">
                    <span className="text-xs text-text-secondary">
                      {eq.pillar}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-xs text-text-secondary max-w-[200px] truncate" title={eq.catalyst ?? undefined}>
                    {eq.catalyst ?? "\u2014"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
