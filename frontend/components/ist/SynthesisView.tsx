"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { getSynthesis } from "@/lib/api/ist";
import type {
  SynthesisReview,
  TierAdjustment,
  Disagreement,
} from "@/types/ist";
import {
  AlertCircle,
  Loader2,
  Scale,
  ArrowUp,
  ArrowDown,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Minus,
} from "lucide-react";

// ─── Title/Description Splitter ─────────────────────────────────────

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

// ─── Collapsible Risk ───────────────────────────────────────────────

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

// ─── Conviction Level Parser ────────────────────────────────────────

const CONVICTION_COLORS: Record<string, { bg: string; text: string }> = {
  HIGH:   { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  MEDIUM: { bg: "bg-amber-500/10", text: "text-amber-400" },
  LOW:    { bg: "bg-white/10", text: "text-text-secondary" },
};

const LEVEL_ALIASES: Record<string, string> = {
  HIGH: "HIGH", MEDIUM: "MEDIUM", LOW: "LOW",
  MODERATE: "MEDIUM", VERY_HIGH: "HIGH", VERY_LOW: "LOW",
};

function parseConvictionLevel(raw: string): { label: string; summary: string | null } {
  const match = raw.match(/^(\w[\w\s]*?)\s*[\u2014\u2013\-:]\s+([\s\S]+)/);
  if (match) {
    const word = match[1].trim().toUpperCase().replace(/\s+/g, "_");
    const label = LEVEL_ALIASES[word] ?? word;
    return { label, summary: match[2].trim() };
  }
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

function TierAdjustmentTable({ adjustments }: { adjustments: TierAdjustment[] }) {
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

// ─── Disagreement Accordion Item ───────────────────────────────────

function DisagreementItem({ disagreement }: { disagreement: Disagreement }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "w-full flex items-center justify-between px-4 py-3 text-left",
          "hover:bg-white/5 transition-colors duration-150",
          "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1",
          expanded && "bg-white/5"
        )}
        aria-expanded={expanded}
      >
        <span className="text-xs font-medium text-text-primary">
          {disagreement.topic}
        </span>
        {expanded ? (
          <ChevronUp size={14} className="text-text-tertiary flex-shrink-0" />
        ) : (
          <ChevronDown size={14} className="text-text-tertiary flex-shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-border bg-white/5">
          {/* Optimist View */}
          <div className="pt-3">
            <p className="text-[10px] font-medium text-emerald-400 uppercase tracking-wider mb-1">
              Optimist View
            </p>
            <p className="text-xs text-text-primary leading-relaxed">
              {disagreement.optimistView}
            </p>
          </div>

          {/* Pessimist View */}
          <div>
            <p className="text-[10px] font-medium text-red-400 uppercase tracking-wider mb-1">
              Pessimist View
            </p>
            <p className="text-xs text-text-primary leading-relaxed">
              {disagreement.pessimistView}
            </p>
          </div>

          {/* Resolution */}
          <div className="pt-2 border-t border-border">
            <p className="text-[10px] font-medium text-violet-400 uppercase tracking-wider mb-1">
              Resolution
            </p>
            <p className="text-xs text-text-primary leading-relaxed">
              {disagreement.resolution}
            </p>
          </div>

          {/* Tier Impact */}
          <div>
            <p className="text-[10px] font-medium text-text-secondary uppercase tracking-wider mb-1">
              Tier Impact
            </p>
            <p className="text-xs text-text-secondary leading-relaxed">
              {disagreement.impactOnTiers}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Skeleton ──────────────────────────────────────────────────────

function SynthesisSkeleton() {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-5">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-white/10 rounded-full animate-pulse" />
        <div className="h-5 w-32 bg-white/10 rounded animate-pulse" />
        <div className="ml-auto h-5 w-20 bg-white/10 rounded-full animate-pulse" />
      </div>
      <div className="flex flex-wrap gap-1.5">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-5 w-28 bg-white/10 rounded-full animate-pulse" />
        ))}
      </div>
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-12 w-full bg-white/10 rounded animate-pulse" />
        ))}
      </div>
      <div className="h-24 w-full bg-white/10 rounded animate-pulse" />
      <div className="h-4 w-48 bg-white/10 rounded animate-pulse" />
    </div>
  );
}

// ─── Props ──────────────────────────────────────────────────────────

interface SynthesisViewProps {
  screenId: number;
}

// ─── Component ──────────────────────────────────────────────────────

export default function SynthesisView({ screenId }: SynthesisViewProps) {
  const [data, setData] = useState<SynthesisReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [narrativeExpanded, setNarrativeExpanded] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getSynthesis(screenId);
      setData(result);
    } catch (err) {
      if ((err as any).status === 404) {
        setData(null);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load synthesis");
      }
    } finally {
      setLoading(false);
    }
  }, [screenId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ─── Loading State ────────────────────────────────────────────

  if (loading) {
    return <SynthesisSkeleton />;
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

  if (!data) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <Scale size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">
          Synthesis not available yet
        </p>
        <p className="text-xs text-text-secondary mt-1">
          The synthesis will appear here once both optimist and pessimist reviews are complete.
        </p>
      </div>
    );
  }

  const syn = data.synthesis;

  // ─── Render ───────────────────────────────────────────────────

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-5 gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-violet-500/20">
            <Scale size={16} className="text-violet-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Synthesis</h3>
            <p className="text-xs text-text-secondary mt-0.5">
              Final conclusions from dialectic analysis
            </p>
          </div>
        </div>
        <ConvictionBadge level={syn.overallConviction} />
      </div>

      {/* Conviction Summary */}
      {(() => {
        const { summary } = parseConvictionLevel(syn.overallConviction);
        if (!summary) return null;
        return (
          <div className="mb-5 p-3 rounded-lg border bg-violet-500/10 border-violet-500/30">
            <p className="text-[11px] font-medium text-text-secondary mb-1">Summary</p>
            <p className="text-xs text-text-primary leading-relaxed">{summary}</p>
          </div>
        );
      })()}

      {/* Key Risks */}
      {syn.keyRisks.length > 0 && (
        <div className="mb-5">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Key Risks ({syn.keyRisks.length})
          </p>
          <div className="space-y-1" role="list" aria-label="Key risks">
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

      {/* Disagreements Accordion */}
      {syn.disagreements.length > 0 && (
        <div className="mb-5">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Disagreements ({syn.disagreements.length})
          </p>
          <div className="space-y-2" role="list" aria-label="Disagreements">
            {syn.disagreements.map((d, idx) => (
              <div key={idx} role="listitem">
                <DisagreementItem disagreement={d} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Final Tier Adjustments */}
      {syn.finalTierAdjustments.length > 0 && (
        <div className="mb-5">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Final Tier Adjustments
          </p>
          <TierAdjustmentTable adjustments={syn.finalTierAdjustments} />
        </div>
      )}

      {/* Narrative (collapsible) */}
      {syn.narrative && (
        <div className="pt-3 border-t border-border">
          <button
            onClick={() => setNarrativeExpanded(!narrativeExpanded)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-violet-400 hover:opacity-80 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1 rounded"
            aria-expanded={narrativeExpanded}
          >
            {narrativeExpanded ? "Hide full narrative" : "Read full narrative"}
            {narrativeExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {narrativeExpanded && (
            <div className="mt-2 p-4 bg-violet-500/10 rounded-lg border border-violet-500/30">
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
