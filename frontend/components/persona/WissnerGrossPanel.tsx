"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import MarkdownNarrative from "@/components/MarkdownNarrative";
import type { PersonaAnalysis, WissnerGrossResult } from "@/types/persona";
import {
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Zap,
  Shield,
  Database,
  RefreshCw,
  Activity,
} from "lucide-react";

// ─── Verdict Color Config ──────────────────────────────────────────

const VERDICT_COLORS: Record<string, { bg: string; text: string }> = {
  EXPONENTIAL: { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  LINEAR:      { bg: "bg-amber-500/10",   text: "text-amber-400" },
  DECAYING:    { bg: "bg-red-500/10",     text: "text-red-400" },
};

const MOAT_COLORS: Record<string, { bg: string; text: string }> = {
  DOMINANT:  { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  STRONG:    { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  MODERATE:  { bg: "bg-amber-500/10",   text: "text-amber-400" },
  WEAK:      { bg: "bg-orange-500/10",  text: "text-orange-400" },
  NONE:      { bg: "bg-white/10",       text: "text-text-secondary" },
};

const SEVERITY_COLORS: Record<string, { bg: string; text: string }> = {
  HIGH:     { bg: "bg-red-500/10",    text: "text-red-400" },
  MEDIUM:   { bg: "bg-amber-500/10",  text: "text-amber-400" },
  LOW:      { bg: "bg-white/10",      text: "text-text-secondary" },
  CRITICAL: { bg: "bg-red-500/15",    text: "text-red-300" },
};

// ─── Score Bar Color ────────────────────────────────────────────────

function scoreBarColor(score: number, max: number): string {
  const pct = max > 0 ? score / max : 0;
  if (pct >= 0.7) return "bg-emerald-500";
  if (pct >= 0.4) return "bg-amber-500";
  return "bg-red-400";
}

function scoreTextColor(score: number, max: number): string {
  const pct = max > 0 ? score / max : 0;
  if (pct >= 0.7) return "text-emerald-400";
  if (pct >= 0.4) return "text-amber-400";
  return "text-red-400";
}

// ─── Props ─────────────────────────────────────────────────────────

interface WissnerGrossPanelProps {
  analysis: PersonaAnalysis;
}

// ─── Component ─────────────────────────────────────────────────────

export default function WissnerGrossPanel({ analysis }: WissnerGrossPanelProps) {
  const [narrativeExpanded, setNarrativeExpanded] = useState(false);

  // ─── Pending State ─────────────────────────────────────────────

  if (
    !analysis.analysisResult ||
    (analysis.analysisResult as Record<string, unknown>).status === "pending"
  ) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-orange-500/30 rounded-xl p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-orange-500/10">
            <Zap size={16} className="text-orange-400" />
          </div>
          <h4 className="text-sm font-semibold text-orange-400">
            Alex Wissner-Gross Analysis
          </h4>
        </div>
        <div className="flex items-center gap-2 text-text-tertiary">
          <Loader2 size={14} className="animate-spin" />
          <p className="text-xs">Analysis in progress...</p>
        </div>
      </div>
    );
  }

  // ─── Error State ───────────────────────────────────────────────

  if ((analysis.analysisResult as Record<string, unknown>).error) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-red-500/30 rounded-xl p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-red-500/10">
            <AlertCircle size={16} className="text-red-400" />
          </div>
          <h4 className="text-sm font-semibold text-red-400">
            Wissner-Gross Analysis Failed
          </h4>
        </div>
        <p className="text-xs text-red-400">
          {String((analysis.analysisResult as Record<string, unknown>).error)}
        </p>
      </div>
    );
  }

  // ─── Completed State ───────────────────────────────────────────

  const result = analysis.analysisResult as unknown as WissnerGrossResult;

  const verdictKey = (result.overall_verdict ?? "").toUpperCase();
  const verdictConfig = VERDICT_COLORS[verdictKey] ?? { bg: "bg-white/10", text: "text-text-secondary" };

  const expScore = result.exponential_score?.score ?? 0;
  const expMax = result.exponential_score?.max ?? 10;
  const phaseProb = result.phase_transition_probability?.probability ?? 0;

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-orange-500/30 rounded-xl p-5 hover:border-orange-500/50 transition-all duration-200">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-orange-500/10">
          <Zap size={16} className="text-orange-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-orange-400">
            Alex Wissner-Gross Analysis
          </h4>
          <p className="text-[10px] text-text-secondary">
            Exponential growth and phase transition assessment
          </p>
        </div>
        <span
          className={cn(
            "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
            verdictConfig.bg,
            verdictConfig.text
          )}
        >
          {result.overall_verdict}
        </span>
      </div>

      {/* Exponential Score Gauge */}
      {result.exponential_score && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Exponential Score
          </p>
          <div className="bg-orange-500/10 rounded-lg border border-orange-500/20 p-3">
            <div className="flex items-center gap-3 mb-1.5">
              <span
                className={cn(
                  "text-2xl font-bold font-mono",
                  scoreTextColor(expScore, expMax)
                )}
              >
                {expScore.toFixed(1)}
              </span>
              <span className="text-xs text-text-secondary">/ {expMax}</span>
              {/* Visual bar */}
              <div
                className="flex-1 h-3 bg-white/10 rounded-full overflow-hidden"
                role="progressbar"
                aria-valuenow={expScore}
                aria-valuemin={0}
                aria-valuemax={expMax}
                aria-label={`Exponential score: ${expScore} out of ${expMax}`}
              >
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-300",
                    scoreBarColor(expScore, expMax)
                  )}
                  style={{ width: `${expMax > 0 ? (expScore / expMax) * 100 : 0}%` }}
                />
              </div>
            </div>
            {result.exponential_score.reasoning && (
              <p className="text-[11px] text-text-secondary leading-relaxed">
                {result.exponential_score.reasoning}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Phase Transition Probability */}
      {result.phase_transition_probability && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Phase Transition Probability
          </p>
          <div className="bg-white/5 rounded-lg border border-border p-3">
            <div className="flex items-center gap-3 mb-1.5">
              <Activity size={14} className="text-orange-400 flex-shrink-0" />
              <span
                className={cn(
                  "text-lg font-bold font-mono",
                  phaseProb >= 0.7 ? "text-emerald-400" : phaseProb >= 0.4 ? "text-amber-400" : "text-red-400"
                )}
              >
                {(phaseProb * 100).toFixed(0)}%
              </span>
              {/* Visual bar */}
              <div
                className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden"
                role="progressbar"
                aria-valuenow={phaseProb * 100}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`Phase transition probability: ${(phaseProb * 100).toFixed(0)}%`}
              >
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-300",
                    phaseProb >= 0.7 ? "bg-emerald-500" : phaseProb >= 0.4 ? "bg-amber-500" : "bg-red-400"
                  )}
                  style={{ width: `${phaseProb * 100}%` }}
                />
              </div>
            </div>
            {result.phase_transition_probability.description && (
              <p className="text-[11px] text-text-secondary leading-relaxed">
                {result.phase_transition_probability.description}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Dataset Moat */}
      {result.dataset_moat && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Dataset Moat
          </p>
          <div className="flex items-center gap-2">
            <Database size={14} className="text-orange-400 flex-shrink-0" />
            <span
              className={cn(
                "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                (MOAT_COLORS[result.dataset_moat.strength?.toUpperCase()] ?? MOAT_COLORS.NONE).bg,
                (MOAT_COLORS[result.dataset_moat.strength?.toUpperCase()] ?? MOAT_COLORS.NONE).text
              )}
            >
              {result.dataset_moat.strength}
            </span>
          </div>
          {result.dataset_moat.description && (
            <p className="text-[11px] text-text-secondary leading-relaxed mt-1.5 ml-6">
              {result.dataset_moat.description}
            </p>
          )}
        </div>
      )}

      {/* Causal Entropy */}
      {result.causal_entropy && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Causal Entropy Assessment
          </p>
          <div className="bg-white/5 rounded-lg border border-border p-3">
            <div className="flex items-center gap-2 mb-1">
              <Shield size={12} className="text-orange-400 flex-shrink-0" />
              <span className="text-xs font-bold text-text-primary">
                {result.causal_entropy.assessment}
              </span>
            </div>
            {result.causal_entropy.description && (
              <p className="text-[11px] text-text-secondary leading-relaxed">
                {result.causal_entropy.description}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Recursive Improvement */}
      {result.recursive_improvement && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Recursive Improvement
          </p>
          <div className="flex items-center gap-2">
            <RefreshCw size={14} className="text-orange-400 flex-shrink-0" />
            <span
              className={cn(
                "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                result.recursive_improvement.present
                  ? "bg-emerald-500/10 text-emerald-400"
                  : "bg-white/10 text-text-secondary"
              )}
            >
              {result.recursive_improvement.present ? "Present" : "Not Detected"}
            </span>
          </div>
          {result.recursive_improvement.description && (
            <p className="text-[11px] text-text-secondary leading-relaxed mt-1.5 ml-6">
              {result.recursive_improvement.description}
            </p>
          )}
        </div>
      )}

      {/* Kill Conditions */}
      {result.kill_conditions && result.kill_conditions.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Kill Conditions
          </p>
          <div className="space-y-1.5">
            {result.kill_conditions.map((kc, idx) => {
              const sevConfig = SEVERITY_COLORS[kc.severity?.toUpperCase()] ?? SEVERITY_COLORS.LOW;
              return (
                <div
                  key={idx}
                  className="flex items-start gap-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20"
                >
                  <AlertTriangle
                    size={12}
                    className="text-red-400 mt-0.5 flex-shrink-0"
                    aria-hidden="true"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="text-xs font-medium text-red-300">
                        {kc.condition}
                      </span>
                      <span
                        className={cn(
                          "inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium",
                          sevConfig.bg,
                          sevConfig.text
                        )}
                      >
                        {kc.severity}
                      </span>
                    </div>
                    {kc.explanation && (
                      <p className="text-[11px] text-red-400 leading-relaxed">
                        {kc.explanation}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Verdict Reasoning */}
      {result.verdict_reasoning && (
        <div className="mb-3">
          <p className="text-[11px] font-medium text-text-secondary mb-1">
            Verdict Reasoning
          </p>
          <p className="text-xs text-text-secondary leading-relaxed">
            {result.verdict_reasoning}
          </p>
        </div>
      )}

      {/* Collapsible Raw Narrative */}
      {analysis.rawResponse && (
        <div className="mt-3">
          <button
            onClick={() => setNarrativeExpanded(!narrativeExpanded)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-orange-400 hover:opacity-80 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1 rounded"
            aria-expanded={narrativeExpanded}
          >
            {narrativeExpanded ? "Hide full narrative" : "Read full narrative"}
            {narrativeExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {narrativeExpanded && (
            <div className="mt-2 p-3 bg-white/5 rounded-lg border border-border">
              <MarkdownNarrative content={analysis.rawResponse} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
