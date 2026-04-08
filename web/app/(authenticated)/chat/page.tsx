'use client';

/**
 * Chat Page — TP chat surface (ADR-165 v5).
 *
 * The page is the dedicated TP chat product. Workspace state is opened
 * on demand by TP (via the workspace-state marker) or by the user (via
 * the input-row icon). No always-on artifact strip.
 *
 * The "Update my context" plus-menu action is owned by ChatSurface itself,
 * since ContextSetup is the surface's empty-lead view.
 */

import { useEffect, useMemo } from 'react';
import { ListChecks } from 'lucide-react';
import { ChatSurface } from '@/components/chat-surface/ChatSurface';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import { useTP } from '@/contexts/TPContext';
import { useAgentsAndTasks } from '@/hooks/useAgentsAndTasks';

export default function HomePage() {
  const { messages, sendMessage, isLoading, loadScopedHistory } = useTP();
  const hasMessages = messages.length > 0 || isLoading;
  const { agents, tasks, loading: dataLoading } = useAgentsAndTasks({ pollInterval: 60_000 });

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  const hasTasks = tasks.length > 0;
  const isNewUser = !dataLoading && !hasTasks;

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
      isNewUser={isNewUser && !hasMessages}
      plusMenuActions={plusMenuActions}
      onContextSubmit={(msg) => sendMessage(msg)}
    />
  );
}
