"use client";

import { cn } from "@/lib/utils";
import {
  Factory,
  TrendingUp,
  AlertTriangle,
  ShieldAlert,
  Merge,
  BarChart3,
} from "lucide-react";

/* ── Data shape from IndustryAnalysisResult (Template 04) ─────────── */

interface IndustryAnalysisData {
  industry: string;
  sector: string;
  market_size: string | null;
  tam_sam_som: Record<string, unknown>;
  growth_rate: string | null;
  industry_lifecycle_stage: string;
  key_trends: string[];
  regulatory_environment: string;
  sector_specific_kpis: Record<string, unknown>;
  key_players: Array<Record<string, unknown>>;
  barriers_to_entry: string[];
  disruption_risks: string[];
  cyclicality: string;
  recent_m_and_a: string[];
}

interface IndustryAnalysisProps {
  data: Record<string, unknown>;
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(val: unknown): string {
  if (val == null) return "N/A";
  if (typeof val === "number") {
    return val.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(val);
}

function getLifecycleColor(stage: string): { bg: string; text: string } {
  const lower = stage?.toLowerCase() ?? "";
  if (lower.includes("emerg") || lower.includes("intro")) {
    return { bg: "bg-blue-500/10", text: "text-blue-300" };
  }
  if (lower.includes("growth")) {
    return { bg: "bg-emerald-500/10", text: "text-emerald-300" };
  }
  if (lower.includes("mature") || lower.includes("maturity")) {
    return { bg: "bg-amber-500/10", text: "text-amber-300" };
  }
  if (lower.includes("declin")) {
    return { bg: "bg-red-500/10", text: "text-red-300" };
  }
  return { bg: "bg-white/10", text: "text-text-primary" };
}

export default function IndustryAnalysis({ data }: IndustryAnalysisProps) {
  const d = data as unknown as IndustryAnalysisData;

  if (!d || !d.industry) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 text-center py-12 text-text-tertiary">
        <Factory size={32} className="mx-auto mb-3" />
        <p className="text-sm">Industry analysis not yet available.</p>
      </div>
    );
  }

  const lifecycleColor = getLifecycleColor(d.industry_lifecycle_stage ?? "");

