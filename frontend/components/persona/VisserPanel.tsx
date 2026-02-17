"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import MarkdownNarrative from "@/components/MarkdownNarrative";
import type { PersonaAnalysis, VisserResult } from "@/types/persona";
import {
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Eye,
  Target,
  Crosshair,
} from "lucide-react";

// ─── Verdict Color Config ──────────────────────────────────────────

const VERDICT_COLORS: Record<string, { bg: string; text: string }> = {
  PROCEED:  { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  CAUTION:  { bg: "bg-amber-500/10",   text: "text-amber-400" },
  AVOID:    { bg: "bg-red-500/10",     text: "text-red-400" },
};

const CONFIDENCE_COLORS: Record<string, { bg: string; text: string }> = {
  HIGH:   { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  MEDIUM: { bg: "bg-amber-500/10",   text: "text-amber-400" },
  LOW:    { bg: "bg-white/10",       text: "text-text-secondary" },
};

const SEVERITY_COLORS: Record<string, { bg: string; text: string }> = {
  HIGH:     { bg: "bg-red-500/10",    text: "text-red-400" },
  MEDIUM:   { bg: "bg-amber-500/10",  text: "text-amber-400" },
  LOW:      { bg: "bg-white/10",      text: "text-text-secondary" },
  CRITICAL: { bg: "bg-red-500/15",    text: "text-red-300" },
};

// ─── Props ─────────────────────────────────────────────────────────

interface VisserPanelProps {
  analysis: PersonaAnalysis;
}

// ─── Component ─────────────────────────────────────────────────────

export default function VisserPanel({ analysis }: VisserPanelProps) {
  const [narrativeExpanded, setNarrativeExpanded] = useState(false);

  // ─── Pending State ─────────────────────────────────────────────

  if (
    !analysis.analysisResult ||
    (analysis.analysisResult as Record<string, unknown>).status === "pending"
  ) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-purple-500/30 rounded-xl p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-purple-500/10">
            <Eye size={16} className="text-purple-400" />
          </div>
          <h4 className="text-sm font-semibold text-purple-400">
            Jordi Visser Analysis
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
            Visser Analysis Failed
          </h4>
        </div>
        <p className="text-xs text-red-400">
          {String((analysis.analysisResult as Record<string, unknown>).error)}
        </p>
      </div>
    );
  }

  // ─── Completed State ───────────────────────────────────────────

  const result = analysis.analysisResult as unknown as VisserResult;

  const verdictKey = (result.overall_verdict ?? "").toUpperCase();
  const verdictConfig = VERDICT_COLORS[verdictKey] ?? { bg: "bg-white/10", text: "text-text-secondary" };

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-purple-500/30 rounded-xl p-5 hover:border-purple-500/50 transition-all duration-200">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-purple-500/10">
          <Eye size={16} className="text-purple-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-purple-400">
            Jordi Visser Analysis
          </h4>
          <p className="text-[10px] text-text-secondary">
            Macro regime and opportunity assessment
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

      {/* Regime Classification */}
      {result.regime_classification && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Regime Classification
          </p>
          <div className="bg-purple-500/10 rounded-lg border border-purple-500/20 p-3">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold text-purple-300">
                {result.regime_classification.current_regime}
              </span>
              {result.regime_classification.confidence && (
                <span
                  className={cn(
                    "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium",
                    (CONFIDENCE_COLORS[result.regime_classification.confidence.toUpperCase()] ?? CONFIDENCE_COLORS.LOW).bg,
                    (CONFIDENCE_COLORS[result.regime_classification.confidence.toUpperCase()] ?? CONFIDENCE_COLORS.LOW).text
                  )}
                >
                  {result.regime_classification.confidence} confidence
                </span>
              )}
            </div>
            {result.regime_classification.description && (
              <p className="text-[11px] text-text-secondary leading-relaxed">
                {result.regime_classification.description}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Opportunity Map */}
      {result.opportunity_map && result.opportunity_map.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Opportunity Map
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {result.opportunity_map.map((opp, idx) => (
              <div
                key={idx}
                className="bg-white/5 rounded-lg border border-border p-3 hover:border-purple-500/30 transition-colors duration-150"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Target size={12} className="text-purple-400 flex-shrink-0" />
                  <span className="text-xs font-medium text-text-primary">
                    {opp.name}
                  </span>
                </div>
                {opp.description && (
                  <p className="text-[11px] text-text-secondary leading-relaxed mb-1.5">
                    {opp.description}
                  </p>
                )}
                <div className="flex items-center gap-1.5">
                  {opp.regime_alignment && (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium bg-purple-500/10 text-purple-400">
                      {opp.regime_alignment}
                    </span>
                  )}
                  {opp.conviction && (
                    <span
                      className={cn(
                        "inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium",
                        (CONFIDENCE_COLORS[opp.conviction.toUpperCase()] ?? CONFIDENCE_COLORS.LOW).bg,
                        (CONFIDENCE_COLORS[opp.conviction.toUpperCase()] ?? CONFIDENCE_COLORS.LOW).text
                      )}
                    >
                      {opp.conviction}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
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

      {/* Green Marbles */}
      {result.green_marbles && (
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Green Marbles Assessment
          </p>
          <div className="bg-emerald-500/10 rounded-lg border border-emerald-500/20 p-3">
            <div className="flex items-center gap-2 mb-1.5">
              <Crosshair size={12} className="text-emerald-400 flex-shrink-0" />
              <span className="text-xs font-bold font-mono text-emerald-400">
                {result.green_marbles.count} / {result.green_marbles.max}
              </span>
              {/* Visual bar */}
              <div
                className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden"
                aria-hidden="true"
              >
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all duration-300"
                  style={{
                    width: `${result.green_marbles.max > 0 ? (result.green_marbles.count / result.green_marbles.max) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>
            {result.green_marbles.assessment && (
              <p className="text-[11px] text-text-secondary leading-relaxed">
                {result.green_marbles.assessment}
              </p>
            )}
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
            className="inline-flex items-center gap-1.5 text-xs font-medium text-purple-400 hover:opacity-80 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1 rounded"
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
