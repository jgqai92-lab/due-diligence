import type {
  SynthesisDetail,
  SynthesisDialectic,
  SynthesisEquity,
  SynthesisListItem,
  SynthesisSource,
  SynthesisTierChange,
  ThesisInteraction,
  OverlapEntry,
} from "@/types/ist-synthesis";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function handleErrorResponse(res: Response): Promise<never> {
  let message = `API Error: ${res.status}`;
  try {
    const body = await res.json();
    if (body?.detail) {
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (body.detail?.error?.message) {
        message = body.detail.error.message;
      } else if (body.detail?.message) {
        message = body.detail.message;
      } else {
        message = JSON.stringify(body.detail);
      }
    } else if (body?.message) {
      message = body.message;
    }
  } catch {
    // Non-JSON body.
  }
  const err = new Error(message);
  (err as any).status = res.status;
  throw err;
}

export async function createSynthesis(data: {
  name: string;
  screenIds: number[];
  autoAdvance?: boolean;
  idempotencyKey?: string;
}): Promise<{ id: number; workflowRunId: number; status: string; warning?: string }> {
  const res = await fetch(`${API_BASE}/api/ist/syntheses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function listSyntheses(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ syntheses: SynthesisListItem[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const res = await fetch(`${API_BASE}/api/ist/syntheses?${searchParams}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function getSynthesis(id: number): Promise<SynthesisDetail> {
  const res = await fetch(`${API_BASE}/api/ist/syntheses/${id}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function deleteSynthesis(id: number): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/ist/syntheses/${id}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function getSynthesisSources(id: number): Promise<{ synthesisId: number; sources: SynthesisSource[] }> {
  const res = await fetch(`${API_BASE}/api/ist/syntheses/${id}/sources`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function getSynthesisOverlap(id: number): Promise<{ synthesisId: number; overlap: OverlapEntry[] }> {
  const res = await fetch(`${API_BASE}/api/ist/syntheses/${id}/overlap`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function getSynthesisInteractions(id: number): Promise<{ synthesisId: number; interactions: ThesisInteraction[] }> {
  const res = await fetch(`${API_BASE}/api/ist/syntheses/${id}/interactions`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function getSynthesisTierChanges(id: number): Promise<{ synthesisId: number; tierChanges: SynthesisTierChange[] }> {
  const res = await fetch(`${API_BASE}/api/ist/syntheses/${id}/tier-changes`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function getSynthesisEquities(id: number): Promise<{ synthesisId: number; equities: SynthesisEquity[] }> {
  const res = await fetch(`${API_BASE}/api/ist/syntheses/${id}/equities`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function getSynthesisDialectic(
  id: number,
  side: "OPTIMIST" | "PESSIMIST" | "SYNTHESIS"
): Promise<SynthesisDialectic> {
  const res = await fetch(`${API_BASE}/api/ist/syntheses/${id}/dialectic/${side}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function getSynthesisReport(id: number): Promise<{ synthesisId: number; report: string; metadata: Record<string, unknown> }> {
  const res = await fetch(`${API_BASE}/api/ist/syntheses/${id}/report`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function getSynthesisHandoff(id: number): Promise<{ synthesisId: number; handoff: Record<string, unknown> }> {
  const res = await fetch(`${API_BASE}/api/ist/syntheses/${id}/handoff`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

