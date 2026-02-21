"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { listSyntheses } from "@/lib/api/ist-synthesis";
import type { SynthesisListItem } from "@/types/ist-synthesis";

export default function SynthesesPage() {
  const router = useRouter();
  const [items, setItems] = useState<SynthesisListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSyntheses({ limit: 50 })
      .then((res) => setItems(res.syntheses))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load syntheses"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">Screen Syntheses</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            Cross-screen meta-analysis and re-tiering workflows
          </p>
        </div>
        <button
          onClick={() => router.push("/screens/syntheses/new")}
          className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-[#050810] bg-primary rounded-lg hover:bg-primary-hover"
        >
          <Plus size={16} />
          New Synthesis
        </button>
      </div>

      <Link href="/screens" className="text-sm text-text-secondary hover:text-text-primary">
        Back to Screens
      </Link>

      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-text-secondary">Loading syntheses...</div>
      ) : items.length === 0 ? (
        <div className="text-sm text-text-secondary bg-[rgba(10,15,26,0.6)] border border-border rounded-lg p-5">
          No syntheses yet.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <button
              key={item.id}
              onClick={() => router.push(`/screens/syntheses/${item.id}`)}
              className="w-full text-left bg-[rgba(10,15,26,0.6)] border border-border rounded-lg p-4 hover:bg-white/5"
            >
              <p className="text-sm font-semibold text-text-primary">{item.name}</p>
              <p className="text-xs text-text-secondary mt-1">
                {item.status} · Sources: {item.sourceScreenCount} · Tier Changes: {item.tierChangeCount}
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

