"use client";

import { useState, useEffect, useCallback, useRef } from 'react';
import type { SSEEvent, StepStatus, WorkflowStatus } from '@/types/workflow';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const MAX_RETRIES = 5;
const RECONNECT_DELAY_MS = 3000;

interface UseWorkflowSSEOptions {
  workflowId: number | null;
  onStepComplete?: (stepName: string, durationMs: number) => void;
  onCheckpoint?: (phase: number, nextPhase: number) => void;
  onGateFailed?: (gateName: string, deficiencies: string[]) => void;
  onWorkflowComplete?: () => void;
  onWorkflowFailed?: (error: string) => void;
}

interface UseWorkflowSSEReturn {
  connected: boolean;
  steps: Map<string, { status: StepStatus; durationMs: number | null }>;
  currentStep: string | null;
  workflowStatus: WorkflowStatus | null;
  lastEvent: SSEEvent | null;
  error: string | null;
}

/**
 * Custom React hook that manages an EventSource (SSE) connection to a
 * workflow's real-time event stream.
 *
 * Handles all 14 SSE event types, auto-reconnects on disconnect (up to
 * MAX_RETRIES), and cleans up on unmount or when workflowId changes.
 */
export function useWorkflowSSE(options: UseWorkflowSSEOptions): UseWorkflowSSEReturn {
  const { workflowId } = options;

  // Store callbacks in refs so they don't trigger reconnects
  const callbacksRef = useRef(options);
  callbacksRef.current = options;

  const [connected, setConnected] = useState(false);
  const [steps, setSteps] = useState<Map<string, { status: StepStatus; durationMs: number | null }>>(new Map());
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatus | null>(null);
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const [error, setError] = useState<string | null>(null);

  const retriesRef = useRef(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const handleEvent = useCallback((event: MessageEvent) => {
    let data: SSEEvent;
    try {
      data = JSON.parse(event.data);
    } catch {
      return; // Ignore malformed SSE data
    }

    setLastEvent(data);

    switch (data.type) {
      case 'workflow_started': {
        setWorkflowStatus('RUNNING');
        setError(null);
        break;
      }

      case 'phase_started': {
        // Phase has begun — no step-level change needed
        break;
      }

      case 'step_started': {
        if (data.stepName) {
          setCurrentStep(data.stepName);
          setSteps(prev => {
            const next = new Map(prev);
            next.set(data.stepName!, { status: 'RUNNING', durationMs: null });
            return next;
          });
        }
        break;
      }

      case 'step_progress': {
        // Progress updates (percent) — handled via lastEvent
        break;
      }

      case 'step_complete': {
        if (data.stepName) {
          const duration = data.durationMs ?? null;
          setSteps(prev => {
            const next = new Map(prev);
            next.set(data.stepName!, { status: 'COMPLETED', durationMs: duration });
            return next;
          });
          if (currentStep === data.stepName) {
            setCurrentStep(null);
          }
          if (callbacksRef.current.onStepComplete && duration != null) {
            callbacksRef.current.onStepComplete(data.stepName, duration);
          }
        }
        break;
      }

      case 'step_failed': {
        if (data.stepName) {
          setSteps(prev => {
            const next = new Map(prev);
            next.set(data.stepName!, { status: 'FAILED', durationMs: null });
            return next;
          });
          if (currentStep === data.stepName) {
            setCurrentStep(null);
          }
        }
        break;
      }

      case 'phase_complete': {
        // Phase finished — no special handling needed
        break;
      }

      case 'checkpoint_reached': {
        setWorkflowStatus('PAUSED');
        if (callbacksRef.current.onCheckpoint && data.phase != null && data.nextPhase != null) {
          callbacksRef.current.onCheckpoint(data.phase, data.nextPhase);
        }
        break;
      }

      case 'phase_auto_advanced': {
        // Auto-advance skipped the checkpoint — workflow stays RUNNING
        setWorkflowStatus('RUNNING');
        break;
      }

      case 'gate_passed': {
        // Quality gate passed — continue
        break;
      }

      case 'gate_failed': {
        if (callbacksRef.current.onGateFailed && data.gateName && data.deficiencies) {
          callbacksRef.current.onGateFailed(data.gateName, data.deficiencies);
        }
        break;
      }

      case 'workflow_complete': {
        setWorkflowStatus('COMPLETED');
        setCurrentStep(null);
        callbacksRef.current.onWorkflowComplete?.();
        break;
      }

      case 'workflow_failed': {
        setWorkflowStatus('FAILED');
        setCurrentStep(null);
        const errorMsg = data.error || 'Workflow failed';
        setError(errorMsg);
        callbacksRef.current.onWorkflowFailed?.(errorMsg);
        break;
      }

      case 'heartbeat': {
        // Keep-alive — no action needed
        break;
      }

      case 'catch_up': {
        // Populate state from server snapshot on reconnect
        if (data.status) {
          setWorkflowStatus(data.status as WorkflowStatus);
        }
        if (data.steps && Array.isArray(data.steps)) {
          const newSteps = new Map<string, { status: StepStatus; durationMs: number | null }>();
          let activeStep: string | null = null;
          for (const step of data.steps) {
            newSteps.set(step.stepName, {
              status: step.status,
              durationMs: step.durationMs,
            });
            if (step.status === 'RUNNING') {
              activeStep = step.stepName;
            }
          }
          setSteps(newSteps);
          setCurrentStep(activeStep);
        }
        // If workflow is already terminal, close the connection immediately —
        // no live events will arrive and keeping it open wastes a browser
        // connection slot (browsers limit ~6 per domain).
        const TERMINAL_STATUSES = ['COMPLETED', 'FAILED', 'CANCELLED'];
        if (data.status && TERMINAL_STATUSES.includes(data.status)) {
          cleanup();
          setConnected(false);
        }
        break;
      }

      default: {
        // Unknown event type — ignore gracefully
        break;
      }
    }
  }, [currentStep]);

  const connect = useCallback(() => {
    if (workflowId == null) return;

    cleanup();

    const url = `${API_BASE}/api/workflows/${workflowId}/stream`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnected(true);
      setError(null);
      retriesRef.current = 0;
    };

    // Named SSE events require addEventListener (onmessage only handles unnamed events)
    const SSE_EVENT_TYPES = [
      'workflow_started', 'phase_started', 'step_started', 'step_progress',
      'step_complete', 'step_failed', 'phase_complete', 'checkpoint_reached',
      'phase_auto_advanced', 'gate_passed', 'gate_failed',
      'workflow_complete', 'workflow_failed',
      'workflow_paused', 'workflow_cancelled', 'heartbeat', 'catch_up',
    ];
    for (const eventType of SSE_EVENT_TYPES) {
      es.addEventListener(eventType, handleEvent as EventListener);
    }
    // Also handle unnamed events as fallback
    es.onmessage = handleEvent;

    es.onerror = () => {
      setConnected(false);
      es.close();
      eventSourceRef.current = null;

      if (retriesRef.current < MAX_RETRIES) {
        retriesRef.current += 1;
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, RECONNECT_DELAY_MS);
      } else {
        setError('Lost connection to workflow stream. Please refresh the page.');
      }
    };
  }, [workflowId, cleanup, handleEvent]);

  useEffect(() => {
    if (workflowId == null) {
      cleanup();
      setConnected(false);
      setSteps(new Map());
      setCurrentStep(null);
      setWorkflowStatus(null);
      setLastEvent(null);
      setError(null);
      return;
    }

    connect();

    return () => {
      cleanup();
    };
  }, [workflowId, connect, cleanup]);

  return {
    connected,
    steps,
    currentStep,
    workflowStatus,
    lastEvent,
    error,
  };
}
