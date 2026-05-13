"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { getDemandModels } from "@/lib/api/ist";
import type { DemandModel, DemandModelsResponse } from "@/types/ist";
import { AlertCircle, Loader2, ArrowRight, BookOpen, Info } from "lucide-react";

// ─── TAM Formatter ──────────────────────────────────────────────────

/**
 * Parse a TAM value that may be a number (in $B) or a string like "$225B annually".
 * Returns the numeric value in billions, or null if unparseable.
 */
/**
 * Parse a TAM value that may be:
 *   - A raw-dollar number (e.g., 9000000000 = $9B)
 *   - A number already in billions (e.g., 225)
 *   - A string with suffix (e.g., "$225B", "$2.0T", "$450M")
 *
 * Returns the numeric value in billions, or null if unparseable.
 *
 * Heuristic for bare numbers: if the value is > 10,000 it's almost certainly
 * raw dollars, not billions (no single bottleneck has a $10,000B TAM).
 */
function parseTam(raw: unknown): number | null {
  if (raw == null) return null;

  if (typeof raw === "number") {
    if (isNaN(raw)) return null;
    // Bare numbers > 10,000 are raw dollars — convert to billions
    if (raw > 10_000) return raw / 1_000_000_000;
    return raw;
  }

  if (typeof raw !== "string") return null;

  const s = raw.replace(/,/g, "").trim();

  // Match patterns like "$2.0T", "$225B", "$450M", "$12K", or bare numbers with suffix
  const match = s.match(/([\d.]+)\s*(T|B|M|K)?/i);
  if (!match) return null;

  const num = parseFloat(match[1]);
  if (isNaN(num)) return null;

  const suffix = (match[2] || "").toUpperCase();
  switch (suffix) {
    case "T": return num * 1_000;   // trillions -> billions
    case "B": return num;           // already billions
    case "M": return num / 1_000;   // millions -> billions
    case "K": return num / 1_000_000;
    default:
      // Bare number in a string — apply same heuristic
      if (num > 10_000) return num / 1_000_000_000;
      return num;
  }
}

function formatTam(value: unknown): string {
  const num = parseTam(value);
  if (num == null) return "—";
  if (num >= 1_000) {
    return `$${(num / 1_000).toFixed(1)}T`;
  }
  if (num >= 1) {
    return `$${num.toFixed(1)}B`;
  }
  return `$${(num * 1_000).toFixed(0)}M`;
}

// ─── Number Formatter ───────────────────────────────────────────────

function formatSensitivityValue(value: unknown): string {
  if (value == null) return "—";
  // Claude often returns sensitivity values as descriptive strings ("4%", "Severe (-35%)")
  if (typeof value === "string") return value;
  if (typeof value !== "number" || isNaN(value)) return "—";
  if (Math.abs(value) >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toLocaleString("en-US");
}

// ─── Skeleton Card ──────────────────────────────────────────────────

function SkeletonModelCard() {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-4">
      <div className="h-5 w-48 bg-white/10 rounded animate-pulse" />
      <div className="h-12 w-full bg-white/10 rounded-lg animate-pulse" />
      <div className="grid grid-cols-3 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-16 bg-white/10 rounded-lg animate-pulse" />
        ))}
      </div>
      <div className="h-24 w-full bg-white/10 rounded-lg animate-pulse" />
    </div>
  );
}

// ─── Multiplier Chain Display ───────────────────────────────────────

function MultiplierChain({ chain }: { chain: string }) {
  const parts = chain.split(/\s*[*x\u00D7]\s*/i).filter(Boolean);

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {parts.map((part, idx) => (
        <span key={idx} className="inline-flex items-center">
          <span className="inline-flex items-center px-2 py-0.5 rounded bg-white/10 text-xs font-mono text-text-primary">
            {part.trim()}
          </span>
          {idx < parts.length - 1 && (
            <ArrowRight size={12} className="text-text-tertiary mx-0.5" aria-hidden="true" />
          )}
        </span>
      ))}
    </div>
  );
}

// ─── Model Card ─────────────────────────────────────────────────────

