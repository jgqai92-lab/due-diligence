"use client";

import type { ISTScreenListItem } from "@/types/ist";

interface ScreenSelectorProps {
  screens: ISTScreenListItem[];
  selectedIds: number[];
  onToggle: (id: number) => void;
}

export default function ScreenSelector({
  screens,
  selectedIds,
  onToggle,
}: ScreenSelectorProps) {
  return (
    <div className="space-y-2">
      {screens.map((screen) => (
        <label
          key={screen.id}
          className="flex items-start gap-3 p-3 rounded-lg border border-border bg-[rgba(10,15,26,0.6)]"
        >
          <input
            type="checkbox"
            checked={selectedIds.includes(screen.id)}
            onChange={() => onToggle(screen.id)}
            className="mt-0.5"
          />
          <div className="min-w-0">
            <p className="text-sm font-medium text-text-primary">{screen.name}</p>
            <p className="text-xs text-text-secondary">
              Tier 1: {screen.tier1Count} · Candidates: {screen.candidateCount}
            </p>
          </div>
        </label>
      ))}
    </div>
  );
}

