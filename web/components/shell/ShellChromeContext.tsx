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

import { createContext, useContext, useState, useMemo, type ReactNode } from 'react';

interface ShellChromeContextValue {
  userEmail: string | undefined;
  launcherOpen: boolean;
  openLauncher: () => void;
  closeLauncher: () => void;
}

const Ctx = createContext<ShellChromeContextValue | null>(null);

interface ShellChromeProviderProps {
  userEmail: string | undefined;
  children: ReactNode;
}

export function ShellChromeProvider({ userEmail, children }: ShellChromeProviderProps) {
  const [launcherOpen, setLauncherOpen] = useState(false);

  const value = useMemo<ShellChromeContextValue>(
    () => ({
      userEmail,
      launcherOpen,
      openLauncher: () => setLauncherOpen(true),
      closeLauncher: () => setLauncherOpen(false),
    }),
    [userEmail, launcherOpen]
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
