"use client";

import type { GrowthMetrics, ValuationMetrics, ShareholderMetrics, MetricComponent as MC } from "@/types/analysis";
import { cn, formatPercentFromDecimal, formatMultiple, classifyGrowth, classifyValuation, getGrowthZoneColor, getValuationZoneColor } from "@/lib/utils";
import CitationTooltip from "./CitationTooltip";

interface ValuationGrowthPanelProps {
  growth: GrowthMetrics;
  valuation: ValuationMetrics;
  shareholderReturns: ShareholderMetrics;
}

interface MetricRow { label: string; metric: MC; format: "percent" | "multiple"; colorClass?: string; }

function formatValue(metric: MC, format: "percent" | "multiple"): string {
  if (metric.value == null) return "N/A";
  return format === "percent" ? formatPercentFromDecimal(metric.value) : formatMultiple(metric.value);
}

function MetricItem({ label, metric, format, colorClass }: MetricRow) {
  return (
    <div className="flex justify-between items-center py-2.5 border-b border-border/50 last:border-b-0">
      <span className="text-xs text-text-secondary">{label}</span>
      <CitationTooltip citation={metric.citation}>
        <span className={cn("font-mono text-sm font-medium", colorClass ?? "text-text-primary")}>{formatValue(metric, format)}</span>
      </CitationTooltip>
    </div>
  );
}

function SubSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface rounded-xl shadow-card">
      <div className="px-6 py-4 border-b border-border/50">
        <h4 className="text-xs font-medium tracking-wide text-text-secondary">{title}</h4>
      </div>
      <div className="px-6 py-3">{children}</div>
    </div>
  );
}

export default function ValuationGrowthPanel({ growth, valuation, shareholderReturns }: ValuationGrowthPanelProps) {
  const peColor = getValuationZoneColor(classifyValuation(valuation.pe_trailing.value));

  return (
    <div className="space-y-4">
      <SubSection title="Growth Trajectory">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6">
          <MetricItem label="Revenue Growth YoY" metric={growth.revenue_growth_yoy} format="percent" colorClass={getGrowthZoneColor(classifyGrowth(growth.revenue_growth_yoy.value))} />
          <MetricItem label="Earnings Growth YoY" metric={growth.earnings_growth_yoy} format="percent" colorClass={getGrowthZoneColor(classifyGrowth(growth.earnings_growth_yoy.value))} />
          <MetricItem label="FCF Growth YoY" metric={growth.fcf_growth_yoy} format="percent" colorClass={getGrowthZoneColor(classifyGrowth(growth.fcf_growth_yoy.value))} />
          <MetricItem label="Revenue CAGR (3Y)" metric={growth.revenue_cagr_3y} format="percent" colorClass={getGrowthZoneColor(classifyGrowth(growth.revenue_cagr_3y.value))} />
        </div>
      </SubSection>
      <SubSection title="Valuation Multiples">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6">
          <MetricItem label="P/E (Trailing)" metric={valuation.pe_trailing} format="multiple" colorClass={peColor} />
          <MetricItem label="P/E (Forward)" metric={valuation.pe_forward} format="multiple" colorClass={getValuationZoneColor(classifyValuation(valuation.pe_forward.value))} />
          <MetricItem label="EV / EBITDA" metric={valuation.ev_to_ebitda} format="multiple" />
          <MetricItem label="Price / FCF" metric={valuation.price_to_fcf} format="multiple" />
          <MetricItem label="Price / Sales" metric={valuation.price_to_sales} format="multiple" />
          <MetricItem label="PEG Ratio" metric={valuation.peg_ratio} format="multiple" />
        </div>
      </SubSection>
      <SubSection title="Shareholder Returns">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6">
          <MetricItem label="Dividend Yield" metric={shareholderReturns.dividend_yield} format="percent" />
          <MetricItem label="Payout Ratio" metric={shareholderReturns.payout_ratio} format="percent" />
        </div>
      </SubSection>
    </div>
  );
}
