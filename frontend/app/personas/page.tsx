"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { cn } from "@/lib/utils";
import {
  runPersonaAnalysis,
  runTrioAnalysis,
  getAnalysisById,
  getPersonaAnalyses,
  getAnalysesByTarget,
} from "@/lib/api/personas";
import type {
  PersonaAnalysis,
  PersonaName,
  AnalysisMode,
} from "@/types/persona";
import { PERSONA_DISPLAY_NAMES, PERSONA_COLORS } from "@/types/persona";
import { timeAgo } from "@/lib/utils";
import VisserPanel from "@/components/persona/VisserPanel";
import MeldrumPanel from "@/components/persona/MeldrumPanel";
import WissnerGrossPanel from "@/components/persona/WissnerGrossPanel";
import TrioSummary from "@/components/persona/TrioSummary";
import {
  Loader2,
  AlertCircle,
  Send,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Users,
  Eye,
  DollarSign,
  Zap,
  Brain,
  History,
  Clock,
} from "lucide-react";

// ─── Mode Options ──────────────────────────────────────────────────

type LaunchMode = "trio" | "visser" | "meldrum" | "wissner_gross";

const LAUNCH_OPTIONS: { value: LaunchMode; label: string; icon: typeof Users }[] = [
  { value: "trio",          label: "Run Trio Analysis",        icon: Users },
  { value: "visser",        label: "Ask Jordi Visser",         icon: Eye },
  { value: "meldrum",       label: "Ask Mark Meldrum",         icon: DollarSign },
  { value: "wissner_gross", label: "Ask Alex Wissner-Gross",   icon: Zap },
];

// ─── Constants ─────────────────────────────────────────────────────

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 200;

// ─── Helper: Extract verdict preview ───────────────────────────────

