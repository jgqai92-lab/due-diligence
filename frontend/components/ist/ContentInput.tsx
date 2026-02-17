"use client";

import { cn } from "@/lib/utils";

// ─── Content Type Placeholders ──────────────────────────────────────

const PLACEHOLDER_MAP: Record<string, string> = {
  podcast_transcript:
    "Paste your podcast transcript here...\n\nInclude the full transcript text. The system will extract investable claims, quantitative anchors, and temporal markers.",
  article:
    "Paste the article text here...\n\nInclude the full article content. The system will extract investable claims and thematic patterns.",
  earnings_call:
    "Paste the earnings call transcript here...\n\nInclude management commentary and Q&A. The system will extract forward-looking statements and quantitative guidance.",
  research_note:
    "Paste the research note here...\n\nInclude the analyst's thesis, key data points, and recommendations.",
  text:
    "Paste your content here...\n\nPodcast transcripts, articles, earnings call transcripts, or any text-based content.\n\nMinimum 100 characters.",
};

// ─── Props ──────────────────────────────────────────────────────────

interface ContentInputProps {
  value: string;
  onChange: (value: string) => void;
  contentType?: string;
  minLength?: number;
  maxLength?: number;
  disabled?: boolean;
}

// ─── Component ──────────────────────────────────────────────────────

export default function ContentInput({
  value,
  onChange,
  contentType = "text",
  minLength = 100,
  maxLength,
  disabled = false,
}: ContentInputProps) {
  const charCount = value.length;
  const isBelowMin = charCount > 0 && charCount < minLength;
  const isAtMax = maxLength != null && charCount >= maxLength;
  const placeholder = PLACEHOLDER_MAP[contentType] || PLACEHOLDER_MAP.text;

  return (
    <div className="space-y-1.5">
      <textarea
        value={value}
        onChange={(e) => {
          const newValue = maxLength
            ? e.target.value.slice(0, maxLength)
            : e.target.value;
          onChange(newValue);
        }}
        placeholder={placeholder}
        disabled={disabled}
        rows={12}
        className={cn(
          "w-full min-h-[300px] px-4 py-3 text-sm text-text-primary bg-[rgba(10,15,26,0.6)]",
          "border border-border rounded-lg resize-y transition-colors duration-200",
          "placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-offset-[#050810]",
          disabled && "bg-white/5 text-text-secondary cursor-not-allowed",
          isBelowMin
            ? "border-red-500/30 focus:ring-red-500 focus:border-red-500"
            : "border-border focus:ring-primary focus:border-primary"
        )}
        aria-label="Content input"
        aria-describedby="content-char-count"
        aria-invalid={isBelowMin ? "true" : undefined}
      />
      <div
        id="content-char-count"
        className="flex items-center justify-between text-xs"
      >
        <div>
          {isBelowMin && (
            <span className="text-red-400">
              Minimum {minLength} characters required ({minLength - charCount} more needed)
            </span>
          )}
        </div>
        <span
          className={cn(
            "font-mono",
            isAtMax ? "text-red-400" : "text-text-secondary"
          )}
        >
          {charCount.toLocaleString()}
          {maxLength != null && ` / ${maxLength.toLocaleString()}`}
          {" characters"}
        </span>
      </div>
    </div>
  );
}
