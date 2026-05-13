"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { getProject, getTemplates, deleteProject, rerunProject } from "@/lib/api/hfrt";
import { getWorkflow, advanceWorkflow, pauseWorkflow, cancelWorkflow, retryWorkflow, toggleAutoAdvance } from "@/lib/api/workflows";
import { useWorkflowSSE } from "@/hooks/useWorkflowSSE";
import WorkflowProgressTracker from "@/components/workflow/WorkflowProgressTracker";
import IdeaScreenPanel from "@/components/hfrt/IdeaScreenPanel";
import CompanyOverview from "@/components/hfrt/CompanyOverview";
import BusinessModelPanel from "@/components/hfrt/BusinessModelPanel";
import CompetitivePosition from "@/components/hfrt/CompetitivePosition";
import IndustryAnalysis from "@/components/hfrt/IndustryAnalysis";
import FinancialAnalysis from "@/components/hfrt/FinancialAnalysis";
import ValuationPanel from "@/components/hfrt/ValuationPanel";
import ManagementAssessment from "@/components/hfrt/ManagementAssessment";
import RiskAnalysis from "@/components/hfrt/RiskAnalysis";
import QualityOfEarnings from "@/components/hfrt/QualityOfEarnings";
import CatalystAnalysis from "@/components/hfrt/CatalystAnalysis";
import InvestmentThesis from "@/components/hfrt/InvestmentThesis";
import BullBearView from "@/components/hfrt/BullBearView";
import InvestmentMemo from "@/components/hfrt/InvestmentMemo";
import InvariantChecklist from "@/components/hfrt/InvariantChecklist";
import type { HFRTProjectDetail, HFRTProjectStatus, HFRTTemplate } from "@/types/hfrt";
import { HFRT_TEMPLATE_NAMES } from "@/types/hfrt";
import type { WorkflowDetail, WorkflowStatus, WorkflowStep } from "@/types/workflow";
import { ArrowLeft, AlertCircle, FileText, BarChart3, Target, Shield, Scale, BookOpen, TrendingUp, DollarSign, Users, AlertTriangle, CheckCircle, Flame, Lightbulb, ScrollText, Layers, RefreshCw, Trash2 } from "lucide-react";
import ActionMenu from "@/components/ActionMenu";
import ConfirmDialog from "@/components/ConfirmDialog";
import PersonaLauncher from "@/components/persona/PersonaLauncher";
import PersonaHistory from "@/components/persona/PersonaHistory";

// ─── Status Badge Config ────────────────────────────────────────────

const STATUS_CONFIG: Record<HFRTProjectStatus, { bg: string; text: string; label: string }> = {
  PENDING:        { bg: "bg-white/10",         text: "text-text-secondary",  label: "Pending" },
  SCREENING:      { bg: "bg-sky-500/20",       text: "text-sky-400",         label: "Screening" },
  RESEARCHING:    { bg: "bg-violet-500/20",    text: "text-violet-400",      label: "Researching" },
  DUE_DILIGENCE:  { bg: "bg-amber-500/20",     text: "text-amber-400",       label: "Due Diligence" },
  DIALECTIC:      { bg: "bg-rose-500/20",      text: "text-rose-400",        label: "Dialectic" },
  SYNTHESIZING:   { bg: "bg-emerald-500/20",   text: "text-emerald-400",     label: "Synthesizing" },
  COMPLETED:      { bg: "bg-emerald-600",      text: "text-white",           label: "Completed" },
  FAILED:         { bg: "bg-red-600",          text: "text-white",           label: "Failed" },
  NOT_INVESTABLE: { bg: "bg-orange-500/20",    text: "text-orange-400",      label: "Not Investable" },
};

// ─── Template Tab Config ────────────────────────────────────────────

type TemplateTab = number; // 0-14

const TEMPLATE_TABS: { id: TemplateTab; label: string; icon: typeof FileText; minPhase: number }[] = [
  { id: 0,  label: "Idea Screen",        icon: Target,         minPhase: 1 },
  { id: 1,  label: "Company Overview",    icon: BookOpen,       minPhase: 2 },
  { id: 2,  label: "Business Model",      icon: BarChart3,      minPhase: 2 },
  { id: 3,  label: "Competitive Pos.",    icon: Shield,         minPhase: 2 },
  { id: 4,  label: "Industry",            icon: TrendingUp,     minPhase: 2 },
  { id: 5,  label: "Financials",          icon: DollarSign,     minPhase: 2 },
  { id: 6,  label: "Valuation",           icon: BarChart3,      minPhase: 2 },
  { id: 7,  label: "Management",          icon: Users,          minPhase: 3 },
  { id: 8,  label: "Risk",                icon: AlertTriangle,  minPhase: 3 },
  { id: 9,  label: "Earnings Quality",    icon: CheckCircle,    minPhase: 3 },
  { id: 10, label: "Catalysts",           icon: Flame,          minPhase: 5 },
  { id: 11, label: "Thesis",              icon: Lightbulb,      minPhase: 5 },
  { id: 12, label: "Bull/Bear Case",      icon: Scale,          minPhase: 4 },
];

