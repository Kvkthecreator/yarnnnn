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

// ADR-385 follow-on (2026-06-30): the render-alias TITLE map (`feed`/`context`
// → `channels`) is DELETED. Those legacy slugs were retired from the registry
// (full alias deletion); persisted dock/foreground state naming them is now
// normalized → `channels` at the surface-preferences READ boundary
// (lib/shell/surface-preferences.ts), so no `feed`/`context` slug ever reaches
// this resolver. The single normalization point replaces the scattered
// per-consumer alias handling (registry / title / chat-drawer) — Singular
// Implementation.

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
  const resolved = slug;
  const match = (surfaces || []).find((s) => s.slug === resolved);
  if (match?.title) return match.title;
  // Title-Case the slug as a last resort (e.g. "workspace-settings" →
  // "Workspace Settings") so an unregistered slug still reads cleanly.
  return resolved
    .split('-')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}
