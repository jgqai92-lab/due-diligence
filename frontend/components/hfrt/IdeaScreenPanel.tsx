"use client";

import { cn } from "@/lib/utils";
import type { HFRTTemplate, IdeaScreenData } from "@/types/hfrt";
import { CheckCircle, XCircle, AlertTriangle, Target } from "lucide-react";

interface IdeaScreenPanelProps {
  projectId: number;
  template: HFRTTemplate | null;
}

export default function IdeaScreenPanel({ projectId, template }: IdeaScreenPanelProps) {
  if (!template || template.status !== "POPULATED" || !template.data) {
    if (template?.status === "POPULATING") {
      return (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-text-secondary">Running idea screen...</p>
        </div>
      );
    }
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 text-center py-12 text-text-tertiary">
        <Target size={32} className="mx-auto mb-3" />
        <p className="text-sm">Idea screen not yet completed.</p>
        <p className="text-xs mt-1">Start the workflow to run the initial screening.</p>
      </div>
    );
  }

  const raw = template.data as Record<string, unknown>;

  // IST handoff pre-populates template 0 with a different shape than HFRT's idea screen.
  // Detect it and render a handoff-specific view.
  if (raw.prePopulated) {
    return (
      <div className="space-y-4">
        {/* IST Handoff Banner */}
        <div className="rounded-xl border px-6 py-5 flex items-center gap-4 bg-sky-500/10 border-sky-500/30">
          <Target size={28} className="text-sky-400" />
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-1">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-bold bg-sky-500/20 text-sky-300">
                IST Handoff
              </span>
              <span className="text-sm text-text-secondary">{String(raw.companyName ?? "")}</span>
            </div>
            <p className="text-sm text-text-primary">{String(raw.thesis ?? "")}</p>
          </div>
        </div>

        {/* Handoff Details */}
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">IST Screen Context</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-text-secondary">Ticker</p>
              <p className="text-sm font-mono font-bold text-text-primary">{String(raw.ticker ?? "")}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">Source Screen</p>
              <p className="text-sm text-text-primary">{String(raw.istScreenName ?? `Screen #${raw.istScreenId}`)}</p>
            </div>
            {raw.scarcityScore != null && (
              <div>
                <p className="text-xs text-text-secondary">Scarcity Score</p>
                <p className="text-sm font-mono text-text-primary">{Number(raw.scarcityScore).toFixed(1)}</p>
              </div>
            )}
            {raw.bottleneckExposure != null && (
              <div>
                <p className="text-xs text-text-secondary">Bottleneck Exposure</p>
                <p className="text-sm text-text-primary">{String(raw.bottleneckExposure)}</p>
              </div>
            )}
          </div>
          {raw.catalyst != null && (
            <div className="mt-3 pt-3 border-t border-border">
              <p className="text-xs text-text-secondary mb-1">Key Catalyst</p>
              <p className="text-sm text-text-primary">{String(raw.catalyst)}</p>
            </div>
          )}
        </div>

        <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-xl px-5 py-4">
          <p className="text-xs text-indigo-300">
            This idea screen was pre-populated from the IST pipeline. Start the HFRT workflow to run the full screening analysis with liquidity checks, red flag detection, and sector classification.
          </p>
        </div>
      </div>
    );
  }

  const data = raw as unknown as IdeaScreenData;

  const verdictConfig = {
    PASS: { bg: "bg-emerald-500/10", text: "text-emerald-300", icon: CheckCircle },
    FAIL: { bg: "bg-red-500/10", text: "text-red-300", icon: XCircle },
    CONDITIONAL: { bg: "bg-amber-500/10", text: "text-amber-300", icon: AlertTriangle },
  };
  const verdict = verdictConfig[data.verdict] || verdictConfig.CONDITIONAL;
  const VerdictIcon = verdict.icon;

  return (
    <div className="space-y-4">
      {/* Verdict Banner */}
      <div className={cn(
        "rounded-xl border px-6 py-5 flex items-center gap-4",
        data.verdict === "PASS" ? "bg-emerald-500/10 border-emerald-500/30" :
        data.verdict === "FAIL" ? "bg-red-500/10 border-red-500/30" :
        "bg-amber-500/10 border-amber-500/30"
      )}>
        <VerdictIcon size={28} className={verdict.text} />
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-1">
            <span className={cn(
              "inline-flex items-center px-3 py-1 rounded-full text-sm font-bold",
              verdict.bg, verdict.text
            )}>
              {data.verdict}
            </span>
            <span className="text-sm text-text-secondary">{data.companyName}</span>
          </div>
          <p className="text-sm text-text-primary">{data.rationale}</p>
        </div>
      </div>

      {/* Company Info */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-3">Company Info</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-text-secondary">Ticker</p>
            <p className="text-sm font-mono font-bold text-text-primary">{data.ticker}</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">Sector</p>
            <p className="text-sm text-text-primary">{data.sector}</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">Exchange</p>
            <p className="text-sm text-text-primary">{data.exchange}</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">Market Cap</p>
            <p className="text-sm font-mono text-text-primary">
              {data.marketCapBillions != null ? `$${data.marketCapBillions.toFixed(1)}B` : "N/A"}
            </p>
          </div>
        </div>
      </div>

      {/* Liquidity Check */}
      {data.liquidityCheck && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Liquidity Check</h3>
          <div className="flex items-center gap-2 mb-3">
            {data.liquidityCheck.passes ? (
              <CheckCircle size={16} className="text-emerald-500" />
            ) : (
              <XCircle size={16} className="text-red-500" />
            )}
            <span className={cn(
              "text-sm font-medium",
              data.liquidityCheck.passes ? "text-emerald-300" : "text-red-300"
            )}>
              {data.liquidityCheck.passes ? "Passes" : "Fails"}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
            {data.liquidityCheck.avg_daily_volume != null && (
              <div className="bg-white/5 rounded-lg px-3 py-2">
                <p className="text-xs text-text-secondary">Avg Daily Volume</p>
                <p className="font-mono text-text-primary">
                  {data.liquidityCheck.avg_daily_volume.toLocaleString()}
                </p>
              </div>
            )}
            {data.liquidityCheck.market_cap_billions != null && (
              <div className="bg-white/5 rounded-lg px-3 py-2">
                <p className="text-xs text-text-secondary">Market Cap</p>
                <p className="font-mono text-text-primary">
                  ${data.liquidityCheck.market_cap_billions.toFixed(1)}B
                </p>
              </div>
            )}
            {data.liquidityCheck.bid_ask_spread && (
              <div className="bg-white/5 rounded-lg px-3 py-2">
                <p className="text-xs text-text-secondary">Bid-Ask Spread</p>
                <p className="font-mono text-text-primary">{data.liquidityCheck.bid_ask_spread}</p>
              </div>
            )}
          </div>
          {data.liquidityCheck.notes && (
            <p className="text-xs text-text-secondary mt-2">{data.liquidityCheck.notes}</p>
          )}
        </div>
      )}

      {/* Red Flags */}
      {data.redFlags && data.redFlags.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Red Flags ({data.redFlags.length})
          </h3>
          <ul className="space-y-2">
            {data.redFlags.map((flag, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <AlertTriangle size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />
                <span className="text-text-primary">{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Key Metrics */}
      {data.keyMetrics && Object.keys(data.keyMetrics).length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Key Metrics</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(data.keyMetrics).map(([key, value]) => (
              <div key={key} className="bg-white/5 rounded-lg px-3 py-2">
                <p className="text-xs text-text-secondary capitalize">
                  {key.replace(/_/g, " ")}
                </p>
                <p className="text-sm font-mono text-text-primary">
                  {typeof value === "number" ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(value ?? "N/A")}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
