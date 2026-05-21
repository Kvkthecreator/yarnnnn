'use client';

/**
 * DockSurface — ADR-297 D11 chrome surface (region: bottom-floating).
 *
 * Zero-prop wrapper over the existing Dock component. The compositor
 * mounts this surface into the bottom-floating region; the wrapper
 * sources its data (composition + pinned slugs) from the same hooks
 * AuthenticatedLayout previously read.
 *
 * Body unchanged from pre-D11 Dock — only the invocation site moves
 * from inline JSX in AuthenticatedLayout to compositor-driven mount.
 */

import { useComposition } from '@/lib/compositor/useComposition';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { Dock } from '../Dock';

export function DockSurface() {
  const { data: composition } = useComposition();
  const { pinned } = useSurfacePreferences();

  return <Dock surfaces={composition.surfaces || []} pinned={pinned} />;
}
