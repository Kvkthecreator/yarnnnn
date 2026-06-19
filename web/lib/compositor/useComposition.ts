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
  Surface,
} from './types';

// Kernel-default CHROME surfaces (mirrors the chrome entries in
// api/services/kernel_surfaces.py::KERNEL_SURFACES). These are static,
// kernel-universal, and known at build time — they carry no
// workspace-dependent data, only the `default_region` the compositor needs
// to mount the OS frame. Seeding them into the pre-fetch response lets the
// shell chrome (top bar / launcher / chat rail) paint on the FIRST render,
// before /api/programs/surfaces resolves — the OS frame is the persistent
// container, not the last thing in (operator-observed KVK 2026-06-19: the
// topbar painted after the surface content because the WHOLE chrome was
// gated on the client-side composition fetch). When the fetch lands,
// `surfaces` is replaced with the full set (chrome + content + program) and
// the launcher's surface list fills in. Honors the "cockpit never breaks;
// it renders kernel defaults" invariant this hook already claims.
//
// Only chrome surfaces are seeded — content/program surfaces genuinely need
// the workspace fetch (the launcher index, program activation). The launcher
// at-rest list stays empty until the fetch lands, but the frame is there.
const KERNEL_CHROME_DEFAULTS: Surface[] = [
  {
    slug: 'top-bar',
    title: 'Top Bar',
    archetype: 'chrome',
    substrate_paths: [],
    icon_key: 'layout-top',
    default_pinned: false,
    route: '',
    summary: 'Top-center merged dock-bar — brand · launcher trigger · pinned surfaces · user menu.',
    tier: 'kernel',
    default_region: 'top',
    default_visibility: 'always',
  },
  {
    slug: 'launcher',
    title: 'Launcher',
    archetype: 'navigator',
    substrate_paths: [],
    icon_key: 'layout-grid',
    default_pinned: false,
    route: '',
    summary: 'Full surface index overlay — type-to-filter, tier grouping. Trigger lives in top-bar.',
    tier: 'kernel',
    default_region: 'floating-overlay',
    default_visibility: 'summon',
  },
  {
    slug: 'chat-drawer',
    title: 'Chat Drawer',
    archetype: 'input',
    substrate_paths: [],
    icon_key: 'message-circle',
    default_pinned: false,
    route: '',
    summary: 'Operator command rail — FAB summons a dockable right rail (desktop) / overlay (mobile).',
    tier: 'kernel',
    default_region: 'main-rail',
    default_visibility: 'summon',
  },
];

const EMPTY_RESPONSE: SurfacesResponse = {
  schema_version: 1,
  active_bundles: [],
  composition: { tabs: {}, chat_chips: [] },
  // Pre-fetch loading state. surfaces[] seeds the kernel CHROME defaults so
  // the OS frame (top bar / launcher / chat rail) paints on first render,
  // before /api/programs/surfaces resolves. Content + program surfaces
  // populate when the fetch lands. Consumers that need the FULL surface
  // index (launcher at-rest list) during loading should gate on `loading`.
  surfaces: KERNEL_CHROME_DEFAULTS,
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
