"use client";

import type { SectorSpecificMetrics, MetricComponent as MC } from "@/types/analysis";
import { cn, formatScore } from "@/lib/utils";
import CitationTooltip from "./CitationTooltip";
import ForensicScoreCard from "./ForensicScoreCard";
import type { ZoneType } from "@/types/analysis";

interface SectorSpecificPanelProps { sectorSpecific: SectorSpecificMetrics | null; }

function getMetricZone(key: string, value: number | null): ZoneType {
  if (value == null) return null;
  if (key === "rule_of_40") { if (value >= 40) return "safe"; if (value >= 25) return "warning"; return "danger"; }
  if (key === "magic_number") { if (value >= 1.0) return "safe"; if (value >= 0.5) return "warning"; return "danger"; }
  return null;
}

function prettifyKey(key: string): string {
  return key.split("_").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

export default function SectorSpecificPanel({ sectorSpecific }: SectorSpecificPanelProps) {
  if (!sectorSpecific) return null;
  const metricKeys = Object.keys(sectorSpecific.metrics);
  const hasScoreCards = metricKeys.some((k) => k === "rule_of_40" || k === "magic_number");

  return (
    <div className="space-y-4">
      <div className="bg-surface rounded-xl shadow-card">
        <div className="px-6 py-4 border-b border-border/50 flex items-center gap-3">
          <h4 className="text-xs font-medium tracking-wide text-text-secondary">{sectorSpecific.label}</h4>
          <span className="px-2 py-0.5 bg-primary/10 text-primary text-[10px] font-medium rounded-lg border border-primary/20">{sectorSpecific.sector_category}</span>
        </div>
        {hasScoreCards ? (
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {metricKeys.map((key) => {
                const metric = sectorSpecific.metrics[key];
                return <ForensicScoreCard key={key} title={prettifyKey(key).toUpperCase()} score={metric.value} zone={getMetricZone(key, metric.value)} interpretation={sectorSpecific.interpretations[key]?.replace(/_/g, " ") ?? ""} />;
              })}
            </div>
          </div>
        ) : (
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6">
              {metricKeys.map((key) => {
                const metric = sectorSpecific.metrics[key];
                const interpretation = sectorSpecific.interpretations[key];
                return (
                  <div key={key} className="py-2.5 border-b border-border/50 last:border-b-0">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-text-secondary">{prettifyKey(key)}</span>
                      <CitationTooltip citation={metric.citation}><span className="font-mono text-sm font-medium text-text-primary">{formatScore(metric.value)}</span></CitationTooltip>
                    </div>
                    {interpretation && <div className="text-xs text-text-tertiary mt-1">{interpretation}</div>}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
