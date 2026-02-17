"use client";

import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface AlertBannerProps { ticker: string; alertType: string; severity: "info" | "warning" | "critical"; message: string; onDismiss: () => void; onViewTicker?: (ticker: string) => void; }

const severityStyles = {
  info: "border-l-info bg-info/5",
  warning: "border-l-warning bg-warning/5",
  critical: "border-l-bear bg-bear/5",
};

export default function AlertBanner({ ticker, alertType, severity, message, onDismiss, onViewTicker }: AlertBannerProps) {
  return (
    <div className={cn("border-l-[3px] rounded-xl p-4 flex items-center justify-between bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border", severityStyles[severity])}>
      <div className="flex items-center gap-3">
        <span className="font-mono font-bold text-sm text-text-primary">{ticker}</span>
        <span className="text-sm text-text-secondary">{message}</span>
      </div>
      <div className="flex items-center gap-2">
        {onViewTicker && <button onClick={() => onViewTicker(ticker)} className="text-xs text-primary hover:text-primary-hover underline">View</button>}
        <button onClick={onDismiss} className="text-text-tertiary hover:text-text-primary p-1 rounded-lg hover:bg-background transition-colors"><X size={14} /></button>
      </div>
    </div>
  );
}
