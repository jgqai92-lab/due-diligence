"use client";

import { cn } from "@/lib/utils";
import { AlertTriangle, Users, Briefcase } from "lucide-react";

// ─── Data Shape ─────────────────────────────────────────────────────

interface ManagementAssessmentData {
  ceo: Record<string, unknown>;
  cfo: Record<string, unknown>;
  board_composition: Record<string, unknown>;
  compensation_analysis: Record<string, unknown>;
  insider_ownership: string | null;
  governance_red_flags: string[];
  management_quality_score: number | null; // 1-10
  track_record: string;
  key_concerns: string[];
}

// ─── Props ──────────────────────────────────────────────────────────

interface ManagementAssessmentProps {
  data: Record<string, unknown>;
}

// ─── Helpers ────────────────────────────────────────────────────────

function scoreColor(score: number | null): string {
  if (score == null) return "text-text-tertiary";
  if (score >= 8) return "text-emerald-400";
  if (score >= 5) return "text-amber-400";
  return "text-red-400";
}

function scoreBg(score: number | null): string {
  if (score == null) return "bg-white/5";
  if (score >= 8) return "bg-emerald-500/10";
  if (score >= 5) return "bg-amber-500/10";
  return "bg-red-500/10";
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

// ─── Key-Value Grid Sub-component ───────────────────────────────────

function KeyValueGrid({
  title,
  icon,
  record,
}: {
  title: string;
  icon?: React.ReactNode;
  record: Record<string, unknown> | null | undefined;
}) {
  if (!record || Object.keys(record).length === 0) return null;

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
        {icon}
        {title}
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {Object.entries(record).map(([key, value]) => (
          <div key={key} className="bg-white/5 rounded-lg px-3 py-2">
            <p className="text-xs text-text-secondary">{formatKey(key)}</p>
            <p className="text-sm font-mono text-text-primary">{formatValue(value)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Component ──────────────────────────────────────────────────────

export default function ManagementAssessment({ data }: ManagementAssessmentProps) {
  const d = data as unknown as ManagementAssessmentData;

  return (
    <div className="space-y-4">
      {/* Management Quality Score Banner */}
      <div
        className={cn(
          "rounded-xl border px-6 py-5 flex items-center gap-4",
          scoreBg(d.management_quality_score),
          d.management_quality_score != null && d.management_quality_score >= 8
            ? "border-emerald-500/30"
            : d.management_quality_score != null && d.management_quality_score >= 5
            ? "border-amber-500/30"
            : d.management_quality_score != null
            ? "border-red-500/30"
            : "border-border"
        )}
      >
        <Users size={24} className={scoreColor(d.management_quality_score)} />
        <div className="flex-1">
          <p className="text-xs text-text-secondary mb-1">Management Quality Score</p>
          <div className="flex items-baseline gap-1">
            <span
              className={cn(
                "text-3xl font-bold font-mono",
                scoreColor(d.management_quality_score)
              )}
            >
              {d.management_quality_score != null ? d.management_quality_score : "N/A"}
            </span>
            {d.management_quality_score != null && (
              <span className="text-sm text-text-secondary">/10</span>
            )}
          </div>
        </div>
        {d.insider_ownership && (
          <div className="bg-white/10 rounded-lg px-3 py-2 text-right">
            <p className="text-xs text-text-secondary">Insider Ownership</p>
            <p className="text-sm font-mono font-medium text-text-primary">
              {d.insider_ownership}
            </p>
          </div>
        )}
      </div>

      {/* CEO Section */}
      <KeyValueGrid
        title="CEO"
        icon={<Briefcase size={14} className="text-text-tertiary" />}
        record={d.ceo}
      />

      {/* CFO Section */}
      <KeyValueGrid
        title="CFO"
        icon={<Briefcase size={14} className="text-text-tertiary" />}
        record={d.cfo}
      />

      {/* Board Composition */}
      <KeyValueGrid title="Board Composition" record={d.board_composition} />

      {/* Compensation Analysis */}
      <KeyValueGrid title="Compensation Analysis" record={d.compensation_analysis} />

      {/* Track Record */}
      {d.track_record && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Track Record</h3>
          <p className="text-sm text-text-primary leading-relaxed">{d.track_record}</p>
        </div>
      )}

      {/* Governance Red Flags */}
      {d.governance_red_flags && d.governance_red_flags.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Governance Red Flags ({d.governance_red_flags.length})
          </h3>
          <ul className="space-y-2">
            {d.governance_red_flags.map((flag, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <AlertTriangle
                  size={14}
                  className="text-amber-500 mt-0.5 flex-shrink-0"
                />
                <span className="text-text-primary">{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Key Concerns */}
      {d.key_concerns && d.key_concerns.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Key Concerns ({d.key_concerns.length})
          </h3>
          <ul className="space-y-2">
            {d.key_concerns.map((concern, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <span className="text-red-400 mt-0.5 flex-shrink-0">&#x2022;</span>
                <span className="text-text-primary">{concern}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
