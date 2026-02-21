"use client";

import type { SynthesisTierChange } from "@/types/ist-synthesis";

interface TierChangesProps {
  changes: SynthesisTierChange[];
}

export default function TierChanges({ changes }: TierChangesProps) {
  if (!changes.length) {
    return <p className="text-sm text-text-secondary">No tier changes identified.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left text-sm">
        <thead className="bg-white/5">
          <tr>
            <th className="px-3 py-2">Ticker</th>
            <th className="px-3 py-2">Before</th>
            <th className="px-3 py-2">After</th>
            <th className="px-3 py-2">Rationale</th>
          </tr>
        </thead>
        <tbody>
          {changes.map((change, idx) => (
            <tr key={`${change.ticker}-${idx}`} className="border-t border-border">
              <td className="px-3 py-2 font-mono">{change.ticker}</td>
              <td className="px-3 py-2">Tier {change.originalTier}</td>
              <td className="px-3 py-2">Tier {change.newTier}</td>
              <td className="px-3 py-2">{change.rationale}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

