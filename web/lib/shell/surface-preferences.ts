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
const WINDOW_STATE_KEY_PREFIX = 'yarnnn:shell:window-state:';

export const DEFAULT_KEPT_SURFACES: string[] = ['feed'];
export const DEFAULT_OPEN_SURFACES: string[] = [];
export const DEFAULT_FOREGROUNDED_SURFACE: string | null = null;

// D15 — window manager soft cap.
export const MAX_OPEN_WINDOWS = 8;
// D15 — mobile breakpoint below which we collapse to single-window UX.
export const MOBILE_BREAKPOINT_PX = 640;
// D15 — minimum window dimensions (clamped during resize).
export const WINDOW_MIN_WIDTH = 320;
export const WINDOW_MIN_HEIGHT = 240;
// D15 — cascade offset between newly-opened windows.
export const CASCADE_OFFSET_PX = 30;
// D15 — default window dimensions (% of viewport).
export const DEFAULT_WINDOW_WIDTH_PCT = 0.7;
export const DEFAULT_WINDOW_HEIGHT_PCT = 0.7;

// D17 — FAB reserved zone on the Desktop layer. The FAB lives at the
// Desktop's bottom-center; windows cannot be positioned or resized
// such that their bottom edge extends into this zone. Guarantees the
// FAB stays reachable regardless of window arrangement.
//
// Zone shape: centered horizontally at the bottom, FAB_RESERVED_WIDTH
// wide × FAB_RESERVED_HEIGHT tall. Windows must have their bottom
// edge AT LEAST `FAB_RESERVED_HEIGHT` above the viewport bottom WHEN
// their horizontal extent overlaps the central column where the FAB
// sits. Outside the central column, windows can extend further down.
export const FAB_RESERVED_WIDTH = 96; // central column width (px)
export const FAB_RESERVED_HEIGHT = 80; // bottom strip height (px)

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

// ----------------------------------------------------------------------------
// Window state (D15 — window manager)
// ----------------------------------------------------------------------------
//
// Per-surface window geometry + z-order. Persisted as a single record
// per userId keyed by slug. Newly-opened surfaces with no prior entry
// receive a cascade-derived default; closed surfaces retain their
// last-used arrangement so Re-Open lands them where they were.

export interface WindowState {
  /** Top-left corner pixel position, viewport-relative. */
  x: number;
  y: number;
  width: number;
  height: number;
  /** Relative z-order among open windows. Highest = foreground. */
  z: number;
  /**
   * D19.1 (2026-05-22) — macOS-style zoom (maximize). When a window is
   * zoomed-to-fill-desktop, `prevGeometry` holds the pre-zoom geometry
   * so the second maximize click restores it. When undefined, the
   * window is in its normal (un-zoomed) state.
   *
   * Geometry shape is the un-zoomed x/y/width/height; z is excluded
   * (z-order is preserved across maximize/restore via the live `z`
   * field). Persisted to localStorage like the rest of WindowState.
   */
  prevGeometry?: { x: number; y: number; width: number; height: number };
}

export type WindowStateMap = Record<string, WindowState>;

export function getWindowStates(userId: string): WindowStateMap {
  if (!isBrowser() || !userId) return {};
  try {
    const raw = localStorage.getItem(key(WINDOW_STATE_KEY_PREFIX, userId));
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as WindowStateMap;
    }
    return {};
  } catch {
    return {};
  }
}

export function setWindowStates(userId: string, states: WindowStateMap): void {
  if (!isBrowser() || !userId) return;
  try {
    localStorage.setItem(key(WINDOW_STATE_KEY_PREFIX, userId), JSON.stringify(states));
  } catch {
    // ignore
  }
}

/** D19.1 — Compute the "maximized" geometry for a window: fill the
 *  available desktop area (viewport minus top bar minus FAB reserved
 *  zone at bottom minus horizontal padding). This is the macOS "zoom"
 *  target — fills the available work area, NOT the entire viewport
 *  (top bar + FAB stay visible). z is excluded; caller preserves it.
 */
export function computeMaximizedGeometry(
  viewportWidth: number,
  viewportHeight: number
): { x: number; y: number; width: number; height: number } {
  // Match the constants used by the cascade origin in useSurfacePreferences
  // so cascade-positioned + maximized geometries play by the same rules.
  const horizPad = 16;
  const vertPadTop = 56 + 16; // top bar (~56px) + desktop padding (16px)
  const vertPadBottom = FAB_RESERVED_HEIGHT + 16; // FAB zone + padding
  return {
    x: horizPad,
    y: vertPadTop,
    width: Math.max(WINDOW_MIN_WIDTH, viewportWidth - horizPad * 2),
    height: Math.max(WINDOW_MIN_HEIGHT, viewportHeight - vertPadTop - vertPadBottom),
  };
}

