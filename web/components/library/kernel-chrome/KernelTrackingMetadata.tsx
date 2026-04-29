'use client';

/**
 * KernelTrackingMetadata — kernel-default chrome for accumulates_context
 * (ADR-225 Phase 3).
 */

import Link from 'next/link';
import { useWorkDetailActions } from '../WorkDetailActionsContext';
import { WorkShapeBadge } from '@/components/work/WorkShapeBadge';
import { AGENTS_ROUTE, CONTEXT_ROUTE } from '@/lib/routes';
import { formatRelativeTime } from '@/lib/formatting';
import { resolveDomainWorkspacePath } from '@/lib/recurrence-shapes';

export function KernelTrackingMetadata() {
  const { task, assignedAgent } = useWorkDetailActions();
  const writes = task.context_writes ?? [];
  const primaryDomain = writes.find(d => d !== 'signals') ?? writes[0] ?? null;

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <WorkShapeBadge schedule={task.schedule} />
      {assignedAgent && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <Link
            href={`${AGENTS_ROUTE}?agent=${assignedAgent.slug}`}
            className="hover:text-foreground hover:underline"
          >
            {assignedAgent.title}
          </Link>
        </>
      )}
      {task.schedule && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="capitalize">{task.schedule}</span>
        </>
      )}
      {task.next_run_at ? (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Next: {formatRelativeTime(task.next_run_at)}</span>
        </>
      ) : task.last_run_at ? (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Last run: {formatRelativeTime(task.last_run_at)}</span>
        </>
      ) : (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-muted-foreground/60">Never run</span>
        </>
      )}
      {primaryDomain && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <Link
            href={`${CONTEXT_ROUTE}?path=${encodeURIComponent(resolveDomainWorkspacePath(primaryDomain))}`}
            className="text-primary hover:underline text-[11px]"
          >
            → {resolveDomainWorkspacePath(primaryDomain)}/
          </Link>
        </>
      )}
    </div>
  );
}
