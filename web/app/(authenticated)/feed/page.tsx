'use client';

/**
 * Feed Page — YARNNN feed surface (ADR-259, renames ADR-167 v5 chat surface).
 *
 * HOME route per ADR-205 F1. The feed is the operator's primary view —
 * chronological, multi-actor, continuously-updating timeline. Operator messages
 * are one entry mode; Reviewer decisions, System Agent narrations, recurrence
 * completions all land here. "Start new work" opens the RecurrenceSetupModal
 * (ADR-178 two-route structured intent capture). Onboarding is conversational
 * with YARNNN per ADR-190 — no onboarding modal. Mid-conversation awareness
 * lives in the SnapshotModal (ADR-215 Phase 6).
 */

import { useEffect } from 'react';
import { FeedSurface } from '@/components/feed-surface/FeedSurface';
import { useNarrative } from '@/contexts/NarrativeContext';

export default function HomePage() {
  const { loadScopedHistory } = useNarrative();

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  // Post-2026-05-14 context-modal refactor: FeedSurface no longer needs
  // tasks prop. The modal's Pulse section reads its own activity data
  // via api.agents.reviewerActivity() and api.proposals.list().
  return <FeedSurface />;
}
