"use client";

interface HandoffCandidate {
  ticker: string;
  companyName: string;
  tier: number;
  conviction: string;
  sourceScreenCount: number;
}

interface SynthesisHandoffProps {
  handoff: Record<string, unknown> | null;
}

export default function SynthesisHandoff({ handoff }: SynthesisHandoffProps) {
  if (!handoff) {
    return <p className="text-sm text-text-secondary">HFRT handoff not generated yet.</p>;
  }

  const candidates = (handoff.tier1Candidates || []) as HandoffCandidate[];
  const tier1Count = (handoff.tier1Count as number) || 0;

  if (!candidates.length) {
    return <p className="text-sm text-text-secondary">No Tier 1 candidates for HFRT handoff.</p>;
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-text-secondary">
        {tier1Count} Tier 1 candidate{tier1Count !== 1 ? "s" : ""} ready for HFRT research
      </p>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left text-sm">
          <thead className="bg-white/5">
            <tr>
              <th className="px-3 py-2">Ticker</th>
              <th className="px-3 py-2">Company</th>
              <th className="px-3 py-2">Conviction</th>
              <th className="px-3 py-2">Sources</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((candidate) => (
              <tr key={candidate.ticker} className="border-t border-border">
                <td className="px-3 py-2 font-mono font-medium text-primary">
                  {candidate.ticker}
                </td>
                <td className="px-3 py-2 text-text-primary">
                  {candidate.companyName}
                </td>
                <td className="px-3 py-2">
                  <span
                    className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                      candidate.conviction === "HIGH"
                        ? "bg-green-500/20 text-green-400"
                        : candidate.conviction === "MEDIUM"
                        ? "bg-yellow-500/20 text-yellow-400"
                        : "bg-red-500/20 text-red-400"
                    }`}
                  >
                    {candidate.conviction}
                  </span>
                </td>
                <td className="px-3 py-2 text-text-secondary">
                  {candidate.sourceScreenCount} screen
                  {candidate.sourceScreenCount !== 1 ? "s" : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
