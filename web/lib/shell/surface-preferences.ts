/**
 * Shell preferences — ADR-297 D5 + D6 + D13.
 *
 * Operator's per-workspace surface preferences:
 *   - pinnedSurfaces: ordered list of surface slugs in the dock (D5)
 *   - openSurfaces: ordered list of currently-mounted surface slugs (D13)
 *   - foregroundedSurface: the one slug currently visible in main (D13)
 *
 * D13 (2026-05-21) replaced the prior single `lastActiveSurface` slot
 * with the open-surfaces registry + foregrounded pointer. "Last-active"
 * is now a property of `foregroundedSurface` (the most-recently-
 * foregrounded slug); when the registry is empty, the operator boots
 * to the desktop empty state (D13 §5).
 *
 * Persisted to localStorage (keyed by user id). Backend persistence
 * deferred — localStorage gives single-device continuity which covers
 * the dominant operator usage pattern. Cross-device sync becomes a
 * future ADR if pressure surfaces.
 *
 * Defaults (per ADR-297 D5 + D13):
 *   - pinnedSurfaces: ['feed'] (Feed only by default — D5 unchanged)
 *   - openSurfaces: [] (first-time operators boot to desktop — D13)
 *   - foregroundedSurface: null (no surface foregrounded on first boot)
 */

const PINNED_KEY_PREFIX = 'yarnnn:shell:pinned-surfaces:';
const OPEN_KEY_PREFIX = 'yarnnn:shell:open-surfaces:';
const FOREGROUND_KEY_PREFIX = 'yarnnn:shell:foregrounded-surface:';

export const DEFAULT_PINNED_SURFACES: string[] = ['feed'];
export const DEFAULT_OPEN_SURFACES: string[] = [];
export const DEFAULT_FOREGROUNDED_SURFACE: string | null = null;

function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof localStorage !== 'undefined';
}

function key(prefix: string, userId: string): string {
  return `${prefix}${userId}`;
}

// ----------------------------------------------------------------------------
// Pinned surfaces
// ----------------------------------------------------------------------------

export function getPinnedSurfaces(userId: string): string[] {
  if (!isBrowser() || !userId) return DEFAULT_PINNED_SURFACES;
  try {
    const raw = localStorage.getItem(key(PINNED_KEY_PREFIX, userId));
    if (!raw) return DEFAULT_PINNED_SURFACES;
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.every((s) => typeof s === 'string')) {
      return parsed;
    }
    return DEFAULT_PINNED_SURFACES;
  } catch {
    return DEFAULT_PINNED_SURFACES;
  }
}

export function setPinnedSurfaces(userId: string, slugs: string[]): void {
  if (!isBrowser() || !userId) return;
  try {
    localStorage.setItem(key(PINNED_KEY_PREFIX, userId), JSON.stringify(slugs));
  } catch {
    // localStorage may throw in private-browsing mode; silently noop.
  }
}

export function pinSurface(userId: string, slug: string): string[] {
  const current = getPinnedSurfaces(userId);
  if (current.includes(slug)) return current;
  const next = [...current, slug];
  setPinnedSurfaces(userId, next);
  return next;
}

export function unpinSurface(userId: string, slug: string): string[] {
  const current = getPinnedSurfaces(userId);
  const next = current.filter((s) => s !== slug);
  setPinnedSurfaces(userId, next);
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
//
// D13 deleted the prior `lastActiveSurface` slot — the
// foregroundedSurface IS the last-active concept. When the operator
// returns to yarnnn.com, they boot to the foregroundedSurface; if the
// open list is empty, they boot to the desktop empty state.

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
 *  the resulting list (operator pin order preserved; newly-opened
 *  surfaces append to the tail per macOS Dock convention). */
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
