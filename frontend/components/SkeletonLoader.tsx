"use client";

import { cn } from "@/lib/utils";

interface SkeletonLoaderProps { variant?: "card" | "table-row" | "score" | "report" | "text"; count?: number; }

function SkeletonBlock({ className }: { className?: string }) {
  return <div className={cn("animate-pulse bg-[rgba(136,146,176,0.1)] rounded-lg", className)} />;
}

export default function SkeletonLoader({ variant = "card", count = 1 }: SkeletonLoaderProps) {
  const items = Array.from({ length: count });

  if (variant === "text") {
    return (<div className="space-y-2">{items.map((_, i) => <SkeletonBlock key={i} className="h-4 w-full" />)}<SkeletonBlock className="h-4 w-3/4" /></div>);
  }
  if (variant === "score") {
    return (<div className="flex gap-4">{items.map((_, i) => (<div key={i} className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 flex-1"><SkeletonBlock className="h-4 w-32 mb-4" /><SkeletonBlock className="h-8 w-20 mb-2" /><SkeletonBlock className="h-3 w-40" /></div>))}</div>);
  }
  if (variant === "table-row") {
    return (<>{items.map((_, i) => (<div key={i} className="flex gap-4 p-3 border-b border-border/50"><SkeletonBlock className="h-4 w-16" /><SkeletonBlock className="h-4 w-12" /><SkeletonBlock className="h-4 w-20" /><SkeletonBlock className="h-4 w-20" /><SkeletonBlock className="h-4 w-16" /></div>))}</>);
  }
  if (variant === "report") {
    return (<div className="space-y-4 p-6 bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl"><SkeletonBlock className="h-6 w-48 mb-6" /><SkeletonBlock className="h-4 w-full" /><SkeletonBlock className="h-4 w-full" /><SkeletonBlock className="h-4 w-3/4" /><div className="h-4" /><SkeletonBlock className="h-4 w-full" /><SkeletonBlock className="h-4 w-5/6" /></div>);
  }
  return (<>{items.map((_, i) => (<div key={i} className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6"><SkeletonBlock className="h-4 w-32 mb-4" /><SkeletonBlock className="h-8 w-24 mb-2" /><SkeletonBlock className="h-3 w-48" /></div>))}</>);
}
