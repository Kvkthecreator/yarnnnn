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
 * Kernel-default cockpit pane sequence — six-question framing
 * (2026-04-28). When `resolveCockpitPanes` finds no
 * `tabs.work.list.cockpit_panes` declaration in the active composition,
 * it returns this list.
 *
 * The six questions the operator asks of a delegation product, in order:
 *   1. "Did anything just break my trust?"        → TrustViolations
 *   2. "What's my standing intent right now?"     → MandateStrip
 *   3. "What needs my judgment right now?"        → KernelNeedsMePane
 *   4. "Where does the money stand?"              → MoneyTruthTile
 *   5. "What did the team do since I last looked?" → MaterialNarrativeStrip
 *   6. "Is the team itself healthy?"               → TeamHealthCard
 *
 * Order is deliberate: safety (#1) and standing-intent legibility (#2)
 * gate everything else — the operator must trust the rules + see their
 * own delegation contract before consuming downstream signal. #1
 * renders nothing 99% of the time (zero violations) so the strip
 * collapses to MandateStrip-on-top in the common case.
 *
 * Universal across program bundles. Bundles override panes when their
 * specific data calls for it (alpha-trader replaces NeedsMePane with
 * TradingProposalQueue, MoneyTruthTile binding with portfolio-shaped
 * substrate). Bundles never invent new questions; they specialize the
 * answers.
 */
export const KERNEL_DEFAULT_COCKPIT_PANES: ComponentDecl[] = [
  { kind: 'TrustViolations' },
  { kind: 'MandateStrip' },
  { kind: 'KernelNeedsMePane' },
  { kind: 'MoneyTruthTile' },
  { kind: 'MaterialNarrativeStrip' },
  { kind: 'TeamHealthCard' },
];
