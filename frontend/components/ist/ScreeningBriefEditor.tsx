"use client";

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import type { ISTScreenDetail } from "@/types/ist";
import { Pencil, Save, X, FileText, Target, Layers } from "lucide-react";

// ─── Props ──────────────────────────────────────────────────────────

interface ScreeningBriefEditorProps {
  screenId: number;
  brief: ISTScreenDetail["screeningBrief"];
  isEditable: boolean;
  onSave?: (data: {
    hypothesis?: string;
    constraints?: Record<string, unknown>;
    frameworks?: string[];
  }) => void;
}

// ─── Available Frameworks ───────────────────────────────────────────

const AVAILABLE_FRAMEWORKS = [
  "bottleneck_mapping",
  "demand_modeling",
  "forensic_accounting",
  "competitive_moat",
  "management_quality",
  "capital_allocation",
  "sector_dynamics",
];

// ─── Component ──────────────────────────────────────────────────────

export default function ScreeningBriefEditor({
  brief,
  isEditable,
  onSave,
}: ScreeningBriefEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [hypothesis, setHypothesis] = useState(brief?.hypothesis ?? "");
  const [constraintsJson, setConstraintsJson] = useState(
    brief?.constraints ? JSON.stringify(brief.constraints, null, 2) : "{}"
  );
  const [selectedFrameworks, setSelectedFrameworks] = useState<string[]>(
    brief?.frameworks ?? []
  );
  const [constraintsError, setConstraintsError] = useState<string | null>(null);

  const handleStartEditing = useCallback(() => {
    setHypothesis(brief?.hypothesis ?? "");
    setConstraintsJson(
      brief?.constraints ? JSON.stringify(brief.constraints, null, 2) : "{}"
    );
    setSelectedFrameworks(brief?.frameworks ?? []);
    setConstraintsError(null);
    setIsEditing(true);
  }, [brief]);

  const handleCancel = useCallback(() => {
    setIsEditing(false);
    setConstraintsError(null);
  }, []);

  const handleSave = useCallback(() => {
    let parsedConstraints: Record<string, unknown>;
    try {
      parsedConstraints = JSON.parse(constraintsJson);
    } catch {
      setConstraintsError("Invalid JSON. Please check the constraints format.");
      return;
    }

    onSave?.({
      hypothesis: hypothesis || undefined,
      constraints: parsedConstraints,
      frameworks: selectedFrameworks.length > 0 ? selectedFrameworks : undefined,
    });
    setIsEditing(false);
  }, [hypothesis, constraintsJson, selectedFrameworks, onSave]);

  const toggleFramework = useCallback((framework: string) => {
    setSelectedFrameworks((prev) =>
      prev.includes(framework)
        ? prev.filter((f) => f !== framework)
        : [...prev, framework]
    );
  }, []);

  // Empty brief state
  if (!brief && !isEditing) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl px-6 py-8 text-center">
        <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <FileText size={20} className="text-text-tertiary" />
        </div>
        <p className="text-sm font-medium text-text-primary">
          No screening brief yet
        </p>
        <p className="text-xs text-text-secondary mt-1">
          The screening brief will be generated during the content extraction phase.
        </p>
        {isEditable && (
          <button
            onClick={handleStartEditing}
            className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary bg-primary/10 rounded-lg hover:bg-primary/20 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          >
            <Pencil size={12} />
            Create Brief
          </button>
        )}
      </div>
    );
  }

  // Editing mode
  if (isEditing) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border border-primary/30 rounded-xl ring-2 ring-primary/10">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h3 className="text-sm font-semibold text-text-primary">
            Edit Screening Brief
          </h3>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCancel}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-secondary bg-white/10 rounded-lg hover:bg-white/10 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2"
              aria-label="Cancel editing"
            >
              <X size={12} />
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
              aria-label="Save screening brief"
            >
              <Save size={12} />
              Save Brief
            </button>
          </div>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Hypothesis */}
          <div>
            <label
              htmlFor="brief-hypothesis"
              className="block text-xs font-medium text-text-primary mb-1.5"
            >
              <Target size={12} className="inline mr-1" />
              Hypothesis
            </label>
            <textarea
              id="brief-hypothesis"
              value={hypothesis}
              onChange={(e) => setHypothesis(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 text-sm text-text-primary bg-[rgba(10,15,26,0.6)] border border-border rounded-lg placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-colors duration-200 resize-y"
              placeholder="Enter your investment hypothesis..."
            />
          </div>

          {/* Constraints */}
          <div>
            <label
              htmlFor="brief-constraints"
              className="block text-xs font-medium text-text-primary mb-1.5"
            >
              <Layers size={12} className="inline mr-1" />
              Constraints (JSON)
            </label>
            <textarea
              id="brief-constraints"
              value={constraintsJson}
              onChange={(e) => {
                setConstraintsJson(e.target.value);
                setConstraintsError(null);
              }}
              rows={4}
              className={cn(
                "w-full px-3 py-2 text-sm font-mono text-text-primary bg-[rgba(10,15,26,0.6)] placeholder:text-text-tertiary border rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-1 transition-colors duration-200 resize-y",
                constraintsError
                  ? "border-red-500/30 focus:ring-red-500"
                  : "border-border focus:ring-primary"
              )}
              placeholder='{"min_market_cap": 1000000000}'
            />
            {constraintsError && (
              <p className="mt-1 text-xs text-red-400">{constraintsError}</p>
            )}
          </div>

          {/* Frameworks */}
          <div>
            <span className="block text-xs font-medium text-text-primary mb-2">
              Frameworks
            </span>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_FRAMEWORKS.map((fw) => {
                const isSelected = selectedFrameworks.includes(fw);
                return (
                  <button
                    key={fw}
                    onClick={() => toggleFramework(fw)}
                    className={cn(
                      "px-3 py-1.5 text-xs font-medium rounded-lg transition-colors duration-200",
                      "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1",
                      isSelected
                        ? "bg-primary text-white"
                        : "bg-white/10 text-text-secondary hover:bg-white/10"
                    )}
                    aria-pressed={isSelected}
                  >
                    {fw.replace(/_/g, " ")}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Read-only display
  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <h3 className="text-sm font-semibold text-text-primary">
          Screening Brief
        </h3>
        {isEditable && (
          <button
            onClick={handleStartEditing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary bg-primary/10 rounded-lg hover:bg-primary/20 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
            aria-label="Edit screening brief"
          >
            <Pencil size={12} />
            Edit
          </button>
        )}
      </div>

      <div className="px-6 py-5 space-y-4">
        {/* Hypothesis */}
        {brief?.hypothesis && (
          <div>
            <div className="flex items-center gap-1.5 mb-1">
              <Target size={12} className="text-text-tertiary" />
              <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                Hypothesis
              </span>
            </div>
            <p className="text-sm text-text-primary leading-relaxed">
              {brief.hypothesis}
            </p>
          </div>
        )}

        {/* Content Type */}
        {brief?.contentType && (
          <div>
            <div className="flex items-center gap-1.5 mb-1">
              <FileText size={12} className="text-text-tertiary" />
              <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                Content Type
              </span>
            </div>
            <p className="text-sm text-text-primary">
              {brief.contentType.replace(/_/g, " ")}
            </p>
          </div>
        )}

        {/* Constraints */}
        {brief?.constraints && Object.keys(brief.constraints).length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-1">
              <Layers size={12} className="text-text-tertiary" />
              <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                Constraints
              </span>
            </div>
            <pre className="text-xs font-mono text-text-primary bg-white/5 rounded-lg px-3 py-2 overflow-x-auto">
              {JSON.stringify(brief.constraints, null, 2)}
            </pre>
          </div>
        )}

        {/* Frameworks */}
        {brief?.frameworks && brief.frameworks.length > 0 && (
          <div>
            <span className="text-xs font-medium text-text-secondary uppercase tracking-wider block mb-2">
              Frameworks
            </span>
            <div className="flex flex-wrap gap-1.5">
              {brief.frameworks.map((fw) => (
                <span
                  key={fw}
                  className="px-2.5 py-1 text-xs font-medium bg-violet-500/10 text-violet-400 rounded-lg"
                >
                  {fw.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
