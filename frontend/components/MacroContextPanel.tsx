"use client";

import type { CompanyProfile } from "@/types/analysis";
import { cn, formatLargeNumber } from "@/lib/utils";
import { Building2, Users, Globe, Layers } from "lucide-react";
import MetricGrid, { type MetricGridItem } from "./MetricGrid";

interface MacroContextPanelProps {
  companyProfile: CompanyProfile;
  sectorCategory: string;
}

function getSectorBadge(sectorCategory: string): { label: string; colorClass: string; bgClass: string } {
  const map: Record<string, { label: string; colorClass: string; bgClass: string }> = {
    SAAS: { label: "SaaS / Cloud", colorClass: "text-accent-purple", bgClass: "bg-accent-purple/10 border-accent-purple/30" },
    FINANCIAL: { label: "Financial Services", colorClass: "text-info", bgClass: "bg-info/10 border-info/30" },
    REIT: { label: "Real Estate / REIT", colorClass: "text-warning", bgClass: "bg-warning/10 border-warning/30" },
    ENERGY: { label: "Energy", colorClass: "text-bear", bgClass: "bg-bear/10 border-bear/30" },
    HEALTHCARE: { label: "Healthcare", colorClass: "text-bull", bgClass: "bg-bull/10 border-bull/30" },
    INDUSTRIAL: { label: "Industrial", colorClass: "text-text-secondary", bgClass: "bg-background border-border" },
    CONSUMER: { label: "Consumer", colorClass: "text-warning", bgClass: "bg-warning/10 border-warning/30" },
    GENERAL: { label: "General", colorClass: "text-text-secondary", bgClass: "bg-background border-border" },
  };
  return map[sectorCategory] || { label: sectorCategory, colorClass: "text-text-secondary", bgClass: "bg-background border-border" };
}

function formatEmployees(count: number | null): string {
  if (count == null) return "N/A";
  if (count >= 1000) return (count / 1000).toFixed(1).replace(/\.0$/, "") + "K";
  return count.toLocaleString();
}

export default function MacroContextPanel({ companyProfile, sectorCategory }: MacroContextPanelProps) {
  const sectorBadge = getSectorBadge(sectorCategory);
  const overviewMetrics: MetricGridItem[] = [{ label: "Market Cap", value: companyProfile.market_cap, format: "currency" }];

  return (
    <div role="tabpanel" id="tabpanel-macro" aria-labelledby="tab-macro" className="space-y-6">
      <div className="bg-surface rounded-xl shadow-card p-6">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="space-y-3">
            <h2 className="text-2xl font-display font-bold text-text-primary">{companyProfile.name || "Unknown Company"}</h2>
            <div className="flex flex-wrap items-center gap-4 text-sm text-text-secondary">
              <div className="flex items-center gap-1.5"><Globe size={14} className="text-text-tertiary" /><span>{companyProfile.sector || "N/A"}</span></div>
              <div className="flex items-center gap-1.5"><Layers size={14} className="text-text-tertiary" /><span>{companyProfile.industry || "N/A"}</span></div>
              <div className="flex items-center gap-1.5"><Building2 size={14} className="text-text-tertiary" /><span className="font-mono tabular-nums">{formatLargeNumber(companyProfile.market_cap)}</span></div>
              <div className="flex items-center gap-1.5"><Users size={14} className="text-text-tertiary" /><span className="font-mono tabular-nums">{formatEmployees(companyProfile.full_time_employees)} employees</span></div>
            </div>
          </div>
          <div className={cn("inline-flex items-center px-3 py-1.5 border text-[11px] font-medium rounded-lg", sectorBadge.bgClass, sectorBadge.colorClass)}>
            {sectorBadge.label}
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-xs font-medium tracking-wide text-text-secondary mb-3">Key Metrics</h3>
        <MetricGrid metrics={overviewMetrics} columns={3} />
      </div>

      <div className="bg-surface rounded-xl shadow-card p-6">
        <h3 className="text-xs font-medium tracking-wide text-text-secondary mb-3">Sector Context</h3>
        <p className="text-sm text-text-tertiary leading-relaxed">
          Sector-level macro context and thematic analysis will be available when the AI Brief tab is populated. This section will surface sector positioning, secular vs cyclical trends, regulatory considerations, and competitive dynamics relevant to{" "}
          <span className="text-text-primary font-medium">{companyProfile.name || "this company"}</span> within the{" "}
          <span className="text-text-primary font-medium">{companyProfile.sector || "its"} / {companyProfile.industry || "industry"}</span> space.
        </p>
      </div>
    </div>
  );
}
