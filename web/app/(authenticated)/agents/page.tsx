'use client';

/**
 * Agents Page — atomic Agents surface (ADR-297 D1 + D19).
 *
 * D19 (2026-05-22) refactor: window-shaped per the OS metaphor. The
 * page DELETES its prior outer chrome (ThreePanelLayout + PageHeader +
 * setBreadcrumb) — those were workspace-wide concerns from the
 * pre-ADR-297 page paradigm. The WindowFrame is now the chrome.
 *
 * What this surface renders: content-only. List mode (no `?agent=`)
 * shows the roster (Reviewer + Domain Agents). Detail mode
 * (`?agent={slug}`) shows AgentContentView for the selected agent.
 * `?agent=X` is window-internal deep-link state — Figma-shaped, like
 * `?node-id=X` — not a separate page navigation.
 *
 * Post-ADR-272: System Agent dissolved as a cockpit entity. Roster
 * shows Reviewer (systemic) + user-authored Domain Agents only.
 *
 * Legacy URL handling:
 *   ?agent=yarnnn / ?agent=thinking-partner / ?agent=system → 404-clean
 *   ?agent=reviewer → renders ReviewerDetail (unchanged from ADR-214)
 */

import { useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useAgentsAndRecurrences } from '@/hooks/useAgentsAndRecurrences';
import { getAgentSlug } from '@/lib/agent-identity';
import { AgentContentView } from '@/components/agents/AgentContentView';

export default function AgentsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { agents, tasks, loading } = useAgentsAndRecurrences();

  const agentFromUrl = searchParams.get('agent');

  // Detail mode is URL-driven. Intra-surface state — D19.4: ?agent=X is
  // window-internal deep-link, not cross-surface navigation.
  const selectedAgent = useMemo(() => {
    if (!agentFromUrl) return null;
    if (agentFromUrl === 'reviewer') {
      return agents.find(a => a.agent_class === 'reviewer') ?? null;
    }
    return agents.find(a => a.id === agentFromUrl || getAgentSlug(a) === agentFromUrl) ?? null;
  }, [agentFromUrl, agents]);

  const agentTasks = selectedAgent
    ? tasks.filter(t => t.agent_slugs?.includes(getAgentSlug(selectedAgent)))
    : [];

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Detail mode — render the selected agent in the window body.
  if (selectedAgent) {
    return (
      <div className="h-full overflow-y-auto">
        <AgentContentView agent={selectedAgent} tasks={agentTasks} />
      </div>
    );
  }

  // List mode — roster (Reviewer + Domain Agents). D19.4: clicking a
  // card updates intra-surface URL state (?agent=X); no router.push
  // to another surface; no cross-window opening — same surface,
  // different deep-link.
  const reviewer = agents.find(a => a.agent_class === 'reviewer');
  const domainAgents = agents.filter(a => a.agent_class !== 'reviewer');

  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-3xl space-y-6">
        {reviewer && (
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-3">Systemic</p>
            <button
              onClick={() => router.push('/agents?agent=reviewer', { scroll: false })}
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
                  onClick={() => router.push(`/agents?agent=${encodeURIComponent(getAgentSlug(a))}`, { scroll: false })}
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
    </div>
  );
}
