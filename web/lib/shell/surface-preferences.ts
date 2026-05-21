/**
 * Shell preferences — ADR-297 D5 + D6 + D13 + D14.
 *
 * Operator's per-workspace surface preferences:
 *   - keptSurfaces:        dock-permanence surfaces (D14 — was `pinned`)
 *   - openSurfaces:        currently-mounted surface slugs (D13)
 *   - foregroundedSurface: the one slug currently visible in main (D13)
 *
 * D14 (2026-05-21) renamed `pinnedSurfaces` → `keptSurfaces`. The
 * concept reframed: pinning was a separate "this is in the Dock" rail;
 * keeping is the macOS "Keep in Dock" permanence toggle on a Dock icon
 * whose surface is open OR independently kept. The Dock's contents
 * are the UNION of kept + open. See ADR-297 §D14.
 *
 * D13 (2026-05-21) introduced openSurfaces + foregroundedSurface,
 * replacing the prior single `lastActiveSurface` slot.
 *
 * Persisted to localStorage (keyed by user id). Backend persistence
 * deferred — localStorage gives single-device continuity which covers
 * the dominant operator usage pattern. Cross-device sync becomes a
 * future ADR if pressure surfaces.
 *
 * Defaults:
 *   - keptSurfaces:        ['feed'] (D5 rationale preserved through D14
 *                          rename — first-boot operators see Feed as
 *                          their one Dock anchor)
 *   - openSurfaces:        [] (first-time operators boot to desktop — D13)
 *   - foregroundedSurface: null (no surface foregrounded on first boot)
 */

const KEPT_KEY_PREFIX = 'yarnnn:shell:kept-surfaces:';
const OPEN_KEY_PREFIX = 'yarnnn:shell:open-surfaces:';
const FOREGROUND_KEY_PREFIX = 'yarnnn:shell:foregrounded-surface:';

export const DEFAULT_KEPT_SURFACES: string[] = ['feed'];
export const DEFAULT_OPEN_SURFACES: string[] = [];
export const DEFAULT_FOREGROUNDED_SURFACE: string | null = null;

function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof localStorage !== 'undefined';
}

function key(prefix: string, userId: string): string {
  return `${prefix}${userId}`;
}

// ----------------------------------------------------------------------------
// Kept surfaces (D14 — was `pinned`)
// ----------------------------------------------------------------------------
//
// The macOS "Keep in Dock" permanence toggle. A surface is "kept" when
// the operator has explicitly declared they want it in the Dock
// regardless of whether it's currently open. The Dock's contents are
// the UNION of kept ∪ open; see TopBarSurface for the rendering.

export function getKeptSurfaces(userId: string): string[] {
  if (!isBrowser() || !userId) return DEFAULT_KEPT_SURFACES;
  try {
    const raw = localStorage.getItem(key(KEPT_KEY_PREFIX, userId));
    if (!raw) return DEFAULT_KEPT_SURFACES;
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.every((s) => typeof s === 'string')) {
      return parsed;
    }
    return DEFAULT_KEPT_SURFACES;
  } catch {
    return DEFAULT_KEPT_SURFACES;
  }
}

export function setKeptSurfaces(userId: string, slugs: string[]): void {
  if (!isBrowser() || !userId) return;
  try {
    localStorage.setItem(key(KEPT_KEY_PREFIX, userId), JSON.stringify(slugs));
  } catch {
    // localStorage may throw in private-browsing mode; silently noop.
  }
}

export function keepSurface(userId: string, slug: string): string[] {
  const current = getKeptSurfaces(userId);
  if (current.includes(slug)) return current;
  const next = [...current, slug];
  setKeptSurfaces(userId, next);
  return next;
}

export function releaseSurface(userId: string, slug: string): string[] {
  const current = getKeptSurfaces(userId);
  const next = current.filter((s) => s !== slug);
  setKeptSurfaces(userId, next);
  return next;
}

// ----------------------------------------------------------------------------
// Open surfaces (D13 — multi-surface lifecycle)
// ----------------------------------------------------------------------------
//
// The open-surfaces registry tracks which content surfaces are currently
// mounted in the React tree. Exactly one of them is foregrounded
// (visible in `main`); the rest are hidden via `display: none` but
// preserve their state. macOS Dock metaphor — surfaces are windows.

export function getOpenSurfaces(userId: string): string[] {
  if (!isBrowser() || !userId) return DEFAULT_OPEN_SURFACES;
  try {
    const raw = localStorage.getItem(key(OPEN_KEY_PREFIX, userId));
    if (!raw) return DEFAULT_OPEN_SURFACES;
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.every((s) => typeof s === 'string')) {
      return parsed;
    }
    return DEFAULT_OPEN_SURFACES;
  } catch {
    return DEFAULT_OPEN_SURFACES;
  }
}

export function setOpenSurfaces(userId: string, slugs: string[]): void {
  if (!isBrowser() || !userId) return;
  try {
    localStorage.setItem(key(OPEN_KEY_PREFIX, userId), JSON.stringify(slugs));
  } catch {
    // ignore
  }
}

/** Add a surface to the open registry if not already present. Returns
 *  the resulting list (newly-opened surfaces append to the tail per
 *  macOS Dock convention). */
export function openSurface(userId: string, slug: string): string[] {
  const current = getOpenSurfaces(userId);
  if (current.includes(slug)) return current;
  const next = [...current, slug];
  setOpenSurfaces(userId, next);
  return next;
}

/** Remove a surface from the open registry. Returns the resulting list. */
export function closeSurface(userId: string, slug: string): string[] {
  const current = getOpenSurfaces(userId);
  const next = current.filter((s) => s !== slug);
  setOpenSurfaces(userId, next);
  return next;
}

// ----------------------------------------------------------------------------
// Foregrounded surface (D13 — replaces D6 lastActive concept)
// ----------------------------------------------------------------------------

export function getForegroundedSurface(userId: string): string | null {
  if (!isBrowser() || !userId) return DEFAULT_FOREGROUNDED_SURFACE;
  try {
    const raw = localStorage.getItem(key(FOREGROUND_KEY_PREFIX, userId));
    return raw || DEFAULT_FOREGROUNDED_SURFACE;
  } catch {
    return DEFAULT_FOREGROUNDED_SURFACE;
  }
}

export function setForegroundedSurface(userId: string, slug: string | null): void {
  if (!isBrowser() || !userId) return;
  try {
    if (slug === null) {
      localStorage.removeItem(key(FOREGROUND_KEY_PREFIX, userId));
    } else {
      localStorage.setItem(key(FOREGROUND_KEY_PREFIX, userId), slug);
    }
  } catch {
    // ignore
  }
}
