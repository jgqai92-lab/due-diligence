"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { getScreenClaims } from "@/lib/api/ist";
import type { ISTClaim, ValidationVerdict } from "@/types/ist";
import { Loader2, AlertCircle, Filter, CheckCircle2, XCircle, HelpCircle, MinusCircle } from "lucide-react";

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

// ─── Validation Badge ───────────────────────────────────────────────

function ValidationBadge({ verdict }: { verdict: ValidationVerdict | null; }) {
  if (!verdict) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-white/10 text-text-secondary">
        <MinusCircle size={12} />
        Pending
      </span>
    );
  }

  const config: Record<ValidationVerdict, { icon: typeof CheckCircle2; bg: string; text: string; label: string }> = {
    confirmed: {
      icon: CheckCircle2,
      bg: "bg-emerald-500/10",
      text: "text-emerald-400",
      label: "Confirmed",
    },
    partially_confirmed: {
      icon: HelpCircle,
      bg: "bg-amber-500/10",
      text: "text-amber-400",
      label: "Partial",
    },
    contradicted: {
      icon: XCircle,
      bg: "bg-red-500/10",
      text: "text-red-400",
      label: "Contradicted",
    },
    unvalidatable: {
      icon: MinusCircle,
      bg: "bg-white/10",
      text: "text-text-secondary",
      label: "Unvalidatable",
    },
  };

  const { icon: Icon, bg, text, label } = config[verdict];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
        bg,
        text
      )}
    >
      <Icon size={12} />
      {label}
    </span>
  );
}

// ─── Skeleton Row ───────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr>
      <td className="px-3 py-3"><div className="h-4 w-6 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-full bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-24 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-16 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-16 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-16 bg-white/10 rounded animate-pulse" /></td>
      <td className="px-3 py-3"><div className="h-4 w-20 bg-white/10 rounded animate-pulse" /></td>
    </tr>
  );
}

// ─── Props ──────────────────────────────────────────────────────────

interface ClaimsTableProps {
  screenId: number;
}

// ─── Component ──────────────────────────────────────────────────────

export default function ClaimsTable({ screenId }: ClaimsTableProps) {
  const [claims, setClaims] = useState<ISTClaim[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [validatedCount, setValidatedCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [validatedOnly, setValidatedOnly] = useState(false);
  const [quantAnchorOnly, setQuantAnchorOnly] = useState(false);

  const fetchClaims = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getScreenClaims(screenId, {
        validated: validatedOnly || undefined,
        hasQuantAnchor: quantAnchorOnly || undefined,
      });
      setClaims(result.claims);
      setTotalCount(result.totalCount);
      setValidatedCount(result.validatedCount);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load claims");
    } finally {
      setLoading(false);
    }
  }, [screenId, validatedOnly, quantAnchorOnly]);

  useEffect(() => {
    fetchClaims();
  }, [fetchClaims]);

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between px-6 py-4 border-b border-border gap-3">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Extracted Claims</h3>
          <p className="text-xs text-text-secondary mt-0.5">
            {totalCount} total claims
            {validatedCount > 0 && ` \u00B7 ${validatedCount} validated`}
          </p>
        </div>

        {/* Filter toggles */}
        <div className="flex items-center gap-3">
          <Filter size={14} className="text-text-tertiary" aria-hidden="true" />
          <label className="flex items-center gap-1.5 text-xs text-text-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={validatedOnly}
              onChange={(e) => setValidatedOnly(e.target.checked)}
              className="w-3.5 h-3.5 rounded border-border text-primary focus:ring-primary"
            />
            Validated only
          </label>
          <label className="flex items-center gap-1.5 text-xs text-text-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={quantAnchorOnly}
              onChange={(e) => setQuantAnchorOnly(e.target.checked)}
              className="w-3.5 h-3.5 rounded border-border text-primary focus:ring-primary"
            />
            Has quant anchor
          </label>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="px-6 py-8 text-center">
          <AlertCircle size={24} className="mx-auto text-red-400 mb-2" />
          <p className="text-sm text-red-400">{error}</p>
          <button
            onClick={fetchClaims}
            className="mt-3 text-xs font-medium text-primary hover:text-primary-hover transition-colors duration-200"
          >
            Try again
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && !error && (
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border">
                <th className="px-3 py-3 text-xs font-medium text-text-secondary w-10">#</th>
                <th className="px-3 py-3 text-xs font-medium text-text-secondary">Claim</th>
                <th className="px-3 py-3 text-xs font-medium text-text-secondary">Citation</th>
                <th className="px-3 py-3 text-xs font-medium text-text-secondary">Quant Anchor</th>
                <th className="px-3 py-3 text-xs font-medium text-text-secondary">Temporal</th>
                <th className="px-3 py-3 text-xs font-medium text-text-secondary">Confidence</th>
                <th className="px-3 py-3 text-xs font-medium text-text-secondary">Validated</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 5 }).map((_, i) => (
                <SkeletonRow key={i} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && claims.length === 0 && (
        <div className="px-6 py-12 text-center">
          <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
            <Loader2 size={20} className="text-text-tertiary" />
          </div>
          <p className="text-sm font-medium text-text-primary">No claims extracted yet</p>
          <p className="text-xs text-text-secondary mt-1">
            Claims will appear here once the content extraction phase completes.
          </p>
        </div>
      )}

      {/* Table */}
      {!loading && !error && claims.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left" role="table">
            <thead>
              <tr className="border-b border-border">
                <th className="px-3 py-3 text-xs font-medium text-text-secondary w-10" scope="col">#</th>
                <th className="px-3 py-3 text-xs font-medium text-text-secondary min-w-[200px]" scope="col">Claim</th>
                <th className="px-3 py-3 text-xs font-medium text-text-secondary" scope="col">Citation</th>
                <th className="px-3 py-3 text-xs font-medium text-text-secondary" scope="col">Quant Anchor</th>
                <th className="px-3 py-3 text-xs font-medium text-text-secondary" scope="col">Temporal</th>
                <th className="px-3 py-3 text-xs font-medium text-text-secondary" scope="col">Confidence</th>
                <th className="px-3 py-3 text-xs font-medium text-text-secondary" scope="col">Validated</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((claim, idx) => (
                <tr
                  key={claim.id}
                  className="border-b border-border hover:bg-white/5 transition-colors duration-150"
                >
                  <td className="px-3 py-3 text-xs font-mono text-text-tertiary">
                    {idx + 1}
                  </td>
                  <td className="px-3 py-3 text-xs text-text-primary leading-relaxed max-w-md">
                    {claim.claimText}
                  </td>
                  <td className="px-3 py-3 text-xs text-text-secondary max-w-[160px] truncate" title={claim.sourceCitation}>
                    {claim.sourceCitation}
                  </td>
                  <td className="px-3 py-3 text-xs">
                    {claim.quantitativeAnchor ? (
                      <span className="font-mono text-violet-400">{claim.quantitativeAnchor}</span>
                    ) : (
                      <span className="text-text-tertiary">&mdash;</span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-xs">
                    {claim.temporalMarker ? (
                      <span className="text-sky-400">{claim.temporalMarker}</span>
                    ) : (
                      <span className="text-text-tertiary">&mdash;</span>
                    )}
                  </td>
                  <td className="px-3 py-3">
                    <ConfidenceBar confidence={claim.confidence} />
                  </td>
                  <td className="px-3 py-3">
                    <ValidationBadge verdict={claim.validationVerdict} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
