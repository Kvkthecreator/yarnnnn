'use client';

/**
 * useSurfacePreferences — ADR-297 D5 + D6 + D13 + D14.
 *
 * React hook over the localStorage-backed surface preferences. Tracks
 * current Supabase user id and exposes:
 *   - kept         — Dock-permanence surfaces (D14 — was `pinned`)
 *   - open         — currently-open surface slugs (D13)
 *   - foregrounded — the open slug currently visible in main (D13)
 *   + mutators (keep, release, reorder, openSurface, closeSurface,
 *     foregroundSurface, isKept, isOpen)
 *
 * D14 (2026-05-21) renamed the pin concept to keep. The Dock's
 * contents are the UNION of kept ∪ open. See ADR-297 §D14.
 *
 * D13 (2026-05-21) replaced `lastActive` + `recordVisit` with the
 * open-surfaces registry + foregroundSurface mutator.
 */

import { useCallback, useEffect, useState } from 'react';
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
  /** Dock-permanence surfaces (D14 — was `pinned`). The macOS
   *  "Keep in Dock" semantic — operator-declared "this stays in the
   *  Dock regardless of whether it's currently open." */
  kept: string[];
  /** Currently-open surfaces (D13). The macOS "currently running"
   *  semantic — a surface has a live mount in the React tree. */
  open: string[];
  /** The slug currently visible in main. Exactly one open surface is
   *  foregrounded at any time; the others are hidden via `display:
   *  none` but preserve their state. null = desktop empty state. */
  foregrounded: string | null;
  /** Add a surface to the Dock-permanence list (macOS "Keep in Dock"). */
  keep: (slug: string) => void;
  /** Remove a surface from the Dock-permanence list. Does NOT close
   *  the surface — if it's currently open, it remains open and visible
   *  in the Dock (under the Open-but-not-Kept rules); when closed it
   *  disappears from the Dock. */
  release: (slug: string) => void;
  /** Reorder the kept-surfaces list. */
  reorder: (slugs: string[]) => void;
  /** Open a surface (add to open registry if not present). Does NOT
   *  foreground it — caller decides whether to also call
   *  foregroundSurface. Most call sites want foregroundSurface
   *  (which combines open + foreground in one action). */
  openSurface: (slug: string) => void;
  /** Close a surface (remove from open registry). If the closed
   *  surface was foregrounded, foreground falls through to the
   *  next-most-recent open surface; if no surfaces remain open,
   *  foreground becomes null (desktop empty state). */
  closeSurface: (slug: string) => void;
  /** Bring an open surface to the foreground. If the slug is not yet
   *  in the open registry, it is added (open + foreground in one
   *  action — the common case for Dock clicks + launcher selections). */
  foregroundSurface: (slug: string) => void;
  isKept: (slug: string) => boolean;
  isOpen: (slug: string) => boolean;
}

export function useSurfacePreferences(): SurfacePreferences {
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
      // openSurface returns the resulting list with the slug present.
      // This combines open + foreground in a single action — the
      // common case for every Dock click / launcher selection /
      // setSurface dispatch on a kernel surface.
      const nextOpen = openSurfaceWrite(userId, slug);
      setOpen(nextOpen);
      setForegroundedWrite(userId, slug);
      setForegrounded(slug);
    },
    [userId]
  );

  const isKept = useCallback((slug: string) => kept.includes(slug), [kept]);
  const isOpen = useCallback((slug: string) => open.includes(slug), [open]);

  return {
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
  };
}
