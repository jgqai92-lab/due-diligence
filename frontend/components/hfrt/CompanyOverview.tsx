"use client";

import { cn } from "@/lib/utils";
import { Building2, Users, MapPin, Calendar, Briefcase } from "lucide-react";

/* ── Data shape from CompanyOverviewResult (Template 01) ──────────── */

interface ManagementMember {
  name?: string;
  title?: string;
  [key: string]: unknown;
}

interface CompanyOverviewData {
  company_name: string;
  ticker: string;
  sector: string;
  industry: string;
  headquarters: string | null;
  founded: string | null;
  employees: number | null;
  description: string;
  business_segments: Array<Record<string, unknown>>;
  key_products_services: string[];
  geographic_presence: string[];
  recent_developments: string[];
  management_team: ManagementMember[];
}

interface CompanyOverviewProps {
  data: Record<string, unknown>;
}

export default function CompanyOverview({ data }: CompanyOverviewProps) {
  const d = data as unknown as CompanyOverviewData;

  if (!d || !d.company_name) {
    return (
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-6 text-center py-12 text-text-tertiary">
        <Building2 size={32} className="mx-auto mb-3" />
        <p className="text-sm">Company overview not yet available.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Company Info Grid */}
      <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-3">Company Info</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <div className="bg-white/5 rounded-lg px-3 py-2">
            <p className="text-xs text-text-secondary">Sector</p>
            <p className="text-sm text-text-primary">{d.sector || "N/A"}</p>
          </div>
          <div className="bg-white/5 rounded-lg px-3 py-2">
            <p className="text-xs text-text-secondary">Industry</p>
            <p className="text-sm text-text-primary">{d.industry || "N/A"}</p>
          </div>
          <div className="bg-white/5 rounded-lg px-3 py-2">
            <div className="flex items-center gap-1">
              <MapPin size={10} className="text-text-tertiary" />
              <p className="text-xs text-text-secondary">Headquarters</p>
            </div>
            <p className="text-sm text-text-primary">{d.headquarters ?? "N/A"}</p>
          </div>
          <div className="bg-white/5 rounded-lg px-3 py-2">
            <div className="flex items-center gap-1">
              <Calendar size={10} className="text-text-tertiary" />
              <p className="text-xs text-text-secondary">Founded</p>
            </div>
            <p className="text-sm font-mono text-text-primary">{d.founded ?? "N/A"}</p>
          </div>
          <div className="bg-white/5 rounded-lg px-3 py-2">
            <div className="flex items-center gap-1">
              <Users size={10} className="text-text-tertiary" />
              <p className="text-xs text-text-secondary">Employees</p>
            </div>
            <p className="text-sm font-mono text-text-primary">
              {d.employees != null ? d.employees.toLocaleString() : "N/A"}
            </p>
          </div>
        </div>
      </div>

      {/* Description */}
      {d.description && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Description</h3>
          <p className="text-sm text-text-primary leading-relaxed">{d.description}</p>
        </div>
      )}

      {/* Business Segments */}
      {d.business_segments?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Business Segments ({d.business_segments.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left text-xs font-medium text-text-secondary pb-2 pr-4">Segment</th>
                  <th className="text-right text-xs font-medium text-text-secondary pb-2 pr-4">Revenue</th>
                  <th className="text-left text-xs font-medium text-text-secondary pb-2">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {d.business_segments.map((seg, idx) => (
                  <tr key={idx} className="hover:bg-white/5">
                    <td className="py-2 pr-4 text-text-primary font-medium">
                      {String(seg.name ?? seg.segment ?? `Segment ${idx + 1}`)}
                    </td>
                    <td className="py-2 pr-4 text-right font-mono text-text-primary">
                      {seg.revenue != null
                        ? typeof seg.revenue === "number"
                          ? `$${(seg.revenue as number).toLocaleString()}`
                          : String(seg.revenue)
                        : seg.percentage != null
                        ? `${seg.percentage}%`
                        : "N/A"}
                    </td>
                    <td className="py-2 text-text-secondary text-xs">
                      {String(seg.description ?? "")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Key Products / Services */}
      {d.key_products_services?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Key Products & Services</h3>
          <ul className="space-y-2">
            {d.key_products_services.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-text-primary">
                <Briefcase size={14} className="text-text-tertiary mt-0.5 flex-shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Geographic Presence */}
      {d.geographic_presence?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Geographic Presence</h3>
          <div className="flex flex-wrap gap-2">
            {d.geographic_presence.map((geo, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-300 border border-blue-500/30"
              >
                <MapPin size={10} className="mr-1" />
                {geo}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Recent Developments */}
      {d.recent_developments?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Recent Developments ({d.recent_developments.length})
          </h3>
          <ul className="space-y-2">
            {d.recent_developments.map((dev, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-text-primary">
                <span className="text-text-tertiary font-mono text-xs mt-0.5 flex-shrink-0">
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <span>{dev}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Management Team */}
      {d.management_team?.length > 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Management Team</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left text-xs font-medium text-text-secondary pb-2">Name</th>
                  <th className="text-left text-xs font-medium text-text-secondary pb-2">Title</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {d.management_team.map((member, idx) => (
                  <tr key={idx} className="hover:bg-white/5">
                    <td className="py-2 text-text-primary font-medium">{member.name ?? "N/A"}</td>
                    <td className="py-2 text-text-secondary">{member.title ?? "N/A"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
