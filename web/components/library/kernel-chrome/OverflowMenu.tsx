'use client';

/**
 * OverflowMenu — kernel chrome utility (ADR-225 Phase 3).
 *
 * Three-dot lifecycle menu used by KernelDeliverableActions and
 * KernelTrackingActions. Pause/Resume + Edit in chat. Reads handlers
 * from WorkDetailActionsContext.
 *
 * Originally inline in WorkDetail.tsx; extracted here as part of the
 * unified compositor seam refactor — chrome action components live in
 * the library, registered in LIBRARY_COMPONENTS, dispatched by the
 * resolver.
 */

import { useState, useRef, useEffect } from 'react';
import { MoreHorizontal, Pause, Play, MessageSquare } from 'lucide-react';
import { useWorkDetailActions } from '../WorkDetailActionsContext';

export function OverflowMenu() {
  const { task, mutationPending, onPauseTask, onEdit } = useWorkDetailActions();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const isActive = task.status === 'active';
  const isPaused = task.paused === true;
  const isTerminal = task.status === 'completed' || task.status === 'archived';

  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  if (isTerminal) return null;

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        disabled={mutationPending}
        className="inline-flex items-center justify-center w-7 h-7 rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50"
        aria-label="More actions"
      >
        <MoreHorizontal className="w-3.5 h-3.5" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-20 min-w-[140px] rounded-md border border-border bg-popover shadow-md py-1">
          {(isActive || isPaused) && (
            <button
              onClick={() => { setOpen(false); onPauseTask(task.slug); }}
              disabled={mutationPending}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50"
            >
              {isActive
                ? <><Pause className="w-3 h-3" /> Pause</>
                : <><Play className="w-3 h-3" /> Resume</>
              }
            </button>
          )}
          <button
            onClick={() => { setOpen(false); onEdit(); }}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted"
          >
            <MessageSquare className="w-3 h-3" /> Edit in chat
          </button>
        </div>
      )}
    </div>
  );
}
