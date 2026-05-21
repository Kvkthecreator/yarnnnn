'use client';

/**
 * AtomicSurfaceMount — ADR-297 axiom (2026-05-21).
 *
 * Per-route deep-link adapter. Each Next.js route under `(authenticated)/`
 * for an atomic surface (cadence, mandate, delegation, etc.) renders
 * this mount component with its declared slug. The mount:
 *
 *   1. On first render, dispatches SET_SURFACE to put DeskState into
 *      the atomic shape for this slug (carrying any URL query params
 *      as the surface's params bag for deep-link state).
 *   2. Renders SurfaceViewport, which reads DeskState and mounts the
 *      registry-resolved component.
 *
 * The Next.js routes thus serve as **bookmark-safe entry vectors** to
 * the single-page shell; they don't render different content. The
 * actual surface render lives in SurfaceViewport via SurfaceRegistry.
 *
 * When operator demand surfaces for multi-surface coexistence (split-
 * mode, peek, pinned content per ADR-297 D10), the viewport can render
 * N surfaces — at that point each Next.js route still functions as a
 * deep-link receiver but the shell may also render other panels
 * alongside.
 */

import { useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { useDesk } from '@/contexts/DeskContext';
import type { KernelSurfaceSlug } from '@/types/desk';
import { SurfaceViewport } from './SurfaceViewport';

interface AtomicSurfaceMountProps {
  slug: KernelSurfaceSlug;
  /**
   * URL query param keys to preserve as the surface's params bag. E.g.,
   * Cadence accepts `task` and `agent`; Files accepts `path`. Other
   * params (utm_*, etc.) are ignored by the mount and dropped from
   * surface state.
   */
  paramKeys?: readonly string[];
}

export function AtomicSurfaceMount({ slug, paramKeys = [] }: AtomicSurfaceMountProps) {
  const { setSurface } = useDesk();
  const searchParams = useSearchParams();

  useEffect(() => {
    const params: Record<string, string> = {};
    paramKeys.forEach((k) => {
      const v = searchParams.get(k);
      if (v) params[k] = v;
    });
    setSurface({
      type: 'atomic',
      slug,
      params: Object.keys(params).length > 0 ? params : undefined,
    });
  }, [slug, searchParams, setSurface, paramKeys]);

  return <SurfaceViewport />;
}
