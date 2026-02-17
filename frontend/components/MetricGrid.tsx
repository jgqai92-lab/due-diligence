"use client";

import type { Citation } from "@/types/analysis";
import {
  formatPercentFromDecimal,
  formatRatio,
  formatMultiple,
  formatLargeNumber,
  formatScore,
  cn,
} from "@/lib/utils";
import CitationTooltip from "./CitationTooltip";

export interface MetricGridItem {
  label: string;
  value: number | null;
  format: "percent" | "ratio" | "currency" | "number" | "multiple";
  citation?: Citation;
  zone?: string;
  interpretation?: string;
}

interface MetricGridProps {
  metrics: MetricGridItem[];
  columns?: 2 | 3 | 4;
}

function formatMetricValue(value: number | null, format: MetricGridItem["format"]): string {
  if (value == null) return "N/A";
  switch (format) {
    case "percent": return formatPercentFromDecimal(value);
    case "ratio": return formatRatio(value);
    case "currency": return formatLargeNumber(value);
    case "multiple": return formatMultiple(value);
    case "number": return formatScore(value);
    default: return formatScore(value);
  }
}

function getZoneBorderClass(zone?: string): string {
  if (!zone) return "border-l-border-strong";
  if (zone === "text-bull") return "border-l-bull";
  if (zone === "text-bear") return "border-l-bear";
  if (zone === "text-warning") return "border-l-warning";
  if (zone === "text-text-secondary") return "border-l-border-strong";
  return "border-l-border-strong";
}

export default function MetricGrid({ metrics, columns = 3 }: MetricGridProps) {
  const gridCols = {
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-2 sm:grid-cols-2 lg:grid-cols-4",
  };

  return (
    <div className={cn("grid gap-3", gridCols[columns])}>
      {metrics.map((metric) => {
        const formatted = formatMetricValue(metric.value, metric.format);
        const borderClass = getZoneBorderClass(metric.zone);

        const valueElement = (
          <span className={cn("font-mono text-lg font-bold tabular-nums", metric.value != null ? metric.zone || "text-text-primary" : "text-text-tertiary")}>
            {formatted}
          </span>
        );

        return (
          <div
            key={metric.label}
            className={cn("bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-[14px] border-l-[3px] p-4 hover:-translate-y-1 hover:border-primary hover:shadow-[0_12px_40px_rgba(255,77,77,0.15)] transition-all duration-200", borderClass)}
          >
            <div className="text-[11px] font-medium tracking-wide text-text-secondary mb-2">
              {metric.label}
            </div>
            <div className="flex items-baseline gap-2">
              {metric.citation ? <CitationTooltip citation={metric.citation}>{valueElement}</CitationTooltip> : valueElement}
            </div>
            {metric.interpretation && (
              <div className={cn("text-[11px] font-medium mt-1", metric.zone || "text-text-secondary")}>
                {metric.interpretation}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
