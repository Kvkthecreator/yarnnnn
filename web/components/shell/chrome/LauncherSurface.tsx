'use client';

/**
 * LauncherSurface — ADR-297 D11 chrome surface (region: floating-overlay,
 * visibility: summon) + D14 (kept/released vocabulary).
 *
 * Zero-prop wrapper over the existing Launcher overlay. The compositor
 * mounts this surface into the floating-overlay region; visibility is
 * controlled by the launcherOpen flag in ShellChromeContext (toggled
 * by TopBarSurface's launcher trigger button).
 *
 * D14 rename: pin/unpin → keep/release. The Launcher's per-row toggle
 * now writes through the keep/release path from useSurfacePreferences.
 */

import { useMemo } from 'react';
import { useComposition } from '@/lib/compositor/useComposition';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { Launcher } from '../Launcher';
import { useShellChrome } from '../ShellChromeContext';

export function LauncherSurface() {
  const { data: composition } = useComposition();
  const { kept, keep, release, foregroundSurface } = useSurfacePreferences();
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
      kept={kept}
      onKeep={keep}
      onRelease={release}
      onForeground={foregroundSurface}
      bundleTitleBySlug={bundleTitleBySlug}
    />
  );
}