function DemandModelCard({ model }: { model: DemandModel }) {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 hover:bg-white/5 transition-colors duration-200">
      {/* Header */}
      <h4 className="text-sm font-semibold text-text-primary mb-4">
        {model.bottleneckName}
      </h4>

      {/* Formula */}
      <div className="bg-white/5 rounded-lg px-4 py-3 mb-5">
        <p className="text-[11px] font-medium text-text-secondary mb-1">Formula</p>
        <p className="text-xs font-mono text-text-primary leading-relaxed break-all">
          {model.formula}
        </p>
      </div>

      {/* Scenario columns: Bear / Base / Bull */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        {/* Bear */}
        <div className="bg-red-500/10 rounded-lg px-3 py-3 text-center overflow-hidden">
          <p className="text-[11px] font-medium text-red-400 mb-1">Bear Case</p>
          <p className="text-lg font-bold font-mono text-red-400">
            {formatTam(model.bearCase.tam)}
          </p>
          <p className="text-[10px] text-red-500 mt-0.5 leading-snug break-words">
            {model.bearCase.demand}
          </p>
        </div>

        {/* Base */}
        <div className="bg-white/10 rounded-lg px-3 py-3 text-center overflow-hidden">
          <p className="text-[11px] font-medium text-text-secondary mb-1">Base Case</p>
          <p className="text-lg font-bold font-mono text-text-primary">
            {formatTam(model.baseCase.tam)}
          </p>
          <p className="text-[10px] text-text-secondary mt-0.5 leading-snug break-words">
            {model.baseCase.demand}
          </p>
        </div>

        {/* Bull */}
        <div className="bg-emerald-500/10 rounded-lg px-3 py-3 text-center overflow-hidden">
          <p className="text-[11px] font-medium text-emerald-400 mb-1">Bull Case</p>
          <p className="text-lg font-bold font-mono text-emerald-400">
            {formatTam(model.bullCase.tam)}
          </p>
          <p className="text-[10px] text-emerald-500 mt-0.5 leading-snug break-words">
            {model.bullCase.demand}
          </p>
        </div>
      </div>

      {/* Sensitivity Table */}
      {model.sensitivityTable.length > 0 && (
        <div className="mb-5">
          <p className="text-[11px] font-medium text-text-secondary mb-2">Sensitivity Analysis</p>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-left" role="table">
              <thead>
                <tr className="bg-white/5 border-b border-border">
                  <th className="px-3 py-2 text-[11px] font-medium text-text-secondary" scope="col">Variable</th>
                  <th className="px-3 py-2 text-[11px] font-medium text-red-500 text-right" scope="col">Low</th>
                  <th className="px-3 py-2 text-[11px] font-medium text-text-secondary text-right" scope="col">Base</th>
                  <th className="px-3 py-2 text-[11px] font-medium text-emerald-500 text-right" scope="col">High</th>
                  <th className="px-3 py-2 text-[11px] font-medium text-text-secondary text-right" scope="col">TAM Impact</th>
                </tr>
              </thead>
              <tbody>
                {model.sensitivityTable.map((row, idx) => (
                  <tr
                    key={idx}
                    className={cn(
                      "border-b border-border",
                      idx % 2 === 1 && "bg-white/5"
                    )}
                  >
                    <td className="px-3 py-2 text-xs text-text-primary">{row.variable}</td>
                    <td className="px-3 py-2 text-xs font-mono text-red-400 text-right">
                      {formatSensitivityValue(row.low)}
                    </td>
                    <td className="px-3 py-2 text-xs font-mono text-text-primary text-right">
                      {formatSensitivityValue(row.base)}
                    </td>
                    <td className="px-3 py-2 text-xs font-mono text-emerald-400 text-right">
                      {formatSensitivityValue(row.high)}
                    </td>
                    <td className="px-3 py-2 text-xs text-text-secondary text-right">
                      {row.tamImpact}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Multiplier Chain */}
      {model.multiplierChain && (
        <div className="mb-5">
          <p className="text-[11px] font-medium text-text-secondary mb-2">Multiplier Chain</p>
          <MultiplierChain chain={model.multiplierChain} />
        </div>
      )}

      {/* Methodology */}
      {model.methodology && (
        <div className="mb-5">
          <div className="flex items-center gap-1.5 mb-2">
            <Info size={12} className="text-text-tertiary" />
            <p className="text-[11px] font-medium text-text-secondary">Methodology</p>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed">
            {model.methodology}
          </p>
        </div>
      )}

      {/* Sources */}
      {model.sources && model.sources.length > 0 ? (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <BookOpen size={12} className="text-text-tertiary" />
            <p className="text-[11px] font-medium text-text-secondary">Sources</p>
          </div>
          <ul className="space-y-1">
            {model.sources.map((source, idx) => (
              <li key={idx} className="text-xs text-text-secondary leading-relaxed flex items-start gap-1.5">
                <span className="text-text-tertiary mt-0.5 shrink-0">{idx + 1}.</span>
                <span>{source}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="border-t border-border pt-4">
          <div className="flex items-center gap-1.5">
            <Info size={12} className="text-text-tertiary" />
            <p className="text-[11px] text-text-tertiary italic">
              Source citations and methodology will appear for newly created screens.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Props ──────────────────────────────────────────────────────────

interface DemandModelsProps {
  screenId: number;
}

// ─── Component ──────────────────────────────────────────────────────

export default function DemandModels({ screenId }: DemandModelsProps) {
  const [data, setData] = useState<DemandModelsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getDemandModels(screenId);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load demand models");
    } finally {
      setLoading(false);
    }
  }, [screenId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ─── Loading State ────────────────────────────────────────────

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-1">
          <div className="h-5 w-40 bg-white/10 rounded animate-pulse" />
          <div className="h-5 w-24 bg-white/10 rounded animate-pulse" />
        </div>
        <SkeletonModelCard />
        <SkeletonModelCard />
      </div>
    );
  }

  // ─── Error State ──────────────────────────────────────────────

  if (error) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-8 text-center">
        <AlertCircle size={24} className="mx-auto text-red-400 mb-2" />
        <p className="text-sm text-red-400">{error}</p>
        <button
          onClick={fetchData}
          className="mt-3 text-xs font-medium text-primary hover:text-primary-hover transition-colors duration-200"
        >
          Try again
        </button>
      </div>
    );
  }

  // ─── Empty State ──────────────────────────────────────────────

  if (!data || data.demandModels.length === 0) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <Loader2 size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">No demand models yet</p>
        <p className="text-xs text-text-secondary mt-1">
          Demand models will appear here once the analysis phase completes.
        </p>
      </div>
    );
  }

  // ─── Render ───────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Demand Models</h3>
          <p className="text-xs text-text-secondary mt-0.5">
            {data.demandModels.length} model{data.demandModels.length !== 1 ? "s" : ""} with scenario analysis
          </p>
        </div>
      </div>

      {/* Model cards */}
      <div className="grid grid-cols-1 gap-4">
        {data.demandModels.map((model) => (
          <DemandModelCard key={model.id} model={model} />
        ))}
      </div>
    </div>
  );
}
