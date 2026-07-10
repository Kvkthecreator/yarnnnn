'use client';

/**
 * Library Component Registry — ADR-225 Phase 3, amended by ADR-228, ADR-273.
 *
 * The dispatch table mapping component `kind` strings (declared
 * in SURFACES.yaml or `kernel-defaults.ts`) to React renderers.
 *
 * Singular Implementation discipline: this is THE registry. Kernel
 * defaults, /work detail middles, chrome components, and bundle program-
 * section components register here side-by-side; the resolver doesn't
 * distinguish them by registration shape — the folder location does (per
 * ADR-273 D1: kernel-general at library/ root, program-specific at
 * library/programs/{slug}/).
 *
 * Post-ADR-273 Phase 2: the Home DOES dispatch through this registry —
 * program_sections render via dispatchComponent({ kind }) (alpha-trader's
 * SURFACES.yaml lists TraderRegime / TraderPortfolio / TraderMoneyTruth /
 * TraderExpectancy / TraderPositions / TraderSignals / TraderOrders).
 * HomeHeader (the Constitution band; renamed from CockpitHeader by ADR-312)
 * stays imported directly because it's always-rendered Layer 1, not
 * declaratively composed.
 *
 * Components are invoked via React.createElement so the registry can
 * stay shape-agnostic — the only convention is that a registered
 * renderer accepts `LibraryComponentProps`. Components that don't need
 * all props ignore them.
 */

import type { Binding } from '@/lib/compositor';

// Kernel-default chrome (Phase I post-merge sweep, 2026-05-10):
// per-output_kind variants (Tracking/Action/Maintenance) collapsed into
// the universal Deliverable variants per ADR-261 D1's "one execution
// shape." Kept registered under their original names as no-op aliases
// so any bundle SURFACES.yaml that still references them by string
// keeps rendering against the universal chrome.
import { KernelDeliverableMetadata } from './kernel-chrome/KernelDeliverableMetadata';
import { KernelDeliverableActions } from './kernel-chrome/KernelDeliverableActions';

// ADR-435 (2026-07-10) — the kernel-universal Home slots (KernelDecisionQueue /
// KernelRecentArtifacts / KernelJudgmentTrail) and ALL program-cockpit sections
// (alpha-trader Trader*, alpha-author Author*) were DELETED with the Home
// surface. They rendered ONLY through `home.program_sections` via ProgramCockpit
// (Home was their sole consumer). Their concerns live on their own mirror
// surfaces now (queue, activity, files). What remains registered below is only
// the WorkDetail chrome pair, which MiddleResolver + ChromeRenderer still use.

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
  // them through the same path as bundle components. Phase I (ADR-261 D1
  // "one execution shape") collapsed the per-output_kind chrome map to
  // a single universal pair. KERNEL_DEFAULT_CHROME in
  // web/lib/compositor/kernel-defaults.ts references only these two.
  KernelDeliverableMetadata: () => <KernelDeliverableMetadata />,
  KernelDeliverableActions: () => <KernelDeliverableActions />,

  // ADR-435 — the Home-slot components (KernelDecisionQueue / *RecentArtifacts /
  // *JudgmentTrail) and every program-cockpit section (Trader* / Author*) were
  // deleted with the Home surface (their sole consumer). Only the WorkDetail
  // chrome pair above remains — dispatched by MiddleResolver + ChromeRenderer.
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
