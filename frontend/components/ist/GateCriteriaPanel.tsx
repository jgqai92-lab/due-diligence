"use client";

import { cn } from "@/lib/utils";
import { IST_GATES, CONTENT_EXAMPLES } from "@/lib/ist/quality-checks";
import type { ContentType, ContentQualityResult } from "@/lib/ist/quality-checks";

// ─── Props ──────────────────────────────────────────────────────────

interface GateCriteriaPanelProps {
  contentType: ContentType;
  quality: ContentQualityResult;
  className?: string;
}

// ─── Phase Color Map ────────────────────────────────────────────────

const PHASE_DOT_COLOR: Record<number, string> = {
  2: "bg-sky-400",
  3: "bg-violet-400",
  5: "bg-amber-400",
};

// ─── Content Type Labels ────────────────────────────────────────────

const CONTENT_TYPE_LABELS: Record<ContentType, string> = {
  podcast_transcript: "Podcast Transcript",
  article: "Article",
  earnings_call: "Earnings Call",
  research_note: "Research Note",
  text: "General Text",
};

// ─── Gate-to-Quality Mapping ────────────────────────────────────────

function getCriterionPassState(
  criterionLabel: string,
  source: "user_input" | "workflow",
  quality: ContentQualityResult
): boolean | null {
  // Only Gate 1 user_input criteria get live feedback
  if (source !== "user_input") return null;

  const lower = criterionLabel.toLowerCase();
  if (lower.includes("quantitative")) {
    return quality.quantitativeAnchors.passed;
  }
  if (lower.includes("temporal")) {
    return quality.temporalMarkers.passed;
  }

  return null;
}

// ─── Component ──────────────────────────────────────────────────────

export default function GateCriteriaPanel({
  contentType,
  quality,
  className,
}: GateCriteriaPanelProps) {
  const examples = CONTENT_EXAMPLES[contentType] ?? CONTENT_EXAMPLES.text;

  return (
    <div
      className={cn(
        "space-y-3 bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-4",
        className
      )}
    >
      {/* Header */}
      <h2 className="text-sm font-semibold text-text-primary">
        Pipeline Gates
      </h2>

      {/* Gate cards */}
      <div>
        {IST_GATES.map((gate) => (
          <section
            key={gate.id}
            className="border-b border-border last:border-b-0 py-3"
          >
            {/* Gate header */}
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "w-2 h-2 rounded-full flex-shrink-0",
                  PHASE_DOT_COLOR[gate.phase] ?? "bg-text-tertiary"
                )}
                aria-hidden="true"
              />
              <span className="text-xs font-medium text-text-primary">
                {gate.name}
              </span>
              <span className="text-xs text-text-tertiary ml-auto">
                {gate.phaseLabel}
              </span>
            </div>

            {/* Criteria list */}
            <ul className="ml-4 mt-1.5 space-y-1" aria-label={`${gate.name} criteria`} aria-live="polite">
              {gate.criteria.map((criterion, idx) => {
                const passState = getCriterionPassState(
                  criterion.label,
                  criterion.source,
                  quality
                );

                let dotColor = "bg-text-tertiary";
                if (passState === true) dotColor = "bg-emerald-400";
                if (passState === false) dotColor = "bg-text-tertiary";

                return (
                  <li
                    key={`${gate.id}-${idx}`}
                    className="flex items-start gap-1.5"
                  >
                    <span
                      className={cn(
                        "w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0 transition-colors duration-200",
                        dotColor
                      )}
                      aria-hidden="true"
                    />
                    <span className="text-xs text-text-tertiary">
                      {criterion.label}
                    </span>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>

      {/* Content Examples */}
      <div className="border-t border-border pt-3">
        <h3 className="text-xs font-medium text-text-secondary mb-2">
          Example &mdash; {CONTENT_TYPE_LABELS[contentType] ?? "General Text"}
        </h3>
        {examples.map((ex, idx) => (
          <div
            key={idx}
            className="bg-black/20 rounded-md p-2 text-xs text-text-tertiary font-mono leading-relaxed max-h-32 overflow-y-auto"
          >
            {ex.snippet}
          </div>
        ))}
      </div>

      {/* Tips */}
      <p className="text-xs text-text-tertiary italic">
        Include dollar figures, percentages, and dates for best results.
      </p>
    </div>
  );
}
