'use client';

/**
 * KernelSinceLastLookPane — kernel-default cockpit pane (ADR-225 Phase 3).
 * Temporal changes since last session — pure read.
 */

import { SinceLastLookPane } from '@/components/work/briefing/SinceLastLookPane';

export function KernelSinceLastLookPane() {
  return <SinceLastLookPane />;
}