function getVerdictPreview(analysis: PersonaAnalysis): string | null {
  if (!analysis.analysisResult) return null;
  const result = analysis.analysisResult as Record<string, unknown>;
  if (result.status === "pending") return "Pending...";
  if (result.error) return "Failed";
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

// ─── Page Component ────────────────────────────────────────────────

export default function PersonasPage() {
  // Form state
  const [mode, setMode] = useState<LaunchMode>("trio");
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("structured");
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Polling state
  const [polling, setPolling] = useState(false);
  const pollCountRef = useRef(0);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Result state
  const [resultAnalyses, setResultAnalyses] = useState<PersonaAnalysis[]>([]);
  const [showResult, setShowResult] = useState(false);

  // History state
  const [history, setHistory] = useState<PersonaAnalysis[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [expandedHistoryId, setExpandedHistoryId] = useState<number | null>(null);

  // ─── Fetch History ─────────────────────────────────────────────

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const response = await getPersonaAnalyses({
        targetType: "standalone",
        limit: 50,
      });
      const sorted = [...response.analyses].sort(
        (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      );
      setHistory(sorted);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Failed to load history");
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // ─── Cleanup on unmount ────────────────────────────────────────

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, []);

  // ─── Poll for completion ───────────────────────────────────────

  const startPolling = useCallback(
    (analysisId: number, isTrio: boolean) => {
      setPolling(true);
      pollCountRef.current = 0;

      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }

      pollTimerRef.current = setInterval(async () => {
        pollCountRef.current += 1;

        if (pollCountRef.current > MAX_POLL_ATTEMPTS) {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          setPolling(false);
          setSubmitError("Analysis timed out. Check back later.");
          return;
        }

        try {
          const analysis = await getAnalysisById(analysisId);

          if (
            analysis.analysisResult &&
            (analysis.analysisResult as Record<string, unknown>).status !== "pending"
          ) {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
            setPolling(false);

            if (isTrio) {
              // For standalone trio, fetch related analyses by scanning recent standalone analyses
              const response = await getPersonaAnalyses({
                targetType: "standalone",
                limit: 10,
              });
              const trioTime = new Date(analysis.createdAt).getTime();
              const batchAnalyses = response.analyses.filter((a) => {
                const diff = Math.abs(new Date(a.createdAt).getTime() - trioTime);
                return diff < 5 * 60 * 1000;
              });
              setResultAnalyses(batchAnalyses);
            } else {
              setResultAnalyses([analysis]);
            }

            setShowResult(true);
            // Refresh history
            fetchHistory();
          }
        } catch {
          // Continue polling on error
        }
      }, POLL_INTERVAL_MS);
    },
    [fetchHistory]
  );

  // ─── Submit Handler ────────────────────────────────────────────

  const handleSubmit = useCallback(async () => {
    if (!prompt.trim()) return;

    setSubmitting(true);
    setSubmitError(null);
    setShowResult(false);
    setResultAnalyses([]);

    try {
      if (mode === "trio") {
        const response = await runTrioAnalysis({
          targetType: "standalone",
          userPrompt: prompt.trim(),
          mode: analysisMode,
        });
        startPolling(response.id, true);
      } else {
        const response = await runPersonaAnalysis({
          personaName: mode as PersonaName,
          targetType: "standalone",
          userPrompt: prompt.trim(),
          mode: analysisMode,
        });
        startPolling(response.id, false);
      }
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to submit analysis");
    } finally {
      setSubmitting(false);
    }
  }, [mode, analysisMode, prompt, startPolling]);

  // ─── History item batch helper ──────────────────────────────────

  const getTrioBatch = (trioAnalysis: PersonaAnalysis): PersonaAnalysis[] => {
    const trioTime = new Date(trioAnalysis.createdAt).getTime();
    return history.filter((a) => {
      const diff = Math.abs(new Date(a.createdAt).getTime() - trioTime);
      return diff < 5 * 60 * 1000;
    });
  };

  // Group history by date
  const groupedHistory = new Map<string, PersonaAnalysis[]>();
  for (const a of history) {
    const dateKey = new Date(a.createdAt).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
    const existing = groupedHistory.get(dateKey) ?? [];
    existing.push(a);
    groupedHistory.set(dateKey, existing);
  }

  // ─── Render ────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="animate-in">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center">
            <Brain size={20} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="font-display text-2xl font-bold text-text-primary">
              Persona Analysis
            </h1>
            <p className="text-xs text-text-secondary mt-0.5">
              Get expert investment perspectives from AI personas
            </p>
          </div>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Launcher + Results (2 cols) */}
        <div className="lg:col-span-2 space-y-4 animate-in-d1">
          {/* Launcher Card */}
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
            <div className="mb-4">
              <h3 className="text-sm font-semibold text-text-primary">
                New Analysis
              </h3>
              <p className="text-xs text-text-secondary mt-0.5">
                Paste your investment thesis or ask a question about any opportunity
              </p>
            </div>

            {/* Mode Selector */}
            <div className="mb-3">
              <label
                htmlFor="standalone-mode"
                className="block text-[11px] font-medium text-text-secondary mb-1.5"
              >
                Analysis Mode
              </label>
              <div className="relative">
                <select
                  id="standalone-mode"
                  value={mode}
                  onChange={(e) => setMode(e.target.value as LaunchMode)}
                  className={cn(
                    "w-full appearance-none bg-[rgba(10,15,26,0.6)] border border-border rounded-lg",
                    "px-3 py-2 pr-8 text-xs text-text-primary",
                    "focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary",
                    "transition-colors duration-200"
                  )}
                  disabled={submitting || polling}
                >
                  {LAUNCH_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value} className="bg-[#111827] text-[#f0f4ff]">
                      {opt.label}
                    </option>
                  ))}
                </select>
                <ChevronDown
                  size={14}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none"
                />
              </div>
            </div>

            {/* Output Style Toggle (Structured / Freeform) */}
            <div className="mb-3">
              <label className="block text-[11px] font-medium text-text-secondary mb-1.5">
                Output Style
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setAnalysisMode("structured")}
                  disabled={submitting || polling}
                  className={cn(
                    "flex-1 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200",
                    analysisMode === "structured"
                      ? "bg-primary/10 text-primary border-primary/30"
                      : "bg-white/5 text-text-secondary border-border hover:border-white/20"
                  )}
                >
                  Structured
                </button>
                <button
                  type="button"
                  onClick={() => setAnalysisMode("freeform")}
                  disabled={submitting || polling}
                  className={cn(
                    "flex-1 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200",
                    analysisMode === "freeform"
                      ? "bg-primary/10 text-primary border-primary/30"
                      : "bg-white/5 text-text-secondary border-border hover:border-white/20"
                  )}
                >
                  Freeform
                </button>
              </div>
              <p className="text-[10px] text-text-tertiary mt-1.5 leading-relaxed">
                {analysisMode === "structured"
                  ? "Each analyst follows a predefined template with scored sections (e.g. Regime Assessment, Conviction 1-10). Best for systematic comparison across analyses."
                  : "Each analyst keeps their expertise and analytical lens but responds freely without a forced template. Best for open-ended exploration where you want deeper, more creative reasoning."}
              </p>
            </div>

            {/* Prompt Textarea */}
            <div className="mb-3">
              <label
                htmlFor="standalone-prompt"
                className="block text-[11px] font-medium text-text-secondary mb-1.5"
              >
                Investment Thesis / Question
              </label>
              <textarea
                id="standalone-prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe your investment thesis, paste a research excerpt, or ask a specific question about an investment opportunity..."
                rows={6}
                className={cn(
                  "w-full bg-[rgba(10,15,26,0.6)] border border-border rounded-lg",
                  "px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary",
                  "focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary",
                  "resize-y transition-colors duration-200"
                )}
                disabled={submitting || polling}
              />
            </div>

            {/* Submit Button */}
            <button
              onClick={handleSubmit}
              disabled={submitting || polling || !prompt.trim()}
              className={cn(
                "inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium",
                "transition-all duration-200",
                "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
                submitting || polling || !prompt.trim()
                  ? "bg-white/10 text-text-tertiary cursor-not-allowed"
                  : "bg-primary text-[#050810] hover:bg-primary-hover shadow-sm"
              )}
            >
              {submitting ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Submitting...
                </>
              ) : polling ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Send size={14} />
                  Run Analysis
                </>
              )}
            </button>

            {/* Error */}
            {submitError && (
              <div className="mt-3 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 flex items-start gap-2">
                <AlertCircle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-red-400">{submitError}</p>
                  <button
                    onClick={() => { setSubmitError(null); handleSubmit(); }}
                    className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-red-300 hover:text-red-200 transition-colors duration-200"
                  >
                    <RefreshCw size={12} />
                    Retry
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Polling Status */}
          {polling && (
            <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-xl px-5 py-4 flex items-center gap-3">
              <Loader2 size={16} className="animate-spin text-indigo-400" />
              <div>
                <p className="text-xs font-medium text-indigo-300">
                  {mode === "trio"
                    ? "Trio analysis"
                    : `${PERSONA_DISPLAY_NAMES[mode as PersonaName]} analysis`}{" "}
                  in progress
                </p>
                <p className="text-[11px] text-indigo-400 mt-0.5">
                  This may take a few minutes. Results will appear automatically.
                </p>
              </div>
            </div>
          )}

          {/* Results */}
          {showResult && resultAnalyses.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <div className="h-px flex-1 bg-border" />
                <span className="text-[10px] font-medium text-text-tertiary uppercase tracking-wider">
                  Results
                </span>
                <div className="h-px flex-1 bg-border" />
              </div>

              {mode === "trio" ? (
                <TrioSummary analyses={resultAnalyses} />
              ) : (
                (() => {
                  const analysis = resultAnalyses[0];
                  if (!analysis) return null;
                  switch (mode) {
                    case "visser":
                      return <VisserPanel analysis={analysis} />;
                    case "meldrum":
                      return <MeldrumPanel analysis={analysis} />;
                    case "wissner_gross":
                      return <WissnerGrossPanel analysis={analysis} />;
                    default:
                      return null;
                  }
                })()
              )}
            </div>
          )}
        </div>

        {/* Right: History Panel (1 col) */}
        <div className="lg:col-span-1 animate-in-d2">
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5 sticky top-6">
            <div className="flex items-center gap-2 mb-4">
              <History size={14} className="text-text-tertiary" />
              <h3 className="text-sm font-semibold text-text-primary">
                History
              </h3>
              {!historyLoading && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-white/10 text-text-secondary">
                  {history.length}
                </span>
              )}
            </div>

            {/* History Loading */}
            {historyLoading && (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-10 bg-white/10 rounded-lg animate-pulse" />
                ))}
              </div>
            )}

            {/* History Error */}
            {historyError && !historyLoading && (
              <div className="text-center py-4">
                <AlertCircle size={20} className="mx-auto text-red-400 mb-1.5" />
                <p className="text-xs text-red-400">{historyError}</p>
                <button
                  onClick={fetchHistory}
                  className="mt-2 text-xs font-medium text-primary hover:text-primary-hover transition-colors duration-200"
                >
                  Try again
                </button>
              </div>
            )}

            {/* History Empty */}
            {!historyLoading && !historyError && history.length === 0 && (
              <div className="text-center py-6">
                <History size={20} className="mx-auto text-text-tertiary mb-2" />
                <p className="text-xs text-text-secondary">
                  No standalone analyses yet.
                </p>
              </div>
            )}

            {/* History Items */}
            {!historyLoading && !historyError && history.length > 0 && (
              <div className="space-y-3 max-h-[60vh] overflow-y-auto" role="list">
                {Array.from(groupedHistory.entries()).map(([dateLabel, dateAnalyses]) => (
                  <div key={dateLabel}>
                    <div className="flex items-center gap-2 mb-1.5">
                      <Clock size={10} className="text-text-tertiary" />
                      <span className="text-[10px] font-medium text-text-tertiary uppercase tracking-wider">
                        {dateLabel}
                      </span>
                    </div>
                    <div className="space-y-1" role="list">
                      {dateAnalyses.map((a) => {
                        const personaName = a.personaName as PersonaName;
                        const colors = PERSONA_COLORS[personaName] ?? PERSONA_COLORS.trio_summary;
                        const isExpanded = expandedHistoryId === a.id;
                        const verdict = getVerdictPreview(a);

                        return (
                          <div key={a.id} role="listitem">
                            <button
                              onClick={() =>
                                setExpandedHistoryId(isExpanded ? null : a.id)
                              }
                              className={cn(
                                "w-full flex items-center justify-between px-2.5 py-2 text-left rounded-lg",
                                "hover:bg-white/5 transition-colors duration-150",
                                "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1",
                                isExpanded && "bg-white/5"
                              )}
                              aria-expanded={isExpanded}
                            >
                              <div className="flex items-center gap-1.5 min-w-0">
                                <span
                                  className={cn(
                                    "inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium flex-shrink-0",
                                    colors.bg,
                                    colors.text
                                  )}
                                >
                                  {PERSONA_DISPLAY_NAMES[personaName]?.split(" ")[0] ?? personaName}
                                </span>
                                <span className="text-[10px] text-text-tertiary truncate">
                                  {timeAgo(a.createdAt)}
                                </span>
                              </div>
                              <div className="flex items-center gap-1">
                                {verdict && (
                                  <span
                                    className={cn(
                                      "text-[9px] font-medium",
                                      getVerdictColor(verdict)
                                    )}
                                  >
                                    {verdict}
                                  </span>
                                )}
                                {isExpanded ? (
                                  <ChevronUp size={10} className="text-text-tertiary" />
                                ) : (
                                  <ChevronDown size={10} className="text-text-tertiary" />
                                )}
                              </div>
                            </button>
                            {isExpanded && (
                              <div className="mt-1 mb-2">
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
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
