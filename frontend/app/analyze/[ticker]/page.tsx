"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { analyzeTicker, refreshAnalysis, hasComprehensiveAnalysis, getComprehensiveAnalysis } from "@/lib/api";
import type { AnalysisResponse } from "@/types/analysis";
import BeneishMScorePanel from "@/components/BeneishMScorePanel";
import AltmanZScorePanel from "@/components/AltmanZScorePanel";
import SaaSMetricsPanel from "@/components/SaaSMetricsPanel";
import ForensicReport from "@/components/ForensicReport";
import DataFreshnessIndicator from "@/components/DataFreshnessIndicator";
import SkeletonLoader from "@/components/SkeletonLoader";
import AnalysisSummaryCards from "@/components/AnalysisSummaryCards";
import AnalysisTabs from "@/components/AnalysisTabs";
import MacroContextPanel from "@/components/MacroContextPanel";
import FundamentalsPanel from "@/components/FundamentalsPanel";
import ForensicPanel from "@/components/ForensicPanel";
import ValuationGrowthPanel from "@/components/ValuationGrowthPanel";
import SentimentPanel from "@/components/SentimentPanel";
import InvestmentBriefPanel from "@/components/InvestmentBriefPanel";
import SectorSpecificPanel from "@/components/SectorSpecificPanel";
import IncomeStatementPanel from "@/components/IncomeStatementPanel";
import BalanceSheetPanel from "@/components/BalanceSheetPanel";
import CashFlowPanel from "@/components/CashFlowPanel";
import { formatLargeNumber } from "@/lib/utils";
import Link from "next/link";
import { Search } from "lucide-react";

type TabId = "macro" | "fundamentals" | "forensic" | "valuation" | "sentiment" | "income-stmt" | "balance-sheet" | "cash-flow" | "ai-brief";

export default function AnalyzePage() {
  const params = useParams();
  const ticker = (params.ticker as string)?.toUpperCase();
  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("forensic");

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);
    analyzeTicker(ticker)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [ticker]);

  const handleRefresh = () => {
    setLoading(true);
    refreshAnalysis(ticker)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <SkeletonLoader variant="card" />
        <SkeletonLoader variant="score" count={4} />
        <SkeletonLoader variant="report" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-8 text-center animate-fade-in">
        <div className="text-bear text-lg font-semibold mb-2">Analysis Failed</div>
        <div className="text-text-secondary text-sm">{error}</div>
      </div>
    );
  }

  if (!data) return null;

  const { company_profile: profile, report, data_sources } = data;
  const comprehensive = getComprehensiveAnalysis(data);
  const isComprehensive = hasComprehensiveAnalysis(data);

  if (!isComprehensive) {
    const metrics = data.forensic_metrics;
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="bg-warning/10 border border-warning/30 text-text-primary px-4 py-3 rounded-xl flex items-center justify-between">
          <p className="text-sm">
            <span className="font-bold">Cached data from older version.</span>{' '}
            Click Refresh for the full comprehensive analysis with all metrics.
          </p>
          <button onClick={handleRefresh} className="text-sm font-bold text-primary hover:underline">
            Refresh Now
          </button>
        </div>

        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-display text-2xl font-bold">{ticker}</h1>
              <span className="text-text-secondary text-sm">{profile.name}</span>
            </div>
            <div className="flex gap-4 mt-1 text-xs text-text-tertiary">
              <span>{profile.sector}</span>
              <span>{profile.industry}</span>
              {profile.market_cap && <span className="font-mono">{formatLargeNumber(profile.market_cap)}</span>}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRefresh}
              className="flex items-center gap-1.5 px-4 py-2 text-xs text-text-secondary hover:text-primary bg-white/5 border border-border rounded-lg hover:bg-white/10 transition-all duration-200"
              aria-label="Refresh analysis"
            >
              Refresh
            </button>
            <DataFreshnessIndicator fetchedAt={data_sources.fetched_at} />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <BeneishMScorePanel data={metrics.beneish_m_score} />
          <AltmanZScorePanel data={metrics.altman_z_score} />
        </div>

        <SaaSMetricsPanel ruleOf40={metrics.rule_of_40} magicNumber={metrics.magic_number} />

        <ForensicReport
          markdown={report.markdown}
          generatedAt={report.generated_at}
          onRegenerate={handleRefresh}
        />
      </div>
    );
  }

  const isSaasSector = comprehensive!.sector_category === "SAAS";

  function renderActivePanel() {
    if (!comprehensive) return null;

    switch (activeTab) {
      case "macro":
        return <MacroContextPanel companyProfile={profile} sectorCategory={comprehensive.sector_category} />;
      case "fundamentals":
        return <FundamentalsPanel profitability={comprehensive.profitability} leverage={comprehensive.leverage} cashFlow={comprehensive.cash_flow} sectorSpecific={comprehensive.sector_specific} />;
      case "forensic":
        return (
          <div className="space-y-6">
            <ForensicPanel beneishMScore={comprehensive.beneish_m_score} altmanZScore={comprehensive.altman_z_score} />
            {isSaasSector && comprehensive.sector_specific && (
              <SectorSpecificPanel sectorSpecific={comprehensive.sector_specific} />
            )}
          </div>
        );
      case "valuation":
        return <ValuationGrowthPanel growth={comprehensive.growth} valuation={comprehensive.valuation} shareholderReturns={comprehensive.shareholder_returns} />;
      case "sentiment":
        return <SentimentPanel sentiment={comprehensive.sentiment} />;
      case "income-stmt":
        return <IncomeStatementPanel statement={data!.financial_statements?.income_statement ?? { periods: [], line_items: [] }} />;
      case "balance-sheet":
        return <BalanceSheetPanel statement={data!.financial_statements?.balance_sheet ?? { periods: [], line_items: [] }} />;
      case "cash-flow":
        return <CashFlowPanel statement={data!.financial_statements?.cash_flow ?? { periods: [], line_items: [] }} />;
      case "ai-brief":
        return <InvestmentBriefPanel report={report} onRegenerate={handleRefresh} dataTimestamp={data_sources.fetched_at} />;
      default:
        return null;
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-4 animate-in">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-display text-2xl font-bold">{ticker}</h1>
            <span className="text-text-secondary text-sm">{profile.name}</span>
          </div>
          <div className="flex gap-4 mt-1 text-xs text-text-tertiary">
            <span>{profile.sector}</span>
            <span>{profile.industry}</span>
            {profile.market_cap && <span className="font-mono">{formatLargeNumber(profile.market_cap)}</span>}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href={`/research/new?ticker=${ticker}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary hover:text-primary-hover bg-primary/5 hover:bg-primary/10 rounded-lg hover:-translate-y-0.5 transition-all duration-200"
          >
            <Search size={14} />
            Start Deep Research
          </Link>
          <button
            onClick={handleRefresh}
            className="flex items-center gap-1.5 px-4 py-2 text-xs text-text-secondary hover:text-primary bg-white/5 border border-border rounded-lg hover:bg-white/10 transition-all duration-200"
            aria-label="Refresh analysis"
          >
            Refresh
          </button>
          <DataFreshnessIndicator fetchedAt={data_sources.fetched_at} />
        </div>
      </div>

      <div className="animate-in-d1">
        <AnalysisSummaryCards comprehensiveAnalysis={comprehensive!} />
      </div>
      <div className="animate-in-d2">
        <AnalysisTabs activeTab={activeTab} onTabChange={(tab) => setActiveTab(tab as TabId)} />
      </div>

      <div className="animate-in-d3">
        {renderActivePanel()}
      </div>
    </div>
  );
}
