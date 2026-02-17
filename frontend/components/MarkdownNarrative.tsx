"use client";

import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import DOMPurify from "dompurify";

interface MarkdownNarrativeProps {
  content: string;
  className?: string;
}

export default function MarkdownNarrative({ content, className }: MarkdownNarrativeProps) {
  const sanitized = useMemo(() => DOMPurify.sanitize(content), [content]);

  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
        h1: ({ children }) => <h1 className="text-base font-display font-bold mt-4 mb-2 text-text-primary">{children}</h1>,
        h2: ({ children }) => <h2 className="text-sm font-display font-semibold mt-4 mb-2 text-text-primary">{children}</h2>,
        h3: ({ children }) => <h3 className="text-xs font-display font-semibold mt-3 mb-1.5 text-text-primary">{children}</h3>,
        p: ({ children }) => <p className="text-xs text-text-secondary leading-relaxed mb-2">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold text-text-primary">{children}</strong>,
        em: ({ children }) => <em className="italic text-text-secondary">{children}</em>,
        ul: ({ children }) => <ul className="text-xs text-text-secondary list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="text-xs text-text-secondary list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li className="text-xs text-text-secondary">{children}</li>,
        blockquote: ({ children }) => <blockquote className="border-l-2 border-primary/40 pl-3 my-2 text-text-tertiary italic">{children}</blockquote>,
        table: ({ children }) => <div className="overflow-x-auto my-2"><table className="w-full text-xs border border-border rounded-lg overflow-hidden">{children}</table></div>,
        thead: ({ children }) => <thead className="bg-background text-text-secondary text-[11px]">{children}</thead>,
        th: ({ children }) => <th className="px-2 py-1.5 text-left font-medium border-b border-border">{children}</th>,
        td: ({ children }) => <td className="px-2 py-1.5 border-b border-border/50 font-mono text-text-primary">{children}</td>,
        hr: () => <hr className="border-border my-4" />,
        code: ({ children, className: codeClassName }) => {
          const isBlock = codeClassName?.includes("language-");
          if (isBlock) return <code className="block bg-black/30 border border-border rounded-lg p-3 font-mono text-[11px] text-text-primary overflow-x-auto my-2">{children}</code>;
          return <code className="bg-black/30 px-1 py-0.5 font-mono text-[11px] text-primary rounded">{children}</code>;
        },
      }}>{sanitized}</ReactMarkdown>
    </div>
  );
}
