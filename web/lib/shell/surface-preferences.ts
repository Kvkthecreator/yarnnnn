/**
 * Shell preferences — ADR-297 D5 + D6.
 *
 * Operator's per-workspace surface preferences:
 *   - pinnedSurfaces: ordered list of surface slugs in the dock
 *   - lastActiveSurface: most-recently-active surface slug (drives home behavior)
 *
 * Persisted to localStorage (keyed by user id). Backend persistence
 * deferred — localStorage gives single-device continuity which covers
 * the dominant operator usage pattern. Cross-device sync becomes a
 * future ADR if pressure surfaces.
 *
 * Defaults (per ADR-297 D5):
 *   - pinnedSurfaces: ['feed'] (Feed only by default; operator pins more)
 *   - lastActiveSurface: 'feed' (first-time operators land on Feed)
 */

const PINNED_KEY_PREFIX = 'yarnnn:shell:pinned-surfaces:';
const LAST_ACTIVE_KEY_PREFIX = 'yarnnn:shell:last-active-surface:';

export const DEFAULT_PINNED_SURFACES: string[] = ['feed'];
export const DEFAULT_LAST_ACTIVE: string = 'feed';

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
// Last active surface (home behavior — ADR-297 D6)
// ----------------------------------------------------------------------------

export function getLastActiveSurface(userId: string): string {
  if (!isBrowser() || !userId) return DEFAULT_LAST_ACTIVE;
  try {
    const raw = localStorage.getItem(key(LAST_ACTIVE_KEY_PREFIX, userId));
    return raw || DEFAULT_LAST_ACTIVE;
  } catch {
    return DEFAULT_LAST_ACTIVE;
  }
}

export function setLastActiveSurface(userId: string, slug: string): void {
  if (!isBrowser() || !userId) return;
  try {
    localStorage.setItem(key(LAST_ACTIVE_KEY_PREFIX, userId), slug);
  } catch {
    // ignore
  }
}
