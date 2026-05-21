'use client';

/**
 * useSurfacePreferences — ADR-297 D5 + D6 + D13.
 *
 * React hook over the localStorage-backed surface preferences. Tracks
 * current Supabase user id and exposes:
 *   - pinned     — dock-pinned surface slugs (D5)
 *   - open       — currently-open surface slugs (D13)
 *   - foregrounded — the open slug currently visible in main (D13)
 *   + mutators (pin, unpin, reorder, openSurface, closeSurface,
 *     foregroundSurface, isPinned, isOpen)
 *
 * D13 (2026-05-21) replaced `lastActive` + `recordVisit` with the
 * open-surfaces registry + foregroundSurface mutator. The
 * foregroundedSurface IS the last-active concept — when the operator
 * returns, the foregroundedSurface determines what mounts; when no
 * surface is foregrounded (cold start for first-time operators), the
 * compositor renders the desktop empty state.
 */

import { useCallback, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import {
  DEFAULT_FOREGROUNDED_SURFACE,
  DEFAULT_OPEN_SURFACES,
  DEFAULT_PINNED_SURFACES,
  closeSurface as closeSurfaceWrite,
  getForegroundedSurface,
  getOpenSurfaces,
  getPinnedSurfaces,
  openSurface as openSurfaceWrite,
  pinSurface as pinSurfaceWrite,
  setForegroundedSurface as setForegroundedWrite,
  setPinnedSurfaces as setPinnedWrite,
  unpinSurface as unpinSurfaceWrite,
} from './surface-preferences';

export interface SurfacePreferences {
  userId: string | null;
  pinned: string[];
  open: string[];
  foregrounded: string | null;
  pin: (slug: string) => void;
  unpin: (slug: string) => void;
  reorder: (slugs: string[]) => void;
  /** Open a surface (add to registry if not present). Does NOT
   *  foreground it — caller decides whether to also call
   *  foregroundSurface. Most call sites want openAndForeground;
   *  this primitive is exposed for cases that want them separately. */
  openSurface: (slug: string) => void;
  /** Close a surface (remove from registry). If the closed surface was
   *  foregrounded, foreground falls through to the next-most-recent
   *  open surface; if no surfaces remain open, foreground becomes null
   *  (desktop empty state). */
  closeSurface: (slug: string) => void;
  /** Bring an open surface to the foreground. If the slug is not yet
   *  in the open registry, it is added (open + foreground in one
   *  action — the common case for dock clicks + launcher selections). */
  foregroundSurface: (slug: string) => void;
  isPinned: (slug: string) => boolean;
  isOpen: (slug: string) => boolean;
}

export function useSurfacePreferences(): SurfacePreferences {
  const [userId, setUserId] = useState<string | null>(null);
  const [pinned, setPinned] = useState<string[]>(DEFAULT_PINNED_SURFACES);
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
        setPinned(getPinnedSurfaces(uid));
        setOpen(getOpenSurfaces(uid));
        setForegrounded(getForegroundedSurface(uid));
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  const pin = useCallback(
    (slug: string) => {
      if (!userId) return;
      const next = pinSurfaceWrite(userId, slug);
      setPinned(next);
    },
    [userId]
  );

  const unpin = useCallback(
    (slug: string) => {
      if (!userId) return;
      const next = unpinSurfaceWrite(userId, slug);
      setPinned(next);
    },
    [userId]
  );

  const reorder = useCallback(
    (slugs: string[]) => {
      if (!userId) return;
      setPinnedWrite(userId, slugs);
      setPinned(slugs);
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
      // openSurface returns the resulting list with the slug present.
      // This combines open + foreground in a single action — the
      // common case for every dock click / launcher selection /
      // setSurface dispatch on a kernel surface.
      const nextOpen = openSurfaceWrite(userId, slug);
      setOpen(nextOpen);
      setForegroundedWrite(userId, slug);
      setForegrounded(slug);
    },
    [userId]
  );

  const isPinned = useCallback((slug: string) => pinned.includes(slug), [pinned]);
  const isOpen = useCallback((slug: string) => open.includes(slug), [open]);

  return {
    userId,
    pinned,
    open,
    foregrounded,
    pin,
    unpin,
    reorder,
    openSurface: doOpenSurface,
    closeSurface: doCloseSurface,
    foregroundSurface,
    isPinned,
    isOpen,
  };
}
