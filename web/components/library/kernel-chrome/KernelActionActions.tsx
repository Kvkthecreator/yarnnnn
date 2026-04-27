'use client';

/**
 * KernelActionActions — kernel-default chrome actions for external_action
 * (ADR-225 Phase 3). "Fire" button (immediate trigger) + Edit in chat.
 * No Pause — reactive tasks are not on a schedule.
 */

import { Loader2, MessageSquare, Send } from 'lucide-react';
import { useWorkDetailActions } from '../WorkDetailActionsContext';

export function KernelActionActions() {
  const { task, mutationPending, pendingAction, onRunTask, onEdit } = useWorkDetailActions();
  const isFiring = mutationPending && pendingAction === 'run';
  const isTerminal = task.status === 'completed' || task.status === 'archived';

  return (
    <>
      {!isTerminal && (
        <button
          onClick={() => onRunTask(task.slug)}
          disabled={mutationPending}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-50"
        >
          {isFiring
            ? <Loader2 className="w-3 h-3 animate-spin" />
            : <Send className="w-3 h-3" />
          }
          Fire
        </button>
      )}
      {!isTerminal && (
        <button
          onClick={() => onEdit()}
          className="inline-flex items-center justify-center w-7 h-7 rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
          aria-label="Edit in chat"
          title="Edit in chat"
        >
          <MessageSquare className="w-3.5 h-3.5" />
        </button>
      )}
    </>
  );
}
