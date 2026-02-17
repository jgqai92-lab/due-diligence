import type { WorkflowRun, WorkflowDetail } from '@/types/workflow';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Parse an error response body and throw a descriptive Error.
 */
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

/**
 * List workflow runs with optional filtering and pagination.
 */
export async function listWorkflows(params?: {
  type?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ workflows: WorkflowRun[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.type) searchParams.set('type', params.type);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.offset) searchParams.set('offset', String(params.offset));

  const url = `${API_BASE}/api/workflows?${searchParams}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

/**
 * Create a new workflow run.
 */
export async function createWorkflow(data: {
  workflowType: string;
  name: string;
  config?: Record<string, unknown>;
}): Promise<WorkflowRun> {
  const res = await fetch(`${API_BASE}/api/workflows`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

/**
 * Get a single workflow run with all steps.
 */
export async function getWorkflow(id: number): Promise<WorkflowDetail> {
  const res = await fetch(`${API_BASE}/api/workflows/${id}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

/**
 * Advance a paused workflow past a checkpoint.
 */
export async function advanceWorkflow(
  id: number,
  userNotes?: string
): Promise<{ id: number; status: string; advancingToPhase: number; message: string }> {
  const res = await fetch(`${API_BASE}/api/workflows/${id}/advance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userNotes }),
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

/**
 * Pause a running workflow.
 */
export async function pauseWorkflow(
  id: number
): Promise<{ id: number; status: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/workflows/${id}/pause`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

/**
 * Retry a failed workflow from the failed step.
 */
export async function retryWorkflow(
  id: number
): Promise<{ id: number; status: string; retryFromStep: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/workflows/${id}/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

/**
 * Toggle auto-advance mode on an existing workflow.
 */
export async function toggleAutoAdvance(
  id: number,
  enabled: boolean
): Promise<{ id: number; autoAdvance: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/api/workflows/${id}/auto-advance`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}

/**
 * Cancel a running or paused workflow.
 */
export async function cancelWorkflow(
  id: number
): Promise<{ id: number; status: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/workflows/${id}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) await handleErrorResponse(res);
  return res.json();
}
