import type { HandoffCandidate } from '@/types/ist';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ─── Error Handling ─────────────────────────────────────────────────

async function handleErrorResponse(res: Response): Promise<never> {
  let message = `API Error: ${res.status}`;
  try {
    const body = await res.json();
    if (body?.detail) {
      if (typeof body.detail === 'string') {
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
    } else if (body?.error) {
      message = typeof body.error === 'string' ? body.error : (body.error.message ?? JSON.stringify(body.error));
    }
  } catch {
    // Response body was not JSON
  }
  const err = new Error(message);
  (err as any).status = res.status;
  throw err;
}

// ─── Types ──────────────────────────────────────────────────────────

export interface BridgeCandidatesResponse {
  screenName: string;
  screenId: number;
  certifiedAt: string;
  tier1Count: number;
  totalCount?: number;
  tierBreakdown?: { tier1: number; tier2: number; tier3: number };
  candidates: HandoffCandidate[];
}

export interface BridgeCreateRequest {
  screenId: number;
  tickers: string[];
}

export interface BridgeCreatedProject {
  ticker: string;
  projectId: number;
  workflowRunId: number;
  link: string;
}

export interface BridgeCreateResponse {
  created: BridgeCreatedProject[];
  failed: Array<{ ticker: string; error: string }>;
  total: number;
}

// ─── Get Bridge Candidates ──────────────────────────────────────────

export async function getBridgeCandidates(screenId: number): Promise<BridgeCandidatesResponse> {
  const res = await fetch(`${API_BASE}/api/bridge/ist-to-hfrt/candidates/${screenId}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Create HFRT Projects from Bridge ───────────────────────────────

export async function createHFRTFromBridge(request: BridgeCreateRequest): Promise<BridgeCreateResponse> {
  const res = await fetch(`${API_BASE}/api/bridge/ist-to-hfrt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}
