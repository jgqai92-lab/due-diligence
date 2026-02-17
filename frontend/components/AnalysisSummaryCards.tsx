"use client";

import type { ComprehensiveAnalysis } from "@/types/analysis";
import {
  cn,
  getHealthScore,
  getForensicRisk,
  classifyValuation,
  classifyGrowth,
  getHealthScoreColor,
  getHealthScoreBorder,
  getForensicRiskColor,
  getForensicRiskBorder,
  getValuationZoneColor,
  getGrowthZoneColor,
  formatPercentFromDecimal,
} from "@/lib/utils";
import { TrendingUp, TrendingDown, Shield, Activity, DollarSign } from "lucide-react";

interface AnalysisSummaryCardsProps {
  comprehensiveAnalysis: ComprehensiveAnalysis;
}

const CARD_GRADIENTS = [
  "card-gradient-orange",
  "card-gradient-purple",
  "card-gradient-coral",
  "card-gradient-warm",
];

export default function AnalysisSummaryCards({
  comprehensiveAnalysis,
}: AnalysisSummaryCardsProps) {
  const healthScore = getHealthScore(
    comprehensiveAnalysis.profitability.net_margin.value,
    comprehensiveAnalysis.leverage.debt_to_equity.value,
    comprehensiveAnalysis.cash_flow.ocf_to_net_income.value
  );
  const healthColor = getHealthScoreColor(healthScore);

  const forensicRisk = getForensicRisk(
    comprehensiveAnalysis.beneish_m_score.composite,
    comprehensiveAnalysis.altman_z_score.standard.score
  );
  const riskColor = getForensicRiskColor(forensicRisk);

  const revenueGrowthValue = comprehensiveAnalysis.growth.revenue_growth_yoy.value;
  const growthZone = classifyGrowth(revenueGrowthValue);
  const growthColor = getGrowthZoneColor(growthZone);
  const growthIsPositive = revenueGrowthValue != null && revenueGrowthValue >= 0;

  const peValue = comprehensiveAnalysis.valuation.pe_trailing.value;
  const valuationZone = classifyValuation(peValue);
  const valuationColor = getValuationZoneColor(valuationZone);
  const valuationLabel = valuationZone.toUpperCase();

  const cards = [
    {
      title: "Financial Health",
      value: healthScore,
      color: healthColor,
      icon: Activity,
    },
    {
      title: "Forensic Risk",
      value: forensicRisk === "LOW" ? "Low Risk" : forensicRisk === "MEDIUM" ? "Medium Risk" : "High Risk",
      color: riskColor,
      icon: Shield,
    },
    {
      title: "Growth Profile",
      value: revenueGrowthValue != null ? formatPercentFromDecimal(revenueGrowthValue) + " Rev" : "N/A",
      color: growthColor,
      icon: growthIsPositive ? TrendingUp : TrendingDown,
    },
    {
      title: "Valuation",
      value: valuationLabel,
      color: valuationColor,
      icon: DollarSign,
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={card.title}
            className={cn(
              "rounded-xl p-5 bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border",
              "hover:-translate-y-1 hover:border-primary hover:shadow-[0_12px_40px_rgba(255,77,77,0.15)] transition-all duration-200",
              CARD_GRADIENTS[idx % CARD_GRADIENTS.length]
            )}
          >
            <div className="flex items-center gap-2 mb-3">
              <Icon size={16} className="text-text-secondary" />
              <h4 className="text-[11px] font-medium tracking-wide text-text-secondary">
                {card.title}
              </h4>
            </div>
            <div className={cn("text-xl font-bold font-mono", card.color)}>
              {card.value}
            </div>
          </div>
        );
      })}
    </div>
  );
}
