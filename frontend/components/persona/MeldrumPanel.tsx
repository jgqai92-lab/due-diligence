"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import MarkdownNarrative from "@/components/MarkdownNarrative";
import type { PersonaAnalysis, MeldrumResult } from "@/types/persona";
import {
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Clock,
} from "lucide-react";

// ─── Verdict Color Config ──────────────────────────────────────────

const VERDICT_COLORS: Record<string, { bg: string; text: string }> = {
  UNDERVALUED:   { bg: "bg-emerald-500/10",  text: "text-emerald-400" },
  FAIR:          { bg: "bg-amber-500/10",    text: "text-amber-400" },
  OVERVALUED:    { bg: "bg-red-500/10",      text: "text-red-400" },
  UNINVESTABLE:  { bg: "bg-red-500/15",      text: "text-red-300" },
};

const SEVERITY_COLORS: Record<string, { bg: string; text: string }> = {
  HIGH:     { bg: "bg-red-500/10",    text: "text-red-400" },
  MEDIUM:   { bg: "bg-amber-500/10",  text: "text-amber-400" },
  LOW:      { bg: "bg-white/10",      text: "text-text-secondary" },
  CRITICAL: { bg: "bg-red-500/15",    text: "text-red-300" },
};

// ─── Props ─────────────────────────────────────────────────────────

interface MeldrumPanelProps {
  analysis: PersonaAnalysis;
}

// ─── Component ─────────────────────────────────────────────────────

export default function MeldrumPanel({ analysis }: MeldrumPanelProps) {
  const [narrativeExpanded, setNarrativeExpanded] = useState(false);

  // ─── Pending State ─────────────────────────────────────────────

  if (
    !analysis.analysisResult ||
    (analysis.analysisResult as Record<string, unknown>).status === "pending"
  ) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-sky-500/30 rounded-xl p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-sky-500/10">
            <DollarSign size={16} className="text-sky-400" />
          </div>
          <h4 className="text-sm font-semibold text-sky-400">
            Mark Meldrum Analysis
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
            Meldrum Analysis Failed
          </h4>
        </div>
        <p className="text-xs text-red-400">
          {String((analysis.analysisResult as Record<string, unknown>).error)}
        </p>
      </div>
    );
  }

  // ─── Completed State ───────────────────────────────────────────

  const result = analysis.analysisResult as unknown as MeldrumResult;

  const verdictKey = (result.overall_verdict ?? "").toUpperCase();
  const verdictConfig = VERDICT_COLORS[verdictKey] ?? { bg: "bg-white/10", text: "text-text-secondary" };

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-sky-500/30 rounded-xl p-5 hover:border-sky-500/50 transition-all duration-200">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-sky-500/10">
          <DollarSign size={16} className="text-sky-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-sky-400">
            Mark Meldrum Analysis
          </h4>
          <p className="text-[10px] text-text-secondary">
            Fundamental valuation and financial model assessment
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

      {/* Fundamental Assessment */}
      {result.fundamental_assessment && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Fundamental Assessment
          </p>
          <div className="bg-sky-500/10 rounded-lg border border-sky-500/20 p-3">
            {result.fundamental_assessment.summary && (
              <p className="text-xs text-text-secondary leading-relaxed mb-2">
                {result.fundamental_assessment.summary}
              </p>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Strengths */}
              {result.fundamental_assessment.strengths &&
                result.fundamental_assessment.strengths.length > 0 && (
                  <div>
                    <p className="text-[10px] font-medium text-emerald-400 uppercase tracking-wider mb-1">
                      Strengths
                    </p>
                    <ul className="space-y-1" role="list">
                      {result.fundamental_assessment.strengths.map((s, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <TrendingUp
                            size={10}
                            className="text-emerald-400 mt-0.5 flex-shrink-0"
                            aria-hidden="true"
                          />
                          <span className="text-[11px] text-text-secondary leading-relaxed">
                            {s}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              {/* Weaknesses */}
              {result.fundamental_assessment.weaknesses &&
                result.fundamental_assessment.weaknesses.length > 0 && (
                  <div>
                    <p className="text-[10px] font-medium text-red-400 uppercase tracking-wider mb-1">
                      Weaknesses
                    </p>
                    <ul className="space-y-1" role="list">
                      {result.fundamental_assessment.weaknesses.map((w, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <TrendingDown
                            size={10}
                            className="text-red-400 mt-0.5 flex-shrink-0"
                            aria-hidden="true"
                          />
                          <span className="text-[11px] text-text-secondary leading-relaxed">
                            {w}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>
          </div>
        </div>
      )}

      {/* Valuation Reality Check */}
      {result.valuation_reality_check && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Valuation Reality Check
          </p>
          <div className="bg-white/5 rounded-lg border border-border p-3">
            {result.valuation_reality_check.assessment && (
              <p className="text-xs text-text-secondary leading-relaxed mb-2">
                {result.valuation_reality_check.assessment}
              </p>
            )}
            <div className="flex flex-wrap gap-3">
              {result.valuation_reality_check.fair_value_range && (
                <div>
                  <p className="text-[10px] font-medium text-text-secondary">Fair Value Range</p>
                  <p className="text-xs font-bold font-mono text-sky-400">
                    {result.valuation_reality_check.fair_value_range}
                  </p>
                </div>
              )}
              {result.valuation_reality_check.current_vs_fair && (
                <div>
                  <p className="text-[10px] font-medium text-text-secondary">Current vs Fair</p>
                  <p className="text-xs font-bold font-mono text-text-primary">
                    {result.valuation_reality_check.current_vs_fair}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Financial Model Flags */}
      {result.financial_model_flags && result.financial_model_flags.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Financial Model Flags ({result.financial_model_flags.length})
          </p>
          <div className="space-y-1.5">
            {result.financial_model_flags.map((flag, idx) => {
              const sevConfig = SEVERITY_COLORS[flag.severity?.toUpperCase()] ?? SEVERITY_COLORS.LOW;
              return (
                <div
                  key={idx}
                  className="flex items-start gap-2 p-2 rounded-lg bg-amber-500/10 border border-amber-500/20"
                >
                  <AlertTriangle
                    size={12}
                    className="text-amber-400 mt-0.5 flex-shrink-0"
                    aria-hidden="true"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="text-xs font-medium text-amber-300">
                        {flag.flag}
                      </span>
                      <span
                        className={cn(
                          "inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium",
                          sevConfig.bg,
                          sevConfig.text
                        )}
                      >
                        {flag.severity}
                      </span>
                    </div>
                    {flag.explanation && (
                      <p className="text-[11px] text-amber-400 leading-relaxed">
                        {flag.explanation}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Duration Classification */}
      {result.duration_classification && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Duration Classification
          </p>
          <div className="flex items-center gap-2">
            <Clock size={14} className="text-sky-400 flex-shrink-0" />
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-500/10 text-sky-400">
              {result.duration_classification.duration}
            </span>
          </div>
          {result.duration_classification.reasoning && (
            <p className="text-[11px] text-text-secondary leading-relaxed mt-1.5 ml-6">
              {result.duration_classification.reasoning}
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
            className="inline-flex items-center gap-1.5 text-xs font-medium text-sky-400 hover:opacity-80 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1 rounded"
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
