'use client';

/**
 * Compatibility entry for legacy `/agents/[id]` (and transitively `/team/[id]`) links.
 *
 * ADR-167 made `?agent={slug}` the canonical agent detail surface.
 * ADR-214 (2026-04-23) reversed ADR-201 — `/agents` is canonical again.
 * This route forwards the requested agent into `/agents?agent={slug}` so the
 * product keeps one agent-detail implementation.
 *
 * SIMPLIFIED 2026-07-16. This stub used to resolve the id → a slug against the
 * `agents` DB table (via `useAgentsAndRecurrences`). That table is EMPTY
 * (ADR-414 retired the last row), so the lookup could only ever miss — it was a
 * spinner that always fell through. The param now passes STRAIGHT THROUGH: the
 * surface matches it against the workspace's Agent folders + the kernel set and
 * falls back to list mode when it matches nothing, which is the honest
 * behaviour for a legacy id that no longer names anything.
 * (The hook itself stays — /recurrence and /notifications are live consumers.)
 *
 * Preserved: `navigateToSurface` with the `agents.`-namespaced param — it keeps
 * the OS shell on /desktop. A bare `router.replace('?agent=')` would be a
 * pathname flip + an un-namespaced param: the ADR-308 orphaned-frame
 * anti-pattern.
 */

import { useEffect } from 'react';
import { useParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

export default function AgentIdRedirectPage() {
  const params = useParams<{ id: string }>();
  const { navigateToSurface } = useSurfacePreferences();

  useEffect(() => {
    navigateToSurface('agents', params.id ? { agent: params.id } : undefined);
  }, [params.id, navigateToSurface]);

  return (
    <div className="h-full flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
    </div>
  );
}
