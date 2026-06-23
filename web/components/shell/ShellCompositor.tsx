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
 *                           ADR-358: child order is the layout mode — rail
 *                           LEFT in canvas, RIGHT in desktop.
 *   - `main-rail`        → dockable command rail (ADR-316, today:
 *                           ChatDrawerSurface). Reduces the surface area;
 *                           never occludes it. ADR-358: docks left in
 *                           canvas mode, right in desktop mode.
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
import {
  CHROME_SURFACE_REGISTRY,
  isChromeSurfaceSlug,
  type ChromeSurfaceSlug,
} from './ChromeRegistry';
import { useShellChrome } from './ShellChromeContext';
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
  const { layoutMode } = useShellChrome();
  const byRegion = partitionChromeByRegion(composition.surfaces || []);

  const mountRegion = (region: LayoutRegion) =>
    byRegion[region].map((slug) => {
      const Component = CHROME_SURFACE_REGISTRY[slug];
      return <Component key={slug} />;
    });

  // ADR-358 — the `main` flex row's child order is the spatial paradigm.
  // CANVAS: chat-rail LEFT, surface column right (the ChatGPT/Claude
  // convention). DESKTOP: surface column flex-1, chat-rail RIGHT (ADR-316
  // verbatim). The rail's own border + resize-edge flip is ChatDrawer's
  // concern; the compositor owns only sibling order here.
  const surfaceColumn = (
    <div className="flex-1 min-w-0 overflow-hidden">
      <SurfaceViewport>{children}</SurfaceViewport>
    </div>
  );
  // main-rail region — the dockable command rail (chat). It owns its own
  // open/closed + width + dock-side state; renders null-width when closed
  // (desktop) or as an overlay (mobile).
  const chatRail = mountRegion('main-rail');

  return (
    <>
      <div className="flex flex-col h-screen bg-background">
        {/* Top region — TopBarSurface (D12 + D14: merged dock-bar —
            brand · launcher trigger · Dock icons (kept ∪ open) ·
            user menu). */}
        {mountRegion('top')}

        {/* Main region — ADR-316 + ADR-358: a flex ROW. The window area
            (SurfaceViewport) is flex-1; the command rail (chat) docks as a
            flex sibling, reducing the window area instead of occluding it.
            ADR-358 — child ORDER is the spatial paradigm: CANVAS docks the
            rail LEFT (chat-interface convention), DESKTOP docks it RIGHT
            (ADR-316). On mobile the rail renders itself as a full-screen
            overlay (its own isMobile branch), so the row collapses to just
            the window area there. */}
        <main className="flex-1 min-h-0 overflow-hidden flex flex-row">
          {layoutMode === 'canvas' ? (
            <>
              {chatRail}
              {surfaceColumn}
            </>
          ) : (
            <>
              {surfaceColumn}
              {chatRail}
            </>
          )}
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
