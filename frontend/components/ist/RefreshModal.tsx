"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import type { ContentType } from "@/types/ist";

interface RefreshModalSubmitPayload {
  content: string;
  contentType: ContentType;
  autoAdvance: boolean;
}

interface RefreshModalProps {
  open: boolean;
  loading?: boolean;
  defaultContentType: ContentType;
  refreshCount: number;
  error?: string | null;
  onClose: () => void;
  onSubmit: (payload: RefreshModalSubmitPayload) => Promise<void> | void;
}

const CONTENT_TYPE_OPTIONS: Array<{ value: ContentType; label: string }> = [
  { value: "podcast_transcript", label: "Podcast Transcript" },
  { value: "article", label: "Article" },
  { value: "earnings_call", label: "Earnings Call" },
  { value: "research_note", label: "Research Note" },
  { value: "text", label: "Text" },
];

export default function RefreshModal({
  open,
  loading = false,
  defaultContentType,
  refreshCount,
  error = null,
  onClose,
  onSubmit,
}: RefreshModalProps) {
  const [content, setContent] = useState("");
  const [contentType, setContentType] = useState<ContentType>(defaultContentType);
  const [autoAdvance, setAutoAdvance] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setContent("");
    setContentType(defaultContentType);
    setAutoAdvance(false);
    setLocalError(null);
  }, [open, defaultContentType]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !loading) {
        onClose();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, loading, onClose]);

  const trimmedContent = content.trim();
  const canSubmit = trimmedContent.length >= 100 && !loading;
  const charsRemaining = useMemo(() => Math.max(0, 100 - trimmedContent.length), [trimmedContent.length]);

  async function handleSubmit() {
    if (!canSubmit) {
      setLocalError("Refresh content must be at least 100 characters.");
      return;
    }
    setLocalError(null);
    await onSubmit({
      content: trimmedContent,
      contentType,
      autoAdvance,
    });
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={loading ? undefined : onClose} />
      <div className="relative w-full max-w-2xl mx-4 bg-[rgba(10,15,26,0.95)] backdrop-blur-[16px] border border-border rounded-xl shadow-2xl">
        <div className="px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold text-text-primary">Refresh Screen</h2>
          <p className="text-sm text-text-secondary mt-1">
            Add new source content and re-run only impacted analysis steps.
          </p>
        </div>

        <div className="px-6 py-5 space-y-4">
          {refreshCount >= 3 && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
              <p className="text-xs text-amber-300 inline-flex items-start gap-2">
                <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
                This screen has been refreshed 3+ times. Consider creating a fresh screen.
              </p>
            </div>
          )}

          {(localError || error) && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3">
              <p className="text-xs text-red-300">{localError ?? error}</p>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-text-secondary">Content Type</label>
            <select
              value={contentType}
              onChange={(event) => setContentType(event.target.value as ContentType)}
              disabled={loading}
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-[rgba(10,15,26,0.8)] text-text-primary"
            >
              {CONTENT_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-text-secondary">New Content</label>
            <textarea
              value={content}
              onChange={(event) => setContent(event.target.value)}
              disabled={loading}
              rows={10}
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-[rgba(10,15,26,0.8)] text-text-primary resize-y"
              placeholder="Paste new transcript or notes here..."
            />
            <p className="text-[11px] text-text-tertiary">
              {trimmedContent.length} characters
              {charsRemaining > 0 && ` - ${charsRemaining} more required`}
            </p>
          </div>

          <label className="inline-flex items-center gap-2 text-sm text-text-secondary">
            <input
              type="checkbox"
              checked={autoAdvance}
              onChange={(event) => setAutoAdvance(event.target.checked)}
              disabled={loading}
            />
            Auto-advance refresh workflow
          </label>
        </div>

        <div className="px-6 py-4 border-t border-border flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary rounded-lg hover:bg-white/5 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-[#050810] disabled:bg-white/10 disabled:text-text-tertiary"
          >
            {loading && <Loader2 size={14} className="animate-spin" />}
            Start Refresh
          </button>
        </div>
      </div>
    </div>
  );
}
