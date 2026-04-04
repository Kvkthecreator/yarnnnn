'use client';

/**
 * Agents Page — Primary working surface (HOME).
 *
 * SURFACE-ARCHITECTURE.md v3: Three-panel layout.
 * Left: AgentTreeNav (stable roster with task children)
 * Center: AgentContentView (class-aware: domain/output/observations)
 * Right: ChatPanel (agent-scoped TP, FAB toggle)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Loader2,
  MessageCircle,
  Users,
  ListChecks,
  Globe,
  Upload,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import type { Agent, Task } from '@/types';
import { api } from '@/lib/api/client';
import {
  AgentTreeNav,
  getDefaultAgentView,
  type AgentView,
} from '@/components/agents/AgentTreeNav';
import { AgentContentView } from '@/components/agents/AgentContentView';
import { ChatPanel } from '@/components/tp/ChatPanel';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';

export default function AgentsPage() {
  const searchParams = useSearchParams();
  const { sendMessage } = useTP();

  const agentFromUrl = searchParams.get('agent');

  // ── State ──
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [selectedTaskSlug, setSelectedTaskSlug] = useState<string | null>(null);
  const [selectedView, setSelectedView] = useState<AgentView>('domain');
  const [filter, setFilter] = useState<string | null>(null);

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
    loadData().then(({ agents: agentList }) => {
      // Auto-select agent from URL param or first with active tasks
      if (agentFromUrl) {
        const match = agentList.find(
          a => a.id === agentFromUrl || a.slug === agentFromUrl
        );
        if (match) {
          setSelectedAgentId(match.id);
          setSelectedView(getDefaultAgentView(match));
        }
      } else if (agentList.length > 0 && !selectedAgentId) {
        // Select first agent that has tasks, or just first agent
        const withTasks = agentList.find(a => a.agent_class === 'domain-steward');
        const first = withTasks || agentList[0];
        setSelectedAgentId(first.id);
        setSelectedView(getDefaultAgentView(first));
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

  // ── Derived state ──
  const selectedAgent = agents.find(a => a.id === selectedAgentId) || null;

  // Get agent slug for task grouping
  const getAgentSlug = (agent: Agent): string =>
    agent.slug || agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

  const agentTasks = selectedAgent
    ? tasks.filter(t => t.agent_slugs?.includes(getAgentSlug(selectedAgent)))
    : [];

  // ── Actions ──
  const handleSelectAgent = (agentId: string) => {
    const agent = agents.find(a => a.id === agentId);
    setSelectedAgentId(agentId);
    setSelectedTaskSlug(null);
    if (agent) setSelectedView(getDefaultAgentView(agent));
  };

  const handleSelectTask = (agentId: string, taskSlug: string) => {
    setSelectedAgentId(agentId);
    setSelectedTaskSlug(taskSlug);
    setSelectedView('task-output');
  };

  const handleBack = () => {
    setSelectedTaskSlug(null);
    if (selectedAgent) setSelectedView(getDefaultAgentView(selectedAgent));
  };

  const handleRunTask = async (taskSlug: string) => {
    setMutationPending(true);
    try {
      await api.tasks.run(taskSlug);
    } catch (err) {
      console.error('Failed to trigger task:', err);
    } finally {
      setMutationPending(false);
    }
  };

  const handleToggleTaskStatus = async (taskSlug: string) => {
    const task = tasks.find(t => t.slug === taskSlug);
    if (!task) return;
    setMutationPending(true);
    try {
      const newStatus = task.status === 'active' ? 'paused' : 'active';
      await api.tasks.update(taskSlug, { status: newStatus });
      await loadData();
    } catch (err) {
      console.error('Failed to toggle task status:', err);
    } finally {
      setMutationPending(false);
    }
  };

  // ── Chat plus menu (agent-scoped) ──
  const plusMenuActions: PlusMenuAction[] = selectedAgent ? [
    ...(agentTasks.filter(t => t.status === 'active').length > 0 ? [{
      id: 'run-task',
      label: `Run ${agentTasks[0]?.title || 'task'}`,
      icon: ListChecks,
      verb: 'prompt' as const,
      onSelect: () => { sendMessage(`Run the task "${agentTasks[0]?.title}" now`); },
    }] : []),
    {
      id: 'assign-task',
      label: 'Assign a new task',
      icon: ListChecks,
      verb: 'prompt' as const,
      onSelect: () => { /* ChatPanel handles */ },
    },
    {
      id: 'web-search',
      label: 'Web research',
      icon: Globe,
      verb: 'prompt' as const,
      onSelect: () => { /* ChatPanel handles */ },
    },
    {
      id: 'upload-file',
      label: 'Upload file',
      icon: Upload,
      verb: 'attach' as const,
      onSelect: () => { /* ChatPanel handles file upload */ },
    },
  ] : [{
    id: 'assign-task',
    label: 'Create a task',
    icon: ListChecks,
    verb: 'prompt' as const,
    onSelect: () => { /* ChatPanel handles */ },
  }];

  // ── Surface context ──
  const surfaceOverride = selectedTaskSlug
    ? { type: 'task-detail', taskSlug: selectedTaskSlug }
    : selectedAgent
    ? { type: 'agent-detail', agentSlug: getAgentSlug(selectedAgent) }
    : { type: 'chat' };

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
      {/* Left Panel — Agent Tree */}
      <div className="w-[280px] shrink-0 border-r border-border flex flex-col bg-background">
        <AgentTreeNav
          agents={agents}
          tasks={tasks}
          selectedAgentId={selectedAgentId}
          selectedTaskSlug={selectedTaskSlug}
          selectedView={selectedView}
          filter={filter}
          onFilterChange={setFilter}
          onSelectAgent={handleSelectAgent}
          onSelectTask={handleSelectTask}
          onSelectView={setSelectedView}
          onRunTask={handleRunTask}
          onToggleTaskStatus={handleToggleTaskStatus}
          busy={mutationPending}
        />
      </div>

      {/* Center Panel — Agent Content */}
      <div className="flex-1 min-w-0 flex flex-col bg-background">
        {selectedAgent ? (
          <AgentContentView
            agent={selectedAgent}
            tasks={agentTasks}
            view={selectedView}
            selectedTaskSlug={selectedTaskSlug}
            onBack={handleBack}
            onSelectTask={(slug) => handleSelectTask(selectedAgent.id, slug)}
            onRunTask={handleRunTask}
            busy={mutationPending}
          />
        ) : (
          <div className="flex items-center justify-center h-full p-8">
            <div className="text-center max-w-sm">
              <Users className="w-10 h-10 text-muted-foreground/15 mx-auto mb-3" />
              <h2 className="text-lg font-medium mb-1">Your agents</h2>
              <p className="text-sm text-muted-foreground">
                Select an agent to see what they know and what they&apos;re working on.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Right Panel — Chat (FAB toggle) */}
      {chatOpen ? (
        <div className="w-[380px] shrink-0 border-l border-border flex flex-col bg-background relative">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
            <span className="text-xs text-muted-foreground truncate">
              {selectedTaskSlug
                ? `viewing ${tasks.find(t => t.slug === selectedTaskSlug)?.title || selectedTaskSlug}`
                : selectedAgent
                ? `viewing ${selectedAgent.title}`
                : 'Chat'}
            </span>
            <button onClick={() => setChatOpen(false)} className="text-muted-foreground hover:text-foreground">
              <MessageCircle className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <ChatPanel
              surfaceOverride={surfaceOverride}
              plusMenuActions={plusMenuActions}
              placeholder={
                selectedTaskSlug ? `Steer ${tasks.find(t => t.slug === selectedTaskSlug)?.title || 'task'}...`
                : selectedAgent ? `Ask about ${selectedAgent.title}...`
                : 'Ask anything...'
              }
              showCommandPicker={false}
            />
          </div>
        </div>
      ) : (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-4 right-4 z-50 w-12 h-12 rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90 flex items-center justify-center transition-transform hover:scale-105"
          title="Open chat"
        >
          <MessageCircle className="w-5 h-5" />
        </button>
      )}
    </div>
  );
}
