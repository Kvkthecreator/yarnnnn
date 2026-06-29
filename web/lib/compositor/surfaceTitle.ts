/**
 * surfaceTitleFor — resolve a kernel/program surface slug to its display
 * title from the live composition, with a Title-Case fallback.
 *
 * Extracted (2026-06-26) from SurfaceViewport's inline `titleBySlug` +
 * `titleFor` so the two consumers — the WindowFrame title bar
 * (SurfaceViewport) and the GlobalLocatorStrip — share ONE implementation
 * (Singular Implementation; no duplicated map+fallback logic).
 */

import type { Surface } from '@/lib/compositor/types';

// Render-alias slugs: a slug that the SurfaceRegistry maps to ANOTHER surface's
// component should borrow that surface's TITLE too. `feed` + `context` both
// render ChannelsPage (ADR-370 — Feed dissolved into the perception surface;
// ADR-385 — that surface renamed `context` → `channels`), so a window/dock
// state still foregrounding the legacy `feed`/`context` slugs must read
// "Channels". Without this, existing operators (with `feed`/`context` persisted
// in their kept/foreground localStorage) saw a stale title even though the body
// IS Channels. The DEFAULT_KEPT fix covers fresh/cleared operators; this covers
// the already-persisted ones.
const TITLE_ALIAS: Record<string, string> = {
  feed: 'channels',
  context: 'channels',
};

/**
 * @param surfaces composition.surfaces (may be undefined before load)
 * @param slug the surface slug, or null (empty Desktop)
 * @param fallback what to return when slug is null/empty (default 'Desktop')
 */
export function surfaceTitleFor(
  surfaces: Surface[] | undefined,
  slug: string | null,
  fallback = 'Desktop'
): string {
  if (!slug) return fallback;
  const resolved = TITLE_ALIAS[slug] ?? slug;
  const match = (surfaces || []).find((s) => s.slug === resolved);
  if (match?.title) return match.title;
  // Title-Case the slug as a last resort (e.g. "workspace-settings" →
  // "Workspace Settings") so an unregistered slug still reads cleanly.
  return resolved
    .split('-')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}
