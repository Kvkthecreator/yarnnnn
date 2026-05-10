'use client';

/**
 * MiddleResolver — ADR-225 dispatch component for WorkDetail content area.
 *
 * Phase I (post-merge sweep, 2026-05-10): output_kind dispatch DELETED
 * per ADR-261 D1's "one execution shape" principle and ADR-262 §6.1
 * resolution. Every recurrence's substrate lives at the slug-templated
 * path `/workspace/reports/{slug}/{date}/output.md` (per CONVENTIONS
 * topology); `DeliverableMiddle` is the universal viewer that reads
 * those dated outputs and degrades gracefully ("No past outputs yet")
 * for reactive recurrences and recurrences that haven't fired yet.
 *
 * Resolution flow:
 *   1. Consult bundle SURFACES.yaml via composition. If a bundle middle
 *      matches by `task_slug` (Tier 1 — the only surviving match axis
 *      post-Phase I), render its components through the shared registry.
 *   2. Otherwise, render `DeliverableMiddle` universally.
 *
 * The legacy per-shape middles (TrackingEntityGrid, ActionMiddle,
 * MaintenanceMiddle, TrackingMiddle) are DELETED per ADR-261's
 * unified-execution-shape framing — there is one substrate convention,
 * one viewer.
 *
 * Singular Implementation discipline: ONE dispatch path lives here.
 */

import type { RecurrenceDetail } from '@/types';
import type { Recurrence } from '@/types';
import { resolveMiddle, getDetailMiddles, useComposition } from '@/lib/compositor';

import { dispatchComponent } from './registry';

import { DeliverableMiddle } from '@/components/work/details/DeliverableMiddle';

interface MiddleResolverProps {
  task: Recurrence | RecurrenceDetail;
  refreshKey: number;
  onSourcesUpdated?: () => void;
}

export function MiddleResolver({ task, refreshKey }: MiddleResolverProps) {
  const { data: composition } = useComposition();

  // Try bundle-supplied middles first (task_slug match — Tier 1)
  const bundleMiddles = getDetailMiddles(composition.composition, 'work');
  const resolvedMiddle = resolveMiddle(
    {
      task: { slug: task.slug },
    },
    bundleMiddles,
  );

  if (resolvedMiddle) {
    const bindings = resolvedMiddle.bindings ?? {};
    return (
      <div className="space-y-3">
        {resolvedMiddle.components.map((component, idx) => (
          <div key={`${component.kind}-${idx}`}>
            {dispatchComponent(component, bindings)}
          </div>
        ))}
      </div>
    );
  }

  // Universal fallback: every recurrence renders as a deliverable view.
  // Per ADR-261 D1 + ADR-262 D1: one substrate convention
  // (/workspace/reports/{slug}/{date}/output.md), one viewer.
  const taskDetail = task as RecurrenceDetail;
  return (
    <DeliverableMiddle
      taskSlug={task.slug}
      refreshKey={refreshKey}
      deliverableSpec={taskDetail.deliverable_spec}
    />
  );
}
