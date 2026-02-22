"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  getScreen,
  updateScreenBrief,
  deleteScreen,
  getScreenInputs,
  rerunScreen,
  createScreenRefresh,
  listScreenRefreshes,
  getScreenRefresh,
  getScreenRefreshClaims,
} from "@/lib/api/ist";
import { getWorkflow, advanceWorkflow, pauseWorkflow, cancelWorkflow, retryWorkflow, toggleAutoAdvance } from "@/lib/api/workflows";
import { useWorkflowSSE } from "@/hooks/useWorkflowSSE";
import WorkflowProgressTracker from "@/components/workflow/WorkflowProgressTracker";
import ClaimsTable from "@/components/ist/ClaimsTable";
import ScreeningBriefEditor from "@/components/ist/ScreeningBriefEditor";
import type { ISTClaim, ISTRefreshDetail, ISTRefreshListItem, ISTScreenDetail, ISTScreenStatus } from "@/types/ist";
import type { WorkflowDetail, WorkflowStatus, WorkflowStep } from "@/types/workflow";
import { ArrowLeft, Loader2, AlertCircle, FileText, BarChart3, Target, Map, TrendingUp, Scale, FileCheck, CheckCircle, GitBranch, ShieldCheck, Trophy, RefreshCw, Calendar, Zap, Trash2, Eye, ChevronUp } from "lucide-react";
import ActionMenu from "@/components/ActionMenu";
import ConfirmDialog from "@/components/ConfirmDialog";
import BottleneckMap from "@/components/ist/BottleneckMap";
import DemandModels from "@/components/ist/DemandModels";
import ValidationResults from "@/components/ist/ValidationResults";
import EquityCandidates from "@/components/ist/EquityCandidates";
import EffectsChains from "@/components/ist/EffectsChains";
import InvariantChecklist from "@/components/ist/InvariantChecklist";
import DialecticView from "@/components/ist/DialecticView";
import SynthesisView from "@/components/ist/SynthesisView";
import InvestmentThesisReport from "@/components/ist/InvestmentThesisReport";
import MasterScreenTable from "@/components/ist/MasterScreenTable";
import RotationStrategy from "@/components/ist/RotationStrategy";
import CatalystCalendar from "@/components/ist/CatalystCalendar";
import StressTests from "@/components/ist/StressTests";
import FrameworksPanel from "@/components/ist/FrameworksPanel";
import HandoffPanel from "@/components/ist/HandoffPanel";
import RefreshModal from "@/components/ist/RefreshModal";
import RefreshHistory from "@/components/ist/RefreshHistory";
import RefreshDelta from "@/components/ist/RefreshDelta";
import PersonaLauncher from "@/components/persona/PersonaLauncher";
import PersonaHistory from "@/components/persona/PersonaHistory";

// ─── IST Status Badge Config ────────────────────────────────────────

const IST_STATUS_CONFIG: Record<ISTScreenStatus, { bg: string; text: string; label: string }> = {
  PENDING:      { bg: "bg-white/10",         text: "text-text-secondary",  label: "Pending" },
  EXTRACTING:   { bg: "bg-sky-500/20",       text: "text-sky-400",         label: "Extracting" },
  ANALYZING:    { bg: "bg-violet-500/20",    text: "text-violet-400",      label: "Analyzing" },
  SCANNING:     { bg: "bg-amber-500/20",     text: "text-amber-400",       label: "Scanning" },
  DIALECTIC:    { bg: "bg-rose-500/20",      text: "text-rose-400",        label: "Dialectic" },
  SYNTHESIZING: { bg: "bg-emerald-500/20",   text: "text-emerald-400",     label: "Synthesizing" },
  COMPLETED:    { bg: "bg-emerald-600",      text: "text-white",           label: "Completed" },
  FAILED:       { bg: "bg-red-600",          text: "text-white",           label: "Failed" },
};

