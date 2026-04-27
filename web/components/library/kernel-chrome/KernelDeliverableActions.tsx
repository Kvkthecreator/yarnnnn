'use client';

/**
 * KernelDeliverableActions — kernel-default chrome actions for
 * produces_deliverable (ADR-225 Phase 3). Pause/Resume + Edit in chat
 * via the OverflowMenu.
 */

import { OverflowMenu } from './OverflowMenu';

export function KernelDeliverableActions() {
  return <OverflowMenu />;
}
