"use client";

import { cn } from "@/lib/utils";

interface RedFlagBadgeProps { flag: string; severity: "low" | "medium" | "high" | "critical"; }

const severityStyles = {
  low: "bg-info/10 text-info border-info/30",
  medium: "bg-warning/10 text-warning border-warning/30",
  high: "bg-bear/10 text-bear border-bear/30",
  critical: "bg-bear text-white border-bear font-bold",
};

export default function RedFlagBadge({ flag, severity }: RedFlagBadgeProps) {
  return <span className={cn("inline-flex items-center px-2 py-0.5 border rounded-lg text-[11px] font-medium", severityStyles[severity])}>{flag}</span>;
}
