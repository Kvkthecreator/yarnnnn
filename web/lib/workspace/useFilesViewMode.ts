'use client';

/**
 * Files-surface view mode (ADR-388 D4) — one Finder-like preference shared
 * across the whole Files surface (was Recents-only). 'icon' = grid of tiles,
 * 'list' = details rows. Persisted per-operator in localStorage, shared by
 * every mount (Recents, folder listings, search). Default 'icon' (the
 * operator's prior Recents default).
 */

import { useCallback, useEffect, useState } from 'react';

export type FilesViewMode = 'icon' | 'list';

const VIEW_PREF_KEY = 'yarnnn:files:view-mode';
const DEFAULT_MODE: FilesViewMode = 'icon';

function readStored(): FilesViewMode {
  if (typeof window === 'undefined') return DEFAULT_MODE;
  const raw = window.localStorage.getItem(VIEW_PREF_KEY);
  return raw === 'icon' || raw === 'list' ? raw : DEFAULT_MODE;
}

// Module-level subscriber set so every mount stays in sync within a tab
// (a localStorage write in one component reflects in the others immediately,
// not just on next mount). The `storage` event covers cross-tab.
const listeners = new Set<(m: FilesViewMode) => void>();

export function useFilesViewMode(): {
  mode: FilesViewMode;
  setMode: (m: FilesViewMode) => void;
} {
  const [mode, setLocal] = useState<FilesViewMode>(DEFAULT_MODE);

  useEffect(() => {
    setLocal(readStored());
    const onChange = (m: FilesViewMode) => setLocal(m);
    listeners.add(onChange);
    const onStorage = (e: StorageEvent) => {
      if (e.key === VIEW_PREF_KEY) setLocal(readStored());
    };
    window.addEventListener('storage', onStorage);
    return () => {
      listeners.delete(onChange);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  const setMode = useCallback((m: FilesViewMode) => {
    if (typeof window !== 'undefined') window.localStorage.setItem(VIEW_PREF_KEY, m);
    listeners.forEach((fn) => fn(m));
  }, []);

  return { mode, setMode };
}
