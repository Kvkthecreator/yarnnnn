'use client';

/**
 * Home Page — Two-panel layout: dashboard + TP chat.
 *
 * SURFACE-ARCHITECTURE.md v6: Dashboard left, TP chat right.
 * Returning users: daily briefing dashboard + chat side by side.
 * New users: ContextSetup overlay (full page).
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Globe, Upload, ListChecks, Settings2, X } from 'lucide-react';
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
  const [chatOpen, setChatOpen] = useState(true);

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

  // ── New user: full-page onboarding ──
  if (isNewUser && !hasMessages) {
    return (
      <div className="flex h-full items-center justify-center px-6 py-8 bg-background">
        <div className="w-full max-w-2xl">
          <ContextSetup onSubmit={(msg) => sendMessage(msg)} />
        </div>
      </div>
    );
  }

  // ── Returning user: two-panel layout ──
  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: Daily briefing dashboard */}
      <div className="flex-1 min-w-0 flex flex-col bg-background overflow-auto">
        <DailyBriefing
          agents={agents}
          tasks={tasks}
          hasMessages={hasMessages}
        />
      </div>

      {/* Right: TP chat panel */}
      {chatOpen && (
        <div className="w-[420px] shrink-0 border-l border-border flex flex-col bg-background overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-border bg-background z-10 shrink-0">
            <div className="flex items-center gap-2">
              <img src="/assets/logos/circleonly_yarnnn_1.svg" alt="" className="w-5 h-5" />
              <span className="text-xs font-medium">TP</span>
            </div>
            <button onClick={() => setChatOpen(false)} className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <ChatPanel
              surfaceOverride={{ type: 'chat' }}
              plusMenuActions={plusMenuActions}
              placeholder="Ask anything or type / ..."
              showCommandPicker={true}
            />
          </div>
        </div>
      )}

      {/* FAB when chat is closed */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition-all flex items-center justify-center group"
          title="Chat with TP"
        >
          <img
            src="/assets/logos/circleonly_yarnnn_1.svg"
            alt="yarnnn"
            className="w-12 h-12 transition-transform duration-500 group-hover:rotate-180"
          />
        </button>
      )}
    </div>
  );
}
