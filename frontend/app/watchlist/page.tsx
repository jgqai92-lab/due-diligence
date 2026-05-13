"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { getWatchlist } from "@/lib/api/ist";
import type { WatchlistCandidate, WatchlistResponse, ScarcityScore } from "@/types/ist";
import {
  AlertCircle,
  Eye,
  ArrowUpDown,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

// ─── Tier / Conviction Config ──────────────────────────────────────

const TIER_CONFIG: Record<1 | 2 | 3, { bg: string; text: string; label: string }> = {
  1: { bg: "bg-emerald-500/10", text: "text-emerald-400", label: "Tier 1" },
  2: { bg: "bg-amber-500/10", text: "text-amber-400", label: "Tier 2" },
  3: { bg: "bg-white/10", text: "text-text-secondary", label: "Tier 3" },
};

const CONVICTION_CONFIG: Record<string, { bg: string; text: string }> = {
  HIGH:   { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  MEDIUM: { bg: "bg-amber-500/10", text: "text-amber-400" },
  LOW:    { bg: "bg-white/10", text: "text-text-secondary" },
};

// ─── Sort Config ───────────────────────────────────────────────────

type SortKey = "ticker" | "tier" | "conviction" | "scarcity" | "screen";

// ─── Scarcity Mini Chart ───────────────────────────────────────────

const DIMENSION_LABELS = ["SC", "DV", "SD", "PP", "TU"];
const DIMENSION_KEYS: (keyof ScarcityScore["dimensions"])[] = [
  "supplyConstraint",
  "demandVisibility",
  "substitutionDifficulty",
  "pricingPower",
  "temporalUrgency",
];

function ScarcityMiniChart({ dimensions }: { dimensions: ScarcityScore["dimensions"] }) {
  return (
    <div className="flex items-end gap-px" aria-hidden="true" title="Scarcity dimensions: SC, DV, SD, PP, TU">
      {DIMENSION_KEYS.map((key, idx) => {
        const val = dimensions[key];
        const heightPct = Math.max(val * 10, 5);
        return (
          <div
            key={key}
            className="w-1.5 rounded-t bg-violet-400"
            style={{ height: `${heightPct}px` }}
            title={`${DIMENSION_LABELS[idx]}: ${val.toFixed(1)}`}
          />
        );
      })}
    </div>
  );
}

// ─── Skeleton Row ──────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr>
      <td className="px-3 py-3"><div className="h-4 w-14 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-32 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-5 w-14 bg-white/10 rounded-full animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-5 w-16 bg-white/10 rounded-full animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-12 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-28 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-24 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-20 bg-white/10 rounded animate-pulse" /></td>
    </tr>
  );
}

// ─── Expandable Row ────────────────────────────────────────────────

