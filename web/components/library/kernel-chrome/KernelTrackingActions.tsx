'use client';

/**
 * KernelTrackingActions — kernel-default chrome actions for
 * accumulates_context (ADR-225 Phase 3). Same shape as
 * KernelDeliverableActions today (Pause + Edit via OverflowMenu);
 * preserved as a distinct component so bundles can override one
 * kind without affecting the other.
 */

import { OverflowMenu } from './OverflowMenu';

export function KernelTrackingActions() {
  return <OverflowMenu />;
}
