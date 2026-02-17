"use client";

import { cn } from "@/lib/utils";
import { Calculator, TrendingUp, TrendingDown, ArrowRight } from "lucide-react";

/* ── Data shape from ValuationResult (Template 06) ────────────────── */

interface DCFValuation {
  wacc: number | null;
  wacc_components: Record<string, unknown>;
  projected_fcf: Array<Record<string, unknown>>;
  terminal_value: number | null;
  terminal_growth_rate: number | null;
  enterprise_value: number | null;
  equity_value: number | null;
  implied_share_price: number | null;
  current_price: number | null;
  upside_downside_pct: number | null;
}

interface ValuationData {
  dcf: DCFValuation;
  relative_valuation: Record<string, unknown>;
  sensitivity_table: Array<Record<string, unknown>>;
  peer_comparison: Array<Record<string, unknown>>;
  valuation_summary: string;
  fair_value_range: Record<string, unknown>;
}

interface ValuationPanelProps {
  data: Record<string, unknown>;
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDollar(val: number | null): string {
  if (val == null) return "N/A";
  return "$" + val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatLarge(val: number | null): string {
  if (val == null) return "N/A";
  const abs = Math.abs(val);
  if (abs >= 1e12) return "$" + (val / 1e12).toFixed(2) + "T";
  if (abs >= 1e9) return "$" + (val / 1e9).toFixed(2) + "B";
  if (abs >= 1e6) return "$" + (val / 1e6).toFixed(2) + "M";
  return "$" + val.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatPct(val: number | null): string {
  if (val == null) return "N/A";
  return (val * 100).toFixed(2) + "%";
}

function formatValue(val: unknown): string {
  if (val == null) return "N/A";
  if (typeof val === "number") {
    if (Math.abs(val) < 1 && val !== 0) {
      return (val * 100).toFixed(2) + "%";
    }
    return val.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(val);
}

export default function ValuationPanel({ data }: ValuationPanelProps) {
  const d = data as unknown as ValuationData;

  if (!d || (!d.dcf && !d.valuation_summary)) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 text-center py-12 text-text-tertiary">
        <Calculator size={32} className="mx-auto mb-3" />
        <p className="text-sm">Valuation analysis not yet available.</p>
      </div>
    );
  }

  const dcf = d.dcf;
  const upside = dcf?.upside_downside_pct;
  const isPositive = upside != null && upside > 0;
  const isNegative = upside != null && upside < 0;

  return (
    <div className="space-y-4">
      {/* DCF Headline: Implied vs Current price */}
      {dcf && (
        <div className={cn(
          "rounded-xl border px-6 py-5",
          isPositive ? "bg-emerald-500/10 border-emerald-500/30" :
          isNegative ? "bg-red-500/10 border-red-500/30" :
          "bg-white/5 border-border"
        )}>
          <div className="flex flex-wrap items-center gap-4 mb-2">
            {isPositive ? (
              <TrendingUp size={28} className="text-emerald-400" />
            ) : isNegative ? (
              <TrendingDown size={28} className="text-red-400" />
            ) : (
              <Calculator size={28} className="text-text-tertiary" />
            )}
            <div className="flex-1 min-w-[200px]">
              <p className="text-xs text-text-secondary mb-1">DCF Implied Share Price</p>
              <div className="flex flex-wrap items-baseline gap-3">
                <span className={cn(
                  "text-2xl font-bold font-mono",
                  isPositive ? "text-emerald-300" : isNegative ? "text-red-300" : "text-text-primary"
                )}>
                  {formatDollar(dcf.implied_share_price)}
                </span>
                {dcf.current_price != null && (
                  <>
                    <span className="text-sm text-text-tertiary">vs</span>
                    <span className="text-lg font-mono text-text-secondary">
                      {formatDollar(dcf.current_price)} current
                    </span>
                  </>
                )}
                {upside != null && (
                  <span className={cn(
                    "inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-bold",
                    isPositive ? "bg-emerald-500/10 text-emerald-300" :
                    isNegative ? "bg-red-500/10 text-red-300" :
                    "bg-white/10 text-text-primary"
                  )}>
                    {isPositive ? "+" : ""}{(upside * 100).toFixed(1)}%
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* WACC & Terminal Growth Rate */}
      {dcf && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">DCF Assumptions</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-white/5 rounded-lg px-3 py-2">
              <p className="text-xs text-text-secondary">WACC</p>
              <p className="text-sm font-mono font-bold text-text-primary">{formatPct(dcf.wacc)}</p>
            </div>
            <div className="bg-white/5 rounded-lg px-3 py-2">
              <p className="text-xs text-text-secondary">Terminal Growth</p>
              <p className="text-sm font-mono font-bold text-text-primary">{formatPct(dcf.terminal_growth_rate)}</p>
            </div>
            {dcf.wacc_components && Object.entries(dcf.wacc_components).map(([key, val]) => (
              <div key={key} className="bg-white/5 rounded-lg px-3 py-2">
                <p className="text-xs text-text-secondary">{humanizeKey(key)}</p>
                <p className="text-sm font-mono text-text-primary">{formatValue(val)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Projected FCF table */}
      {dcf?.projected_fcf?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Projected Free Cash Flow</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left text-xs font-medium text-text-secondary pb-2 pr-4">Year</th>
                  <th className="text-right text-xs font-medium text-text-secondary pb-2">FCF</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {dcf.projected_fcf.map((row, idx) => (
                  <tr key={idx} className="hover:bg-white/5">
                    <td className="py-2 pr-4 text-text-primary font-medium">
                      {String(row.year ?? row.period ?? `Year ${idx + 1}`)}
                    </td>
                    <td className="py-2 text-right font-mono text-text-primary">
                      {row.fcf != null
                        ? formatLarge(Number(row.fcf))
                        : row.free_cash_flow != null
                        ? formatLarge(Number(row.free_cash_flow))
                        : "N/A"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Value Flow: Terminal -> Enterprise -> Equity */}
      {dcf && (dcf.terminal_value != null || dcf.enterprise_value != null || dcf.equity_value != null) && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Value Bridge</h3>
          <div className="flex flex-wrap items-center justify-center gap-2">
            {dcf.terminal_value != null && (
              <div className="bg-white/5 rounded-lg px-4 py-3 text-center min-w-[120px]">
                <p className="text-xs text-text-secondary mb-0.5">Terminal Value</p>
                <p className="text-lg font-bold font-mono text-text-primary">{formatLarge(dcf.terminal_value)}</p>
              </div>
            )}
            {dcf.terminal_value != null && dcf.enterprise_value != null && (
              <ArrowRight size={20} className="text-text-tertiary flex-shrink-0" />
            )}
            {dcf.enterprise_value != null && (
              <div className="bg-white/5 rounded-lg px-4 py-3 text-center min-w-[120px]">
                <p className="text-xs text-text-secondary mb-0.5">Enterprise Value</p>
                <p className="text-lg font-bold font-mono text-text-primary">{formatLarge(dcf.enterprise_value)}</p>
              </div>
            )}
            {dcf.enterprise_value != null && dcf.equity_value != null && (
              <ArrowRight size={20} className="text-text-tertiary flex-shrink-0" />
            )}
            {dcf.equity_value != null && (
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg px-4 py-3 text-center min-w-[120px]">
                <p className="text-xs text-blue-400 mb-0.5">Equity Value</p>
                <p className="text-lg font-bold font-mono text-blue-300">{formatLarge(dcf.equity_value)}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Sensitivity Table */}
      {d.sensitivity_table?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Sensitivity Analysis</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {(() => {
                    const allKeys = Array.from(
                      new Set(d.sensitivity_table.flatMap((r) => Object.keys(r)))
                    );
                    return allKeys.map((key) => (
                      <th key={key} className="text-center text-xs font-medium text-text-secondary pb-2 px-2">
                        {humanizeKey(key)}
                      </th>
                    ));
                  })()}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {d.sensitivity_table.map((row, idx) => {
                  const allKeys = Array.from(
                    new Set(d.sensitivity_table.flatMap((r) => Object.keys(r)))
                  );
                  return (
                    <tr key={idx} className="hover:bg-white/5">
                      {allKeys.map((key, colIdx) => {
                        const val = row[key];
                        const isNumeric = typeof val === "number";
                        // Color-code implied prices relative to current price
                        let cellColor = "";
                        if (colIdx > 0 && isNumeric && dcf?.current_price != null) {
                          if ((val as number) > dcf.current_price * 1.1) cellColor = "bg-emerald-500/10 text-emerald-300";
                          else if ((val as number) < dcf.current_price * 0.9) cellColor = "bg-red-500/10 text-red-300";
                          else cellColor = "bg-amber-500/10 text-amber-300";
                        }
                        return (
                          <td key={key} className={cn(
                            "py-2 px-2 text-center font-mono text-text-primary",
                            colIdx === 0 ? "font-medium text-text-primary" : "",
                            cellColor
                          )}>
                            {isNumeric ? formatValue(val) : (val != null ? String(val) : "N/A")}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {dcf?.current_price != null && (
            <p className="text-xs text-text-tertiary mt-2">
              Cells color-coded relative to current price of {formatDollar(dcf.current_price)}
            </p>
          )}
        </div>
      )}

      {/* Relative Valuation */}
      {d.relative_valuation && Object.keys(d.relative_valuation).length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Relative Valuation</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {Object.entries(d.relative_valuation).map(([key, val]) => (
              <div key={key} className="bg-white/5 rounded-lg px-3 py-2">
                <p className="text-xs text-text-secondary">{humanizeKey(key)}</p>
                <p className="text-sm font-mono text-text-primary">{formatValue(val)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Peer Comparison */}
      {d.peer_comparison?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Peer Comparison</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {(() => {
                    const allKeys = Array.from(
                      new Set(d.peer_comparison.flatMap((p) => Object.keys(p)))
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
                {d.peer_comparison.map((peer, idx) => {
                  const allKeys = Array.from(
                    new Set(d.peer_comparison.flatMap((p) => Object.keys(p)))
                  );
                  return (
                    <tr key={idx} className="hover:bg-white/5">
                      {allKeys.map((key) => (
                        <td key={key} className="py-2 pr-4 text-text-primary font-mono">
                          {peer[key] != null ? formatValue(peer[key]) : "N/A"}
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

      {/* Fair Value Range */}
      {d.fair_value_range && Object.keys(d.fair_value_range).length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Fair Value Range</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {["bear", "base", "bull"].map((scenario) => {
              const val = d.fair_value_range[scenario] ?? d.fair_value_range[scenario + "_case"];
              if (val == null) return null;
              const colors = {
                bear: { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-300", label: "Bear" },
                base: { bg: "bg-white/5", border: "border-border", text: "text-text-primary", label: "Base" },
                bull: { bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-300", label: "Bull" },
              }[scenario]!;
              return (
                <div key={scenario} className={cn("rounded-lg px-4 py-3 text-center border", colors.bg, colors.border)}>
                  <p className={cn("text-xs font-medium mb-1", colors.text)}>{colors.label} Case</p>
                  <p className={cn("text-xl font-bold font-mono", colors.text)}>
                    {typeof val === "number" ? formatDollar(val) : String(val)}
                  </p>
                </div>
              );
            })}
            {/* Render any other keys not in bear/base/bull */}
            {Object.entries(d.fair_value_range)
              .filter(([k]) => !["bear", "base", "bull", "bear_case", "base_case", "bull_case"].includes(k))
              .map(([key, val]) => (
                <div key={key} className="bg-white/5 rounded-lg px-4 py-3 text-center">
                  <p className="text-xs text-text-secondary mb-1">{humanizeKey(key)}</p>
                  <p className="text-lg font-bold font-mono text-text-primary">{formatValue(val)}</p>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Valuation Summary */}
      {d.valuation_summary && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Valuation Summary</h3>
          <p className="text-sm text-text-primary leading-relaxed">{d.valuation_summary}</p>
        </div>
      )}
    </div>
  );
}
