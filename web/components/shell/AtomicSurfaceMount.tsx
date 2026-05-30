'use client';

/**
 * AtomicSurfaceMount — ADR-297 axiom (2026-05-21; simplified Phase 3
 * 2026-05-30).
 *
 * Per-route deep-link adapter. Each Next.js route under `(authenticated)/`
 * for an atomic surface (cadence, mandate, delegation, etc.) renders
 * this mount component with its declared slug. The route is a
 * **bookmark-safe entry vector** to the single-page shell — it doesn't
 * render different content.
 *
 * The actual foregrounding on cold-load is owned by the window manager:
 * `AuthenticatedLayout`'s pathname watcher reads the URL and calls
 * `foregroundSurface(slug)`. `SurfaceViewport` then renders from the
 * window manager's open-surfaces registry (`useSurfacePreferences`),
 * NOT from DeskState. The pre-Phase-3 `setSurface` dispatch here wrote
 * to a DeskState that SurfaceViewport never read — it was dead. Deleted
 * with the rest of the legacy Supervisor Desk system. This component is
 * now a thin SurfaceViewport host kept for route-file ergonomics.
 */

import type { KernelSurfaceSlug } from '@/types/desk';
import { SurfaceViewport } from './SurfaceViewport';

interface AtomicSurfaceMountProps {
  /** Declared for route-file readability; foregrounding is handled by
   *  the window manager's pathname watcher, not by this component. */
  slug?: KernelSurfaceSlug;
  /** Retained for route-file call-site compatibility; unused now that
   *  surfaces read their params from useSearchParams directly. */
  paramKeys?: readonly string[];
}

export function AtomicSurfaceMount(_props: AtomicSurfaceMountProps) {
  return <SurfaceViewport />;
}
