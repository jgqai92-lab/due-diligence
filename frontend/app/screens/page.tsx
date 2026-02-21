"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { timeAgo } from "@/lib/utils";
import { listScreens, deleteScreen, rerunScreen } from "@/lib/api/ist";
import { advanceWorkflow } from "@/lib/api/workflows";
import type { ISTScreenListItem, ISTScreenStatus } from "@/types/ist";
import { Plus, Layers, AlertCircle, RefreshCw, Trash2 } from "lucide-react";
import ActionMenu from "@/components/ActionMenu";
import type { ActionMenuItem } from "@/components/ActionMenu";
import ConfirmDialog from "@/components/ConfirmDialog";

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

// ─── Phase Name Lookup ──────────────────────────────────────────────

const PHASE_NAMES: Record<number, string> = {
  0: "Not Started",
  1: "Content Extraction",
  2: "Thematic Analysis",
  3: "Equity Identification",
  4: "Dialectic Scrutiny",
  5: "Final Synthesis",
};

// ─── Status Badge ───────────────────────────────────────────────────

function StatusBadge({ status }: { status: ISTScreenStatus }) {
  const config = IST_STATUS_CONFIG[status] || IST_STATUS_CONFIG.PENDING;
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
        <div className="h-5 w-48 bg-white/10 rounded" />
        <div className="h-5 w-20 bg-white/10 rounded-full" />
      </div>
      <div className="h-4 w-40 bg-white/10 rounded mb-2" />
      <div className="h-3 w-56 bg-white/10 rounded" />
    </div>
  );
}

// ─── Screen Card ────────────────────────────────────────────────────

function ScreenCard({
  screen,
  onClick,
  onRerun,
  onDelete,
}: {
  screen: ISTScreenListItem;
  onClick: () => void;
  onRerun: () => void;
  onDelete: () => void;
}) {
  const phaseName = PHASE_NAMES[screen.currentPhase] || `Phase ${screen.currentPhase}`;
  const canRerun = ["COMPLETED", "FAILED", "PENDING"].includes(screen.status);

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
      aria-label={`View screen: ${screen.name}`}
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-sm font-semibold text-text-primary group-hover:text-primary transition-colors duration-200 line-clamp-1 mr-2">
          {screen.name}
        </h3>
        <div className="flex items-center gap-2 flex-shrink-0">
          <StatusBadge status={screen.status} />
          {screen.isRefreshing && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-500/20 text-sky-400">
              Refreshing
            </span>
          )}
          <ActionMenu items={menuItems} />
        </div>
      </div>

      <p className="text-xs text-text-secondary mb-1.5">
        {screen.claimCount} claims
        {screen.candidateCount > 0 && (
          <> &middot; {screen.candidateCount} candidates</>
        )}
        {screen.tier1Count > 0 && (
          <> &middot; {screen.tier1Count} Tier 1</>
        )}
        {screen.refreshCount > 0 && (
          <> &middot; {screen.refreshCount} refresh{screen.refreshCount > 1 ? "es" : ""}</>
        )}
      </p>

      <p className="text-xs text-text-tertiary">
        Phase {screen.currentPhase}: {phaseName}
        {" \u00B7 "}
        Updated {timeAgo(screen.updatedAt)}
      </p>
    </button>
  );
}

// ─── Page ───────────────────────────────────────────────────────────

export default function ScreensListPage() {
  const router = useRouter();
  const [screens, setScreens] = useState<ISTScreenListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action state
  const [deleteTarget, setDeleteTarget] = useState<ISTScreenListItem | null>(null);
  const [rerunTarget, setRerunTarget] = useState<ISTScreenListItem | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listScreens({ limit: 50 })
      .then((result) => {
        setScreens(result.screens);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load screens");
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
      await deleteScreen(deleteTarget.id);
      setScreens((prev) => prev.filter((s) => s.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete screen");
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
      const result = await rerunScreen(rerunTarget.id);
      await advanceWorkflow(result.workflowRunId);
      setRerunTarget(null);
      router.push(`/screens/${rerunTarget.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rerun screen");
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
            Investment Screens
          </h1>
          <p className="text-sm text-text-secondary mt-0.5">
            Create and manage IST content screening workflows
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push("/screens/syntheses")}
            className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-text-primary bg-white/10 border border-border rounded-lg hover:bg-white/15"
          >
            Syntheses
          </button>
          <button
            onClick={() => router.push("/screens/new")}
            className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-[#050810] bg-primary rounded-lg hover:bg-primary-hover active:bg-primary-active hover:-translate-y-0.5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 shadow-sm"
            aria-label="Create new screen"
          >
            <Plus size={16} />
            New Screen
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-5 py-4 flex items-start gap-3">
          <AlertCircle size={18} className="text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-300">Failed to load screens</p>
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
      {!loading && !error && screens.length === 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-16 text-center">
          <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
            <Layers size={28} className="text-text-tertiary" />
          </div>
          <h2 className="text-lg font-semibold text-text-primary mb-1">
            No screens yet
          </h2>
          <p className="text-sm text-text-secondary max-w-md mx-auto mb-6">
            Create your first investment screen to start analyzing content.
            Paste podcast transcripts, articles, or earnings calls to extract
            investable claims and identify equity candidates.
          </p>
          <button
            onClick={() => router.push("/screens/new")}
            className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-[#050810] bg-primary rounded-lg hover:bg-primary-hover active:bg-primary-active hover:-translate-y-0.5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 shadow-sm"
          >
            <Plus size={16} />
            Create Your First Screen
          </button>
        </div>
      )}

      {/* Screen list */}
      {!loading && !error && screens.length > 0 && (
        <div className="space-y-3">
          {screens.map((screen, index) => (
            <div
              key={screen.id}
              className="animate-in"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <ScreenCard
                screen={screen}
                onClick={() => router.push(`/screens/${screen.id}`)}
                onRerun={() => setRerunTarget(screen)}
                onDelete={() => setDeleteTarget(screen)}
              />
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Screen"
        message={`Are you sure you want to delete "${deleteTarget?.name}"? All workflow data, claims, candidates, and reports will be permanently removed.`}
        confirmLabel="Delete"
        confirmVariant="danger"
        loading={actionLoading}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* Rerun Confirmation */}
      <ConfirmDialog
        open={!!rerunTarget}
        title="Rerun Screen"
        message={`This will reset "${rerunTarget?.name}" and restart the 22-step IST workflow from scratch. All existing results will be cleared.`}
        confirmLabel="Rerun"
        confirmVariant="primary"
        loading={actionLoading}
        onConfirm={handleRerun}
        onCancel={() => setRerunTarget(null)}
      />
    </div>
  );
}
