'use client';

/**
 * SurfaceViewport — ADR-297 axiom (2026-05-21) + D13 multi-mount + D14 windows.
 *
 * The shell's single content slot. Renders every open surface from the
 * registry inside a WindowFrame (D14), with the foregrounded surface
 * visible and all others hidden via the `hidden` attribute
 * (display: none). The visible "desktop wallpaper" border around the
 * window is the viewport's own background showing through the inset
 * padding.
 *
 * Resolution order:
 *
 *   1. For every slug in useSurfacePreferences().open, mount that
 *      surface's component inside a WindowFrame. Apply `hidden` to all
 *      but the foregrounded one. Surfaces preserve their state
 *      (scroll position, form drafts, expanded sections, in-flight
 *      network requests) across foreground/background transitions.
 *
 *   2. If the open registry is empty, fall back to:
 *      a. URL pathname (deep-link transport — cold load to /cadence
 *         etc. opens that surface before the foregroundSurface effect
 *         in AuthenticatedLayout has fired).
 *      b. If pathname doesn't resolve to a kernel surface either,
 *         render the Desktop empty state (D13 §5) — no WindowFrame,
 *         the desktop wallpaper extends edge-to-edge.
 *
 *   3. Children (legacy non-atomic routes) render as fallback only
 *      when neither (1) nor (2a) resolves.
 *
 * Why mount-not-just-foreground: D13 commits to macOS-literal lifecycle.
 * Hiding via CSS preserves: React state, scroll position, in-flight
 * fetches, expanded UI sections, focused inputs. The cost is the React
 * tree memory of every open surface — bounded by kernel count (today
 * ≤13 content surfaces). No LRU eviction; operator closes what they
 * don't want.
 *
 * Why each surface gets a WindowFrame (D14): the operator-visible
 * affordance of "this is a window" was missing pre-D14. The 32px
 * title bar + close × inside the frame is the surface's visible
 * window chrome.
 */

import { type ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { useComposition } from '@/lib/compositor/useComposition';
import { isKernelSurfaceSlug } from '@/types/desk';
import type { KernelSurfaceSlug } from '@/types/desk';
import { resolveSurfaceComponent } from './SurfaceRegistry';
import { Desktop } from './Desktop';
import { WindowFrame } from './WindowFrame';

interface SurfaceViewportProps {
  /**
   * Fallback rendered when neither the open-surfaces registry nor the
   * URL pathname resolves to a kernel surface slug. Used for non-atomic
   * routes (legacy).
   */
  children?: ReactNode;
}

export function SurfaceViewport({ children }: SurfaceViewportProps) {
  const pathname = usePathname();
  const { open, foregrounded, closeSurface } = useSurfacePreferences();
  const { data: composition } = useComposition();

  // Cold-load fallback: if the URL deep-links to an atomic surface
  // but the registry hasn't hydrated yet, mount that surface anyway.
  // The AuthenticatedLayout's pathname watcher will fold it into the
  // registry on the next tick.
  const firstSegment = pathname.split('/').filter(Boolean)[0];
  const pathnameSlug: KernelSurfaceSlug | null =
    firstSegment && isKernelSurfaceSlug(firstSegment) ? firstSegment : null;

  // Union of (registry-open) and (pathname-deep-link), preserving the
  // registry's order; pathname slug appended if not already present.
  const mountSlugs: KernelSurfaceSlug[] = (() => {
    const set = new Set<string>(open);
    if (pathnameSlug) set.add(pathnameSlug);
    return Array.from(set).filter(isKernelSurfaceSlug);
  })();

  // Determine which slug is foregrounded (visible). Priority:
  //   1. foregrounded (from registry) if present in mountSlugs
  //   2. pathnameSlug if registry hasn't decided yet
  //   3. last item in mountSlugs (most-recently-opened)
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
    // Fallback: kebab → Title Case
    return slug
      .split('-')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  };

  // Empty registry + non-atomic pathname → let legacy children render.
  if (mountSlugs.length === 0) {
    if (pathnameSlug === null && firstSegment) {
      return <>{children}</>;
    }
    return <Desktop />;
  }

  return (
    // D14: desktop wallpaper margin. The window frames sit inside this
    // padded area, with the muted background showing through as the
    // visible desktop. Inset proportions: 12px on all sides at mobile,
    // 16px at sm+.
    <div className="h-full w-full bg-muted/30 p-3 sm:p-4">
      {mountSlugs.map((slug) => {
        const Component = resolveSurfaceComponent(slug);
        const isVisible = slug === visibleSlug;
        return (
          <div
            key={slug}
            hidden={!isVisible}
            className="h-full w-full"
          >
            <WindowFrame
              title={titleFor(slug)}
              isForegrounded={isVisible}
              onClose={() => closeSurface(slug)}
            >
              <Component />
            </WindowFrame>
          </div>
        );
      })}
    </div>
  );
}
