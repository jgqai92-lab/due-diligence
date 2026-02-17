"use client";

import { timeAgo } from "@/lib/utils";

interface DataFreshnessIndicatorProps { fetchedAt: string; }

export default function DataFreshnessIndicator({ fetchedAt }: DataFreshnessIndicatorProps) {
  let level: "fresh" | "recent" | "stale" | "error" = "error";
  let label = "Fetch failed";

  try {
    const date = new Date(fetchedAt);
    const hours = (Date.now() - date.getTime()) / (1000 * 60 * 60);
    if (hours < 1) { level = "fresh"; label = "Just updated"; }
    else if (hours < 24) { level = "recent"; label = `Updated ${timeAgo(fetchedAt)}`; }
    else { level = "stale"; label = `Stale — ${timeAgo(fetchedAt)}`; }
  } catch { /* keep error defaults */ }

  const dotColor = { fresh: "bg-bull", recent: "bg-warning", stale: "bg-bear", error: "bg-bear" }[level];

  return (
    <div className="flex items-center gap-2 text-xs bg-[rgba(10,15,26,0.6)] border border-border rounded-lg px-2.5 py-1 text-text-secondary">
      <span className={`w-2 h-2 rounded-full ${dotColor}`} />
      <span className={level === "error" ? "italic" : ""}>{label}</span>
    </div>
  );
}
