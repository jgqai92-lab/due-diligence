"use client";

import { cn } from "@/lib/utils";
import { CheckCircle2, AlertCircle, Info } from "lucide-react";
import type { ContentQualityResult, ContentQualityCheck } from "@/lib/ist/quality-checks";

// ─── Props ──────────────────────────────────────────────────────────

interface ContentQualityIndicatorProps {
  quality: ContentQualityResult;
}

// ─── Check Row ──────────────────────────────────────────────────────

function QualityCheckRow({ check }: { check: ContentQualityCheck }) {
  const isAdvisory = check.severity === "advisory";

  // Determine icon and color
  let IconComponent = Info;
  let iconColor = "text-sky-400";

  if (!isAdvisory) {
    if (check.passed) {
      IconComponent = CheckCircle2;
      iconColor = "text-emerald-400";
    } else {
      IconComponent = AlertCircle;
      iconColor = "text-amber-400";
    }
  }

  // Format count display
  const countDisplay = isAdvisory
    ? `${check.count} found`
    : `${check.count} / ${check.required} min`;

  return (
    <div className="flex items-center gap-2 py-1">
      <IconComponent
        size={14}
        className={cn(iconColor, "transition-colors duration-200 flex-shrink-0")}
        aria-hidden="true"
      />
      <span className="text-xs text-text-secondary">{check.label}</span>
      <span className="text-xs font-mono text-text-tertiary ml-auto">
        {countDisplay}
      </span>
    </div>
  );
}

// ─── Component ──────────────────────────────────────────────────────

export default function ContentQualityIndicator({
  quality,
}: ContentQualityIndicatorProps) {
  // Only render if user has typed something
  const hasContent = quality.wordCount.count > 0;
  if (!hasContent) return null;

  const checks: ContentQualityCheck[] = [
    quality.wordCount,
    quality.quantitativeAnchors,
    quality.temporalMarkers,
    quality.namedEntities,
  ];

  return (
    <div
      className="bg-white/5 rounded-lg border border-border p-3"
      aria-live="polite"
      aria-label="Content quality checklist"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">
          Content Quality
        </span>
        {quality.overallReady ? (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400">
            <CheckCircle2 size={12} aria-hidden="true" />
            Ready
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-400">
            <AlertCircle size={12} aria-hidden="true" />
            Not Ready
          </span>
        )}
      </div>

      {/* Check rows */}
      <div>
        {checks.map((check) => (
          <QualityCheckRow key={check.id} check={check} />
        ))}
      </div>
    </div>
  );
}
