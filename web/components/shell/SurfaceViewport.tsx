'use client';

/**
 * SurfaceViewport — ADR-297 axiom (2026-05-21) + D13 multi-mount.
 *
 * The shell's single content slot. Pre-D13 mounted exactly one surface
 * (the active one) and unmounted prior ones on dispatch. D13
 * (2026-05-21) shifted to the macOS-window-manager metaphor: every
 * open surface stays mounted; non-foregrounded ones are hidden via
 * `hidden` attribute (display: none).
 *
 * Resolution order (D13):
 *
 *   1. For every slug in useSurfacePreferences().open, mount that
 *      surface's component. Apply `hidden` to all but the foregrounded
 *      one. Surfaces preserve their state (scroll position, form
 *      drafts, expanded sections, in-flight network requests) across
 *      foreground/background transitions.
 *
 *   2. If the open registry is empty, fall back to:
 *      a. URL pathname (deep-link transport — cold load to /cadence
 *         etc. mounts that surface before DeskContext/useSurfacePreferences
 *         have hydrated). The AuthenticatedLayout's pathname watcher
 *         calls foregroundSurface(slug) which populates the registry
 *         on the first tick post-hydration.
 *      b. If pathname doesn't resolve to a kernel surface either,
 *         render the Desktop empty state (D13 §5).
 *
 *   3. Children (legacy non-atomic routes) render as fallback only
 *      when neither (1) nor (2a) resolves.
 *
 * Why mount-not-just-foreground: D13 commits to macOS-literal lifecycle.
 * Hiding via CSS preserves: React state, scroll position, in-flight
 * fetches, expanded UI sections, focused inputs. The cost is the React
 * tree memory of every open surface — bounded by kernel count (today
 * ≤16 content surfaces) plus small program contribution. If a surface
 * proves heavy we add per-surface virtualization; no LRU eviction.
 * Operator closes what they don't want — that's the contract.
 */

import { type ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { isKernelSurfaceSlug } from '@/types/desk';
import type { KernelSurfaceSlug } from '@/types/desk';
import { resolveSurfaceComponent } from './SurfaceRegistry';
import { Desktop } from './Desktop';

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
  const { open, foregrounded } = useSurfacePreferences();

  // Compute the pathname-derived slug ONCE per render. Used as a
  // cold-load fallback before the foregroundSurface effect in
  // AuthenticatedLayout has fired (registry not yet hydrated). Also
  // ensures the surface is mounted even if the registry persistence
  // lags (e.g. operator pasted a deep link with localStorage cleared).
  const firstSegment = pathname.split('/').filter(Boolean)[0];
  const pathnameSlug: KernelSurfaceSlug | null =
    firstSegment && isKernelSurfaceSlug(firstSegment) ? firstSegment : null;

  // Build the active mount list: union of (registry-open) and
  // (pathname-deep-link), preserving the registry's order. Dedupe via
  // Set so a deep-link to an already-open surface doesn't double-mount.
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
    if (foregrounded && isKernelSurfaceSlug(foregrounded) && mountSlugs.includes(foregrounded)) {
      return foregrounded;
    }
    if (pathnameSlug && mountSlugs.includes(pathnameSlug)) {
      return pathnameSlug;
    }
    return mountSlugs.length > 0 ? mountSlugs[mountSlugs.length - 1] : null;
  })();

  // If neither the registry nor the URL has anything → Desktop empty
  // state. Only when the URL is non-atomic (legacy route) AND nothing
  // is open do we fall through to children (preserves legacy fallback
  // for /settings, /connectors, /docs, etc.).
  if (mountSlugs.length === 0) {
    // Pathname is non-atomic; let legacy children render. If pathname
    // would have been atomic we'd be in mountSlugs already.
    if (pathnameSlug === null && firstSegment) {
      return <>{children}</>;
    }
    return <Desktop />;
  }

  return (
    <>
      {mountSlugs.map((slug) => {
        const Component = resolveSurfaceComponent(slug);
        const isVisible = slug === visibleSlug;
        return (
          <div
            key={slug}
            hidden={!isVisible}
            // The hidden attribute applies display:none; using a
            // wrapper div per surface preserves the surface
            // component's own layout while letting us toggle
            // visibility without unmounting.
            className="h-full w-full"
          >
            <Component />
          </div>
        );
      })}
    </>
  );
}
