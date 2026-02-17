"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { RefreshCw } from "lucide-react";
import DataFreshnessIndicator from "./DataFreshnessIndicator";

interface ForensicReportProps { markdown: string; generatedAt: string; onRegenerate?: () => void; }

export default function ForensicReport({ markdown, generatedAt, onRegenerate }: ForensicReportProps) {
  return (
    <div className="bg-surface rounded-xl shadow-card">
      <div className="flex items-center justify-between p-4 border-b border-border/50">
        <div className="flex items-center gap-3">
          <h3 className="text-xs font-medium tracking-wide text-text-secondary">Forensic Report</h3>
          <span className="px-2 py-0.5 bg-primary/10 text-primary text-[10px] font-medium rounded-lg border border-primary/20">AI-Generated</span>
        </div>
        <div className="flex items-center gap-3">
          <DataFreshnessIndicator fetchedAt={generatedAt} />
          {onRegenerate && (
            <button onClick={onRegenerate} className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-text-secondary hover:text-primary bg-background rounded-lg hover:shadow-sm transition-all duration-200">
              <RefreshCw size={12} />Regenerate
            </button>
          )}
        </div>
      </div>
      <div className="p-6 max-w-3xl">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
          h2: ({ children }) => { const isBear = String(children).toLowerCase().includes("bear case"); return <h2 className={`text-lg font-display font-semibold mt-8 mb-3 ${isBear ? "text-bear" : "text-text-primary"}`}>{children}</h2>; },
          h3: ({ children }) => <h3 className="text-base font-display font-semibold mt-6 mb-2 text-text-primary">{children}</h3>,
          p: ({ children }) => <p className="text-sm text-text-primary leading-relaxed mb-3">{children}</p>,
          ul: ({ children }) => <ul className="text-sm text-text-primary list-disc list-inside mb-3 space-y-1">{children}</ul>,
          li: ({ children }) => <li className="text-sm text-text-primary">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold text-text-primary">{children}</strong>,
          blockquote: ({ children }) => <blockquote className="border-l-[3px] border-bear/50 pl-4 my-4 bg-bear/5 py-2 rounded-r-lg">{children}</blockquote>,
        }}>{markdown}</ReactMarkdown>
      </div>
    </div>
  );
}
