'use client';

/**
 * ShellCompositor — ADR-297 D11.
 *
 * Reads the surface registry from useComposition(), partitions surfaces
 * by `default_region`, and mounts each region's surface(s) into the
 * matching JSX slot. Replaces the hardcoded shell JSX previously living
 * in AuthenticatedLayout.tsx.
 *
 * Layout regions (ADR-297 D11 + ADR-316):
 *   - `top`              → top-of-viewport chrome (today: TopBar)
 *   - `main`             → primary content area (a flex ROW: SurfaceViewport
 *                           window area flex-1 + main-rail command rail).
 *                           ADR-358: chat docks RIGHT as a flex rail in
 *                           canvas; in desktop/mobile it is a fixed overlay
 *                           (zero flex space) so the row is just the surface.
 *   - `main-rail`        → chat (ADR-316/358, today: ChatDrawerSurface).
 *                           Canvas: a right-docked rail that reduces the
 *                           surface. Desktop/mobile: a fixed summoned
 *                           overlay. Never occludes in canvas; floats in
 *                           desktop.
 *   - `bottom-floating`  → floating affordance above main (today: Dock)
 *   - `bottom-fixed`     → fixed input region below main (today: unused)
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
import { GlobalLocatorStrip } from './GlobalLocatorStrip';
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
    'main-rail': [],
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

  // ADR-358 (revised) — chat always renders to the RIGHT of the surface
  // column. In CANVAS (wide) it is a docked flex-sibling RAIL that reduces
  // the surface area. In DESKTOP/mobile it renders as a `position: fixed`
  // overlay, which consumes ZERO flex space — so it floats out of this row
  // regardless of order. Hence the order is fixed (surface, then rail); the
  // docked-vs-overlay decision lives entirely in ChatDrawer.
  const surfaceColumn = (
    <div className="flex-1 min-w-0 overflow-hidden">
      <SurfaceViewport>{children}</SurfaceViewport>
    </div>
  );
  // main-rail region — chat. Owns its own open/closed + width + rail-vs-
  // overlay state. Renders a right rail (canvas), a fixed overlay (desktop/
  // mobile), or null-width when closed.
  const chatRail = mountRegion('main-rail');

  return (
    <>
      <div className="flex flex-col h-screen bg-background">
        {/* Top region — TopBarSurface (D12 + D14: merged dock-bar —
            brand · launcher trigger · Dock icons (kept ∪ open) ·
            user menu). */}
        {mountRegion('top')}

        {/* Global locator strip (2026-06-26) — the OS "you are here"
            indicator. ONE always-visible row (every layout, list + detail),
            mounted between the top bar and the content row. Replaces the
            per-window title-bar crumb that vanished in canvas mode. */}
        <GlobalLocatorStrip />

        {/* Main region — ADR-316 + ADR-358: a flex ROW. The surface column
            is flex-1. In CANVAS the chat rail docks RIGHT as a flex sibling
            (reduces the surface, never occludes). In DESKTOP/mobile chat is
            a fixed overlay (ChatDrawer's own branch) consuming zero flex
            space, so the row is just the surface column there. */}
        <main className="flex-1 min-h-0 overflow-hidden flex flex-row">
          {surfaceColumn}
          {chatRail}
        </main>

        {/* D12 + D16 (2026-05-21..22): bottom-floating + bottom-fixed
            regions intentionally NOT mounted.
              - D12 deleted the Dock kernel surface (responsibility
                absorbed into TopBarSurface).
              - D16 deleted the bottom-strip ChatComposerSurface
                (responsibility absorbed into ChatDrawerSurface in
                floating-overlay).
            Both LayoutRegions survive in the type union for future
            use but no kernel surface targets them today. */}
      </div>

      {/* Floating-overlay region — LauncherSurface only (ADR-316 moved
          ChatDrawerSurface to main-rail). Mounted outside the screen flow
          because overlays use their own fixed positioning + z-index. */}
      {mountRegion('floating-overlay')}
    </>
  );
}
