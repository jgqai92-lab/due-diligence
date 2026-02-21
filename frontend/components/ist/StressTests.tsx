"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { getStressTests } from "@/lib/api/ist";
import type { StressTestResponse } from "@/types/ist";
import {
  AlertCircle,
  Loader2,
  Zap,
  Shield,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  TrendingDown,
} from "lucide-react";

// ─── Survival Score Color ───────────────────────────────────────

function survivalColor(score: number): string {
  if (score >= 70) return "text-emerald-400";
  if (score >= 40) return "text-amber-400";
  return "text-red-400";
}

function survivalBg(score: number): string {
  if (score >= 70) return "bg-emerald-500/10";
  if (score >= 40) return "bg-amber-500/10";
  return "bg-red-500/10";
}

function survivalBarColor(score: number): string {
  if (score >= 70) return "bg-emerald-500";
  if (score >= 40) return "bg-amber-500";
  return "bg-red-400";
}

// ─── Survival Score Summary Cards ───────────────────────────────

function SurvivalSummary({
  scores,
}: {
  scores: StressTestResponse["survivalSummary"];
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-4 py-3 text-center">
        <p className="text-[10px] font-medium text-text-secondary uppercase tracking-wider mb-1">
          Avg Tier 1 Survival
        </p>
        <p className={cn("text-2xl font-bold font-mono", survivalColor(scores.averageTier1))}>
          {scores.averageTier1.toFixed(0)}
        </p>
      </div>
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-4 py-3 text-center">
        <p className="text-[10px] font-medium text-text-secondary uppercase tracking-wider mb-1">
          Avg Tier 2 Survival
        </p>
        <p className={cn("text-2xl font-bold font-mono", survivalColor(scores.averageTier2))}>
          {scores.averageTier2.toFixed(0)}
        </p>
      </div>
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-4 py-3 text-center">
        <p className="text-[10px] font-medium text-text-secondary uppercase tracking-wider mb-1">
          Lowest Survivor
        </p>
        <div className="flex items-center justify-center gap-2">
          <span className="text-xs font-bold font-mono text-text-primary">
            {scores.lowestSurvivor.ticker}
          </span>
          <span className={cn("text-2xl font-bold font-mono", survivalColor(scores.lowestSurvivor.score))}>
            {scores.lowestSurvivor.score.toFixed(0)}
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Framework Test Card ────────────────────────────────────────

function FrameworkTestCard({
  test,
}: {
  test: StressTestResponse["frameworkTests"][0];
}) {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5 hover:bg-white/5 transition-colors duration-200">
      <div className="mb-3">
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-violet-500/10 text-violet-400 mb-2">
          {test.framework}
        </span>
        <p className="text-sm font-medium text-text-primary leading-relaxed">
          {test.scenario}
        </p>
      </div>

      {/* Impact */}
      <p className="text-xs text-text-secondary leading-relaxed mb-3 italic">
        {test.impact}
      </p>

      {/* Survivors vs Casualties */}
      <div className="grid grid-cols-2 gap-3">
        {/* Survivors */}
        <div>
          <p className="text-[10px] font-medium text-emerald-400 uppercase tracking-wider mb-1.5">
            Survivors ({test.survivorTickers.length})
          </p>
          <div className="flex flex-wrap gap-1">
            {test.survivorTickers.map((ticker) => (
              <span
                key={ticker}
                className="inline-flex items-center px-2 py-0.5 rounded bg-emerald-500/10 text-[10px] font-mono font-medium text-emerald-400"
              >
                {ticker}
              </span>
            ))}
            {test.survivorTickers.length === 0 && (
              <span className="text-[10px] text-text-tertiary italic">None</span>
            )}
          </div>
        </div>

        {/* Casualties */}
        <div>
          <p className="text-[10px] font-medium text-red-400 uppercase tracking-wider mb-1.5">
            Casualties ({test.casualtyTickers.length})
          </p>
          <div className="flex flex-wrap gap-1">
            {test.casualtyTickers.map((ticker) => (
              <span
                key={ticker}
                className="inline-flex items-center px-2 py-0.5 rounded bg-red-500/10 text-[10px] font-mono font-medium text-red-400"
              >
                {ticker}
              </span>
            ))}
            {test.casualtyTickers.length === 0 && (
              <span className="text-[10px] text-text-tertiary italic">None</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Name-level Test Row (expandable) ───────────────────────────

function NameTestRow({
  test,
}: {
  test: StressTestResponse["nameTests"][0];
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "w-full flex items-center justify-between px-4 py-3 text-left",
          "hover:bg-white/5 transition-colors duration-150",
          "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1",
          expanded && "bg-white/5"
        )}
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold font-mono text-text-primary">
            {test.ticker}
          </span>
          <span className="text-xs text-text-secondary">
            {test.companyName}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {/* Overall survival score */}
          <div className="flex items-center gap-2">
            <div
              className="h-2 w-16 bg-white/10 rounded-full overflow-hidden"
              aria-hidden="true"
            >
              <div
                className={cn("h-full rounded-full", survivalBarColor(test.overallSurvivalScore))}
                style={{ width: `${Math.min(test.overallSurvivalScore, 100)}%` }}
              />
            </div>
            <span
              className={cn(
                "text-xs font-bold font-mono",
                survivalColor(test.overallSurvivalScore)
              )}
            >
              {test.overallSurvivalScore.toFixed(0)}
            </span>
          </div>
          {expanded ? (
            <ChevronUp size={14} className="text-text-tertiary flex-shrink-0" />
          ) : (
            <ChevronDown size={14} className="text-text-tertiary flex-shrink-0" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-border bg-white/5">
          <div className="overflow-x-auto rounded-lg border border-border mt-3">
            <table className="w-full text-left" role="table">
              <thead>
                <tr className="bg-white/5 border-b border-border">
                  <th className="px-3 py-2 text-[11px] font-medium text-text-secondary" scope="col">
                    Scenario
                  </th>
                  <th className="px-3 py-2 text-[11px] font-medium text-text-secondary" scope="col">
                    Impact Severity
                  </th>
                  <th className="px-3 py-2 text-[11px] font-medium text-text-secondary" scope="col">
                    Survival Score
                  </th>
                </tr>
              </thead>
              <tbody>
                {test.scenarios.map((scenario, idx) => (
                  <tr
                    key={idx}
                    className={cn(
                      "border-b border-border",
                      idx % 2 === 1 && "bg-white/5"
                    )}
                  >
                    <td className="px-3 py-2 text-xs text-text-primary leading-relaxed">
                      {scenario.scenario}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={cn(
                          "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium",
                          scenario.impactSeverity.toLowerCase() === "high"
                            ? "bg-red-500/10 text-red-400"
                            : scenario.impactSeverity.toLowerCase() === "medium"
                            ? "bg-amber-500/10 text-amber-400"
                            : "bg-white/10 text-text-secondary"
                        )}
                      >
                        {scenario.impactSeverity}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <div
                          className="h-2 w-12 bg-white/10 rounded-full overflow-hidden"
                          aria-hidden="true"
                        >
                          <div
                            className={cn(
                              "h-full rounded-full",
                              survivalBarColor(scenario.survivalScore)
                            )}
                            style={{
                              width: `${Math.min(scenario.survivalScore, 100)}%`,
                            }}
                          />
                        </div>
                        <span
                          className={cn(
                            "text-xs font-mono font-medium",
                            survivalColor(scenario.survivalScore)
                          )}
                        >
                          {scenario.survivalScore.toFixed(0)}
                        </span>
                      </div>
                    </td>
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

// ─── Skeleton ────────────────────────────────────────────────────

function StressTestSkeleton() {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-4 py-3">
            <div className="h-3 w-24 bg-white/10 rounded animate-pulse mx-auto mb-2" />
            <div className="h-8 w-12 bg-white/10 rounded animate-pulse mx-auto" />
          </div>
        ))}
      </div>
      {/* Framework cards */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-4">
        <div className="h-5 w-40 bg-white/10 rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 bg-white/10 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
      {/* Name tests */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-3">
        <div className="h-5 w-40 bg-white/10 rounded animate-pulse" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-12 bg-white/10 rounded-lg animate-pulse" />
        ))}
      </div>
    </div>
  );
}

// ─── Props ──────────────────────────────────────────────────────

interface StressTestsProps {
  screenId: number;
}

// ─── Component ──────────────────────────────────────────────────

export default function StressTests({ screenId }: StressTestsProps) {
  const [data, setData] = useState<StressTestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getStressTests(screenId);
      setData(result);
    } catch (err) {
      if ((err as any).status === 404) {
        setData(null);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load stress tests");
      }
    } finally {
      setLoading(false);
    }
  }, [screenId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ─── Loading State ──────────────────────────────────────────

  if (loading) {
    return <StressTestSkeleton />;
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

  if (!data || (data.frameworkTests.length === 0 && data.nameTests.length === 0)) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <Zap size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">No stress tests yet</p>
        <p className="text-xs text-text-secondary mt-1">
          Stress test results will appear here once the synthesis phase completes.
        </p>
      </div>
    );
  }

  // ─── Render ───────────────────────────────────────────────────

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Survival Score Summary */}
      {data.survivalSummary && (
        <SurvivalSummary scores={data.survivalSummary} />
      )}

      {/* Framework-level Tests */}
      {data.frameworkTests.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-text-primary">Framework Stress Tests</h3>
            <p className="text-xs text-text-secondary mt-0.5">
              {data.frameworkTests.length} scenario{data.frameworkTests.length !== 1 ? "s" : ""} tested
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.frameworkTests.map((test, idx) => (
              <FrameworkTestCard key={idx} test={test} />
            ))}
          </div>
        </div>
      )}

      {/* Name-level Tests */}
      {data.nameTests.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-text-primary">Name-Level Stress Tests</h3>
            <p className="text-xs text-text-secondary mt-0.5">
              Per-equity survival analysis across stress scenarios
            </p>
          </div>
          <div className="space-y-2" role="list" aria-label="Name-level stress tests">
            {data.nameTests.map((test) => (
              <div key={test.ticker} role="listitem">
                <NameTestRow test={test} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
