'use client';

/**
 * SurfaceViewport — ADR-297 axiom (2026-05-21).
 *
 * The shell's single content slot. Mounts the active atomic surface
 * via SurfaceRegistry. Resolution order:
 *
 *   1. DeskState.surface.slug (canonical) — set by setSurface dispatches
 *      from the Dock/Launcher/handoff machinery. Wins when present.
 *   2. URL pathname (deep-link transport) — first segment of the path
 *      mapped through isKernelSurfaceSlug. Cold-load fallback before
 *      the URL→state hydration useEffect in DeskContext has fired.
 *
 * The pathname fallback ensures the operator sees the correct surface
 * on first paint after a cold load to /cadence (etc.) without a blank
 * frame. State catches up async via DeskContext's pathname watcher.
 *
 * Per the axiom: surface = viewport panel. The viewport is what panels
 * mount into. Multi-surface coexistence (split-mode, peek, pinned
 * content) is forward-horizon — when ADR-297 D10 advances, the
 * viewport will render N surfaces in a layout. Today it renders one.
 *
 * Idle states with no resolvable atomic slug fall through to children.
 */

import type { ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { useDesk } from '@/contexts/DeskContext';
import { isKernelSurfaceSlug } from '@/types/desk';
import type { KernelSurfaceSlug } from '@/types/desk';
import { resolveSurfaceComponent } from './SurfaceRegistry';

interface SurfaceViewportProps {
  /**
   * Fallback rendered when neither DeskState nor URL pathname resolves
   * to a kernel surface slug. Used for non-atomic routes (legacy).
   */
  children?: ReactNode;
}

export function SurfaceViewport({ children }: SurfaceViewportProps) {
  const { surface } = useDesk();
  const pathname = usePathname();

  // 1. DeskState wins when atomic
  let slug: KernelSurfaceSlug | null = null;
  if (surface.type === 'atomic') {
    slug = surface.slug;
  } else {
    // 2. Pathname fallback — first path segment as deep-link transport
    const firstSegment = pathname.split('/').filter(Boolean)[0];
    if (firstSegment && isKernelSurfaceSlug(firstSegment)) {
      slug = firstSegment;
    }
  }

  if (slug) {
    const Component = resolveSurfaceComponent(slug);
    return <Component />;
  }

  return <>{children}</>;
}
