'use client';

/**
 * KernelMaintenanceMetadata — kernel-default chrome for system_maintenance
 * (ADR-225 Phase 3). Back-office tasks own no user-authored objective;
 * metadata stays minimal.
 */

import { useWorkDetailActions } from '../WorkDetailActionsContext';
import { WorkModeBadge } from '@/components/work/WorkModeBadge';
import { formatRelativeTime } from '@/lib/formatting';

export function KernelMaintenanceMetadata() {
  const { task } = useWorkDetailActions();
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <WorkModeBadge schedule={task.schedule} />
      {task.schedule && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="capitalize">{task.schedule}</span>
        </>
      )}
      {task.last_run_at ? (
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
    </div>
  );
}
