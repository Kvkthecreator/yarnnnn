'use client';

/**
 * Agents Page — List/detail surface (ADR-167 v5).
 *
 * SURFACE-ARCHITECTURE.md v9.4: /agents is a single surface with two modes
 * selected by URL state. PageHeader is the breadcrumb chrome strip (no title,
 * no metadata) — the agent's visual identity lives inside AgentContentView
 * via <SurfaceIdentityHeader /> alongside the agent content it describes.
 */

import { useEffect, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  Loader2,
  MessageCircle,
  ListChecks,
  Play,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { useAgentsAndTasks } from '@/hooks/useAgentsAndTasks';
import { getAgentSlug } from '@/lib/agent-identity';
import { AgentRosterSurface } from '@/components/agents/AgentRosterSurface';
import { AgentContentView } from '@/components/agents/AgentContentView';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import { PageHeader } from '@/components/shell/PageHeader';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import type { Agent } from '@/types';

function buildCreateTaskPrompt(agent: Agent, hasExistingTasks: boolean): string {
  if (hasExistingTasks) {
    return `Create another task for ${agent.title} that fits this agent's role and current workload.`;
  }

  switch (agent.agent_class) {
    case 'platform-bot':
      return `Set up ${agent.title} and create its first recurring task. If the platform or sources are not ready, tell me what needs to be configured first.`;
    case 'synthesizer':
      return `Create the first reporting task for ${agent.title}, using active specialist inputs.`;
    case 'meta-cognitive':
      return `Create the core maintenance tasks for ${agent.title}.`;
    case 'specialist':
    case 'domain-steward': // backward compat for v4 DB rows
    default:
      return `Create the first recurring task for ${agent.title}.`;
  }
}

export default function AgentsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { loadScopedHistory, sendMessage } = useTP();
  const { setBreadcrumb, clearBreadcrumb } = useBreadcrumb();
  const { agents, tasks, loading } = useAgentsAndTasks();

  const agentFromUrl = searchParams.get('agent');

  // Detail mode is determined by URL — no auto-selection (ADR-167)
  const selectedAgent = useMemo(() => {
    if (!agentFromUrl) return null;
    return agents.find(a => a.id === agentFromUrl || getAgentSlug(a) === agentFromUrl) ?? null;
  }, [agentFromUrl, agents]);

  // Load chat history (unified session — once)
  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  const agentTasks = selectedAgent
    ? tasks.filter(t => t.agent_slugs?.includes(getAgentSlug(selectedAgent)))
    : [];

  // Breadcrumb (segment shape from b033513; PageHeader renders inline now)
  useEffect(() => {
    if (selectedAgent) {
      const slug = getAgentSlug(selectedAgent);
      setBreadcrumb([
        { label: 'Agents', href: '/agents', kind: 'surface' },
        { label: selectedAgent.title, href: `/agents?agent=${encodeURIComponent(slug)}`, kind: 'agent' },
      ]);
    } else {
      clearBreadcrumb();
    }
    return () => clearBreadcrumb();
  }, [selectedAgent?.id, selectedAgent?.title, setBreadcrumb, clearBreadcrumb]);

  // Click card in roster → URL transition to detail mode
  const handleSelectAgent = (id: string) => {
    const agent = agents.find(a => a.id === id);
    const slug = agent ? getAgentSlug(agent) : id;
    router.replace(`/agents?agent=${encodeURIComponent(slug)}`, { scroll: false });
  };

  // Chat config
  const surfaceOverride = selectedAgent
    ? { type: 'agent-detail' as const, agentId: selectedAgent.id }
    : undefined;

  const createTaskPrompt = selectedAgent
    ? buildCreateTaskPrompt(selectedAgent, agentTasks.length > 0)
    : null;

  const plusMenuActions: PlusMenuAction[] = useMemo(() => {
    if (selectedAgent) {
      const activeTasks = agentTasks.filter(t => t.status === 'active');
      return [
        ...(activeTasks.length > 0 ? [{
          id: 'run-task',
          label: `Run ${activeTasks[0]?.title || 'task'}`,
          icon: Play,
          verb: 'prompt' as const,
          onSelect: () => { sendMessage(`Run the task "${activeTasks[0]?.title}" now`, { surface: surfaceOverride }); },
        }] : []),
        { id: 'assign-task', label: 'Assign a new task', icon: ListChecks, verb: 'prompt' as const, onSelect: () => { sendMessage(createTaskPrompt || `Create a new task for ${selectedAgent.title}`, { surface: surfaceOverride }); } },
      ];
    }
    return [
      { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt' as const, onSelect: () => { sendMessage('I want to create a task. What do you suggest based on my context?'); } },
    ];
  }, [selectedAgent, agentTasks, createTaskPrompt, sendMessage, surfaceOverride]);

  const chatEmptyState = (
    <div className="py-2 text-center">
      <MessageCircle className="mx-auto mb-1.5 h-5 w-5 text-muted-foreground/15" />
      <p className="text-[11px] text-muted-foreground/40">
        {selectedAgent ? `Ask anything about ${selectedAgent.title}` : 'Ask anything about your team'}
      </p>
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <ThreePanelLayout
      chat={{
        surfaceOverride,
        plusMenuActions,
        placeholder: selectedAgent ? `Ask about ${selectedAgent.title}...` : 'Ask anything or type / ...',
        emptyState: chatEmptyState,
        showCommandPicker: !selectedAgent,
        contextLabel: selectedAgent ? `viewing ${selectedAgent.title}` : undefined,
        defaultOpen: true,
      }}
    >
      <PageHeader defaultLabel="Agents" />
      {selectedAgent ? (
        <AgentContentView
          agent={selectedAgent}
          tasks={agentTasks}
          onCreateTask={createTaskPrompt
            ? () => { sendMessage(createTaskPrompt, { surface: surfaceOverride }); }
            : undefined}
        />
      ) : (
        <AgentRosterSurface
          agents={agents}
          tasks={tasks}
          onSelect={handleSelectAgent}
        />
      )}
    </ThreePanelLayout>
  );
}
