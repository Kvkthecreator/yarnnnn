'use client';

/**
 * Agents Page — List/detail surface (ADR-167 + v2 amendment).
 *
 * SURFACE-ARCHITECTURE.md v9.1: /agents is a single surface with two modes
 * selected by URL state. PageHeader is rendered as the first row of the
 * center surface, replacing the floating breadcrumb bar AND the per-page
 * AgentHeader inside AgentContentView. The breadcrumb's last segment IS the
 * page title — no duplication.
 */

import { useEffect, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  Loader2,
  MessageCircle,
  ListChecks,
  Globe,
  Upload,
  Play,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { useAgentsAndTasks } from '@/hooks/useAgentsAndTasks';
import type { Agent } from '@/types';
import { AgentRosterSurface } from '@/components/agents/AgentRosterSurface';
import { AgentContentView } from '@/components/agents/AgentContentView';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import { PageHeader } from '@/components/shell/PageHeader';
import { formatRelativeTime } from '@/lib/formatting';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';

// Singular, user-facing class labels. Must stay in sync with the section
// titles in AgentRosterSurface.tsx. "Thinking Partner" matches the agent
// title itself so is intentionally omitted when rendering alongside it.
const CLASS_LABELS: Record<string, string> = {
  'domain-steward': 'Specialist',
  'synthesizer': 'Reporting',
  'platform-bot': 'Integration',
  'meta-cognitive': 'Thinking Partner',
};

function getAgentSlug(agent: Agent): string {
  return agent.slug || agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
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
        {selectedAgent ? `Ask anything about ${selectedAgent.title}` : 'Ask anything about your team'}
      </p>
    </div>
  );

  // ─── Detail-mode subtitle: identity metadata strip (ADR-167 v2) ───
  // Replaces the AgentHeader band that used to live inside AgentContentView.
  const detailSubtitle = selectedAgent ? (() => {
    const cls = selectedAgent.agent_class || 'domain-steward';
    const classLabel = CLASS_LABELS[cls] || cls;
    const domain = selectedAgent.context_domain;
    const activeTaskCount = agentTasks.filter(t => t.status === 'active').length;
    const lastRun = agentTasks
      .map(t => t.last_run_at)
      .filter(Boolean)
      .sort()
      .reverse()[0] || selectedAgent.last_run_at || null;

    return (
      <div className="flex items-center gap-1.5 flex-wrap">
        <span>{classLabel}</span>
        {domain && (
          <>
            <span className="text-muted-foreground/30">·</span>
            <span>{domain}/</span>
          </>
        )}
        <span className="text-muted-foreground/30">·</span>
        <span>{activeTaskCount} active {activeTaskCount === 1 ? 'task' : 'tasks'}</span>
        {lastRun && (
          <>
            <span className="text-muted-foreground/30">·</span>
            <span>Ran {formatRelativeTime(lastRun)}</span>
          </>
        )}
      </div>
    );
  })() : undefined;

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
      }}
    >
      <PageHeader
        defaultLabel="Agents"
        subtitle={detailSubtitle}
      />
      {selectedAgent ? (
        <AgentContentView
          agent={selectedAgent}
          tasks={agentTasks}
          onOpenChat={(prompt) => sendMessage(prompt || '')}
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
