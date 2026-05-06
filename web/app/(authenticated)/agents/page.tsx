'use client';

/**
 * Agents Page — Detail-only surface (ADR-167 v5, ADR-214, ADR-241).
 *
 * ADR-251: roster reinstated. `/agents` (no query param) shows the roster.
 * Two systemic entities: System Agent (?agent=system) + Reviewer (?agent=reviewer).
 *
 * Bookmark-safety redirects:
 *   ?agent=yarnnn → ?agent=system
 *   ?agent=thinking-partner → ?agent=system
 *   ?agent=yarnnn&tab=principles → ?agent=reviewer&tab=principles
 *   ?agent=yarnnn&tab=autonomy → ?agent=reviewer&tab=autonomy
 *
 * ?agent=reviewer renders ReviewerDetail directly — no redirect (ADR-251 D7).
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
import { useAgentsAndRecurrences } from '@/hooks/useAgentsAndRecurrences';
import { getAgentSlug } from '@/lib/agent-identity';
// ADR-241: AgentRosterSurface deleted (always-empty roster post-ADR-235 D2).
import { AgentContentView } from '@/components/agents/AgentContentView';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import { PageHeader } from '@/components/shell/PageHeader';
// RecurrenceSetupModal removed — creation via Chat
import type { PlusMenuAction } from '@/components/tp/PlusMenu';


export default function AgentsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { loadScopedHistory, sendMessage } = useTP();
  const { setBreadcrumb, clearBreadcrumb } = useBreadcrumb();
  const { agents, tasks, loading } = useAgentsAndRecurrences();

  const agentFromUrl = searchParams.get('agent');

  // ADR-251: roster reinstated — no default redirect when no agent param.
  // Bookmark-safety redirects for legacy ?agent=yarnnn and ?agent=thinking-partner URLs.
  useEffect(() => {
    if (agentFromUrl === 'yarnnn' || agentFromUrl === 'thinking-partner') {
      router.replace('/agents?agent=system', { scroll: false });
    }
    // ?agent=yarnnn&tab=principles|autonomy → ?agent=reviewer&tab=...
    const tab = searchParams.get('tab');
    if (agentFromUrl === 'yarnnn' && (tab === 'principles' || tab === 'autonomy')) {
      router.replace(`/agents?agent=reviewer&tab=${tab}`, { scroll: false });
    }
  }, [agentFromUrl, router, searchParams]);

  // Detail mode is determined by URL — no auto-selection (ADR-167).
  // ADR-251: ?agent=system maps to the meta-cognitive agent (System Agent).
  // ?agent=reviewer maps to the synthesized Reviewer pseudo-agent.
  const selectedAgent = useMemo(() => {
    if (!agentFromUrl) return null;
    if (agentFromUrl === 'system') {
      return agents.find(a => a.agent_class === 'meta-cognitive') ?? null;
    }
    if (agentFromUrl === 'reviewer') {
      return agents.find(a => a.agent_class === 'reviewer') ?? null;
    }
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

  // Chat config
  const surfaceOverride = selectedAgent
    ? { type: 'agent-detail' as const, agentId: selectedAgent.id }
    : undefined;

  const plusMenuActions: PlusMenuAction[] = useMemo(() => {
    if (selectedAgent) {
      const activeTasks = agentTasks.filter(t => t.status === 'active');
      return [
        ...(activeTasks.length > 0 ? [{
          id: 'run-recurrence',
          label: `Run ${activeTasks[0]?.title || 'work'}`,
          icon: Play,
          verb: 'prompt' as const,
          onSelect: () => { sendMessage(`Run "${activeTasks[0]?.title}" now`, { surface: surfaceOverride }); },
        }] : []),
        {
          id: 'assign-work',
          label: 'Assign new work',
          icon: ListChecks,
          verb: 'prompt' as const,
          onSelect: () => sendMessage(`I want to assign new work to ${selectedAgent.title} — `, { surface: surfaceOverride }),
        },
      ];
    }
    return [
      {
        id: 'create-task',
        label: 'Start new work',
        icon: ListChecks,
        verb: 'prompt' as const,
        onSelect: () => sendMessage('I want to set up some recurring work — ', { surface: surfaceOverride }),
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
        // ADR-251: roster landing — no agent selected. Shows two systemic cards.
        // Full AgentRosterSurface component is the follow-on; this is the interim
        // placeholder that signals the roster is the correct landing state.
        <div className="flex-1 overflow-auto p-6 max-w-3xl space-y-4">
          <p className="text-sm font-medium text-muted-foreground">Your workspace</p>
          <div className="grid grid-cols-2 gap-3">
            {agents.filter(a => a.agent_class === 'meta-cognitive').map(a => (
              <button
                key={a.id}
                onClick={() => router.push('/agents?agent=system')}
                className="text-left rounded-lg border border-border/60 bg-card px-4 py-3 hover:bg-muted/30 transition-colors"
              >
                <p className="text-sm font-medium">System Agent</p>
                <p className="text-xs text-muted-foreground mt-0.5">Executes declared work. Narrates what happened.</p>
              </button>
            ))}
            {agents.filter(a => a.agent_class === 'reviewer').map(a => (
              <button
                key={a.id}
                onClick={() => router.push('/agents?agent=reviewer')}
                className="text-left rounded-lg border border-border/60 bg-card px-4 py-3 hover:bg-muted/30 transition-colors"
              >
                <p className="text-sm font-medium">Reviewer</p>
                <p className="text-xs text-muted-foreground mt-0.5">Your judgment seat — independent verdicts on proposed actions.</p>
              </button>
            ))}
          </div>
        </div>
      )}
    </ThreePanelLayout>

    </>
  );
}
