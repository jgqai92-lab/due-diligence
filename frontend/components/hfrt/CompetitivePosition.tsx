"use client";

import { cn } from "@/lib/utils";
import { Shield, CheckCircle, XCircle, Plus, Minus } from "lucide-react";

/* ── Data shape from CompetitivePositionResult (Template 03) ──────── */

interface PorterForce {
  score: number; // 1-5
  rationale: string;
}

interface SevenPower {
  present: boolean;
  strength: number; // 0-5
  evidence: string;
}

interface CompetitivePositionData {
  competitive_advantages: string[];
  competitive_disadvantages: string[];
  market_share: string | null;
  key_competitors: Array<Record<string, unknown>>;
  porters_five_forces: Record<string, PorterForce>;
  seven_powers: Record<string, SevenPower>;
  overall_moat_strength: string;
  moat_durability: string;
}

interface CompetitivePositionProps {
  data: Record<string, unknown>;
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function ScoreDots({ score, max = 5 }: { score: number; max?: number }) {
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: max }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "w-2.5 h-2.5 rounded-full",
            i < score ? "bg-blue-500" : "bg-white/10"
          )}
        />
      ))}
      <span className="text-xs font-mono text-text-secondary ml-1">{score}/{max}</span>
    </div>
  );
}

function StrengthBar({ strength, max = 5 }: { strength: number; max?: number }) {
  const pct = max > 0 ? (strength / max) * 100 : 0;
  return (
    <div className="flex items-center gap-2 w-full">
      <div className="flex-1 h-2 rounded-full bg-white/10 overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            pct >= 60 ? "bg-emerald-500" : pct >= 30 ? "bg-amber-400" : "bg-white/20"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-text-secondary flex-shrink-0">{strength}/{max}</span>
    </div>
  );
}

function getMoatColor(strength: string): { bg: string; text: string; border: string } {
  const lower = strength?.toLowerCase() ?? "";
  if (lower.includes("strong") || lower.includes("wide")) {
    return { bg: "bg-emerald-500/10", text: "text-emerald-300", border: "border-emerald-500/30" };
  }
  if (lower.includes("moderate") || lower.includes("narrow")) {
    return { bg: "bg-amber-500/10", text: "text-amber-300", border: "border-amber-500/30" };
  }
  if (lower.includes("weak") || lower.includes("none") || lower.includes("no ")) {
    return { bg: "bg-red-500/10", text: "text-red-300", border: "border-red-500/30" };
  }
  return { bg: "bg-white/5", text: "text-text-primary", border: "border-border" };
}

export default function CompetitivePosition({ data }: CompetitivePositionProps) {
  const d = data as unknown as CompetitivePositionData;

  if (!d || (!d.overall_moat_strength && !d.porters_five_forces)) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 text-center py-12 text-text-tertiary">
        <Shield size={32} className="mx-auto mb-3" />
        <p className="text-sm">Competitive position analysis not yet available.</p>
      </div>
    );
  }

  const moatColor = getMoatColor(d.overall_moat_strength ?? "");
  const durabilityColor = getMoatColor(d.moat_durability ?? "");

  return (
    <div className="space-y-4">
      {/* Moat Strength + Durability Banner */}
      <div className={cn("rounded-xl border px-6 py-5 flex flex-wrap items-center gap-4", moatColor.bg, moatColor.border)}>
        <Shield size={28} className={moatColor.text} />
        <div className="flex-1 min-w-[200px]">
          <div className="flex flex-wrap items-center gap-3 mb-1">
            <span className={cn("inline-flex items-center px-3 py-1 rounded-full text-sm font-bold", moatColor.bg, moatColor.text)}>
              Moat: {d.overall_moat_strength ?? "N/A"}
            </span>
            <span className={cn("inline-flex items-center px-3 py-1 rounded-full text-sm font-medium", durabilityColor.bg, durabilityColor.text)}>
              Durability: {d.moat_durability ?? "N/A"}
            </span>
          </div>
          {d.market_share && (
            <p className="text-sm text-text-secondary mt-1">
              Market Share: <span className="font-mono font-medium text-text-primary">{d.market_share}</span>
            </p>
          )}
        </div>
      </div>

      {/* Porter's Five Forces */}
      {d.porters_five_forces && Object.keys(d.porters_five_forces).length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Porter&apos;s Five Forces</h3>
          <div className="space-y-3">
            {Object.entries(d.porters_five_forces).map(([forceName, force]) => {
              const f = force as PorterForce;
              return (
                <div key={forceName} className="bg-white/5 rounded-lg px-4 py-3">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-text-primary">{humanizeKey(forceName)}</span>
                    <ScoreDots score={f?.score ?? 0} />
                  </div>
                  {f?.rationale && (
                    <p className="text-xs text-text-secondary">{f.rationale}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Seven Powers */}
      {d.seven_powers && Object.keys(d.seven_powers).length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Seven Powers Analysis</h3>
          <div className="space-y-3">
            {Object.entries(d.seven_powers).map(([powerName, power]) => {
              const p = power as SevenPower;
              return (
                <div key={powerName} className="bg-white/5 rounded-lg px-4 py-3">
                  <div className="flex items-center gap-3 mb-1.5">
                    {p?.present ? (
                      <CheckCircle size={16} className="text-emerald-500 flex-shrink-0" />
                    ) : (
                      <XCircle size={16} className="text-text-tertiary flex-shrink-0" />
                    )}
                    <span className="text-sm font-medium text-text-primary flex-1">
                      {humanizeKey(powerName)}
                    </span>
                  </div>
                  <div className="ml-7">
                    <StrengthBar strength={p?.strength ?? 0} />
                    {p?.evidence && (
                      <p className="text-xs text-text-secondary mt-1.5">{p.evidence}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Competitive Advantages & Disadvantages */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {d.competitive_advantages?.length > 0 && (
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Competitive Advantages</h3>
            <ul className="space-y-2">
              {d.competitive_advantages.map((adv, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-text-primary">
                  <Plus size={14} className="text-emerald-500 mt-0.5 flex-shrink-0" />
                  <span>{adv}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {d.competitive_disadvantages?.length > 0 && (
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Competitive Disadvantages</h3>
            <ul className="space-y-2">
              {d.competitive_disadvantages.map((dis, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-text-primary">
                  <Minus size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
                  <span>{dis}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Key Competitors Table */}
      {d.key_competitors?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Key Competitors</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {(() => {
                    const allKeys = Array.from(
                      new Set(d.key_competitors.flatMap((c) => Object.keys(c)))
                    );
                    return allKeys.map((key) => (
                      <th key={key} className="text-left text-xs font-medium text-text-secondary pb-2 pr-4">
                        {humanizeKey(key)}
                      </th>
                    ));
                  })()}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {d.key_competitors.map((comp, idx) => {
                  const allKeys = Array.from(
                    new Set(d.key_competitors.flatMap((c) => Object.keys(c)))
                  );
                  return (
                    <tr key={idx} className="hover:bg-white/5">
                      {allKeys.map((key) => (
                        <td key={key} className="py-2 pr-4 text-text-primary">
                          {comp[key] != null ? String(comp[key]) : "N/A"}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
