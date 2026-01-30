'use client';

/**
 * ADR-016: TP Awareness Status
 * Shows current work status in the top bar
 */

import { Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { useWorkStatus } from '@/contexts/WorkStatusContext';
import { useSurface } from '@/contexts/SurfaceContext';
import { cn } from '@/lib/utils';

const agentLabels: Record<string, string> = {
  research: 'Research',
  content: 'Content',
  reporting: 'Report',
};

export function WorkStatus() {
  const { state, clearStatus } = useWorkStatus();
  const { openSurface } = useSurface();

  if (state.status === 'idle') {
    return null;
  }

  const handleClick = () => {
    if (state.status === 'complete' && 'ticketId' in state) {
      openSurface('output', { ticketId: state.ticketId });
      clearStatus();
    }
  };

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors",
        state.status === 'working' && "bg-primary/10 text-primary",
        state.status === 'complete' && "bg-green-500/10 text-green-600 cursor-pointer hover:bg-green-500/20",
        state.status === 'failed' && "bg-red-500/10 text-red-600"
      )}
      onClick={handleClick}
      role={state.status === 'complete' ? 'button' : undefined}
    >
      {state.status === 'working' && (
        <>
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="hidden sm:inline">
            {agentLabels[state.agentType] || state.agentType} working...
          </span>
          <span className="sm:hidden">Working...</span>
        </>
      )}

      {state.status === 'complete' && (
        <>
          <CheckCircle2 className="w-4 h-4" />
          <span className="hidden sm:inline">
            {state.title ? `${state.title.slice(0, 30)}${state.title.length > 30 ? '...' : ''}` : `${agentLabels[state.agentType] || state.agentType} complete`}
          </span>
          <span className="sm:hidden">Complete</span>
          <span className="text-xs opacity-70">· View</span>
        </>
      )}

      {state.status === 'failed' && (
        <>
          <XCircle className="w-4 h-4" />
          <span className="hidden sm:inline">
            Work failed
          </span>
          <span className="sm:hidden">Failed</span>
        </>
      )}
    </div>
  );
}
