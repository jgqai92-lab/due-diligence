"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { getCertification, getHandoff } from "@/lib/api/ist";
import type {
  CertificationResponse,
  CertificationInvariant,
  HandoffResponse,
  HandoffCandidate,
} from "@/types/ist";
import {
  AlertCircle,
  Award,
  CheckCircle,
  Clock,
  ExternalLink,
  FileText,
  Layers,
  Loader2,
  ShieldCheck,
  ShieldAlert,
  Trophy,
  XCircle,
} from "lucide-react";

// ─── Skeleton ───────────────────────────────────────────────────────

function CertificationSkeleton() {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-4 animate-fade-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-white/10 rounded-full animate-pulse" />
        <div className="space-y-1.5">
          <div className="h-4 w-48 bg-white/10 rounded animate-pulse" />
          <div className="h-3 w-32 bg-white/10 rounded animate-pulse" />
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 bg-white/10 rounded-lg animate-pulse" />
        ))}
      </div>
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-8 bg-white/10 rounded animate-pulse" />
        ))}
      </div>
    </div>
  );
}

// ─── Stat Card ──────────────────────────────────────────────────────

function StatCard({
  icon: Icon,
  label,
  value,
  variant = "default",
}: {
  icon: typeof FileText;
  label: string;
  value: string | number;
  variant?: "default" | "success" | "warning";
}) {
  return (
    <div
      className={cn(
        "rounded-lg border px-3 py-2.5",
        variant === "success" && "bg-emerald-500/10 border-emerald-500/30",
        variant === "warning" && "bg-amber-500/10 border-amber-500/30",
        variant === "default" && "bg-white/5 border-border"
      )}
    >
      <div className="flex items-center gap-1.5 mb-1">
        <Icon
          size={12}
          className={cn(
            variant === "success" && "text-emerald-500",
            variant === "warning" && "text-amber-500",
            variant === "default" && "text-text-tertiary"
          )}
        />
        <span className="text-[10px] text-text-secondary">{label}</span>
      </div>
      <p
        className={cn(
          "text-sm font-semibold font-mono",
          variant === "success" && "text-emerald-400",
          variant === "warning" && "text-amber-400",
          variant === "default" && "text-text-primary"
        )}
      >
        {value}
      </p>
    </div>
  );
}

// ─── Invariant Row ──────────────────────────────────────────────────

function InvariantRow({ inv }: { inv: CertificationInvariant }) {
  const passed = inv.status === "PASS";
  return (
    <div
      className={cn(
        "flex items-center gap-2.5 py-2 px-3 rounded-md text-xs",
        passed ? "hover:bg-emerald-500/10" : "bg-red-500/5 hover:bg-red-500/10"
      )}
    >
      {passed ? (
        <CheckCircle size={14} className="text-emerald-500 flex-shrink-0" />
      ) : (
        <XCircle size={14} className="text-red-500 flex-shrink-0" />
      )}
      <span className="font-mono text-text-secondary w-10 flex-shrink-0">{inv.id}</span>
      <span className={cn("font-medium", passed ? "text-text-primary" : "text-red-400")}>
        {inv.name}
      </span>
      <span className="text-text-tertiary ml-auto hidden sm:inline">{inv.details}</span>
    </div>
  );
}

// ─── Handoff Candidate Row ──────────────────────────────────────────

function CandidateRow({ c }: { c: HandoffCandidate }) {
  return (
    <tr className="border-b border-border hover:bg-white/5 transition-colors">
      <td className="px-3 py-2 text-xs font-mono font-medium text-text-primary">
        {c.ticker}
      </td>
      <td className="px-3 py-2 text-xs text-text-primary">{c.companyName}</td>
      <td className="px-3 py-2 text-xs text-text-secondary">{c.pillar}</td>
      <td className="px-3 py-2">
        <span
          className={cn(
            "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium",
            c.conviction === "HIGH"
              ? "bg-emerald-500/20 text-emerald-400"
              : c.conviction === "MEDIUM"
              ? "bg-amber-500/20 text-amber-400"
              : "bg-white/10 text-text-secondary"
          )}
        >
          {c.conviction}
        </span>
      </td>
      <td className="px-3 py-2 text-xs text-text-secondary max-w-[200px] truncate">
        {c.catalyst || "—"}
      </td>
    </tr>
  );
}

// ─── Props ──────────────────────────────────────────────────────────

interface ScreenCertificationProps {
  screenId: number;
}

// ─── Component ──────────────────────────────────────────────────────

