"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { useWorkflowSSE } from "@/hooks/useWorkflowSSE";
import WorkflowProgressTracker from "@/components/workflow/WorkflowProgressTracker";
import OverlapMatrix from "@/components/ist/synthesis/OverlapMatrix";
import ThesisInteractions from "@/components/ist/synthesis/ThesisInteractions";
import TierChanges from "@/components/ist/synthesis/TierChanges";
import SynthesisEquities from "@/components/ist/synthesis/SynthesisEquities";
import SynthesisReport from "@/components/ist/synthesis/SynthesisReport";
import SynthesisHandoff from "@/components/ist/synthesis/SynthesisHandoff";
import {
  getSynthesis,
  getSynthesisDialectic,
  getSynthesisEquities,
} from "@/lib/api/ist-synthesis";
import {
  getWorkflow,
  advanceWorkflow,
  pauseWorkflow,
  cancelWorkflow,
  retryWorkflow,
  toggleAutoAdvance,
} from "@/lib/api/workflows";
import type { SynthesisDetail, SynthesisEquity } from "@/types/ist-synthesis";
import type { WorkflowDetail, WorkflowStatus, WorkflowStep } from "@/types/workflow";

type Tab = "report" | "overlap" | "interactions" | "tier-changes" | "equities" | "dialectic" | "handoff";

export default function SynthesisDetailPage() {
  const params = useParams();
  const synthesisId = Number(params.id);

  const [synthesis, setSynthesis] = useState<SynthesisDetail | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("report");
  const [dialecticSide, setDialecticSide] = useState<"OPTIMIST" | "PESSIMIST" | "SYNTHESIS">("SYNTHESIS");
  const [dialecticContent, setDialecticContent] = useState<Record<string, unknown> | null>(null);
  const [equities, setEquities] = useState<SynthesisEquity[]>([]);

  const load = useCallback(async () => {
    if (Number.isNaN(synthesisId)) return;
    setLoading(true);
    setError(null);
    try {
      const detail = await getSynthesis(synthesisId);
      setSynthesis(detail);
      const wf = await getWorkflow(detail.workflowRunId);
      setWorkflow(wf);
      const eq = await getSynthesisEquities(detail.id);
      setEquities(eq.equities);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load synthesis");
    } finally {
      setLoading(false);
    }
  }, [synthesisId]);

  const refresh = useCallback(async () => {
    if (!synthesis) return;
    try {
      const detail = await getSynthesis(synthesisId);
      setSynthesis(detail);
      const wf = await getWorkflow(detail.workflowRunId);
      setWorkflow(wf);
      const eq = await getSynthesisEquities(detail.id);
      setEquities(eq.equities);
    } catch {
      // Silent refresh.
    }
  }, [synthesis, synthesisId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!synthesis) return;
    getSynthesisDialectic(synthesis.id, dialecticSide)
      .then((d) => setDialecticContent(d.content))
      .catch(() => setDialecticContent(null));
  }, [synthesis, dialecticSide]);

  const { workflowStatus: sseStatus, steps: sseSteps } = useWorkflowSSE({
    workflowId: synthesis?.workflowRunId ?? null,
    onWorkflowComplete: refresh,
    onCheckpoint: refresh,
  });

  const effectiveStatus: WorkflowStatus = sseStatus ?? workflow?.status ?? "PENDING";
  const effectiveSteps: WorkflowStep[] = useMemo(() => {
    if (!workflow?.steps) return [];
    return workflow.steps.map((step) => {
      const update = sseSteps.get(step.stepName);
      if (!update) return step;
      return {
        ...step,
        status: update.status,
        durationMs: update.durationMs ?? step.durationMs,
      };
    });
  }, [workflow?.steps, sseSteps]);

  const effectivePhase = workflow?.currentPhase ?? 0;

  const runId = synthesis?.workflowRunId ?? null;
  const onAdvance = async () => {
    if (!runId) return;
    await advanceWorkflow(runId);
    await refresh();
  };
  const onPause = async () => {
    if (!runId) return;
    await pauseWorkflow(runId);
    await refresh();
  };
  const onCancel = async () => {
    if (!runId) return;
    await cancelWorkflow(runId);
    await refresh();
  };
  const onRetry = async () => {
    if (!runId) return;
    await retryWorkflow(runId);
    await refresh();
  };
  const onToggleAutoAdvance = async (enabled: boolean) => {
    if (!runId) return;
    await toggleAutoAdvance(runId, enabled);
    await refresh();
  };

  if (loading) return <p className="text-sm text-text-secondary">Loading synthesis...</p>;
  if (!synthesis) return <p className="text-sm text-red-400">{error ?? "Synthesis not found."}</p>;

  return (
    <div className="space-y-6">
      <Link href="/screens/syntheses" className="text-sm text-text-secondary hover:text-text-primary">
        Back to Syntheses
      </Link>

      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">{synthesis.name}</h1>
          <p className="text-sm text-text-secondary mt-0.5">Status: {synthesis.status}</p>
        </div>
      </div>

      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {workflow && (
        <WorkflowProgressTracker
          workflowId={workflow.id}
          workflowType="IST_SYNTHESIS"
          steps={effectiveSteps}
          status={effectiveStatus}
          currentPhase={effectivePhase}
          autoAdvance={workflow.autoAdvance}
          onAdvance={onAdvance}
          onPause={onPause}
          onCancel={onCancel}
          onRetry={onRetry}
          onToggleAutoAdvance={onToggleAutoAdvance}
        />
      )}

      <div className="flex items-center gap-1 border-b border-border overflow-x-auto">
        {([
          "report",
          "overlap",
          "interactions",
          "tier-changes",
          "equities",
          "dialectic",
          "handoff",
        ] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "px-3 py-2.5 text-sm whitespace-nowrap",
              tab === t ? "text-primary border-b-2 border-primary" : "text-text-secondary hover:text-text-primary"
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "report" && (
        <SynthesisReport report={synthesis.report} metadata={synthesis.reportMetadata} />
      )}
      {tab === "overlap" && (
        <OverlapMatrix entries={synthesis.overlapMatrix ?? []} />
      )}
      {tab === "interactions" && (
        <ThesisInteractions interactions={synthesis.thesisInteractions ?? []} />
      )}
      {tab === "tier-changes" && (
        <TierChanges changes={synthesis.tierChanges ?? []} />
      )}
      {tab === "equities" && (
        <SynthesisEquities equities={equities} />
      )}
      {tab === "dialectic" && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            {(["OPTIMIST", "PESSIMIST", "SYNTHESIS"] as const).map((side) => (
              <button
                key={side}
                onClick={() => setDialecticSide(side)}
                className={cn(
                  "px-3 py-1.5 text-xs rounded-full",
                  dialecticSide === side ? "bg-primary/20 text-primary" : "bg-white/10 text-text-secondary"
                )}
              >
                {side}
              </button>
            ))}
          </div>
          <pre className="text-xs text-text-secondary bg-[rgba(10,15,26,0.6)] border border-border rounded-lg p-4 overflow-auto">
            {JSON.stringify(dialecticContent, null, 2)}
          </pre>
        </div>
      )}
      {tab === "handoff" && (
        <SynthesisHandoff handoff={synthesis.hfrtHandoff} />
      )}
    </div>
  );
}
