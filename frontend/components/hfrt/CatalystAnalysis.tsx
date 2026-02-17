"use client";

import { cn } from "@/lib/utils";
import { Zap, Clock, Calendar } from "lucide-react";

// ─── Data Shape ─────────────────────────────────────────────────────

interface CatalystAnalysisData {
  catalysts: Array<Record<string, unknown>>;
  timeline: Array<Record<string, unknown>>;
  probability_matrix: Array<Record<string, unknown>>;
  key_catalyst: string;
  expected_timeline: string;
}

// ─── Props ──────────────────────────────────────────────────────────

interface CatalystAnalysisProps {
  data: Record<string, unknown>;
}

// ─── Helpers ────────────────────────────────────────────────────────

function formatKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(value: unknown): string {
  if (value == null) return "N/A";
  if (typeof value === "number") {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value);
}

// ─── Component ──────────────────────────────────────────────────────

export default function CatalystAnalysis({ data }: CatalystAnalysisProps) {
  const d = data as unknown as CatalystAnalysisData;

  return (
    <div className="space-y-4">
      {/* Key Catalyst Banner */}
      {d.key_catalyst && (
        <div className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-6 py-5 flex items-start gap-4">
          <Zap size={22} className="text-sky-400 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-xs font-semibold text-sky-400 uppercase mb-1">
              Key Catalyst
            </p>
            <p className="text-sm text-text-primary leading-relaxed">
              {d.key_catalyst}
            </p>
          </div>
          {d.expected_timeline && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-sky-500/10 text-xs font-medium text-sky-300 flex-shrink-0">
              <Clock size={12} />
              {d.expected_timeline}
            </span>
          )}
        </div>
      )}

      {/* Expected Timeline Badge (standalone if no key_catalyst) */}
      {!d.key_catalyst && d.expected_timeline && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-text-tertiary" />
            <p className="text-xs text-text-secondary">Expected Timeline</p>
          </div>
          <p className="text-sm font-medium text-text-primary mt-1">
            {d.expected_timeline}
          </p>
        </div>
      )}

      {/* Catalysts List */}
      {d.catalysts && d.catalysts.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Catalysts ({d.catalysts.length})
          </h3>
          <div className="space-y-3">
            {d.catalysts.map((catalyst, idx) => {
              const name =
                catalyst.name ?? catalyst.catalyst ?? catalyst.title ?? null;
              const description =
                catalyst.description ?? catalyst.details ?? null;
              const date =
                catalyst.date ?? catalyst.timeframe ?? catalyst.timing ?? null;
              const probability = catalyst.probability ?? null;
              const impact =
                catalyst.expected_impact ?? catalyst.impact ?? null;

              return (
                <div
                  key={idx}
                  className="bg-white/5 rounded-lg px-4 py-3 border border-border"
                >
                  <div className="flex items-start justify-between gap-3 mb-1">
                    <p className="text-sm font-medium text-text-primary">
                      {formatValue(name) !== "N/A"
                        ? formatValue(name)
                        : `Catalyst ${idx + 1}`}
                    </p>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {date && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-blue-500/10 text-blue-300">
                          <Calendar size={10} />
                          {formatValue(date)}
                        </span>
                      )}
                      {probability && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-purple-500/10 text-purple-300">
                          {formatValue(probability)}
                        </span>
                      )}
                    </div>
                  </div>
                  {description && (
                    <p className="text-xs text-text-secondary leading-relaxed mt-1">
                      {formatValue(description)}
                    </p>
                  )}
                  {impact && (
                    <p className="text-xs text-text-secondary mt-1.5">
                      <span className="font-medium">Expected Impact:</span>{" "}
                      {formatValue(impact)}
                    </p>
                  )}

                  {/* Render any other fields not already displayed */}
                  {Object.entries(catalyst)
                    .filter(
                      ([key]) =>
                        ![
                          "name",
                          "catalyst",
                          "title",
                          "description",
                          "details",
                          "date",
                          "timeframe",
                          "timing",
                          "probability",
                          "expected_impact",
                          "impact",
                        ].includes(key)
                    )
                    .map(([key, value]) => (
                      <p key={key} className="text-xs text-text-secondary mt-1">
                        <span className="font-medium">{formatKey(key)}:</span>{" "}
                        {formatValue(value)}
                      </p>
                    ))}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Timeline Section */}
      {d.timeline && d.timeline.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <Calendar size={14} className="text-text-tertiary" />
            Timeline
          </h3>
          <div className="space-y-3">
            {d.timeline.map((item, idx) => (
              <div
                key={idx}
                className="flex items-start gap-3 pl-2 border-l-2 border-sky-500/30"
              >
                <div className="flex-1 py-1">
                  {Object.entries(item).map(([key, value]) => (
                    <div key={key} className="mb-1 last:mb-0">
                      <span className="text-xs text-text-secondary">
                        {formatKey(key)}:
                      </span>{" "}
                      <span className="text-sm text-text-primary">
                        {formatValue(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Probability Matrix */}
      {d.probability_matrix && d.probability_matrix.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h3 className="text-sm font-semibold text-text-primary">
              Probability Matrix
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-black/30 border-b border-border">
                  {d.probability_matrix[0] &&
                    Object.keys(d.probability_matrix[0]).map((key) => (
                      <th
                        key={key}
                        className="px-3 py-2 text-xs font-semibold text-text-secondary"
                      >
                        {formatKey(key)}
                      </th>
                    ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {d.probability_matrix.map((row, idx) => (
                  <tr key={idx} className="hover:bg-white/5">
                    {Object.values(row).map((value, vIdx) => (
                      <td
                        key={vIdx}
                        className="px-3 py-2 text-sm text-text-primary"
                      >
                        {formatValue(value)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
