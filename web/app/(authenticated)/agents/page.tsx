'use client';

/**
 * Agents Page — List/detail surface (ADR-167 v5, ADR-214).
 *
 * Per ADR-214 (2026-04-23), `/agents` is the canonical cockpit surface for
 * judgment-bearing entities (ADR-212 taxonomy): Systemic agents (YARNNN +
 * Reviewer) + Domain agents (user-authored). Route reverses ADR-201; /team
 * retains a bookmark-safety redirect stub.
 *
 * Single surface, two modes, selected by URL state (?agent={slug|reviewer|yarnnn}).
 * PageHeader is the breadcrumb chrome strip (no title, no metadata) — the
 * agent's visual identity lives inside AgentContentView via
 * <SurfaceIdentityHeader /> alongside the agent content it describes.
 *
 * Reviewer is synthesized as a systemic pseudo-agent in the list response
 * (api/routes/agents.py list_agents), substrate stays filesystem-first per
 * ADR-194 v2.
 */

import { useEffect, useMemo, useState } from 'react';
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
import { TaskSetupModal } from '@/components/chat-surface/TaskSetupModal';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';


export default function AgentsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { loadScopedHistory, sendMessage } = useTP();
  const { setBreadcrumb, clearBreadcrumb } = useBreadcrumb();
  const { agents, tasks, loading } = useAgentsAndTasks();
  const [taskSetupOpen, setTaskSetupOpen] = useState(false);
  const [taskSetupNotes, setTaskSetupNotes] = useState('');

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
        {
          id: 'assign-task',
          label: 'Assign a new task',
          icon: ListChecks,
          verb: 'show' as const,
          onSelect: () => {
            setTaskSetupNotes(`For ${selectedAgent.title}.`);
            setTaskSetupOpen(true);
          },
        },
      ];
    }
    return [
      {
        id: 'create-task',
        label: 'Start new work',
        icon: ListChecks,
        verb: 'show' as const,
        onSelect: () => { setTaskSetupNotes(''); setTaskSetupOpen(true); },
      },
    ];
  }, [selectedAgent, agentTasks, sendMessage, surfaceOverride]);

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
    <>
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
        />
      ) : (
        <AgentRosterSurface
          agents={agents}
          tasks={tasks}
          onSelect={handleSelectAgent}
        />
      )}
    </ThreePanelLayout>

    <TaskSetupModal
      open={taskSetupOpen}
      onClose={() => setTaskSetupOpen(false)}
      onSubmit={(msg) => { setTaskSetupOpen(false); sendMessage(msg, { surface: surfaceOverride }); }}
      initialNotes={taskSetupNotes}
    />
    </>
  );
}
