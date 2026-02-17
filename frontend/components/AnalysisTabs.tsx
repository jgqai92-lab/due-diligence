"use client";

import { cn } from "@/lib/utils";
import {
  Globe,
  BarChart3,
  Search,
  DollarSign,
  Users,
  FileText,
  Table2,
  Landmark,
  ArrowLeftRight,
} from "lucide-react";

interface AnalysisTabsProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const TABS = [
  { id: "macro", label: "Macro", icon: Globe },
  { id: "fundamentals", label: "Fundamentals", icon: BarChart3 },
  { id: "forensic", label: "Forensic", icon: Search },
  { id: "valuation", label: "Valuation", icon: DollarSign },
  { id: "sentiment", label: "Sentiment", icon: Users },
  { id: "income-stmt", label: "Income Stmt", icon: Table2 },
  { id: "balance-sheet", label: "Balance Sheet", icon: Landmark },
  { id: "cash-flow", label: "Cash Flow", icon: ArrowLeftRight },
  { id: "ai-brief", label: "AI Brief", icon: FileText },
] as const;

export default function AnalysisTabs({
  activeTab,
  onTabChange,
}: AnalysisTabsProps) {
  return (
    <nav
      role="tablist"
      aria-label="Analysis sections"
      className="flex overflow-x-auto bg-black/30 rounded-lg p-[3px] gap-1"
    >
      {TABS.map((tab) => {
        const isActive = activeTab === tab.id;
        const Icon = tab.icon;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            aria-controls={`tabpanel-${tab.id}`}
            id={`tab-${tab.id}`}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-xs font-medium whitespace-nowrap transition-all duration-200 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50",
              isActive
                ? "bg-primary text-[#050810] font-semibold rounded-md shadow-sm"
                : "text-text-secondary hover:text-text-primary"
            )}
          >
            <Icon size={14} strokeWidth={isActive ? 2.2 : 1.8} />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
