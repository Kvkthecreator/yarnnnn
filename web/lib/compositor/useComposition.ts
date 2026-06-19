'use client';

/**
 * useComposition — React hook that fetches /api/programs/surfaces and
 * caches the response per session.
 *
 * Per ADR-225: the composition tree changes only at deploy time (bundle
 * file changes) + when a workspace's platform_connections change
 * (capability-implicit activation per ADR-224 §3). Per-session cache is
 * appropriate; refetch on mount of the top-level cockpit shell suffices.
 *
 * Intentionally minimal: no SWR / React Query dependency. Empty-state
 * fallback when the fetch fails — the cockpit never breaks because the
 * compositor is unreachable; it simply renders kernel defaults.
 */

import { useEffect, useState } from 'react';
import { fetchWorkspaceSurfaces } from './client';
import type {
  SurfacesResponse,
  CompositionTree,
  TabBlock,
  MiddleDecl,
  BundleMetadata,
} from './types';

const EMPTY_RESPONSE: SurfacesResponse = {
  schema_version: 1,
  active_bundles: [],
  composition: { tabs: {}, chat_chips: [] },
  // ADR-297 Phase 1: surfaces[] is empty during the pre-fetch loading state.
  // The hook's real value (kernel surfaces always present) populates from the
  // API response. Consumers that need kernel surfaces during loading should
  // gate on `loading` flag.
  surfaces: [],
};

interface UseCompositionResult {
  data: SurfacesResponse;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

export function useComposition(
  opts?: { initialData?: SurfacesResponse },
): UseCompositionResult {
  // Pre-primed path (ADR-312 home-bundle): when the parent already fetched
  // surfaces (the Home reads them inside the single home-bundle call), prime
  // the hook and skip the self-fetch. Mounts without initialData self-fetch.
  const initial = opts?.initialData;
  const [data, setData] = useState<SurfacesResponse>(initial ?? EMPTY_RESPONSE);
  const [loading, setLoading] = useState<boolean>(initial === undefined);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchWorkspaceSurfaces();
      setData(response);
    } catch (err) {
      // Empty fallback — cockpit renders kernel defaults if compositor
      // endpoint fails. This is the "cockpit never breaks" invariant.
      setError(err instanceof Error ? err.message : String(err));
      setData(EMPTY_RESPONSE);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Primed: nothing to fetch; keep the response the parent supplied.
    if (initial !== undefined) {
      setData(initial);
      setLoading(false);
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initial]);

  return { data, loading, error, reload: load };
}

// ---------------------------------------------------------------------------
// Convenience selectors over the composition tree
// ---------------------------------------------------------------------------

/**
 * Get the tab block for a specific tab name. Empty object if absent.
 */
export function getTab(
  composition: CompositionTree,
  tabName: 'chat' | 'work' | 'agents' | 'context' | 'files',
): TabBlock {
  return composition.tabs[tabName] ?? {};
}

/**
 * Get the middles[] declared for a tab's detail view. Empty array if absent.
 */
export function getDetailMiddles(
  composition: CompositionTree,
  tabName: 'work' | 'agents',
): MiddleDecl[] {
  const tab = getTab(composition, tabName);
  return tab.detail?.middles ?? [];
}

/**
 * Get the active bundle metadata array (zero or more).
 */
export function getActiveBundles(data: SurfacesResponse): BundleMetadata[] {
  return data.active_bundles ?? [];
}
