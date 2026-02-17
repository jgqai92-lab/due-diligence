"use client";

import { useState, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import DOMPurify from "dompurify";
import { RefreshCw } from "lucide-react";
import type { ForensicReport } from "@/types/analysis";
import { cn } from "@/lib/utils";
import DataFreshnessIndicator from "./DataFreshnessIndicator";

interface InvestmentBriefPanelProps { report: ForensicReport; onRegenerate?: () => void; dataTimestamp?: string; }

type Recommendation = "INVEST" | "MONITOR" | "AVOID" | null;

function extractRecommendation(markdown: string): Recommendation {
  if (/\bINVEST\b/.test(markdown) && !/\bAVOID\b/.test(markdown)) return "INVEST";
  if (/\bAVOID\b/.test(markdown)) return "AVOID";
  if (/\bMONITOR\b/.test(markdown)) return "MONITOR";
  return null;
}

function getRecommendationStyle(rec: Recommendation): string {
  switch (rec) {
    case "INVEST": return "bg-bull/10 text-bull border-bull/30";
    case "MONITOR": return "bg-warning/10 text-warning border-warning/30";
    case "AVOID": return "bg-bear/10 text-bear border-bear/30";
    default: return "";
  }
}

function getCaseBorderClass(text: string): string | null {
  const lower = text.toLowerCase();
  if (lower.includes("bull case")) return "border-l-[3px] border-l-bull bg-bull/5 rounded-r-lg";
  if (lower.includes("bear case")) return "border-l-[3px] border-l-bear bg-bear/5 rounded-r-lg";
  if (lower.includes("base case")) return "border-l-[3px] border-l-warning bg-warning/5 rounded-r-lg";
  return null;
}

export default function InvestmentBriefPanel({ report, onRegenerate, dataTimestamp }: InvestmentBriefPanelProps) {
  const [regenerating, setRegenerating] = useState(false);
  const recommendation = extractRecommendation(report.markdown);
  const freshnessTimestamp = dataTimestamp ?? report.generated_at;

  const sanitizedMarkdown = useMemo(() => {
    if (typeof window !== "undefined") return DOMPurify.sanitize(report.markdown);
    return report.markdown;
  }, [report.markdown]);

  function handleRegenerate() {
    if (!onRegenerate) return;
    setRegenerating(true);
    onRegenerate();
    setTimeout(() => setRegenerating(false), 30000);
  }

  return (
    <div className="bg-surface rounded-xl shadow-card">
      <div className="flex items-center justify-between p-4 border-b border-border/50">
        <div className="flex items-center gap-3">
          <h3 className="text-xs font-medium tracking-wide text-text-secondary">Investment Brief</h3>
          <span className="px-2 py-0.5 bg-primary/10 text-primary text-[10px] font-medium rounded-lg border border-primary/20">AI-Generated</span>
          {recommendation && <span className={cn("px-2 py-0.5 text-[10px] font-bold uppercase rounded-lg border", getRecommendationStyle(recommendation))}>{recommendation}</span>}
        </div>
        <div className="flex items-center gap-3">
          <DataFreshnessIndicator fetchedAt={freshnessTimestamp} />
          {onRegenerate && (
            <button onClick={handleRegenerate} disabled={regenerating} className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-text-secondary hover:text-primary bg-background rounded-lg hover:shadow-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed" aria-label="Regenerate report">
              <RefreshCw size={12} className={cn(regenerating && "animate-spin")} />Regenerate
            </button>
          )}
        </div>
      </div>
      <div className="p-6 max-w-3xl">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
          h1: ({ children }) => <h1 className="text-xl font-display font-bold mt-6 mb-4 text-text-primary">{children}</h1>,
          h2: ({ children }) => {
            const text = String(children);
            const caseBorder = getCaseBorderClass(text);
            const isBear = text.toLowerCase().includes("bear case");
            const isBull = text.toLowerCase().includes("bull case");
            const isBase = text.toLowerCase().includes("base case");
            let textColor = "text-text-primary";
            if (isBear) textColor = "text-bear"; if (isBull) textColor = "text-bull"; if (isBase) textColor = "text-warning";
            if (caseBorder) return <div className={cn("pl-4 py-2 mt-8 mb-3", caseBorder)}><h2 className={cn("text-lg font-display font-semibold", textColor)}>{children}</h2></div>;
            return <h2 className={cn("text-lg font-display font-semibold mt-8 mb-3", textColor)}>{children}</h2>;
          },
          h3: ({ children }) => <h3 className="text-base font-display font-semibold mt-6 mb-2 text-text-primary">{children}</h3>,
          h4: ({ children }) => <h4 className="text-sm font-display font-semibold mt-4 mb-1.5 text-text-secondary">{children}</h4>,
          p: ({ children }) => <p className="text-sm text-text-primary leading-relaxed mb-3">{children}</p>,
          ul: ({ children }) => <ul className="text-sm text-text-primary list-disc list-inside mb-3 space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="text-sm text-text-primary list-decimal list-inside mb-3 space-y-1">{children}</ol>,
          li: ({ children }) => <li className="text-sm text-text-primary">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold text-text-primary">{children}</strong>,
          em: ({ children }) => <em className="italic text-text-secondary">{children}</em>,
          blockquote: ({ children }) => <blockquote className="border-l-[3px] border-bear/50 pl-4 my-4 bg-bear/5 py-2 rounded-r-lg">{children}</blockquote>,
          table: ({ children }) => <div className="overflow-x-auto my-4"><table className="w-full text-sm border border-border rounded-xl overflow-hidden">{children}</table></div>,
          thead: ({ children }) => <thead className="bg-background text-text-secondary text-xs">{children}</thead>,
          th: ({ children }) => <th className="px-3 py-2 text-left font-medium border-b border-border">{children}</th>,
          td: ({ children }) => <td className="px-3 py-2 border-b border-border/50 font-mono text-text-primary">{children}</td>,
          hr: () => <hr className="border-border my-6" />,
          code: ({ children, className }) => {
            const isBlock = className?.includes("language-");
            if (isBlock) return <code className="block bg-background border border-border rounded-xl p-4 font-mono text-xs text-text-primary overflow-x-auto my-3">{children}</code>;
            return <code className="bg-background px-1.5 py-0.5 font-mono text-xs text-primary rounded-md">{children}</code>;
          },
        }}>{sanitizedMarkdown}</ReactMarkdown>
      </div>
    </div>
  );
}
