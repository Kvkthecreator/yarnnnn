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
};

interface UseCompositionResult {
  data: SurfacesResponse;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

export function useComposition(): UseCompositionResult {
  const [data, setData] = useState<SurfacesResponse>(EMPTY_RESPONSE);
  const [loading, setLoading] = useState<boolean>(true);
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
    load();
  }, []);

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
