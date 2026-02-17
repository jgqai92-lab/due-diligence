"use client";

import { cn } from "@/lib/utils";
import { DollarSign, Layers, Users, Truck, Handshake, TrendingUp } from "lucide-react";

/* ── Data shape from BusinessModelResult (Template 02) ────────────── */

interface BusinessModelData {
  revenue_model: string;
  revenue_streams: Array<Record<string, unknown>>;
  cost_structure: Record<string, unknown>;
  unit_economics: Record<string, unknown>;
  customer_segments: string[];
  value_proposition: string;
  distribution_channels: string[];
  key_partnerships: string[];
  scalability_assessment: string;
  recurring_revenue_pct: number | null;
}

interface BusinessModelPanelProps {
  data: Record<string, unknown>;
}

function formatValue(val: unknown): string {
  if (val == null) return "N/A";
  if (typeof val === "number") {
    if (Math.abs(val) < 1 && val !== 0) {
      return (val * 100).toFixed(1) + "%";
    }
    return val.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(val);
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function BusinessModelPanel({ data }: BusinessModelPanelProps) {
  const d = data as unknown as BusinessModelData;

  if (!d || !d.revenue_model) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 text-center py-12 text-text-tertiary">
        <Layers size={32} className="mx-auto mb-3" />
        <p className="text-sm">Business model analysis not yet available.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Revenue Model + Recurring Revenue */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-3">Revenue Model</h3>
        <p className="text-sm text-text-primary leading-relaxed mb-4">{d.revenue_model}</p>
        {d.recurring_revenue_pct != null && (
          <div className="inline-flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-4 py-2">
            <TrendingUp size={14} className="text-emerald-400" />
            <div>
              <p className="text-xs text-emerald-400">Recurring Revenue</p>
              <p className="text-lg font-bold font-mono text-emerald-300">
                {d.recurring_revenue_pct.toFixed(1)}%
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Revenue Streams */}
      {d.revenue_streams?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Revenue Streams ({d.revenue_streams.length})
          </h3>
          <div className="space-y-3">
            {d.revenue_streams.map((stream, idx) => (
              <div key={idx} className="bg-white/5 rounded-lg px-4 py-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-text-primary">
                    {String(stream.name ?? stream.stream ?? `Stream ${idx + 1}`)}
                  </span>
                  {stream.percentage != null && (
                    <span className="text-sm font-mono font-bold text-text-primary">
                      {Number(stream.percentage).toFixed(1)}%
                    </span>
                  )}
                </div>
                {stream.description != null && (
                  <p className="text-xs text-text-secondary">{String(stream.description)}</p>
                )}
                {stream.revenue != null && (
                  <p className="text-xs font-mono text-text-secondary mt-1">
                    Revenue: {typeof stream.revenue === "number"
                      ? `$${(stream.revenue as number).toLocaleString()}`
                      : String(stream.revenue)}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cost Structure */}
      {d.cost_structure && Object.keys(d.cost_structure).length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Cost Structure</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(d.cost_structure).map(([key, value]) => (
              <div key={key} className="bg-white/5 rounded-lg px-3 py-2">
                <p className="text-xs text-text-secondary">{humanizeKey(key)}</p>
                <p className="text-sm font-mono text-text-primary">{formatValue(value)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Unit Economics */}
      {d.unit_economics && Object.keys(d.unit_economics).length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Unit Economics</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(d.unit_economics).map(([key, value]) => (
              <div key={key} className="bg-white/5 rounded-lg px-3 py-2">
                <p className="text-xs text-text-secondary">{humanizeKey(key)}</p>
                <p className="text-sm font-mono text-text-primary">{formatValue(value)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Customer Segments */}
      {d.customer_segments?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Customer Segments</h3>
          <div className="flex flex-wrap gap-2">
            {d.customer_segments.map((segment, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/30"
              >
                <Users size={10} className="mr-1" />
                {segment}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Value Proposition */}
      {d.value_proposition && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Value Proposition</h3>
          <p className="text-sm text-text-primary leading-relaxed">{d.value_proposition}</p>
        </div>
      )}

      {/* Distribution Channels & Key Partnerships */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {d.distribution_channels?.length > 0 && (
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-text-primary mb-3">
              <span className="inline-flex items-center gap-1.5">
                <Truck size={14} className="text-text-tertiary" />
                Distribution Channels
              </span>
            </h3>
            <ul className="space-y-2">
              {d.distribution_channels.map((channel, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-text-primary">
                  <span className="text-text-tertiary mt-0.5 flex-shrink-0">&#8226;</span>
                  <span>{channel}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {d.key_partnerships?.length > 0 && (
          <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-text-primary mb-3">
              <span className="inline-flex items-center gap-1.5">
                <Handshake size={14} className="text-text-tertiary" />
                Key Partnerships
              </span>
            </h3>
            <ul className="space-y-2">
              {d.key_partnerships.map((partner, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-text-primary">
                  <span className="text-text-tertiary mt-0.5 flex-shrink-0">&#8226;</span>
                  <span>{partner}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Scalability Assessment */}
      {d.scalability_assessment && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Scalability Assessment</h3>
          <p className="text-sm text-text-primary leading-relaxed">{d.scalability_assessment}</p>
        </div>
      )}
    </div>
  );
}
