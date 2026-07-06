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
 * shows the roster (user-authored Domain Agents; persona agents when
 * ADR-382 builds). Detail mode (`?agent={slug}`) shows AgentContentView
 * for the selected agent. `?agent=X` is window-internal deep-link state —
 * Figma-shaped, like `?node-id=X` — not a separate page navigation.
 *
 * ADR-412 D5 (2026-07-06): the Freddie card LEFT the roster — the Agents
 * surface is Altitude 3 only; the system agent's panes re-homed to
 * Workspace Settings (System Agent group). The roster keeps the governor
 * FRAME (ADR-381 D5: agents are created and governed by Freddie) as a
 * line, not a seat. Stale ?agent=freddie deep-links fall through to list
 * mode (the roster filters the freddie class out).
 */

import { useMemo } from 'react';
import { Loader2 } from 'lucide-react';
import { useAgentsAndRecurrences } from '@/hooks/useAgentsAndRecurrences';
import { getAgentSlug, agentDisplayName } from '@/lib/agent-identity';
import { AgentContentView } from '@/components/agents/AgentContentView';
import { useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { useWindowCrumb } from '@/contexts/BreadcrumbContext';

export default function AgentsPage() {
  // ADR-297 D19.6 + ADR-358 D6: agent=X is this window's OWN deep-link
  // state — read/written under the `agents.` namespace, no pathname flip.
  const p = useSurfaceParam('agents');
  const { agents, tasks, loading } = useAgentsAndRecurrences();

  const agentFromUrl = p.get('agent');
  // ADR-412 D5 — the roster is Altitude 3 only: the freddie class is
  // filtered out here, so a stale ?agent=freddie deep-link (or the old
  // ADR-387 agents.pane= form) gracefully falls through to list mode. The
  // governance panes are pane_of: workspace-settings again.
  const roster = useMemo(
    () => agents.filter(a => a.agent_class !== 'freddie'),
    [agents],
  );

  // Detail mode is URL-driven. Intra-surface state — D19.4: ?agent=X is
  // window-internal deep-link, not cross-surface navigation.
  const selectedAgent = useMemo(() => {
    if (!agentFromUrl) return null;
    return roster.find(a => a.id === agentFromUrl || getAgentSlug(a) === agentFromUrl) ?? null;
  }, [agentFromUrl, roster]);

  const agentTasks = selectedAgent
    ? tasks.filter(t => t.agent_slugs?.includes(getAgentSlug(selectedAgent)))
    : [];

  // Per-window locator (2026-06-25). Detail mode reports "Agents › {name}"
  // in the WindowFrame title bar with a back-to-roster crumb; list mode
  // registers [] so the flat "Agents" title stands. The back crumb clears
  // the window's own `?agents.agent=` param (no pathname flip).
  useWindowCrumb(
    'agents',
    selectedAgent
      ? [
          {
            label: agentDisplayName(selectedAgent.title ?? undefined, getAgentSlug(selectedAgent)),
            kind: 'agent',
            onClick: () => p.set({ agent: null }),
          },
        ]
      : []
  );

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

  // List mode — the Altitude-3 roster. D19.4 + D19.6: clicking a card
  // updates intra-surface URL state (?agent=X) via setSurfaceParams — no
  // pathname flip, no cross-window opening; same surface, different
  // deep-link. ADR-412 D5: no Freddie card — the governor frame below is a
  // line, not a seat (ADR-381 D5 legibility; manager in the letterhead).
  const domainAgents = roster;

  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-3xl space-y-6">
        <p className="text-xs text-muted-foreground/70">
          Agents are created and governed by Freddie, the system agent —
          its dials live in Workspace Settings → System Agent.
        </p>
        {domainAgents.length > 0 && (
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-3">Your agents</p>
            <div className="grid grid-cols-2 gap-3">
              {domainAgents.map(a => (
                <button
                  key={a.id}
                  onClick={() => p.set({ agent: getAgentSlug(a) })}
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
