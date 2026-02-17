import type {
  PersonaAnalysis,
  PersonaAnalysisRequest,
  TrioAnalysisRequest,
  PersonaAnalysisListResponse,
  PersonaAnalysisByTargetResponse,
  PersonaSubmitResponse,
} from '@/types/persona';

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

// ─── Run Single Persona Analysis ────────────────────────────────────

export async function runPersonaAnalysis(
  request: PersonaAnalysisRequest
): Promise<PersonaSubmitResponse> {
  const res = await fetch(`${API_BASE}/api/personas/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Run Trio Analysis ──────────────────────────────────────────────

export async function runTrioAnalysis(
  request: TrioAnalysisRequest
): Promise<PersonaSubmitResponse> {
  const res = await fetch(`${API_BASE}/api/personas/trio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── List Persona Analyses ──────────────────────────────────────────

export async function getPersonaAnalyses(
  filters?: {
    personaName?: string;
    targetType?: string;
    targetId?: number;
    skip?: number;
    limit?: number;
  }
): Promise<PersonaAnalysisListResponse> {
  const searchParams = new URLSearchParams();
  if (filters?.personaName) searchParams.set('personaName', filters.personaName);
  if (filters?.targetType) searchParams.set('targetType', filters.targetType);
  if (filters?.targetId != null) searchParams.set('targetId', String(filters.targetId));
  if (filters?.skip != null) searchParams.set('skip', String(filters.skip));
  if (filters?.limit != null) searchParams.set('limit', String(filters.limit));

  const url = `${API_BASE}/api/personas/analyses?${searchParams}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Analysis By ID ─────────────────────────────────────────────

export async function getAnalysisById(id: number): Promise<PersonaAnalysis> {
  const res = await fetch(`${API_BASE}/api/personas/analyses/${id}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Analyses By Target ─────────────────────────────────────────

export async function getAnalysesByTarget(
  targetType: string,
  targetId: number
): Promise<PersonaAnalysisByTargetResponse> {
  const res = await fetch(
    `${API_BASE}/api/personas/analyses/by-target/${encodeURIComponent(targetType)}/${targetId}`,
    {
      headers: { 'Content-Type': 'application/json' },
    }
  );
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}
