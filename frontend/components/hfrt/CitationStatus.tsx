"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { getCitations } from "@/lib/api/hfrt";
import type { HFRTCitationResponse } from "@/types/hfrt";
import {
  AlertCircle,
  BookOpen,
  CheckCircle,
  Loader2,
  XCircle,
} from "lucide-react";

// ─── Props ──────────────────────────────────────────────────────────

interface CitationStatusProps {
  projectId: number;
  templateNumber: number;
  templateName?: string;
}

// ─── Component ──────────────────────────────────────────────────────

export default function CitationStatus({
  projectId,
  templateNumber,
  templateName,
}: CitationStatusProps) {
  const [data, setData] = useState<HFRTCitationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getCitations(projectId, templateNumber);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to validate citations");
    } finally {
      setLoading(false);
    }
  }, [projectId, templateNumber]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ─── Loading ──────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-2">
        <Loader2 size={14} className="text-text-tertiary animate-spin" />
        <span className="text-xs text-text-secondary">Checking citations...</span>
      </div>
    );
  }

  // ─── Error ────────────────────────────────────────────────────

  if (error) {
    return (
      <div className="flex items-center gap-2 py-2">
        <AlertCircle size={14} className="text-red-400" />
        <span className="text-xs text-red-400">{error}</span>
      </div>
    );
  }

  if (!data || data.total_claims === 0) {
    return (
      <div className="flex items-center gap-2 py-2">
        <BookOpen size={14} className="text-text-tertiary" />
        <span className="text-xs text-text-tertiary">
          {templateName ? `${templateName}: ` : ""}No quantitative claims found
        </span>
      </div>
    );
  }

  // ─── Render ───────────────────────────────────────────────────

  const coverageHigh = data.coverage_pct >= 80;
  const coverageMedium = data.coverage_pct >= 50;

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <BookOpen size={14} className="text-text-tertiary" />
          <span className="text-xs font-medium text-text-primary">
            {templateName || `Template ${templateNumber}`}
          </span>
        </div>
        <span
          className={cn(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium",
            coverageHigh
              ? "bg-emerald-500/10 text-emerald-300"
              : coverageMedium
              ? "bg-amber-500/10 text-amber-300"
              : "bg-red-500/10 text-red-300"
          )}
        >
          {coverageHigh ? (
            <CheckCircle size={10} />
          ) : (
            <XCircle size={10} />
          )}
          {data.coverage_pct}% cited
        </span>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-4 text-xs text-text-secondary mb-3">
        <span>
          Claims: <strong className="text-text-primary">{data.total_claims}</strong>
        </span>
        <span>
          Cited: <strong className="text-emerald-300">{data.cited_claims}</strong>
        </span>
        <span>
          Uncited:{" "}
          <strong className={data.uncited_claims.length > 0 ? "text-red-300" : "text-text-primary"}>
            {data.uncited_claims.length}
          </strong>
        </span>
      </div>

      {/* Coverage bar */}
      <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden mb-3">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-300",
            coverageHigh ? "bg-emerald-500" : coverageMedium ? "bg-amber-500" : "bg-red-500"
          )}
          style={{ width: `${data.coverage_pct}%` }}
        />
      </div>

      {/* Uncited claims */}
      {data.uncited_claims.length > 0 && (
        <details className="mt-2">
          <summary className="text-[11px] text-red-400 cursor-pointer hover:text-red-300">
            {data.uncited_claims.length} uncited claim{data.uncited_claims.length !== 1 ? "s" : ""}
          </summary>
          <ul className="mt-2 space-y-1 pl-4">
            {data.uncited_claims.slice(0, 10).map((claim, i) => (
              <li key={i} className="text-[11px] text-text-secondary leading-relaxed list-disc">
                {claim}
              </li>
            ))}
            {data.uncited_claims.length > 10 && (
              <li className="text-[11px] text-text-tertiary">
                ...and {data.uncited_claims.length - 10} more
              </li>
            )}
          </ul>
        </details>
      )}
    </div>
  );
}
