"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { getValidationResults } from "@/lib/api/ist";
import type { ValidationItem, ValidationResponse, ValidationVerdict } from "@/types/ist";
import {
  AlertCircle,
  Loader2,
  CheckCircle2,
  XCircle,
  HelpCircle,
  MinusCircle,
  ExternalLink,
  Search,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

// ─── Verdict Config ─────────────────────────────────────────────────

const VERDICT_CONFIG: Record<
  ValidationVerdict,
  { icon: typeof CheckCircle2; bg: string; text: string; label: string; border: string }
> = {
  confirmed: {
    icon: CheckCircle2,
    bg: "bg-emerald-500/10",
    text: "text-emerald-400",
    label: "Confirmed",
    border: "border-l-emerald-500",
  },
  partially_confirmed: {
    icon: HelpCircle,
    bg: "bg-amber-500/10",
    text: "text-amber-400",
    label: "Partially Confirmed",
    border: "border-l-amber-500",
  },
  contradicted: {
    icon: XCircle,
    bg: "bg-red-500/10",
    text: "text-red-400",
    label: "Contradicted",
    border: "border-l-red-500",
  },
  unvalidatable: {
    icon: MinusCircle,
    bg: "bg-white/10",
    text: "text-text-secondary",
    label: "Unvalidatable",
    border: "border-l-gray-400",
  },
};

// ─── Confidence Bar ─────────────────────────────────────────────────

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color =
    confidence >= 0.7
      ? "bg-emerald-500"
      : confidence >= 0.4
        ? "bg-amber-500"
        : "bg-red-500";

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-2 bg-white/10 rounded-full overflow-hidden" aria-hidden="true">
        <div
          className={cn("h-full rounded-full transition-all duration-300", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-text-secondary" aria-label={`Confidence ${pct}%`}>
        {pct}%
      </span>
    </div>
  );
}

// ─── Skeleton Row ───────────────────────────────────────────────────

function SkeletonValidationCard() {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-2">
          <div className="h-4 w-full bg-white/10 rounded animate-pulse" />
          <div className="h-4 w-3/4 bg-white/10 rounded animate-pulse" />
        </div>
        <div className="h-6 w-24 bg-white/10 rounded-full animate-pulse" />
      </div>
      <div className="h-3 w-full bg-white/10 rounded animate-pulse" />
      <div className="h-3 w-1/2 bg-white/10 rounded animate-pulse" />
    </div>
  );
}

// ─── Validation Card ────────────────────────────────────────────────

function ValidationCard({ item }: { item: ValidationItem }) {
  const [expanded, setExpanded] = useState(false);
  const config = VERDICT_CONFIG[item.verdict];
  const VerdictIcon = config.icon;

  return (
    <div
      className={cn(
        "bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl overflow-hidden",
        "border-l-4",
        config.border,
        "hover:bg-white/5 transition-colors duration-200"
      )}
    >
      <div className="p-5">
        {/* Top row: claim + verdict badge */}
        <div className="flex items-start justify-between gap-4 mb-3">
          <p className="text-xs text-text-primary leading-relaxed flex-1">
            {item.claimText}
          </p>
          <span
            className={cn(
              "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap flex-shrink-0",
              config.bg,
              config.text
            )}
          >
            <VerdictIcon size={12} />
            {config.label}
          </span>
        </div>

        {/* Confidence */}
        <div className="flex items-center gap-4 mb-3">
          <span className="text-[11px] text-text-secondary">Confidence:</span>
          <ConfidenceBar confidence={item.confidence} />
        </div>

        {/* Evidence summary */}
        <p className="text-xs text-text-secondary leading-relaxed">
          {item.evidence}
        </p>

        {/* Expandable detail section */}
        {(item.sources.length > 0 || item.searchQueries.length > 0) && (
          <button
            onClick={() => setExpanded(!expanded)}
            className={cn(
              "mt-3 inline-flex items-center gap-1 text-[11px] font-medium transition-colors duration-200",
              "text-text-secondary hover:text-text-primary",
              "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1 rounded"
            )}
            aria-expanded={expanded}
            aria-label={expanded ? "Collapse details" : "Expand details"}
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {expanded ? "Hide details" : "Show details"}
          </button>
        )}
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-border px-5 py-4 bg-white/5 space-y-3">
          {/* Sources */}
          {item.sources.length > 0 && (
            <div>
              <p className="text-[11px] font-medium text-text-secondary mb-1.5 flex items-center gap-1">
                <ExternalLink size={11} aria-hidden="true" />
                Sources
              </p>
              <ul className="space-y-1">
                {item.sources.map((source, idx) => (
                  <li key={idx}>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary hover:text-primary-hover hover:underline transition-colors duration-200 inline-flex items-center gap-1"
                    >
                      {source.title}
                      <ExternalLink size={10} aria-hidden="true" />
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Search queries */}
          {item.searchQueries.length > 0 && (
            <div>
              <p className="text-[11px] font-medium text-text-secondary mb-1.5 flex items-center gap-1">
                <Search size={11} aria-hidden="true" />
                Search Queries
              </p>
              <div className="flex flex-wrap gap-1.5">
                {item.searchQueries.map((q, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono bg-white/10 text-text-secondary"
                  >
                    {q}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Props ──────────────────────────────────────────────────────────

interface ValidationResultsProps {
  screenId: number;
}

// ─── Component ──────────────────────────────────────────────────────

export default function ValidationResults({ screenId }: ValidationResultsProps) {
  const [data, setData] = useState<ValidationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getValidationResults(screenId);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load validation results");
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
      <div className="space-y-4">
        {/* Summary bar skeleton */}
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-4">
          <div className="flex items-center gap-3 flex-wrap">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-7 w-28 bg-white/10 rounded-full animate-pulse" />
            ))}
          </div>
        </div>
        {/* Card skeletons */}
        <SkeletonValidationCard />
        <SkeletonValidationCard />
        <SkeletonValidationCard />
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

  if (!data || data.validations.length === 0) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <Loader2 size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">No validation results yet</p>
        <p className="text-xs text-text-secondary mt-1">
          Validation results will appear here once claims have been verified against external sources.
        </p>
      </div>
    );
  }

  const { summary } = data;

  // ─── Render ───────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Validation Results</h3>
            <p className="text-xs text-text-secondary mt-0.5">
              {summary.total} claim{summary.total !== 1 ? "s" : ""} validated
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap" role="list" aria-label="Validation summary">
            {summary.confirmed > 0 && (
              <span
                role="listitem"
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400"
              >
                <CheckCircle2 size={12} />
                {summary.confirmed} Confirmed
              </span>
            )}
            {summary.partiallyConfirmed > 0 && (
              <span
                role="listitem"
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400"
              >
                <HelpCircle size={12} />
                {summary.partiallyConfirmed} Partial
              </span>
            )}
            {summary.contradicted > 0 && (
              <span
                role="listitem"
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-400"
              >
                <XCircle size={12} />
                {summary.contradicted} Contradicted
              </span>
            )}
            {summary.unvalidatable > 0 && (
              <span
                role="listitem"
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-white/10 text-text-secondary"
              >
                <MinusCircle size={12} />
                {summary.unvalidatable} Unvalidatable
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Validation cards */}
      <div className="space-y-3" role="list" aria-label="Validation items">
        {data.validations.map((item) => (
          <div key={item.id} role="listitem">
            <ValidationCard item={item} />
          </div>
        ))}
      </div>
    </div>
  );
}
