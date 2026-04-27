'use client';

/**
 * KernelSnapshotPane — kernel-default cockpit pane (ADR-225 Phase 3).
 *
 * Money-truth + workforce + context tiles. The underlying
 * SnapshotPane component supports an `isDayZero` prop that the
 * cockpit caller never sets to true today; preserved as default-false
 * here for future use.
 */

import { SnapshotPane } from '@/components/work/briefing/SnapshotPane';

export function KernelSnapshotPane() {
  return <SnapshotPane />;
}
