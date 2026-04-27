'use client';

/**
 * MiddleResolver — ADR-225 dispatch component.
 *
 * Replaces WorkDetail.tsx::KindMiddle hardcoded switch. Consults the
 * compositor (bundle SURFACES.yaml resolved server-side at
 * /api/programs/surfaces), matches the active task against bundle-
 * supplied middles[], renders bundle components when matched, falls
 * through to existing kernel-default kind-middles when no bundle middle
 * applies.
 *
 * Per ADR-225 §5: existing kind-middles (DeliverableMiddle,
 * TrackingEntityGrid, ActionMiddle, MaintenanceMiddle) ARE the kernel
 * defaults. The Phase 2 implementation refinement keeps them at their
 * existing location (web/components/work/details/) — they're imported
 * here as the fallback path. Library reorg is deferred until bundles
 * surface a new component that demands a flat library namespace.
 *
 * Singular Implementation discipline: ONE dispatch path lives here.
 * The deleted KindMiddle switch and this resolver do not coexist.
 */

import type { MiddleDecl, Binding } from '@/lib/compositor';
import { resolveMiddle, getDetailMiddles, useComposition } from '@/lib/compositor';
import type { Task, TaskDetail } from '@/types';

import { ActionMiddle } from '@/components/work/details/ActionMiddle';
import { DeliverableMiddle } from '@/components/work/details/DeliverableMiddle';
import { MaintenanceMiddle } from '@/components/work/details/MaintenanceMiddle';
import { TrackingEntityGrid } from '@/components/work/details/TrackingEntityGrid';

import { PerformanceSnapshot } from './PerformanceSnapshot';
import { PositionsTable } from './PositionsTable';
import { RiskBudgetGauge } from './RiskBudgetGauge';
import { TradingProposalQueue } from './TradingProposalQueue';

interface MiddleResolverProps {
  task: Task | TaskDetail;
  refreshKey: number;
  onSourcesUpdated?: () => void;
}

// ---------------------------------------------------------------------------
// Library component dispatch
// ---------------------------------------------------------------------------
//
// Map of library component `kind` → renderer. New library components register
// here when they ship. Per ADR-225 §3 component contract: components accept
// either a `source` string (resolved from bindings dict) or an inline binding.

const LIBRARY_COMPONENTS: Record<
  string,
  (props: { source?: string; binding?: Binding; filters?: Record<string, unknown> }) => JSX.Element | null
> = {
  PerformanceSnapshot: ({ source }) =>
    source ? <PerformanceSnapshot source={source} /> : null,
  PositionsTable: ({ source }) =>
    source ? <PositionsTable source={source} /> : null,
  RiskBudgetGauge: ({ source }) =>
    source ? <RiskBudgetGauge source={source} /> : null,
  TradingProposalQueue: ({ filters }) => <TradingProposalQueue filters={filters} />,
};

// ---------------------------------------------------------------------------
// Bundle-middle renderer — declarative, shape-agnostic
// ---------------------------------------------------------------------------

function resolveBindingPath(binding: Binding | undefined): string | undefined {
  if (!binding) return undefined;
  switch (binding.type) {
    case 'file':
    case 'frontmatter':
    case 'directory':
      return binding.path;
    case 'task_output':
      return `/tasks/${binding.task_slug}/outputs/${binding.selector ?? 'latest'}`;
    case 'action_proposals':
    case 'narrative':
      return undefined; // these don't resolve to a single path; handled by component-specific filter
    default:
      return undefined;
  }
}

function renderBundleMiddle(middle: MiddleDecl): JSX.Element {
  const bindings = middle.bindings ?? {};

  return (
    <div className="space-y-3">
      {middle.components.map((component, idx) => {
        const Renderer = LIBRARY_COMPONENTS[component.kind];
        if (!Renderer) {
          return (
            <div
              key={`${component.kind}-${idx}`}
              className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"
            >
              Component <code className="font-mono">{component.kind}</code> referenced in
              SURFACES.yaml but not registered in the system component library.
            </div>
          );
        }

        // Resolve binding for this component:
        //   1. component.binding (inline)
        //   2. middle.bindings[component.source] (named binding from middle dict)
        const inline = component.binding;
        const named = component.source ? bindings[component.source] : undefined;
        const binding = inline ?? named;
        const sourcePath = resolveBindingPath(binding);

        return (
          <Renderer
            key={`${component.kind}-${idx}`}
            source={sourcePath}
            binding={binding}
            filters={component.filters}
          />
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// MiddleResolver — the public component
// ---------------------------------------------------------------------------

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
    return renderBundleMiddle(resolvedMiddle);
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
