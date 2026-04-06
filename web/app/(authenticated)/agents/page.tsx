'use client';

/**
 * Agents Page — Primary working surface (HOME).
 *
 * SURFACE-ARCHITECTURE.md v4: Three-panel layout.
 * Left: AgentNav (flat roster, click to select)
 * Center: AgentContentView (three-tab: Agent / Setup / Settings)
 * Right: ChatPanel (agent-scoped TP, FAB toggle with yarnnn logo)
 */

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  Loader2,
  MessageCircle,
  Users,
  ListChecks,
  Globe,
  Upload,
  X,
  Play,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import type { Agent, Task } from '@/types';
import { api } from '@/lib/api/client';
import { AgentTreeNav } from '@/components/agents/AgentTreeNav';
import { AgentContentView } from '@/components/agents/AgentContentView';
import { ChatPanel } from '@/components/tp/ChatPanel';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';

export default function AgentsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { loadScopedHistory, sendMessage } = useTP();

  const agentFromUrl = searchParams.get('agent');

  // ── State ──
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  const [panelOpen, setPanelOpen] = useState(true);
  const [chatOpen, setChatOpen] = useState(false);
  const [mutationPending, setMutationPending] = useState(false);

  // ── Data loading ──
  const loadData = useCallback(async () => {
    try {
      const [agentList, taskList] = await Promise.all([
        api.agents.list(),
        api.tasks.list(),
      ]);
      setAgents(agentList);
      setTasks(taskList);
      return { agents: agentList, tasks: taskList };
    } catch {
      setAgents([]);
      setTasks([]);
      return { agents: [], tasks: [] };
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Initial load ──
  useEffect(() => {
    loadData().then(({ agents: agentList, tasks: taskList }) => {
      if (agentFromUrl) {
        const match = agentList.find(a => a.id === agentFromUrl || a.slug === agentFromUrl);
        if (match) setSelectedAgentId(match.id);
      } else if (agentList.length > 0) {
        // Select the most recently active agent (has tasks with recent runs),
        // falling back to first domain-steward, then first agent
        const agentWithRecentTask = agentList.find(a => {
          const slug = a.slug || a.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
          return taskList.some((t: Task) => t.agent_slugs?.includes(slug) && t.status === 'active');
        });
        const first = agentWithRecentTask
          || agentList.find(a => a.agent_class === 'domain-steward')
          || agentList[0];
        setSelectedAgentId(first.id);
      }
    });
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  // ── Polling (30s) ──
  useEffect(() => {
    const interval = setInterval(loadData, 30_000);
    return () => clearInterval(interval);
  }, [loadData]);

  // Refresh on tab focus
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') loadData();
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [loadData]);

  // ── Load scoped chat history on agent change ──
  useEffect(() => {
    if (selectedAgentId) loadScopedHistory(selectedAgentId);
  }, [selectedAgentId, loadScopedHistory]);

  // ── Derived state ──
  const selectedAgent = agents.find(a => a.id === selectedAgentId) || null;

  const getAgentSlug = (agent: Agent): string =>
    agent.slug || agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

  const agentTasks = selectedAgent
    ? tasks.filter(t => t.agent_slugs?.includes(getAgentSlug(selectedAgent)))
    : [];

  // ── Actions ──
  const handleSelectAgent = (agentId: string) => {
    setSelectedAgentId(agentId);
  };

  const handleRunTask = async (taskSlug: string) => {
    setMutationPending(true);
    try {
      await api.tasks.run(taskSlug);
      await loadData();
    } catch (err) {
      console.error('Failed to trigger task:', err);
    } finally {
      setMutationPending(false);
    }
  };

  const handlePauseTask = async (taskSlug: string) => {
    setMutationPending(true);
    try {
      const task = tasks.find(t => t.slug === taskSlug);
      const newStatus = task?.status === 'active' ? 'paused' : 'active';
      await api.tasks.update(taskSlug, { status: newStatus });
      await loadData();
    } catch (err) {
      console.error('Failed to update task:', err);
    } finally {
      setMutationPending(false);
    }
  };

  const handleOpenChat = (prompt?: string) => {
    setChatOpen(true);
    if (prompt) sendMessage(prompt);
  };

  // ── Chat config ──
  const surfaceOverride = selectedAgent
    ? { type: 'agent-detail' as const, agentSlug: getAgentSlug(selectedAgent) }
    : undefined;

  const plusMenuActions: PlusMenuAction[] = selectedAgent ? [
    ...(agentTasks.filter(t => t.status === 'active').length > 0 ? [{
      id: 'run-task',
      label: `Run ${agentTasks[0]?.title || 'task'}`,
      icon: Play,
      verb: 'prompt' as const,
      onSelect: () => { sendMessage(`Run the task "${agentTasks[0]?.title}" now`); },
    }] : []),
    { id: 'assign-task', label: 'Assign a new task', icon: ListChecks, verb: 'prompt' as const, onSelect: () => { sendMessage(`Create a new task for ${selectedAgent.title}`); } },
    { id: 'web-search', label: 'Web research', icon: Globe, verb: 'prompt' as const, onSelect: () => { setChatOpen(true); } },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach' as const, onSelect: () => {} },
  ] : [
    { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt' as const, onSelect: () => { sendMessage('I want to create a task. What do you suggest based on my context?'); } },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt' as const, onSelect: () => { setChatOpen(true); } },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach' as const, onSelect: () => {} },
  ];

  const chatEmptyState = (
    <div className="py-2 text-center">
      <MessageCircle className="mx-auto mb-1.5 h-5 w-5 text-muted-foreground/15" />
      <p className="text-[11px] text-muted-foreground/40">
        {selectedAgent ? `Ask anything about ${selectedAgent.title}` : 'Select an agent to get started'}
      </p>
    </div>
  );

  // ── Render ──
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: Agent roster — collapsible */}
      {panelOpen ? (
        <div className="w-[280px] shrink-0 border-r border-border flex flex-col bg-background">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
            <p className="text-sm font-medium text-foreground">Agents</p>
            <button onClick={() => setPanelOpen(false)} className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <AgentTreeNav
            agents={agents}
            tasks={tasks}
            selectedAgentId={selectedAgentId}
            onSelectAgent={handleSelectAgent}
          />
        </div>
      ) : (
        <div className="w-10 shrink-0 border-r border-border flex flex-col items-center py-2 gap-2 bg-background">
          <button
            onClick={() => setPanelOpen(true)}
            className="p-2 rounded-md text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
            title="Agents"
          >
            <Users className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Center: Agent content */}
      <div className="flex-1 min-w-0 flex flex-col bg-background">
        {selectedAgent ? (
          <AgentContentView
            agent={selectedAgent}
            tasks={agentTasks}
            onRunTask={handleRunTask}
            onPauseTask={handlePauseTask}
            onOpenChat={handleOpenChat}
            busy={mutationPending}
          />
        ) : agents.length === 0 ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="max-w-sm text-center">
              <Users className="w-10 h-10 text-muted-foreground/15 mx-auto mb-3" />
              <h2 className="text-lg font-medium mb-1">No agents yet</h2>
              <p className="text-sm text-muted-foreground mb-4">
                Set up your workspace first, then your agent roster will appear.
              </p>
              <button
                onClick={() => router.push('/context')}
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Set up workspace
              </button>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
            Select an agent from the panel
          </div>
        )}
      </div>

      {/* Right: Chat panel or FAB */}
      {chatOpen && (
        <div className="w-[380px] shrink-0 border-l border-border flex flex-col bg-background overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-border bg-background z-10 shrink-0">
            <div className="flex items-center gap-2">
              <img src="/assets/logos/circleonly_yarnnn_1.svg" alt="" className="w-5 h-5" />
              <span className="text-xs font-medium">TP</span>
              {selectedAgent && (
                <span className="text-[10px] text-muted-foreground/50 truncate max-w-[160px]">
                  · viewing {selectedAgent.title}
                </span>
              )}
            </div>
            <button onClick={() => setChatOpen(false)} className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <ChatPanel
              surfaceOverride={surfaceOverride}
              plusMenuActions={plusMenuActions}
              placeholder={selectedAgent ? `Ask about ${selectedAgent.title}...` : 'Ask anything or type / ...'}
              emptyState={chatEmptyState}
              showCommandPicker={!selectedAgent}
            />
          </div>
        </div>
      )}

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
