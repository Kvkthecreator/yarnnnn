'use client';

/**
 * Chat Page — TP chat surface (ADR-165 v7, ADR-167 v5, ADR-178).
 *
 * "Start new work" opens the TaskSetupModal — a two-screen structured
 * intent capture that composes a complete message TP can act on in one turn.
 * The plus-menu action and modal state are owned by ChatSurface.
 */

import { useEffect } from 'react';
import { ChatSurface } from '@/components/chat-surface/ChatSurface';
import { useTP } from '@/contexts/TPContext';
import { useAgentsAndTasks } from '@/hooks/useAgentsAndTasks';

export default function HomePage() {
  const { sendMessage, loadScopedHistory } = useTP();
  const { agents, tasks, loading: dataLoading } = useAgentsAndTasks({ pollInterval: 60_000 });

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  return (
    <ChatSurface
      agents={agents}
      tasks={tasks}
      dataLoading={dataLoading}
      onContextSubmit={(msg) => sendMessage(msg)}
    />
  );
}
