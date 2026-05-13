"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import {
  FileText,
  Printer,
  BarChart3,
  Trophy,
  Users,
  Hash,
  Layers,
  TrendingUp,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────

interface TocEntry {
  id: string;
  text: string;
  level: number;
}

type MdBlock =
  | { type: "heading"; level: 1 | 2 | 3 | 4; text: string; id: string }
  | { type: "blockquote"; lines: string[] }
  | { type: "table"; headers: string[]; rows: string[][] }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "code"; language: string; lines: string[] }
  | { type: "hr" }
  | { type: "paragraph"; text: string };

// ─── Markdown Parser (mirrors InvestmentThesisReport) ────────────

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .trim();
}

function parseMarkdown(raw: string): { blocks: MdBlock[]; toc: TocEntry[] } {
  const lines = raw.split("\n");
  const blocks: MdBlock[] = [];
  const toc: TocEntry[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Code block (fenced)
    if (line.trimStart().startsWith("```")) {
      const language = line.trimStart().slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trimStart().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++;
      blocks.push({ type: "code", language, lines: codeLines });
      continue;
    }

    // Horizontal rule
    if (/^(-{3,}|\*{3,}|_{3,})\s*$/.test(line.trim())) {
      blocks.push({ type: "hr" });
      i++;
      continue;
    }

    // Headings
    const headingMatch = line.match(/^(#{1,6})\s+(.+)/);
    if (headingMatch) {
      const level = Math.min(headingMatch[1].length, 4) as 1 | 2 | 3 | 4;
      const text = headingMatch[2].trim();
      const id = slugify(text);
      blocks.push({ type: "heading", level, text, id });
      toc.push({ id, text, level });
      i++;
      continue;
    }

    // Blockquote
    if (line.trimStart().startsWith(">")) {
      const bqLines: string[] = [];
      while (i < lines.length && lines[i].trimStart().startsWith(">")) {
        bqLines.push(lines[i].replace(/^>\s?/, ""));
        i++;
      }
      blocks.push({ type: "blockquote", lines: bqLines });
      continue;
    }

    // Table
    if (
      line.includes("|") &&
      i + 1 < lines.length &&
      /^[\s|:-]+$/.test(lines[i + 1])
    ) {
      const parseRow = (row: string) =>
        row
          .split("|")
          .map((c) => c.trim())
          .filter((c) => c.length > 0);
      const headers = parseRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim().length > 0) {
        rows.push(parseRow(lines[i]));
        i++;
      }
      blocks.push({ type: "table", headers, rows });
      continue;
    }

    // Unordered list
    if (/^(\s*[-*+])\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^(\s*[-*+])\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^(\s*[-*+])\s+/, ""));
        i++;
      }
      blocks.push({ type: "ul", items });
      continue;
    }

    // Ordered list
    if (/^\s*\d+[.)]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+[.)]\s+/, ""));
        i++;
      }
      blocks.push({ type: "ol", items });
      continue;
    }

    // Blank line
    if (line.trim() === "") {
      i++;
      continue;
    }

    // Paragraph
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !lines[i].trimStart().startsWith("#") &&
      !lines[i].trimStart().startsWith(">") &&
      !lines[i].trimStart().startsWith("```") &&
      !/^(\s*[-*+])\s+/.test(lines[i]) &&
      !/^\s*\d+[.)]\s+/.test(lines[i]) &&
      !(lines[i].includes("|") && i + 1 < lines.length && /^[\s|:-]+$/.test(lines[i + 1] ?? "")) &&
      !/^(-{3,}|\*{3,}|_{3,})\s*$/.test(lines[i].trim())
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    if (paraLines.length > 0) {
      blocks.push({ type: "paragraph", text: paraLines.join(" ") });
    }
  }

  return { blocks, toc };
}

// ─── Inline Formatting ──────────────────────────────────────────

function renderInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let keyIdx = 0;

  while (remaining.length > 0) {
    type MatchInfo = { match: RegExpMatchArray; type: string; index: number };
    const candidates: MatchInfo[] = [];

    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    if (boldMatch && boldMatch.index != null) {
      candidates.push({ match: boldMatch, type: "bold", index: boldMatch.index });
    }

    const codeMatch = remaining.match(/`(.+?)`/);
    if (codeMatch && codeMatch.index != null) {
      candidates.push({ match: codeMatch, type: "code", index: codeMatch.index });
    }

    const linkMatch = remaining.match(/\[([^\]]+)\]\(([^)]+)\)/);
    if (linkMatch && linkMatch.index != null) {
      candidates.push({ match: linkMatch, type: "link", index: linkMatch.index });
    }

    const italicMatch = remaining.match(/(?:^|[^*])\*([^*]+?)\*(?:[^*]|$)/);
    if (italicMatch && italicMatch.index != null) {
      const adjustedIndex = remaining[italicMatch.index] !== "*"
        ? italicMatch.index + 1
        : italicMatch.index;
      candidates.push({ match: italicMatch, type: "italic", index: adjustedIndex });
    }

    if (candidates.length === 0) {
      parts.push(remaining);
      break;
    }

    candidates.sort((a, b) => a.index - b.index);
    const earliest = candidates[0];

    if (earliest.index > 0) {
      parts.push(remaining.slice(0, earliest.index));
    }

    if (earliest.type === "bold") {
      parts.push(
        <strong key={keyIdx++} className="font-semibold text-text-primary">
          {earliest.match[1]}
        </strong>
      );
      remaining = remaining.slice(earliest.index + earliest.match[0].length);
    } else if (earliest.type === "code") {
      parts.push(
        <code
          key={keyIdx++}
          className="px-1.5 py-0.5 rounded bg-white/10 text-xs font-mono text-text-primary"
        >
          {earliest.match[1]}
        </code>
      );
      remaining = remaining.slice(earliest.index + earliest.match[0].length);
    } else if (earliest.type === "link") {
      parts.push(
        <a
          key={keyIdx++}
          href={earliest.match[2]}
          className="text-primary hover:text-primary-hover underline transition-colors duration-200"
          target="_blank"
          rel="noopener noreferrer"
        >
          {earliest.match[1]}
        </a>
      );
      remaining = remaining.slice(earliest.index + earliest.match[0].length);
    } else if (earliest.type === "italic") {
      const italicText = earliest.match[1];
      parts.push(
        <em key={keyIdx++} className="italic">
          {italicText}
        </em>
      );
      remaining = remaining.slice(earliest.index + italicText.length + 2);
    }
  }

  return parts;
}

// ─── Block Renderers ────────────────────────────────────────────

function HeadingBlock({ block }: { block: Extract<MdBlock, { type: "heading" }> }) {
  const Tag = (block.level <= 3 ? `h${block.level}` : "h4") as "h1" | "h2" | "h3" | "h4";
  const sizeClass =
    block.level === 1
      ? "text-2xl font-bold text-text-primary mt-10 mb-4 font-display"
      : block.level === 2
      ? "text-xl font-bold text-text-primary mt-8 mb-3 font-display"
      : block.level === 3
      ? "text-base font-semibold text-text-primary mt-6 mb-2"
      : "text-sm font-semibold text-text-primary mt-4 mb-1.5";

  return (
    <Tag id={block.id} className={cn(sizeClass, "scroll-mt-24")}>
      {renderInline(block.text)}
    </Tag>
  );
}

function BlockquoteBlock({ block }: { block: Extract<MdBlock, { type: "blockquote" }> }) {
  return (
    <blockquote className="border-l-4 border-primary/40 pl-4 py-2 my-4 bg-primary/5 rounded-r-lg">
      {block.lines.map((line, idx) => (
        <p key={idx} className="text-sm text-text-primary italic leading-relaxed">
          {renderInline(line)}
        </p>
      ))}
    </blockquote>
  );
}

