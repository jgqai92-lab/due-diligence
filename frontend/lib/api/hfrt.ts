import type {
  HFRTProjectListItem,
  HFRTProjectDetail,
  HFRTTemplateListResponse,
  HFRTTemplate,
  HFRTDialecticReview,
  HFRTInvariantsResponse,
  HFRTMemoResponse,
  HFRTReadinessResponse,
  HFRTCitationResponse,
  HFRTIsolationAuditResponse,
  SECFiling,
  HFRTFrameworkListResponse,
  HFRTFrameworkDetail,
} from '@/types/hfrt';

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

// ─── Create Project ─────────────────────────────────────────────────

export async function createProject(data: {
  ticker: string;
}): Promise<{ id: number; workflowRunId: number; ticker: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/hfrt/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── List Projects ──────────────────────────────────────────────────

export async function listProjects(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ projects: HFRTProjectListItem[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.offset) searchParams.set('offset', String(params.offset));

  const url = `${API_BASE}/api/hfrt/projects?${searchParams}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Project Detail ─────────────────────────────────────────────

export async function getProject(id: number): Promise<HFRTProjectDetail> {
  const res = await fetch(`${API_BASE}/api/hfrt/projects/${id}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get All Templates ──────────────────────────────────────────────

export async function getTemplates(projectId: number): Promise<HFRTTemplateListResponse> {
  const res = await fetch(`${API_BASE}/api/hfrt/projects/${projectId}/templates`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Single Template ────────────────────────────────────────────

export async function getTemplate(
  projectId: number,
  templateNumber: number
): Promise<HFRTTemplate> {
  const res = await fetch(
    `${API_BASE}/api/hfrt/projects/${projectId}/templates/${templateNumber}`,
    { headers: { 'Content-Type': 'application/json' } }
  );
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get SEC Filings ────────────────────────────────────────────────

export async function getSECFilings(
  projectId: number
): Promise<{ projectId: number; filings: SECFiling[] }> {
  const res = await fetch(`${API_BASE}/api/hfrt/projects/${projectId}/sec-filings`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Dialectic Review ───────────────────────────────────────────

export async function getDialecticReview(
  projectId: number,
  side: 'bull' | 'bear'
): Promise<HFRTDialecticReview> {
  const res = await fetch(
    `${API_BASE}/api/hfrt/projects/${projectId}/dialectic/${side}`,
    { headers: { 'Content-Type': 'application/json' } }
  );
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Invariants ─────────────────────────────────────────────────

export async function getInvariants(projectId: number): Promise<HFRTInvariantsResponse> {
  const res = await fetch(`${API_BASE}/api/hfrt/projects/${projectId}/invariants`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Investment Memo ────────────────────────────────────────────

export async function getMemo(projectId: number): Promise<HFRTMemoResponse> {
  const res = await fetch(`${API_BASE}/api/hfrt/projects/${projectId}/memo`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Readiness Check (Gap B1) ──────────────────────────────────

export async function getReadiness(force?: boolean): Promise<HFRTReadinessResponse> {
  const params = force ? '?force=true' : '';
  const res = await fetch(`${API_BASE}/api/hfrt/readiness${params}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Citation Validation (Gap B5) ─────────────────────────────

export async function getCitations(
  projectId: number,
  templateNumber: number
): Promise<HFRTCitationResponse> {
  const res = await fetch(
    `${API_BASE}/api/hfrt/projects/${projectId}/citations/${templateNumber}`,
    { headers: { 'Content-Type': 'application/json' } }
  );
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Dialectic Isolation Audit (Gap B6) ───────────────────────

export async function getIsolationAudit(
  projectId: number
): Promise<HFRTIsolationAuditResponse> {
  const res = await fetch(
    `${API_BASE}/api/hfrt/projects/${projectId}/dialectic/audit`,
    { headers: { 'Content-Type': 'application/json' } }
  );
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get HFRT Frameworks List ──────────────────────────────────────

export async function getHFRTFrameworks(): Promise<HFRTFrameworkListResponse> {
  const res = await fetch(`${API_BASE}/api/frameworks/hfrt`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get HFRT Framework Detail ─────────────────────────────────────

export async function getHFRTFrameworkDetail(name: string): Promise<HFRTFrameworkDetail> {
  const res = await fetch(`${API_BASE}/api/frameworks/hfrt/${encodeURIComponent(name)}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Delete Project ─────────────────────────────────────────────────

export async function deleteProject(id: number): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/hfrt/projects/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Get Project Inputs ─────────────────────────────────────────────

export async function getProjectInputs(id: number): Promise<{
  id: number;
  ticker: string;
  source: string | null;
  istScreenId: number | null;
  createdAt: string | null;
}> {
  const res = await fetch(`${API_BASE}/api/hfrt/projects/${id}/inputs`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

// ─── Rerun Project ──────────────────────────────────────────────────

export async function rerunProject(id: number): Promise<{
  id: number;
  workflowRunId: number;
  ticker: string;
  status: string;
  message: string;
}> {
  const res = await fetch(`${API_BASE}/api/hfrt/projects/${id}/rerun`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}
