'use client';

/**
 * Home Page — Daily briefing + unscoped TP chat.
 *
 * SURFACE-ARCHITECTURE.md v4: The Home page (nav label "Home", route /chat).
 * Returning users see a persistent collapsible daily briefing above the chat.
 * New users (0 tasks) see ContextSetup onboarding overlay.
 *
 * The briefing never disappears — it auto-collapses to a one-line summary
 * after the first message, and the user can expand/collapse at any time.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Globe, Upload, ListChecks, Settings2 } from 'lucide-react';
import { ChatPanel } from '@/components/tp/ChatPanel';
import { ContextSetup } from '@/components/tp/ContextSetup';
import { DailyBriefing } from '@/components/home/DailyBriefing';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import { useTP } from '@/contexts/TPContext';
import type { Agent, Task } from '@/types';
import { api } from '@/lib/api/client';

export default function HomePage() {
  const { messages, sendMessage, isLoading, loadScopedHistory } = useTP();
  const hasMessages = messages.length > 0 || isLoading;

  // ── Data for briefing ──
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [dataLoaded, setDataLoaded] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [agentList, taskList] = await Promise.all([
        api.agents.list(),
        api.tasks.list(),
      ]);
      setAgents(agentList);
      setTasks(taskList);
    } catch {
      // Silently fail — briefing will show empty state
    } finally {
      setDataLoaded(true);
    }
  }, []);

  // Load global session history + briefing data
  useEffect(() => {
    loadScopedHistory();
    loadData();
  }, [loadScopedHistory, loadData]);

  // Refresh briefing data every 60s
  useEffect(() => {
    const interval = setInterval(loadData, 60_000);
    return () => clearInterval(interval);
  }, [loadData]);

  const hasTasks = tasks.length > 0;
  const isNewUser = dataLoaded && !hasTasks;

  // Plus menu actions — workspace-level
  const plusMenuActions: PlusMenuAction[] = useMemo(() => [
    { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt' as const, onSelect: () => sendMessage('I want to create a task. What do you suggest based on my context?') },
    { id: 'update-context', label: 'Update my context', icon: Settings2, verb: 'prompt' as const, onSelect: () => {} },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt' as const, onSelect: () => {} },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach' as const, onSelect: () => {} },
  ], [sendMessage]);

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto w-full relative">
      {/* Daily briefing — persistent header for returning users */}
      {hasTasks && (
        <DailyBriefing
          agents={agents}
          tasks={tasks}
          hasMessages={hasMessages}
        />
      )}

      {/* ChatPanel always renders — handles messages + input bar */}
      <ChatPanel
        surfaceOverride={{ type: 'chat' }}
        plusMenuActions={plusMenuActions}
        placeholder={hasMessages ? 'Ask anything or type / ...' : hasTasks ? 'Ask anything or type / ...' : 'Or just type here...'}
        showCommandPicker={true}
      />

      {/* Onboarding overlay — only for new users (no tasks) */}
      {isNewUser && !hasMessages && (
        <div className="absolute inset-0 bottom-[72px] flex items-center justify-center px-6 py-8 bg-background z-10">
          <div className="w-full max-w-xl">
            <ContextSetup
              onSubmit={(msg) => sendMessage(msg)}
              showSkipOptions
              onSkipAction={(msg) => sendMessage(msg)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