// ─── Page ───────────────────────────────────────────────────────────

export default function ResearchDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = Number(params.id);

  // Project data
  const [project, setProject] = useState<HFRTProjectDetail | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowDetail | null>(null);
  const [templates, setTemplates] = useState<HFRTTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showRerunConfirm, setShowRerunConfirm] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Tab state
  const [mainTab, setMainTab] = useState<"memo" | "templates" | "personas">("templates");
  const [activeTemplate, setActiveTemplate] = useState<TemplateTab>(0);
  const [hasAutoSwitched, setHasAutoSwitched] = useState(false);

  // SSE
  const {
    workflowStatus: sseStatus,
    steps: sseSteps,
    reconnect: reconnectSSE,
  } = useWorkflowSSE({
    workflowId: project?.workflowRunId ?? null,
    onStepComplete: () => refreshData(),
    onWorkflowComplete: () => refreshData(),
    onCheckpoint: () => refreshData(),
    onWorkflowFailed: () => refreshData(),
  });

  const effectiveStatus: WorkflowStatus = sseStatus ?? workflow?.status ?? "PENDING";

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

  const effectivePhase = workflow?.currentPhase ?? project?.currentPhase ?? 0;

  // Fetch data
  const fetchData = useCallback(async () => {
    if (isNaN(projectId)) return;

    setLoading(true);
    setError(null);

    try {
      const projectData = await getProject(projectId);
      setProject(projectData);

      if (projectData.workflowRunId) {
        const workflowData = await getWorkflow(projectData.workflowRunId);
        setWorkflow(workflowData);
      }

      const templatesData = await getTemplates(projectId);
      setTemplates(templatesData.templates);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const refreshData = useCallback(async () => {
    try {
      const projectData = await getProject(projectId);
      setProject(projectData);
      if (projectData.workflowRunId) {
        const workflowData = await getWorkflow(projectData.workflowRunId);
        setWorkflow(workflowData);
      }
      const templatesData = await getTemplates(projectId);
      setTemplates(templatesData.templates);
    } catch {
      // Silent refresh
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-switch to memo when complete
  useEffect(() => {
    if (project && !hasAutoSwitched) {
      if (project.status === "COMPLETED") {
        setMainTab("memo");
        setActiveTemplate(14);
      }
      setHasAutoSwitched(true);
    }
  }, [project, hasAutoSwitched]);

  // Workflow controls
  const handleAdvance = useCallback(async () => {
    if (!project?.workflowRunId) return;
    try {
      await advanceWorkflow(project.workflowRunId);
      await refreshData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to advance workflow");
    }
  }, [project?.workflowRunId, refreshData]);

  const handlePause = useCallback(async () => {
    if (!project?.workflowRunId) return;
    try {
      await pauseWorkflow(project.workflowRunId);
      await refreshData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to pause workflow");
    }
  }, [project?.workflowRunId, refreshData]);

  const handleCancel = useCallback(async () => {
    if (!project?.workflowRunId) return;
    try {
      await cancelWorkflow(project.workflowRunId);
      await refreshData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel workflow");
    }
  }, [project?.workflowRunId, refreshData]);

  // Retry handler
  const handleRetry = useCallback(async () => {
    if (!project?.workflowRunId) return;
    try {
      await retryWorkflow(project.workflowRunId);
      await refreshData();
      reconnectSSE();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to retry workflow");
    }
  }, [project?.workflowRunId, refreshData, reconnectSSE]);

  // Auto-advance toggle
  const handleToggleAutoAdvance = useCallback(async (enabled: boolean) => {
    if (!project?.workflowRunId) return;
    try {
      await toggleAutoAdvance(project.workflowRunId, enabled);
      await refreshData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle auto-advance");
    }
  }, [project?.workflowRunId, refreshData]);

  // Delete handler
  const handleDelete = useCallback(async () => {
    setActionLoading(true);
    try {
      await deleteProject(projectId);
      router.push("/research");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete project");
      setShowDeleteConfirm(false);
    } finally {
      setActionLoading(false);
    }
  }, [projectId, router]);

  // Rerun handler
  const handleRerun = useCallback(async () => {
    setActionLoading(true);
    try {
      const result = await rerunProject(projectId);
      await advanceWorkflow(result.workflowRunId);
      setShowRerunConfirm(false);
      await refreshData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rerun project");
      setShowRerunConfirm(false);
    } finally {
      setActionLoading(false);
    }
  }, [projectId, refreshData]);

  // Get current template data
  const currentTemplate = templates.find((t) => t.templateNumber === activeTemplate);

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
          <div className="h-8 w-full bg-white/10 rounded animate-pulse" />
        </div>
      </div>
    );
  }

  // ─── Error State ────────────────────────────────────────────────

  if (error && !project) {
    return (
      <div className="space-y-6 animate-fade-in">
        <Link
          href="/research"
          className="inline-flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors duration-200"
        >
          <ArrowLeft size={16} />
          Back to Research
        </Link>
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-6 py-8 text-center">
          <AlertCircle size={28} className="mx-auto text-red-400 mb-3" />
          <p className="text-sm font-medium text-red-300">Failed to load project</p>
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

  if (!project) return null;

  const statusConfig = STATUS_CONFIG[project.status] || STATUS_CONFIG.PENDING;

  // ─── Render ─────────────────────────────────────────────────────

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back link */}
      <Link
        href="/research"
        className="inline-flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors duration-200"
      >
        <ArrowLeft size={16} />
        Back to Research
      </Link>

      {/* Page header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-display text-2xl font-bold text-text-primary">
              {project.ticker}
            </h1>
            {project.companyName && (
              <span className="text-sm text-text-secondary mt-1">{project.companyName}</span>
            )}
          </div>
          {project.sector && (
            <p className="text-xs text-text-tertiary mt-0.5">{project.sector} &middot; {project.exchange}</p>
          )}
        </div>
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
              { label: "Rerun", icon: RefreshCw, onClick: () => setShowRerunConfirm(true), disabled: !["COMPLETED", "FAILED", "PENDING", "NOT_INVESTABLE"].includes(project.status) },
              { label: "Delete", icon: Trash2, onClick: () => setShowDeleteConfirm(true), variant: "danger" },
            ]}
          />
        </div>
      </div>

      {/* IST Source Link */}
      {project.source === "IST_HANDOFF" && project.istScreenId && (
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <Layers size={14} />
          <span>From IST Screen:</span>
          <Link
            href={`/screens/${project.istScreenId}`}
            className="text-primary hover:text-primary-hover font-medium transition-colors"
          >
            Screen #{project.istScreenId}
          </Link>
        </div>
      )}

      {/* Inline error */}
      {error && project && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-5 py-3 flex items-start gap-3">
          <AlertCircle size={16} className="text-red-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {/* Quick stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-4 py-3 text-center">
          <p className="text-lg font-bold text-text-primary font-mono">
            {templates.filter((t) => t.status === "POPULATED").length}/15
          </p>
          <p className="text-xs text-text-secondary">Templates</p>
        </div>
        {project.marketCap != null && (
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-4 py-3 text-center">
            <p className="text-lg font-bold text-violet-400 font-mono">
              ${project.marketCap.toFixed(1)}B
            </p>
            <p className="text-xs text-text-secondary">Market Cap</p>
          </div>
        )}
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-4 py-3 text-center">
          <p className={cn(
            "text-lg font-bold font-mono",
            project.investable ? "text-emerald-400" : "text-red-400"
          )}>
            {project.investable ? "Yes" : "No"}
          </p>
          <p className="text-xs text-text-secondary">Investable</p>
        </div>
        {project.convictionScore != null && (
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-4 py-3 text-center">
            <p className="text-lg font-bold text-sky-400 font-mono">
              {(project.convictionScore * 100).toFixed(0)}%
            </p>
            <p className="text-xs text-text-secondary">Conviction</p>
          </div>
        )}
      </div>

      {/* Workflow Progress */}
      {workflow && (
        <WorkflowProgressTracker
          workflowId={workflow.id}
          workflowType="HFRT"
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

      {/* Main Tabs */}
      <div className="flex items-center gap-1 border-b border-border">
        <button
          onClick={() => setMainTab("memo")}
          className={cn(
            "px-4 py-2.5 text-sm font-medium transition-colors duration-200",
            "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-t-lg",
            mainTab === "memo"
              ? "text-primary border-b-2 border-primary"
              : "text-text-secondary hover:text-text-primary"
          )}
        >
          Investment Memo
        </button>
        <button
          onClick={() => setMainTab("templates")}
          className={cn(
            "px-4 py-2.5 text-sm font-medium transition-colors duration-200",
            "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-t-lg",
            mainTab === "templates"
              ? "text-primary border-b-2 border-primary"
              : "text-text-secondary hover:text-text-primary"
          )}
        >
          Research Templates
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

      {/* Memo Tab */}
      {mainTab === "memo" && (
        <div className="space-y-6">
          {(() => {
            const memoTemplate = templates.find((t) => t.templateNumber === 14);
            if (memoTemplate?.status === "POPULATED" && memoTemplate.data) {
              return <InvestmentMemo data={memoTemplate.data} />;
            }
            return (
              <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 text-center py-12 text-text-tertiary">
                <ScrollText size={32} className="mx-auto mb-3" />
                <p className="text-sm">Investment memo not yet generated.</p>
                <p className="text-xs mt-1">Complete all 5 phases to generate the final memo.</p>
              </div>
            );
          })()}

          {/* Invariant Checklist */}
          {(project.status === "COMPLETED" || project.status === "SYNTHESIZING") && (
            <InvariantChecklist projectId={projectId} />
          )}
        </div>
      )}

      {/* Templates Tab */}
      {mainTab === "templates" && (
        <div className="space-y-4">
          {/* Template sub-tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1">
            {TEMPLATE_TABS.map((tab) => {
              const TabIcon = tab.icon;
              const template = templates.find((t) => t.templateNumber === tab.id);
              const isPopulated = template?.status === "POPULATED";
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTemplate(tab.id)}
                  className={cn(
                    "inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg whitespace-nowrap",
                    "transition-colors duration-200",
                    "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1",
                    activeTemplate === tab.id
                      ? "bg-primary/10 text-primary"
                      : isPopulated
                        ? "text-text-primary hover:bg-white/5"
                        : "text-text-tertiary hover:text-text-secondary hover:bg-white/5"
                  )}
                  aria-pressed={activeTemplate === tab.id}
                >
                  <TabIcon size={14} />
                  {tab.label}
                  {isPopulated && (
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Template content */}
          {(() => {
            // Handle populating/empty states universally
            if (activeTemplate !== 0 && currentTemplate?.status === "POPULATING") {
              return (
                <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 text-center py-12 text-text-tertiary">
                  <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                  <p className="text-sm">Generating {HFRT_TEMPLATE_NAMES[activeTemplate]}...</p>
                </div>
              );
            }

            if (activeTemplate !== 0 && (!currentTemplate || currentTemplate.status !== "POPULATED" || !currentTemplate.data)) {
              return (
                <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 text-center py-12 text-text-tertiary">
                  <FileText size={32} className="mx-auto mb-3" />
                  <p className="text-sm">{HFRT_TEMPLATE_NAMES[activeTemplate]} not yet populated.</p>
                  <p className="text-xs mt-1">This template will be filled during the research pipeline.</p>
                </div>
              );
            }

            // Route to dedicated components
            switch (activeTemplate) {
              case 0:
                return <IdeaScreenPanel projectId={projectId} template={currentTemplate ?? null} />;
              case 1:
                return <CompanyOverview data={currentTemplate!.data!} />;
              case 2:
                return <BusinessModelPanel data={currentTemplate!.data!} />;
              case 3:
                return <CompetitivePosition data={currentTemplate!.data!} />;
              case 4:
                return <IndustryAnalysis data={currentTemplate!.data!} />;
              case 5:
                return <FinancialAnalysis data={currentTemplate!.data!} />;
              case 6:
                return <ValuationPanel data={currentTemplate!.data!} />;
              case 7:
                return <ManagementAssessment data={currentTemplate!.data!} />;
              case 8:
                return <RiskAnalysis data={currentTemplate!.data!} />;
              case 9:
                return <QualityOfEarnings data={currentTemplate!.data!} />;
              case 10:
                return <CatalystAnalysis data={currentTemplate!.data!} />;
              case 11:
                return <InvestmentThesis data={currentTemplate!.data!} />;
              case 12:
                return <BullBearView projectId={projectId} />;
              default:
                return null;
            }
          })()}
        </div>
      )}

      {/* Personas Tab */}
      {mainTab === "personas" && (
        <div className="space-y-6">
          <PersonaLauncher targetType="hfrt_project" targetId={projectId} />
          <PersonaHistory targetType="hfrt_project" targetId={projectId} />
        </div>
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={showDeleteConfirm}
        title="Delete Project"
        message={`Are you sure you want to delete the research project for "${project.ticker}"? All templates, filings, and analysis will be permanently removed.`}
        confirmLabel="Delete"
        confirmVariant="danger"
        loading={actionLoading}
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteConfirm(false)}
      />

      {/* Rerun Confirmation */}
      <ConfirmDialog
        open={showRerunConfirm}
        title="Rerun Project"
        message={`This will reset the research project for "${project.ticker}" and restart the 23-step HFRT workflow from scratch. All templates and analysis will be cleared.`}
        confirmLabel="Rerun"
        confirmVariant="primary"
        loading={actionLoading}
        onConfirm={handleRerun}
        onCancel={() => setShowRerunConfirm(false)}
      />
    </div>
  );
}
