"use client";

import type { ThesisInteraction } from "@/types/ist-synthesis";

interface ThesisInteractionsProps {
  interactions: ThesisInteraction[];
}

export default function ThesisInteractions({ interactions }: ThesisInteractionsProps) {
  if (!interactions.length) {
    return <p className="text-sm text-text-secondary">No thesis interactions available yet.</p>;
  }

  return (
    <div className="space-y-3">
      {interactions.map((item, idx) => (
        <div key={idx} className="rounded-lg border border-border bg-[rgba(10,15,26,0.6)] p-4">
          <p className="text-sm font-medium text-text-primary">
            {item.screenA.name} × {item.screenB.name}
          </p>
          <p className="text-xs text-text-secondary mt-1">
            {item.classification.toUpperCase()} · {item.rationale}
          </p>
        </div>
      ))}
    </div>
  );
}

