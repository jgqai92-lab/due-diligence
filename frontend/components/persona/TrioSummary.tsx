"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import MarkdownNarrative from "@/components/MarkdownNarrative";
import type {
  PersonaAnalysis,
  TrioSummaryResult,
  PersonaName,
} from "@/types/persona";
import { PERSONA_DISPLAY_NAMES } from "@/types/persona";
import VisserPanel from "./VisserPanel";
import MeldrumPanel from "./MeldrumPanel";
import WissnerGrossPanel from "./WissnerGrossPanel";
import {
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Users,
  Target,
} from "lucide-react";

// ─── Action Recommendation Colors ──────────────────────────────────

const ACTION_COLORS: Record<string, { bg: string; text: string }> = {
  BUY:                 { bg: "bg-emerald-500/10",  text: "text-emerald-400" },
  HOLD:                { bg: "bg-amber-500/10",    text: "text-amber-400" },
  AVOID:               { bg: "bg-red-500/10",      text: "text-red-400" },
  NEEDS_MORE_RESEARCH: { bg: "bg-sky-500/10",      text: "text-sky-400" },
};

const CONSENSUS_COLORS: Record<string, { bg: string; text: string }> = {
  STRONG_BUY:     { bg: "bg-emerald-500/15", text: "text-emerald-300" },
  BUY:            { bg: "bg-emerald-500/10",  text: "text-emerald-400" },
  HOLD:           { bg: "bg-amber-500/10",    text: "text-amber-400" },
  SELL:           { bg: "bg-red-500/10",      text: "text-red-400" },
  STRONG_SELL:    { bg: "bg-red-500/15",      text: "text-red-300" },
  MIXED:          { bg: "bg-white/10",        text: "text-text-secondary" },
  PROCEED:        { bg: "bg-emerald-500/10",  text: "text-emerald-400" },
  CAUTION:        { bg: "bg-amber-500/10",    text: "text-amber-400" },
  AVOID:          { bg: "bg-red-500/10",      text: "text-red-400" },
};

const SEVERITY_COLORS: Record<string, { bg: string; text: string }> = {
  HIGH:     { bg: "bg-red-500/10",    text: "text-red-400" },
  MEDIUM:   { bg: "bg-amber-500/10",  text: "text-amber-400" },
  LOW:      { bg: "bg-white/10",      text: "text-text-secondary" },
  CRITICAL: { bg: "bg-red-500/15",    text: "text-red-300" },
};

// ─── Conviction Bar Color ──────────────────────────────────────────

function convictionColor(score: number): string {
  if (score >= 7) return "bg-emerald-500";
  if (score >= 4) return "bg-amber-500";
  return "bg-red-400";
}

function convictionTextColor(score: number): string {
  if (score >= 7) return "text-emerald-400";
  if (score >= 4) return "text-amber-400";
  return "text-red-400";
}

// ─── Props ─────────────────────────────────────────────────────────

interface TrioSummaryProps {
  analyses: PersonaAnalysis[];
}

// ─── Component ─────────────────────────────────────────────────────

