'use client';

/**
 * Chat Page — YARNNN chat surface (ADR-167 v5, ADR-178, ADR-215 Phase 5).
 *
 * HOME route per ADR-205 F1. "Start new work" opens the TaskSetupModal
 * (ADR-178 two-route structured intent capture). Onboarding is conversational
 * with YARNNN per ADR-190 — no onboarding modal.
 */

import { useEffect } from 'react';
import { ChatSurface } from '@/components/chat-surface/ChatSurface';
import { useTP } from '@/contexts/TPContext';
import { useAgentsAndTasks } from '@/hooks/useAgentsAndTasks';

export default function HomePage() {
  const { loadScopedHistory } = useTP();
  const { agents, tasks, loading: dataLoading } = useAgentsAndTasks({ pollInterval: 60_000 });

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  return (
    <ChatSurface
      agents={agents}
      tasks={tasks}
      dataLoading={dataLoading}
    />
  );
}
