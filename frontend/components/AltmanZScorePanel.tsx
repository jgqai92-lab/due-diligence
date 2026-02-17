"use client";

import type { AltmanZScore } from "@/types/analysis";
import { classifyZScore, cn, formatScore, getZoneColor } from "@/lib/utils";

interface AltmanZScorePanelProps { data: AltmanZScore; }

function ZoneBar({ score }: { score: number | null }) {
  const clampedScore = score != null ? Math.max(0, Math.min(6, score)) : null;
  const pct = clampedScore != null ? (clampedScore / 6) * 100 : 0;

  return (
    <div className="relative mt-4 mb-2">
      <div className="flex h-3 rounded-full overflow-hidden">
        <div className="bg-bear/20 flex-1 border-r border-background" title="Distress" />
        <div className="bg-warning/20 flex-1 border-r border-background" title="Grey Zone" />
        <div className="bg-bull/20 flex-1" title="Safe" />
      </div>
      {score != null && <div className="absolute top-0 w-0.5 h-5 bg-text-primary rounded-full -translate-x-1/2" style={{ left: `${pct}%` }} />}
      <div className="flex justify-between text-[10px] text-text-tertiary mt-1.5 font-mono">
        <span>{"< 1.81"}</span><span>1.81 - 2.99</span><span>{"> 2.99"}</span>
      </div>
    </div>
  );
}

export default function AltmanZScorePanel({ data }: AltmanZScorePanelProps) {
  const stdZone = classifyZScore(data.standard.score);
  const saasZone = classifyZScore(data.saas_modified.score);

  return (
    <div className="bg-surface rounded-xl shadow-card">
      <div className="p-6">
        <h3 className="text-xs font-medium tracking-wide text-text-secondary mb-4">Altman Z-Score</h3>
        <div className="grid grid-cols-2 gap-6">
          <div>
            <div className="text-xs text-text-tertiary mb-1">Standard</div>
            <div className={cn("text-2xl font-mono font-bold", getZoneColor(stdZone))}>{formatScore(data.standard.score)}</div>
            <div className={cn("text-xs font-medium", getZoneColor(stdZone))}>{data.standard.zone?.replace(/_/g, " ") || "N/A"}</div>
          </div>
          <div>
            <div className="text-xs text-text-tertiary mb-1">SaaS-Modified</div>
            <div className={cn("text-2xl font-mono font-bold", getZoneColor(saasZone))}>{formatScore(data.saas_modified.score)}</div>
            <div className={cn("text-xs font-medium", getZoneColor(saasZone))}>{data.saas_modified.zone?.replace(/_/g, " ") || "N/A"}</div>
            {data.saas_modified.disclaimer && <div className="text-[10px] text-text-tertiary italic mt-1">{data.saas_modified.disclaimer}</div>}
          </div>
        </div>
        <ZoneBar score={data.standard.score} />
      </div>
    </div>
  );
}
