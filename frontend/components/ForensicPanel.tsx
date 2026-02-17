"use client";

import type { BeneishMScore, AltmanZScore } from "@/types/analysis";
import BeneishMScorePanel from "./BeneishMScorePanel";
import AltmanZScorePanel from "./AltmanZScorePanel";

interface ForensicPanelProps {
  beneishMScore: BeneishMScore;
  altmanZScore: AltmanZScore;
}

export default function ForensicPanel({ beneishMScore, altmanZScore }: ForensicPanelProps) {
  return (
    <div className="space-y-4">
      <BeneishMScorePanel data={beneishMScore} />
      <AltmanZScorePanel data={altmanZScore} />
    </div>
  );
}