/** Compute the default geometry for a newly-opened window. Cascades
 *  +CASCADE_OFFSET_PX from `cascadeAnchor`, wrapping back to top-left
 *  when the offset reaches the viewport edge. Clamps to viewport. */
export function computeDefaultWindowState(
  viewportWidth: number,
  viewportHeight: number,
  desktopPaddingPx: number,
  cascadeIndex: number
): WindowState {
  const usableWidth = Math.max(WINDOW_MIN_WIDTH, viewportWidth - desktopPaddingPx * 2);
  const usableHeight = Math.max(WINDOW_MIN_HEIGHT, viewportHeight - desktopPaddingPx * 2);
  const width = Math.max(WINDOW_MIN_WIDTH, Math.round(usableWidth * DEFAULT_WINDOW_WIDTH_PCT));
  const height = Math.max(WINDOW_MIN_HEIGHT, Math.round(usableHeight * DEFAULT_WINDOW_HEIGHT_PCT));

  // Cascade origin sits at the desktop-padding inset; offset by index,
  // wrapping when the offset would push the window off the desktop.
  const maxOffsetX = Math.max(0, usableWidth - width);
  const maxOffsetY = Math.max(0, usableHeight - height);
  const stride = CASCADE_OFFSET_PX;
  const xOffset = stride * cascadeIndex;
  const yOffset = stride * cascadeIndex;
  const wrappedX = maxOffsetX > 0 ? xOffset % (maxOffsetX + 1) : 0;
  const wrappedY = maxOffsetY > 0 ? yOffset % (maxOffsetY + 1) : 0;

  return {
    x: desktopPaddingPx + wrappedX,
    y: desktopPaddingPx + wrappedY,
    width,
    height,
    z: 0, // caller updates with max-z + 1
  };
}

/** Clamp a window's position so the title bar is at least partially
 *  visible (the operator can always grab the title bar). Clamps size
 *  to (WINDOW_MIN_*, viewport - 2*padding).
 *
 *  D17 (2026-05-22) — FAB reserved zone: when a window's horizontal
 *  extent overlaps the central FAB_RESERVED_WIDTH-wide column at the
 *  viewport's horizontal center, the window's bottom edge is pushed
 *  up so it doesn't cover the FAB. Windows that don't overlap the
 *  central column are unaffected. Guarantees the FAB stays reachable
 *  regardless of window arrangement. */
export function clampWindowState(
  state: WindowState,
  viewportWidth: number,
  viewportHeight: number,
  desktopPaddingPx: number,
  titleBarHeightPx: number = 32
): WindowState {
  const maxWidth = Math.max(WINDOW_MIN_WIDTH, viewportWidth - desktopPaddingPx * 2);
  const maxHeight = Math.max(WINDOW_MIN_HEIGHT, viewportHeight - desktopPaddingPx * 2);
  const width = Math.min(maxWidth, Math.max(WINDOW_MIN_WIDTH, state.width));
  const height = Math.min(maxHeight, Math.max(WINDOW_MIN_HEIGHT, state.height));

  // Position bounds: keep at least 80px of the title bar visible on
  // every edge so the operator can always grab it. y can't go above
  // the desktop padding (would hide the title bar entirely).
  const minVisible = 80;
  const minX = desktopPaddingPx - width + minVisible;
  const maxX = viewportWidth - desktopPaddingPx - minVisible;
  const minY = desktopPaddingPx;
  let maxY = viewportHeight - desktopPaddingPx - titleBarHeightPx;
  const x = Math.min(maxX, Math.max(minX, state.x));

  // D17 FAB reserved zone. Compute whether the window (at its
  // proposed x + width) overlaps the central column where the FAB
  // lives. If it does, tighten maxY by FAB_RESERVED_HEIGHT so the
  // window's bottom edge sits above the FAB. The horizontal slot
  // outside the central column is unaffected.
  const fabColLeft = (viewportWidth - FAB_RESERVED_WIDTH) / 2;
  const fabColRight = fabColLeft + FAB_RESERVED_WIDTH;
  const winLeft = x;
  const winRight = x + width;
  const overlapsFabColumn = winRight > fabColLeft && winLeft < fabColRight;
  if (overlapsFabColumn) {
    maxY = Math.max(minY, maxY - FAB_RESERVED_HEIGHT);
  }

  const y = Math.min(maxY, Math.max(minY, state.y));

  return { x, y, width, height, z: state.z };
}
