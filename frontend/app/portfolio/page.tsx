"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getPortfolio, addHolding, deleteHolding } from "@/lib/api";
import type { PortfolioResponse } from "@/types/portfolio";
import PortfolioTable from "@/components/PortfolioTable";
import { formatLargeNumber, formatPercent } from "@/lib/utils";

export default function PortfolioPage() {
  const router = useRouter();
  const [data, setData] = useState<PortfolioResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ ticker: "", shares: "", costBasis: "", purchaseDate: "" });

  const fetchPortfolio = () => { setLoading(true); getPortfolio().then(setData).catch(() => {}).finally(() => setLoading(false)); };
  useEffect(() => { fetchPortfolio(); }, []);

  const handleAdd = async () => {
    if (!form.ticker || !form.shares || !form.costBasis || !form.purchaseDate) return;
    await addHolding({ ticker: form.ticker.toUpperCase(), shares: parseFloat(form.shares), costBasis: parseFloat(form.costBasis), purchaseDate: form.purchaseDate });
    setForm({ ticker: "", shares: "", costBasis: "", purchaseDate: "" });
    setShowAdd(false);
    fetchPortfolio();
  };

  const handleDelete = async (id: number) => { await deleteHolding(id); fetchPortfolio(); };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between animate-in">
        <h1 className="font-display text-2xl font-bold">Portfolio</h1>
        <button onClick={() => setShowAdd(!showAdd)} className="px-4 py-2 bg-primary hover:bg-primary-hover text-[#050810] text-sm font-medium rounded-xl hover:-translate-y-0.5 transition-all duration-200 shadow-sm hover:shadow-md">
          + Add Holding
        </button>
      </div>

      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-in-d1">
          {[
            { label: "Market Value", value: formatLargeNumber(data.summary.total_market_value) },
            { label: "Cost Basis", value: formatLargeNumber(data.summary.total_cost_basis) },
            { label: "Total P&L", value: `$${data.summary.total_gain_loss.toFixed(2)}` },
            { label: "Holdings", value: String(data.summary.holding_count) },
          ].map((s) => (
            <div key={s.label} className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-4">
              <div className="text-[11px] text-text-tertiary tracking-wider">{s.label}</div>
              <div className="text-lg font-mono font-bold text-text-primary mt-1">{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-primary/20 rounded-xl p-4 space-y-3 animate-in-d3">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <input placeholder="Ticker" value={form.ticker} onChange={(e) => setForm({ ...form, ticker: e.target.value })} className="bg-background border border-border rounded-lg px-3 py-2 text-sm font-mono text-text-primary focus:border-primary/40 focus:ring-1 focus:ring-primary/20 outline-none transition-colors" />
            <input placeholder="Shares" type="number" value={form.shares} onChange={(e) => setForm({ ...form, shares: e.target.value })} className="bg-background border border-border rounded-lg px-3 py-2 text-sm font-mono text-text-primary focus:border-primary/40 focus:ring-1 focus:ring-primary/20 outline-none transition-colors" />
            <input placeholder="Cost Basis" type="number" value={form.costBasis} onChange={(e) => setForm({ ...form, costBasis: e.target.value })} className="bg-background border border-border rounded-lg px-3 py-2 text-sm font-mono text-text-primary focus:border-primary/40 focus:ring-1 focus:ring-primary/20 outline-none transition-colors" />
            <input placeholder="Date" type="date" value={form.purchaseDate} onChange={(e) => setForm({ ...form, purchaseDate: e.target.value })} className="bg-background border border-border rounded-lg px-3 py-2 text-sm font-mono text-text-primary focus:border-primary/40 focus:ring-1 focus:ring-primary/20 outline-none transition-colors" />
          </div>
          <button onClick={handleAdd} className="px-4 py-2 bg-primary hover:bg-primary-hover text-[#050810] text-sm font-medium rounded-lg hover:-translate-y-0.5 transition-all duration-200">Add</button>
        </div>
      )}

      {data && <div className="animate-in-d2"><PortfolioTable holdings={data.holdings} onDelete={handleDelete} onAnalyze={(ticker) => router.push(`/analyze/${ticker}`)} /></div>}
    </div>
  );
}
