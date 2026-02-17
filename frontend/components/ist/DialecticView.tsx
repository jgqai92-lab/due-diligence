"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { getDialecticReview, getSynthesis } from "@/lib/api/ist";
import type {
  DialecticReview,
  SynthesisReview,
  TierAdjustment,
  Disagreement,
} from "@/types/ist";
import {
  AlertCircle,
  Loader2,
  TrendingUp,
  TrendingDown,
  Scale,
  ArrowUp,
  ArrowDown,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Minus,
} from "lucide-react";

// ─── Conviction Badge Config ────────────────────────────────────────

const CONVICTION_COLORS: Record<string, { bg: string; text: string }> = {
  HIGH:   { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  MEDIUM: { bg: "bg-amber-500/10", text: "text-amber-400" },
  LOW:    { bg: "bg-white/10", text: "text-text-secondary" },
};

function ConvictionBadge({ level }: { level: string }) {
  const upper = level.toUpperCase();
  const config = CONVICTION_COLORS[upper] ?? CONVICTION_COLORS.LOW;
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        config.bg,
        config.text
      )}
    >
      {level}
    </span>
  );
}

// ─── Tier Adjustment Table ──────────────────────────────────────────

function TierAdjustmentTable({
  adjustments,
  variant,
}: {
  adjustments: TierAdjustment[];
  variant: "optimist" | "pessimist" | "synthesis";
}) {
  if (adjustments.length === 0) return null;

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left" role="table">
        <thead>
          <tr className="bg-white/5 border-b border-border">
            <th className="px-3 py-2 text-[11px] font-medium text-text-secondary" scope="col">
              Ticker
            </th>
            <th className="px-3 py-2 text-[11px] font-medium text-text-secondary" scope="col">
              Current
            </th>
            <th className="px-3 py-2 text-[11px] font-medium text-text-secondary" scope="col">
              Proposed
            </th>
            <th className="px-3 py-2 text-[11px] font-medium text-text-secondary" scope="col">
              Rationale
            </th>
          </tr>
        </thead>
        <tbody>
          {adjustments.map((adj, idx) => {
            const isUpgrade = adj.proposedTier < adj.currentTier;
            const isDowngrade = adj.proposedTier > adj.currentTier;
            const isUnchanged = adj.proposedTier === adj.currentTier;

            return (
              <tr key={`${adj.ticker}-${idx}`} className="border-b border-border">
                <td className="px-3 py-2">
                  <span className="text-xs font-bold font-mono text-text-primary">
                    {adj.ticker}
                  </span>
                </td>
                <td className="px-3 py-2 text-xs text-text-secondary font-mono">
                  T{adj.currentTier}
                </td>
                <td className="px-3 py-2">
                  <span className="inline-flex items-center gap-1">
                    <span
                      className={cn(
                        "text-xs font-mono font-medium",
                        isUpgrade && "text-emerald-400",
                        isDowngrade && "text-red-400",
                        isUnchanged && "text-text-secondary"
                      )}
                    >
                      T{adj.proposedTier}
                    </span>
                    {isUpgrade && (
                      <ArrowUp size={12} className="text-emerald-500" aria-label="Upgrade" />
                    )}
                    {isDowngrade && (
                      <ArrowDown size={12} className="text-red-500" aria-label="Downgrade" />
                    )}
                    {isUnchanged && (
                      <Minus size={12} className="text-text-tertiary" aria-label="No change" />
                    )}
                  </span>
                </td>
                <td className="px-3 py-2 text-[11px] text-text-secondary leading-relaxed max-w-[300px]">
                  {adj.rationale}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ─── Collapsible Narrative ──────────────────────────────────────────

function CollapsibleNarrative({
  narrative,
  accentColor,
}: {
  narrative: string;
  accentColor: string;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "inline-flex items-center gap-1.5 text-xs font-medium transition-colors duration-200",
          "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1 rounded",
          accentColor,
          "hover:opacity-80"
        )}
        aria-expanded={expanded}
      >
        {expanded ? "Hide full analysis" : "Read full analysis"}
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {expanded && (
        <div className="mt-2 p-3 bg-white/5 rounded-lg border border-border">
          <p className="text-xs text-text-primary leading-relaxed whitespace-pre-wrap">
            {narrative}
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Side Panel (Optimist / Pessimist) ─────────────────────────────

function SidePanel({
  review,
  side,
}: {
  review: DialecticReview | null;
  side: "optimist" | "pessimist";
}) {
  const isOptimist = side === "optimist";

  const accentBg = isOptimist ? "bg-emerald-500/10" : "bg-red-500/10";
  const accentText = isOptimist ? "text-emerald-400" : "text-red-400";
  const accentBorder = isOptimist ? "border-emerald-500/30" : "border-red-500/30";
  const iconBg = isOptimist ? "bg-emerald-500/20" : "bg-red-500/20";
  const Icon = isOptimist ? TrendingUp : TrendingDown;
  const label = isOptimist ? "Optimist" : "Pessimist";

  // Placeholder state: review not yet available
  if (!review) {
    return (
      <div
        className={cn(
          "bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5",
          accentBorder
        )}
      >
        <div className="flex items-center gap-3 mb-4">
          <div
            className={cn(
              "w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0",
              iconBg
            )}
          >
            <Icon size={16} className={accentText} />
          </div>
          <h4 className={cn("text-sm font-semibold", accentText)}>
            {label}
          </h4>
        </div>
        <div className="flex items-center gap-2 text-text-tertiary">
          <Loader2 size={14} className="animate-spin" />
          <p className="text-xs">
            {label} analysis in progress...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5 hover:bg-white/5 transition-colors duration-200",
        accentBorder
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div
          className={cn(
            "w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0",
            iconBg
          )}
        >
          <Icon size={16} className={accentText} />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className={cn("text-sm font-semibold", accentText)}>
            {label}
          </h4>
        </div>
        <ConvictionBadge level={review.content.convictionLevel} />
      </div>

      {/* Key Arguments */}
      {review.content.keyArguments.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Key Arguments
          </p>
          <ul className="space-y-1.5" role="list">
            {review.content.keyArguments.map((arg, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span
                  className={cn(
                    "w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0",
                    isOptimist ? "bg-emerald-400" : "bg-red-400"
                  )}
                  aria-hidden="true"
                />
                <span className="text-xs text-text-primary leading-relaxed">
                  {arg}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Risk Discount */}
      {review.content.riskDiscount != null && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-1">
            Risk Discount
          </p>
          <span className="text-xs font-mono text-text-primary">
            {(review.content.riskDiscount * 100).toFixed(0)}%
          </span>
        </div>
      )}

      {/* Tier Adjustments */}
      {review.content.tierAdjustments.length > 0 && (
        <div className="mb-3">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Tier Adjustments
          </p>
          <TierAdjustmentTable
            adjustments={review.content.tierAdjustments}
            variant={side}
          />
        </div>
      )}

      {/* Collapsible Narrative */}
      {review.content.narrative && (
        <CollapsibleNarrative
          narrative={review.content.narrative}
          accentColor={accentText}
        />
      )}
    </div>
  );
}

// ─── Synthesis Section ─────────────────────────────────────────────

function SynthesisSection({ synthesis }: { synthesis: SynthesisReview | null }) {
  const [narrativeExpanded, setNarrativeExpanded] = useState(false);

  if (!synthesis) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border border-violet-500/30 rounded-xl p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-violet-500/20">
            <Scale size={16} className="text-violet-400" />
          </div>
          <h4 className="text-sm font-semibold text-violet-400">Synthesis</h4>
        </div>
        <div className="flex items-center gap-2 text-text-tertiary">
          <Loader2 size={14} className="animate-spin" />
          <p className="text-xs">Synthesis in progress...</p>
        </div>
      </div>
    );
  }

  const syn = synthesis.synthesis;

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border border-violet-500/30 rounded-xl p-5 hover:bg-white/5 transition-colors duration-200">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-violet-500/20">
          <Scale size={16} className="text-violet-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-violet-400">Synthesis</h4>
        </div>
        <ConvictionBadge level={syn.overallConviction} />
      </div>

      {/* Key Risks */}
      {syn.keyRisks.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">Key Risks</p>
          <div className="flex flex-wrap gap-1.5">
            {syn.keyRisks.map((risk, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30"
              >
                <AlertTriangle size={10} className="flex-shrink-0" aria-hidden="true" />
                {risk}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Disagreements Table */}
      {syn.disagreements.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">Disagreements</p>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-left" role="table">
              <thead>
                <tr className="bg-white/5 border-b border-border">
                  <th className="px-3 py-2 text-[11px] font-medium text-text-secondary" scope="col">
                    Topic
                  </th>
                  <th className="px-3 py-2 text-[11px] font-medium text-emerald-400" scope="col">
                    Optimist View
                  </th>
                  <th className="px-3 py-2 text-[11px] font-medium text-red-400" scope="col">
                    Pessimist View
                  </th>
                  <th className="px-3 py-2 text-[11px] font-medium text-violet-400" scope="col">
                    Resolution
                  </th>
                  <th className="px-3 py-2 text-[11px] font-medium text-text-secondary" scope="col">
                    Tier Impact
                  </th>
                </tr>
              </thead>
              <tbody>
                {syn.disagreements.map((d: Disagreement, idx: number) => (
                  <tr key={idx} className="border-b border-border">
                    <td className="px-3 py-2 text-xs font-medium text-text-primary">
                      {d.topic}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-emerald-400 leading-relaxed max-w-[180px]">
                      {d.optimistView}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-red-400 leading-relaxed max-w-[180px]">
                      {d.pessimistView}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-violet-400 leading-relaxed max-w-[180px]">
                      {d.resolution}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-text-secondary leading-relaxed max-w-[120px]">
                      {d.impactOnTiers}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Final Tier Adjustments */}
      {syn.finalTierAdjustments.length > 0 && (
        <div className="mb-3">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Final Tier Adjustments
          </p>
          <TierAdjustmentTable
            adjustments={syn.finalTierAdjustments}
            variant="synthesis"
          />
        </div>
      )}

      {/* Collapsible Narrative */}
      {syn.narrative && (
        <div className="mt-3">
          <button
            onClick={() => setNarrativeExpanded(!narrativeExpanded)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-violet-400 hover:opacity-80 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1 rounded"
            aria-expanded={narrativeExpanded}
          >
            {narrativeExpanded ? "Hide full analysis" : "Read full analysis"}
            {narrativeExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {narrativeExpanded && (
            <div className="mt-2 p-3 bg-white/5 rounded-lg border border-border">
              <p className="text-xs text-text-primary leading-relaxed whitespace-pre-wrap">
                {syn.narrative}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Skeleton Cards ────────────────────────────────────────────────

function SkeletonSidePanel() {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-white/10 rounded-full animate-pulse" />
        <div className="h-4 w-24 bg-white/10 rounded animate-pulse" />
        <div className="ml-auto h-5 w-16 bg-white/10 rounded-full animate-pulse" />
      </div>
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 bg-white/10 rounded-full mt-1.5 flex-shrink-0" />
            <div className="h-3 w-full bg-white/10 rounded animate-pulse" />
          </div>
        ))}
      </div>
      <div className="h-20 w-full bg-white/10 rounded animate-pulse" />
    </div>
  );
}

function SkeletonSynthesis() {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-white/10 rounded-full animate-pulse" />
        <div className="h-4 w-24 bg-white/10 rounded animate-pulse" />
        <div className="ml-auto h-5 w-16 bg-white/10 rounded-full animate-pulse" />
      </div>
      <div className="flex flex-wrap gap-1.5">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-5 w-24 bg-white/10 rounded-full animate-pulse" />
        ))}
      </div>
      <div className="h-32 w-full bg-white/10 rounded animate-pulse" />
      <div className="h-20 w-full bg-white/10 rounded animate-pulse" />
    </div>
  );
}

// ─── Props ──────────────────────────────────────────────────────────

interface DialecticViewProps {
  screenId: number;
}

// ─── Component ──────────────────────────────────────────────────────

export default function DialecticView({ screenId }: DialecticViewProps) {
  const [optimist, setOptimist] = useState<DialecticReview | null>(null);
  const [pessimist, setPessimist] = useState<DialecticReview | null>(null);
  const [synthesis, setSynthesis] = useState<SynthesisReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Track which parts are available vs. still loading
  const [optimistAvailable, setOptimistAvailable] = useState(false);
  const [pessimistAvailable, setPessimistAvailable] = useState(false);
  const [synthesisAvailable, setSynthesisAvailable] = useState(false);
  const [anyDataFound, setAnyDataFound] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setOptimistAvailable(false);
    setPessimistAvailable(false);
    setSynthesisAvailable(false);
    setAnyDataFound(false);

    // Fetch all three in parallel; each may 404 independently
    const results = await Promise.allSettled([
      getDialecticReview(screenId, "optimist"),
      getDialecticReview(screenId, "pessimist"),
      getSynthesis(screenId),
    ]);

    let foundAny = false;

    // Optimist
    if (results[0].status === "fulfilled") {
      setOptimist(results[0].value);
      setOptimistAvailable(true);
      foundAny = true;
    } else {
      setOptimist(null);
    }

    // Pessimist
    if (results[1].status === "fulfilled") {
      setPessimist(results[1].value);
      setPessimistAvailable(true);
      foundAny = true;
    } else {
      setPessimist(null);
    }

    // Synthesis
    if (results[2].status === "fulfilled") {
      setSynthesis(results[2].value);
      setSynthesisAvailable(true);
      foundAny = true;
    } else {
      setSynthesis(null);
    }

    // If all three failed and at least one wasn't a 404, surface an error
    if (!foundAny) {
      const firstError = results.find(
        (r) => r.status === "rejected" && (r.reason as any)?.status !== 404
      );
      if (firstError && firstError.status === "rejected") {
        setError(firstError.reason?.message ?? "Failed to load dialectic data");
      }
    }

    setAnyDataFound(foundAny);
    setLoading(false);
  }, [screenId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ─── Loading State ────────────────────────────────────────────

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="flex items-center justify-between">
          <div className="h-5 w-48 bg-white/10 rounded animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SkeletonSidePanel />
          <SkeletonSidePanel />
        </div>
        <SkeletonSynthesis />
      </div>
    );
  }

  // ─── Error State ──────────────────────────────────────────────

  if (error && !anyDataFound) {
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

  if (!anyDataFound) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <Scale size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">
          Dialectic analysis has not started yet
        </p>
        <p className="text-xs text-text-secondary mt-1">
          The optimist and pessimist reviews will appear here once the dialectic phase begins.
        </p>
      </div>
    );
  }

  // ─── Render ───────────────────────────────────────────────────

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div>
        <h3 className="text-sm font-semibold text-text-primary">Dialectic Scrutiny</h3>
        <p className="text-xs text-text-secondary mt-0.5">
          Side-by-side optimist and pessimist analysis with synthesized conclusion
        </p>
      </div>

      {/* Side-by-side Optimist vs Pessimist */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SidePanel
          review={optimistAvailable ? optimist : null}
          side="optimist"
        />
        <SidePanel
          review={pessimistAvailable ? pessimist : null}
          side="pessimist"
        />
      </div>

      {/* Synthesis (full-width below) */}
      <SynthesisSection
        synthesis={synthesisAvailable ? synthesis : null}
      />
    </div>
  );
}
