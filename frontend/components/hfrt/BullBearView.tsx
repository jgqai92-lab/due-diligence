"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { getDialecticReview } from "@/lib/api/hfrt";
import type { HFRTDialecticReview } from "@/types/hfrt";
import { TrendingUp, TrendingDown, AlertCircle, Loader2, ChevronDown, ChevronUp } from "lucide-react";

// ─── Helpers ────────────────────────────────────────────────────────

const LEVEL_ALIASES: Record<string, string> = {
  HIGH: "HIGH", MEDIUM: "MEDIUM", LOW: "LOW",
  MODERATE: "MEDIUM", VERY_HIGH: "HIGH", VERY_LOW: "LOW",
};

function parseConvictionLevel(raw: string): { label: string; summary: string | null } {
  const match = raw.match(/^(\w[\w\s]*?)\s*[\u2014\u2013\-:]\s+([\s\S]+)/);
  if (match) {
    const word = match[1].trim().toUpperCase().replace(/\s+/g, "_");
    return { label: LEVEL_ALIASES[word] ?? word, summary: match[2].trim() };
  }
  const upper = raw.trim().toUpperCase().replace(/\s+/g, "_");
  return { label: LEVEL_ALIASES[upper] ?? upper, summary: null };
}

function splitTitleDescription(
  text: string
): { title: string; description: string } | null {
  const match = text.match(/^([A-Z][A-Z0-9\s\-./&,()]+?)[\s]*[\u2014\u2013:]\s+([\s\S]+)/);
  if (!match) return null;
  const title = match[1].trim();
  if (title.length < 3) return null;
  return { title, description: match[2].trim() };
}

function CollapsibleItem({
  text,
  accentColor,
  marker,
}: {
  text: string;
  accentColor: string;
  marker: string;
}) {
  const parsed = splitTitleDescription(text);
  const [open, setOpen] = useState(false);

  if (!parsed) {
    return (
      <li className="text-xs text-text-secondary flex items-start gap-1.5">
        <span className={cn("mt-0.5", accentColor)}>{marker}</span>
        {text}
      </li>
    );
  }

  return (
    <li>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-start gap-1.5 text-left text-xs hover:bg-white/5 rounded py-0.5 transition-colors"
        aria-expanded={open}
      >
        <span className={cn("mt-0.5 flex-shrink-0", accentColor)}>{marker}</span>
        <span className={cn("font-semibold flex-1 min-w-0", accentColor)}>{parsed.title}</span>
        {open ? (
          <ChevronUp size={12} className="text-text-tertiary flex-shrink-0 mt-0.5" />
        ) : (
          <ChevronDown size={12} className="text-text-tertiary flex-shrink-0 mt-0.5" />
        )}
      </button>
      {open && (
        <div className="ml-4 pl-2 border-l border-border mt-0.5 mb-1">
          <p className="text-xs text-text-secondary leading-relaxed">{parsed.description}</p>
        </div>
      )}
    </li>
  );
}

interface BullBearViewProps {
  projectId: number;
}

