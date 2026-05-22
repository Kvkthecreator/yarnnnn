'use client';

/**
 * ShellChromeContext — ADR-297 D11 + D14.1 + D16.
 *
 * Lightweight provider for chrome-surface shared state. Chrome
 * surfaces registered in ChromeRegistry consume this context instead
 * of receiving props from AuthenticatedLayout, so the compositor can
 * mount them without wiring N props through M JSX slots.
 *
 * D16 (2026-05-22): chat-composer → chat-drawer. The pre-D16
 * `composerSuppressed` + `useSuppressShellComposer()` machinery (used
 * to prevent the bottom-strip composer from doubling with per-surface
 * ConversationPanel right panels and /feed's drawer) is DELETED
 * entirely. D16 collapses all chat affordances into one universal
 * drawer; nothing to suppress. ShellChromeContext gains `drawerOpen`
 * (mirroring `launcherOpen`) for the FAB → drawer open/close cycle.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

interface ShellChromeContextValue {
  userEmail: string | undefined;
  launcherOpen: boolean;
  openLauncher: () => void;
  closeLauncher: () => void;
  /** ADR-297 D16 — universal chat drawer open/close state.
   *  Mirrors launcherOpen. The FAB inside ChatDrawerSurface toggles
   *  this; the drawer body renders conditionally on it. */
  drawerOpen: boolean;
  openDrawer: () => void;
  closeDrawer: () => void;
  toggleDrawer: () => void;
}

const Ctx = createContext<ShellChromeContextValue | null>(null);

interface ShellChromeProviderProps {
  userEmail: string | undefined;
  children: ReactNode;
}

export function ShellChromeProvider({ userEmail, children }: ShellChromeProviderProps) {
  const [launcherOpen, setLauncherOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const openDrawer = useCallback(() => setDrawerOpen(true), []);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);
  const toggleDrawer = useCallback(() => setDrawerOpen((v) => !v), []);

  const value = useMemo<ShellChromeContextValue>(
    () => ({
      userEmail,
      launcherOpen,
      openLauncher: () => setLauncherOpen(true),
      closeLauncher: () => setLauncherOpen(false),
      drawerOpen,
      openDrawer,
      closeDrawer,
      toggleDrawer,
    }),
    [userEmail, launcherOpen, drawerOpen, openDrawer, closeDrawer, toggleDrawer]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useShellChrome(): ShellChromeContextValue {
  const ctx = useContext(Ctx);
  if (!ctx) {
    throw new Error('useShellChrome must be used inside <ShellChromeProvider>');
  }
  return ctx;
}
