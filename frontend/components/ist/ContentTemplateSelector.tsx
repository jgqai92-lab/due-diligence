"use client";

import { cn } from "@/lib/utils";
import { FileText } from "lucide-react";
import { CONTENT_TEMPLATES } from "@/lib/ist/quality-checks";
import type { ContentType } from "@/lib/ist/quality-checks";

// ─── Props ──────────────────────────────────────────────────────────

interface ContentTemplateSelectorProps {
  contentType: ContentType;
  hasContent: boolean;
  onLoadTemplate: (template: string) => void;
}

// ─── Component ──────────────────────────────────────────────────────

export default function ContentTemplateSelector({
  contentType,
  hasContent,
  onLoadTemplate,
}: ContentTemplateSelectorProps) {
  const templateDef = CONTENT_TEMPLATES[contentType];
  if (!templateDef) return null;

  return (
    <div className="flex items-center justify-between px-3 py-2 bg-white/5 rounded-lg border border-dashed border-border">
      {/* Left side — label */}
      <div className="flex items-center gap-2 min-w-0">
        <FileText
          size={14}
          className="text-text-tertiary flex-shrink-0"
          aria-hidden="true"
        />
        <span className="text-xs text-text-secondary truncate">
          Use {templateDef.label} Template
        </span>
      </div>

      {/* Right side — action button */}
      <button
        type="button"
        onClick={() => onLoadTemplate(templateDef.template)}
        className={cn(
          "text-xs text-primary hover:text-primary-hover font-medium",
          "transition-colors duration-200 flex-shrink-0 ml-3",
          "focus:outline-none focus:underline"
        )}
        aria-label={`Load ${templateDef.label} template`}
      >
        Load Template
      </button>
    </div>
  );
}
