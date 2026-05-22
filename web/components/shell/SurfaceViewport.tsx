'use client';

/**
 * SurfaceViewport — ADR-297 axiom + D13 multi-mount + D14 windows + D15 window manager.
 *
 * D15 (2026-05-22): full window-manager mode on desktop. Each open
 * surface mounts inside a WindowFrame that's absolutely-positioned at
 * its (x, y, width, height) from windowStates. The foregrounded
 * window has the highest z. All open windows are visually present;
 * pre-D15 'hidden' attribute single-window-at-a-time behavior is
 * dropped on desktop.
 *
 * Mobile (<MOBILE_BREAKPOINT_PX): single-window mode preserved. Only
 * the foregrounded window renders; multi-window UX collapses to
 * Dock-as-tab-switcher.
 *
 * Resolution order:
 *   1. mountSlugs = union of (registry-open) and (pathname-deep-link).
 *   2. Desktop: render every mountSlug absolute-positioned, z-stacked.
 *   3. Mobile: render only the foregrounded mountSlug, full-bleed.
 *   4. Empty registry + non-atomic pathname → legacy children.
 *   5. Empty registry + atomic-or-empty pathname → Desktop empty state.
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
  const { open, foregrounded, windowStates, closeSurface, raiseWindow, setWindowState } =
    useSurfacePreferences();
  const { data: composition } = useComposition();
  const viewport = useViewport();

  // Cold-load deep-link fallback (D13).
  const firstSegment = pathname.split('/').filter(Boolean)[0];
  const pathnameSlug: KernelSurfaceSlug | null =
    firstSegment && isKernelSurfaceSlug(firstSegment) ? firstSegment : null;

  const mountSlugs: KernelSurfaceSlug[] = (() => {
    const set = new Set<string>(open);
    if (pathnameSlug) set.add(pathnameSlug);
    return Array.from(set).filter(isKernelSurfaceSlug);
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

  if (mountSlugs.length === 0) {
    if (pathnameSlug === null && firstSegment) {
      return <>{children}</>;
    }
    return <Desktop />;
  }

  // Mobile: single-window mode — render only the foregrounded slug,
  // full-bleed within the desktop padding.
  if (viewport.isMobile) {
    const slug = visibleSlug;
    if (!slug) return <Desktop />;
    const Component = resolveSurfaceComponent(slug);
    return (
      <div className="h-full w-full bg-muted/30 p-2">
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
    );
  }

  // Desktop: full multi-window. Each surface is absolutely-positioned
  // at its window state. Position-relative parent so absolute children
  // inherit the viewport coordinate space.
  return (
    <div className="relative h-full w-full bg-muted/30">
      {mountSlugs.map((slug) => {
        const Component = resolveSurfaceComponent(slug);
        const isVisible = slug === visibleSlug;
        const ws = windowStates[slug];
        // If we don't have window state yet (first paint before the
        // foregroundSurface effect ran), skip rendering until it does
        // — prevents flash of un-positioned window at (0,0).
        if (!ws) return null;
        return (
          <WindowFrame
            key={slug}
            title={titleFor(slug)}
            isForegrounded={isVisible}
            onRaise={() => raiseWindow(slug)}
            onClose={() => closeSurface(slug)}
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
    </div>
  );
}
