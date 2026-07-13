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
 *
 * ADR-358 (2026-06-23): layout mode — the shell's spatial paradigm is an
 * operator preference, not a fixed architectural fact. `layoutMode` carries
 * the choice between CANVAS (chat-left + one full-bleed surface-right,
 * side-to-side divider only — the ChatGPT/Claude convention) and DESKTOP
 * (the ADR-297 D15 free-floating window manager + ADR-316 right-docked
 * rail). It persists to localStorage (mirroring `drawerOpen`), defaults
 * CANVAS, and is restored post-mount (SSR renders the default → no
 * hydration mismatch). Three consumers read it: ShellCompositor (flex
 * order), ChatDrawer (dock side), SurfaceViewport (single-vs-multi window).
 * Mobile is mode-independent (one physically-possible arrangement).
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
import { STEWARD_CHROME_ENABLED } from '@/lib/steward-chrome';

// ADR-316 posture-default tune: the rail's open/closed posture persists
// here, mirroring ChatDrawer's rail-WIDTH persistence. Default is OPEN on
// desktop (co-visible chrome), suppressed on mobile (the overlay branch
// would occlude). Unset → default-open-on-desktop is applied post-mount so
// SSR renders closed and there is no hydration mismatch.
const DRAWER_OPEN_KEY = 'yarnnn:shell:chat-drawer-open';

// ADR-358 — the shell's spatial paradigm. CANVAS = chat-left + one
// full-bleed surface-right (the chat-interface convention); DESKTOP = the
// free-floating window manager + right-docked rail. Persisted, default
// CANVAS, restored post-mount (SSR renders the default → no hydration
// mismatch). Mode is desktop-only — on mobile both modes collapse to the
// same single-surface + overlay-chat arrangement.
export type LayoutMode = 'canvas' | 'desktop';
const LAYOUT_MODE_KEY = 'yarnnn:shell:layout-mode';
const DEFAULT_LAYOUT_MODE: LayoutMode = 'canvas';

interface ShellChromeContextValue {
  userEmail: string | undefined;
  launcherOpen: boolean;
  openLauncher: () => void;
  closeLauncher: () => void;
  /** ADR-358 — the operator's chosen spatial paradigm. Read by the
   *  compositor (flex order), the chat rail (dock side), and the surface
   *  viewport (single-vs-multi window). Default canvas. */
  layoutMode: LayoutMode;
  setLayoutMode: (mode: LayoutMode) => void;
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
  // ADR-358 — SSR renders the DEFAULT layout mode; the post-mount effect
  // applies the persisted choice. Server can't read localStorage, so
  // starting at the default avoids a hydration mismatch (same pattern as
  // drawerOpen above).
  const [layoutMode, setLayoutModeState] = useState<LayoutMode>(DEFAULT_LAYOUT_MODE);

  // Posture default (ADR-316 + ADR-358 revised): on first client render,
  // restore the persisted open/closed posture; when unset, the default
  // depends on whether chat is a DOCKED RAIL or a SUMMONED OVERLAY:
  //   - Canvas on desktop → chat is the docked rail of a two-panel
  //     composition → default OPEN (chat present beside the surface).
  //   - Desktop mode + mobile → chat is a fixed overlay that would cover
  //     the windows/surface → default CLOSED (FAB-summoned).
  useEffect(() => {
    // Read the layout mode first — the drawer default depends on it.
    let storedMode: string | null = null;
    try {
      storedMode = window.localStorage.getItem(LAYOUT_MODE_KEY);
    } catch {}
    const mode: LayoutMode =
      storedMode === 'canvas' || storedMode === 'desktop'
        ? storedMode
        : DEFAULT_LAYOUT_MODE;
    if (mode !== DEFAULT_LAYOUT_MODE) setLayoutModeState(mode);

    // ADR-454 D3 — the ambient steward: with the persona chrome gated off,
    // the drawer never opens (neither the persisted posture nor the
    // rail-mode default), so a returning operator with a persisted-open
    // rail doesn't resurrect it.
    if (!STEWARD_CHROME_ENABLED) return;

    let stored: string | null = null;
    try {
      stored = window.localStorage.getItem(DRAWER_OPEN_KEY);
    } catch {}
    const isMobile = window.innerWidth < MOBILE_BREAKPOINT_PX;
    // Chat is a docked rail only in Canvas on a wide viewport; that is the
    // only posture that defaults open.
    const railMode = !isMobile && mode === 'canvas';
    if (stored === 'true') setDrawerOpen(true);
    else if (stored === 'false') setDrawerOpen(false);
    else setDrawerOpen(railMode); // unset → open only when docked rail
  }, []);

  // ADR-358 — persist the operator's layout-mode choice, and RE-DERIVE the
  // chat posture: switching to Canvas opens the docked rail (chat present
  // beside the surface); switching to Desktop closes the summoned overlay
  // (it would otherwise pop open over the windows). A deliberate mode switch
  // is a fresh intent, so it overrides the persisted open/closed posture
  // (and writes the new posture through, keeping the two keys consistent).
  const setLayoutMode = useCallback((next: LayoutMode) => {
    setLayoutModeState(next);
    try {
      window.localStorage.setItem(LAYOUT_MODE_KEY, next);
    } catch {}
    // ADR-454 D3 — chrome gated: a mode switch never re-opens the rail.
    if (!STEWARD_CHROME_ENABLED) return;
    const isMobile = window.innerWidth < MOBILE_BREAKPOINT_PX;
    const railMode = !isMobile && next === 'canvas';
    setDrawerOpen(railMode);
    try {
      window.localStorage.setItem(DRAWER_OPEN_KEY, String(railMode));
    } catch {}
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
    // ADR-454 D3 — persona chrome gated off: opening is a no-op (the
    // machinery stays; nothing summons it).
    if (!STEWARD_CHROME_ENABLED) return;
    setLauncherOpen(false);
    setDrawerOpen(true);
    persistDrawerOpen(true);
  }, [persistDrawerOpen]);
  const closeDrawer = useCallback(() => {
    setDrawerOpen(false);
    persistDrawerOpen(false);
  }, [persistDrawerOpen]);
  const toggleDrawer = useCallback(() => {
    if (!STEWARD_CHROME_ENABLED) return;
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
      layoutMode,
      setLayoutMode,
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
      layoutMode,
      setLayoutMode,
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