export default function TrioSummary({ analyses }: TrioSummaryProps) {
  const [expandedPanels, setExpandedPanels] = useState<Record<string, boolean>>({});

  // Find each persona analysis
  const trioAnalysis = analyses.find((a) => a.personaName === "trio_summary");
  const visserAnalysis = analyses.find((a) => a.personaName === "visser");
  const meldrumAnalysis = analyses.find((a) => a.personaName === "meldrum");
  const wissnerGrossAnalysis = analyses.find((a) => a.personaName === "wissner_gross");

  const togglePanel = (name: string) => {
    setExpandedPanels((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  // ─── No Trio Summary Yet ────────────────────────────────────────

  if (!trioAnalysis) {
    return (
      <div className="space-y-4">
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-indigo-500/30 rounded-xl p-5 text-center py-12">
          <Users size={32} className="mx-auto text-text-tertiary mb-3" />
          <p className="text-sm font-medium text-text-secondary">
            Trio summary not available
          </p>
          <p className="text-xs text-text-secondary mt-1">
            Individual persona analyses may still be in progress.
          </p>
        </div>

        {/* Show whatever individual analyses are available */}
        {visserAnalysis && <VisserPanel analysis={visserAnalysis} />}
        {meldrumAnalysis && <MeldrumPanel analysis={meldrumAnalysis} />}
        {wissnerGrossAnalysis && <WissnerGrossPanel analysis={wissnerGrossAnalysis} />}
      </div>
    );
  }

  // ─── Pending State ──────────────────────────────────────────────

  const isPending =
    !trioAnalysis.analysisResult ||
    (trioAnalysis.analysisResult as Record<string, unknown>).status === "pending";

  if (isPending) {
    return (
      <div className="space-y-4">
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-indigo-500/30 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-indigo-500/10">
              <Users size={16} className="text-indigo-400" />
            </div>
            <h4 className="text-sm font-semibold text-indigo-400">
              Trio Summary
            </h4>
          </div>
          <div className="flex items-center gap-2 text-text-tertiary">
            <Loader2 size={14} className="animate-spin" />
            <p className="text-xs">Synthesizing trio analysis...</p>
          </div>
        </div>

        {/* Show individual analyses during pending trio */}
        {visserAnalysis && <VisserPanel analysis={visserAnalysis} />}
        {meldrumAnalysis && <MeldrumPanel analysis={meldrumAnalysis} />}
        {wissnerGrossAnalysis && <WissnerGrossPanel analysis={wissnerGrossAnalysis} />}
      </div>
    );
  }

  // ─── Error State ────────────────────────────────────────────────

  if ((trioAnalysis.analysisResult as Record<string, unknown>).error) {
    return (
      <div className="space-y-4">
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-red-500/30 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-red-500/10">
              <AlertCircle size={16} className="text-red-400" />
            </div>
            <h4 className="text-sm font-semibold text-red-400">
              Trio Summary Failed
            </h4>
          </div>
          <p className="text-xs text-red-400">
            {String((trioAnalysis.analysisResult as Record<string, unknown>).error)}
          </p>
        </div>

        {/* Show individual analyses even on trio failure */}
        {visserAnalysis && <VisserPanel analysis={visserAnalysis} />}
        {meldrumAnalysis && <MeldrumPanel analysis={meldrumAnalysis} />}
        {wissnerGrossAnalysis && <WissnerGrossPanel analysis={wissnerGrossAnalysis} />}
      </div>
    );
  }

  // ─── Completed State ────────────────────────────────────────────

  const result = trioAnalysis.analysisResult as unknown as TrioSummaryResult;

  const consensusKey = (result.consensus_verdict ?? "").toUpperCase();
  const consensusConfig = CONSENSUS_COLORS[consensusKey] ?? { bg: "bg-white/10", text: "text-text-secondary" };

  const actionKey = (result.action_recommendation ?? "").toUpperCase();
  const actionConfig = ACTION_COLORS[actionKey] ?? { bg: "bg-white/10", text: "text-text-secondary" };

  const convictionScore = result.composite_conviction_score ?? 0;

  const individualPanels: { name: PersonaName; label: string; analysis: PersonaAnalysis | undefined }[] = [
    { name: "visser", label: PERSONA_DISPLAY_NAMES.visser, analysis: visserAnalysis },
    { name: "meldrum", label: PERSONA_DISPLAY_NAMES.meldrum, analysis: meldrumAnalysis },
    { name: "wissner_gross", label: PERSONA_DISPLAY_NAMES.wissner_gross, analysis: wissnerGrossAnalysis },
  ];

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Trio Summary Card */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-indigo-500/30 rounded-xl p-5 hover:border-indigo-500/50 transition-all duration-200">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-indigo-500/10">
            <Users size={16} className="text-indigo-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-indigo-400">
              Trio Summary
            </h4>
            <p className="text-[10px] text-text-secondary">
              Synthesized perspective from all three personas
            </p>
          </div>
        </div>

        {/* Top Badges Row */}
        <div className="flex flex-wrap items-center gap-2 mb-4">
          {/* Consensus Verdict */}
          <div>
            <p className="text-[10px] font-medium text-text-secondary mb-1">Consensus</p>
            <span
              className={cn(
                "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                consensusConfig.bg,
                consensusConfig.text
              )}
            >
              {result.consensus_verdict}
            </span>
          </div>

          {/* Action Recommendation */}
          <div>
            <p className="text-[10px] font-medium text-text-secondary mb-1">Action</p>
            <span
              className={cn(
                "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                actionConfig.bg,
                actionConfig.text
              )}
            >
              {result.action_recommendation}
            </span>
          </div>
        </div>

        {/* Composite Conviction Score */}
        <div className="mb-4">
          <p className="text-[11px] font-medium text-text-secondary mb-2">
            Composite Conviction Score
          </p>
          <div className="flex items-center gap-3">
            <span
              className={cn(
                "text-2xl font-bold font-mono",
                convictionTextColor(convictionScore)
              )}
            >
              {convictionScore.toFixed(1)}
            </span>
            <span className="text-xs text-text-secondary">/ 10</span>
            <div
              className="flex-1 h-3 bg-white/10 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={convictionScore}
              aria-valuemin={0}
              aria-valuemax={10}
              aria-label={`Conviction score: ${convictionScore} out of 10`}
            >
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-300",
                  convictionColor(convictionScore)
                )}
                style={{ width: `${(convictionScore / 10) * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* Disagreement Table */}
        {result.disagreements && result.disagreements.length > 0 && (
          <div className="mb-4">
            <p className="text-[11px] font-medium text-text-secondary mb-2">
              Disagreements
            </p>
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-left" role="table">
                <thead>
                  <tr className="bg-white/5 border-b border-border">
                    <th
                      className="px-3 py-2 text-[11px] font-medium text-text-secondary"
                      scope="col"
                    >
                      Persona
                    </th>
                    <th
                      className="px-3 py-2 text-[11px] font-medium text-text-secondary"
                      scope="col"
                    >
                      Position
                    </th>
                    <th
                      className="px-3 py-2 text-[11px] font-medium text-text-secondary"
                      scope="col"
                    >
                      Reasoning
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {result.disagreements.map((d, idx) => (
                    <tr key={idx} className="border-b border-border/50">
                      <td className="px-3 py-2 text-xs font-medium text-text-primary whitespace-nowrap">
                        {d.persona}
                      </td>
                      <td className="px-3 py-2 text-[11px] text-text-secondary leading-relaxed max-w-[180px]">
                        {d.position}
                      </td>
                      <td className="px-3 py-2 text-[11px] text-text-secondary leading-relaxed max-w-[260px]">
                        {d.reasoning}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Unified Risk/Kill Conditions */}
        {result.unified_kill_conditions && result.unified_kill_conditions.length > 0 && (
          <div className="mb-4">
            <p className="text-[11px] font-medium text-text-secondary mb-2">
              Unified Risk / Kill Conditions
            </p>
            <div className="space-y-1.5">
              {result.unified_kill_conditions.map((risk, idx) => {
                const sevConfig = SEVERITY_COLORS[risk.severity?.toUpperCase()] ?? SEVERITY_COLORS.LOW;
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
                          {risk.condition}
                        </span>
                        <span
                          className={cn(
                            "inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium",
                            sevConfig.bg,
                            sevConfig.text
                          )}
                        >
                          {risk.severity}
                        </span>
                        {risk.source && (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium bg-white/10 text-text-secondary">
                            {risk.source}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Summary Narrative */}
        {result.summary_narrative && (
          <div className="mb-3">
            <p className="text-[11px] font-medium text-text-secondary mb-1">
              Summary Narrative
            </p>
            <MarkdownNarrative content={result.summary_narrative} />
          </div>
        )}
      </div>

      {/* Individual Persona Panels (collapsible accordion) */}
      <div className="space-y-2">
        <p className="text-[11px] font-medium text-text-secondary">
          Individual Analyses
        </p>
        {individualPanels.map(({ name, label, analysis: panelAnalysis }) => {
          if (!panelAnalysis) return null;
          const isExpanded = expandedPanels[name] ?? false;

          return (
            <div key={name} className="border border-border rounded-xl overflow-hidden">
              <button
                onClick={() => togglePanel(name)}
                className={cn(
                  "w-full flex items-center justify-between px-4 py-3 text-left",
                  "hover:bg-white/5 transition-colors duration-150",
                  "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1",
                  isExpanded && "bg-white/5 border-b border-border"
                )}
                aria-expanded={isExpanded}
              >
                <div className="flex items-center gap-2">
                  <Target size={14} className="text-text-tertiary" />
                  <span className="text-xs font-medium text-text-primary">{label}</span>
                  {/* Status indicator */}
                  {panelAnalysis.analysisResult &&
                    (panelAnalysis.analysisResult as Record<string, unknown>).status !== "pending" &&
                    !(panelAnalysis.analysisResult as Record<string, unknown>).error && (
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
                    )}
                  {panelAnalysis.analysisResult &&
                    (panelAnalysis.analysisResult as Record<string, unknown>).status === "pending" && (
                      <Loader2 size={12} className="animate-spin text-text-tertiary" />
                    )}
                </div>
                {isExpanded ? (
                  <ChevronUp size={14} className="text-text-tertiary flex-shrink-0" />
                ) : (
                  <ChevronDown size={14} className="text-text-tertiary flex-shrink-0" />
                )}
              </button>
              {isExpanded && (
                <div className="p-4 bg-white/[0.02]">
                  {name === "visser" && <VisserPanel analysis={panelAnalysis} />}
                  {name === "meldrum" && <MeldrumPanel analysis={panelAnalysis} />}
                  {name === "wissner_gross" && <WissnerGrossPanel analysis={panelAnalysis} />}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
