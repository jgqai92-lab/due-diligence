"use client";

import { cn } from "@/lib/utils";
import {
  Cpu,
  Heart,
  Landmark,
  ShoppingCart,
  Zap,
  Factory,
  HelpCircle,
} from "lucide-react";

// ─── Sector Config ─────────────────────────────────────────────────

const SECTOR_CONFIG: Record<
  string,
  { icon: typeof Cpu; bg: string; text: string; border: string }
> = {
  "information technology": {
    icon: Cpu,
    bg: "bg-blue-500/10",
    text: "text-blue-300",
    border: "border-blue-500/30",
  },
  technology: {
    icon: Cpu,
    bg: "bg-blue-500/10",
    text: "text-blue-300",
    border: "border-blue-500/30",
  },
  "communication services": {
    icon: Cpu,
    bg: "bg-indigo-500/10",
    text: "text-indigo-300",
    border: "border-indigo-500/30",
  },
  "health care": {
    icon: Heart,
    bg: "bg-rose-500/10",
    text: "text-rose-300",
    border: "border-rose-500/30",
  },
  healthcare: {
    icon: Heart,
    bg: "bg-rose-500/10",
    text: "text-rose-300",
    border: "border-rose-500/30",
  },
  financials: {
    icon: Landmark,
    bg: "bg-emerald-500/10",
    text: "text-emerald-300",
    border: "border-emerald-500/30",
  },
  "consumer discretionary": {
    icon: ShoppingCart,
    bg: "bg-amber-500/10",
    text: "text-amber-300",
    border: "border-amber-500/30",
  },
  "consumer staples": {
    icon: ShoppingCart,
    bg: "bg-orange-500/10",
    text: "text-orange-300",
    border: "border-orange-500/30",
  },
  energy: {
    icon: Zap,
    bg: "bg-yellow-500/10",
    text: "text-yellow-300",
    border: "border-yellow-500/30",
  },
  materials: {
    icon: Zap,
    bg: "bg-lime-500/10",
    text: "text-lime-300",
    border: "border-lime-500/30",
  },
  industrials: {
    icon: Factory,
    bg: "bg-slate-500/10",
    text: "text-slate-300",
    border: "border-slate-500/30",
  },
  utilities: {
    icon: Zap,
    bg: "bg-teal-500/10",
    text: "text-teal-300",
    border: "border-teal-500/30",
  },
  "real estate": {
    icon: Landmark,
    bg: "bg-purple-500/10",
    text: "text-purple-300",
    border: "border-purple-500/30",
  },
};

const DEFAULT_CONFIG = {
  icon: HelpCircle,
  bg: "bg-white/5",
  text: "text-text-primary",
  border: "border-border",
};

// ─── Props ──────────────────────────────────────────────────────────

interface SectorBadgeProps {
  sector: string | null;
  size?: "sm" | "md";
  className?: string;
}

// ─── Component ──────────────────────────────────────────────────────

export default function SectorBadge({
  sector,
  size = "sm",
  className,
}: SectorBadgeProps) {
  if (!sector) return null;

  const config =
    SECTOR_CONFIG[sector.toLowerCase()] ?? DEFAULT_CONFIG;
  const Icon = config.icon;

  const sizeClasses =
    size === "md"
      ? "px-3 py-1.5 text-xs gap-2"
      : "px-2 py-0.5 text-[10px] gap-1.5";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border font-medium",
        config.bg,
        config.text,
        config.border,
        sizeClasses,
        className
      )}
    >
      <Icon size={size === "md" ? 14 : 10} />
      {sector}
    </span>
  );
}
