'use client';

/**
 * Library Component Registry — ADR-225 Phase 3, amended by ADR-228.
 *
 * The dispatch table mapping component `kind` strings (declared
 * in SURFACES.yaml or `kernel-defaults.ts`) to React renderers.
 *
 * Singular Implementation discipline: this is THE registry. Kernel
 * defaults and bundle middle components register here side-by-side; the
 * resolver doesn't distinguish them.
 *
 * Cockpit faces (MandateFace · MoneyTruthFace · PerformanceFace ·
 * TrackingFace) are NOT registered here — they are imported directly by
 * `CockpitRenderer.tsx`. The cockpit no longer dispatches through this
 * registry per ADR-228; only /work detail middles + chrome do.
 *
 * Components are invoked via React.createElement so the registry can
 * stay shape-agnostic — the only convention is that a registered
 * renderer accepts `LibraryComponentProps`. Components that don't need
 * all props ignore them.
 */

import type { Binding } from '@/lib/compositor';

// Kernel-default chrome
import { KernelDeliverableMetadata } from './kernel-chrome/KernelDeliverableMetadata';
import { KernelTrackingMetadata } from './kernel-chrome/KernelTrackingMetadata';
import { KernelActionMetadata } from './kernel-chrome/KernelActionMetadata';
import { KernelMaintenanceMetadata } from './kernel-chrome/KernelMaintenanceMetadata';
import { KernelDeliverableActions } from './kernel-chrome/KernelDeliverableActions';
import { KernelTrackingActions } from './kernel-chrome/KernelTrackingActions';
import { KernelActionActions } from './kernel-chrome/KernelActionActions';
import { KernelMaintenanceActions } from './kernel-chrome/KernelMaintenanceActions';

/**
 * Standard prop bag passed to every library component. Components
 * destructure only what they need; React context (e.g.,
 * WorkDetailActionsContext) carries cross-cutting state.
 */
export interface LibraryComponentProps {
  source?: string;
  binding?: Binding;
  filters?: Record<string, unknown>;
}

export type LibraryComponent = (props: LibraryComponentProps) => JSX.Element | null;

export const LIBRARY_COMPONENTS: Record<string, LibraryComponent> = {
  // Kernel-default chrome — register here so the resolver can dispatch
  // them through the same path as bundle components.
  KernelDeliverableMetadata: () => <KernelDeliverableMetadata />,
  KernelTrackingMetadata: () => <KernelTrackingMetadata />,
  KernelActionMetadata: () => <KernelActionMetadata />,
  KernelMaintenanceMetadata: () => <KernelMaintenanceMetadata />,
  KernelDeliverableActions: () => <KernelDeliverableActions />,
  KernelTrackingActions: () => <KernelTrackingActions />,
  KernelActionActions: () => <KernelActionActions />,
  KernelMaintenanceActions: () => <KernelMaintenanceActions />,
};

/**
 * Helper to resolve a binding to a single path string when the binding
 * is path-shaped. action_proposals + narrative bindings don't have a
 * single path; components handle those filter-based.
 */
export function resolveBindingPath(binding: Binding | undefined): string | undefined {
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
      return undefined;
    default:
      return undefined;
  }
}

/**
 * Render a single ComponentDecl through the library dispatch. Used by
 * both MiddleResolver (middle content) and ChromeRenderer (chrome).
 *
 * Falls through to an amber warning box if the kind is unregistered —
 * matches the prior MiddleResolver behavior. Singular implementation
 * for "library component not found" UX.
 */
import type { ComponentDecl } from '@/lib/compositor';

export function dispatchComponent(
  decl: ComponentDecl,
  bindings?: Record<string, Binding>,
): JSX.Element {
  const Renderer = LIBRARY_COMPONENTS[decl.kind];
  if (!Renderer) {
    return (
      <div
        className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"
      >
        Component <code className="font-mono">{decl.kind}</code> referenced in
        composition but not registered in the system component library.
      </div>
    );
  }

  // Binding resolution priority: inline → named → undefined
  const inline = decl.binding;
  const named = decl.source && bindings ? bindings[decl.source] : undefined;
  const binding = inline ?? named;
  const sourcePath = resolveBindingPath(binding);

  return (
    <Renderer
      source={sourcePath}
      binding={binding}
      filters={decl.filters}
    />
  );
}
