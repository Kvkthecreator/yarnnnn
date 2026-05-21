'use client';

/**
 * ShellChromeContext — ADR-297 D11.
 *
 * Lightweight provider for chrome-surface shared state (launcher open/
 * close, current operator email for the top bar). Chrome surfaces
 * registered in ChromeRegistry consume this context instead of
 * receiving props from AuthenticatedLayout, so the compositor can
 * mount them without wiring N props through M JSX slots.
 *
 * Per ADR-297 D11: chrome is not a special case at the architecture
 * layer. Chrome surfaces participate in the same compositor as content
 * surfaces — they just declare different `default_region` /
 * `default_visibility` values. The shared state they need (auth
 * identity, summon toggle) is the price chrome pays for being a
 * Navigator/Chrome/Input archetype rather than a content archetype.
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

interface ShellChromeContextValue {
  userEmail: string | undefined;
  launcherOpen: boolean;
  openLauncher: () => void;
  closeLauncher: () => void;
  /**
   * ADR-297 D11 Phase C safer-shape (2026-05-21): surfaces that mount
   * their own ConversationPanel (today: /agents /context /cadence via
   * ThreePanelLayout.conversation) call useSuppressShellComposer() to
   * register themselves; ChatComposerSurface reads this count and
   * renders null when > 0. Prevents double-composer UX while Phase C.2
   * (full per-surface migration) is still ahead.
   *
   * Count-based so multiple consumers on the same page (rare) don't
   * fight; suppression lifts when all consumers unmount.
   */
  composerSuppressed: boolean;
  registerComposerSuppression: () => void;
  unregisterComposerSuppression: () => void;
}

const Ctx = createContext<ShellChromeContextValue | null>(null);

interface ShellChromeProviderProps {
  userEmail: string | undefined;
  children: ReactNode;
}

export function ShellChromeProvider({ userEmail, children }: ShellChromeProviderProps) {
  const [launcherOpen, setLauncherOpen] = useState(false);
  const [suppressorCount, setSuppressorCount] = useState(0);

  const registerComposerSuppression = useCallback(() => {
    setSuppressorCount((n) => n + 1);
  }, []);
  const unregisterComposerSuppression = useCallback(() => {
    setSuppressorCount((n) => Math.max(0, n - 1));
  }, []);

  const value = useMemo<ShellChromeContextValue>(
    () => ({
      userEmail,
      launcherOpen,
      openLauncher: () => setLauncherOpen(true),
      closeLauncher: () => setLauncherOpen(false),
      composerSuppressed: suppressorCount > 0,
      registerComposerSuppression,
      unregisterComposerSuppression,
    }),
    [
      userEmail,
      launcherOpen,
      suppressorCount,
      registerComposerSuppression,
      unregisterComposerSuppression,
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

/**
 * useSuppressShellComposer — surfaces that mount their own composer
 * (Phase C safer shape: /agents /context /cadence via
 * ThreePanelLayout.conversation) call this hook to suppress the
 * shell-bottom ChatComposerSurface for as long as the surface is
 * mounted. Suppression releases on unmount.
 *
 * Phase C.2 follow-on (when ConversationPanel migrates to subscribe
 * to the shell composer): callers of this hook can drop the
 * suppression and rely on the shell composer alone.
 */
export function useSuppressShellComposer() {
  const { registerComposerSuppression, unregisterComposerSuppression } = useShellChrome();
  useEffect(() => {
    registerComposerSuppression();
    return () => {
      unregisterComposerSuppression();
    };
  }, [registerComposerSuppression, unregisterComposerSuppression]);
}
