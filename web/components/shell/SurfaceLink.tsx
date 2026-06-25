'use client';

/**
 * SurfaceLink — the sanctioned cross-surface link (2026-06-25).
 *
 * The ONE way a component links from one surface to another. Renders a real
 * `<a>` (so middle-click / cmd-click / "open in new tab" and screen readers
 * all work) but intercepts the plain left-click and routes it through
 * `navigateToSurface(slug, params)` — the compositor's window manager —
 * instead of letting the browser hard-navigate. That keeps the OS shell on
 * its `/desktop` baseline (ADR-358 D5): the target surface foregrounds as a
 * window, the docked chat persists, and params land window-namespaced
 * (`{slug}.{key}`) with no collision (ADR-358 D6).
 *
 * WHY THIS EXISTS: the pre-OS-shell pattern was `<Link href="/recurrence?…">`.
 * Next treats that as a route navigation → the pathname flips off `/desktop`
 * → the SPA unmounts and remounts, resetting chat and re-running the shell's
 * pathname→foreground effects. That's the "inconsistent redirect" operators
 * felt: some launches foregrounded a window cleanly (navigateToSurface),
 * others hard-navigated (<Link>). SurfaceLink makes every cross-surface jump
 * take the window-manager path while preserving native link affordances.
 *
 * Use `navigateToSurface(...)` directly for button-shaped triggers; use
 * SurfaceLink when the trigger is semantically a link (text/inline).
 *
 * The href is computed for native affordances only (`/{slug}` + namespaced
 * query) — the plain click never uses it.
 */

import type { AnchorHTMLAttributes, MouseEvent, ReactNode } from 'react';
import { useSurfacePreferences, scopeParamKey } from '@/lib/shell/useSurfacePreferences';
import type { KernelSurfaceSlug } from '@/types/desk';

interface SurfaceLinkProps
  extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> {
  /** Target surface kernel slug (e.g. 'recurrence', 'files', 'connectors'). */
  to: KernelSurfaceSlug;
  /** Optional intra-surface deep-link params (bare keys — namespaced for you). */
  params?: Record<string, string>;
  children: ReactNode;
}

export function SurfaceLink({ to, params, children, onClick, ...rest }: SurfaceLinkProps) {
  const { navigateToSurface } = useSurfacePreferences();

  // Native href for middle-click / new-tab / a11y. Plain click is intercepted.
  const href = (() => {
    const qs = new URLSearchParams();
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v != null && v !== '') qs.set(scopeParamKey(to, k), v);
      }
    }
    const query = qs.toString();
    return `/${to}${query ? `?${query}` : ''}`;
  })();

  const handleClick = (e: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e);
    if (e.defaultPrevented) return;
    // Let the browser handle modified clicks (new tab / window / download).
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
    e.preventDefault();
    navigateToSurface(to, params);
  };

  return (
    <a href={href} onClick={handleClick} {...rest}>
      {children}
    </a>
  );
}