export default function BullBearView({ projectId }: BullBearViewProps) {
  const [bull, setBull] = useState<HFRTDialecticReview | null>(null);
  const [bear, setBear] = useState<HFRTDialecticReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    Promise.allSettled([
      getDialecticReview(projectId, "bull"),
      getDialecticReview(projectId, "bear"),
    ])
      .then(([bullResult, bearResult]) => {
        if (bullResult.status === "fulfilled") setBull(bullResult.value);
        if (bearResult.status === "fulfilled") setBear(bearResult.value);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load reviews");
      })
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 size={24} className="animate-spin text-text-tertiary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-5 py-4 flex items-start gap-3">
        <AlertCircle size={16} className="text-red-500 mt-0.5" />
        <p className="text-xs text-red-400">{error}</p>
      </div>
    );
  }

  if (!bull && !bear) {
    return (
      <div className="text-center py-12 text-text-tertiary">
        <p className="text-sm">Dialectic analysis not yet completed.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Bull Case */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-emerald-500/30 rounded-xl overflow-hidden">
        <div className="bg-emerald-500/10 px-5 py-3 flex items-center gap-2 border-b border-emerald-500/30">
          <TrendingUp size={18} className="text-emerald-400" />
          <h3 className="text-sm font-semibold text-emerald-300">Bull Case</h3>
          {bull?.content?.convictionLevel && (
            <span className="ml-auto text-xs font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
              {parseConvictionLevel(bull.content.convictionLevel).label}
            </span>
          )}
        </div>
        <div className="p-5 space-y-4">
          {bull?.content ? (
            <>
              {/* Conviction Summary */}
              {bull.content.convictionLevel && (() => {
                const { summary } = parseConvictionLevel(bull.content.convictionLevel);
                if (!summary) return null;
                return (
                  <div className="p-3 rounded-lg border bg-emerald-500/10 border-emerald-500/30">
                    <p className="text-[11px] font-medium text-text-secondary mb-1">Summary</p>
                    <p className="text-xs text-text-primary leading-relaxed">{summary}</p>
                  </div>
                );
              })()}

              <p className="text-sm text-text-primary leading-relaxed">{bull.content.narrative}</p>

              {bull.content.keyArguments?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-text-secondary uppercase mb-2">Key Arguments</h4>
                  <ul className="space-y-1">
                    {bull.content.keyArguments.map((arg, i) => (
                      <CollapsibleItem key={i} text={arg} accentColor="text-emerald-500" marker="+" />
                    ))}
                  </ul>
                </div>
              )}

              {bull.content.catalysts?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-text-secondary uppercase mb-2">Catalysts</h4>
                  <ul className="space-y-1">
                    {bull.content.catalysts.map((cat, i) => (
                      <li key={i} className="text-xs text-text-secondary">{cat}</li>
                    ))}
                  </ul>
                </div>
              )}

              {bull.content.priceTarget != null && (
                <div className="bg-emerald-500/10 rounded-lg px-3 py-2">
                  <p className="text-xs text-emerald-400">Price Target</p>
                  <p className="text-lg font-bold font-mono text-emerald-300">
                    ${bull.content.priceTarget.toFixed(2)}
                  </p>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-text-tertiary">Bull case not yet generated.</p>
          )}
        </div>
      </div>

      {/* Bear Case */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-red-500/30 rounded-xl overflow-hidden">
        <div className="bg-red-500/10 px-5 py-3 flex items-center gap-2 border-b border-red-500/30">
          <TrendingDown size={18} className="text-red-400" />
          <h3 className="text-sm font-semibold text-red-300">Bear Case</h3>
          {bear?.content?.convictionLevel && (
            <span className="ml-auto text-xs font-medium text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full">
              {parseConvictionLevel(bear.content.convictionLevel).label}
            </span>
          )}
        </div>
        <div className="p-5 space-y-4">
          {bear?.content ? (
            <>
              {/* Conviction Summary */}
              {bear.content.convictionLevel && (() => {
                const { summary } = parseConvictionLevel(bear.content.convictionLevel);
                if (!summary) return null;
                return (
                  <div className="p-3 rounded-lg border bg-red-500/10 border-red-500/30">
                    <p className="text-[11px] font-medium text-text-secondary mb-1">Summary</p>
                    <p className="text-xs text-text-primary leading-relaxed">{summary}</p>
                  </div>
                );
              })()}

              <p className="text-sm text-text-primary leading-relaxed">{bear.content.narrative}</p>

              {bear.content.keyArguments?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-text-secondary uppercase mb-2">Key Arguments</h4>
                  <ul className="space-y-1">
                    {bear.content.keyArguments.map((arg, i) => (
                      <CollapsibleItem key={i} text={arg} accentColor="text-red-500" marker="-" />
                    ))}
                  </ul>
                </div>
              )}

              {bear.content.risks?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-text-secondary uppercase mb-2">Key Risks</h4>
                  <ul className="space-y-1">
                    {bear.content.risks.map((risk, i) => (
                      <CollapsibleItem key={i} text={risk} accentColor="text-red-500" marker="-" />
                    ))}
                  </ul>
                </div>
              )}

              {bear.content.priceTarget != null && (
                <div className="bg-red-500/10 rounded-lg px-3 py-2">
                  <p className="text-xs text-red-400">Price Target</p>
                  <p className="text-lg font-bold font-mono text-red-300">
                    ${bear.content.priceTarget.toFixed(2)}
                  </p>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-text-tertiary">Bear case not yet generated.</p>
          )}
        </div>
      </div>
    </div>
  );
}
