'use client';

/**
 * Compatibility entry for legacy `/agents/[id]` (and transitively `/team/[id]`) links.
 *
 * ADR-167 made `?agent={slug}` the canonical agent detail surface.
 * ADR-214 (2026-04-23) reversed ADR-201 — `/agents` is canonical again.
 * This route resolves the requested agent id and redirects into
 * `/agents?agent={slug}` so the product keeps one agent-detail implementation.
 */

import { useEffect } from 'react';
import { useParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useAgentsAndRecurrences } from '@/hooks/useAgentsAndRecurrences';
import { getAgentSlug } from '@/lib/agent-identity';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

export default function AgentIdRedirectPage() {
  const params = useParams<{ id: string }>();
  // ADR-358 (2026-06-25): resolve the legacy id → slug client-side (we need
  // the agent list to map it), then foreground the Agents window with the
  // `agents.`-namespaced param via navigateToSurface — keeps the OS shell on
  // /desktop. Pre-fix this router.replace-d a BARE `?agent=` (pathname flip +
  // un-namespaced), the ADR-308 orphaned-frame anti-pattern.
  const { navigateToSurface } = useSurfacePreferences();
  const { agents, loading } = useAgentsAndRecurrences({ pollInterval: 0, refreshOnFocus: false });

  useEffect(() => {
    if (loading) return;

    const agent = agents.find((item) => item.id === params.id || getAgentSlug(item) === params.id);
    if (agent) {
      navigateToSurface('agents', { agent: getAgentSlug(agent) });
      return;
    }

    navigateToSurface('agents');
  }, [agents, loading, params.id, navigateToSurface]);

  return (
    <div className="h-full flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
