'use client';

/**
 * SurfaceViewport — ADR-297 axiom (2026-05-21).
 *
 * The shell's single content slot. Reads the active surface from
 * DeskContext and mounts the corresponding component via
 * SurfaceRegistry.
 *
 * Per the axiom: surface = viewport panel. The viewport is what panels
 * mount into. Multi-surface coexistence (split-mode, peek, pinned
 * content) is forward-horizon — when ADR-297 D10 advances, the
 * viewport will render N surfaces in a layout. Today it renders one.
 *
 * Idle/legacy states fall through to children (the route's standard
 * page render) — this preserves backward compatibility for any
 * surface type not yet migrated to the atomic shape.
 */

import type { ReactNode } from 'react';
import { useDesk } from '@/contexts/DeskContext';
import { resolveSurfaceComponent } from './SurfaceRegistry';

interface SurfaceViewportProps {
  /**
   * Fallback rendered when DeskState carries no atomic surface (idle or
   * a legacy non-atomic surface type). Typically the Next.js page's
   * default content for surfaces that haven't migrated to the atomic
   * registry pattern.
   */
  children?: ReactNode;
}

export function SurfaceViewport({ children }: SurfaceViewportProps) {
  const { surface } = useDesk();

  if (surface.type === 'atomic') {
    const Component = resolveSurfaceComponent(surface.slug);
    return <Component />;
  }

  return <>{children}</>;
}
