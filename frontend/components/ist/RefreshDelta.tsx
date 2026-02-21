"use client";

import type { ISTClaim, ISTRefreshDetail } from "@/types/ist";

interface RefreshDeltaProps {
  detail: ISTRefreshDetail | null;
  claims: ISTClaim[];
  loading: boolean;
  error: string | null;
}

type ImpactAssessmentMap = Record<string, { needed?: boolean; reason?: string | null }>;

function toImpactRows(impact: Record<string, unknown> | null): Array<{ step: string; needed: boolean; reason: string | null }> {
  if (!impact || typeof impact !== "object") return [];
  const map = impact as ImpactAssessmentMap;
  return Object.entries(map).map(([step, value]) => ({
    step,
    needed: Boolean(value?.needed),
    reason: value?.reason ?? null,
  }));
}

export default function RefreshDelta({ detail, claims, loading, error }: RefreshDeltaProps) {
  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-[rgba(10,15,26,0.6)] p-5">
        <p className="text-sm text-text-secondary">Loading refresh detail...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-5">
        <p className="text-sm text-red-300">{error}</p>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="rounded-xl border border-border bg-[rgba(10,15,26,0.6)] p-5">
        <p className="text-sm text-text-secondary">Select a refresh to inspect delta claims and impact scope.</p>
      </div>
    );
  }

  const impactRows = toImpactRows(detail.impactAssessment);

  return (
    <div className="rounded-xl border border-border bg-[rgba(10,15,26,0.6)] p-5 space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-text-primary">Refresh #{detail.refreshNumber} Delta</h3>
        <p className="text-xs text-text-secondary mt-1">
          Status: {detail.status} - Delta claims: {detail.deltaClaimCount}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="rounded-lg border border-border bg-white/5 p-3">
          <p className="text-[11px] uppercase tracking-wide text-text-tertiary">Re-executed Steps</p>
          {detail.stepsReexecuted?.length ? (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {detail.stepsReexecuted.map((step) => (
                <span key={step} className="inline-flex px-2 py-0.5 rounded bg-primary/10 text-primary text-[11px]">
                  {step}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-xs text-text-secondary mt-2">No step list available.</p>
          )}
        </div>

        <div className="rounded-lg border border-border bg-white/5 p-3">
          <p className="text-[11px] uppercase tracking-wide text-text-tertiary">Impact Assessment</p>
          {impactRows.length ? (
            <ul className="mt-2 space-y-1.5">
              {impactRows.map((row) => (
                <li key={row.step} className="text-xs text-text-secondary">
                  <span className={row.needed ? "text-amber-300" : "text-emerald-300"}>
                    {row.needed ? "Re-run" : "No re-run"}
                  </span>
                  {" - "}
                  <span className="font-mono">{row.step}</span>
                  {row.reason ? `: ${row.reason}` : ""}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-text-secondary mt-2">No impact assessment available.</p>
          )}
        </div>
      </div>

      <div className="rounded-lg border border-border overflow-hidden">
        <div className="px-3 py-2 border-b border-border bg-white/5">
          <p className="text-xs font-medium text-text-primary">Delta Claims</p>
        </div>
        {!claims.length ? (
          <p className="text-xs text-text-secondary px-3 py-3">No claims found for this refresh.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-3 py-2">Claim</th>
                  <th className="px-3 py-2">Quant Anchor</th>
                  <th className="px-3 py-2">Temporal</th>
                  <th className="px-3 py-2">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {claims.map((claim) => (
                  <tr key={claim.id} className="border-b border-border">
                    <td className="px-3 py-2 text-text-primary">{claim.claimText}</td>
                    <td className="px-3 py-2 text-violet-400">{claim.quantitativeAnchor ?? "-"}</td>
                    <td className="px-3 py-2 text-sky-400">{claim.temporalMarker ?? "-"}</td>
                    <td className="px-3 py-2 text-text-secondary">{Math.round(claim.confidence * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

