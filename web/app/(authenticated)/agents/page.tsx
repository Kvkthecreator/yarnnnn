'use client';

/**
 * Agents Page — Roster + identity (ADR-163 Surface Restructure).
 *
 * Answers exactly one question: "Who is this agent, and are they healthy?"
 *
 * Left: AgentTreeNav (flat roster, click to select)
 * Center: Identity card (AGENT.md, role, origin, creation) + Health card
 *         (tasks assigned, approval rate, last run) + links out to /work
 *         and /context
 * Right: ChatPanel via ThreePanelLayout (agent-scoped TP)
 *
 * Work observation (Pipeline, Report) moved to /work surface per ADR-163.
 * Domain entity browsing (Data) moved to /context?domain= per ADR-163.
 */

import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Loader2,
  MessageCircle,
  Users,
  ListChecks,
  Globe,
  Upload,
  Play,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { useAgentsAndTasks } from '@/hooks/useAgentsAndTasks';
import type { Agent } from '@/types';
import { AgentTreeNav } from '@/components/agents/AgentTreeNav';
import { AgentContentView } from '@/components/agents/AgentContentView';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';

function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <p className="text-sm text-muted-foreground/30">Select an agent</p>
    </div>
  );
}

export default function AgentsPage() {
  const searchParams = useSearchParams();
  const { loadScopedHistory, sendMessage } = useTP();
  const { setBreadcrumb, clearBreadcrumb } = useBreadcrumb();
  const { agents, tasks, loading } = useAgentsAndTasks();

  const agentFromUrl = searchParams.get('agent');

  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  // Auto-select from URL on first load
  useEffect(() => {
    if (agentFromUrl && agents.length > 0 && !selectedAgentId) {
      const match = agents.find(a => a.id === agentFromUrl || a.slug === agentFromUrl);
      if (match) setSelectedAgentId(match.id);
    }
  }, [agentFromUrl, agents, selectedAgentId]);

  // Load chat history (unified session — once)
  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  // Derived state
  const selectedAgent = agents.find(a => a.id === selectedAgentId) || null;

  const getAgentSlug = (agent: Agent): string =>
    agent.slug || agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

  const agentTasks = selectedAgent
    ? tasks.filter(t => t.agent_slugs?.includes(getAgentSlug(selectedAgent)))
    : [];

  // Breadcrumb
  useEffect(() => {
    if (selectedAgent) {
      setBreadcrumb([{ label: selectedAgent.title }]);
    } else {
      clearBreadcrumb();
    }
    return () => clearBreadcrumb();
  }, [selectedAgent?.id, selectedAgent?.title, setBreadcrumb, clearBreadcrumb]);

  // ADR-163: Run/pause task actions moved to /work. The Agents page is
  // now roster + identity + health only — no work mutations here.

  // Chat config
  const surfaceOverride = selectedAgent
    ? { type: 'agent-detail' as const, agentSlug: getAgentSlug(selectedAgent) }
    : undefined;

  const plusMenuActions: PlusMenuAction[] = useMemo(() => {
    if (selectedAgent) {
      const activeTasks = agentTasks.filter(t => t.status === 'active');
      return [
        ...(activeTasks.length > 0 ? [{
          id: 'run-task',
          label: `Run ${activeTasks[0]?.title || 'task'}`,
          icon: Play,
          verb: 'prompt' as const,
          onSelect: () => { sendMessage(`Run the task "${activeTasks[0]?.title}" now`); },
        }] : []),
        { id: 'assign-task', label: 'Assign a new task', icon: ListChecks, verb: 'prompt' as const, onSelect: () => { sendMessage(`Create a new task for ${selectedAgent.title}`); } },
        { id: 'web-search', label: 'Web research', icon: Globe, verb: 'prompt' as const, onSelect: () => {} },
        { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach' as const, onSelect: () => {} },
      ];
    }
    return [
      { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt' as const, onSelect: () => { sendMessage('I want to create a task. What do you suggest based on my context?'); } },
      { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt' as const, onSelect: () => {} },
      { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach' as const, onSelect: () => {} },
    ];
  }, [selectedAgent, agentTasks, sendMessage]);

  const chatEmptyState = (
    <div className="py-2 text-center">
      <MessageCircle className="mx-auto mb-1.5 h-5 w-5 text-muted-foreground/15" />
      <p className="text-[11px] text-muted-foreground/40">
        {selectedAgent ? `Ask anything about ${selectedAgent.title}` : 'Select an agent to get started'}
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
      leftPanel={{
        title: 'Agents',
        content: (
          <AgentTreeNav
            agents={agents}
            tasks={tasks}
            selectedAgentId={selectedAgentId}
            onSelectAgent={setSelectedAgentId}
          />
        ),
        collapsedIcon: <Users className="w-4 h-4" />,
        collapsedTitle: 'Agents',
      }}
      chat={{
        surfaceOverride,
        plusMenuActions,
        placeholder: selectedAgent ? `Ask about ${selectedAgent.title}...` : 'Ask anything or type / ...',
        emptyState: chatEmptyState,
        showCommandPicker: !selectedAgent,
        contextLabel: selectedAgent ? `viewing ${selectedAgent.title}` : undefined,
      }}
    >
      {selectedAgent ? (
        <AgentContentView
          agent={selectedAgent}
          tasks={agentTasks}
          onOpenChat={(prompt) => sendMessage(prompt || '')}
        />
      ) : (
        <EmptyState />
      )}
    </ThreePanelLayout>
  );
}
