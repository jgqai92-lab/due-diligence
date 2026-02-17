"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAlerts, dismissAlert } from "@/lib/api";
import type { AlertsResponse } from "@/types/alerts";
import AlertBanner from "@/components/AlertBanner";

export default function AlertsPage() {
  const router = useRouter();
  const [data, setData] = useState<AlertsResponse | null>(null);

  const fetchAlerts = () => { getAlerts().then(setData).catch(() => {}); };
  useEffect(() => { fetchAlerts(); }, []);

  const handleDismiss = async (id: number) => { await dismissAlert(id); fetchAlerts(); };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between animate-in">
        <h1 className="font-display text-2xl font-bold">Alerts</h1>
        {data && <span className="text-xs text-text-tertiary">{data.undismissed_count} active alert{data.undismissed_count !== 1 ? "s" : ""}</span>}
      </div>
      {data && data.alerts.length === 0 && (
        <div className="bg-[rgba(10,15,26,0.6)] backdrop-blur-[12px] border border-border rounded-xl p-8 text-center text-text-secondary">No alerts. Run the Portfolio Watchdog to scan for forensic deterioration.</div>
      )}
      <div className="space-y-2 animate-in-d1">
        {data?.alerts.filter((a) => !a.dismissed).map((alert) => (
          <AlertBanner key={alert.id} ticker={alert.ticker} alertType={alert.alert_type} severity={alert.severity as "info" | "warning" | "critical"} message={alert.message} onDismiss={() => handleDismiss(alert.id)} onViewTicker={(t) => router.push(`/analyze/${t}`)} />
        ))}
      </div>
    </div>
  );
}
