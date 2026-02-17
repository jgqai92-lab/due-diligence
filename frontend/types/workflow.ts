export type WorkflowType = 'IST' | 'HFRT';

export type WorkflowStatus =
  | 'PENDING' | 'RUNNING' | 'PAUSED'
  | 'COMPLETED' | 'FAILED' | 'CANCELLED'
  | 'CANCELLING' | 'RETRYING';

export type StepStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'SKIPPED';

export interface WorkflowStep {
  id: number;
  stepName: string;
  phase: number;
  phaseName: string;
  status: StepStatus;
  startedAt: string | null;
  completedAt: string | null;
  durationMs: number | null;
  errorMessage: string | null;
}

export interface WorkflowRun {
  id: number;
  workflowType: WorkflowType;
  name: string;
  status: WorkflowStatus;
  currentPhase: number;
  currentPhaseName: string | null;
  config: Record<string, unknown> | null;
  stepsCompleted: number;
  stepsTotal: number;
  autoAdvance?: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowDetail extends WorkflowRun {
  steps: WorkflowStep[];
  errorMessage: string | null;
}

export interface SSEEvent {
  type: string;
  workflowId?: number;
  workflowType?: string;
  stepName?: string;
  phase?: number;
  phaseName?: string;
  durationMs?: number;
  message?: string;
  percent?: number;
  error?: string;
  gateName?: string;
  deficiencies?: string[];
  details?: Record<string, unknown>;
  requiresApproval?: boolean;
  nextPhase?: number;
  timestamp: string;
  status?: string;
  currentPhase?: number;
  steps?: Array<{
    stepName: string;
    phase: number;
    status: StepStatus;
    durationMs: number | null;
  }>;
}