export default function ScreenCertification({ screenId }: ScreenCertificationProps) {
  const [certData, setCertData] = useState<CertificationResponse | null>(null);
  const [handoffData, setHandoffData] = useState<HandoffResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cert, handoff] = await Promise.all([
        getCertification(screenId),
        getHandoff(screenId),
      ]);
      setCertData(cert);
      setHandoffData(handoff);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load certification data"
      );
    } finally {
      setLoading(false);
    }
  }, [screenId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ─── Loading ──────────────────────────────────────────────────

  if (loading) return <CertificationSkeleton />;

  // ─── Error ────────────────────────────────────────────────────

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

  // ─── Not Certified Yet ────────────────────────────────────────

  if (!certData) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-14 h-14 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-4">
          <Award size={24} className="text-text-tertiary" />
        </div>
        <h2 className="text-base font-semibold text-text-primary mb-1">
          Not Yet Certified
        </h2>
        <p className="text-sm text-text-secondary max-w-sm mx-auto">
          Screen certification will be available after the coherence gate passes
          and the screen is certified.
        </p>
      </div>
    );
  }

  const cert = certData.certification;
  const certDate = new Date(cert.certifiedAt).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  // ─── Render ───────────────────────────────────────────────────

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Certification Header */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
        <div className="flex items-start gap-4 mb-5">
          <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
            <ShieldCheck size={20} className="text-emerald-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-text-primary">
              Screen Certified
            </h3>
            <p className="text-xs text-text-secondary mt-0.5">
              {certData.screenName} &mdash; Certified {certDate}
            </p>
          </div>
          <div className="ml-auto">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-xs font-medium text-emerald-400">
              <CheckCircle size={12} />
              Gate 3 Passed
            </span>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          <StatCard icon={Layers} label="Pillars" value={cert.pillarCount} />
          <StatCard icon={Trophy} label="Total Equities" value={cert.totalRankedEquities} />
          <StatCard icon={FileText} label="Report Words" value={cert.reportWordCount.toLocaleString()} />
          <StatCard
            icon={ShieldCheck}
            label="Invariants"
            value={`${cert.invariantsPassed}/${cert.invariantsPassed + cert.invariantsFailed}`}
            variant={cert.invariantsFailed === 0 ? "success" : "warning"}
          />
        </div>

        {/* Tier Breakdown */}
        <div className="flex items-center gap-4 text-xs text-text-secondary mb-5">
          <span>
            Tier 1: <strong className="text-text-primary">{cert.tierBreakdown.tier1}</strong>
          </span>
          <span className="text-text-tertiary">|</span>
          <span>
            Tier 2: <strong className="text-text-primary">{cert.tierBreakdown.tier2}</strong>
          </span>
          <span className="text-text-tertiary">|</span>
          <span>
            Tier 3: <strong className="text-text-primary">{cert.tierBreakdown.tier3}</strong>
          </span>
          <span className="text-text-tertiary">|</span>
          <span className="text-text-tertiary">
            Model: <span className="font-mono">{cert.model}</span>
          </span>
        </div>

        {/* Invariant Results */}
        <div>
          <h4 className="text-xs font-semibold text-text-primary mb-2">
            Invariant Compliance
          </h4>
          <div className="space-y-0.5" role="list" aria-label="Certification invariants">
            {cert.invariantResults.map((inv) => (
              <InvariantRow key={inv.id} inv={inv} />
            ))}
          </div>
        </div>
      </div>

      {/* HFRT Handoff Table */}
      {handoffData && handoffData.candidates.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <ExternalLink size={14} className="text-primary" />
                HFRT Handoff Candidates
              </h3>
              <p className="text-xs text-text-secondary mt-0.5">
                {handoffData.tier1Count} Tier 1 candidate{handoffData.tier1Count !== 1 ? "s" : ""}{" "}
                ready for deep-dive research
              </p>
            </div>
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-primary/10 text-[10px] font-medium text-primary">
              <Clock size={10} />
              Awaiting HFRT
            </span>
          </div>

          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-left" role="table">
              <thead>
                <tr className="bg-white/5 border-b border-border">
                  <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                    Ticker
                  </th>
                  <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                    Company
                  </th>
                  <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                    Pillar
                  </th>
                  <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                    Conviction
                  </th>
                  <th className="px-3 py-2.5 text-[11px] font-medium text-text-secondary" scope="col">
                    Catalyst
                  </th>
                </tr>
              </thead>
              <tbody>
                {handoffData.candidates.map((c) => (
                  <CandidateRow key={c.ticker} c={c} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
