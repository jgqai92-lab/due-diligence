"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { createProject } from "@/lib/api/hfrt";
import { advanceWorkflow } from "@/lib/api/workflows";
import { ArrowLeft, Loader2, AlertCircle } from "lucide-react";

export default function NewResearchPage() {
  const router = useRouter();

  const [ticker, setTicker] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const tickerError =
    ticker.length > 0 && !/^[A-Za-z]{1,10}$/.test(ticker.trim())
      ? "Ticker must be 1-10 letters only"
      : null;
  const isValid = ticker.trim().length > 0 && !tickerError;

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!isValid || submitting) return;

      setSubmitting(true);
      setError(null);

      try {
        const result = await createProject({ ticker: ticker.trim().toUpperCase() });
        // Auto-start the workflow (Phase 1)
        await advanceWorkflow(result.workflowRunId);
        router.push(`/research/${result.id}`);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to create project"
        );
        setSubmitting(false);
      }
    },
    [ticker, isValid, submitting, router]
  );

  return (
    <div className="max-w-xl mx-auto space-y-6 animate-fade-in">
      {/* Back link */}
      <Link
        href="/research"
        className="inline-flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors duration-200"
      >
        <ArrowLeft size={16} />
        Back to Research
      </Link>

      {/* Page header */}
      <div>
        <h1 className="font-display text-2xl font-bold text-text-primary">
          New Research Project
        </h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Enter a ticker symbol to start a deep equity research pipeline.
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-5 py-4 flex items-start gap-3">
          <AlertCircle size={18} className="text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-300">
              Failed to create project
            </p>
            <p className="text-xs text-red-400 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Ticker */}
        <div>
          <label
            htmlFor="ticker"
            className="block text-sm font-medium text-text-secondary mb-1.5"
          >
            Ticker Symbol <span className="text-red-500">*</span>
          </label>
          <input
            id="ticker"
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="e.g., MSFT, AAPL, NVDA"
            maxLength={10}
            required
            disabled={submitting}
            className={cn(
              "w-full px-4 py-3 text-lg font-mono text-text-primary bg-[rgba(10,15,26,0.6)] border rounded-lg",
              "placeholder:text-text-tertiary transition-colors duration-200 tracking-wider",
              "focus:outline-none focus:ring-1 focus:ring-primary/30",
              submitting && "bg-white/5 cursor-not-allowed",
              tickerError
                ? "border-red-500/50 focus:border-red-500"
                : "border-border focus:border-primary"
            )}
            aria-invalid={tickerError ? "true" : undefined}
            aria-describedby={tickerError ? "ticker-error" : undefined}
          />
          {tickerError && (
            <p id="ticker-error" className="mt-1 text-xs text-red-400">
              {tickerError}
            </p>
          )}
          <p className="mt-2 text-xs text-text-tertiary">
            The HFRT pipeline will automatically run 23 steps across 5 phases:
            Screening, Deep Research, Risk &amp; DD, Dialectic, and Synthesis.
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Link
            href="/research"
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
            {submitting && <Loader2 size={16} className="animate-spin" />}
            {submitting ? "Creating..." : "Start Research"}
          </button>
        </div>
      </form>
    </div>
  );
}