// ─── Main Tab Types ─────────────────────────────────────────────────

type MainTab = "report" | "working-data" | "personas";

// ─── Working Data Sub-Tab Types ─────────────────────────────────────

type WorkingDataTab = "brief" | "claims" | "bottleneck-map" | "demand-models" | "validation" | "candidates" | "effects" | "invariants" | "dialectic" | "synthesis" | "master-screen" | "rotation" | "catalysts" | "stress-tests";

const WORKING_DATA_TABS: { id: WorkingDataTab; label: string; icon: typeof FileText; minPhase: number; description: string }[] = [
  { id: "brief",          label: "Brief",          icon: Target,      minPhase: 1, description: "Source bias profile of your input content \u2014 who the speaker is, their incentives, and credibility score. Editable when paused." },
  { id: "claims",         label: "Claims",         icon: FileText,    minPhase: 1, description: "Every discrete factual claim extracted from your input, tagged with quantitative anchors, temporal markers, and named entities." },
  { id: "bottleneck-map", label: "Bottleneck Map", icon: Map,         minPhase: 2, description: "Claims organized into named supply/demand bottlenecks with temporal cascades \u2014 when each binds, eases, and what triggers rotation." },
  { id: "demand-models",  label: "Demand Models",  icon: TrendingUp,  minPhase: 2, description: "Quantitative TAM models per bottleneck with bear/base/bull scenarios, formulas, multiplier chains, and sensitivity analysis." },
  { id: "validation",     label: "Validation",     icon: CheckCircle, minPhase: 2, description: "Cross-references major claims against independent data. Flags each as confirmed, contradicted, or unverifiable." },
  { id: "candidates",     label: "Candidates",     icon: BarChart3,   minPhase: 3, description: "Investable companies mapped to each bottleneck, with Tier 1/2/3 classification based on scarcity of exposure and basic valuation data." },
  { id: "effects",        label: "Effects",        icon: GitBranch,   minPhase: 3, description: "2nd and 3rd order downstream effects \u2014 traces causal chains from obvious first-order beneficiaries to non-consensus opportunities." },
  { id: "invariants",     label: "Invariants",     icon: ShieldCheck, minPhase: 3, description: "Internal consistency checks \u2014 verifies TAM alignment with candidates, bottleneck coverage, and catches logical gaps before proceeding." },
  { id: "dialectic",      label: "Dialectic",      icon: Scale,       minPhase: 4, description: "Adversarial three-part review: an Optimist builds the bull case, a Pessimist stress-tests it, then a Synthesis reconciles both views." },
  { id: "synthesis",      label: "Synthesis",      icon: FileCheck,   minPhase: 5, description: "Reconciled investment thesis combining the dialectic output into a final narrative with conviction assessment." },
  { id: "master-screen",  label: "Master Screen",  icon: Trophy,      minPhase: 5, description: "Ranked equity table \u2014 every candidate with final tier, conviction score, key metrics, and positioning thesis. The actionable output." },
  { id: "rotation",       label: "Rotation",       icon: RefreshCw,   minPhase: 5, description: "Temporal rotation strategy \u2014 when to shift weight between themes as bottlenecks evolve and earlier plays peak." },
  { id: "catalysts",      label: "Catalysts",      icon: Calendar,    minPhase: 5, description: "Calendar of upcoming events that validate or invalidate the thesis \u2014 earnings, regulatory rulings, plant commissioning milestones." },
  { id: "stress-tests",   label: "Stress Tests",   icon: Zap,         minPhase: 5, description: "Scenario analysis on the overall screen \u2014 what happens under demand disappointment, accelerated supply, or policy change." },
];

// ─── Page ───────────────────────────────────────────────────────────

