"use client";

import type { RuleOf40, MagicNumber } from "@/types/analysis";
import { formatScore, formatPercent } from "@/lib/utils";
import type { ZoneType } from "@/types/analysis";
import ForensicScoreCard from "./ForensicScoreCard";

interface SaaSMetricsPanelProps {
  ruleOf40: RuleOf40;
  magicNumber: MagicNumber;
}

function getR40Zone(score: number | null): ZoneType {
  if (score == null) return null;
  if (score >= 40) return "safe";
  if (score >= 25) return "warning";
  return "danger";
}

function getMagicZone(score: number | null): ZoneType {
  if (score == null) return null;
  if (score >= 1.0) return "safe";
  if (score >= 0.5) return "warning";
  return "danger";
}

export default function SaaSMetricsPanel({ ruleOf40, magicNumber }: SaaSMetricsPanelProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <ForensicScoreCard
        title="RULE OF 40"
        score={ruleOf40.score}
        zone={getR40Zone(ruleOf40.score)}
        interpretation={`Rev Growth: ${formatPercent(ruleOf40.revenue_growth_percent)} + FCF Margin: ${formatPercent(ruleOf40.fcf_margin_percent)}`}
      />
      <ForensicScoreCard
        title="MAGIC NUMBER"
        score={magicNumber.score}
        zone={getMagicZone(magicNumber.score)}
        interpretation={magicNumber.interpretation?.replace(/_/g, " ") || ""}
      />
    </div>
  );
}
