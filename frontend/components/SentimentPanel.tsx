"use client";

import type { SentimentMetrics, MetricComponent as MC } from "@/types/analysis";
import { cn, formatMultiple, formatPercentFromDecimal, classifySentiment, getSentimentZoneColor } from "@/lib/utils";
import CitationTooltip from "./CitationTooltip";

interface SentimentPanelProps { sentiment: SentimentMetrics; }

function getAnalystLabel(rating: number | null): string {
  if (rating == null) return "N/A";
  if (rating <= 1.5) return "Strong Buy";
  if (rating <= 2.5) return "Buy";
  if (rating <= 3.5) return "Hold";
  if (rating <= 4.5) return "Sell";
  return "Strong Sell";
}

function formatValue(metric: MC, format: "ratio" | "percent" | "rating"): string {
  if (metric.value == null) return "N/A";
  if (format === "percent") return formatPercentFromDecimal(metric.value);
  if (format === "ratio") return formatMultiple(metric.value);
  return metric.value.toFixed(1);
}

function MetricItem({ label, metric, format, colorClass, suffix }: { label: string; metric: MC; format: "ratio" | "percent" | "rating"; colorClass?: string; suffix?: string }) {
  return (
    <div className="flex justify-between items-center py-2.5 border-b border-border/50 last:border-b-0">
      <span className="text-xs text-text-secondary">{label}</span>
      <CitationTooltip citation={metric.citation}>
        <span className={cn("font-mono text-sm font-medium", colorClass ?? "text-text-primary")}>
          {formatValue(metric, format)}
          {suffix && <span className="text-xs text-text-secondary ml-1">{suffix}</span>}
        </span>
      </CitationTooltip>
    </div>
  );
}

function SubSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface rounded-xl shadow-card">
      <div className="px-6 py-4 border-b border-border/50">
        <h4 className="text-xs font-medium tracking-wide text-text-secondary">{title}</h4>
      </div>
      <div className="px-6 py-3">{children}</div>
    </div>
  );
}

export default function SentimentPanel({ sentiment }: SentimentPanelProps) {
  const ratingZone = classifySentiment(sentiment.analyst_rating.value);
  const ratingColor = getSentimentZoneColor(ratingZone);

  return (
    <div className="space-y-4">
      <SubSection title="Analyst Consensus">
        <div className="flex items-center gap-4 py-3 mb-2">
          <div className={cn("text-3xl font-mono font-bold", ratingColor)}>
            {sentiment.analyst_rating.value != null ? sentiment.analyst_rating.value.toFixed(1) : "N/A"}
          </div>
          <div>
            <div className={cn("text-sm font-medium", ratingColor)}>{getAnalystLabel(sentiment.analyst_rating.value)}</div>
            {sentiment.analyst_count != null && <div className="text-xs text-text-tertiary mt-0.5">Based on {sentiment.analyst_count} analyst{sentiment.analyst_count !== 1 ? "s" : ""}</div>}
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6">
          <MetricItem label="Rating (1-5)" metric={sentiment.analyst_rating} format="rating" colorClass={ratingColor} />
          {sentiment.analyst_recommendation && (
            <div className="flex justify-between items-center py-2.5 border-b border-border/50 last:border-b-0">
              <span className="text-xs text-text-secondary">Recommendation</span>
              <span className="font-mono text-sm font-medium text-text-primary capitalize">{sentiment.analyst_recommendation}</span>
            </div>
          )}
        </div>
      </SubSection>
      <SubSection title="Short Interest & Ownership">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6">
          <MetricItem label="Short Ratio" metric={sentiment.short_ratio} format="ratio" />
          <MetricItem label="Short % of Float" metric={sentiment.short_percent_float} format="percent" />
          <MetricItem label="Institutional %" metric={sentiment.institutional_pct} format="percent" />
          <MetricItem label="Insider %" metric={sentiment.insider_pct} format="percent" />
        </div>
      </SubSection>
    </div>
  );
}
