"use client";

import type { OverlapEntry } from "@/types/ist-synthesis";

interface OverlapMatrixProps {
  entries: OverlapEntry[];
}

export default function OverlapMatrix({ entries }: OverlapMatrixProps) {
  if (!entries.length) {
    return <p className="text-sm text-text-secondary">No overlap data available yet.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left text-sm">
        <thead className="bg-white/5">
          <tr>
            <th className="px-3 py-2">Ticker</th>
            <th className="px-3 py-2">Company</th>
            <th className="px-3 py-2">Appearances</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.ticker} className="border-t border-border">
              <td className="px-3 py-2 font-mono">{entry.ticker}</td>
              <td className="px-3 py-2">{entry.companyName}</td>
              <td className="px-3 py-2">
                {entry.appearances.map((a, idx) => (
                  <span key={`${entry.ticker}-${idx}`} className="inline-flex mr-2 mb-1 px-2 py-0.5 rounded bg-white/10 text-xs">
                    Screen {a.screenId} · Tier {a.tier}
                  </span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

