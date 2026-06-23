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
 *
 * ADR-316 posture-default tune (2026-06-23): the chat rail is co-visible
 * chrome (a dockable rail, not an occluding overlay), so its natural
 * resting state on desktop is OPEN — chat present beside the surface, not
 * FAB-summoned. The open/closed choice now persists to localStorage
 * (mirroring the rail-WIDTH persistence in ChatDrawer) so the operator's
 * last posture survives reloads. Default-open on first load; the mobile
 * overlay branch (ChatDrawer) is unaffected — it reads the same flag but
 * renders as a full-screen takeover, where "default open" would occlude,
 * so the persisted default is suppressed on mobile (see initializer).
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
import { MOBILE_BREAKPOINT_PX } from '@/lib/shell/surface-preferences';

// ADR-316 posture-default tune: the rail's open/closed posture persists
// here, mirroring ChatDrawer's rail-WIDTH persistence. Default is OPEN on
// desktop (co-visible chrome), suppressed on mobile (the overlay branch
// would occlude). Unset → default-open-on-desktop is applied post-mount so
// SSR renders closed and there is no hydration mismatch.
const DRAWER_OPEN_KEY = 'yarnnn:shell:chat-drawer-open';

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
  // SSR renders closed (no stored read on the server); the post-mount
  // effect below applies the persisted choice, or the default-open-on-
  // desktop policy when unset. Keeping the SSR value `false` avoids a
  // hydration mismatch (server can't read localStorage or viewport).
  const [drawerOpen, setDrawerOpen] = useState(false);

  // ADR-316 posture default: on first client render, restore the
  // persisted open/closed posture; when unset, default OPEN on desktop
  // and CLOSED on mobile (the mobile overlay would occlude the surface).
  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = window.localStorage.getItem(DRAWER_OPEN_KEY);
    } catch {}
    const isMobile = window.innerWidth < MOBILE_BREAKPOINT_PX;
    if (stored === 'true') setDrawerOpen(true);
    else if (stored === 'false') setDrawerOpen(false);
    else setDrawerOpen(!isMobile); // unset → desktop default-open
  }, []);

  const persistDrawerOpen = useCallback((next: boolean) => {
    try {
      window.localStorage.setItem(DRAWER_OPEN_KEY, String(next));
    } catch {}
  }, []);

  // D18.1 mutex: openDrawer auto-closes launcher; openLauncher auto-
  // closes drawer. toggleDrawer (the FAB action) follows the same
  // rule when transitioning closed → open.
  const openLauncher = useCallback(() => {
    // Mutex side-effect only — DON'T persist. Closing the rail because the
    // launcher opened is transient; the operator's deliberate posture
    // (set via the FAB / rail ×) is what gets remembered.
    setDrawerOpen(false);
    setLauncherOpen(true);
  }, []);
  const closeLauncher = useCallback(() => setLauncherOpen(false), []);

  const openDrawer = useCallback(() => {
    setLauncherOpen(false);
    setDrawerOpen(true);
    persistDrawerOpen(true);
  }, [persistDrawerOpen]);
  const closeDrawer = useCallback(() => {
    setDrawerOpen(false);
    persistDrawerOpen(false);
  }, [persistDrawerOpen]);
  const toggleDrawer = useCallback(() => {
    setDrawerOpen((wasOpen) => {
      const willOpen = !wasOpen;
      if (willOpen) setLauncherOpen(false);
      persistDrawerOpen(willOpen);
      return willOpen;
    });
  }, [persistDrawerOpen]);

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
