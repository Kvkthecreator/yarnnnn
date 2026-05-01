'use client';

/**
 * Agents Page — Detail-only surface (ADR-167 v5, ADR-214, ADR-241).
 *
 * Per ADR-241 (2026-04-30), `/agents` defaults to Thinking Partner detail.
 * With ADR-235 D2 removing custom-agent creation and Reviewer collapsing
 * into TP per ADR-241, the roster surface was always-empty ceremony —
 * `/agents` (no query param) now redirects to `?agent=thinking-partner`.
 *
 * Legacy `?agent=reviewer` deep-links continue to work — they redirect to
 * `?agent=thinking-partner&tab=principles` per ADR-241 D3 (the Reviewer's
 * principles.md substrate becomes TP's Principles tab).
 *
 * AgentRosterSurface is deleted (Singular Implementation rule). Future
 * ADRs that re-introduce user-authored Agents will reintroduce a roster
 * landing then.
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

  // ADR-241: detail-only landing. Default to thinking-partner when no
  // agent param is set. Roster mode is dead UX post-ADR-235 D2.
  useEffect(() => {
    if (!agentFromUrl) {
      router.replace('/agents?agent=thinking-partner', { scroll: false });
    }
  }, [agentFromUrl, router]);

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
        // ADR-241: roster mode deleted; this branch only shows briefly
        // during the redirect-to-thinking-partner effect.
        <div className="flex items-center justify-center h-full">
          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      )}
    </ThreePanelLayout>

    </>
  );
}
