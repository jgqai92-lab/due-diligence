"use client";

import { useState } from "react";
import { cn, formatScore, getZoneColor, getZoneBorder } from "@/lib/utils";
import type { ZoneType, MetricComponent as MC } from "@/types/analysis";
import CitationTooltip from "./CitationTooltip";
import { ChevronDown, ChevronUp } from "lucide-react";

interface ForensicScoreCardProps {
  title: string;
  score: number | null;
  zone: ZoneType;
  interpretation: string;
  components?: { name: string; value: number | null; citation: MC["citation"] }[];
}

export default function ForensicScoreCard({ title, score, zone, interpretation, components }: ForensicScoreCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={cn("bg-surface rounded-xl shadow-card border-l-[3px] hover:shadow-card-hover transition-shadow duration-200", getZoneBorder(zone))}>
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-medium tracking-wide text-text-secondary">{title}</h3>
          {components && components.length > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-text-tertiary hover:text-text-primary transition-colors duration-200 p-1 rounded-lg hover:bg-background"
              aria-label={expanded ? "Collapse" : "Expand"}
            >
              {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          )}
        </div>

        <div className={cn("text-3xl font-mono font-bold mb-1", getZoneColor(zone))}>
          {formatScore(score)}
        </div>
        <div className={cn("text-sm font-medium", getZoneColor(zone))}>
          {interpretation || "Insufficient Data"}
        </div>
      </div>

      {expanded && components && (
        <div className="border-t border-border px-6 py-4 animate-fade-in">
          <div className="grid grid-cols-2 gap-3">
            {components.map((c) => (
              <div key={c.name} className="flex justify-between items-center">
                <span className="text-xs text-text-secondary">{c.name}</span>
                <CitationTooltip citation={c.citation}>
                  <span className="font-mono text-sm text-text-primary">
                    {c.value != null ? c.value.toFixed(4) : "N/A"}
                  </span>
                </CitationTooltip>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
