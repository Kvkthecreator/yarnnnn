'use client';

/**
 * KernelMaintenanceMetadata — kernel-default chrome for system_maintenance
 * (ADR-225 Phase 3). Back-office tasks own no user-authored objective;
 * metadata stays minimal.
 */

import { useWorkDetailActions } from '../WorkDetailActionsContext';
import { WorkShapeBadge } from '@/components/work/WorkShapeBadge';
import { formatRelativeTime } from '@/lib/formatting';

export function KernelMaintenanceMetadata() {
  const { task } = useWorkDetailActions();
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <WorkShapeBadge schedule={task.schedule} />
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
