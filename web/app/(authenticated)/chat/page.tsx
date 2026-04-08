'use client';

/**
 * Chat Page — TP chat surface (ADR-165 v6).
 *
 * The page is the dedicated TP chat product. The workspace state surface
 * is a TP-directed modal — TP opens it via the workspace-state marker, the
 * user opens it via the input-row icon. No always-on artifact strip, no
 * cold-start auto-open from the frontend.
 *
 * The "Update my context" plus-menu action is owned by ChatSurface itself,
 * since ContextSetup is the modal's empty-lead view.
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
