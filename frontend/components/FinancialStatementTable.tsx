"use client";

import type { FinancialStatement } from "@/types/analysis";
import { formatStatementValue, formatFiscalPeriod, cn } from "@/lib/utils";

interface FinancialStatementTableProps { statement: FinancialStatement; title: string; }

const KEY_ROW_LABELS = new Set([
  "Total Revenue", "Revenue", "Gross Profit", "Operating Income", "EBIT", "EBITDA",
  "Pretax Income", "Net Income", "Net Income Common Stockholders", "Total Assets",
  "Total Liabilities Net Minority Interest", "Total Liabilities",
  "Total Equity Gross Minority Interest", "Stockholders Equity", "Total Stockholders Equity",
  "Total Capitalization", "Operating Cash Flow", "Free Cash Flow", "Capital Expenditure",
  "Cash And Cash Equivalents",
]);

export default function FinancialStatementTable({ statement, title }: FinancialStatementTableProps) {
  if (!statement || !statement.periods || statement.periods.length === 0 || !statement.line_items || statement.line_items.length === 0) {
    return <div role="tabpanel" className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl shadow-card p-8 text-center"><p className="text-text-secondary text-sm">No data available for this statement.</p></div>;
  }

  const { periods, line_items } = statement;

  return (
    <div role="tabpanel" className="space-y-3">
      <div>
        <h2 className="font-display text-xl font-bold text-text-primary">{title}</h2>
        <p className="text-[11px] font-medium text-text-tertiary mt-1">($ in millions)</p>
      </div>
      <div className="overflow-x-auto rounded-xl shadow-card bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border">
        <table className="w-full border-collapse min-w-[600px]">
          <thead>
            <tr className="bg-black/30 border-b border-border">
              <th className="sticky left-0 z-10 bg-black/30 text-left px-4 py-3 text-xs font-medium uppercase tracking-wider text-text-secondary border-r border-border/50 whitespace-nowrap" scope="col">Line Item</th>
              {periods.map((period) => <th key={period} scope="col" className="text-right px-4 py-3 text-xs font-medium uppercase tracking-wider text-text-secondary font-mono whitespace-nowrap">{formatFiscalPeriod(period)}</th>)}
            </tr>
          </thead>
          <tbody>
            {line_items.map((item, rowIdx) => {
              const isKeyRow = KEY_ROW_LABELS.has(item.label);
              const isEvenRow = rowIdx % 2 === 0;
              return (
                <tr key={item.label} className={cn("h-10 transition-colors duration-100 border-b border-border hover:bg-white/5", isKeyRow && "font-semibold")}>
                  <td className={cn("sticky left-0 z-10 px-4 py-1.5 text-sm text-text-primary border-r border-border/50 whitespace-nowrap bg-[rgba(10,15,26,0.6)]", isKeyRow && "font-semibold")}>{item.label}</td>
                  {item.values.map((val, colIdx) => (
                    <td key={`${item.label}-${periods[colIdx]}`} className={cn("text-right px-4 py-1.5 text-sm font-mono tabular-nums whitespace-nowrap", val != null && val < 0 ? "text-bear" : val == null ? "text-text-tertiary" : "text-text-primary")}>{formatStatementValue(val)}</td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
