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
import { useParams, useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useAgentsAndRecurrences } from '@/hooks/useAgentsAndRecurrences';
import { getAgentSlug } from '@/lib/agent-identity';

export default function AgentIdRedirectPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { agents, loading } = useAgentsAndRecurrences({ pollInterval: 0, refreshOnFocus: false });

  useEffect(() => {
    if (loading) return;

    const agent = agents.find((item) => item.id === params.id || getAgentSlug(item) === params.id);
    if (agent) {
      router.replace(`/agents?agent=${encodeURIComponent(getAgentSlug(agent))}`);
      return;
    }

    router.replace('/agents');
  }, [agents, loading, params.id, router]);

  return (
    <div className="h-full flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
