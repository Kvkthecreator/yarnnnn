'use client';

/**
 * WorkDetailActionsContext — ADR-225 Phase 3.
 *
 * The context that threads action handlers + per-task state from
 * WorkDetail into kernel-default chrome components (and any
 * bundle-supplied chrome components that opt in).
 *
 * Singular Implementation discipline: this is the single channel by
 * which chrome components reach lifecycle actions (run, pause, edit
 * in chat) and surface state (mutationPending, actionNotice). The
 * deleted per-kind action clusters in WorkDetail.tsx took these as
 * direct props — those clusters are gone; this context replaces the
 * plumbing.
 */

import { createContext, useContext } from 'react';
import type { Agent, Recurrence } from '@/types';

export interface WorkDetailActionsContextValue {
  task: Recurrence;
  agents: Agent[];
  assignedAgent: Agent | null;
  mutationPending: boolean;
  pendingAction: 'run' | 'pause' | null;
  actionNotice: { kind: 'info' | 'success' | 'error'; text: string } | null;
  onRunTask: (slug: string) => void;
  onPauseTask: (slug: string) => void;
  onEdit: (prompt?: string) => void;
}

const WorkDetailActionsContext = createContext<WorkDetailActionsContextValue | null>(null);

export const WorkDetailActionsProvider = WorkDetailActionsContext.Provider;

export function useWorkDetailActions(): WorkDetailActionsContextValue {
  const ctx = useContext(WorkDetailActionsContext);
  if (!ctx) {
    throw new Error(
      'useWorkDetailActions must be used inside <WorkDetailActionsProvider> — '
      + 'kernel-chrome and bundle-chrome components are rendered through the '
      + 'compositor seam (ADR-225 Phase 3) and require the actions context.',
    );
  }
  return ctx;
}
