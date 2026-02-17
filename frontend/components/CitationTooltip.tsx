"use client";

import { useState } from "react";
import type { Citation } from "@/types/analysis";
import { formatLargeNumber } from "@/lib/utils";

interface CitationTooltipProps {
  citation: Citation;
  children: React.ReactNode;
}

export default function CitationTooltip({ citation, children }: CitationTooltipProps) {
  const [show, setShow] = useState(false);

  // Don't render tooltip wrapper if no meaningful data
  if (!citation.source && !citation.formula && !citation.description) {
    return <>{children}</>;
  }

  return (
    <span
      className="relative inline-flex items-center gap-1 cursor-help"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      onFocus={() => setShow(true)}
      onBlur={() => setShow(false)}
      tabIndex={0}
      role="button"
      aria-describedby={show ? "citation-tooltip" : undefined}
    >
      {children}
      <span className="text-info text-[10px] opacity-60 hover:opacity-100 transition-opacity">i</span>
      {show && (
        <div
          id="citation-tooltip"
          role="tooltip"
          className="absolute bottom-full left-0 mb-2 z-50 w-80 p-4 bg-[rgba(10,15,26,0.95)] backdrop-blur-[16px] border border-border rounded-xl shadow-lg text-xs animate-fade-in text-text-primary"
        >
          {/* Formula Section - Most Prominent */}
          {citation.formula && (
            <div className="mb-3 pb-3 border-b border-border">
              <div className="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mb-1">
                Formula
              </div>
              <div className="font-mono text-sm text-text-primary bg-black/30 rounded-lg px-2 py-1.5 break-all">
                {citation.formula}
              </div>
            </div>
          )}

          {/* Description Section */}
          {citation.description && (
            <div className="mb-3 pb-3 border-b border-border">
              <div className="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mb-1">
                What it measures
              </div>
              <div className="text-text-secondary leading-relaxed">
                {citation.description}
              </div>
            </div>
          )}

          {/* Data Source Section */}
          <div className="space-y-1.5">
            <div className="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider">
              Data Source
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-text-secondary">
              <div>
                <span className="text-text-tertiary">Provider:</span>{" "}
                <span className="text-text-primary">{citation.source || "yfinance"}</span>
              </div>
              <div>
                <span className="text-text-tertiary">Period:</span>{" "}
                <span className="text-text-primary">{citation.period || "N/A"}</span>
              </div>
              {citation.line_item && (
                <div className="col-span-2">
                  <span className="text-text-tertiary">Line Item:</span>{" "}
                  <span className="text-text-primary font-mono text-[11px]">{citation.line_item}</span>
                </div>
              )}
              {citation.raw_value != null && (
                <div className="col-span-2">
                  <span className="text-text-tertiary">Raw Value:</span>{" "}
                  <span className="text-text-primary font-mono">{formatLargeNumber(citation.raw_value)}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </span>
  );
}
