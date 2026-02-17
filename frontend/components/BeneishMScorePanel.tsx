"use client";

import type { BeneishMScore } from "@/types/analysis";
import { classifyMScore } from "@/lib/utils";
import ForensicScoreCard from "./ForensicScoreCard";

interface BeneishMScorePanelProps {
  data: BeneishMScore;
}

const COMPONENT_NAMES: (keyof BeneishMScore["components"])[] = [
  "dsri", "gmi", "aqi", "sgi", "depi", "sgai", "lvgi", "tata",
];

export default function BeneishMScorePanel({ data }: BeneishMScorePanelProps) {
  const zone = classifyMScore(data.composite);
  const interpretation = data.interpretation?.replace(/_/g, " ") || "";

  const components = COMPONENT_NAMES.map((name) => ({
    name: name.toUpperCase(),
    value: data.components[name].value,
    citation: data.components[name].citation,
  }));

  return (
    <ForensicScoreCard
      title="BENEISH M-SCORE"
      score={data.composite}
      zone={zone}
      interpretation={interpretation}
      components={components}
    />
  );
}
