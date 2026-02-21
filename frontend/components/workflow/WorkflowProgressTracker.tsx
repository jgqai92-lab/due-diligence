"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";
import type {
  WorkflowType,
  WorkflowStatus,
  WorkflowStep,
  StepStatus,
} from "@/types/workflow";
import {
  Loader2,
  CheckCircle2,
  XCircle,
  PauseCircle,
  PlayCircle,
  RotateCcw,
  Square,
  Clock,
} from "lucide-react";

// ─── Phase Metadata ─────────────────────────────────────────────────

interface PhaseConfig {
  name: string;
  textColor: string;
  bgColor: string;
}

const IST_PHASES: Record<number, PhaseConfig> = {
  1: { name: "Content Extraction", textColor: "text-sky-400", bgColor: "bg-sky-500/10" },
  2: { name: "Thematic Analysis", textColor: "text-violet-400", bgColor: "bg-violet-500/10" },
  3: { name: "Equity Identification", textColor: "text-amber-400", bgColor: "bg-amber-500/10" },
  4: { name: "Dialectic Scrutiny", textColor: "text-rose-400", bgColor: "bg-rose-500/10" },
  5: { name: "Final Synthesis", textColor: "text-emerald-400", bgColor: "bg-emerald-500/10" },
};

const HFRT_PHASES: Record<number, PhaseConfig> = {
  1: { name: "Data Collection", textColor: "text-sky-400", bgColor: "bg-sky-500/10" },
  2: { name: "Financial Analysis", textColor: "text-violet-400", bgColor: "bg-violet-500/10" },
  3: { name: "Risk Assessment", textColor: "text-amber-400", bgColor: "bg-amber-500/10" },
  4: { name: "Valuation", textColor: "text-rose-400", bgColor: "bg-rose-500/10" },
  5: { name: "Investment Thesis", textColor: "text-emerald-400", bgColor: "bg-emerald-500/10" },
};

const IST_SYNTHESIS_PHASES: Record<number, PhaseConfig> = {
  1: { name: "Screen Ingestion", textColor: "text-sky-400", bgColor: "bg-sky-500/10" },
  2: { name: "Re-Analysis", textColor: "text-violet-400", bgColor: "bg-violet-500/10" },
  3: { name: "Synthesis", textColor: "text-emerald-400", bgColor: "bg-emerald-500/10" },
};

const IST_REFRESH_PHASES: Record<number, PhaseConfig> = {
  1: { name: "Delta Extraction", textColor: "text-sky-400", bgColor: "bg-sky-500/10" },
  2: { name: "Re-Analysis", textColor: "text-violet-400", bgColor: "bg-violet-500/10" },
  3: { name: "Re-Synthesis", textColor: "text-emerald-400", bgColor: "bg-emerald-500/10" },
};

function derivePhasesFromSteps(steps: WorkflowStep[]): Record<number, PhaseConfig> {
  const derived: Record<number, PhaseConfig> = {};
  for (const step of steps) {
    if (!derived[step.phase]) {
      derived[step.phase] = {
        name: step.phaseName || `Phase ${step.phase}`,
        textColor: "text-text-secondary",
        bgColor: "bg-white/10",
      };
    }
  }
  return derived;
}

function getPhases(workflowType: WorkflowType, steps: WorkflowStep[]): Record<number, PhaseConfig> {
  if (workflowType === "IST") return IST_PHASES;
  if (workflowType === "HFRT") return HFRT_PHASES;
  if (workflowType === "IST_SYNTHESIS") return IST_SYNTHESIS_PHASES;
  if (workflowType === "IST_REFRESH") return IST_REFRESH_PHASES;
  const derived = derivePhasesFromSteps(steps);
  return Object.keys(derived).length ? derived : HFRT_PHASES;
}

// ─── Status Styling ─────────────────────────────────────────────────

