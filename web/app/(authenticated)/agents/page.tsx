'use client';

/**
 * Agents Page — Reviewer + Domain Agents (ADR-272 Phase 2).
 *
 * Post-ADR-272: System Agent dissolved as a cockpit entity. The roster
 * shows the Reviewer (systemic) + user-authored Domain Agents only. The
 * orchestration LLM identity (formerly labeled "System Agent") persists
 * as chat-mode substrate behind /feed; it is not rendered here. System
 * activity (recurrence health, last-run timestamps, mechanical vs judgment
 * distinction) surfaces on /work Schedule tab.
 *
 * Legacy URL handling:
 *   ?agent=yarnnn → 404-clean (redirect block deleted per ADR-272 D7)
 *   ?agent=thinking-partner → 404-clean
 *   ?agent=system → 404-clean
 *   ?agent=reviewer → renders ReviewerDetail (unchanged from ADR-214)
 */

import { useEffect, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  Loader2,
  MessageCircle,
  ListChecks,
  Play,
} from 'lucide-react';
import { useNarrative } from '@/contexts/NarrativeContext';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { useAgentsAndRecurrences } from '@/hooks/useAgentsAndRecurrences';
import { getAgentSlug } from '@/lib/agent-identity';
import { AgentContentView } from '@/components/agents/AgentContentView';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import { PageHeader } from '@/components/shell/PageHeader';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';


export default function AgentsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { loadScopedHistory, sendMessage } = useNarrative();
  const { setBreadcrumb, clearBreadcrumb } = useBreadcrumb();
  const { agents, tasks, loading } = useAgentsAndRecurrences();

  const agentFromUrl = searchParams.get('agent');

  // Detail mode is URL-driven (ADR-167). ADR-272: no redirect for legacy
  // ?agent=system / ?agent=yarnnn / ?agent=thinking-partner — those URLs
  // 404-clean (no silent forwarding to a dissolved surface).
  const selectedAgent = useMemo(() => {
    if (!agentFromUrl) return null;
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

  // Breadcrumb
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

  // Roster (no agent selected): Reviewer + Domain Agents only post-ADR-272.
  const reviewer = agents.find(a => a.agent_class === 'reviewer');
  const domainAgents = agents.filter(a => a.agent_class !== 'reviewer');

  return (
    <>
    <ThreePanelLayout
      conversation={{
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
        <div className="flex-1 overflow-auto p-6 max-w-3xl space-y-6">
          {reviewer && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-3">Systemic</p>
              <button
                onClick={() => router.push('/agents?agent=reviewer')}
                className="w-full text-left rounded-lg border border-border/60 bg-card px-4 py-3 hover:bg-muted/30 transition-colors"
              >
                <p className="text-sm font-medium">Reviewer</p>
                <p className="text-xs text-muted-foreground mt-0.5">Your judgment seat — independent verdicts on proposed actions.</p>
              </button>
            </div>
          )}
          {domainAgents.length > 0 && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-3">Your agents</p>
              <div className="grid grid-cols-2 gap-3">
                {domainAgents.map(a => (
                  <button
                    key={a.id}
                    onClick={() => router.push(`/agents?agent=${encodeURIComponent(getAgentSlug(a))}`)}
                    className="text-left rounded-lg border border-border/60 bg-card px-4 py-3 hover:bg-muted/30 transition-colors"
                  >
                    <p className="text-sm font-medium">{a.title}</p>
                    {a.description && (
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{a.description}</p>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
          {domainAgents.length === 0 && (
            <p className="text-xs text-muted-foreground/60">
              No agents authored yet. Ask in chat to set up recurring work — that&apos;s where agent identity comes from.
            </p>
          )}
        </div>
      )}
    </ThreePanelLayout>

    </>
  );
}