export default function ScreenDetailPage() {
  const params = useParams();
  const router = useRouter();
  const screenId = Number(params.id);

  // Screen data
  const [screen, setScreen] = useState<ISTScreenDetail | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showRerunConfirm, setShowRerunConfirm] = useState(false);
  const [showRefreshModal, setShowRefreshModal] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [refreshWarning, setRefreshWarning] = useState<string | null>(null);
  const [refreshModalError, setRefreshModalError] = useState<string | null>(null);
  const [refreshes, setRefreshes] = useState<ISTRefreshListItem[]>([]);
  const [selectedRefreshId, setSelectedRefreshId] = useState<number | null>(null);
  const [selectedRefresh, setSelectedRefresh] = useState<ISTRefreshDetail | null>(null);
  const [selectedRefreshClaims, setSelectedRefreshClaims] = useState<ISTClaim[]>([]);
  const [refreshDetailLoading, setRefreshDetailLoading] = useState(false);
  const [refreshDetailError, setRefreshDetailError] = useState<string | null>(null);

  // Original Inputs state
  const [showInputs, setShowInputs] = useState(false);
  const [inputs, setInputs] = useState<Awaited<ReturnType<typeof getScreenInputs>> | null>(null);
  const [inputsLoading, setInputsLoading] = useState(false);

  // Tab state -- initial tab depends on screen status (set after load)
  const [mainTab, setMainTab] = useState<MainTab>("working-data");
  const [workingDataTab, setWorkingDataTab] = useState<WorkingDataTab>("claims");
  const [hasAutoSwitched, setHasAutoSwitched] = useState(false);
  const activeWorkflowRunId = screen?.activeWorkflowRunId ?? screen?.workflowRunId ?? null;

  // SSE connection for real-time workflow updates
  const {
    workflowStatus: sseStatus,
    steps: sseSteps,
  } = useWorkflowSSE({
    workflowId: activeWorkflowRunId,
    onWorkflowComplete: () => refreshScreen(),
    onCheckpoint: () => refreshScreen(),
  });

  // Derive the effective workflow status (SSE overrides if connected)
  const effectiveStatus: WorkflowStatus = sseStatus ?? workflow?.status ?? "PENDING";

  // Merge SSE step updates with the initial workflow steps
  const effectiveSteps: WorkflowStep[] = workflow?.steps
    ? workflow.steps.map((step) => {
        const sseUpdate = sseSteps.get(step.stepName);
        if (sseUpdate) {
          return {
            ...step,
            status: sseUpdate.status,
            durationMs: sseUpdate.durationMs ?? step.durationMs,
          };
        }
        return step;
      })
    : [];

  // Derive effective current phase
  const effectivePhase = workflow?.currentPhase ?? screen?.currentPhase ?? 0;

  // Fetch screen and workflow data
  const fetchData = useCallback(async () => {
    if (isNaN(screenId)) return;

    setLoading(true);
    setError(null);

    try {
      const screenData = await getScreen(screenId);
      setScreen(screenData);
      const refreshData = await listScreenRefreshes(screenId).catch(() => null);
      const nextRefreshes = refreshData?.refreshes ?? [];
      setRefreshes(nextRefreshes);
      setSelectedRefreshId((prev) => {
        if (!nextRefreshes.length) return null;
        if (prev && nextRefreshes.some((item) => item.id === prev)) return prev;
        return nextRefreshes[0].id;
      });

      const runId = screenData.activeWorkflowRunId ?? screenData.workflowRunId;
      if (runId) {
        const workflowData = await getWorkflow(runId);
        setWorkflow(workflowData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load screen");
    } finally {
      setLoading(false);
    }
  }, [screenId]);

  const refreshScreen = useCallback(async () => {
    try {
      const screenData = await getScreen(screenId);
      setScreen(screenData);
      const refreshData = await listScreenRefreshes(screenId).catch(() => null);
      const nextRefreshes = refreshData?.refreshes ?? [];
      setRefreshes(nextRefreshes);
      setSelectedRefreshId((prev) => {
        if (!nextRefreshes.length) return null;
        if (prev && nextRefreshes.some((item) => item.id === prev)) return prev;
        return nextRefreshes[0].id;
      });
      const runId = screenData.activeWorkflowRunId ?? screenData.workflowRunId;
      if (runId) {
        const workflowData = await getWorkflow(runId);
        setWorkflow(workflowData);
      }
    } catch {
      // Silent refresh failure -- data will update on next SSE event
    }
  }, [screenId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!selectedRefreshId) {
      setSelectedRefresh(null);
      setSelectedRefreshClaims([]);
      setRefreshDetailError(null);
      setRefreshDetailLoading(false);
      return;
    }

    let cancelled = false;
    setRefreshDetailLoading(true);
    setRefreshDetailError(null);

    Promise.all([
      getScreenRefresh(screenId, selectedRefreshId),
      getScreenRefreshClaims(screenId, selectedRefreshId),
    ])
      .then(([detail, claims]) => {
        if (cancelled) return;
        setSelectedRefresh(detail);
        setSelectedRefreshClaims(claims.claims ?? []);
      })
      .catch((err) => {
        if (cancelled) return;
        setRefreshDetailError(err instanceof Error ? err.message : "Failed to load refresh detail.");
      })
      .finally(() => {
        if (cancelled) return;
        setRefreshDetailLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [screenId, selectedRefreshId]);

  // Auto-switch to Report tab when screen is COMPLETED (on first load)
  useEffect(() => {
    if (screen && !hasAutoSwitched) {
      if (screen.status === "COMPLETED") {
        setMainTab("report");
      }
      setHasAutoSwitched(true);
    }
  }, [screen, hasAutoSwitched]);

  // Workflow control handlers
  const handleAdvance = useCallback(async () => {
    if (!activeWorkflowRunId) return;
    try {
      await advanceWorkflow(activeWorkflowRunId);
      await refreshScreen();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to advance workflow");
    }
  }, [activeWorkflowRunId, refreshScreen]);

  const handlePause = useCallback(async () => {
    if (!activeWorkflowRunId) return;
    try {
      await pauseWorkflow(activeWorkflowRunId);
      await refreshScreen();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to pause workflow");
    }
  }, [activeWorkflowRunId, refreshScreen]);

  const handleCancel = useCallback(async () => {
    if (!activeWorkflowRunId) return;
    try {
      await cancelWorkflow(activeWorkflowRunId);
      await refreshScreen();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel workflow");
    }
  }, [activeWorkflowRunId, refreshScreen]);

  const handleRetry = useCallback(async () => {
    if (!activeWorkflowRunId) return;
    try {
      await retryWorkflow(activeWorkflowRunId);
      await refreshScreen();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to retry workflow");
    }
  }, [activeWorkflowRunId, refreshScreen]);

  // Auto-advance toggle handler
  const handleToggleAutoAdvance = useCallback(async (enabled: boolean) => {
    if (!activeWorkflowRunId) return;
    try {
      await toggleAutoAdvance(activeWorkflowRunId, enabled);
      await refreshScreen();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle auto-advance");
    }
  }, [activeWorkflowRunId, refreshScreen]);

  // Brief save handler
  const handleSaveBrief = useCallback(
    async (data: { hypothesis?: string; constraints?: Record<string, unknown>; frameworks?: string[] }) => {
      try {
        const updated = await updateScreenBrief(screenId, data);
        setScreen(updated);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to update brief");
      }
    },
    [screenId]
  );

  // Delete handler
  const handleDelete = useCallback(async () => {
    setActionLoading(true);
    try {
      await deleteScreen(screenId);
      router.push("/screens");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete screen");
      setShowDeleteConfirm(false);
    } finally {
      setActionLoading(false);
    }
  }, [screenId, router]);

  // Rerun handler
  const handleRerun = useCallback(async () => {
    setActionLoading(true);
    try {
      const result = await rerunScreen(screenId);
      await advanceWorkflow(result.workflowRunId);
      setShowRerunConfirm(false);
      await refreshScreen();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rerun screen");
      setShowRerunConfirm(false);
    } finally {
      setActionLoading(false);
    }
  }, [screenId, refreshScreen]);

  const handleCreateRefresh = useCallback(async (payload: { content: string; contentType: string; autoAdvance: boolean }) => {
    if (!screen || screen.status !== "COMPLETED" || !screen.isCertified) {
      setError("Screen must be completed and certified before refresh.");
      return;
    }

    setActionLoading(true);
    setRefreshWarning(null);
    setRefreshModalError(null);
    try {
      const idempotencyKey = typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `refresh-${screenId}-${Date.now()}`;
      const result = await createScreenRefresh(screenId, {
        content: payload.content,
        contentType: payload.contentType,
        autoAdvance: payload.autoAdvance,
        idempotencyKey,
      });
      setShowRefreshModal(false);
      if (result.warning) {
        setRefreshWarning(result.warning);
      }
      await advanceWorkflow(result.workflowRunId);
      await refreshScreen();
    } catch (err) {
      setRefreshModalError(err instanceof Error ? err.message : "Failed to start refresh");
    } finally {
      setActionLoading(false);
    }
  }, [screen, screenId, refreshScreen]);

  // Toggle Original Inputs (lazy-fetch on first open)
  const toggleInputs = useCallback(async () => {
    if (!showInputs && !inputs) {
      setInputsLoading(true);
      try {
        const data = await getScreenInputs(screenId);
        setInputs(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load inputs");
      } finally {
        setInputsLoading(false);
      }
    }
    setShowInputs((prev) => !prev);
  }, [showInputs, inputs, screenId]);

  // ─── Loading State ──────────────────────────────────────────────

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="h-5 w-32 bg-white/10 rounded animate-pulse" />
        <div className="flex items-center justify-between">
          <div className="h-7 w-64 bg-white/10 rounded animate-pulse" />
          <div className="h-6 w-24 bg-white/10 rounded-full animate-pulse" />
        </div>
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
          <div className="h-4 w-40 bg-white/10 rounded animate-pulse mb-4" />
          <div className="h-8 w-full bg-white/10 rounded animate-pulse mb-3" />
          <div className="h-4 w-3/4 bg-white/10 rounded animate-pulse" />
        </div>
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6">
          <div className="h-4 w-32 bg-white/10 rounded animate-pulse mb-4" />
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-4 w-full bg-white/10 rounded animate-pulse" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ─── Error State ────────────────────────────────────────────────

  if (error && !screen) {
    return (
      <div className="space-y-6 animate-fade-in">
        <Link
          href="/screens"
          className="inline-flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors duration-200"
        >
          <ArrowLeft size={16} />
          Back to Screens
        </Link>
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-6 py-8 text-center">
          <AlertCircle size={28} className="mx-auto text-red-400 mb-3" />
          <p className="text-sm font-medium text-red-300">Failed to load screen</p>
          <p className="text-xs text-red-400 mt-1">{error}</p>
          <button
            onClick={fetchData}
            className="mt-4 text-sm font-medium text-primary hover:text-primary-hover transition-colors duration-200"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (!screen) return null;

  const screenStatus = screen.status;
  const statusConfig = IST_STATUS_CONFIG[screenStatus] || IST_STATUS_CONFIG.PENDING;
  const isBriefEditable = effectiveStatus === "PAUSED";

  // ─── Render ─────────────────────────────────────────────────────

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back link */}
      <Link
        href="/screens"
        className="inline-flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors duration-200"
      >
        <ArrowLeft size={16} />
        Back to Screens
      </Link>

      {/* Page header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <h1 className="font-display text-2xl font-bold text-text-primary">
          {screen.name}
        </h1>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center px-3 py-1 rounded-full text-xs font-medium",
              statusConfig.bg,
              statusConfig.text
            )}
          >
            {statusConfig.label}
          </span>
          <ActionMenu
            items={[
              { label: "View Original Inputs", icon: Eye, onClick: toggleInputs },
              {
                label: "Refresh",
                icon: RefreshCw,
                onClick: () => {
                  setRefreshModalError(null);
                  setShowRefreshModal(true);
                },
                disabled: !screen.isCertified || screen.status !== "COMPLETED" || actionLoading,
              },
              { label: "Rerun", icon: RefreshCw, onClick: () => setShowRerunConfirm(true), disabled: !["COMPLETED", "FAILED", "PENDING"].includes(screen.status) },
              { label: "Delete", icon: Trash2, onClick: () => setShowDeleteConfirm(true), variant: "danger" },
            ]}
          />
        </div>
      </div>

      {/* Inline error banner for non-fatal errors */}
      {error && screen && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-5 py-3 flex items-start gap-3">
          <AlertCircle size={16} className="text-red-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {refreshWarning && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl px-5 py-3">
          <p className="text-xs text-amber-300">{refreshWarning}</p>
        </div>
      )}

      {screen.isRefreshing && (
        <div className="bg-sky-500/10 border border-sky-500/30 rounded-xl px-5 py-3">
          <p className="text-xs text-sky-300">
            Refresh in progress on workflow run {screen.activeWorkflowRunId}.
          </p>
        </div>
      )}

      {/* Workflow Progress Tracker */}
      {workflow && (
        <WorkflowProgressTracker
          workflowId={workflow.id}
          workflowType={workflow.workflowType}
          steps={effectiveSteps}
          status={effectiveStatus}
          currentPhase={effectivePhase}
          autoAdvance={workflow.autoAdvance}
          onAdvance={handleAdvance}
          onPause={handlePause}
          onCancel={handleCancel}
          onRetry={handleRetry}
          onToggleAutoAdvance={handleToggleAutoAdvance}
        />
      )}

      {/* Content Extraction Stats (if available) */}
      {screen.contentExtraction && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-4 py-3 text-center">
            <p className="text-lg font-bold text-text-primary font-mono">
              {screen.contentExtraction.totalClaims}
            </p>
            <p className="text-xs text-text-secondary">Total Claims</p>
          </div>
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-4 py-3 text-center">
            <p className="text-lg font-bold text-violet-400 font-mono">
              {screen.contentExtraction.claimsWithQuantAnchors}
            </p>
            <p className="text-xs text-text-secondary">Quant Anchors</p>
          </div>
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-4 py-3 text-center">
            <p className="text-lg font-bold text-sky-400 font-mono">
              {screen.contentExtraction.claimsWithTemporalMarkers}
            </p>
            <p className="text-xs text-text-secondary">Temporal Markers</p>
          </div>
          {screen.sourceBias && (
            <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-4 py-3 text-center">
              <p className={cn(
                "text-lg font-bold font-mono",
                screen.sourceBias.rating === "low" ? "text-emerald-400" :
                screen.sourceBias.rating === "medium" ? "text-amber-400" :
                "text-red-400"
              )}>
                {screen.sourceBias.rating}
              </p>
              <p className="text-xs text-text-secondary">Source Bias</p>
            </div>
          )}
        </div>
      )}

      {/* Main Tabs */}
      <div className="flex items-center gap-1 border-b border-border">
        <button
          onClick={() => setMainTab("report")}
          className={cn(
            "px-4 py-2.5 text-sm font-medium transition-colors duration-200",
            "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-t-lg",
            mainTab === "report"
              ? "text-primary border-b-2 border-primary"
              : "text-text-secondary hover:text-text-primary"
          )}
        >
          Report
        </button>
        <button
          onClick={() => setMainTab("working-data")}
          className={cn(
            "px-4 py-2.5 text-sm font-medium transition-colors duration-200",
            "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-t-lg",
            mainTab === "working-data"
              ? "text-primary border-b-2 border-primary"
              : "text-text-secondary hover:text-text-primary"
          )}
        >
          Working Data
        </button>
        <button
          onClick={() => setMainTab("personas")}
          className={cn(
            "px-4 py-2.5 text-sm font-medium transition-colors duration-200",
            "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-t-lg",
            mainTab === "personas"
              ? "text-primary border-b-2 border-primary"
              : "text-text-secondary hover:text-text-primary"
          )}
        >
          Personas
        </button>
      </div>

      {/* Report Tab */}
      {mainTab === "report" && (
        <InvestmentThesisReport screenId={screenId} />
      )}

      {/* Working Data Tab */}
      {mainTab === "working-data" && (
        <div className="space-y-4">
          {/* Sub-tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1">
            {WORKING_DATA_TABS.map((tab) => {
              const TabIcon = tab.icon;
              const isDisabled = effectivePhase < tab.minPhase;
              return (
                <button
                  key={tab.id}
                  onClick={() => !isDisabled && setWorkingDataTab(tab.id)}
                  disabled={isDisabled}
                  className={cn(
                    "inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg whitespace-nowrap",
                    "transition-colors duration-200",
                    "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1",
                    isDisabled
                      ? "text-text-tertiary/50 cursor-not-allowed"
                      : workingDataTab === tab.id
                        ? "bg-primary/10 text-primary"
                        : "text-text-secondary hover:text-text-primary hover:bg-white/5"
                  )}
                  aria-pressed={workingDataTab === tab.id}
                  title={isDisabled ? `Available after Phase ${tab.minPhase}` : undefined}
                >
                  <TabIcon size={14} />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Tab description */}
          {(() => {
            const activeTab = WORKING_DATA_TABS.find(t => t.id === workingDataTab);
            return activeTab ? (
              <p className="text-xs text-text-secondary leading-relaxed px-1">
                {activeTab.description}
              </p>
            ) : null;
          })()}

          {/* Sub-tab content */}
          {workingDataTab === "brief" && (
            <ScreeningBriefEditor
              screenId={screenId}
              brief={screen.screeningBrief}
              isEditable={isBriefEditable}
              onSave={handleSaveBrief}
            />
          )}

          {workingDataTab === "claims" && (
            <ClaimsTable screenId={screenId} />
          )}

          {workingDataTab === "bottleneck-map" && (
            <BottleneckMap screenId={screenId} />
          )}

          {workingDataTab === "demand-models" && (
            <DemandModels screenId={screenId} />
          )}

          {workingDataTab === "validation" && (
            <ValidationResults screenId={screenId} />
          )}

          {workingDataTab === "candidates" && (
            <EquityCandidates screenId={screenId} />
          )}

          {workingDataTab === "effects" && (
            <EffectsChains screenId={screenId} />
          )}

          {workingDataTab === "invariants" && (
            <InvariantChecklist screenId={screenId} />
          )}

          {workingDataTab === "dialectic" && (
            <DialecticView screenId={screenId} />
          )}

          {workingDataTab === "synthesis" && (
            <SynthesisView screenId={screenId} />
          )}

          {workingDataTab === "master-screen" && (
            <MasterScreenTable screenId={screenId} />
          )}

          {workingDataTab === "rotation" && (
            <RotationStrategy screenId={screenId} />
          )}

          {workingDataTab === "catalysts" && (
            <CatalystCalendar screenId={screenId} />
          )}

          {workingDataTab === "stress-tests" && (
            <StressTests screenId={screenId} />
          )}
        </div>
      )}

      {/* Personas Tab */}
      {mainTab === "personas" && (
        <div className="space-y-6">
          <PersonaLauncher targetType="ist_screen" targetId={screenId} />
          <PersonaHistory targetType="ist_screen" targetId={screenId} />
        </div>
      )}

      {/* HFRT Handoff Panel - visible when screen is certified */}
      {screen.isCertified && (
        <HandoffPanel screenId={screenId} isCertified={screen.isCertified} />
      )}

      {(refreshes.length > 0 || screen.refreshCount > 0) && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <RefreshHistory
            refreshes={refreshes}
            selectedRefreshId={selectedRefreshId}
            onSelectRefresh={setSelectedRefreshId}
          />
          <RefreshDelta
            detail={selectedRefresh}
            claims={selectedRefreshClaims}
            loading={refreshDetailLoading}
            error={refreshDetailError}
          />
        </div>
      )}

      {/* Original Inputs (collapsible) */}
      {showInputs && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5 space-y-3 animate-in">
          <button
            onClick={() => setShowInputs(false)}
            className="flex items-center gap-2 text-sm font-medium text-text-primary hover:text-primary transition-colors"
          >
            <ChevronUp size={16} />
            Original Inputs
          </button>
          {inputsLoading ? (
            <div className="flex items-center gap-2 text-text-tertiary text-sm">
              <Loader2 size={14} className="animate-spin" /> Loading...
            </div>
          ) : inputs ? (
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-text-tertiary">Name:</span>{" "}
                <span className="text-text-primary">{inputs.name}</span>
              </div>
              <div>
                <span className="text-text-tertiary">Content Type:</span>{" "}
                <span className="text-text-primary">{inputs.contentType}</span>
              </div>
              {inputs.hypothesis && (
                <div>
                  <span className="text-text-tertiary">Hypothesis:</span>{" "}
                  <span className="text-text-primary">{inputs.hypothesis}</span>
                </div>
              )}
              {inputs.rawContent && (
                <div>
                  <span className="text-text-tertiary block mb-1">Raw Content:</span>
                  <p className="text-text-secondary text-xs bg-white/5 rounded-lg p-3 max-h-40 overflow-y-auto whitespace-pre-wrap font-mono">
                    {inputs.rawContent.length > 500
                      ? inputs.rawContent.slice(0, 500) + "..."
                      : inputs.rawContent}
                  </p>
                </div>
              )}
              {inputs.constraints && Object.keys(inputs.constraints).length > 0 && (
                <div>
                  <span className="text-text-tertiary">Constraints:</span>{" "}
                  <span className="text-text-primary">{JSON.stringify(inputs.constraints)}</span>
                </div>
              )}
              {inputs.frameworks && inputs.frameworks.length > 0 && (
                <div>
                  <span className="text-text-tertiary">Frameworks:</span>{" "}
                  <span className="text-text-primary">{inputs.frameworks.join(", ")}</span>
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}

      {/* Frameworks Reference Panel (floating button + slide-out drawer) */}
      <FrameworksPanel />

      <RefreshModal
        open={showRefreshModal}
        loading={actionLoading}
        defaultContentType={screen.contentType}
        refreshCount={screen.refreshCount}
        error={refreshModalError}
        onClose={() => {
          setRefreshModalError(null);
          setShowRefreshModal(false);
        }}
        onSubmit={handleCreateRefresh}
      />

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={showDeleteConfirm}
        title="Delete Screen"
        message={`Are you sure you want to delete "${screen.name}"? All workflow data, claims, candidates, and reports will be permanently removed.`}
        confirmLabel="Delete"
        confirmVariant="danger"
        loading={actionLoading}
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteConfirm(false)}
      />

      {/* Rerun Confirmation */}
      <ConfirmDialog
        open={showRerunConfirm}
        title="Rerun Screen"
        message={`This will reset "${screen.name}" and restart the 22-step IST workflow from scratch. All existing results will be cleared.`}
        confirmLabel="Rerun"
        confirmVariant="primary"
        loading={actionLoading}
        onConfirm={handleRerun}
        onCancel={() => setShowRerunConfirm(false)}
      />
    </div>
  );
}