const STATUS_STYLES: Record<WorkflowStatus, { text: string; bg: string; label: string }> = {
  PENDING:    { text: "text-text-tertiary", bg: "bg-white/5",          label: "Pending" },
  RUNNING:    { text: "text-blue-400",    bg: "bg-blue-500/10",      label: "Running" },
  PAUSED:     { text: "text-amber-400",   bg: "bg-amber-500/10",     label: "Paused" },
  COMPLETED:  { text: "text-emerald-400", bg: "bg-emerald-500/10",   label: "Completed" },
  FAILED:     { text: "text-red-400",     bg: "bg-red-500/10",       label: "Failed" },
  CANCELLED:  { text: "text-text-tertiary", bg: "bg-white/5",        label: "Cancelled" },
  CANCELLING: { text: "text-text-tertiary", bg: "bg-white/5",        label: "Cancelling" },
  RETRYING:   { text: "text-blue-400",    bg: "bg-blue-500/10",      label: "Retrying" },
};

// ─── Helper: Format Duration ────────────────────────────────────────

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

// ─── Props ──────────────────────────────────────────────────────────

interface WorkflowProgressTrackerProps {
  workflowId: number;
  workflowType: WorkflowType;
  steps: WorkflowStep[];
  status: WorkflowStatus;
  currentPhase: number;
  autoAdvance?: boolean;
  onAdvance?: () => void;
  onPause?: () => void;
  onCancel?: () => void;
  onRetry?: () => void;
  onToggleAutoAdvance?: (enabled: boolean) => void;
}

// ─── Component ──────────────────────────────────────────────────────

