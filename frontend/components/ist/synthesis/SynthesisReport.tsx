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

  return (
    <div className="space-y-3">
      {metadata && (
        <pre className="text-xs text-text-secondary bg-white/5 rounded-lg p-3 overflow-auto">
          {JSON.stringify(metadata, null, 2)}
        </pre>
      )}
      <article className="prose prose-invert max-w-none text-sm">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {report}
        </ReactMarkdown>
      </article>
    </div>
  );
}
