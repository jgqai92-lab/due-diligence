import type {
  ISTScreenListItem,
  ISTScreenDetail,
  ISTClaim,
  BottleneckMapResponse,
  DemandModelsResponse,
  ValidationResponse,
  CandidatesResponse,
  TiersResponse,
  EffectsResponse,
  InvariantsResponse,
  DialecticReview,
  SynthesisReview,
  MasterScreenResponse,
  RotationResponse,
  CatalystResponse,
  StressTestResponse,
  ISTRefreshListItem,
  ISTRefreshDetail,
  ISTRefreshClaimsResponse,
  ReportResponse,
  CertificationResponse,
  HandoffResponse,
  FrameworkListResponse,
  FrameworkDetail,
} from '@/types/ist';

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

// ─── Create Screen ──────────────────────────────────────────────────

export async function createScreen(data: {
  name: string;
  content: string;
  contentType?: string;
  hypothesis?: string;
  constraints?: Record<string, unknown>;
  frameworks?: string[];
  autoAdvance?: boolean;
}): Promise<{
  id: number;
  workflowRunId: number;
  activeWorkflowRunId: number;
  name: string;
  status: string;
  refreshCount: number;
}> {
  const res = await fetch(`${API_BASE}/api/ist/screens`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── List Screens ───────────────────────────────────────────────────

export async function listScreens(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ screens: ISTScreenListItem[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.offset) searchParams.set('offset', String(params.offset));

  const url = `${API_BASE}/api/ist/screens?${searchParams}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Screen Detail ──────────────────────────────────────────────

export async function getScreen(id: number): Promise<ISTScreenDetail> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${id}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Screen Claims ──────────────────────────────────────────────

export async function getScreenClaims(
  id: number,
  params?: {
    validated?: boolean;
    hasQuantAnchor?: boolean;
  }
): Promise<{
  screenId: number;
  claims: ISTClaim[];
  totalCount: number;
  validatedCount: number;
}> {
  const searchParams = new URLSearchParams();
  if (params?.validated != null) searchParams.set('validated', String(params.validated));
  if (params?.hasQuantAnchor != null) searchParams.set('has_quant_anchor', String(params.hasQuantAnchor));

  const url = `${API_BASE}/api/ist/screens/${id}/claims?${searchParams}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Update Screening Brief ─────────────────────────────────────────

export async function updateScreenBrief(
  id: number,
  data: {
    hypothesis?: string;
    constraints?: Record<string, unknown>;
    frameworks?: string[];
  }
): Promise<ISTScreenDetail> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${id}/brief`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Bottleneck Map ────────────────────────────────────────────

export async function getBottlenecks(screenId: number): Promise<BottleneckMapResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/bottlenecks`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Demand Models ─────────────────────────────────────────────

export async function getDemandModels(screenId: number): Promise<DemandModelsResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/demand-models`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Validation Results ────────────────────────────────────────

export async function getValidationResults(screenId: number): Promise<ValidationResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/validation`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Candidates ───────────────────────────────────────────────

export async function getCandidates(
  screenId: number,
  tier?: number,
  bottleneckId?: number
): Promise<CandidatesResponse> {
  const searchParams = new URLSearchParams();
  if (tier != null) searchParams.set('tier', String(tier));
  if (bottleneckId != null) searchParams.set('bottleneck_id', String(bottleneckId));

  const url = `${API_BASE}/api/ist/screens/${screenId}/candidates?${searchParams}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Tiers ────────────────────────────────────────────────────

export async function getTiers(screenId: number): Promise<TiersResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/tiers`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Effects ──────────────────────────────────────────────────

export async function getEffects(screenId: number): Promise<EffectsResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/effects`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Invariants ───────────────────────────────────────────────

export async function getInvariants(screenId: number): Promise<InvariantsResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/invariants`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Dialectic Review ────────────────────────────────────────

export async function getDialecticReview(
  screenId: number,
  side: 'optimist' | 'pessimist' | 'synthesis'
): Promise<DialecticReview> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/dialectic/${side}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Synthesis ──────────────────────────────────────────────

export async function getSynthesis(screenId: number): Promise<SynthesisReview> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/synthesis`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Master Screen ──────────────────────────────────────────

export async function getMasterScreen(screenId: number): Promise<MasterScreenResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/master-screen`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Rotation Strategy ──────────────────────────────────────

export async function getRotation(screenId: number): Promise<RotationResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/rotation`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Catalysts ──────────────────────────────────────────────

export async function getCatalysts(screenId: number): Promise<CatalystResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/catalysts`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  const data = await res.json();
  return {
    ...data,
    nextCatalystDetails: data.nextCatalystDetails ?? null,
    nextCatalyst: typeof data.nextCatalyst === "string" ? data.nextCatalyst : null,
  };
}

// ─── Get Stress Tests ──────────────────────────────────────────

export async function getStressTests(screenId: number): Promise<StressTestResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/stress-tests`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  const data = await res.json();
  return {
    ...data,
    survivalScores: Array.isArray(data.survivalScores) ? data.survivalScores : [],
    survivalSummary: data.survivalSummary ?? {
      averageTier1: 0,
      averageTier2: 0,
      lowestSurvivor: { ticker: "", score: 0 },
    },
  };
}

// ─── Get Report ─────────────────────────────────────────────────

export async function getReport(screenId: number): Promise<ReportResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/report`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  const data = await res.json();
  const report = data.report ?? {
    id: 0,
    title: data.title,
    content: data.content,
    metadata: data.metadata,
  };
  return {
    ...data,
    title: data.title ?? report.title,
    content: data.content ?? report.content,
    metadata: data.metadata ?? report.metadata,
    report,
  };
}

// ─── Get Frameworks List ────────────────────────────────────────

export async function getFrameworks(): Promise<FrameworkListResponse> {
  const res = await fetch(`${API_BASE}/api/frameworks/ist`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Framework Detail ───────────────────────────────────────

export async function getFrameworkDetail(name: string): Promise<FrameworkDetail> {
  const res = await fetch(`${API_BASE}/api/frameworks/ist/${encodeURIComponent(name)}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Certification ─────────────────────────────────────────

export async function getCertification(screenId: number): Promise<CertificationResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/certification`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Handoff Data ──────────────────────────────────────────

export async function getHandoff(screenId: number): Promise<HandoffResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/handoff`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Delete Screen ──────────────────────────────────────────────

export async function deleteScreen(id: number): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Screen Inputs ──────────────────────────────────────────

export async function getScreenInputs(id: number): Promise<{
  id: number;
  name: string;
  contentType: string;
  rawContent: string;
  hypothesis: string | null;
  constraints: Record<string, unknown> | null;
  frameworks: string[] | null;
  createdAt: string | null;
}> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${id}/inputs`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Rerun Screen ───────────────────────────────────────────────

export async function rerunScreen(id: number): Promise<{
  id: number;
  workflowRunId: number;
  name: string;
  status: string;
  message: string;
}> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${id}/rerun`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function createScreenRefresh(
  id: number,
  data: {
    content: string;
    contentType?: string;
    autoAdvance?: boolean;
    idempotencyKey?: string;
  }
): Promise<{
  id: number;
  screenId: number;
  workflowRunId: number;
  refreshNumber: number;
  status: string;
  warning?: string;
}> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${id}/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function listScreenRefreshes(id: number): Promise<{
  screenId: number;
  refreshes: ISTRefreshListItem[];
  total: number;
}> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${id}/refreshes`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function getScreenRefresh(
  screenId: number,
  refreshId: number
): Promise<ISTRefreshDetail> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/refreshes/${refreshId}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

export async function getScreenRefreshClaims(
  screenId: number,
  refreshId: number
): Promise<ISTRefreshClaimsResponse> {
  const res = await fetch(`${API_BASE}/api/ist/screens/${screenId}/refreshes/${refreshId}/claims`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}
