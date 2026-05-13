"use client";

import { useState, useEffect, useCallback, useMemo, Fragment } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  getBridgeCandidates,
  createHFRTFromBridge,
} from "@/lib/api/bridge";
import type {
  BridgeCandidatesResponse,
  BridgeCreateResponse,
} from "@/lib/api/bridge";
import type { HandoffCandidate } from "@/types/ist";
import {
  ArrowRight,
  CheckCircle,
  AlertCircle,
  Loader2,
  ExternalLink,
  Send,
} from "lucide-react";

// ─── Badge Config ────────────────────────────────────────────────────

const TIER_CONFIG: Record<number, { bg: string; text: string; label: string }> = {
  1: { bg: "bg-emerald-500/10", text: "text-emerald-400", label: "Tier 1" },
  2: { bg: "bg-amber-500/10", text: "text-amber-400", label: "Tier 2" },
  3: { bg: "bg-white/10", text: "text-text-secondary", label: "Tier 3" },
};

const CONVICTION_CONFIG: Record<string, { bg: string; text: string }> = {
  HIGH:   { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  MEDIUM: { bg: "bg-amber-500/10", text: "text-amber-400" },
  LOW:    { bg: "bg-white/10", text: "text-text-secondary" },
};

// ─── Props ──────────────────────────────────────────────────────────

interface HandoffPanelProps {
  screenId: number;
  isCertified: boolean;
}

// ─── Component ──────────────────────────────────────────────────────

export default function HandoffPanel({ screenId, isCertified }: HandoffPanelProps) {
  const [data, setData] = useState<BridgeCandidatesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selection state
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // Submission state
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<BridgeCreateResponse | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // ─── Fetch Candidates ──────────────────────────────────────────

  const fetchCandidates = useCallback(async () => {
    if (!isCertified) return;

    setLoading(true);
    setError(null);
    try {
      const response = await getBridgeCandidates(screenId);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load handoff candidates");
    } finally {
      setLoading(false);
    }
  }, [screenId, isCertified]);

  useEffect(() => {
    fetchCandidates();
  }, [fetchCandidates]);

  // ─── Selection Handlers ────────────────────────────────────────

  const toggleCandidate = useCallback((ticker: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(ticker)) {
        next.delete(ticker);
      } else {
        next.add(ticker);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    if (!data) return;
    setSelected(new Set(data.candidates.map((c) => c.ticker)));
  }, [data]);

  const deselectAll = useCallback(() => {
    setSelected(new Set());
  }, []);

  // ─── Submit Handler ────────────────────────────────────────────

  const handleSubmit = useCallback(async () => {
    if (selected.size === 0 || !data) return;

    setSubmitting(true);
    setSubmitError(null);
    try {
      const response = await createHFRTFromBridge({
        screenId,
        tickers: Array.from(selected),
      });
      setResult(response);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to create HFRT projects");
    } finally {
      setSubmitting(false);
    }
  }, [screenId, selected, data]);

  // Sort candidates by tier (ascending), preserving original order within each tier
  const sortedCandidates = useMemo(() => {
    if (!data) return [];
    return [...data.candidates].sort((a, b) => a.tier - b.tier);
  }, [data]);

  // ─── Guard: Not Certified ──────────────────────────────────────

  if (!isCertified) return null;

  // ─── Loading State ─────────────────────────────────────────────

  if (loading) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 bg-white/10 rounded animate-pulse" />
          <div className="h-5 w-56 bg-white/10 rounded animate-pulse" />
        </div>
        <div className="h-4 w-72 bg-white/10 rounded animate-pulse" />
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-10 w-full bg-white/10 rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  // ─── Error State ───────────────────────────────────────────────

  if (error) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-8 text-center">
        <AlertCircle size={24} className="mx-auto text-red-400 mb-2" />
        <p className="text-sm text-red-400">{error}</p>
        <button
          onClick={fetchCandidates}
          className="mt-3 text-xs font-medium text-primary hover:text-primary-hover transition-colors duration-200"
        >
          Try again
        </button>
      </div>
    );
  }

  // ─── Empty State ───────────────────────────────────────────────

  if (!data || data.candidates.length === 0) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <Send size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">No handoff candidates available</p>
        <p className="text-xs text-text-secondary mt-1">
          Candidates will appear here once the screen is fully certified.
        </p>
      </div>
    );
  }

  // ─── Success State ─────────────────────────────────────────────

  if (result) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
        {/* Header */}
        <div className="flex items-center gap-2.5 mb-4">
          <CheckCircle size={20} className="text-emerald-400" />
          <h3 className="text-sm font-semibold text-text-primary">HFRT Deep Research Handoff</h3>
        </div>

        {/* Success summary */}
        <p className="text-xs text-text-secondary mb-4">
          {result.created.length} of {result.total} project{result.total !== 1 ? "s" : ""} created successfully.
        </p>

        {/* Created project cards */}
        {result.created.length > 0 && (
          <div className="space-y-2 mb-4">
            {result.created.map((project) => (
              <div
                key={project.ticker}
                className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-4 py-3 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <CheckCircle size={16} className="text-emerald-400 flex-shrink-0" />
                  <div>
                    <span className="text-xs font-bold font-mono text-text-primary">
                      {project.ticker}
                    </span>
                    <span className="text-xs text-text-secondary ml-2">
                      Project #{project.projectId}
                    </span>
                  </div>
                </div>
                <Link
                  href={`/research/${project.projectId}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-emerald-400 bg-emerald-500/20 hover:bg-emerald-200 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-1"
                >
                  View Research
                  <ExternalLink size={12} />
                </Link>
              </div>
            ))}
          </div>
        )}

        {/* Failed project cards */}
        {result.failed.length > 0 && (
          <div className="space-y-2">
            <p className="text-[11px] font-medium text-red-400 mb-1">
              Failed ({result.failed.length})
            </p>
            {result.failed.map((failure) => (
              <div
                key={failure.ticker}
                className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 flex items-center gap-3"
              >
                <AlertCircle size={16} className="text-red-500 flex-shrink-0" />
                <div>
                  <span className="text-xs font-bold font-mono text-text-primary">
                    {failure.ticker}
                  </span>
                  <span className="text-xs text-red-400 ml-2">
                    {failure.error}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ─── Candidate Selection State ─────────────────────────────────

  const allSelected = selected.size === data.candidates.length;
  const noneSelected = selected.size === 0;

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-3">
        <div className="flex items-center gap-2.5">
          <ArrowRight size={20} className="text-primary flex-shrink-0" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">
              HFRT Deep Research Handoff
            </h3>
            <p className="text-xs text-text-secondary mt-0.5">
              Select candidates to send to deep equity research
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {data.tierBreakdown ? (
            <>
              {([1, 2, 3] as const).map((tier) => {
                const cfg = TIER_CONFIG[tier];
                const count = data.tierBreakdown![`tier${tier}` as keyof typeof data.tierBreakdown];
                if (!count) return null;
                return (
                  <span
                    key={tier}
                    className={cn(
                      "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium",
                      cfg.bg,
                      cfg.text
                    )}
                  >
                    {cfg.label}: {count}
                  </span>
                );
              })}
            </>
          ) : (
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400">
              {data.tier1Count} Tier 1 candidate{data.tier1Count !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      {/* Select all / Deselect all controls */}
      <div className="flex items-center gap-3 mb-3">
        <button
          onClick={selectAll}
          disabled={allSelected}
          className={cn(
            "text-xs font-medium transition-colors duration-200",
            "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1 rounded",
            allSelected
              ? "text-text-tertiary cursor-not-allowed"
              : "text-primary hover:text-primary-hover"
          )}
        >
          Select All
        </button>
        <span className="text-text-tertiary" aria-hidden="true">|</span>
        <button
          onClick={deselectAll}
          disabled={noneSelected}
          className={cn(
            "text-xs font-medium transition-colors duration-200",
            "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1 rounded",
            noneSelected
              ? "text-text-tertiary cursor-not-allowed"
              : "text-primary hover:text-primary-hover"
          )}
        >
          Deselect All
        </button>
        {selected.size > 0 && (
          <span className="text-xs text-text-secondary ml-auto">
            {selected.size} selected
          </span>
        )}
      </div>

      {/* Candidates table */}
      <div className="overflow-x-auto rounded-lg border border-border mb-4">
        <table className="w-full text-left" role="table">
          <thead>
            <tr className="bg-white/5 border-b border-border">
              <th className="px-3 py-2.5 w-10" scope="col">
                <span className="sr-only">Select</span>
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Ticker
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Company
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Tier
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Conviction
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Pillar
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Catalyst
              </th>
              <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                Scarcity
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedCandidates.map((candidate, idx) => {
              const prevTier = idx > 0 ? sortedCandidates[idx - 1].tier : null;
              const showGroupHeader = candidate.tier !== prevTier;
              const tierCfg = TIER_CONFIG[candidate.tier] ?? TIER_CONFIG[3];
              return (
                <Fragment key={candidate.ticker}>
                  {showGroupHeader && (
                    <tr className="bg-white/3">
                      <td colSpan={8} className="px-3 py-2">
                        <span
                          className={cn(
                            "inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold",
                            tierCfg.bg,
                            tierCfg.text
                          )}
                        >
                          {tierCfg.label}
                        </span>
                      </td>
                    </tr>
                  )}
                  <CandidateRow
                    candidate={candidate}
                    isSelected={selected.has(candidate.ticker)}
                    onToggle={() => toggleCandidate(candidate.ticker)}
                  />
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Submit error */}
      {submitError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 flex items-start gap-3 mb-4">
          <AlertCircle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-red-400">{submitError}</p>
        </div>
      )}

      {/* Submit button */}
      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={noneSelected || submitting}
          className={cn(
            "inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium",
            "transition-colors duration-200",
            "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
            noneSelected || submitting
              ? "bg-white/10 text-text-tertiary cursor-not-allowed"
              : "bg-primary text-white hover:bg-primary-hover"
          )}
          aria-label={`Send ${selected.size} candidate${selected.size !== 1 ? "s" : ""} to deep research`}
        >
          {submitting ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Sending...
            </>
          ) : (
            <>
              <Send size={16} />
              Send to Deep Research
              {selected.size > 0 && (
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-white/20 text-xs">
                  {selected.size}
                </span>
              )}
            </>
          )}
        </button>
      </div>
    </div>
  );
}

// ─── Candidate Row ───────────────────────────────────────────────────

function CandidateRow({
  candidate,
  isSelected,
  onToggle,
}: {
  candidate: HandoffCandidate;
  isSelected: boolean;
  onToggle: () => void;
}) {
  const convCfg = CONVICTION_CONFIG[candidate.conviction] ?? CONVICTION_CONFIG.LOW;
  const tierCfg = TIER_CONFIG[candidate.tier] ?? TIER_CONFIG[3];

  // Scarcity score color
  const scarcityColor =
    candidate.scarcityScore != null && candidate.scarcityScore >= 7
      ? "text-emerald-400"
      : candidate.scarcityScore != null && candidate.scarcityScore >= 4
        ? "text-amber-400"
        : "text-red-500";

  return (
    <tr
      className={cn(
        "border-b border-border cursor-pointer transition-colors duration-150",
        isSelected ? "bg-primary/5" : "hover:bg-white/5"
      )}
      onClick={onToggle}
      role="row"
    >
      <td className="px-3 py-3">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggle}
          onClick={(e) => e.stopPropagation()}
          className="h-4 w-4 rounded border-border text-primary focus:ring-primary focus:ring-offset-0 cursor-pointer"
          aria-label={`Select ${candidate.ticker}`}
        />
      </td>
      <td className="px-3 py-3">
        <span className="text-xs font-bold font-mono text-text-primary">
          {candidate.ticker}
        </span>
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
      <td className="px-3 py-3 text-xs text-text-secondary">
        {candidate.pillar}
      </td>
      <td className="px-3 py-3 text-xs text-text-secondary max-w-[200px] truncate" title={candidate.catalyst ?? undefined}>
        {candidate.catalyst ?? "\u2014"}
      </td>
      <td className="px-3 py-3">
        {candidate.scarcityScore != null ? (
          <span className={cn("text-xs font-mono font-medium", scarcityColor)}>
            {candidate.scarcityScore.toFixed(1)}
          </span>
        ) : (
          <span className="text-xs text-text-tertiary">{"\u2014"}</span>
        )}
      </td>
    </tr>
  );
}
