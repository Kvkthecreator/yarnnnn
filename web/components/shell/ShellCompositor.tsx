'use client';

/**
 * ShellCompositor — ADR-297 D11.
 *
 * Reads the surface registry from useComposition(), partitions surfaces
 * by `default_region`, and mounts each region's surface(s) into the
 * matching JSX slot. Replaces the hardcoded shell JSX previously living
 * in AuthenticatedLayout.tsx.
 *
 * Layout regions (ADR-297 D11):
 *   - `top`              → top-of-viewport chrome (today: TopBar)
 *   - `main`             → primary content area (mounts SurfaceViewport;
 *                           atomic content surface dispatched by DeskContext)
 *   - `bottom-floating`  → floating affordance above main (today: Dock)
 *   - `bottom-fixed`     → fixed input region below main (today:
 *                           ChatComposerSurface placeholder; Phase C wires
 *                           the actual composer body)
 *   - `floating-overlay` → modal overlays summoned over main (today:
 *                           LauncherSurface)
 *
 * Visibility policy:
 *   - `always`           → mounted unconditionally
 *   - `summon`           → mounted unconditionally; surface controls its
 *                           own open/close via shared context (the
 *                           rendering is conditional inside the surface,
 *                           not at the compositor)
 *   - `pinned-only`      → reserved; not yet used by any chrome surface
 *
 * The compositor does NOT enforce visibility — surfaces with
 * `summon`/`pinned-only` visibility render null when inactive (see
 * Launcher.tsx for the pattern). This keeps the compositor purely
 * structural and leaves per-surface UX (animations, focus traps, etc.)
 * to the surface implementation.
 *
 * Content surfaces (archetype ∈ document/dashboard/queue/briefing/
 * stream/browser/roster, default_region absent) are NOT mounted by
 * iterating composition.surfaces — they're rendered by SurfaceViewport,
 * which resolves the active atomic surface from DeskContext +
 * pathname. The compositor mounts SurfaceViewport once in the `main`
 * region; SurfaceViewport handles the per-route surface swap.
 *
 * Why not iterate everything: today there is exactly one active content
 * surface at a time (the D10 multi-surface advance is forward horizon).
 * SurfaceViewport already owns the atomic dispatch; the compositor's
 * job is to mount chrome alongside it, not to duplicate dispatch logic.
 */

import { type ReactNode } from 'react';
import { useComposition } from '@/lib/compositor/useComposition';
import { SurfaceViewport } from './SurfaceViewport';
import {
  CHROME_SURFACE_REGISTRY,
  isChromeSurfaceSlug,
  type ChromeSurfaceSlug,
} from './ChromeRegistry';
import type { LayoutRegion, Surface } from '@/lib/compositor/types';

interface ShellCompositorProps {
  /**
   * Fallback content rendered inside the `main` region when no atomic
   * surface resolves from DeskContext / pathname. Legacy non-atomic
   * routes (settings, connectors, docs, etc.) pass their page children
   * through here.
   */
  children?: ReactNode;
}

/**
 * Group chrome surfaces from composition.surfaces[] by their declared
 * `default_region`. Only surfaces that (a) appear in CHROME_SURFACE_REGISTRY
 * and (b) declare a default_region are mounted. Anything else is ignored
 * by the compositor (content surfaces flow through SurfaceViewport;
 * unknown chrome slugs are silently skipped to tolerate drift between
 * the kernel registry and the FE registry).
 */
function partitionChromeByRegion(
  surfaces: Surface[]
): Record<LayoutRegion, ChromeSurfaceSlug[]> {
  const byRegion: Record<LayoutRegion, ChromeSurfaceSlug[]> = {
    main: [],
    top: [],
    'bottom-floating': [],
    'bottom-fixed': [],
    'floating-overlay': [],
  };

  surfaces.forEach((s) => {
    if (!s.default_region) return;
    if (!isChromeSurfaceSlug(s.slug)) return;
    byRegion[s.default_region].push(s.slug);
  });

  return byRegion;
}

export function ShellCompositor({ children }: ShellCompositorProps) {
  const { data: composition } = useComposition();
  const byRegion = partitionChromeByRegion(composition.surfaces || []);

  const mountRegion = (region: LayoutRegion) =>
    byRegion[region].map((slug) => {
      const Component = CHROME_SURFACE_REGISTRY[slug];
      return <Component key={slug} />;
    });

  return (
    <>
      <div className="flex flex-col h-screen bg-background">
        {/* Top region — TopBarSurface (D12 + D14: merged dock-bar —
            brand · launcher trigger · Dock icons (kept ∪ open) ·
            user menu). */}
        {mountRegion('top')}

        {/* Main region — atomic content surface via SurfaceViewport,
            with legacy children as fallback */}
        <main className="flex-1 min-h-0 overflow-hidden">
          <SurfaceViewport>{children}</SurfaceViewport>
        </main>

        {/* Bottom-fixed region — ChatComposerSurface (D11 Phase C). */}
        {mountRegion('bottom-fixed')}

        {/* D12 (2026-05-21): bottom-floating region intentionally NOT
            mounted. The Dock kernel surface was deleted; its Dock-
            icon responsibility absorbed into TopBarSurface's body. The
            `bottom-floating` LayoutRegion survives in the type union
            (a future chrome surface might target it) but no kernel
            surface emits there today. */}
      </div>

      {/* Floating-overlay region — LauncherSurface. Mounted outside the
          screen flow because overlays use their own portal-like fixed
          positioning + z-index stacking. */}
      {mountRegion('floating-overlay')}
    </>
  );
}
