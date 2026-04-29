'use client';

/**
 * KernelActionMetadata — kernel-default chrome for external_action
 * (ADR-225 Phase 3).
 */

import Link from 'next/link';
import { useWorkDetailActions } from '../WorkDetailActionsContext';
import { WorkShapeBadge } from '@/components/work/WorkShapeBadge';
import { AGENTS_ROUTE } from '@/lib/routes';
import { formatRelativeTime } from '@/lib/formatting';

export function KernelActionMetadata() {
  const { task, assignedAgent } = useWorkDetailActions();
  const target = (task.delivery && task.delivery !== 'none')
    ? task.delivery
    : task.objective?.audience || null;

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
      {target && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Target: {target}</span>
        </>
      )}
      {task.last_run_at ? (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Last fired: {formatRelativeTime(task.last_run_at)}</span>
        </>
      ) : (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-muted-foreground/60">Never fired</span>
        </>
      )}
    </div>
  );
}