export default function WorkflowProgressTracker({
  workflowType,
  steps,
  status,
  currentPhase,
  autoAdvance,
  onAdvance,
  onPause,
  onCancel,
  onRetry,
  onToggleAutoAdvance,
}: WorkflowProgressTrackerProps) {
  const phases = getPhases(workflowType, steps);
  const phaseNumbers = Object.keys(phases).map(Number).sort((a, b) => a - b);
  const totalPhases = phaseNumbers.length;

  // Compute step counts
  const completedSteps = steps.filter(s => s.status === "COMPLETED").length;
  const totalSteps = steps.length;

  // Find the currently running step
  const activeStep = useMemo(
    () => steps.find(s => s.status === "RUNNING"),
    [steps]
  );

  // Compute total elapsed time from completed steps
  const totalDurationMs = useMemo(
    () => steps.reduce((sum, s) => sum + (s.durationMs ?? 0), 0),
    [steps]
  );

  // Group steps by phase for the detail section
  const stepsByPhase = useMemo(() => {
    const grouped = new Map<number, WorkflowStep[]>();
    for (const step of steps) {
      const existing = grouped.get(step.phase) || [];
      existing.push(step);
      grouped.set(step.phase, existing);
    }
    return grouped;
  }, [steps]);

  // Determine phase status: COMPLETED if all steps in that phase are done,
  // RUNNING if any step is running, PENDING otherwise
  function getPhaseStatus(phaseNum: number): StepStatus {
    const phaseSteps = stepsByPhase.get(phaseNum);
    if (!phaseSteps || phaseSteps.length === 0) return "PENDING";
    if (phaseSteps.every(s => s.status === "COMPLETED")) return "COMPLETED";
    if (phaseSteps.some(s => s.status === "RUNNING")) return "RUNNING";
    if (phaseSteps.some(s => s.status === "FAILED")) return "FAILED";
    if (phaseSteps.some(s => s.status === "COMPLETED")) return "RUNNING"; // partially done
    return "PENDING";
  }

  const statusStyle = STATUS_STYLES[status];

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] rounded-xl border border-border">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-text-primary">Workflow Progress</h3>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium",
              statusStyle.bg,
              statusStyle.text
            )}
          >
            {status === "RUNNING" && (
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
              </span>
            )}
            {statusStyle.label}
          </span>
        </div>

        {/* Control Buttons */}
        <div className="flex items-center gap-2">
          {/* Auto-Advance Toggle — visible when workflow is active */}
          {onToggleAutoAdvance && status !== "COMPLETED" && status !== "FAILED" && status !== "CANCELLED" && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-secondary">Auto-advance</span>
              <button
                type="button"
                role="switch"
                aria-checked={!!autoAdvance}
                aria-label={autoAdvance ? "Auto-advance is on" : "Auto-advance is off"}
                onClick={() => onToggleAutoAdvance(!autoAdvance)}
                className={cn(
                  "relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
                  autoAdvance ? "bg-primary" : "bg-white/20"
                )}
              >
                <span
                  className={cn(
                    "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
                    autoAdvance ? "translate-x-4" : "translate-x-0"
                  )}
                />
              </button>
            </div>
          )}
          {status === "PENDING" && onAdvance && (
            <button
              onClick={onAdvance}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-primary rounded-lg hover:bg-primary-hover transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
              aria-label="Start workflow"
            >
              <PlayCircle size={14} />
              Start Workflow
            </button>
          )}
          {status === "PAUSED" && onAdvance && !autoAdvance && (
            <button
              onClick={onAdvance}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
              aria-label="Advance workflow to next phase"
            >
              <PlayCircle size={14} />
              Advance
            </button>
          )}
          {status === "RUNNING" && onPause && (
            <button
              onClick={onPause}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-lg hover:bg-amber-500/20 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 focus:ring-offset-transparent"
              aria-label="Pause workflow"
            >
              <PauseCircle size={14} />
              Pause
            </button>
          )}
          {(status === "RUNNING" || status === "PAUSED") && onCancel && (
            <button
              onClick={onCancel}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg hover:bg-red-500/20 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-transparent"
              aria-label="Cancel workflow"
            >
              <Square size={14} />
              Cancel
            </button>
          )}
          {status === "FAILED" && onRetry && (
            <button
              onClick={onRetry}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
              aria-label="Retry workflow from failed step"
            >
              <RotateCcw size={14} />
              Retry
            </button>
          )}
        </div>
      </div>

      {/* Phase Progress Bar */}
      <div className="px-6 py-5">
        {/* Desktop: Horizontal phase dots with connecting line */}
        <div className="hidden sm:block">
          <div className="relative">
            {/* Background track */}
            <div className="absolute top-4 left-0 right-0 h-0.5 bg-white/10" aria-hidden="true" />

            {/* Completed track */}
            {currentPhase > 0 && (
              <div
                className="absolute top-4 left-0 h-0.5 bg-emerald-400 transition-all duration-500"
                style={{
                  width: `${Math.min(
                    ((Math.max(currentPhase - 1, 0)) / (totalPhases - 1)) * 100,
                    100
                  )}%`,
                }}
                aria-hidden="true"
              />
            )}

            {/* Phase dots */}
            <div className="relative flex justify-between">
              {phaseNumbers.map(phaseNum => {
                const phase = phases[phaseNum];
                const phaseStatus = getPhaseStatus(phaseNum);

                return (
                  <div
                    key={phaseNum}
                    className="flex flex-col items-center"
                    style={{ width: `${100 / totalPhases}%` }}
                  >
                    {/* Dot */}
                    <div
                      className={cn(
                        "w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all duration-300",
                        phaseStatus === "COMPLETED" && "bg-emerald-500 border-emerald-500",
                        phaseStatus === "RUNNING" && "bg-[rgba(10,15,26,0.8)] border-blue-500",
                        phaseStatus === "FAILED" && "bg-red-500/10 border-red-500",
                        phaseStatus === "PENDING" && "bg-[rgba(10,15,26,0.8)] border-white/20"
                      )}
                    >
                      {phaseStatus === "COMPLETED" && (
                        <CheckCircle2 size={16} className="text-white" />
                      )}
                      {phaseStatus === "RUNNING" && (
                        <Loader2 size={16} className="text-blue-400 animate-spin" />
                      )}
                      {phaseStatus === "FAILED" && (
                        <XCircle size={16} className="text-red-400" />
                      )}
                      {phaseStatus === "PENDING" && (
                        <span className="w-2 h-2 rounded-full bg-white/20" />
                      )}
                    </div>

                    {/* Label */}
                    <span
                      className={cn(
                        "mt-2 text-xs font-medium text-center leading-tight",
                        phaseStatus === "COMPLETED" && "text-emerald-400",
                        phaseStatus === "RUNNING" && phase.textColor,
                        phaseStatus === "FAILED" && "text-red-400",
                        phaseStatus === "PENDING" && "text-white/30"
                      )}
                    >
                      {phase.name}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Mobile: Vertical phase list */}
        <div className="sm:hidden space-y-3">
          {phaseNumbers.map(phaseNum => {
            const phase = phases[phaseNum];
            const phaseStatus = getPhaseStatus(phaseNum);

            return (
              <div key={phaseNum} className="flex items-center gap-3">
                <div
                  className={cn(
                    "w-7 h-7 rounded-full flex items-center justify-center border-2 flex-shrink-0",
                    phaseStatus === "COMPLETED" && "bg-emerald-500 border-emerald-500",
                    phaseStatus === "RUNNING" && "bg-[rgba(10,15,26,0.8)] border-blue-500",
                    phaseStatus === "FAILED" && "bg-red-500/10 border-red-500",
                    phaseStatus === "PENDING" && "bg-[rgba(10,15,26,0.8)] border-white/20"
                  )}
                >
                  {phaseStatus === "COMPLETED" && (
                    <CheckCircle2 size={14} className="text-white" />
                  )}
                  {phaseStatus === "RUNNING" && (
                    <Loader2 size={14} className="text-blue-400 animate-spin" />
                  )}
                  {phaseStatus === "FAILED" && (
                    <XCircle size={14} className="text-red-400" />
                  )}
                  {phaseStatus === "PENDING" && (
                    <span className="w-1.5 h-1.5 rounded-full bg-white/20" />
                  )}
                </div>
                <span
                  className={cn(
                    "text-xs font-medium",
                    phaseStatus === "COMPLETED" && "text-emerald-400",
                    phaseStatus === "RUNNING" && phase.textColor,
                    phaseStatus === "FAILED" && "text-red-400",
                    phaseStatus === "PENDING" && "text-white/30"
                  )}
                >
                  Phase {phaseNum}: {phase.name}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Active Step Indicator */}
      <div className="px-6 pb-4">
        {status === "PENDING" && (
          <div className="flex items-center gap-2 text-sm text-white/30">
            <Clock size={16} />
            <span>Waiting to start</span>
          </div>
        )}

        {status === "RUNNING" && activeStep && (
          <div className="bg-blue-500/10 rounded-lg px-4 py-3 border border-blue-500/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Loader2 size={16} className="text-blue-400 animate-spin" />
                <span className="text-sm font-medium text-blue-300">
                  {activeStep.stepName}
                </span>
              </div>
              {activeStep.durationMs != null && (
                <span className="text-xs font-mono text-blue-400">
                  {formatDuration(activeStep.durationMs)}
                </span>
              )}
            </div>
          </div>
        )}

        {status === "RUNNING" && !activeStep && (
          <div className="flex items-center gap-2 text-sm text-blue-400">
            <Loader2 size={16} className="animate-spin" />
            <span>Processing...</span>
          </div>
        )}

        {status === "PAUSED" && (
          <div className="bg-amber-500/10 rounded-lg px-4 py-3 border border-amber-500/20">
            <div className="flex items-center gap-2">
              <PauseCircle size={16} className="text-amber-400" />
              <span className="text-sm font-medium text-amber-300">
                Checkpoint reached -- review and approve to continue
              </span>
            </div>
          </div>
        )}

        {status === "COMPLETED" && (
          <div className="bg-emerald-500/10 rounded-lg px-4 py-3 border border-emerald-500/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-emerald-400" />
                <span className="text-sm font-medium text-emerald-300">
                  Workflow completed successfully
                </span>
              </div>
              {totalDurationMs > 0 && (
                <span className="text-xs font-mono text-emerald-400">
                  Total: {formatDuration(totalDurationMs)}
                </span>
              )}
            </div>
          </div>
        )}

        {status === "FAILED" && (
          <div className="bg-red-500/10 rounded-lg px-4 py-3 border border-red-500/20">
            <div className="flex items-center gap-2">
              <XCircle size={16} className="text-red-400" />
              <span className="text-sm font-medium text-red-300">
                Workflow failed {onRetry && "— click Retry to resume from the failed step"}
              </span>
            </div>
          </div>
        )}

        {(status === "CANCELLED" || status === "CANCELLING") && (
          <div className="bg-white/5 rounded-lg px-4 py-3 border border-border">
            <div className="flex items-center gap-2">
              <Square size={16} className="text-white/40" />
              <span className="text-sm font-medium text-white/50">
                {status === "CANCELLING" ? "Cancelling workflow..." : "Workflow cancelled"}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Step Counter Footer */}
      <div className="px-6 py-3 border-t border-border flex items-center justify-between">
        <span className="text-xs text-text-secondary">
          Steps: <span className="font-medium text-text-primary">{completedSteps}</span>/{totalSteps} completed
        </span>
        {totalDurationMs > 0 && status !== "COMPLETED" && (
          <span className="text-xs font-mono text-text-tertiary">
            Elapsed: {formatDuration(totalDurationMs)}
          </span>
        )}
      </div>

      {/* Expandable Step Details */}
      {steps.length > 0 && (
        <div className="px-6 pb-4">
          <details className="group">
            <summary className="text-xs text-text-tertiary cursor-pointer hover:text-text-secondary transition-colors duration-200 select-none">
              Show step details
            </summary>
            <div className="mt-3 space-y-1">
              {phaseNumbers.map(phaseNum => {
                const phaseSteps = stepsByPhase.get(phaseNum);
                if (!phaseSteps || phaseSteps.length === 0) return null;
                const phase = phases[phaseNum];

                return (
                  <div key={phaseNum} className="mb-3">
                    <div
                      className={cn(
                        "text-xs font-medium mb-1 px-2 py-0.5 rounded inline-block",
                        phase.bgColor,
                        phase.textColor
                      )}
                    >
                      Phase {phaseNum}: {phase.name}
                    </div>
                    <div className="space-y-0.5 ml-2">
                      {phaseSteps.map(step => (
                        <div
                          key={step.id}
                          className="flex items-center justify-between py-1 px-2 rounded hover:bg-white/5"
                        >
                          <div className="flex items-center gap-2">
                            <StepStatusIcon status={step.status} />
                            <span
                              className={cn(
                                "text-xs",
                                step.status === "COMPLETED" && "text-text-secondary",
                                step.status === "RUNNING" && "text-blue-400 font-medium",
                                step.status === "FAILED" && "text-red-400",
                                step.status === "PENDING" && "text-white/30",
                                step.status === "SKIPPED" && "text-white/30 line-through"
                              )}
                            >
                              {step.stepName}
                            </span>
                          </div>
                          {step.durationMs != null && (
                            <span className="text-xs font-mono text-text-tertiary">
                              {formatDuration(step.durationMs)}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </details>
        </div>
      )}
    </div>
  );
}

// ─── Sub-Component: Step Status Icon ────────────────────────────────

function StepStatusIcon({ status }: { status: StepStatus }) {
  switch (status) {
    case "COMPLETED":
      return <CheckCircle2 size={12} className="text-emerald-400 flex-shrink-0" />;
    case "RUNNING":
      return <Loader2 size={12} className="text-blue-400 animate-spin flex-shrink-0" />;
    case "FAILED":
      return <XCircle size={12} className="text-red-400 flex-shrink-0" />;
    case "SKIPPED":
      return <span className="w-3 h-3 flex items-center justify-center flex-shrink-0"><span className="w-1.5 h-1.5 rounded-full bg-white/20" /></span>;
    case "PENDING":
    default:
      return <span className="w-3 h-3 flex items-center justify-center flex-shrink-0"><span className="w-1.5 h-1.5 rounded-full bg-white/20" /></span>;
  }
}
