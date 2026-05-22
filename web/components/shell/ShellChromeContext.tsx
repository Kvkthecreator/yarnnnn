'use client';

/**
 * ShellChromeContext — ADR-297 D11 + D14.1 + D16 + D18.1.
 *
 * Lightweight provider for chrome-surface shared state. Chrome
 * surfaces registered in ChromeRegistry consume this context instead
 * of receiving props from AuthenticatedLayout, so the compositor can
 * mount them without wiring N props through M JSX slots.
 *
 * D16 (2026-05-22): chat-composer → chat-drawer. ShellChromeContext
 * gains `drawerOpen` (mirroring `launcherOpen`) for the FAB → drawer
 * open/close cycle.
 *
 * D18.1 (2026-05-22 follow-up): mutex between drawer + launcher.
 * Only one overlay is open at a time. openDrawer auto-closes the
 * launcher; openLauncher auto-closes the drawer. toggleDrawer also
 * dismisses the launcher when opening. Operator-observed (KVK 2026-05-22):
 * the prior 'both can be open; launcher z-stacks above drawer'
 * behavior was confusing — closing launcher revealed drawer behind it
 * unexpectedly. Mutex is simpler mental model.
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
   *  this; the drawer body renders conditionally on it.
   *  D18.1: opening either drawer or launcher auto-closes the other
   *  (mutex). Only one shell overlay open at a time. */
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

  // D18.1 mutex: openDrawer auto-closes launcher; openLauncher auto-
  // closes drawer. toggleDrawer (the FAB action) follows the same
  // rule when transitioning closed → open.
  const openLauncher = useCallback(() => {
    setDrawerOpen(false);
    setLauncherOpen(true);
  }, []);
  const closeLauncher = useCallback(() => setLauncherOpen(false), []);

  const openDrawer = useCallback(() => {
    setLauncherOpen(false);
    setDrawerOpen(true);
  }, []);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);
  const toggleDrawer = useCallback(() => {
    setDrawerOpen((wasOpen) => {
      const willOpen = !wasOpen;
      if (willOpen) setLauncherOpen(false);
      return willOpen;
    });
  }, []);

  const value = useMemo<ShellChromeContextValue>(
    () => ({
      userEmail,
      launcherOpen,
      openLauncher,
      closeLauncher,
      drawerOpen,
      openDrawer,
      closeDrawer,
      toggleDrawer,
    }),
    [
      userEmail,
      launcherOpen,
      openLauncher,
      closeLauncher,
      drawerOpen,
      openDrawer,
      closeDrawer,
      toggleDrawer,
    ]
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
