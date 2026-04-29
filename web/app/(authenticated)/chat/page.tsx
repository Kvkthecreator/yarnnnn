'use client';

/**
 * Chat Page — YARNNN chat surface (ADR-167 v5, ADR-178, ADR-215 Phase 6).
 *
 * HOME route per ADR-205 F1. "Start new work" opens the TaskSetupModal
 * (ADR-178 two-route structured intent capture). Onboarding is conversational
 * with YARNNN per ADR-190 — no onboarding modal. Mid-conversation awareness
 * lives in the SnapshotModal (ADR-215 Phase 6).
 */

import { useEffect } from 'react';
import { ChatSurface } from '@/components/chat-surface/ChatSurface';
import { useTP } from '@/contexts/TPContext';
import { useAgentsAndRecurrences } from '@/hooks/useAgentsAndRecurrences';

export default function HomePage() {
  const { loadScopedHistory } = useTP();
  const { tasks } = useAgentsAndRecurrences({ pollInterval: 60_000 });

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  return <ChatSurface tasks={tasks} />;
}
