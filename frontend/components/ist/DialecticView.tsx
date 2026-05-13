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

// ─── Title/Description Splitter ─────────────────────────────────────
// Detects "ALL CAPS TITLE: explanation…" pattern and splits into parts.
// Falls back to null for plain sentences (e.g. screen 1 data).

function splitTitleDescription(
  text: string
): { title: string; description: string } | null {
  // Match "ALL CAPS TITLE: explanation" or "ALL CAPS TITLE — explanation"
  const match = text.match(/^([A-Z][A-Z0-9\s\-./&,()]+?)[\s]*[\u2014\u2013:]\s+([\s\S]+)/);
  if (!match) return null;
  const title = match[1].trim();
  if (title.length < 3) return null;
  return { title, description: match[2].trim() };
}

// ─── Conviction Level Parser ────────────────────────────────────────
// Claude sometimes returns "HIGH — long explanation" or "HIGH: explanation"
// instead of just "HIGH". Parse out the label and the summary.

const CONVICTION_COLORS: Record<string, { bg: string; text: string }> = {
  HIGH:   { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  MEDIUM: { bg: "bg-amber-500/10", text: "text-amber-400" },
  LOW:    { bg: "bg-white/10", text: "text-text-secondary" },
};

// Map alternative level words to canonical labels
const LEVEL_ALIASES: Record<string, string> = {
  HIGH: "HIGH", MEDIUM: "MEDIUM", LOW: "LOW",
  MODERATE: "MEDIUM", VERY_HIGH: "HIGH", VERY_LOW: "LOW",
};

function parseConvictionLevel(raw: string): { label: string; summary: string | null } {
  // Match "HIGH — explanation", "MODERATE - explanation", etc.
  const match = raw.match(/^(\w[\w\s]*?)\s*[\u2014\u2013\-:]\s+([\s\S]+)/);
  if (match) {
    const word = match[1].trim().toUpperCase().replace(/\s+/g, "_");
    const label = LEVEL_ALIASES[word] ?? word;
    return { label, summary: match[2].trim() };
  }
  // Already clean: just "HIGH" or "MODERATE"
  const upper = raw.trim().toUpperCase().replace(/\s+/g, "_");
  const label = LEVEL_ALIASES[upper] ?? upper;
  return { label, summary: null };
}

function ConvictionBadge({ level }: { level: string }) {
  const { label } = parseConvictionLevel(level);
  const config = CONVICTION_COLORS[label] ?? CONVICTION_COLORS.LOW;
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        config.bg,
        config.text
      )}
    >
      {label}
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
                <td className="px-3 py-2 text-[11px] text-text-secondary leading-relaxed">
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

// ─── Collapsible Argument (title-only by default) ──────────────────

