'use client';

/**
 * LauncherSurface — ADR-297 D11 chrome surface (region: floating-overlay,
 * visibility: summon).
 *
 * Zero-prop wrapper over the existing Launcher overlay. The compositor
 * mounts this surface into the floating-overlay region; visibility is
 * controlled by the launcherOpen flag in ShellChromeContext (toggled
 * by TopBarSurface's LauncherButton).
 *
 * Body unchanged from pre-D11 Launcher — only the invocation site
 * moves from inline JSX in AuthenticatedLayout to compositor-driven
 * mount.
 */

import { useMemo } from 'react';
import { useComposition } from '@/lib/compositor/useComposition';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { Launcher } from '../Launcher';
import { useShellChrome } from '../ShellChromeContext';

export function LauncherSurface() {
  const { data: composition } = useComposition();
  const { pinned, pin, unpin } = useSurfacePreferences();
  const { launcherOpen, closeLauncher } = useShellChrome();

  // Build bundle title map from active_bundles for Launcher tier headers.
  const bundleTitleBySlug = useMemo<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    composition.active_bundles.forEach((b) => {
      if (b.slug && b.title) map[b.slug] = b.title;
    });
    return map;
  }, [composition.active_bundles]);

  return (
    <Launcher
      open={launcherOpen}
      onClose={closeLauncher}
      surfaces={composition.surfaces || []}
      pinned={pinned}
      onPin={pin}
      onUnpin={unpin}
      bundleTitleBySlug={bundleTitleBySlug}
    />
  );
}
