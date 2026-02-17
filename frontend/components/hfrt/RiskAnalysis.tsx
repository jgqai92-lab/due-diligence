"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { AlertTriangle, ChevronDown, ChevronUp, Shield } from "lucide-react";

// ─── Data Shape ─────────────────────────────────────────────────────

interface RiskItem {
  risk: string;
  category: string;
  probability: string;
  impact: string;
  severity_score: number; // 1-25
  mitigation: string;
}

interface RiskAnalysisData {
  risk_register: RiskItem[];
  top_risks: string[];
  risk_heat_map: Record<string, unknown>;
  scenario_analysis: Array<Record<string, unknown>>;
  overall_risk_rating: string;
}

// ─── Props ──────────────────────────────────────────────────────────

interface RiskAnalysisProps {
  data: Record<string, unknown>;
}

// ─── Helpers ────────────────────────────────────────────────────────

function ratingColor(rating: string): {
  bg: string;
  text: string;
  border: string;
} {
  const r = rating?.toLowerCase() ?? "";
  if (r === "low")
    return {
      bg: "bg-emerald-500/10",
      text: "text-emerald-300",
      border: "border-emerald-500/30",
    };
  if (r === "moderate")
    return {
      bg: "bg-amber-500/10",
      text: "text-amber-300",
      border: "border-amber-500/30",
    };
  // high, very high, critical
  return { bg: "bg-red-500/10", text: "text-red-300", border: "border-red-500/30" };
}

function severityColor(score: number): string {
  if (score <= 5) return "bg-emerald-500/10 text-emerald-300";
  if (score <= 10) return "bg-yellow-500/10 text-yellow-300";
  if (score <= 15) return "bg-amber-500/10 text-amber-300";
  return "bg-red-500/10 text-red-300";
}

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

// ─── Expandable Risk Row ────────────────────────────────────────────

function RiskRow({ item }: { item: RiskItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        className="hover:bg-white/5 cursor-pointer transition-colors duration-150"
        onClick={() => setExpanded(!expanded)}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        aria-label={`Risk: ${item.risk}. Click to ${expanded ? "collapse" : "expand"} mitigation details.`}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setExpanded(!expanded);
          }
        }}
      >
        <td className="px-3 py-2.5 text-sm text-text-primary max-w-[200px]">
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronUp size={14} className="text-text-tertiary flex-shrink-0" />
            ) : (
              <ChevronDown size={14} className="text-text-tertiary flex-shrink-0" />
            )}
            <span className="truncate">{item.risk}</span>
          </div>
        </td>
        <td className="px-3 py-2.5 text-xs text-text-secondary">{item.category}</td>
        <td className="px-3 py-2.5 text-xs text-text-secondary">{item.probability}</td>
        <td className="px-3 py-2.5 text-xs text-text-secondary">{item.impact}</td>
        <td className="px-3 py-2.5">
          <span
            className={cn(
              "inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium",
              severityColor(item.severity_score)
            )}
          >
            {item.severity_score}
          </span>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={5} className="px-3 py-3 bg-white/5">
            <div className="ml-6">
              <p className="text-xs font-semibold text-text-secondary mb-1">Mitigation</p>
              <p className="text-sm text-text-primary leading-relaxed">
                {item.mitigation || "No mitigation strategy documented."}
              </p>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ─── Component ──────────────────────────────────────────────────────

export default function RiskAnalysis({ data }: RiskAnalysisProps) {
  const d = data as unknown as RiskAnalysisData;
  const rc = ratingColor(d.overall_risk_rating);

  return (
    <div className="space-y-4">
      {/* Overall Risk Rating Badge */}
      <div
        className={cn(
          "rounded-xl border px-6 py-5 flex items-center gap-4",
          d.overall_risk_rating?.toLowerCase() === "low"
            ? "bg-emerald-500/10 border-emerald-500/30"
            : d.overall_risk_rating?.toLowerCase() === "moderate"
            ? "bg-amber-500/10 border-amber-500/30"
            : "bg-red-500/10 border-red-500/30"
        )}
      >
        <Shield size={24} className={rc.text} />
        <div className="flex-1">
          <p className="text-xs text-text-secondary mb-1">Overall Risk Rating</p>
          <span
            className={cn(
              "inline-flex items-center px-3 py-1 rounded-full text-sm font-bold",
              rc.bg,
              rc.text
            )}
          >
            {d.overall_risk_rating || "N/A"}
          </span>
        </div>
      </div>

      {/* Top Risks */}
      {d.top_risks && d.top_risks.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Top Risks</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {d.top_risks.map((risk, idx) => (
              <div
                key={idx}
                className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 flex items-start gap-2"
              >
                <AlertTriangle
                  size={14}
                  className="text-red-500 mt-0.5 flex-shrink-0"
                />
                <span className="text-sm text-red-300">{risk}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk Register Table */}
      {d.risk_register && d.risk_register.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h3 className="text-sm font-semibold text-text-primary">
              Risk Register ({d.risk_register.length})
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-black/30 border-b border-border">
                  <th className="px-3 py-2 text-xs font-semibold text-text-secondary">
                    Risk
                  </th>
                  <th className="px-3 py-2 text-xs font-semibold text-text-secondary">
                    Category
                  </th>
                  <th className="px-3 py-2 text-xs font-semibold text-text-secondary">
                    Probability
                  </th>
                  <th className="px-3 py-2 text-xs font-semibold text-text-secondary">
                    Impact
                  </th>
                  <th className="px-3 py-2 text-xs font-semibold text-text-secondary">
                    Severity
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {d.risk_register.map((item, idx) => (
                  <RiskRow key={idx} item={item} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Scenario Analysis */}
      {d.scenario_analysis && d.scenario_analysis.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Scenario Analysis
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {d.scenario_analysis.map((scenario, idx) => (
              <div
                key={idx}
                className="bg-white/5 rounded-lg px-4 py-3 space-y-2"
              >
                {Object.entries(scenario).map(([key, value]) => (
                  <div key={key}>
                    <p className="text-xs text-text-secondary">{formatKey(key)}</p>
                    <p className="text-sm text-text-primary">{formatValue(value)}</p>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
