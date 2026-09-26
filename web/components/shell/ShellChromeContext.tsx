'use client';

/**
 * ShellChromeContext — ADR-297 D11 + D14.1.
 *
 * Lightweight provider for chrome-surface shared state. Chrome
 * surfaces registered in ChromeRegistry consume this context instead
 * of receiving props from AuthenticatedLayout, so the compositor can
 * mount them without wiring N props through M JSX slots.
 *
 * This context carries the launcher + the layout mode. Chat is a windowed
 * surface, not chrome, so no chat state lives here (ADR-632 · ADR-670 D8).
 *
 * ADR-358 (2026-06-23): layout mode — the shell's spatial paradigm is an
 * operator preference, not a fixed architectural fact. `layoutMode` carries
 * the choice between CANVAS (one full-bleed surface at a time, window
 * chrome suppressed) and DESKTOP (the ADR-297 D15 free-floating window
 * manager). It persists to localStorage, defaults CANVAS, and is restored
 * post-mount (SSR renders the default → no hydration mismatch). Readers:
 * SurfaceViewport (single-vs-multi window), Desktop (wallpaper vs fill),
 * TopBar, and the UserMenu control that sets it.
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
import { createClient } from '@/lib/supabase/client';

// ADR-358 — the shell's spatial paradigm. CANVAS = one full-bleed surface
// at a time; DESKTOP = the free-floating window manager. Persisted, default
// CANVAS, restored post-mount (SSR renders the default → no hydration
// mismatch). Mode is desktop-only — on mobile both modes collapse to the
// same single-surface arrangement.
export type LayoutMode = 'canvas' | 'desktop';
const LAYOUT_MODE_KEY = 'yarnnn:shell:layout-mode';
const DEFAULT_LAYOUT_MODE: LayoutMode = 'canvas';

interface ShellChromeContextValue {
  userEmail: string | undefined;
  launcherOpen: boolean;
  openLauncher: () => void;
  closeLauncher: () => void;
  /** ADR-358 — the member's chosen spatial paradigm. Read by the surface
   *  viewport (single-vs-multi window) and the Desktop. Default canvas. */
  layoutMode: LayoutMode;
  setLayoutMode: (mode: LayoutMode) => void;
}

const Ctx = createContext<ShellChromeContextValue | null>(null);

interface ShellChromeProviderProps {
  userEmail: string | undefined;
  children: ReactNode;
}

export function ShellChromeProvider({ userEmail: serverEmail, children }: ShellChromeProviderProps) {
  const [launcherOpen, setLauncherOpen] = useState(false);
  // WHERE THE EMAIL COMES FROM. The web layout reads it server-side and hands
  // it in, so the avatar paints with the page. The desktop shell has no
  // request to read (ADR-661 §7n — a `cookies()` read made every authenticated
  // route un-exportable), so it arrives undefined and the avatar showed `?`.
  // Then it comes from the session the client already holds: `getSession()`
  // is local, no round-trip — the same question `AuthGate` has just asked
  // above this provider. A prop always wins; the session is only the fallback.
  const [sessionEmail, setSessionEmail] = useState<string | undefined>(undefined);
  useEffect(() => {
    if (serverEmail) return;
    const supabase = createClient();
    let active = true;
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (active) setSessionEmail(session?.user?.email ?? undefined);
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (active) setSessionEmail(session?.user?.email ?? undefined);
    });
    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, [serverEmail]);
  const userEmail = serverEmail ?? sessionEmail;
  // ADR-358 — SSR renders the DEFAULT layout mode; the post-mount effect
  // applies the persisted choice. Server can't read localStorage, so
  // starting at the default avoids a hydration mismatch.
  const [layoutMode, setLayoutModeState] = useState<LayoutMode>(DEFAULT_LAYOUT_MODE);

  // ADR-358 — restore the persisted layout mode post-mount.
  useEffect(() => {
    let storedMode: string | null = null;
    try {
      storedMode = window.localStorage.getItem(LAYOUT_MODE_KEY);
    } catch {}
    const mode: LayoutMode =
      storedMode === 'canvas' || storedMode === 'desktop'
        ? storedMode
        : DEFAULT_LAYOUT_MODE;
    if (mode !== DEFAULT_LAYOUT_MODE) setLayoutModeState(mode);
  }, []);

  // ADR-358 — persist the operator's layout-mode choice.
  const setLayoutMode = useCallback((next: LayoutMode) => {
    setLayoutModeState(next);
    try {
      window.localStorage.setItem(LAYOUT_MODE_KEY, next);
    } catch {}
  }, []);

  const openLauncher = useCallback(() => setLauncherOpen(true), []);
  const closeLauncher = useCallback(() => setLauncherOpen(false), []);

  const value = useMemo<ShellChromeContextValue>(
    () => ({
      userEmail,
      launcherOpen,
      openLauncher,
      closeLauncher,
      layoutMode,
      setLayoutMode,
    }),
    [
      userEmail,
      launcherOpen,
      openLauncher,
      closeLauncher,
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
