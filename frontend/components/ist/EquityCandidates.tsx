"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { cn } from "@/lib/utils";
import { formatLargeNumber } from "@/lib/utils";
import { getCandidates } from "@/lib/api/ist";
import type { EquityCandidate, CandidatesResponse, ScarcityScore } from "@/types/ist";
import {
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  ArrowUpDown,
} from "lucide-react";

// ─── Tier Config ──────────────────────────────────────────────────────

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

// ─── Sort Config ──────────────────────────────────────────────────────

type SortKey = "scarcityScore" | "ticker" | "tier";

// ─── Scarcity Mini Chart ─────────────────────────────────────────────

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
        const heightPct = Math.max(val * 10, 5); // scale 0-10 to percentage, minimum visible
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

// ─── Scarcity Detail Bars ──────────────────────────────────────────

const DIMENSION_FULL_LABELS: Record<keyof ScarcityScore["dimensions"], string> = {
  supplyConstraint: "Supply Constraint",
  demandVisibility: "Demand Visibility",
  substitutionDifficulty: "Substitution Difficulty",
  pricingPower: "Pricing Power",
  temporalUrgency: "Temporal Urgency",
};

function ScarcityDetailBars({ dimensions }: { dimensions: ScarcityScore["dimensions"] }) {
  return (
    <div className="space-y-2">
      {DIMENSION_KEYS.map((key) => {
        const val = dimensions[key];
        const pct = Math.round(val * 10); // 0-10 -> 0-100%
        const color =
          val >= 7 ? "bg-emerald-500" :
          val >= 4 ? "bg-amber-500" :
          "bg-red-400";

        return (
          <div key={key} className="flex items-center gap-3">
            <span className="text-[11px] text-text-secondary w-36 flex-shrink-0">
              {DIMENSION_FULL_LABELS[key]}
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
  );
}

// ─── Skeleton ───────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr>
      <td className="px-3 py-3"><div className="h-4 w-14 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-32 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-12 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-5 w-14 bg-white/10 rounded-full animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-5 w-16 bg-white/10 rounded-full animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-28 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-24 bg-white/10 rounded animate-pulse" /></td>
    </tr>
  );
}

// ─── Expandable Row ─────────────────────────────────────────────────

function CandidateRow({ candidate }: { candidate: EquityCandidate }) {
  const [expanded, setExpanded] = useState(false);
  const tierCfg = TIER_CONFIG[candidate.tier];
  const convCfg = CONVICTION_CONFIG[candidate.conviction] ?? CONVICTION_CONFIG.LOW;

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
          <span className="text-xs font-bold font-mono text-text-primary">
            {candidate.ticker}
          </span>
        </td>
        <td className="px-3 py-3 text-xs text-text-primary">
          {candidate.companyName}
        </td>
        <td className="px-3 py-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-text-primary">
              {candidate.scarcityScore.overall.toFixed(1)}
            </span>
            <ScarcityMiniChart dimensions={candidate.scarcityScore.dimensions} />
          </div>
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
        <td className="px-3 py-3 text-xs text-text-secondary">
          {candidate.bottleneckName}
        </td>
        <td className="px-3 py-3 text-xs text-text-secondary max-w-[200px] truncate" title={candidate.catalyst ?? undefined}>
          {candidate.catalyst ?? "\u2014"}
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
            {expanded ? <ChevronUp size={14} className="text-text-tertiary" /> : <ChevronDown size={14} className="text-text-tertiary" />}
          </button>
        </td>
      </tr>

      {/* Expanded detail row */}
      {expanded && (
        <tr className="border-b border-border">
          <td colSpan={8} className="px-4 py-4 bg-white/5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Scarcity dimensions */}
              <div>
                <p className="text-[11px] font-medium text-text-secondary mb-3">Scarcity Dimensions</p>
                <ScarcityDetailBars dimensions={candidate.scarcityScore.dimensions} />
              </div>

              {/* Details */}
              <div className="space-y-3">
                {/* Moat */}
                {candidate.moatType && (
                  <div>
                    <p className="text-[11px] font-medium text-text-secondary mb-1">Moat</p>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-violet-500/10 text-violet-400 mb-1">
                      {candidate.moatType}
                    </span>
                    {candidate.moatEvidence && (
                      <p className="text-xs text-text-secondary leading-relaxed mt-1">
                        {candidate.moatEvidence}
                      </p>
                    )}
                  </div>
                )}

                {/* Tier rationale */}
                {candidate.tierRationale && (
                  <div>
                    <p className="text-[11px] font-medium text-text-secondary mb-1">Tier Rationale</p>
                    <p className="text-xs text-text-secondary leading-relaxed">
                      {candidate.tierRationale}
                    </p>
                  </div>
                )}

                {/* Financial info */}
                <div className="flex flex-wrap gap-3">
                  {candidate.priceAtScreen != null && (
                    <div>
                      <p className="text-[11px] text-text-secondary">Price</p>
                      <p className="text-xs font-mono text-text-primary">
                        ${candidate.priceAtScreen.toFixed(2)}
                      </p>
                    </div>
                  )}
                  {candidate.peRatio != null && (
                    <div>
                      <p className="text-[11px] text-text-secondary">P/E</p>
                      <p className="text-xs font-mono text-text-primary">
                        {candidate.peRatio.toFixed(1)}x
                      </p>
                    </div>
                  )}
                  {candidate.marketCap != null && (
                    <div>
                      <p className="text-[11px] text-text-secondary">Market Cap</p>
                      <p className="text-xs font-mono text-text-primary">
                        {formatLargeNumber(candidate.marketCap)}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ─── Props ──────────────────────────────────────────────────────────

interface EquityCandidatesProps {
  screenId: number;
}

// ─── Component ──────────────────────────────────────────────────────

export default function EquityCandidates({ screenId }: EquityCandidatesProps) {
  const [data, setData] = useState<CandidatesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("scarcityScore");
  const [sortAsc, setSortAsc] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getCandidates(screenId);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load candidates");
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
      // defaults: scarcityScore desc, ticker asc, tier asc
      setSortAsc(key === "ticker" || key === "tier");
      return key;
    });
  }, []);

  const sortedCandidates = useMemo(() => {
    if (!data) return [];
    const sorted = [...data.candidates];
    sorted.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "scarcityScore":
          cmp = a.scarcityScore.overall - b.scarcityScore.overall;
          break;
        case "ticker":
          cmp = a.ticker.localeCompare(b.ticker);
          break;
        case "tier":
          cmp = a.tier - b.tier;
          break;
      }
      return sortAsc ? cmp : -cmp;
    });
    return sorted;
  }, [data, sortKey, sortAsc]);

  // ─── Loading State ────────────────────────────────────────────

  if (loading) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-4">
        {/* Header skeleton */}
        <div className="flex items-center justify-between">
          <div className="h-5 w-40 bg-white/10 rounded animate-pulse" />
          <div className="flex gap-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-6 w-16 bg-white/10 rounded-full animate-pulse" />
            ))}
          </div>
        </div>
        {/* Table skeleton */}
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-white/5 border-b border-border">
                {["Ticker", "Company", "Score", "Tier", "Conv.", "Bottleneck", "Catalyst"].map((h) => (
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

  if (!data || data.candidates.length === 0) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <Loader2 size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">No equity candidates yet</p>
        <p className="text-xs text-text-secondary mt-1">
          Candidates will appear here once the scanning phase completes.
        </p>
      </div>
    );
  }

  // ─── Sort header helper ────────────────────────────────────────

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
      {/* Header with tier breakdown */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-5 gap-3">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Equity Candidates</h3>
          <p className="text-xs text-text-secondary mt-0.5">
            {data.totalCount} candidate{data.totalCount !== 1 ? "s" : ""} identified
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap" role="list" aria-label="Tier breakdown">
          <span
            role="listitem"
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400"
          >
            Tier 1: {data.tierBreakdown.tier1}
          </span>
          <span
            role="listitem"
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400"
          >
            Tier 2: {data.tierBreakdown.tier2}
          </span>
          <span
            role="listitem"
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-white/10 text-text-secondary"
          >
            Tier 3: {data.tierBreakdown.tier3}
          </span>
        </div>
      </div>

      {/* Sortable data table */}
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
                <SortHeader label="Scarcity" sortKeyVal="scarcityScore" />
              </th>
              <th className="px-3 py-2.5" scope="col">
                <SortHeader label="Tier" sortKeyVal="tier" />
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Conviction
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Bottleneck
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Catalyst
              </th>
              <th className="px-3 py-2.5 w-8" scope="col">
                <span className="sr-only">Expand</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedCandidates.map((candidate) => (
              <CandidateRow key={candidate.id} candidate={candidate} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
