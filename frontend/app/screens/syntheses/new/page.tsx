"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ScreenSelector from "@/components/ist/synthesis/ScreenSelector";
import { listScreens } from "@/lib/api/ist";
import { createSynthesis } from "@/lib/api/ist-synthesis";
import { advanceWorkflow } from "@/lib/api/workflows";
import type { ISTScreenListItem } from "@/types/ist";

export default function NewSynthesisPage() {
  const router = useRouter();
  const [screens, setScreens] = useState<ISTScreenListItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [name, setName] = useState("");
  const [autoAdvance, setAutoAdvance] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listScreens({ limit: 100 })
      .then((res) => setScreens(res.screens))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load screens"))
      .finally(() => setLoading(false));
  }, []);

  const completedScreens = useMemo(
    () => screens.filter((s) => s.status === "COMPLETED"),
    [screens]
  );

  const canSubmit = name.trim().length > 0 && selectedIds.length >= 2 && !submitting;

  function toggleScreen(id: number) {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const idempotencyKey =
        typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : `synth-${Date.now()}`;
      const created = await createSynthesis({
        name: name.trim(),
        screenIds: selectedIds,
        autoAdvance,
        idempotencyKey,
      });
      await advanceWorkflow(created.workflowRunId);
      router.push(`/screens/syntheses/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create synthesis");
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <Link href="/screens/syntheses" className="text-sm text-text-secondary hover:text-text-primary">
        Back to Syntheses
      </Link>

      <div>
        <h1 className="font-display text-2xl font-bold text-text-primary">Create New Synthesis</h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Select at least two completed screens and launch the synthesis workflow.
        </p>
      </div>

      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-text-secondary">Loading available screens...</p>
      ) : (
        <form onSubmit={onSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">Synthesis Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border bg-[rgba(10,15,26,0.6)] text-sm text-text-primary"
              placeholder="e.g., AI Agents + Energy Infrastructure"
            />
          </div>

          <div className="flex items-center justify-between">
            <p className="text-sm text-text-secondary">
              Select source screens ({selectedIds.length} selected)
            </p>
            <label className="text-sm text-text-secondary inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={autoAdvance}
                onChange={(e) => setAutoAdvance(e.target.checked)}
              />
              Auto-advance
            </label>
          </div>

          <ScreenSelector screens={completedScreens} selectedIds={selectedIds} onToggle={toggleScreen} />

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={!canSubmit}
              className="px-4 py-2.5 text-sm font-medium rounded-lg bg-primary text-[#050810] disabled:bg-white/10 disabled:text-text-tertiary"
            >
              {submitting ? "Creating..." : "Create Synthesis"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
