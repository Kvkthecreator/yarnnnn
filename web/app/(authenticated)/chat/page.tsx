'use client';

/**
 * Chat Page — TP chat surface (ADR-165 v7, ADR-167 v5).
 *
 * The page is the dedicated TP chat product. The workspace state surface
 * is a TP-directed modal — TP opens it via the workspace-state marker, the
 * user opens it via the toggle in the surface header. No always-on artifact
 * strip, no cold-start auto-open from the frontend.
 *
 * Context capture lives inside the modal as the `context` peer lens (one of
 * four peer tabs: context | briefing | recent | gaps). Cold-start acts as a
 * soft gate via `isEmpty` — the switcher is hidden until the workspace has
 * any content, after which "Add context" becomes a reachable peer tab for
 * re-entry. No separate plus-menu action.
 */

import { useEffect, useMemo } from 'react';
import { ListChecks } from 'lucide-react';
import { ChatSurface } from '@/components/chat-surface/ChatSurface';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import { useTP } from '@/contexts/TPContext';
import { useAgentsAndTasks } from '@/hooks/useAgentsAndTasks';

export default function HomePage() {
  const { sendMessage, loadScopedHistory } = useTP();
  const { agents, tasks, loading: dataLoading } = useAgentsAndTasks({ pollInterval: 60_000 });

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  const plusMenuActions: PlusMenuAction[] = useMemo(() => [
    {
      id: 'create-task',
      label: 'Create a task',
      icon: ListChecks,
      verb: 'prompt',
      onSelect: () => sendMessage('I want to create a task. What do you suggest based on my context?'),
    },
  ], [sendMessage]);

  return (
    <ChatSurface
      agents={agents}
      tasks={tasks}
      dataLoading={dataLoading}
      plusMenuActions={plusMenuActions}
      onContextSubmit={(msg) => sendMessage(msg)}
    />
  );
}
