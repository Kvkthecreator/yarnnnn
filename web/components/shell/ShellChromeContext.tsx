'use client';

/**
 * ShellChromeContext — ADR-297 D11 + D14.1 + D16 + D18.1.
 *
 * Lightweight provider for chrome-surface shared state. Chrome
 * surfaces registered in ChromeRegistry consume this context instead
 * of receiving props from AuthenticatedLayout, so the compositor can
 * mount them without wiring N props through M JSX slots.
 *
 * ADR-632: the chat drawer (D16/D18.1/ADR-316) is DELETED with the steward;
 * this context carries the launcher + the layout mode.
 *
 * ADR-358 (2026-06-23): layout mode — the shell's spatial paradigm is an
 * operator preference, not a fixed architectural fact. `layoutMode` carries
 * the choice between CANVAS (chat-left + one full-bleed surface-right,
 * side-to-side divider only — the ChatGPT/Claude convention) and DESKTOP
 * (the ADR-297 D15 free-floating window manager + ADR-316 right-docked
 * rail). It persists to localStorage, defaults
 * CANVAS, and is restored post-mount (SSR renders the default → no
 * hydration mismatch). Three consumers read it: ShellCompositor (flex
 * order), SurfaceViewport (single-vs-multi window).
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
}

const Ctx = createContext<ShellChromeContextValue | null>(null);

interface ShellChromeProviderProps {
  userEmail: string | undefined;
  children: ReactNode;
}

export function ShellChromeProvider({ userEmail, children }: ShellChromeProviderProps) {
  const [launcherOpen, setLauncherOpen] = useState(false);
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
