"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { cn } from "@/lib/utils";
import {
  runPersonaAnalysis,
  runTrioAnalysis,
  getAnalysisById,
  getAnalysesByTarget,
} from "@/lib/api/personas";
import type {
  PersonaAnalysis,
  PersonaName,
  TargetType,
  AnalysisMode,
} from "@/types/persona";
import { PERSONA_DISPLAY_NAMES } from "@/types/persona";
import VisserPanel from "./VisserPanel";
import MeldrumPanel from "./MeldrumPanel";
import WissnerGrossPanel from "./WissnerGrossPanel";
import TrioSummary from "./TrioSummary";
import {
  Loader2,
  AlertCircle,
  Send,
  ChevronDown,
  RefreshCw,
  Users,
  Eye,
  DollarSign,
  Zap,
} from "lucide-react";

// ─── Mode Options ──────────────────────────────────────────────────

type LaunchMode = "trio" | "visser" | "meldrum" | "wissner_gross";

const LAUNCH_OPTIONS: { value: LaunchMode; label: string; icon: typeof Users }[] = [
  { value: "trio",          label: "Run Trio Analysis",        icon: Users },
  { value: "visser",        label: "Ask Jordi Visser",         icon: Eye },
  { value: "meldrum",       label: "Ask Mark Meldrum",         icon: DollarSign },
  { value: "wissner_gross", label: "Ask Alex Wissner-Gross",   icon: Zap },
];

// ─── Props ─────────────────────────────────────────────────────────

interface PersonaLauncherProps {
  targetType: TargetType;
  targetId: number;
}

// ─── Polling Constants ─────────────────────────────────────────────

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 200; // ~10 minutes

// ─── Component ─────────────────────────────────────────────────────

export default function PersonaLauncher({
  targetType,
  targetId,
}: PersonaLauncherProps) {
  // Form state
  const [mode, setMode] = useState<LaunchMode>("trio");
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("structured");
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Polling state
  const [pollingId, setPollingId] = useState<number | null>(null);
  const [polling, setPolling] = useState(false);
  const pollCountRef = useRef(0);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Result state
  const [resultAnalyses, setResultAnalyses] = useState<PersonaAnalysis[]>([]);
  const [showResult, setShowResult] = useState(false);

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
      setPollingId(analysisId);
      setPolling(true);
      pollCountRef.current = 0;

      // Clear any existing timer
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }

      pollTimerRef.current = setInterval(async () => {
        pollCountRef.current += 1;

        if (pollCountRef.current > MAX_POLL_ATTEMPTS) {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          setPolling(false);
          setSubmitError("Analysis timed out. Please check the history panel later.");
          return;
        }

        try {
          if (isTrio) {
            // For trio, fetch all analyses for the target to get all persona results
            const response = await getAnalysesByTarget(targetType, targetId);
            // Find the most recent batch: filter analyses that share the same approximate createdAt
            // Or more simply: check the trio_summary record status
            const trioRecord = response.analyses.find(
              (a) => a.id === analysisId
            );

            if (
              trioRecord &&
              trioRecord.analysisResult &&
              (trioRecord.analysisResult as Record<string, unknown>).status !== "pending"
            ) {
              // Trio is done. Gather all related analyses from the same batch.
              // Use time proximity: analyses created within 5 minutes of each other
              const trioTime = new Date(trioRecord.createdAt).getTime();
              const batchAnalyses = response.analyses.filter((a) => {
                const diff = Math.abs(new Date(a.createdAt).getTime() - trioTime);
                return diff < 5 * 60 * 1000; // 5 minutes
              });

              if (pollTimerRef.current) clearInterval(pollTimerRef.current);
              setPolling(false);
              setResultAnalyses(batchAnalyses);
              setShowResult(true);
            }
          } else {
            // Single persona polling
            const analysis = await getAnalysisById(analysisId);
            if (
              analysis.analysisResult &&
              (analysis.analysisResult as Record<string, unknown>).status !== "pending"
            ) {
              if (pollTimerRef.current) clearInterval(pollTimerRef.current);
              setPolling(false);
              setResultAnalyses([analysis]);
              setShowResult(true);
            }
          }
        } catch {
          // Polling errors are non-fatal; continue polling
        }
      }, POLL_INTERVAL_MS);
    },
    [targetType, targetId]
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
          targetType,
          targetId,
          userPrompt: prompt.trim(),
          mode: analysisMode,
        });
        startPolling(response.id, true);
      } else {
        const response = await runPersonaAnalysis({
          personaName: mode as PersonaName,
          targetType,
          targetId,
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
  }, [mode, analysisMode, prompt, targetType, targetId, startPolling]);

  // ─── Retry Handler ─────────────────────────────────────────────

  const handleRetry = useCallback(() => {
    setSubmitError(null);
    handleSubmit();
  }, [handleSubmit]);

  // ─── Render ────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      {/* Launcher Card */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-text-primary">
            Persona Analysis
          </h3>
          <p className="text-xs text-text-secondary mt-0.5">
            Get expert perspectives on your investment thesis
          </p>
        </div>

        {/* Mode Selector */}
        <div className="mb-3">
          <label
            htmlFor="persona-mode"
            className="block text-[11px] font-medium text-text-secondary mb-1.5"
          >
            Analysis Mode
          </label>
          <div className="relative">
            <select
              id="persona-mode"
              value={mode}
              onChange={(e) => setMode(e.target.value as LaunchMode)}
              className={cn(
                "w-full appearance-none bg-white/5 border border-border rounded-lg",
                "px-3 py-2 pr-8 text-xs text-text-primary",
                "focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary",
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

        {/* Analysis Mode Toggle (Structured / Freeform) */}
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
            htmlFor="persona-prompt"
            className="block text-[11px] font-medium text-text-secondary mb-1.5"
          >
            Your Question / Thesis
          </label>
          <textarea
            id="persona-prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe your investment thesis or ask a specific question..."
            rows={4}
            className={cn(
              "w-full bg-white/5 border border-border rounded-lg",
              "px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary",
              "focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary",
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
              ? "bg-white/5 text-text-tertiary cursor-not-allowed"
              : "bg-primary text-white hover:bg-primary-hover"
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

        {/* Error Message */}
        {submitError && (
          <div className="mt-3 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 flex items-start gap-2">
            <AlertCircle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-red-400">{submitError}</p>
              <button
                onClick={handleRetry}
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
              {mode === "trio" ? "Trio analysis" : `${PERSONA_DISPLAY_NAMES[mode as PersonaName]} analysis`} in progress
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

          {/* Render appropriate panel based on mode */}
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
  );
}
