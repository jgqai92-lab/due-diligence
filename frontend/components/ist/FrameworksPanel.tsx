"use client";

import {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
} from "react";
import { cn } from "@/lib/utils";
import { getFrameworks, getFrameworkDetail } from "@/lib/api/ist";
import type { FrameworkSummary, FrameworkDetail } from "@/types/ist";
import {
  BookOpen,
  X,
  AlertCircle,
  ChevronRight,
  ArrowLeft,
} from "lucide-react";

// ─── Category Badge Colors ────────────────────────────────────────

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  scoring: { bg: "bg-violet-500/10", text: "text-violet-400" },
  analysis: { bg: "bg-sky-500/10", text: "text-sky-400" },
  screening: { bg: "bg-amber-500/10", text: "text-amber-400" },
  validation: { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  risk: { bg: "bg-rose-500/10", text: "text-rose-400" },
  strategy: { bg: "bg-indigo-500/10", text: "text-indigo-400" },
};

function getCategoryColors(category: string): { bg: string; text: string } {
  const key = category.toLowerCase();
  return CATEGORY_COLORS[key] ?? { bg: "bg-white/10", text: "text-text-secondary" };
}

// ─── Simple Markdown Renderer (adapted from InvestmentThesisReport) ──

type MdBlock =
  | { type: "heading"; level: 1 | 2 | 3; text: string }
  | { type: "blockquote"; lines: string[] }
  | { type: "table"; headers: string[]; rows: string[][] }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "code"; language: string; lines: string[] }
  | { type: "hr" }
  | { type: "paragraph"; text: string };

