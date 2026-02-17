"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { timeAgo } from "@/lib/utils";
import { listProjects, deleteProject, rerunProject } from "@/lib/api/hfrt";
import { advanceWorkflow } from "@/lib/api/workflows";
import type { HFRTProjectListItem, HFRTProjectStatus } from "@/types/hfrt";
import { HFRT_PHASE_NAMES } from "@/types/hfrt";
import { Plus, Search, AlertCircle, RefreshCw, Trash2 } from "lucide-react";
import ActionMenu from "@/components/ActionMenu";
import type { ActionMenuItem } from "@/components/ActionMenu";
import ConfirmDialog from "@/components/ConfirmDialog";

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

// ─── Status Badge ───────────────────────────────────────────────────

function StatusBadge({ status }: { status: HFRTProjectStatus }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.PENDING;
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        config.bg,
        config.text
      )}
    >
      {config.label}
    </span>
  );
}

// ─── Skeleton Card ──────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5 animate-pulse">
      <div className="flex items-start justify-between mb-3">
        <div className="h-5 w-32 bg-white/10 rounded" />
        <div className="h-5 w-20 bg-white/10 rounded-full" />
      </div>
      <div className="h-4 w-48 bg-white/10 rounded mb-2" />
      <div className="h-3 w-56 bg-white/10 rounded" />
    </div>
  );
}

// ─── Project Card ────────────────────────────────────────────────────

function ProjectCard({
  project,
  onClick,
  onRerun,
  onDelete,
}: {
  project: HFRTProjectListItem;
  onClick: () => void;
  onRerun: () => void;
  onDelete: () => void;
}) {
  const phaseName = HFRT_PHASE_NAMES[project.currentPhase] || `Phase ${project.currentPhase}`;
  const canRerun = ["COMPLETED", "FAILED", "PENDING", "NOT_INVESTABLE"].includes(project.status);

  const menuItems: ActionMenuItem[] = [
    {
      label: "Rerun",
      icon: RefreshCw,
      onClick: onRerun,
      disabled: !canRerun,
    },
    {
      label: "Delete",
      icon: Trash2,
      onClick: onDelete,
      variant: "danger",
    },
  ];

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5 hover:bg-white/5 hover:border-border hover:-translate-y-1 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 group"
      aria-label={`View research: ${project.ticker}`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-3 mr-2">
          <span className="text-lg font-bold text-text-primary group-hover:text-primary transition-colors duration-200">
            {project.ticker}
          </span>
          {project.companyName && (
            <span className="text-sm text-text-secondary">{project.companyName}</span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <StatusBadge status={project.status} />
          <ActionMenu items={menuItems} />
        </div>
      </div>

      <p className="text-xs text-text-secondary mb-1.5">
        {project.templatesPopulated}/15 templates
        {project.sector && <> &middot; {project.sector}</>}
        {project.recommendation && (
          <> &middot; <span className="font-medium">{project.recommendation}</span></>
        )}
      </p>

      <p className="text-xs text-text-tertiary">
        Phase {project.currentPhase}: {phaseName}
        {" \u00B7 "}
        Updated {timeAgo(project.updatedAt)}
      </p>
    </button>
  );
}

// ─── Page ───────────────────────────────────────────────────────────

export default function ResearchListPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<HFRTProjectListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action state
  const [deleteTarget, setDeleteTarget] = useState<HFRTProjectListItem | null>(null);
  const [rerunTarget, setRerunTarget] = useState<HFRTProjectListItem | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listProjects({ limit: 50 })
      .then((result) => {
        setProjects(result.projects);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load projects");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  // Delete handler
  const handleDelete = async () => {
    if (!deleteTarget) return;
    setActionLoading(true);
    try {
      await deleteProject(deleteTarget.id);
      setProjects((prev) => prev.filter((p) => p.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete project");
      setDeleteTarget(null);
    } finally {
      setActionLoading(false);
    }
  };

  // Rerun handler
  const handleRerun = async () => {
    if (!rerunTarget) return;
    setActionLoading(true);
    try {
      const result = await rerunProject(rerunTarget.id);
      await advanceWorkflow(result.workflowRunId);
      setRerunTarget(null);
      router.push(`/research/${rerunTarget.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rerun project");
      setRerunTarget(null);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between animate-in">
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">
            Equity Research
          </h1>
          <p className="text-sm text-text-secondary mt-0.5">
            Deep HFRT research pipeline — from idea screen to investment memo
          </p>
        </div>
        <button
          onClick={() => router.push("/research/new")}
          className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-[#050810] bg-primary rounded-lg hover:bg-primary-hover active:bg-primary-active hover:-translate-y-0.5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 shadow-sm"
          aria-label="New research project"
        >
          <Plus size={16} />
          New Research
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-5 py-4 flex items-start gap-3">
          <AlertCircle size={18} className="text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-300">Failed to load projects</p>
            <p className="text-xs text-red-400 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && projects.length === 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-16 text-center">
          <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
            <Search size={28} className="text-text-tertiary" />
          </div>
          <h2 className="text-lg font-semibold text-text-primary mb-1">
            No research projects yet
          </h2>
          <p className="text-sm text-text-secondary max-w-md mx-auto mb-6">
            Start a new equity research project by entering a ticker symbol.
            The HFRT pipeline will run a 5-phase analysis from idea screen through
            investment memo.
          </p>
          <button
            onClick={() => router.push("/research/new")}
            className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-[#050810] bg-primary rounded-lg hover:bg-primary-hover active:bg-primary-active hover:-translate-y-0.5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 shadow-sm"
          >
            <Plus size={16} />
            Start Your First Research
          </button>
        </div>
      )}

      {/* Project list */}
      {!loading && !error && projects.length > 0 && (
        <div className="space-y-3">
          {projects.map((project, index) => (
            <div
              key={project.id}
              className="animate-in"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <ProjectCard
                project={project}
                onClick={() => router.push(`/research/${project.id}`)}
                onRerun={() => setRerunTarget(project)}
                onDelete={() => setDeleteTarget(project)}
              />
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Project"
        message={`Are you sure you want to delete the research project for "${deleteTarget?.ticker}"? All templates, filings, and analysis will be permanently removed.`}
        confirmLabel="Delete"
        confirmVariant="danger"
        loading={actionLoading}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* Rerun Confirmation */}
      <ConfirmDialog
        open={!!rerunTarget}
        title="Rerun Project"
        message={`This will reset the research project for "${rerunTarget?.ticker}" and restart the 23-step HFRT workflow from scratch. All templates and analysis will be cleared.`}
        confirmLabel="Rerun"
        confirmVariant="primary"
        loading={actionLoading}
        onConfirm={handleRerun}
        onCancel={() => setRerunTarget(null)}
      />
    </div>
  );
}
