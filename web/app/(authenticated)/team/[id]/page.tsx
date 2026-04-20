'use client';

/**
 * Compatibility entry for legacy `/team/[id]` (and transitively `/agents/[id]`) links.
 *
 * ADR-167 made `?agent={slug}` the canonical agent detail surface.
 * ADR-201 renamed /agents → /team. This route resolves the requested agent
 * id and redirects into the canonical `/team?agent={slug}` surface so the
 * product keeps one agent-detail implementation.
 */

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useAgentsAndTasks } from '@/hooks/useAgentsAndTasks';
import { getAgentSlug } from '@/lib/agent-identity';

export default function TeamIdRedirectPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { agents, loading } = useAgentsAndTasks({ pollInterval: 0, refreshOnFocus: false });

  useEffect(() => {
    if (loading) return;

    const agent = agents.find((item) => item.id === params.id || getAgentSlug(item) === params.id);
    if (agent) {
      router.replace(`/team?agent=${encodeURIComponent(getAgentSlug(agent))}`);
      return;
    }

    router.replace('/team');
  }, [agents, loading, params.id, router]);

  return (
    <div className="h-full flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