function TableBlock({ block }: { block: Extract<MdBlock, { type: "table" }> }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border my-4">
      <table className="w-full text-left" role="table">
        <thead>
          <tr className="bg-white/5 border-b border-border">
            {block.headers.map((h, idx) => (
              <th
                key={idx}
                className="px-3 py-2.5 text-[11px] font-medium text-text-secondary whitespace-nowrap"
                scope="col"
              >
                {renderInline(h)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {block.rows.map((row, rIdx) => (
            <tr
              key={rIdx}
              className={cn(
                "border-b border-border",
                rIdx % 2 === 1 && "bg-white/5"
              )}
            >
              {row.map((cell, cIdx) => (
                <td
                  key={cIdx}
                  className="px-3 py-2 text-xs text-text-primary leading-relaxed"
                >
                  {renderInline(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function UlBlock({ block }: { block: Extract<MdBlock, { type: "ul" }> }) {
  return (
    <ul className="list-disc list-inside space-y-1.5 my-3 pl-2" role="list">
      {block.items.map((item, idx) => (
        <li key={idx} className="text-sm text-text-primary leading-relaxed">
          {renderInline(item)}
        </li>
      ))}
    </ul>
  );
}

function OlBlock({ block }: { block: Extract<MdBlock, { type: "ol" }> }) {
  return (
    <ol className="list-decimal list-inside space-y-1.5 my-3 pl-2" role="list">
      {block.items.map((item, idx) => (
        <li key={idx} className="text-sm text-text-primary leading-relaxed">
          {renderInline(item)}
        </li>
      ))}
    </ol>
  );
}

function CodeBlock({ block }: { block: Extract<MdBlock, { type: "code" }> }) {
  return (
    <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 my-4 overflow-x-auto text-xs font-mono leading-relaxed">
      <code>{block.lines.join("\n")}</code>
    </pre>
  );
}

function ParagraphBlock({ block }: { block: Extract<MdBlock, { type: "paragraph" }> }) {
  return (
    <p className="text-sm text-text-primary leading-relaxed my-3">
      {renderInline(block.text)}
    </p>
  );
}

function renderBlock(block: MdBlock, idx: number) {
  switch (block.type) {
    case "heading":
      return <HeadingBlock key={idx} block={block} />;
    case "blockquote":
      return <BlockquoteBlock key={idx} block={block} />;
    case "table":
      return <TableBlock key={idx} block={block} />;
    case "ul":
      return <UlBlock key={idx} block={block} />;
    case "ol":
      return <OlBlock key={idx} block={block} />;
    case "code":
      return <CodeBlock key={idx} block={block} />;
    case "hr":
      return <hr key={idx} className="my-6 border-t border-border" />;
    case "paragraph":
      return <ParagraphBlock key={idx} block={block} />;
  }
}

// ─── Table of Contents Sidebar ──────────────────────────────────

function TocSidebar({ toc, activeId }: { toc: TocEntry[]; activeId: string }) {
  return (
    <nav
      className="hidden xl:block sticky top-24 max-h-[calc(100vh-8rem)] overflow-y-auto print:hidden"
      aria-label="Table of contents"
    >
      <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-3">
        Contents
      </p>
      <ul className="space-y-1" role="list">
        {toc.map((entry) => (
          <li key={entry.id} role="listitem">
            <a
              href={`#${entry.id}`}
              className={cn(
                "block text-xs leading-relaxed py-1 transition-colors duration-150",
                entry.level === 1 && "font-medium",
                entry.level === 2 && "pl-3",
                entry.level === 3 && "pl-6",
                entry.level === 4 && "pl-9",
                activeId === entry.id
                  ? "text-primary font-medium"
                  : "text-text-secondary hover:text-text-primary"
              )}
              onClick={(e) => {
                e.preventDefault();
                const el = document.getElementById(entry.id);
                if (el) {
                  el.scrollIntoView({ behavior: "smooth", block: "start" });
                }
              }}
            >
              {entry.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

// ─── Metadata Badge ─────────────────────────────────────────────

function MetadataBadge({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof FileText;
  label: string;
  value: string | number;
}) {
  return (
    <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 border border-border">
      <Icon size={12} className="text-text-tertiary flex-shrink-0" aria-hidden="true" />
      <span className="text-[10px] text-text-secondary">{label}:</span>
      <span className="text-[10px] font-medium font-mono text-text-primary">{value}</span>
    </div>
  );
}

// ─── Props ──────────────────────────────────────────────────────

interface SynthesisReportProps {
  report: string | null;
  metadata: Record<string, unknown> | null;
  synthesisName?: string;
}

// ─── Component ──────────────────────────────────────────────────

export default function SynthesisReport({ report, metadata, synthesisName }: SynthesisReportProps) {
  const [activeHeading, setActiveHeading] = useState("");
  const contentRef = useRef<HTMLDivElement>(null);

  // Parse markdown
  const parsed = useMemo(() => {
    if (!report) return { blocks: [], toc: [] };
    return parseMarkdown(report);
  }, [report]);

  // Extract title from first h1 block, falling back to synthesisName
  const reportTitle = useMemo(() => {
    const firstH1 = parsed.blocks.find(
      (b): b is Extract<MdBlock, { type: "heading" }> => b.type === "heading" && b.level === 1
    );
    return firstH1?.text ?? synthesisName ?? "Cross-Screen Synthesis Report";
  }, [parsed.blocks, synthesisName]);

  // Blocks to render (skip the first h1 since we show it in the header card)
  const bodyBlocks = useMemo(() => {
    let skippedFirst = false;
    return parsed.blocks.filter((b) => {
      if (!skippedFirst && b.type === "heading" && b.level === 1) {
        skippedFirst = true;
        return false;
      }
      return true;
    });
  }, [parsed.blocks]);

  // IntersectionObserver for TOC highlighting
  useEffect(() => {
    if (parsed.toc.length === 0 || !contentRef.current) return;

    const headingElements = parsed.toc
      .map((entry) => document.getElementById(entry.id))
      .filter(Boolean) as HTMLElement[];

    if (headingElements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntries = entries
          .filter((e) => e.isIntersecting)
          .sort(
            (a, b) =>
              (a.target as HTMLElement).offsetTop -
              (b.target as HTMLElement).offsetTop
          );

        if (visibleEntries.length > 0) {
          setActiveHeading(visibleEntries[0].target.id);
        }
      },
      {
        rootMargin: "-80px 0px -70% 0px",
        threshold: 0.1,
      }
    );

    headingElements.forEach((el) => observer.observe(el));

    return () => {
      headingElements.forEach((el) => observer.unobserve(el));
    };
  }, [parsed.toc]);

  // Print handler
  const handlePrint = useCallback(() => {
    window.print();
  }, []);

  // ─── Empty State ──────────────────────────────────────────────

  if (!report) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-12 text-center">
        <div className="w-14 h-14 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-4">
          <FileText size={24} className="text-text-tertiary" />
        </div>
        <h2 className="text-base font-semibold text-text-primary mb-1">
          Report Not Yet Generated
        </h2>
        <p className="text-sm text-text-secondary max-w-sm mx-auto">
          The synthesis report will be available here once all synthesis
          phases complete and the final report is generated.
        </p>
      </div>
    );
  }

  // ─── Metadata ─────────────────────────────────────────────────

  const meta = (metadata ?? {}) as Record<string, unknown>;
  const tierBreakdown = (
    meta.tierBreakdown && typeof meta.tierBreakdown === "object"
      ? meta.tierBreakdown
      : {}
  ) as Record<string, number>;

  const equityCount = meta.equityCount as number | undefined;
  const tier1 = tierBreakdown.tier1 ?? 0;
  const tier2 = tierBreakdown.tier2 ?? 0;
  const tier3 = tierBreakdown.tier3 ?? 0;
  const tierChangeCount = meta.tierChangeCount as number | undefined;

  // Word count from the raw markdown
  const wordCount = report.split(/\s+/).filter(Boolean).length;

  // ─── Render ───────────────────────────────────────────────────

  return (
    <div className="animate-fade-in">
      {/* Report Header Card */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h1 className="font-display text-2xl font-bold text-text-primary leading-tight">
              {reportTitle}
            </h1>
            <p className="text-xs text-text-secondary mt-2">
              Cross-screen synthesis report
            </p>
          </div>
          <button
            onClick={handlePrint}
            className={cn(
              "inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium",
              "bg-white/5 text-text-primary border border-border",
              "hover:bg-white/10 transition-colors duration-200",
              "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
              "print:hidden flex-shrink-0"
            )}
            aria-label="Print report"
          >
            <Printer size={16} />
            Print
          </button>
        </div>

        {/* Metadata badges */}
        <div className="flex flex-wrap gap-2 mt-4">
          {equityCount != null && (
            <MetadataBadge icon={BarChart3} label="Equities" value={equityCount} />
          )}
          {tier1 > 0 && <MetadataBadge icon={Trophy} label="Tier 1" value={tier1} />}
          {tier2 > 0 && <MetadataBadge icon={Users} label="Tier 2" value={tier2} />}
          {tier3 > 0 && <MetadataBadge icon={Hash} label="Tier 3" value={tier3} />}
          {tierChangeCount != null && tierChangeCount > 0 && (
            <MetadataBadge icon={TrendingUp} label="Tier Changes" value={tierChangeCount} />
          )}
          <MetadataBadge icon={Layers} label="Words" value={wordCount.toLocaleString()} />
        </div>
      </div>

      {/* Report Body with TOC sidebar */}
      <div className="flex gap-8">
        {/* TOC Sidebar - sticky on desktop */}
        {parsed.toc.length > 0 && (
          <div className="w-56 flex-shrink-0">
            <TocSidebar toc={parsed.toc} activeId={activeHeading} />
          </div>
        )}

        {/* Report Content */}
        <div
          ref={contentRef}
          className={cn(
            "flex-1 min-w-0 bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-8 py-6",
            "print:shadow-none print:border-0 print:px-0"
          )}
        >
          <article className="max-w-none">
            {bodyBlocks.map((block, idx) => renderBlock(block, idx))}
          </article>
        </div>
      </div>

      {/* Print styles */}
      <style jsx global>{`
        @media print {
          body * {
            visibility: hidden;
          }
          .print-area,
          .print-area * {
            visibility: visible;
          }
          nav[aria-label="Table of contents"] {
            display: none !important;
          }
          @page {
            margin: 1.5cm;
          }
        }
      `}</style>
    </div>
  );
}
