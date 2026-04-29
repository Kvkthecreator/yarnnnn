'use client';

/**
 * KernelDeliverableMetadata — kernel-default chrome for produces_deliverable
 * (ADR-225 Phase 3).
 *
 * One-line operational signal: mode badge · surface · assigned agent · schedule
 * · last output. Reads task + assignedAgent from WorkDetailActionsContext.
 *
 * Bundle middles for produces_deliverable tasks may override this via
 * MiddleDecl.chrome.metadata when the content area calls for non-generic
 * operational context (e.g., a portfolio dashboard wants substrate freshness,
 * not artifact age).
 */

import Link from 'next/link';
import { useWorkDetailActions } from '../WorkDetailActionsContext';
import { WorkShapeBadge } from '@/components/work/WorkShapeBadge';
import { AGENTS_ROUTE } from '@/lib/routes';
import { formatRelativeTime } from '@/lib/formatting';
import { coerceSurfaceType, SURFACE_TYPE_LABELS } from '@/lib/recurrence-shapes';
import type { RecurrenceDetail } from '@/types';

export function KernelDeliverableMetadata() {
  const { task, assignedAgent } = useWorkDetailActions();
  // ADR-231: surface_type comes from the declaration YAML, surfaced via
  // deliverable_spec.expected_output.surface. The legacy type_key fallback
  // is gone — type_key is dissolved per ADR-207 P4b + ADR-231 D5.
  const surface = coerceSurfaceType(
    (task as RecurrenceDetail).deliverable_spec?.expected_output?.surface,
  );
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <WorkShapeBadge schedule={task.schedule} />
      {surface && (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/50">
            {SURFACE_TYPE_LABELS[surface]}
          </span>
        </>
      )}
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
      {task.last_run_at ? (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span>Last output: {formatRelativeTime(task.last_run_at)}</span>
        </>
      ) : (
        <>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-muted-foreground/60">No output yet</span>
        </>
      )}
    </div>
  );
}