function parseMarkdownBlocks(raw: string): MdBlock[] {
  const lines = raw.split("\n");
  const blocks: MdBlock[] = [];
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
      i++; // skip closing ```
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
    const headingMatch = line.match(/^(#{1,3})\s+(.+)/);
    if (headingMatch) {
      const level = headingMatch[1].length as 1 | 2 | 3;
      const text = headingMatch[2].trim();
      blocks.push({ type: "heading", level, text });
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
      while (
        i < lines.length &&
        lines[i].includes("|") &&
        lines[i].trim().length > 0
      ) {
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
      !(
        lines[i].includes("|") &&
        i + 1 < lines.length &&
        /^[\s|:-]+$/.test(lines[i + 1] ?? "")
      ) &&
      !/^(-{3,}|\*{3,}|_{3,})\s*$/.test(lines[i].trim())
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    if (paraLines.length > 0) {
      blocks.push({ type: "paragraph", text: paraLines.join(" ") });
    }
  }

  return blocks;
}

function renderInlineText(text: string): React.ReactNode[] {
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
      const adjustedIndex =
        remaining[italicMatch.index] !== "*"
          ? italicMatch.index + 1
          : italicMatch.index;
      candidates.push({
        match: italicMatch,
        type: "italic",
        index: adjustedIndex,
      });
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

function renderMdBlock(block: MdBlock, idx: number) {
  switch (block.type) {
    case "heading": {
      const Tag = `h${block.level}` as "h1" | "h2" | "h3";
      const sizeClass =
        block.level === 1
          ? "text-lg font-bold text-text-primary mt-6 mb-3 font-display"
          : block.level === 2
          ? "text-base font-bold text-text-primary mt-5 mb-2 font-display"
          : "text-sm font-semibold text-text-primary mt-4 mb-1.5";
      return (
        <Tag key={idx} className={sizeClass}>
          {renderInlineText(block.text)}
        </Tag>
      );
    }
    case "blockquote":
      return (
        <blockquote
          key={idx}
          className="border-l-4 border-primary/40 pl-3 py-1.5 my-3 bg-primary/5 rounded-r-lg"
        >
          {block.lines.map((line, li) => (
            <p
              key={li}
              className="text-xs text-text-primary italic leading-relaxed"
            >
              {renderInlineText(line)}
            </p>
          ))}
        </blockquote>
      );
    case "table":
      return (
        <div
          key={idx}
          className="overflow-x-auto rounded-lg border border-border my-3"
        >
          <table className="w-full text-left" role="table">
            <thead>
              <tr className="bg-white/5 border-b border-border">
                {block.headers.map((h, hi) => (
                  <th
                    key={hi}
                    className="px-2.5 py-2 text-[10px] font-medium text-text-secondary whitespace-nowrap"
                    scope="col"
                  >
                    {renderInlineText(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, ri) => (
                <tr
                  key={ri}
                  className={cn(
                    "border-b border-border",
                    ri % 2 === 1 && "bg-white/5"
                  )}
                >
                  {row.map((cell, ci) => (
                    <td
                      key={ci}
                      className="px-2.5 py-1.5 text-[11px] text-text-primary leading-relaxed"
                    >
                      {renderInlineText(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    case "ul":
      return (
        <ul
          key={idx}
          className="list-disc list-inside space-y-1 my-2 pl-1"
          role="list"
        >
          {block.items.map((item, ii) => (
            <li
              key={ii}
              className="text-xs text-text-primary leading-relaxed"
            >
              {renderInlineText(item)}
            </li>
          ))}
        </ul>
      );
    case "ol":
      return (
        <ol
          key={idx}
          className="list-decimal list-inside space-y-1 my-2 pl-1"
          role="list"
        >
          {block.items.map((item, ii) => (
            <li
              key={ii}
              className="text-xs text-text-primary leading-relaxed"
            >
              {renderInlineText(item)}
            </li>
          ))}
        </ol>
      );
    case "code":
      return (
        <pre
          key={idx}
          className="bg-gray-900 text-gray-100 rounded-lg p-3 my-3 overflow-x-auto text-[11px] font-mono leading-relaxed"
        >
          <code>{block.lines.join("\n")}</code>
        </pre>
      );
    case "hr":
      return <hr key={idx} className="my-4 border-t border-border" />;
    case "paragraph":
      return (
        <p key={idx} className="text-xs text-text-primary leading-relaxed my-2">
          {renderInlineText(block.text)}
        </p>
      );
  }
}

// ─── Scoring Schema Card ──────────────────────────────────────────

function ScoringSchemaCard({
  schema,
}: {
  schema: NonNullable<FrameworkDetail["scoringSchema"]>;
}) {
  return (
    <div className="bg-white/5 rounded-lg border border-border p-3 my-3">
      <p className="text-[10px] font-medium text-text-secondary uppercase tracking-wider mb-2">
        Scoring Schema
      </p>
      <div className="grid grid-cols-2 gap-2 mb-2">
        <div>
          <p className="text-[10px] text-text-tertiary">Scale</p>
          <p className="text-xs font-mono font-medium text-text-primary">
            {schema.scale.min} - {schema.scale.max}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-text-tertiary">Tier Thresholds</p>
          <p className="text-xs font-mono font-medium text-text-primary">
            T1: {schema.tierThresholds.tier1} | T2: {schema.tierThresholds.tier2}
          </p>
        </div>
      </div>
      <div>
        <p className="text-[10px] text-text-tertiary mb-1">Dimensions</p>
        <div className="flex flex-wrap gap-1">
          {schema.dimensions.map((dim) => (
            <span
              key={dim}
              className="inline-flex items-center px-2 py-0.5 rounded-full bg-white/5 border border-border text-[10px] text-text-secondary"
            >
              {dim}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Framework List Item ──────────────────────────────────────────

function FrameworkListItem({
  framework,
  onSelect,
}: {
  framework: FrameworkSummary;
  onSelect: (name: string) => void;
}) {
  const catColors = getCategoryColors(framework.category);

  return (
    <button
      onClick={() => onSelect(framework.name)}
      className={cn(
        "w-full text-left px-4 py-3 rounded-lg border border-border bg-white/5",
        "hover:border-primary/30 hover:bg-white/5 transition-all duration-200",
        "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1",
        "group"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text-primary group-hover:text-primary transition-colors duration-200">
            {framework.displayName}
          </p>
          <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">
            {framework.description}
          </p>
        </div>
        <ChevronRight
          size={16}
          className="text-text-tertiary group-hover:text-primary flex-shrink-0 mt-0.5 transition-colors duration-200"
          aria-hidden="true"
        />
      </div>
      <span
        className={cn(
          "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium mt-2",
          catColors.bg,
          catColors.text
        )}
      >
        {framework.category}
      </span>
    </button>
  );
}

// ─── Content Skeleton ─────────────────────────────────────────────

function ContentSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-5 w-3/4 bg-white/10 rounded" />
      <div className="h-3 w-full bg-white/10 rounded" />
      <div className="h-3 w-full bg-white/10 rounded" />
      <div className="h-3 w-5/6 bg-white/10 rounded" />
      <div className="h-4 w-1/2 bg-white/10 rounded mt-4" />
      <div className="h-3 w-full bg-white/10 rounded" />
      <div className="h-3 w-full bg-white/10 rounded" />
      <div className="h-3 w-4/5 bg-white/10 rounded" />
      <div className="h-4 w-2/3 bg-white/10 rounded mt-4" />
      <div className="h-3 w-full bg-white/10 rounded" />
      <div className="h-3 w-3/4 bg-white/10 rounded" />
    </div>
  );
}

// ─── List Skeleton ────────────────────────────────────────────────

function ListSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="rounded-lg border border-border p-4 space-y-2"
        >
          <div className="h-4 w-2/3 bg-white/10 rounded" />
          <div className="h-3 w-full bg-white/10 rounded" />
          <div className="h-5 w-16 bg-white/10 rounded-full" />
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────

export default function FrameworksPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [frameworks, setFrameworks] = useState<FrameworkSummary[]>([]);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [detail, setDetail] = useState<FrameworkDetail | null>(null);
  const [listLoading, setListLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const triggerButtonRef = useRef<HTMLButtonElement>(null);

  // Fetch frameworks list when panel opens
  const fetchList = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      const result = await getFrameworks();
      setFrameworks(result.frameworks);
    } catch (err) {
      setListError(
        err instanceof Error ? err.message : "Failed to load frameworks"
      );
    } finally {
      setListLoading(false);
    }
  }, []);

  // Fetch individual framework detail
  const fetchDetail = useCallback(async (name: string) => {
    setDetailLoading(true);
    setDetailError(null);
    try {
      const result = await getFrameworkDetail(name);
      setDetail(result);
    } catch (err) {
      setDetailError(
        err instanceof Error ? err.message : "Failed to load framework"
      );
    } finally {
      setDetailLoading(false);
    }
  }, []);

  // Open panel
  const openPanel = useCallback(() => {
    setIsOpen(true);
    if (frameworks.length === 0) {
      fetchList();
    }
  }, [frameworks.length, fetchList]);

  // Close panel
  const closePanel = useCallback(() => {
    setIsOpen(false);
    setSelectedName(null);
    setDetail(null);
    setDetailError(null);
    // Return focus to trigger button
    triggerButtonRef.current?.focus();
  }, []);

  // Select a framework
  const selectFramework = useCallback(
    (name: string) => {
      setSelectedName(name);
      fetchDetail(name);
    },
    [fetchDetail]
  );

  // Go back to list
  const goBack = useCallback(() => {
    setSelectedName(null);
    setDetail(null);
    setDetailError(null);
  }, []);

  // Focus trap: move focus to close button when panel opens
  useEffect(() => {
    if (isOpen) {
      // Small delay to allow the transition to start, then focus the close button
      const timer = setTimeout(() => {
        closeButtonRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // Escape key to close
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        closePanel();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, closePanel]);

  // Focus trap: keep focus within the panel when open
  useEffect(() => {
    if (!isOpen || !panelRef.current) return;

    const handleFocusTrap = (e: globalThis.KeyboardEvent) => {
      if (e.key !== "Tab" || !panelRef.current) return;

      const focusableElements = panelRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );

      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    document.addEventListener("keydown", handleFocusTrap);
    return () => document.removeEventListener("keydown", handleFocusTrap);
  }, [isOpen]);

  // Prevent body scroll when panel is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // Parse detail content into markdown blocks
  const mdBlocks = useMemo(() => {
    if (!detail?.content) return [];
    return parseMarkdownBlocks(detail.content);
  }, [detail]);

  // Selected framework summary (for the header)
  const selectedSummary = useMemo(() => {
    if (!selectedName) return null;
    return frameworks.find((f) => f.name === selectedName) ?? null;
  }, [selectedName, frameworks]);

  return (
    <>
      {/* Floating trigger button */}
      <button
        ref={triggerButtonRef}
        onClick={openPanel}
        className={cn(
          "fixed bottom-6 right-6 z-40",
          "inline-flex items-center gap-2 px-4 py-3 rounded-full",
          "bg-primary text-white font-medium text-sm",
          "shadow-lg hover:border-border/80 hover:bg-primary-hover",
          "transition-all duration-200",
          "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
          "print:hidden"
        )}
        aria-label="Open IST Frameworks reference panel"
      >
        <BookOpen size={18} aria-hidden="true" />
        <span className="hidden sm:inline">Frameworks</span>
      </button>

      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 z-50 bg-black/30 backdrop-blur-sm",
          "transition-opacity duration-300",
          isOpen
            ? "opacity-100 pointer-events-auto"
            : "opacity-0 pointer-events-none"
        )}
        onClick={closePanel}
        aria-hidden="true"
      />

      {/* Slide-out panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="IST Frameworks Reference"
        className={cn(
          "fixed top-0 right-0 z-50 h-full",
          "w-full sm:w-[400px]",
          "bg-[rgba(10,15,26,0.9)] backdrop-blur-[12px] border border-border shadow-xl",
          "flex flex-col",
          "transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        {/* Panel Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border flex-shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            {selectedName && (
              <button
                onClick={goBack}
                className={cn(
                  "p-1 rounded-md",
                  "text-text-tertiary hover:text-text-primary hover:bg-white/10",
                  "transition-colors duration-200",
                  "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1"
                )}
                aria-label="Back to frameworks list"
              >
                <ArrowLeft size={18} />
              </button>
            )}
            <div className="min-w-0">
              <h2 className="font-display text-base font-bold text-text-primary truncate">
                {selectedName && selectedSummary
                  ? selectedSummary.displayName
                  : "IST Frameworks"}
              </h2>
              {selectedName && selectedSummary && (
                <span
                  className={cn(
                    "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium mt-0.5",
                    getCategoryColors(selectedSummary.category).bg,
                    getCategoryColors(selectedSummary.category).text
                  )}
                >
                  {selectedSummary.category}
                </span>
              )}
            </div>
          </div>
          <button
            ref={closeButtonRef}
            onClick={closePanel}
            className={cn(
              "p-2 rounded-lg",
              "text-text-tertiary hover:text-text-primary hover:bg-white/10",
              "transition-colors duration-200",
              "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1",
              "flex-shrink-0"
            )}
            aria-label="Close frameworks panel"
          >
            <X size={20} />
          </button>
        </div>

        {/* Panel Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {!selectedName ? (
            // ─── Framework List View ─────────────────────────
            <>
              {listLoading && <ListSkeleton />}

              {listError && (
                <div className="text-center py-8">
                  <AlertCircle
                    size={24}
                    className="mx-auto text-red-400 mb-2"
                  />
                  <p className="text-sm text-red-400">{listError}</p>
                  <button
                    onClick={fetchList}
                    className="mt-3 text-xs font-medium text-primary hover:text-primary-hover transition-colors duration-200"
                  >
                    Try again
                  </button>
                </div>
              )}

              {!listLoading && !listError && frameworks.length === 0 && (
                <div className="text-center py-8">
                  <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
                    <BookOpen size={20} className="text-text-tertiary" />
                  </div>
                  <p className="text-sm text-text-secondary">
                    No frameworks available
                  </p>
                </div>
              )}

              {!listLoading && !listError && frameworks.length > 0 && (
                <div className="space-y-2">
                  <p className="text-[10px] font-medium text-text-tertiary uppercase tracking-wider mb-3">
                    {frameworks.length} Analytical Frameworks
                  </p>
                  {frameworks.map((fw) => (
                    <FrameworkListItem
                      key={fw.name}
                      framework={fw}
                      onSelect={selectFramework}
                    />
                  ))}
                </div>
              )}
            </>
          ) : (
            // ─── Framework Detail View ───────────────────────
            <>
              {detailLoading && <ContentSkeleton />}

              {detailError && (
                <div className="text-center py-8">
                  <AlertCircle
                    size={24}
                    className="mx-auto text-red-400 mb-2"
                  />
                  <p className="text-sm text-red-400">{detailError}</p>
                  <button
                    onClick={() => fetchDetail(selectedName)}
                    className="mt-3 text-xs font-medium text-primary hover:text-primary-hover transition-colors duration-200"
                  >
                    Try again
                  </button>
                </div>
              )}

              {!detailLoading && !detailError && detail && (
                <div>
                  {/* Scoring Schema (if present) */}
                  {detail.scoringSchema && (
                    <ScoringSchemaCard schema={detail.scoringSchema} />
                  )}

                  {/* Markdown Content */}
                  <article className="max-w-none">
                    {mdBlocks.map((block, idx) => renderMdBlock(block, idx))}
                  </article>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
