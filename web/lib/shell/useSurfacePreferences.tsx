'use client';

/**
 * Surface preferences — ADR-297 D5 + D6 + D13 + D14 + D14.1.
 *
 * Context-backed source of truth for operator surface preferences:
 *   - kept         — Dock-permanence surfaces (D14)
 *   - open         — currently-open surface slugs (D13)
 *   - foregrounded — the open slug currently visible in main (D13)
 *
 * D14.1 (2026-05-22) moved the implementation from a per-call useState
 * to a single Provider-backed Context. Pre-D14.1 each consumer of
 * useSurfacePreferences held its own copy of (kept, open, foregrounded)
 * in local useState — so when TopBarSurface and SurfaceViewport both
 * mounted, they had independent registries, and a write through one
 * (e.g. AuthenticatedLayout's pathname watcher calling
 * foregroundSurface) didn't propagate to the others. The Dock failed to
 * show open-but-not-kept surfaces because TopBarSurface's `open` slice
 * was always its own stale [].
 *
 * D14.1 fixes that by making one Provider near the top of the tree
 * (AuthenticatedLayout) hold the canonical state; every useSurfacePreferences
 * call reads from + writes through the same context value.
 *
 * D14 reframed pin → keep. D13 introduced multi-mount lifecycle. See
 * ADR-297 §D13, §D14, §D14.1.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { createClient } from '@/lib/supabase/client';
import {
  DEFAULT_FOREGROUNDED_SURFACE,
  DEFAULT_KEPT_SURFACES,
  DEFAULT_OPEN_SURFACES,
  closeSurface as closeSurfaceWrite,
  getForegroundedSurface,
  getKeptSurfaces,
  getOpenSurfaces,
  keepSurface as keepSurfaceWrite,
  openSurface as openSurfaceWrite,
  releaseSurface as releaseSurfaceWrite,
  setForegroundedSurface as setForegroundedWrite,
  setKeptSurfaces as setKeptWrite,
} from './surface-preferences';

export interface SurfacePreferences {
  userId: string | null;
  /** Dock-permanence surfaces (D14). The macOS "Keep in Dock" semantic. */
  kept: string[];
  /** Currently-open surfaces (D13). */
  open: string[];
  /** The slug currently visible in main; null = desktop empty state. */
  foregrounded: string | null;
  keep: (slug: string) => void;
  release: (slug: string) => void;
  reorder: (slugs: string[]) => void;
  openSurface: (slug: string) => void;
  closeSurface: (slug: string) => void;
  foregroundSurface: (slug: string) => void;
  isKept: (slug: string) => boolean;
  isOpen: (slug: string) => boolean;
}

const Ctx = createContext<SurfacePreferences | null>(null);

export function SurfacePreferencesProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState<string | null>(null);
  const [kept, setKept] = useState<string[]>(DEFAULT_KEPT_SURFACES);
  const [open, setOpen] = useState<string[]>(DEFAULT_OPEN_SURFACES);
  const [foregrounded, setForegrounded] = useState<string | null>(
    DEFAULT_FOREGROUNDED_SURFACE
  );

  useEffect(() => {
    let mounted = true;
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      if (!mounted) return;
      const uid = data.user?.id ?? null;
      setUserId(uid);
      if (uid) {
        setKept(getKeptSurfaces(uid));
        setOpen(getOpenSurfaces(uid));
        setForegrounded(getForegroundedSurface(uid));
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  const keep = useCallback(
    (slug: string) => {
      if (!userId) return;
      const next = keepSurfaceWrite(userId, slug);
      setKept(next);
    },
    [userId]
  );

  const release = useCallback(
    (slug: string) => {
      if (!userId) return;
      const next = releaseSurfaceWrite(userId, slug);
      setKept(next);
    },
    [userId]
  );

  const reorder = useCallback(
    (slugs: string[]) => {
      if (!userId) return;
      setKeptWrite(userId, slugs);
      setKept(slugs);
    },
    [userId]
  );

  const doOpenSurface = useCallback(
    (slug: string) => {
      if (!userId) return;
      const next = openSurfaceWrite(userId, slug);
      setOpen(next);
    },
    [userId]
  );

  const doCloseSurface = useCallback(
    (slug: string) => {
      if (!userId) return;
      const next = closeSurfaceWrite(userId, slug);
      setOpen(next);
      // If we just closed the foregrounded surface, foreground falls
      // through to the tail of the remaining list (most-recently-
      // opened), or null if nothing left.
      setForegrounded((current) => {
        if (current !== slug) return current;
        const fallback = next.length > 0 ? next[next.length - 1] : null;
        setForegroundedWrite(userId, fallback);
        return fallback;
      });
    },
    [userId]
  );

  const foregroundSurface = useCallback(
    (slug: string) => {
      if (!userId) return;
      const nextOpen = openSurfaceWrite(userId, slug);
      setOpen(nextOpen);
      setForegroundedWrite(userId, slug);
      setForegrounded(slug);
    },
    [userId]
  );

  const isKept = useCallback((slug: string) => kept.includes(slug), [kept]);
  const isOpen = useCallback((slug: string) => open.includes(slug), [open]);

  const value = useMemo<SurfacePreferences>(
    () => ({
      userId,
      kept,
      open,
      foregrounded,
      keep,
      release,
      reorder,
      openSurface: doOpenSurface,
      closeSurface: doCloseSurface,
      foregroundSurface,
      isKept,
      isOpen,
    }),
    [
      userId,
      kept,
      open,
      foregrounded,
      keep,
      release,
      reorder,
      doOpenSurface,
      doCloseSurface,
      foregroundSurface,
      isKept,
      isOpen,
    ]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSurfacePreferences(): SurfacePreferences {
  const ctx = useContext(Ctx);
  if (!ctx) {
    throw new Error(
      'useSurfacePreferences must be used inside <SurfacePreferencesProvider> ' +
        '(AuthenticatedLayout mounts the provider per ADR-297 D14.1)'
    );
  }
  return ctx;
}
