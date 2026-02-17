"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { cn } from "@/lib/utils";
import { getCatalysts } from "@/lib/api/ist";
import type { CatalystResponse, CatalystEvent } from "@/types/ist";
import {
  AlertCircle,
  Loader2,
  Calendar,
  Clock,
  Zap,
} from "lucide-react";

// ─── Importance Config ──────────────────────────────────────────

const IMPORTANCE_CONFIG: Record<string, { bg: string; text: string; dotBg: string }> = {
  HIGH:   { bg: "bg-red-500/10", text: "text-red-400", dotBg: "bg-red-500" },
  MEDIUM: { bg: "bg-amber-500/10", text: "text-amber-400", dotBg: "bg-amber-500" },
  LOW:    { bg: "bg-white/10", text: "text-text-secondary", dotBg: "bg-gray-400" },
};

// ─── Date Formatter ─────────────────────────────────────────────

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return `${Math.abs(diffDays)}d ago`;
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Tomorrow";
  if (diffDays <= 7) return `In ${diffDays}d`;
  if (diffDays <= 30) return `In ${Math.ceil(diffDays / 7)}w`;
  return `In ${Math.ceil(diffDays / 30)}mo`;
}

// ─── Next Catalyst Highlight Card ───────────────────────────────

function NextCatalystCard({
  nextCatalyst,
}: {
  nextCatalyst: CatalystResponse["nextCatalyst"];
}) {
  if (!nextCatalyst) return null;

  return (
    <div className="bg-gradient-to-r from-primary/5 to-primary/10 rounded-xl border border-primary/20 p-5 mb-6">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
          <Zap size={18} className="text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-medium text-primary uppercase tracking-wider mb-1">
            Next Catalyst
          </p>
          <p className="text-sm font-medium text-text-primary leading-relaxed">
            {nextCatalyst.event}
          </p>
          <div className="flex items-center gap-3 mt-2">
            <span className="inline-flex items-center gap-1.5 text-xs text-text-secondary">
              <Calendar size={12} className="text-text-tertiary" />
              {formatDate(nextCatalyst.date)}
            </span>
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-primary">
              <Clock size={12} />
              {nextCatalyst.daysUntil === 0
                ? "Today"
                : nextCatalyst.daysUntil === 1
                ? "Tomorrow"
                : `${nextCatalyst.daysUntil} days away`}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Catalyst Timeline Item ─────────────────────────────────────

function CatalystTimelineItem({
  catalyst,
  isLast,
}: {
  catalyst: CatalystEvent;
  isLast: boolean;
}) {
  const impConfig = IMPORTANCE_CONFIG[catalyst.importance] ?? IMPORTANCE_CONFIG.LOW;
  const isPast = new Date(catalyst.date) < new Date();

  return (
    <div className="flex gap-4">
      {/* Timeline connector */}
      <div className="flex flex-col items-center flex-shrink-0">
        <div
          className={cn(
            "w-3 h-3 rounded-full mt-1.5 flex-shrink-0",
            impConfig.dotBg,
            isPast && "opacity-50"
          )}
        />
        {!isLast && (
          <div className="w-px flex-1 bg-white/10 mt-1" />
        )}
      </div>

      {/* Content */}
      <div className={cn("pb-6 flex-1 min-w-0", isLast && "pb-0")}>
        {/* Date row */}
        <div className="flex items-center gap-2 mb-1.5">
          <span
            className={cn(
              "text-xs font-mono",
              isPast ? "text-text-tertiary" : "text-text-primary"
            )}
          >
            {formatDate(catalyst.date)}
          </span>
          {catalyst.dateType && (
            <span className="text-[10px] text-text-tertiary">
              ({catalyst.dateType})
            </span>
          )}
          <span
            className={cn(
              "text-[10px] font-mono",
              isPast ? "text-text-tertiary" : "text-text-secondary"
            )}
          >
            {formatRelativeDate(catalyst.date)}
          </span>
        </div>

        {/* Event description */}
        <p
          className={cn(
            "text-sm leading-relaxed mb-2",
            isPast ? "text-text-secondary" : "text-text-primary"
          )}
        >
          {catalyst.event}
        </p>

        {/* Badges row */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Importance */}
          <span
            className={cn(
              "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium",
              impConfig.bg,
              impConfig.text
            )}
          >
            {catalyst.importance}
          </span>

          {/* Pillar */}
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-violet-500/10 text-violet-400">
            {catalyst.pillar}
          </span>

          {/* Ticker pills */}
          {catalyst.tickers.map((ticker) => (
            <span
              key={ticker}
              className="inline-flex items-center px-2 py-0.5 rounded bg-white/10 text-[10px] font-mono font-medium text-text-primary"
            >
              {ticker}
            </span>
          ))}
        </div>

        {/* Expected impact */}
        {catalyst.expectedImpact && (
          <p className="text-[11px] text-text-secondary leading-relaxed mt-2 italic">
            Impact: {catalyst.expectedImpact}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Skeleton ────────────────────────────────────────────────────

function CatalystSkeleton() {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div className="h-5 w-32 bg-white/10 rounded animate-pulse" />
        <div className="h-6 w-20 bg-white/10 rounded-full animate-pulse" />
      </div>
      {/* Highlight card skeleton */}
      <div className="h-20 bg-white/10 rounded-xl animate-pulse" />
      {/* Timeline items skeleton */}
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <div className="flex flex-col items-center">
            <div className="w-3 h-3 bg-white/10 rounded-full animate-pulse" />
            <div className="w-px flex-1 bg-white/10 mt-1" />
          </div>
          <div className="flex-1 space-y-2 pb-6">
            <div className="h-3 w-32 bg-white/10 rounded animate-pulse" />
            <div className="h-4 w-full bg-white/10 rounded animate-pulse" />
            <div className="flex gap-2">
              <div className="h-5 w-14 bg-white/10 rounded-full animate-pulse" />
              <div className="h-5 w-16 bg-white/10 rounded-full animate-pulse" />
              <div className="h-5 w-12 bg-white/10 rounded animate-pulse" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Props ──────────────────────────────────────────────────────

interface CatalystCalendarProps {
  screenId: number;
}

// ─── Component ──────────────────────────────────────────────────

export default function CatalystCalendar({ screenId }: CatalystCalendarProps) {
  const [data, setData] = useState<CatalystResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getCatalysts(screenId);
      setData(result);
    } catch (err) {
      if ((err as any).status === 404) {
        setData(null);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load catalysts");
      }
    } finally {
      setLoading(false);
    }
  }, [screenId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Sort catalysts by date
  const sortedCatalysts = useMemo(() => {
    if (!data) return [];
    return [...data.catalysts].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );
  }, [data]);

  // ─── Loading State ──────────────────────────────────────────

  if (loading) {
    return <CatalystSkeleton />;
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

  if (!data || data.catalysts.length === 0) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <Calendar size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">No catalysts identified yet</p>
        <p className="text-xs text-text-secondary mt-1">
          Catalyst events will appear here once the synthesis phase completes.
        </p>
      </div>
    );
  }

  // ─── Render ───────────────────────────────────────────────────

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-5 gap-3">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Catalyst Calendar</h3>
          <p className="text-xs text-text-secondary mt-0.5">
            {data.totalCatalysts} catalyst event{data.totalCatalysts !== 1 ? "s" : ""} identified
          </p>
        </div>
        {/* Importance summary */}
        <div className="flex items-center gap-2 flex-wrap" role="list" aria-label="Catalyst importance breakdown">
          {(["HIGH", "MEDIUM", "LOW"] as const).map((imp) => {
            const count = data.catalysts.filter((c) => c.importance === imp).length;
            if (count === 0) return null;
            const cfg = IMPORTANCE_CONFIG[imp];
            return (
              <span
                key={imp}
                role="listitem"
                className={cn(
                  "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium",
                  cfg.bg,
                  cfg.text
                )}
              >
                {imp}: {count}
              </span>
            );
          })}
        </div>
      </div>

      {/* Next Catalyst Highlight */}
      <NextCatalystCard nextCatalyst={data.nextCatalyst} />

      {/* Timeline */}
      <div role="list" aria-label="Catalyst timeline">
        {sortedCatalysts.map((catalyst, idx) => (
          <div key={`${catalyst.date}-${idx}`} role="listitem">
            <CatalystTimelineItem
              catalyst={catalyst}
              isLast={idx === sortedCatalysts.length - 1}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
