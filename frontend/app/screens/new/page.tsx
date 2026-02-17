"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { createScreen } from "@/lib/api/ist";
import { advanceWorkflow } from "@/lib/api/workflows";
import ContentInput from "@/components/ist/ContentInput";
import ConfirmDialog from "@/components/ConfirmDialog";
import ContentQualityIndicator from "@/components/ist/ContentQualityIndicator";
import GateCriteriaPanel from "@/components/ist/GateCriteriaPanel";
import ContentTemplateSelector from "@/components/ist/ContentTemplateSelector";
import { useContentQuality } from "@/hooks/useContentQuality";
import { buildWarningMessage } from "@/lib/ist/quality-checks";
import type { ContentType } from "@/lib/ist/quality-checks";
import { ArrowLeft, Loader2, AlertCircle } from "lucide-react";

// ─── Content Type Options ───────────────────────────────────────────

const CONTENT_TYPE_OPTIONS = [
  { value: "podcast_transcript", label: "Podcast Transcript" },
  { value: "article", label: "Article" },
  { value: "earnings_call", label: "Earnings Call" },
  { value: "research_note", label: "Research Note" },
  { value: "text", label: "General Text" },
] as const;

// ─── Page ───────────────────────────────────────────────────────────

export default function NewScreenPage() {
  const router = useRouter();

  // Form state
  const [name, setName] = useState("");
  const [contentType, setContentType] = useState("podcast_transcript");
  const [hypothesis, setHypothesis] = useState("");
  const [content, setContent] = useState("");
  const [autoAdvance, setAutoAdvance] = useState(false);

  // Submission state
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Quality pre-screen state
  const [showSubmitWarning, setShowSubmitWarning] = useState(false);
  const [showTemplateConfirm, setShowTemplateConfirm] = useState(false);
  const [pendingTemplate, setPendingTemplate] = useState("");

  // Quality hook
  const quality = useContentQuality(content);

  // Validation
  const nameError = name.length > 200 ? "Name must be 200 characters or fewer" : null;
  const contentTooShort = content.length > 0 && content.length < 100;
  const isValid =
    name.trim().length > 0 &&
    !nameError &&
    content.length >= 100;

  // Template handling
  const handleLoadTemplate = useCallback((template: string) => {
    if (content.trim()) {
      setPendingTemplate(template);
      setShowTemplateConfirm(true);
    } else {
      setContent(template);
    }
  }, [content]);

  const confirmLoadTemplate = useCallback(() => {
    setContent(pendingTemplate);
    setShowTemplateConfirm(false);
    setPendingTemplate("");
  }, [pendingTemplate]);

  // Submit logic
  const executeSubmit = useCallback(async () => {
    if (!isValid || submitting) return;

    setSubmitting(true);
    setError(null);

    try {
      const result = await createScreen({
        name: name.trim(),
        content,
        contentType,
        hypothesis: hypothesis.trim() || undefined,
        autoAdvance,
      });
      await advanceWorkflow(result.workflowRunId);
      router.push(`/screens/${result.id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create screen"
      );
      setSubmitting(false);
    }
  }, [name, content, contentType, hypothesis, autoAdvance, isValid, submitting, router]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!isValid || submitting) return;

      if (!quality.overallReady) {
        setShowSubmitWarning(true);
        return;
      }

      executeSubmit();
    },
    [isValid, submitting, quality.overallReady, executeSubmit]
  );

  return (
    <div className="max-w-5xl mx-auto animate-fade-in">
      <div className="flex gap-8">
        {/* Left column — Form */}
        <div className="flex-1 min-w-0 space-y-6">
          {/* Back link */}
          <Link
            href="/screens"
            className="inline-flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors duration-200"
          >
            <ArrowLeft size={16} />
            Back to Screens
          </Link>

          {/* Page header */}
          <div>
            <h1 className="font-display text-2xl font-bold text-text-primary">
              Create New Screen
            </h1>
            <p className="text-sm text-text-secondary mt-0.5">
              Paste content to extract investable claims and identify equity candidates.
            </p>
          </div>

          {/* Error banner */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-5 py-4 flex items-start gap-3">
              <AlertCircle size={18} className="text-red-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-red-300">
                  Failed to create screen
                </p>
                <p className="text-xs text-red-400 mt-0.5">{error}</p>
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Screen Name */}
            <div>
              <label
                htmlFor="screen-name"
                className="block text-sm font-medium text-text-secondary mb-1.5"
              >
                Screen Name <span className="text-red-500">*</span>
              </label>
              <input
                id="screen-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., AI Data Center Scarcity Screen"
                maxLength={200}
                required
                disabled={submitting}
                className={cn(
                  "w-full px-4 py-2.5 text-sm text-text-primary bg-[rgba(10,15,26,0.6)] border rounded-lg",
                  "placeholder:text-text-tertiary transition-colors duration-200",
                  "focus:outline-none focus:ring-1 focus:ring-primary/30",
                  submitting && "bg-white/5 cursor-not-allowed",
                  nameError
                    ? "border-red-500/50 focus:border-red-500"
                    : "border-border focus:border-primary"
                )}
                aria-invalid={nameError ? "true" : undefined}
                aria-describedby={nameError ? "name-error" : undefined}
              />
              {nameError && (
                <p id="name-error" className="mt-1 text-xs text-red-400">
                  {nameError}
                </p>
              )}
              <p className="mt-1 text-xs text-text-tertiary">
                {name.length}/200 characters
              </p>
            </div>

            {/* Content Type */}
            <div>
              <label
                htmlFor="content-type"
                className="block text-sm font-medium text-text-secondary mb-1.5"
              >
                Content Type
              </label>
              <select
                id="content-type"
                value={contentType}
                onChange={(e) => setContentType(e.target.value)}
                disabled={submitting}
                className={cn(
                  "w-full px-4 py-2.5 text-sm text-text-primary bg-[rgba(10,15,26,0.6)] border border-border rounded-lg",
                  "focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary",
                  "transition-colors duration-200",
                  submitting && "bg-white/5 cursor-not-allowed"
                )}
              >
                {CONTENT_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value} className="bg-[#111827] text-[#f0f4ff]">
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Template Selector */}
            <ContentTemplateSelector
              contentType={contentType as ContentType}
              hasContent={content.trim().length > 0}
              onLoadTemplate={handleLoadTemplate}
            />

            {/* Content */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                Content <span className="text-red-500">*</span>
              </label>
              <ContentInput
                value={content}
                onChange={setContent}
                contentType={contentType}
                minLength={100}
                disabled={submitting}
              />
            </div>

            {/* Quality Indicator */}
            {content.length > 0 && (
              <ContentQualityIndicator quality={quality} />
            )}

            {/* Hypothesis (optional) */}
            <div>
              <label
                htmlFor="hypothesis"
                className="block text-sm font-medium text-text-secondary mb-1.5"
              >
                Hypothesis{" "}
                <span className="text-text-tertiary font-normal">(optional)</span>
              </label>
              <textarea
                id="hypothesis"
                value={hypothesis}
                onChange={(e) => setHypothesis(e.target.value)}
                rows={3}
                disabled={submitting}
                placeholder="e.g., AI infrastructure buildout creates multi-year bottleneck in power and cooling capacity, benefiting companies positioned across the supply chain..."
                className={cn(
                  "w-full px-4 py-2.5 text-sm text-text-primary bg-[rgba(10,15,26,0.6)] border border-border rounded-lg",
                  "placeholder:text-text-tertiary transition-colors duration-200 resize-y",
                  "focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary",
                  submitting && "bg-white/5 cursor-not-allowed"
                )}
              />
            </div>

            {/* Auto-Advance Toggle */}
            <div className="flex items-center justify-between px-3 py-3 bg-white/5 rounded-lg border border-border">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary">Auto-Advance Phases</p>
                <p className="text-xs text-text-secondary mt-0.5">
                  Automatically proceed through all phases without manual approval. Quality gates still enforce standards.
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={autoAdvance}
                aria-label={autoAdvance ? "Auto-advance is on" : "Auto-advance is off"}
                onClick={() => setAutoAdvance(!autoAdvance)}
                disabled={submitting}
                className={cn(
                  "relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ml-3",
                  "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
                  autoAdvance ? "bg-primary" : "bg-white/20",
                  submitting && "opacity-50 cursor-not-allowed"
                )}
              >
                <span
                  className={cn(
                    "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
                    autoAdvance ? "translate-x-4" : "translate-x-0"
                  )}
                />
              </button>
            </div>

            {/* Action buttons */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <Link
                href="/screens"
                className={cn(
                  "inline-flex items-center px-5 py-2.5 text-sm font-medium text-text-secondary bg-white/5 border border-border rounded-lg",
                  "hover:bg-white/10 hover:text-text-primary transition-colors duration-200",
                  "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
                  submitting && "pointer-events-none opacity-50"
                )}
              >
                Cancel
              </Link>
              <button
                type="submit"
                disabled={!isValid || submitting}
                className={cn(
                  "inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-[#050810] rounded-lg shadow-sm",
                  "transition-colors duration-200",
                  "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
                  isValid && !submitting
                    ? "bg-primary hover:bg-primary-hover active:bg-primary-active"
                    : "bg-white/10 text-text-tertiary cursor-not-allowed"
                )}
              >
                {submitting && (
                  <Loader2 size={16} className="animate-spin" />
                )}
                {submitting ? "Creating..." : "Create Screen"}
              </button>
            </div>
          </form>
        </div>

        {/* Right column — Gate Criteria (desktop) */}
        <div className="hidden lg:block w-[340px] flex-shrink-0 pt-16">
          <GateCriteriaPanel
            contentType={contentType as ContentType}
            quality={quality}
            className="sticky top-6"
          />
        </div>
      </div>

      {/* Mobile: collapsible criteria panel */}
      <details className="lg:hidden mt-4 bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl">
        <summary className="px-4 py-3 text-sm font-medium text-text-secondary cursor-pointer hover:text-text-primary transition-colors">
          Pipeline Gate Criteria
        </summary>
        <div className="px-4 pb-4">
          <GateCriteriaPanel
            contentType={contentType as ContentType}
            quality={quality}
            className="bg-transparent border-0 backdrop-blur-none p-0"
          />
        </div>
      </details>

      {/* Submit warning dialog */}
      <ConfirmDialog
        open={showSubmitWarning}
        title="Content Quality Warning"
        message={buildWarningMessage(quality)}
        confirmLabel="Run Anyway"
        confirmVariant="primary"
        onConfirm={() => {
          setShowSubmitWarning(false);
          executeSubmit();
        }}
        onCancel={() => setShowSubmitWarning(false)}
      />

      {/* Template overwrite confirmation */}
      <ConfirmDialog
        open={showTemplateConfirm}
        title="Replace Content?"
        message="Loading a template will replace your current content. This cannot be undone."
        confirmLabel="Replace"
        confirmVariant="danger"
        onConfirm={confirmLoadTemplate}
        onCancel={() => {
          setShowTemplateConfirm(false);
          setPendingTemplate("");
        }}
      />
    </div>
  );
}
