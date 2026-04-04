'use client';

/**
 * Agents Page — Primary working surface (HOME).
 *
 * SURFACE-ARCHITECTURE.md v3: Three-panel layout.
 * Left: AgentTreeNav (stable roster with task children), collapsible
 * Center: AgentContentView (class-aware: domain/output/observations)
 * Right: ChatPanel (agent-scoped TP, FAB toggle with yarnnn logo)
 *
 * Duplicated from the original tasks page (b2aa309) — same layout patterns,
 * panel widths, FAB behavior, chat header, empty states, and polling.
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
  Settings2,
  X,
  Play,
  Target,
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
import {
  RUN_TASK_CARD,
  ADJUST_TASK_CARD,
  FEEDBACK_TASK_CARD,
  RESEARCH_TASK_CARD,
  type ActionCardConfig,
} from '@/components/tp/InlineActionCard';

export default function AgentsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { loadScopedHistory, sendMessage } = useTP();

  const agentFromUrl = searchParams.get('agent');
  const taskFromUrl = searchParams.get('task');

  // ── State ──
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [selectedTaskSlug, setSelectedTaskSlug] = useState<string | null>(taskFromUrl);
  const [selectedView, setSelectedView] = useState<AgentView>('domain');
  const [filter, setFilter] = useState<string | null>(null);

  const [panelOpen, setPanelOpen] = useState(true);
  const [chatOpen, setChatOpen] = useState(false);
  const [actionCard, setActionCard] = useState<ActionCardConfig | null>(null);
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
      if (agentFromUrl) {
        const match = agentList.find(
          a => a.id === agentFromUrl || a.slug === agentFromUrl
        );
        if (match) {
          setSelectedAgentId(match.id);
          setSelectedView(getDefaultAgentView(match));
        }
      } else if (agentList.length > 0) {
        const first = agentList.find(a => a.agent_class === 'domain-steward') || agentList[0];
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

  // ── Load scoped chat history on agent/task change ──
  useEffect(() => {
    if (selectedTaskSlug) {
      loadScopedHistory(undefined, selectedTaskSlug);
    } else if (selectedAgentId) {
      // Use agent ID for scoped history
      loadScopedHistory(selectedAgentId);
    }
  }, [selectedAgentId, selectedTaskSlug, loadScopedHistory]);

  // ── Derived state ──
  const selectedAgent = agents.find(a => a.id === selectedAgentId) || null;

  const getAgentSlug = (agent: Agent): string =>
    agent.slug || agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

  const agentTasks = selectedAgent
    ? tasks.filter(t => t.agent_slugs?.includes(getAgentSlug(selectedAgent)))
    : [];

  const displayTitle = selectedTaskSlug
    ? tasks.find(t => t.slug === selectedTaskSlug)?.title || selectedTaskSlug
    : selectedAgent?.title || 'Agents';

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
      await loadData();
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

  // ── Chat config ──
  const taskSurface = selectedTaskSlug
    ? { type: 'task-detail' as const, taskSlug: selectedTaskSlug }
    : selectedAgent
    ? { type: 'agent-detail' as const, agentSlug: getAgentSlug(selectedAgent!) }
    : undefined;

  const plusMenuActions: PlusMenuAction[] = selectedTaskSlug ? [
    // Task drill-down: task-specific actions with action cards
    { id: 'run-task', label: 'Run now', icon: Play, verb: 'prompt', onSelect: () => setActionCard(RUN_TASK_CARD) },
    { id: 'adjust-task', label: 'Adjust task', icon: Target, verb: 'prompt', onSelect: () => setActionCard(ADJUST_TASK_CARD) },
    { id: 'feedback', label: 'Give feedback', icon: MessageCircle, verb: 'prompt', onSelect: () => setActionCard(FEEDBACK_TASK_CARD) },
    { id: 'web-research', label: 'Web research', icon: Globe, verb: 'prompt', onSelect: () => setActionCard(RESEARCH_TASK_CARD) },
  ] : selectedAgent ? [
    // Agent selected: agent-level actions
    ...(agentTasks.filter(t => t.status === 'active').length > 0 ? [{
      id: 'run-task',
      label: `Run ${agentTasks[0]?.title || 'task'}`,
      icon: Play,
      verb: 'prompt' as const,
      onSelect: () => { sendMessage(`Run the task "${agentTasks[0]?.title}" now`); },
    }] : []),
    { id: 'assign-task', label: 'Assign a new task', icon: ListChecks, verb: 'prompt', onSelect: () => { sendMessage(`Create a new task for ${selectedAgent.title}`); } },
    { id: 'web-search', label: 'Web research', icon: Globe, verb: 'prompt', onSelect: () => { setChatOpen(true); } },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach' as const, onSelect: () => {} },
  ] : [
    // No agent: workspace-level actions
    { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt', onSelect: () => { sendMessage('I want to create a task. What do you suggest based on my context?'); } },
    { id: 'update-info', label: 'Update my info', icon: Settings2, verb: 'prompt', onSelect: () => { setChatOpen(true); } },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt', onSelect: () => { setChatOpen(true); } },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach', onSelect: () => {} },
  ];

  // Chat empty state — simple prompt, onboarding lives on /chat
  const chatEmptyState = (
    <div className="py-2 text-center">
      <MessageCircle className="mx-auto mb-1.5 h-5 w-5 text-muted-foreground/15" />
      <p className="text-[11px] text-muted-foreground/40">
        {selectedTaskSlug ? 'Ask anything about this task'
          : selectedAgent ? `Ask anything about ${selectedAgent.title}`
          : 'Select an agent to get started'}
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
      {/* Left: Agent tree nav — collapsible */}
      {panelOpen ? (
        <div className="w-[280px] shrink-0 border-r border-border flex flex-col bg-background">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
            <p className="text-sm font-medium text-foreground">Agents</p>
            <button onClick={() => setPanelOpen(false)} className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          {loading ? (
            <div className="flex items-center justify-center flex-1">
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            </div>
          ) : (
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
          )}
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
            view={selectedView}
            selectedTaskSlug={selectedTaskSlug}
            onBack={handleBack}
            onSelectTask={(slug) => handleSelectTask(selectedAgent.id, slug)}
            onRunTask={handleRunTask}
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
              {(selectedAgent || selectedTaskSlug) && (
                <span className="text-[10px] text-muted-foreground/50 truncate max-w-[160px]">
                  · viewing {displayTitle}
                </span>
              )}
            </div>
            <button onClick={() => setChatOpen(false)} className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <ChatPanel
              surfaceOverride={taskSurface}
              plusMenuActions={plusMenuActions}
              placeholder={selectedTaskSlug ? `Steer ${displayTitle}...` : selectedAgent ? `Ask about ${selectedAgent.title}...` : 'Ask anything or type / ...'}
              emptyState={chatEmptyState}
              showCommandPicker={!selectedTaskSlug && !selectedAgent}
              pendingActionConfig={actionCard}
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