  return (
    <div className="space-y-4">
      {/* Industry & Sector Heading */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <Factory size={20} className="text-text-tertiary" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">{d.industry}</h3>
            <p className="text-xs text-text-secondary">{d.sector}</p>
          </div>
          {d.industry_lifecycle_stage && (
            <span className={cn(
              "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ml-auto",
              lifecycleColor.bg, lifecycleColor.text
            )}>
              {d.industry_lifecycle_stage}
            </span>
          )}
        </div>

        {/* Market Size + Growth Rate metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {d.market_size && (
            <div className="bg-white/5 rounded-lg px-3 py-2">
              <p className="text-xs text-text-secondary">Market Size</p>
              <p className="text-sm font-mono text-text-primary">{d.market_size}</p>
            </div>
          )}
          {d.growth_rate && (
            <div className="bg-white/5 rounded-lg px-3 py-2">
              <p className="text-xs text-text-secondary">Growth Rate</p>
              <p className="text-sm font-mono text-text-primary">{d.growth_rate}</p>
            </div>
          )}
          {d.cyclicality && (
            <div className="bg-white/5 rounded-lg px-3 py-2">
              <p className="text-xs text-text-secondary">Cyclicality</p>
              <p className="text-sm text-text-primary">{d.cyclicality}</p>
            </div>
          )}
        </div>
      </div>

      {/* TAM / SAM / SOM */}
      {d.tam_sam_som && Object.keys(d.tam_sam_som).length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Total Addressable Market</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {["tam", "sam", "som"].map((key) => {
              const label = key.toUpperCase();
              const val = d.tam_sam_som[key] ?? d.tam_sam_som[label];
              if (val == null) return null;
              return (
                <div key={key} className="bg-white/5 rounded-lg px-4 py-3 text-center">
                  <p className="text-xs font-medium text-text-secondary uppercase mb-1">{label}</p>
                  <p className="text-lg font-bold font-mono text-text-primary">{formatValue(val)}</p>
                </div>
              );
            })}
            {/* Render any other keys in tam_sam_som not matching tam/sam/som */}
            {Object.entries(d.tam_sam_som)
              .filter(([k]) => !["tam", "sam", "som", "TAM", "SAM", "SOM"].includes(k))
              .map(([key, val]) => (
                <div key={key} className="bg-white/5 rounded-lg px-4 py-3 text-center">
                  <p className="text-xs font-medium text-text-secondary uppercase mb-1">{humanizeKey(key)}</p>
                  <p className="text-lg font-bold font-mono text-text-primary">{formatValue(val)}</p>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Key Trends */}
      {d.key_trends?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Key Trends</h3>
          <ol className="space-y-2">
            {d.key_trends.map((trend, idx) => (
              <li key={idx} className="flex items-start gap-3 text-sm text-text-primary">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-500/10 text-blue-400 text-xs font-bold flex items-center justify-center">
                  {idx + 1}
                </span>
                <span className="pt-0.5">{trend}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Regulatory Environment */}
      {d.regulatory_environment && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Regulatory Environment</h3>
          <p className="text-sm text-text-primary leading-relaxed">{d.regulatory_environment}</p>
        </div>
      )}

      {/* Sector-Specific KPIs */}
      {d.sector_specific_kpis && Object.keys(d.sector_specific_kpis).length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Sector-Specific KPIs</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(d.sector_specific_kpis).map(([key, value]) => (
              <div key={key} className="bg-white/5 rounded-lg px-3 py-2">
                <p className="text-xs text-text-secondary">{humanizeKey(key)}</p>
                <p className="text-sm font-mono text-text-primary">{formatValue(value)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Key Players */}
      {d.key_players?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Key Players</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {(() => {
                    const allKeys = Array.from(
                      new Set(d.key_players.flatMap((p) => Object.keys(p)))
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
                {d.key_players.map((player, idx) => {
                  const allKeys = Array.from(
                    new Set(d.key_players.flatMap((p) => Object.keys(p)))
                  );
                  return (
                    <tr key={idx} className="hover:bg-white/5">
                      {allKeys.map((key) => (
                        <td key={key} className="py-2 pr-4 text-text-primary">
                          {player[key] != null ? String(player[key]) : "N/A"}
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

      {/* Barriers to Entry & Disruption Risks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {d.barriers_to_entry?.length > 0 && (
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-text-primary mb-3">
              <span className="inline-flex items-center gap-1.5">
                <ShieldAlert size={14} className="text-text-tertiary" />
                Barriers to Entry
              </span>
            </h3>
            <ul className="space-y-2">
              {d.barriers_to_entry.map((barrier, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-text-primary">
                  <span className="text-text-tertiary mt-0.5 flex-shrink-0">&#8226;</span>
                  <span>{barrier}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {d.disruption_risks?.length > 0 && (
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-text-primary mb-3">
              <span className="inline-flex items-center gap-1.5">
                <AlertTriangle size={14} className="text-amber-500" />
                Disruption Risks
              </span>
            </h3>
            <ul className="space-y-2">
              {d.disruption_risks.map((risk, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-text-primary">
                  <AlertTriangle size={12} className="text-amber-400 mt-0.5 flex-shrink-0" />
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Recent M&A */}
      {d.recent_m_and_a?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            <span className="inline-flex items-center gap-1.5">
              <Merge size={14} className="text-text-tertiary" />
              Recent M&amp;A Activity
            </span>
          </h3>
          <ul className="space-y-2">
            {d.recent_m_and_a.map((deal, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-text-primary">
                <span className="text-text-tertiary font-mono text-xs mt-0.5 flex-shrink-0">
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <span>{deal}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
