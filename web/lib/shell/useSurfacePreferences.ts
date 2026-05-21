'use client';

/**
 * useSurfacePreferences — ADR-297 D5 + D6.
 *
 * React hook over the localStorage-backed surface preferences. Tracks
 * current Supabase user id and exposes pinned + last-active state +
 * mutators.
 */

import { useCallback, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import {
  DEFAULT_LAST_ACTIVE,
  DEFAULT_PINNED_SURFACES,
  getLastActiveSurface,
  getPinnedSurfaces,
  pinSurface as pinSurfaceWrite,
  setLastActiveSurface as setLastActiveWrite,
  setPinnedSurfaces as setPinnedWrite,
  unpinSurface as unpinSurfaceWrite,
} from './surface-preferences';

export interface SurfacePreferences {
  userId: string | null;
  pinned: string[];
  lastActive: string;
  pin: (slug: string) => void;
  unpin: (slug: string) => void;
  reorder: (slugs: string[]) => void;
  recordVisit: (slug: string) => void;
  isPinned: (slug: string) => boolean;
}

export function useSurfacePreferences(): SurfacePreferences {
  const [userId, setUserId] = useState<string | null>(null);
  const [pinned, setPinned] = useState<string[]>(DEFAULT_PINNED_SURFACES);
  const [lastActive, setLastActive] = useState<string>(DEFAULT_LAST_ACTIVE);

  useEffect(() => {
    let mounted = true;
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      if (!mounted) return;
      const uid = data.user?.id ?? null;
      setUserId(uid);
      if (uid) {
        setPinned(getPinnedSurfaces(uid));
        setLastActive(getLastActiveSurface(uid));
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

  const recordVisit = useCallback(
    (slug: string) => {
      if (!userId) return;
      setLastActiveWrite(userId, slug);
      setLastActive(slug);
    },
    [userId]
  );

  const isPinned = useCallback((slug: string) => pinned.includes(slug), [pinned]);

  return { userId, pinned, lastActive, pin, unpin, reorder, recordVisit, isPinned };
}
