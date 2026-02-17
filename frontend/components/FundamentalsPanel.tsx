"use client";

import type { ProfitabilityMetrics, LeverageMetrics, CashFlowMetrics, SectorSpecificMetrics, MetricComponent } from "@/types/analysis";
import { classifyProfitability, classifyLeverage, classifyCashFlow, getProfitabilityZoneColor, getLeverageZoneColor, getCashFlowZoneColor } from "@/lib/utils";
import MetricGrid, { type MetricGridItem } from "./MetricGrid";
import ForensicScoreCard from "./ForensicScoreCard";

interface FundamentalsPanelProps {
  profitability: ProfitabilityMetrics;
  leverage: LeverageMetrics;
  cashFlow: CashFlowMetrics;
  sectorSpecific?: SectorSpecificMetrics | null;
}

function buildItem(label: string, mc: MetricComponent, format: MetricGridItem["format"], zoneColor?: string, interpretation?: string): MetricGridItem {
  return { label, value: mc.value, format, citation: mc.citation, zone: zoneColor, interpretation };
}

export default function FundamentalsPanel({ profitability, leverage, cashFlow, sectorSpecific }: FundamentalsPanelProps) {
  const profColor = getProfitabilityZoneColor(classifyProfitability(profitability.net_margin.value));
  const levColor = getLeverageZoneColor(classifyLeverage(leverage.debt_to_equity.value));
  const cfColor = getCashFlowZoneColor(classifyCashFlow(cashFlow.ocf_to_net_income.value));

  const profitabilityMetrics: MetricGridItem[] = [
    buildItem("Gross Margin", profitability.gross_margin, "percent", profColor),
    buildItem("Operating Margin", profitability.operating_margin, "percent", profColor),
    buildItem("Net Margin", profitability.net_margin, "percent", profColor),
    buildItem("ROE", profitability.roe, "percent", profColor),
    buildItem("ROA", profitability.roa, "percent", profColor),
    buildItem("ROIC", profitability.roic, "percent", profColor),
  ];

  const leverageMetrics: MetricGridItem[] = [
    buildItem("Debt / Equity", leverage.debt_to_equity, "ratio", levColor),
    buildItem("Interest Coverage", leverage.interest_coverage, "ratio", levColor),
    buildItem("Current Ratio", leverage.current_ratio, "ratio", levColor),
    buildItem("Quick Ratio", leverage.quick_ratio, "ratio", levColor),
    buildItem("Net Debt / EBITDA", leverage.net_debt_to_ebitda, "ratio", levColor),
  ];

  const cashFlowMetrics: MetricGridItem[] = [
    buildItem("FCF Yield", cashFlow.fcf_yield, "percent", cfColor),
    buildItem("OCF / Net Income", cashFlow.ocf_to_net_income, "ratio", cfColor),
    buildItem("FCF Margin", cashFlow.fcf_margin, "percent", cfColor),
    buildItem("CapEx / Revenue", cashFlow.capex_to_revenue, "ratio", cfColor),
  ];

  const sectorItems: { name: string; value: number | null; citation: MetricComponent["citation"] }[] = [];
  if (sectorSpecific) {
    for (const [key, mc] of Object.entries(sectorSpecific.metrics)) {
      sectorItems.push({ name: key.toUpperCase().replace(/_/g, " "), value: mc.value, citation: mc.citation });
    }
  }

  return (
    <div role="tabpanel" id="tabpanel-fundamentals" aria-labelledby="tab-fundamentals" className="space-y-8">
      <section>
        <h3 className="text-xs font-medium tracking-wide text-text-secondary mb-3">Profitability & Efficiency</h3>
        <MetricGrid metrics={profitabilityMetrics} columns={3} />
      </section>
      <section>
        <h3 className="text-xs font-medium tracking-wide text-text-secondary mb-3">Leverage & Solvency</h3>
        <MetricGrid metrics={leverageMetrics} columns={3} />
      </section>
      <section>
        <h3 className="text-xs font-medium tracking-wide text-text-secondary mb-3">Cash Flow Quality</h3>
        <MetricGrid metrics={cashFlowMetrics} columns={4} />
      </section>
      {sectorSpecific && sectorItems.length > 0 && (
        <section>
          <h3 className="text-xs font-medium tracking-wide text-text-secondary mb-3">{sectorSpecific.label} — Sector Metrics</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sectorItems.map((item) => (
              <ForensicScoreCard key={item.name} title={item.name} score={item.value} zone={null} interpretation={sectorSpecific.interpretations?.[item.name.toLowerCase().replace(/ /g, "_")] || ""} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
