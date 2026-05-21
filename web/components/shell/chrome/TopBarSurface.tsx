'use client';

/**
 * TopBarSurface — ADR-297 D11 chrome surface (region: top).
 *
 * Pre-D11 this lived as inline JSX in AuthenticatedLayout.tsx. D11
 * dissolves it into a registered chrome surface that the
 * ShellCompositor mounts at the `top` region.
 *
 * Renders:
 *   - Left: brand mark (clickable → navigate to last-active home per D6)
 *   - Right: LauncherButton (opens Launcher overlay) + UserMenu
 *
 * Consumes useShellChrome for launcher open dispatch + operator email.
 * Consumes useComposition + useSurfacePreferences for last-active home
 * resolution — same logic as the pre-D11 navigateToHome callback,
 * inlined here so the surface is self-contained.
 */

import { useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useComposition } from '@/lib/compositor/useComposition';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { HOME_ROUTE } from '@/lib/routes';
import { LauncherButton } from '../LauncherButton';
import { UserMenu } from '../UserMenu';
import { useShellChrome } from '../ShellChromeContext';

export function TopBarSurface() {
  const router = useRouter();
  const pathname = usePathname();
  const { data: composition } = useComposition();
  const { lastActive } = useSurfacePreferences();
  const { userEmail, openLauncher } = useShellChrome();

  // ADR-297 D6: logo click → operator's last-active surface (macOS-
  // natural). Resolves the slug to a route via the compositor registry;
  // falls back to HOME_ROUTE if the registry isn't loaded yet or the
  // slug is unknown.
  const navigateToHome = useCallback(() => {
    const surface = composition.surfaces?.find((s) => s.slug === lastActive);
    const target = surface?.route || HOME_ROUTE;
    if (pathname !== target) router.push(target);
  }, [router, pathname, composition.surfaces, lastActive]);

  return (
    <header className="h-14 border-b border-border bg-background flex items-center justify-between px-4 shrink-0">
      {/* Left: brand mark */}
      <div className="flex items-center min-w-0">
        <button
          onClick={navigateToHome}
          className="text-xl font-brand hover:opacity-80 transition-opacity shrink-0"
        >
          yarnnn
        </button>
      </div>

      {/* Right: launcher button + user menu */}
      <div className="flex items-center gap-1">
        <LauncherButton onClick={openLauncher} />
        <UserMenu email={userEmail} />
      </div>
    </header>
  );
}
