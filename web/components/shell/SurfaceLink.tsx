'use client';

/**
 * SurfaceLink — the sanctioned cross-surface link (2026-06-25).
 *
 * The ONE way a component links from one surface to another. Renders a real
 * `<a>` (so middle-click / cmd-click / "open in new tab" and screen readers
 * all work) but intercepts the plain left-click and routes it through
 * `navigateToSurface(slug, params)` — the compositor's window manager —
 * instead of letting the browser hard-navigate. The target surface foregrounds
 * as a window, the docked chat persists, and params land window-namespaced
 * (`{slug}.{key}`) with no collision (ADR-358 D6).
 *
 * WHY THIS EXISTS: the pre-OS-shell pattern was `<Link href="/recurrence?…">`.
 * Next treats that as a route navigation → the SPA unmounts and remounts,
 * resetting chat and re-running the shell's pathname→foreground effects. On
 * remount the shell paints the REMEMBERED foreground (the surface you left)
 * and only then foregrounds the target — the operator-visible TWO-STEP. That's
 * the "inconsistent redirect" operators felt: some launches foregrounded a
 * window cleanly (navigateToSurface), others hard-navigated (<Link>).
 * SurfaceLink makes every cross-surface jump take the window-manager path
 * while preserving native link affordances.
 *
 * ⚠️ The two-step recurred 2026-08-20 in four Settings cross-door links that
 * never adopted this component. `api/test_adr297_navigation_enactment.py` now
 * bans a literal href to a kernel-surface route in live component code.
 *
 * NOTE (2026-08-20, ADR-297 D19.8): this used to say the point was keeping the
 * shell on its `/desktop` baseline (ADR-358 D5). That half is WITHDRAWN — the
 * pathname now FOLLOWS the foreground, so navigateToSurface writes `/{slug}`.
 * It does so via `replaceState` (no navigation event, no remount), which is why
 * chat still persists. The reason to use SurfaceLink is unchanged; only the
 * stated mechanism is corrected.
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
