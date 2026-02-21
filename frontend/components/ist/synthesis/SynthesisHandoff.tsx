"use client";

interface SynthesisHandoffProps {
  handoff: Record<string, unknown> | null;
}

export default function SynthesisHandoff({ handoff }: SynthesisHandoffProps) {
  if (!handoff) {
    return <p className="text-sm text-text-secondary">HFRT handoff not generated yet.</p>;
  }

  return (
    <pre className="text-xs text-text-secondary bg-[rgba(10,15,26,0.6)] border border-border rounded-lg p-4 overflow-auto">
      {JSON.stringify(handoff, null, 2)}
    </pre>
  );
}

