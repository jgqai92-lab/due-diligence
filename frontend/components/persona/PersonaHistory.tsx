"use client";

import { useState, useEffect, useCallback } from "react";
import { cn, timeAgo } from "@/lib/utils";
import { getAnalysesByTarget } from "@/lib/api/personas";
import type {
  PersonaAnalysis,
  TargetType,
  PersonaName,
} from "@/types/persona";
import { PERSONA_DISPLAY_NAMES, PERSONA_COLORS } from "@/types/persona";
import VisserPanel from "./VisserPanel";
import MeldrumPanel from "./MeldrumPanel";
import WissnerGrossPanel from "./WissnerGrossPanel";
import TrioSummary from "./TrioSummary";
import {
  Loader2,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  History,
} from "lucide-react";

// ─── Props ─────────────────────────────────────────────────────────

interface PersonaHistoryProps {
  targetType: TargetType;
  targetId: number;
}

// ─── Helper: Group analyses by date ────────────────────────────────

function groupByDate(analyses: PersonaAnalysis[]): Map<string, PersonaAnalysis[]> {
  const groups = new Map<string, PersonaAnalysis[]>();
  for (const a of analyses) {
    const dateKey = new Date(a.createdAt).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
    const existing = groups.get(dateKey) ?? [];
    existing.push(a);
    groups.set(dateKey, existing);
  }
  return groups;
}

// ─── Helper: Extract a short verdict preview ───────────────────────

function getVerdictPreview(analysis: PersonaAnalysis): string | null {
  if (!analysis.analysisResult) return null;
  const result = analysis.analysisResult as Record<string, unknown>;

  if (result.status === "pending") return "Pending...";
  if (result.error) return "Failed";

  // Try common verdict fields
  if (typeof result.overall_verdict === "string") return result.overall_verdict;
  if (typeof result.consensus_verdict === "string") return result.consensus_verdict;
  if (typeof result.action_recommendation === "string") return result.action_recommendation;

  return "Completed";
}

function getVerdictColor(verdict: string | null): string {
  if (!verdict) return "text-text-tertiary";
  const upper = (verdict ?? "").toUpperCase();

  if (["PROCEED", "BUY", "STRONG_BUY", "UNDERVALUED", "EXPONENTIAL"].includes(upper))
    return "text-emerald-400";
  if (["CAUTION", "HOLD", "FAIR", "LINEAR", "NEEDS_MORE_RESEARCH"].includes(upper))
    return "text-amber-400";
  if (["AVOID", "SELL", "STRONG_SELL", "OVERVALUED", "UNINVESTABLE", "DECAYING"].includes(upper))
    return "text-red-400";
  if (upper === "PENDING...") return "text-text-tertiary";
  if (upper === "FAILED") return "text-red-400";

  return "text-text-secondary";
}

// ─── Component ─────────────────────────────────────────────────────

export default function PersonaHistory({
  targetType,
  targetId,
}: PersonaHistoryProps) {
  const [analyses, setAnalyses] = useState<PersonaAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getAnalysesByTarget(targetType, targetId);
      // Sort newest first
      const sorted = [...response.analyses].sort(
        (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      );
      setAnalyses(sorted);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, [targetType, targetId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const toggleExpand = (id: number) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  // ─── Loading State ─────────────────────────────────────────────

  if (loading) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className="h-4 w-32 bg-white/10 rounded animate-pulse" />
        </div>
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 bg-white/10 rounded-lg animate-pulse" />
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
          onClick={fetchData}
          className="mt-3 text-xs font-medium text-primary hover:text-primary-hover transition-colors duration-200"
        >
          Try again
        </button>
      </div>
    );
  }

  // ─── Empty State ───────────────────────────────────────────────

  if (analyses.length === 0) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-3">
          <History size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-secondary">
          No persona analyses yet for this target.
        </p>
        <p className="text-xs text-text-secondary mt-1">
          Use the launcher above to run your first analysis.
        </p>
      </div>
    );
  }

  // ─── Grouped by date ───────────────────────────────────────────

  const grouped = groupByDate(analyses);

  // For expanded trio summaries, gather all same-batch analyses
  const getTrioBatch = (trioAnalysis: PersonaAnalysis): PersonaAnalysis[] => {
    const trioTime = new Date(trioAnalysis.createdAt).getTime();
    return analyses.filter((a) => {
      const diff = Math.abs(new Date(a.createdAt).getTime() - trioTime);
      return diff < 5 * 60 * 1000; // 5 minutes
    });
  };

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <History size={14} className="text-text-tertiary" />
        <h3 className="text-sm font-semibold text-text-primary">Analysis History</h3>
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-white/10 text-text-secondary">
          {analyses.length}
        </span>
      </div>

      <div className="space-y-4" role="list" aria-label="Persona analysis history">
        {Array.from(grouped.entries()).map(([dateLabel, dateAnalyses]) => (
          <div key={dateLabel}>
            {/* Date Header */}
            <div className="flex items-center gap-2 mb-2">
              <Clock size={10} className="text-text-tertiary" />
              <span className="text-[10px] font-medium text-text-tertiary uppercase tracking-wider">
                {dateLabel}
              </span>
              <div className="h-px flex-1 bg-border" />
            </div>

            {/* Items */}
            <div className="space-y-1.5" role="list">
              {dateAnalyses.map((a) => {
                const personaName = a.personaName as PersonaName;
                const colors = PERSONA_COLORS[personaName] ?? PERSONA_COLORS.trio_summary;
                const isExpanded = expandedId === a.id;
                const verdict = getVerdictPreview(a);

                return (
                  <div key={a.id} className="rounded-lg overflow-hidden" role="listitem">
                    <button
                      onClick={() => toggleExpand(a.id)}
                      className={cn(
                        "w-full flex items-center justify-between px-3 py-2.5 text-left",
                        "hover:bg-white/5 transition-colors duration-150 rounded-lg",
                        "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1",
                        isExpanded && "bg-white/5"
                      )}
                      aria-expanded={isExpanded}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className={cn(
                            "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0",
                            colors.bg,
                            colors.text
                          )}
                        >
                          {PERSONA_DISPLAY_NAMES[personaName] ?? personaName}
                        </span>
                        <span className="text-[10px] text-text-tertiary flex-shrink-0">
                          {timeAgo(a.createdAt)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {verdict && (
                          <span
                            className={cn(
                              "text-[10px] font-medium",
                              getVerdictColor(verdict)
                            )}
                          >
                            {verdict}
                          </span>
                        )}
                        {isExpanded ? (
                          <ChevronUp size={12} className="text-text-tertiary flex-shrink-0" />
                        ) : (
                          <ChevronDown size={12} className="text-text-tertiary flex-shrink-0" />
                        )}
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="px-2 pb-3 mt-1">
                        {personaName === "trio_summary" ? (
                          <TrioSummary analyses={getTrioBatch(a)} />
                        ) : personaName === "visser" ? (
                          <VisserPanel analysis={a} />
                        ) : personaName === "meldrum" ? (
                          <MeldrumPanel analysis={a} />
                        ) : personaName === "wissner_gross" ? (
                          <WissnerGrossPanel analysis={a} />
                        ) : null}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
