/**
 * Kernel-default declarations — chrome only (ADR-228 + Phase I post-merge
 * sweep, 2026-05-10).
 *
 * Phase I: per ADR-261 D1's "one execution shape" + ADR-262 D1's slug-
 * templated convention, the per-output_kind chrome variant map collapses
 * to a single universal chrome. Bundle middles that target a specific
 * recurrence by slug may still override `metadata` and/or `actions` via
 * the `chrome` field on `MiddleDecl`.
 *
 * Singular Implementation discipline: this file IS the universal kernel
 * default chrome. Don't redefine kernel chrome anywhere else; consult
 * and register here.
 */

import type { ChromeDecl } from './types';

/**
 * Universal kernel-default chrome. Resolved by `resolveChrome` whenever
 * no bundle middle matches the task's slug, or when the matched middle
 * provides a partial chrome override.
 */
export const KERNEL_DEFAULT_CHROME: ChromeDecl = {
  metadata: { kind: 'KernelDeliverableMetadata' },
  actions: [{ kind: 'KernelDeliverableActions' }],
};
