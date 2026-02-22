"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface SynthesisReportProps {
  report: string | null;
  metadata: Record<string, unknown> | null;
}

export default function SynthesisReport({ report, metadata }: SynthesisReportProps) {
  if (!report) {
    return <p className="text-sm text-text-secondary">Synthesis report not generated yet.</p>;
  }

  const metadataMap = (metadata ?? {}) as Record<string, unknown>;
  const tierBreakdown = (
    metadataMap.tierBreakdown && typeof metadataMap.tierBreakdown === "object"
      ? metadataMap.tierBreakdown
      : {}
  ) as Record<string, number>;

  return (
    <div className="space-y-3">
      {metadata && (
        <div className="flex flex-wrap items-center gap-3 text-xs text-text-secondary">
          {metadataMap.equityCount != null && (
            <span>{String(metadataMap.equityCount)} equities analyzed</span>
          )}
          {Object.keys(tierBreakdown).length > 0 && (
            <span>
              T1: {String(tierBreakdown.tier1 ?? 0)} | T2: {String(tierBreakdown.tier2 ?? 0)}{" "}
              | T3: {String(tierBreakdown.tier3 ?? 0)}
            </span>
          )}
        </div>
      )}
      <article className="prose prose-invert max-w-none text-sm">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {report}
        </ReactMarkdown>
      </article>
    </div>
  );
}
