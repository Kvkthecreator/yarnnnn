'use client';

/**
 * MiddleResolver — ADR-225 dispatch component for WorkDetail content area.
 *
 * Phase 2 (shipped): replaced the hardcoded KindMiddle switch in
 * WorkDetail.tsx. Phase 3 (this commit): the LIBRARY_COMPONENTS registry
 * lifted to `registry.tsx` so MiddleResolver and ChromeRenderer share
 * one dispatch table. Bundle components and kernel-default chrome
 * register side-by-side; the resolver doesn't distinguish them.
 *
 * Resolution flow:
 *   1. Consult bundle SURFACES.yaml via composition (4-tier match).
 *   2. If bundle middle matches, render its components through the
 *      shared registry.
 *   3. Otherwise, fall through to the kernel-default kind-middles
 *      (DeliverableMiddle / TrackingEntityGrid / ActionMiddle /
 *      MaintenanceMiddle) — these stay at web/components/work/details/
 *      per Phase 2 implementation refinement (ADR-225 §5).
 *
 * The kernel-default middles for output_kind dispatch have NOT moved
 * into LIBRARY_COMPONENTS — they take task-specific props (taskSlug,
 * deliverableSpec, refreshKey, onSourcesUpdated) the registry doesn't
 * thread. They remain as the local fallback path here. See
 * docs/architecture/compositor.md for the full rationale.
 *
 * Singular Implementation discipline: ONE dispatch path lives here.
 */

import type { TaskDetail } from '@/types';
import type { Task } from '@/types';
import { resolveMiddle, getDetailMiddles, useComposition } from '@/lib/compositor';

import { dispatchComponent } from './registry';

import { ActionMiddle } from '@/components/work/details/ActionMiddle';
import { DeliverableMiddle } from '@/components/work/details/DeliverableMiddle';
import { MaintenanceMiddle } from '@/components/work/details/MaintenanceMiddle';
import { TrackingEntityGrid } from '@/components/work/details/TrackingEntityGrid';

interface MiddleResolverProps {
  task: Task | TaskDetail;
  refreshKey: number;
  onSourcesUpdated?: () => void;
}

export function MiddleResolver({ task, refreshKey, onSourcesUpdated }: MiddleResolverProps) {
  const { data: composition } = useComposition();

  // Try bundle-supplied middles first (4-tier match resolution)
  const bundleMiddles = getDetailMiddles(composition.composition, 'work');
  const resolvedMiddle = resolveMiddle(
    {
      task: {
        slug: task.slug,
        output_kind: task.output_kind ?? null,
      },
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

  // Fall through to kernel-default kind-middles per ADR-225 §5
  switch (task.output_kind) {
    case 'accumulates_context':
      return <TrackingEntityGrid task={task} onSourcesUpdated={onSourcesUpdated} />;
    case 'external_action':
      return (
        <ActionMiddle
          task={task}
          refreshKey={refreshKey}
          onSourcesUpdated={onSourcesUpdated}
        />
      );
    case 'system_maintenance':
      return <MaintenanceMiddle task={task} refreshKey={refreshKey} />;
    case 'produces_deliverable':
    default: {
      const taskDetail = task as TaskDetail;
      return (
        <DeliverableMiddle
          taskSlug={task.slug}
          refreshKey={refreshKey}
          deliverableSpec={taskDetail.deliverable_spec}
        />
      );
    }
  }
}
