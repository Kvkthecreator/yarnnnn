'use client';

/**
 * SurfaceViewport — ADR-297 axiom + D13 multi-mount + D14 windows + D15 window manager + D17 unified Desktop.
 *
 * D17 (2026-05-22): unifies the prior two code paths (`<Desktop />`
 * empty-state component vs inline padded wrapper around windows) into
 * one always-rendered Desktop layer. The Desktop component now owns:
 *   - padded gray background
 *   - context-aware empty-state copy (visible when no windows)
 *   - the ChatFAB (D17 §7 — moved off viewport-fixed)
 * Windows mount as absolute-positioned children of the Desktop layer.
 *
 * Resolution order (D17):
 *   1. mountSlugs = union of (registry-open) and (pathname-deep-link).
 *   2. Desktop layer ALWAYS renders.
 *   3. Desktop empty-state copy visible iff mountSlugs is empty.
 *   4. Mobile (<MOBILE_BREAKPOINT_PX): one window full-bleed inside Desktop.
 *   5. Desktop: all open windows absolute-positioned + z-stacked.
 *
 * Pathname behavior (D17):
 *   - /desktop → no pathnameSlug; Desktop renders + restores
 *     whatever is in the open-surfaces registry.
 *   - /{surface-slug} → pathnameSlug = the slug; deep-link transport
 *     opens that surface in addition to whatever's in the registry.
 *   - Other authenticated routes (settings, connectors, docs, etc.)
 *     → not handled here; AuthenticatedLayout's ShellCompositor passes
 *     their page render through `children` only if mountSlugs is
 *     empty AND pathname isn't /desktop.
 */

import { type ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { useComposition } from '@/lib/compositor/useComposition';
import { useViewport } from '@/lib/shell/useViewport';
import { isKernelSurfaceSlug } from '@/types/desk';
import type { KernelSurfaceSlug } from '@/types/desk';
import { resolveSurfaceComponent } from './SurfaceRegistry';
import { Desktop } from './Desktop';
import { WindowFrame } from './WindowFrame';

interface SurfaceViewportProps {
  children?: ReactNode;
}

export function SurfaceViewport({ children }: SurfaceViewportProps) {
  const pathname = usePathname();
  const {
    open,
    foregrounded,
    windowStates,
    closeSurface,
    raiseWindow,
    setWindowState,
    toggleMaximize,
    minimizeWindow,
  } = useSurfacePreferences();
  const { data: composition } = useComposition();
  const viewport = useViewport();

  // Cold-load deep-link fallback (D13). Recognize per-slug routes as
  // transports that open the named surface; the /desktop route itself
  // produces no pathnameSlug and just shows the Desktop layer.
  const firstSegment = pathname.split('/').filter(Boolean)[0];
  const pathnameSlug: KernelSurfaceSlug | null =
    firstSegment && isKernelSurfaceSlug(firstSegment) ? firstSegment : null;
  const isDesktopRoute = pathname === '/desktop';

  // D19.3 (2026-05-22) — mountSlugs filters minimized windows out of
  // the render set so they vanish visually while their slugs stay in
  // the `open` registry (so the Dock icon retains its open-indicator).
  // Restore via foregroundSurface (Dock-click on minimized icon).
  const mountSlugs: KernelSurfaceSlug[] = (() => {
    const set = new Set<string>(open);
    if (pathnameSlug) set.add(pathnameSlug);
    return Array.from(set)
      .filter(isKernelSurfaceSlug)
      .filter((slug) => !windowStates[slug]?.minimized);
  })();

  const visibleSlug: KernelSurfaceSlug | null = (() => {
    if (
      foregrounded &&
      isKernelSurfaceSlug(foregrounded) &&
      mountSlugs.includes(foregrounded)
    ) {
      return foregrounded;
    }
    if (pathnameSlug && mountSlugs.includes(pathnameSlug)) {
      return pathnameSlug;
    }
    return mountSlugs.length > 0 ? mountSlugs[mountSlugs.length - 1] : null;
  })();

  // Surface-title lookup for the WindowFrame title bar.
  const titleBySlug = (() => {
    const map = new Map<string, string>();
    (composition.surfaces || []).forEach((s) => map.set(s.slug, s.title));
    return map;
  })();
  const titleFor = (slug: string): string => {
    const t = titleBySlug.get(slug);
    if (t) return t;
    return slug
      .split('-')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  };

  // D17: legacy non-atomic routes (settings, connectors, docs, etc.)
  // pass through to their page render via `children`. The /desktop
  // route + per-slug routes both render the Desktop layer (with or
  // without windows).
  const isLegacyNonAtomicRoute =
    !isDesktopRoute && pathnameSlug === null && firstSegment !== undefined;
  if (isLegacyNonAtomicRoute && mountSlugs.length === 0) {
    return <>{children}</>;
  }

  const hasWindows = mountSlugs.length > 0;

  // Mobile single-window mode (D15). Only the foregrounded window
  // renders, full-bleed inside the Desktop layer.
  if (viewport.isMobile && hasWindows) {
    const slug = visibleSlug;
    if (slug) {
      const Component = resolveSurfaceComponent(slug);
      return (
        <Desktop hasWindows={true}>
          <div className="absolute inset-3 sm:inset-4">
            <WindowFrame
              title={titleFor(slug)}
              isForegrounded={true}
              onRaise={() => raiseWindow(slug)}
              onClose={() => closeSurface(slug)}
              interactive={false}
            >
              <Component />
            </WindowFrame>
          </div>
        </Desktop>
      );
    }
  }

  // Desktop multi-window mode (D15). All open windows absolute-
  // positioned + z-stacked on top of the Desktop layer.
  return (
    <Desktop hasWindows={hasWindows}>
      {mountSlugs.map((slug) => {
        const Component = resolveSurfaceComponent(slug);
        const isVisible = slug === visibleSlug;
        const ws = windowStates[slug];
        // Skip rendering before window state hydrates — prevents flash
        // of un-positioned window at (0,0).
        if (!ws) return null;
        return (
          <WindowFrame
            key={slug}
            title={titleFor(slug)}
            isForegrounded={isVisible}
            onRaise={() => raiseWindow(slug)}
            onClose={() => closeSurface(slug)}
            onMinimize={() => {
              // D19.3 (2026-05-22): minimize = set minimized:true on
              // the window's state. SurfaceViewport then skips
              // rendering this slug; the Dock icon retains the open-
              // indicator dot. Click Dock icon to restore (the
              // foregroundSurface path clears minimized + raises).
              //
              // Pre-D19.3 wired to hideForegrounded() which silently
              // no-op'd when this was the only window — operator
              // observed "minimize doesn't work at all" (KVK
              // 2026-05-22). Direct minimizeWindow(slug) always works.
              minimizeWindow(slug);
            }}
            onMaximize={() => toggleMaximize(slug)}
            windowState={ws}
            viewportWidth={viewport.width}
            viewportHeight={viewport.height}
            onWindowStateChange={(state) => setWindowState(slug, state)}
            interactive={true}
          >
            <Component />
          </WindowFrame>
        );
      })}
    </Desktop>
  );
}
