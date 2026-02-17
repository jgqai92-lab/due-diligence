"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import TickerSearchInput from "@/components/TickerSearchInput";
import { listScreens } from "@/lib/api/ist";
import { listProjects } from "@/lib/api/hfrt";
import { getPersonaAnalyses } from "@/lib/api/personas";
import { Layers, Search, Brain } from "lucide-react";

interface SummaryCounts {
  screens: number;
  projects: number;
  personas: number;
}

export default function HomePage() {
  const router = useRouter();
  const [counts, setCounts] = useState<SummaryCounts>({ screens: 0, projects: 0, personas: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCounts() {
      const results = await Promise.allSettled([
        listScreens({ limit: 1 }),
        listProjects({ limit: 1 }),
        getPersonaAnalyses({ limit: 1 }),
      ]);

      setCounts({
        screens: results[0].status === "fulfilled" ? results[0].value.total : 0,
        projects: results[1].status === "fulfilled" ? results[1].value.total : 0,
        personas: results[2].status === "fulfilled" ? results[2].value.total : 0,
      });
      setLoading(false);
    }

    fetchCounts();
  }, []);

  const handleSelect = (ticker: string) => {
    router.push(`/analyze/${ticker}`);
  };

  const summaryCards = [
    {
      label: "Active IST Screens",
      count: counts.screens,
      href: "/screens",
      icon: Layers,
      gradient: "card-gradient-coral",
    },
    {
      label: "Active HFRT Projects",
      count: counts.projects,
      href: "/research",
      icon: Search,
      gradient: "card-gradient-purple",
    },
    {
      label: "Persona Analyses",
      count: counts.personas,
      href: "/personas",
      icon: Brain,
      gradient: "card-gradient-orange",
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <h1 className="font-display text-4xl font-bold text-text-primary mb-2 tracking-tight gradient-text animate-in">
        The Skeptical Analyst
      </h1>
      <p className="text-text-secondary text-sm mb-8 animate-in-d1">
        Trust, but Verify (with Math)
      </p>

      <div className="w-full max-w-xl animate-in-d2">
        <TickerSearchInput onSelect={handleSelect} autoFocus />
      </div>

      {/* Summary Cards */}
      <div className="mt-8 w-full max-w-2xl grid grid-cols-1 sm:grid-cols-3 gap-4 animate-in-d3">
        {summaryCards.map((card) => {
          const Icon = card.icon;
          return (
            <Link
              key={card.label}
              href={card.href}
              className={`group relative p-5 rounded-xl shadow-card hover:shadow-card-hover hover:-translate-y-1 transition-all duration-200 ${card.gradient}`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-9 h-9 rounded-lg bg-white/20 flex items-center justify-center">
                  <Icon size={18} className="text-text-primary" />
                </div>
              </div>
              {loading ? (
                <div className="h-8 w-12 bg-white/30 rounded animate-pulse mb-1" />
              ) : (
                <p className="text-2xl font-bold text-text-primary font-mono">
                  {card.count}
                </p>
              )}
              <p className="text-xs text-text-secondary mt-0.5">{card.label}</p>
              <span className="inline-flex items-center gap-0.5 text-[11px] font-medium text-text-secondary group-hover:text-text-primary mt-2 transition-colors duration-200">
                View all &rarr;
              </span>
            </Link>
          );
        })}
      </div>

      <div className="mt-8 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 text-center animate-in-d4">
        {[
          { label: "Financial Health", desc: "Profitability & leverage", gradient: "card-gradient-orange" },
          { label: "Forensic Screening", desc: "Manipulation & bankruptcy risk", gradient: "card-gradient-purple" },
          { label: "Growth Analysis", desc: "Revenue & earnings trajectory", gradient: "card-gradient-coral" },
          { label: "Valuation", desc: "Multiples & pricing signals", gradient: "card-gradient-warm" },
          { label: "Sentiment", desc: "Analyst consensus & positioning", gradient: "card-gradient-orange" },
          { label: "AI Investment Brief", desc: "Due diligence narrative", gradient: "card-gradient-purple" },
        ].map((m) => (
          <div key={m.label} className={`p-4 rounded-xl shadow-card hover:shadow-card-hover hover:-translate-y-1 transition-all duration-200 ${m.gradient}`}>
            <div className="text-xs font-semibold text-text-primary mb-1">{m.label}</div>
            <div className="text-[11px] text-text-secondary">{m.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