function CandidateRow({ candidate }: { candidate: WatchlistCandidate }) {
  const [expanded, setExpanded] = useState(false);
  const tierCfg = TIER_CONFIG[candidate.tier];
  const convCfg = CONVICTION_CONFIG[candidate.conviction] ?? CONVICTION_CONFIG.LOW;
  const scarcity = candidate.scarcityScore;
  const scarcityOverall = scarcity?.overall;

  return (
    <>
      <tr
        className={cn(
          "border-b border-border cursor-pointer hover:bg-white/5 transition-colors duration-150",
          expanded && "bg-white/5"
        )}
        onClick={() => setExpanded(!expanded)}
        role="row"
        aria-expanded={expanded}
      >
        <td className="px-3 py-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold font-mono text-text-primary">
              {candidate.ticker}
            </span>
            {candidate.appearsInScreens > 1 && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-violet-500/15 text-violet-400">
                {candidate.appearsInScreens} screens
              </span>
            )}
          </div>
        </td>
        <td className="px-3 py-3 text-xs text-text-primary">
          {candidate.companyName}
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
          <span
            className={cn(
              "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
              convCfg.bg,
              convCfg.text
            )}
          >
            {candidate.conviction}
          </span>
        </td>
        <td className="px-3 py-3">
          {scarcityOverall != null ? (
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-text-primary">
                {scarcityOverall.toFixed(1)}
              </span>
              {scarcity?.dimensions && <ScarcityMiniChart dimensions={scarcity.dimensions} />}
            </div>
          ) : (
            <span className="text-xs text-text-tertiary">{"\u2014"}</span>
          )}
        </td>
        <td className="px-3 py-3 text-xs text-text-secondary max-w-[180px] truncate" title={candidate.catalyst ?? undefined}>
          {candidate.catalyst ?? "\u2014"}
        </td>
        <td className="px-3 py-3">
          <Link
            href={`/screens/${candidate.screenId}`}
            onClick={(e) => e.stopPropagation()}
            className="text-xs text-primary hover:text-primary-hover transition-colors duration-200 hover:underline truncate block max-w-[160px]"
            title={candidate.screenName}
          >
            {candidate.screenName}
          </Link>
        </td>
        <td className="px-3 py-3 text-xs text-text-tertiary whitespace-nowrap">
          {candidate.screenDate
            ? new Date(candidate.screenDate).toLocaleDateString()
            : "\u2014"}
        </td>
        <td className="px-3 py-1.5">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            className="p-1 rounded hover:bg-white/10 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1"
            aria-label={expanded ? "Collapse details" : "Expand details"}
          >
            {expanded ? (
              <ChevronUp size={14} className="text-text-tertiary" />
            ) : (
              <ChevronDown size={14} className="text-text-tertiary" />
            )}
          </button>
        </td>
      </tr>

      {expanded && (
        <tr className="border-b border-border">
          <td colSpan={9} className="px-4 py-4 bg-white/5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {scarcity?.dimensions && (
                <div>
                  <p className="text-[11px] font-medium text-text-secondary mb-3">Scarcity Dimensions</p>
                  <div className="space-y-2">
                    {DIMENSION_KEYS.map((key) => {
                      const val = scarcity.dimensions[key];
                      const pct = Math.round(val * 10);
                      const color =
                        val >= 7 ? "bg-emerald-500" :
                        val >= 4 ? "bg-amber-500" :
                        "bg-red-400";
                      const labels: Record<string, string> = {
                        supplyConstraint: "Supply Constraint",
                        demandVisibility: "Demand Visibility",
                        substitutionDifficulty: "Substitution Difficulty",
                        pricingPower: "Pricing Power",
                        temporalUrgency: "Temporal Urgency",
                      };
                      return (
                        <div key={key} className="flex items-center gap-3">
                          <span className="text-[11px] text-text-secondary w-36 flex-shrink-0">
                            {labels[key]}
                          </span>
                          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden" aria-hidden="true">
                            <div
                              className={cn("h-full rounded-full transition-all duration-300", color)}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="text-xs font-mono text-text-secondary w-8 text-right">
                            {val.toFixed(1)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              <div className="space-y-3">
                <div>
                  <p className="text-[11px] font-medium text-text-secondary mb-1">Bottleneck</p>
                  <p className="text-xs text-text-primary">{candidate.bottleneckName}</p>
                </div>
                {candidate.catalyst && (
                  <div>
                    <p className="text-[11px] font-medium text-text-secondary mb-1">Catalyst</p>
                    <p className="text-xs text-text-secondary leading-relaxed">{candidate.catalyst}</p>
                  </div>
                )}
                <div>
                  <p className="text-[11px] font-medium text-text-secondary mb-1">Source Screen</p>
                  <Link
                    href={`/screens/${candidate.screenId}`}
                    className="text-xs text-primary hover:text-primary-hover transition-colors duration-200 hover:underline"
                  >
                    {candidate.screenName}
                  </Link>
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ─── Page ──────────────────────────────────────────────────────────

export default function WatchlistPage() {
  const [data, setData] = useState<WatchlistResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("tier");
  const [sortAsc, setSortAsc] = useState(true);
  const [tierFilter, setTierFilter] = useState<Set<1 | 2 | 3>>(new Set([1, 2, 3]));

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getWatchlist({ limit: 500 });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const toggleTier = useCallback((tier: 1 | 2 | 3) => {
    setTierFilter((prev) => {
      const next = new Set(prev);
      if (next.has(tier)) {
        if (next.size > 1) next.delete(tier);
      } else {
        next.add(tier);
      }
      return next;
    });
  }, []);

  const handleSort = useCallback((key: SortKey) => {
    setSortKey((prev) => {
      if (prev === key) {
        setSortAsc((a) => !a);
        return key;
      }
      setSortAsc(key === "ticker" || key === "tier");
      return key;
    });
  }, []);

  const filteredAndSorted = useMemo(() => {
    if (!data) return [];
    const filtered = data.candidates.filter((c) => tierFilter.has(c.tier));
    const sorted = [...filtered];
    sorted.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "ticker":
          cmp = a.ticker.localeCompare(b.ticker);
          break;
        case "tier":
          cmp = a.tier - b.tier;
          break;
        case "conviction": {
          const order: Record<string, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };
          cmp = (order[a.conviction] ?? 3) - (order[b.conviction] ?? 3);
          break;
        }
        case "scarcity":
          cmp = (a.scarcityScore?.overall ?? 0) - (b.scarcityScore?.overall ?? 0);
          break;
        case "screen":
          cmp = a.screenName.localeCompare(b.screenName);
          break;
      }
      return sortAsc ? cmp : -cmp;
    });
    return sorted;
  }, [data, sortKey, sortAsc, tierFilter]);

  // ─── Sort Header Helper ────────────────────────────────────────

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="animate-in">
        <h1 className="font-display text-2xl font-bold text-text-primary">
          Equity Watchlist
        </h1>
        <p className="text-sm text-text-secondary mt-0.5">
          All equity candidates across all screens
        </p>
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-5 py-4 flex items-start gap-3">
          <AlertCircle size={18} className="text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-300">Failed to load watchlist</p>
            <p className="text-xs text-red-400 mt-0.5">{error}</p>
          </div>
          <button
            onClick={fetchData}
            className="ml-auto text-xs font-medium text-primary hover:text-primary-hover transition-colors duration-200"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="h-5 w-40 bg-white/10 rounded animate-pulse" />
            <div className="flex gap-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-6 w-16 bg-white/10 rounded-full animate-pulse" />
              ))}
            </div>
          </div>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-white/5 border-b border-border">
                  {["Ticker", "Company", "Tier", "Conv.", "Score", "Catalyst", "Screen", "Date"].map((h) => (
                    <th key={h} className="px-3 py-2.5">
                      <div className="h-3 w-16 bg-white/10 rounded animate-pulse" />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 5 }).map((_, i) => (
                  <SkeletonRow key={i} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && data && data.candidates.length === 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-16 text-center">
          <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
            <Eye size={28} className="text-text-tertiary" />
          </div>
          <h2 className="text-lg font-semibold text-text-primary mb-1">
            No candidates yet
          </h2>
          <p className="text-sm text-text-secondary max-w-md mx-auto">
            Equity candidates will appear here once your IST screens identify them.
            Create a new screen to get started.
          </p>
        </div>
      )}

      {/* Data state */}
      {!loading && !error && data && data.candidates.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
          {/* Header row with tier breakdown + filter toggles */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-5 gap-3">
            <div>
              <h3 className="text-sm font-semibold text-text-primary">
                {filteredAndSorted.length} of {data.total} candidates
              </h3>
            </div>
            <div className="flex items-center gap-2 flex-wrap" role="group" aria-label="Tier filters">
              {([1, 2, 3] as const).map((tier) => {
                const cfg = TIER_CONFIG[tier];
                const count = data.tierBreakdown[`tier${tier}` as keyof typeof data.tierBreakdown];
                const active = tierFilter.has(tier);
                return (
                  <button
                    key={tier}
                    onClick={() => toggleTier(tier)}
                    className={cn(
                      "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium transition-all duration-200",
                      active
                        ? cn(cfg.bg, cfg.text)
                        : "bg-white/5 text-text-tertiary"
                    )}
                    aria-pressed={active}
                  >
                    {cfg.label}: {count}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Multi-screen tickers summary */}
          {data.multiScreenTickers.length > 0 && (
            <div className="mb-4 flex items-center gap-2 flex-wrap">
              <span className="text-[11px] font-medium text-text-secondary">Multi-screen:</span>
              {data.multiScreenTickers.map((ms) => (
                <span
                  key={ms.ticker}
                  className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-violet-500/15 text-violet-400"
                >
                  {ms.ticker} ({ms.screenCount})
                </span>
              ))}
            </div>
          )}

          {/* Table */}
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-left" role="table">
              <thead>
                <tr className="bg-white/5 border-b border-border">
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
                    <SortHeader label="Conviction" sortKeyVal="conviction" />
                  </th>
                  <th className="px-3 py-2.5" scope="col">
                    <SortHeader label="Scarcity" sortKeyVal="scarcity" />
                  </th>
                  <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                    Catalyst
                  </th>
                  <th className="px-3 py-2.5" scope="col">
                    <SortHeader label="Screen" sortKeyVal="screen" />
                  </th>
                  <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                    Date
                  </th>
                  <th className="px-3 py-2.5 w-8" scope="col">
                    <span className="sr-only">Expand</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSorted.map((candidate) => (
                  <CandidateRow key={candidate.id} candidate={candidate} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
