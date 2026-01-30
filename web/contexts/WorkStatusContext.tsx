'use client';

/**
 * ADR-016: TP Awareness Status
 * Context provider for tracking work execution status
 *
 * Status is updated via SSE stream events from chat
 */

import { createContext, useContext, useReducer, useCallback, ReactNode } from 'react';

export type WorkStatusState =
  | { status: 'idle' }
  | { status: 'working'; agentType: string; task: string; ticketId: string }
  | { status: 'complete'; agentType: string; ticketId: string; title?: string }
  | { status: 'failed'; error: string; ticketId?: string };

type WorkStatusAction =
  | { type: 'START_WORK'; payload: { agentType: string; task: string; ticketId: string } }
  | { type: 'COMPLETE_WORK'; payload: { agentType: string; ticketId: string; title?: string } }
  | { type: 'FAIL_WORK'; payload: { error: string; ticketId?: string } }
  | { type: 'CLEAR_STATUS' };

const initialState: WorkStatusState = { status: 'idle' };

function workStatusReducer(state: WorkStatusState, action: WorkStatusAction): WorkStatusState {
  switch (action.type) {
    case 'START_WORK':
      return {
        status: 'working',
        agentType: action.payload.agentType,
        task: action.payload.task,
        ticketId: action.payload.ticketId,
      };
    case 'COMPLETE_WORK':
      return {
        status: 'complete',
        agentType: action.payload.agentType,
        ticketId: action.payload.ticketId,
        title: action.payload.title,
      };
    case 'FAIL_WORK':
      return {
        status: 'failed',
        error: action.payload.error,
        ticketId: action.payload.ticketId,
      };
    case 'CLEAR_STATUS':
      return { status: 'idle' };
    default:
      return state;
  }
}

interface WorkStatusContextValue {
  state: WorkStatusState;
  startWork: (agentType: string, task: string, ticketId: string) => void;
  completeWork: (agentType: string, ticketId: string, title?: string) => void;
  failWork: (error: string, ticketId?: string) => void;
  clearStatus: () => void;
}

const WorkStatusContext = createContext<WorkStatusContextValue | null>(null);

export function WorkStatusProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(workStatusReducer, initialState);

  const startWork = useCallback((agentType: string, task: string, ticketId: string) => {
    dispatch({ type: 'START_WORK', payload: { agentType, task, ticketId } });
  }, []);

  const completeWork = useCallback((agentType: string, ticketId: string, title?: string) => {
    dispatch({ type: 'COMPLETE_WORK', payload: { agentType, ticketId, title } });
    // Auto-clear after 5 seconds
    setTimeout(() => {
      dispatch({ type: 'CLEAR_STATUS' });
    }, 5000);
  }, []);

  const failWork = useCallback((error: string, ticketId?: string) => {
    dispatch({ type: 'FAIL_WORK', payload: { error, ticketId } });
    // Auto-clear after 8 seconds (longer for errors)
    setTimeout(() => {
      dispatch({ type: 'CLEAR_STATUS' });
    }, 8000);
  }, []);

  const clearStatus = useCallback(() => {
    dispatch({ type: 'CLEAR_STATUS' });
  }, []);

  return (
    <WorkStatusContext.Provider value={{ state, startWork, completeWork, failWork, clearStatus }}>
      {children}
    </WorkStatusContext.Provider>
  );
}

export function useWorkStatus() {
  const context = useContext(WorkStatusContext);
  if (!context) {
    throw new Error('useWorkStatus must be used within WorkStatusProvider');
  }
  return context;
}
