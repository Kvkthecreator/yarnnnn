/**
 * Kernel-default declarations — chrome only (ADR-228).
 *
 * Per ADR-228, the cockpit is no longer a flat pane registry — it is
 * four faces rendered directly by `CockpitRenderer`. The
 * `KERNEL_DEFAULT_COCKPIT_PANES` array and `resolveCockpitPanes` resolver
 * are deleted. The compositor seam survives unchanged for /work detail
 * chrome composition (`KERNEL_DEFAULT_CHROME` below + `resolveChrome`).
 *
 * Singular Implementation discipline: this file IS the kernel default
 * chrome shape. Don't redefine kernel chrome anywhere else; consult and
 * register here.
 */

import type { ChromeDecl } from './types';

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
