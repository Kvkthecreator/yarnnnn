'use client';

/**
 * Chat Page - TP chat surface.
 *
 * ADR-165 revision: chat remains the single primary surface. Structured
 * artifacts render inline through a tab switcher rather than floating windows.
 */

import { useEffect, useMemo } from 'react';
import { Globe, Upload, ListChecks, Settings2 } from 'lucide-react';
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
    { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt' as const, onSelect: () => sendMessage('I want to create a task. What do you suggest based on my context?') },
    { id: 'update-context', label: 'Update my context', icon: Settings2, verb: 'prompt' as const, onSelect: () => {} },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt' as const, onSelect: () => {} },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach' as const, onSelect: () => {} },
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
