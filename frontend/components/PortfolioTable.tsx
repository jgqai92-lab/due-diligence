"use client";

import type { Holding } from "@/types/portfolio";
import { cn, formatLargeNumber, formatPercent } from "@/lib/utils";
import { Trash2, BarChart3 } from "lucide-react";

interface PortfolioTableProps { holdings: Holding[]; onDelete: (id: number) => void; onAnalyze: (ticker: string) => void; }

export default function PortfolioTable({ holdings, onDelete, onAnalyze }: PortfolioTableProps) {
  if (holdings.length === 0) {
    return <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl shadow-card p-8 text-center text-text-secondary">No holdings yet. Add a position to get started.</div>;
  }

  return (
    <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl shadow-card overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-black/30 border-b border-border">
            {["Ticker", "Shares", "Cost Basis", "Price", "Value", "P&L ($)", "P&L (%)", "Actions"].map((h) => (
              <th key={h} className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-text-secondary text-left">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {holdings.map((h, i) => (
            <tr key={h.id} className={cn("border-b border-border hover:bg-white/5 transition-colors duration-150")} style={{ height: 44 }}>
              <td className="px-4 py-2 font-mono font-bold text-sm text-text-primary">{h.ticker}</td>
              <td className="px-4 py-2 font-mono text-sm text-text-primary text-right">{h.shares}</td>
              <td className="px-4 py-2 font-mono text-sm text-text-primary text-right">${h.cost_basis.toFixed(2)}</td>
              <td className="px-4 py-2 font-mono text-sm text-text-primary text-right">{h.current_price != null ? `$${h.current_price.toFixed(2)}` : "—"}</td>
              <td className="px-4 py-2 font-mono text-sm text-text-primary text-right">{h.market_value != null ? formatLargeNumber(h.market_value) : "—"}</td>
              <td className={cn("px-4 py-2 font-mono text-sm text-right", h.gain_loss != null && h.gain_loss >= 0 ? "text-bull" : "text-bear")}>{h.gain_loss != null ? `$${h.gain_loss.toFixed(2)}` : "—"}</td>
              <td className={cn("px-4 py-2 font-mono text-sm text-right", h.gain_loss_percent != null && h.gain_loss_percent >= 0 ? "text-bull" : "text-bear")}>{formatPercent(h.gain_loss_percent)}</td>
              <td className="px-4 py-2">
                <div className="flex items-center gap-2 justify-center">
                  <button onClick={() => onAnalyze(h.ticker)} className="text-text-tertiary hover:text-primary p-1 rounded-lg hover:bg-white/5 transition-colors" title="Analyze"><BarChart3 size={14} /></button>
                  <button onClick={() => onDelete(h.id)} className="text-text-tertiary hover:text-bear p-1 rounded-lg hover:bg-white/5 transition-colors" title="Delete"><Trash2 size={14} /></button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
