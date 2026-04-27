/**
 * Kernel-default declarations — ADR-225 Phase 3.
 *
 * The single source of truth for what the cockpit looks like in the
 * absence of a bundle override. Per ADR-225 Phase 3 §3.2: kernel-defaults
 * are themselves library components dispatched by `kind`. The resolver
 * doesn't distinguish "kernel" from "bundle" — both are component
 * declarations matched against `LIBRARY_COMPONENTS`.
 *
 * Singular Implementation discipline: this file IS the kernel default
 * shape. Don't redefine kernel chrome anywhere else; consult and
 * register here.
 */

import type { ChromeDecl, ComponentDecl } from './types';

/**
 * Kernel-default chrome per output_kind. When `resolveChrome` finds no
 * bundle middle (or a bundle middle without a `chrome` field) for a
 * task, it falls back to this registry.
 *
 * Bundle middles that declare `chrome` may provide a partial override
 * (only `metadata`, only `actions`, or both); missing parts inherit
 * from this registry.
 */
export const KERNEL_DEFAULT_CHROME: Record<string, ChromeDecl> = {
  produces_deliverable: {
    metadata: { kind: 'KernelDeliverableMetadata' },
    actions: [{ kind: 'KernelDeliverableActions' }],
  },
  accumulates_context: {
    metadata: { kind: 'KernelTrackingMetadata' },
    actions: [{ kind: 'KernelTrackingActions' }],
  },
  external_action: {
    metadata: { kind: 'KernelActionMetadata' },
    actions: [{ kind: 'KernelActionActions' }],
  },
  system_maintenance: {
    metadata: { kind: 'KernelMaintenanceMetadata' },
    actions: [{ kind: 'KernelMaintenanceActions' }],
  },
};

/**
 * Kernel-default cockpit pane sequence. When `resolveCockpitPanes`
 * finds no `tabs.work.list.cockpit_panes` declaration in the active
 * composition, it returns this list.
 *
 * Order matches ADR-206 deliverables-first: NeedsMe (proposals,
 * most urgent) → Snapshot (money-truth) → SinceLastLook (temporal
 * changes) → Intelligence (synthesis).
 */
export const KERNEL_DEFAULT_COCKPIT_PANES: ComponentDecl[] = [
  { kind: 'KernelNeedsMePane' },
  { kind: 'KernelSnapshotPane' },
  { kind: 'KernelSinceLastLookPane' },
  { kind: 'KernelIntelligenceCard' },
];
