"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { getIsolationAudit } from "@/lib/api/hfrt";
import type { HFRTIsolationAuditResponse } from "@/types/hfrt";
import {
  AlertCircle,
  AlertTriangle,
  Loader2,
  ShieldCheck,
  ShieldAlert,
  Split,
} from "lucide-react";

// ─── Props ──────────────────────────────────────────────────────────

interface IsolationAuditProps {
  projectId: number;
}

// ─── Component ──────────────────────────────────────────────────────

export default function IsolationAudit({ projectId }: IsolationAuditProps) {
  const [data, setData] = useState<HFRTIsolationAuditResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getIsolationAudit(projectId);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run isolation audit");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ─── Loading ──────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-8 text-center">
        <Loader2 size={20} className="mx-auto text-text-tertiary animate-spin mb-2" />
        <p className="text-xs text-text-secondary">Auditing dialectic isolation...</p>
      </div>
    );
  }

  // ─── Error ────────────────────────────────────────────────────

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

  if (!data) return null;

  // ─── Render ───────────────────────────────────────────────────

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <Split size={14} className="text-text-tertiary" />
          Dialectic Isolation Audit
        </h3>
        {data.isIsolated ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-xs font-medium text-emerald-300">
            <ShieldCheck size={12} />
            Isolated
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-500/10 border border-red-500/30 text-xs font-medium text-red-300">
            <ShieldAlert size={12} />
            Contamination Detected
          </span>
        )}
      </div>

      {/* Description */}
      <p className="text-xs text-text-secondary mb-4">
        {data.isIsolated
          ? "The bull and bear cases were generated independently with no cross-contamination detected."
          : "Evidence of cross-contamination was found between the bull and bear cases. This may indicate the isolation pattern was violated."}
      </p>

      {/* Contamination evidence */}
      {data.contaminationEvidence.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-red-300">
            Evidence ({data.contaminationEvidence.length} finding{data.contaminationEvidence.length !== 1 ? "s" : ""})
          </h4>
          <ul className="space-y-1.5">
            {data.contaminationEvidence.map((evidence, i) => (
              <li
                key={i}
                className={cn(
                  "flex items-start gap-2 text-xs text-red-400",
                  "py-1.5 px-2 rounded bg-red-500/5"
                )}
              >
                <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
                <span>{evidence}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