function CollapsibleArgument({
  title,
  description,
  accentColor,
  dotColor,
}: {
  title: string;
  description: string;
  accentColor: string;
  dotColor: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div role="listitem">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "w-full flex items-start gap-2 py-1 text-left",
          "hover:bg-white/5 rounded transition-colors duration-100",
          "focus:outline-none focus:ring-1 focus:ring-primary rounded"
        )}
        aria-expanded={open}
      >
        <span
          className={cn("w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0", dotColor)}
          aria-hidden="true"
        />
        <span className={cn("text-xs font-semibold leading-snug flex-1 min-w-0", accentColor)}>
          {title}
        </span>
        {open ? (
          <ChevronUp size={12} className="text-text-tertiary flex-shrink-0 mt-0.5" />
        ) : (
          <ChevronDown size={12} className="text-text-tertiary flex-shrink-0 mt-0.5" />
        )}
      </button>
      {open && (
        <div className="ml-3.5 pl-2 border-l border-border mt-0.5 mb-1">
          <p className="text-xs text-text-secondary leading-relaxed">
            {description}
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Collapsible Risk (title-only by default) ──────────────────────

function CollapsibleRisk({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div role="listitem">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "w-full flex items-start gap-2 py-1 text-left",
          "hover:bg-white/5 rounded transition-colors duration-100",
          "focus:outline-none focus:ring-1 focus:ring-primary rounded"
        )}
        aria-expanded={open}
      >
        <AlertTriangle size={12} className="flex-shrink-0 text-amber-400 mt-0.5" aria-hidden="true" />
        <span className="text-xs font-semibold text-amber-400 leading-snug flex-1 min-w-0">
          {title}
        </span>
        {open ? (
          <ChevronUp size={12} className="text-text-tertiary flex-shrink-0 mt-0.5" />
        ) : (
          <ChevronDown size={12} className="text-text-tertiary flex-shrink-0 mt-0.5" />
        )}
      </button>
      {open && (
        <div className="ml-3.5 pl-2 border-l border-amber-500/30 mt-0.5 mb-1">
          <p className="text-xs text-amber-400/80 leading-relaxed">
            {description}
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

      {/* Conviction Summary (extracted from conviction_level field) */}
      {(() => {
        const { summary } = parseConvictionLevel(review.content.convictionLevel);
        if (!summary) return null;
        return (
          <div className={cn("mb-4 p-3 rounded-lg border", accentBg, accentBorder)}>
            <p className="text-[11px] font-medium text-text-secondary mb-1">Summary</p>
            <p className="text-xs text-text-primary leading-relaxed">{summary}</p>
          </div>
        );
      })()}

      {/* Key Arguments */}
      {review.content.keyArguments.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Key Arguments ({review.content.keyArguments.length})
          </p>
          <div className="space-y-1" role="list">
            {review.content.keyArguments.map((arg, idx) => {
              const parsed = splitTitleDescription(arg);
              if (!parsed) {
                return (
                  <div key={idx} role="listitem" className="flex items-start gap-2 py-1">
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
                  </div>
                );
              }
              return (
                <CollapsibleArgument
                  key={idx}
                  title={parsed.title}
                  description={parsed.description}
                  accentColor={isOptimist ? "text-emerald-400" : "text-red-400"}
                  dotColor={isOptimist ? "bg-emerald-400" : "bg-red-400"}
                />
              );
            })}
          </div>
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

      {/* Conviction Summary */}
      {(() => {
        const { summary } = parseConvictionLevel(syn.overallConviction);
        if (!summary) return null;
        return (
          <div className="mb-4 p-3 rounded-lg border bg-violet-500/10 border-violet-500/30">
            <p className="text-[11px] font-medium text-text-secondary mb-1">Summary</p>
            <p className="text-xs text-text-primary leading-relaxed">{summary}</p>
          </div>
        );
      })()}

      {/* Key Risks */}
      {syn.keyRisks.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Key Risks ({syn.keyRisks.length})
          </p>
          <div className="space-y-1" role="list">
            {syn.keyRisks.map((risk, idx) => {
              const parsed = splitTitleDescription(risk);
              if (!parsed) {
                return (
                  <div key={idx} role="listitem" className="flex items-start gap-2 py-1">
                    <AlertTriangle size={12} className="flex-shrink-0 text-amber-400 mt-0.5" aria-hidden="true" />
                    <span className="text-xs text-amber-400 leading-relaxed">
                      {risk}
                    </span>
                  </div>
                );
              }
              return <CollapsibleRisk key={idx} title={parsed.title} description={parsed.description} />;
            })}
          </div>
        </div>
      )}

      {/* Disagreements */}
      {syn.disagreements.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Disagreements ({syn.disagreements.length})
          </p>
          <div className="space-y-2">
            {syn.disagreements.map((d: Disagreement, idx: number) => (
              <div key={idx} className="border border-border rounded-lg p-3 space-y-2">
                <p className="text-xs font-medium text-text-primary">{d.topic}</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div>
                    <p className="text-[10px] font-medium text-emerald-400 uppercase tracking-wider mb-0.5">Optimist</p>
                    <p className="text-[11px] text-text-primary leading-relaxed">{d.optimistView}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-medium text-red-400 uppercase tracking-wider mb-0.5">Pessimist</p>
                    <p className="text-[11px] text-text-primary leading-relaxed">{d.pessimistView}</p>
                  </div>
                </div>
                <div className="pt-2 border-t border-border">
                  <p className="text-[10px] font-medium text-violet-400 uppercase tracking-wider mb-0.5">Resolution</p>
                  <p className="text-[11px] text-text-primary leading-relaxed">{d.resolution}</p>
                </div>
                {d.impactOnTiers && (
                  <p className="text-[11px] text-text-secondary leading-relaxed">
                    <span className="font-medium">Tier Impact:</span> {d.impactOnTiers}
                  </p>
                )}
              </div>
            ))}
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
