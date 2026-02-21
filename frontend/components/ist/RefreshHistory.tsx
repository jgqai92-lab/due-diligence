"use client";

import { cn, timeAgo } from "@/lib/utils";
import type { ISTRefreshListItem } from "@/types/ist";

interface RefreshHistoryProps {
  refreshes: ISTRefreshListItem[];
  selectedRefreshId: number | null;
  onSelectRefresh: (refreshId: number) => void;
}

function statusStyle(status: string): string {
  switch (status) {
    case "COMPLETED":
      return "bg-emerald-500/10 text-emerald-400";
    case "FAILED":
      return "bg-red-500/10 text-red-400";
    case "RE_ANALYZING":
    case "RE_SYNTHESIZING":
    case "ASSESSING":
    case "EXTRACTING":
      return "bg-sky-500/10 text-sky-400";
    default:
      return "bg-white/10 text-text-secondary";
  }
}

export default function RefreshHistory({
  refreshes,
  selectedRefreshId,
  onSelectRefresh,
}: RefreshHistoryProps) {
  if (!refreshes.length) {
    return (
      <div className="rounded-xl border border-border bg-[rgba(10,15,26,0.6)] p-5">
        <h3 className="text-sm font-semibold text-text-primary">Refresh History</h3>
        <p className="text-xs text-text-secondary mt-1">No refresh operations yet.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-[rgba(10,15,26,0.6)] p-5 space-y-3">
      <h3 className="text-sm font-semibold text-text-primary">Refresh History</h3>
      <div className="space-y-2">
        {refreshes.map((refresh) => {
          const selected = selectedRefreshId === refresh.id;
          const timestamp = refresh.createdAt ?? refresh.startedAt ?? refresh.completedAt;
          return (
            <button
              key={refresh.id}
              onClick={() => onSelectRefresh(refresh.id)}
              className={cn(
                "w-full text-left rounded-lg border px-3 py-2 transition-colors",
                selected
                  ? "border-primary bg-primary/10"
                  : "border-border hover:bg-white/5"
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs text-text-primary">
                  Refresh #{refresh.refreshNumber}
                  {timestamp && (
                    <span className="text-text-tertiary"> - {timeAgo(timestamp)}</span>
                  )}
                </p>
                <span className={cn("inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium", statusStyle(refresh.status))}>
                  {refresh.status}
                </span>
              </div>
              <p className="text-[11px] text-text-secondary mt-1">
                Delta claims: {refresh.deltaClaimCount}
                {refresh.stepsReexecuted?.length ? ` - Steps: ${refresh.stepsReexecuted.length}` : ""}
                {refresh.isActive ? " - Active" : ""}
              </p>
              {refresh.errorMessage && (
                <p className="text-[11px] text-red-400 mt-1 line-clamp-2">{refresh.errorMessage}</p>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

