"use client";

import type { SynthesisEquity } from "@/types/ist-synthesis";

interface SynthesisEquitiesProps {
  equities: SynthesisEquity[];
}

export default function SynthesisEquities({ equities }: SynthesisEquitiesProps) {
  if (!equities.length) {
    return <p className="text-sm text-text-secondary">No synthesis equities available.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left text-sm">
        <thead className="bg-white/5">
          <tr>
            <th className="px-3 py-2">Ticker</th>
            <th className="px-3 py-2">Company</th>
            <th className="px-3 py-2">New Tier</th>
            <th className="px-3 py-2">Conviction</th>
            <th className="px-3 py-2">Sources</th>
          </tr>
        </thead>
        <tbody>
          {equities.map((eq) => (
            <tr key={eq.id} className="border-t border-border">
              <td className="px-3 py-2 font-mono">{eq.ticker}</td>
              <td className="px-3 py-2">{eq.companyName}</td>
              <td className="px-3 py-2">Tier {eq.newTier}</td>
              <td className="px-3 py-2">{eq.conviction ?? "-"}</td>
              <td className="px-3 py-2">{eq.sourceScreenIds.join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

