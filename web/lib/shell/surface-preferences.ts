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
 * Persisted to localStorage keyed by (workspace, user) — ADR-407 Phase 3:
 * one desktop per workspace binding per user, so switching workspaces never
 * carries stale window state across. localStorage is the LOCAL CACHE; the
 * server-backed member-state store (`PUT /api/member-state/shell`) is the
 * cross-device copy — useSurfacePreferences write-through-debounces the full
 * shell state there and hydrates a fresh device from it on mount. Backend
 * persistence is no longer deferred.
 *
 * Defaults:
 *   - keptSurfaces:        ['chat'] (ADR-435 — the Home surface was deleted;
 *                          `chat`, the steward's voice + the active operating
 *                          surface, is the default dock anchor. The retired
 *                          `channels`/`context`/`feed`/`home` alias slugs
 *                          normalize → `chat` on read.)
 *   - openSurfaces:        [] (first-time operators boot to desktop — D13)
 *   - foregroundedSurface: null (no surface foregrounded on first boot)
 */

import { ACTIVE_WORKSPACE_KEY } from '@/lib/api/client';

const KEPT_KEY_PREFIX = 'yarnnn:shell:kept-surfaces:';
const OPEN_KEY_PREFIX = 'yarnnn:shell:open-surfaces:';
const FOREGROUND_KEY_PREFIX = 'yarnnn:shell:foregrounded-surface:';
const WINDOW_STATE_KEY_PREFIX = 'yarnnn:shell:window-state:';

export const DEFAULT_KEPT_SURFACES: string[] = ['chat'];
export const DEFAULT_OPEN_SURFACES: string[] = [];
export const DEFAULT_FOREGROUNDED_SURFACE: string | null = null;

// D15 — window manager cap → ADR-369 follow-on (2026-06-25): this is a
// PERF ceiling on simultaneously-mounted windows, NOT a refusal threshold.
// Opening past it recedes the least-recently-used window (LRU auto-close in
// foregroundWindowGrade); navigation is never refused. 8 bounds the number of
// mounted surface React trees; with only ~10 window-grade surfaces today
// (most are panes-in-windows or chrome), it rarely binds — and when it does,
// it recedes silently rather than blocking a primary act (ADR-340 DP29).
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

// D19.5.1 (2026-05-22) — FAB_RESERVED_WIDTH + FAB_RESERVED_HEIGHT
// DELETED. The D17 FAB lived at the Desktop's bottom-CENTER below
// windows in the z-stack (z=5; windows start at z=10), requiring a
// reserved column to keep the FAB reachable when windows covered its
// position. D19.5.1 moves the FAB to viewport-fixed bottom-RIGHT at
// Z_FAB (150, above windows) — windows can extend across the full
// bottom edge and the FAB still floats above them. The reserved-zone
// concept dissolves; window clamping returns to a simple viewport-
// padded box. Singular Implementation — one window-clamping rule.

function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof localStorage !== 'undefined';
}

/**
 * ADR-407 Phase 3 — per-(workspace, user) key suffix. The active-workspace
 * binding (set on invite-accept; absent for owners) scopes shell state to the
 * workspace being operated, so switching workspaces never carries stale
 * window state across. `'owner'` is the literal for the unbound (owner-
 * default) case. The ONE place the suffix is formed — every localStorage key
 * in this file (and the attention read cursor) uses it.
 */
export function shellStateSuffix(userId: string): string {
  let workspaceKey = 'owner';
  if (isBrowser()) {
    try {
      workspaceKey = localStorage.getItem(ACTIVE_WORKSPACE_KEY) || 'owner';
    } catch {
      // storage unavailable — owner default applies
    }
  }
  return `${workspaceKey}:${userId}`;
}

function key(prefix: string, userId: string): string {
  return `${prefix}${shellStateSuffix(userId)}`;
}

// ----------------------------------------------------------------------------
// Legacy-slug normalization (ADR-385 follow-on, 2026-06-30)
// ----------------------------------------------------------------------------
//
// The `context` (ADR-385), `feed` (ADR-370), and `channels` (ADR-415) surface
// slugs were successively renamed/folded and finally DISSOLVED (ADR-415 — the
// Channels surface's content re-homed to Activity + Workspace Settings). The
// `home` surface itself was then DELETED (ADR-435 — the one composition in a
// registry of mirrors). All four were removed from the registry + slug union.
// But persisted dock state (kept / open / foregrounded, in localStorage) can
// still NAME them from before. Left as-is, a stale entry rendered a dead /
// duplicate dock icon.
//
// Normalize on READ: every retired alias collapses to `chat` (the ADR-435
// default dock anchor, deduped), so a returning operator's kept/open icon lands
// on Chat rather than a vanished surface. The canonical map; extend if a future
// rename retires another slug.
const LEGACY_SLUG_ALIASES: Record<string, string> = {
  context: 'chat',
  feed: 'chat',
  channels: 'chat',
  home: 'chat',
};

// Slugs retired from the DOCK (kept/open/foregrounded) but NOT deleted as
// surfaces — still URL-reachable + searchable. Unlike an alias (which remaps
// to a live slug), a retired slug is DROPPED from persisted dock lists so a
// stale pin stops rendering an icon.
//
// `agents` WAS here (2026-07-08 → 2026-07-16): the A3 roster was demoted to
// search-only (launch focus = the A2 chat lanes, the user's hands, not the
// user's hire — ADR-380 Rung-2 deferral / ADR-414), and that note said
// "re-surfacing A3 later = flip the tier back AND remove it from this set."
// REMOVED 2026-07-16 — the second half of that instruction, and the reason
// the tier flip alone would have half-worked (a primary surface silently
// dropped from every dock). Not the Rung-2 clock: hiring became the launch
// focus at Rung 1, and ADR-460 dissolved the A2/A3 ladder that made a roster
// "a second AI door". See docs/analysis/agents-surface-and-debt-2026-07-16.md.
//
// `system-agent` (ADR-454 D4, 2026-07-13): the ADR-426 door is reversed
// (hidden registry row + redirect stub) — a persisted dock entry naming it
// would render a dead icon (the ADR-385 ghost-icon lesson).
const DOCK_RETIRED_SLUGS = new Set<string>(['system-agent']);

function normalizeSlug(slug: string): string {
  return LEGACY_SLUG_ALIASES[slug] ?? slug;
}

/** Normalize + dedupe a persisted slug list (order-preserving), dropping any
 *  slug retired from the dock. */
function normalizeSlugList(slugs: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const s of slugs) {
    const n = normalizeSlug(s);
    if (DOCK_RETIRED_SLUGS.has(n)) continue; // dropped, not remapped
    if (!seen.has(n)) {
      seen.add(n);
      out.push(n);
    }
  }
  return out;
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
      // Normalize legacy alias slugs (context/feed → channels, deduped) so a
      // stale persisted dock entry doesn't render a duplicate icon.
      return normalizeSlugList(parsed);
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
      // Normalize legacy alias slugs (context/feed → channels, deduped).
      return normalizeSlugList(parsed);
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
    if (!raw) return DEFAULT_FOREGROUNDED_SURFACE;
    const n = normalizeSlug(raw);
    // A dock-retired slug (today: system-agent) that was the foregrounded
    // surface falls back to the default rather than landing the operator on a
    // de-emphasized surface at cold-load — it's still reachable by direct URL.
    // (Named `agents` until 2026-07-16, when that surface was re-surfaced.)
    if (DOCK_RETIRED_SLUGS.has(n)) return DEFAULT_FOREGROUNDED_SURFACE;
    // Normalize a stale legacy foregrounded slug (context/feed → channels).
    return n;
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

// ADR-404 step 5's `clearShellState` (wipe-on-invite-accept) was DELETED by
// ADR-407 Phase 3: shell state is now keyed per (workspace, user), so a new
// workspace binding reads fresh keys by construction — nothing stale to wipe.

/**
 * ADR-407 Phase 3 — the full shell state as one serializable snapshot: the
 * shape written through to `api.memberState.put('shell', …)` and hydrated
 * back on a fresh device.
 */
export interface ShellStateSnapshot {
  kept: string[];
  open: string[];
  foregrounded: string | null;
  windowState: WindowStateMap;
}

/**
 * ADR-407 Phase 3 — does ANY local shell state exist for the current
 * (workspace, user) suffix? Server hydration only fills a fresh device;
 * when local state exists, local wins (no merge).
 */
export function hasLocalShellState(userId: string): boolean {
  if (!isBrowser() || !userId) return false;
  for (const prefix of [
    KEPT_KEY_PREFIX,
    OPEN_KEY_PREFIX,
    FOREGROUND_KEY_PREFIX,
    WINDOW_STATE_KEY_PREFIX,
  ]) {
    try {
      if (localStorage.getItem(key(prefix, userId)) != null) return true;
    } catch {
      // ignore — private-browsing etc.
    }
  }
  return false;
}

/** ADR-407 Phase 3 — write a server snapshot into localStorage (fresh-device
 *  hydration). Callers re-read via the getters so slug normalization applies. */
export function hydrateShellState(userId: string, snapshot: ShellStateSnapshot): void {
  if (!isBrowser() || !userId) return;
  setKeptSurfaces(userId, snapshot.kept);
  setOpenSurfaces(userId, snapshot.open);
  setForegroundedSurface(userId, snapshot.foregrounded);
  setWindowStates(userId, snapshot.windowState);
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
  /**
   * D19.3 (2026-05-22) — macOS-style minimize. When true, the window
   * is "sent to the Dock": the WindowFrame is NOT rendered, but the
   * slug stays in `open` so the Dock icon remains as an open-indicator.
   * Clicking the Dock icon clears this flag and restores the window.
   * Geometry is preserved across minimize/restore via the rest of the
   * fields. When undefined or false, the window is normally rendered.
   */
  minimized?: boolean;
  /**
   * 2026-06-25 — the window's remembered deep-link params (bare keys, e.g.
   * `{pane: 'account'}`, `{tab: 'alpha-trader'}`). The URL shows ONLY the
   * foregrounded surface's params (an honest address bar — you-are-here), so a
   * backgrounded window's pane/tab can't live in the URL; it's persisted here
   * and re-applied to the URL when the window is re-foregrounded. Written by
   * setSurfaceParams + the foreground param-delivery sites; read by
   * reconcileUrlToForeground. Empty/absent → the window opens at its default.
   */
  params?: Record<string, string>;
}

export type WindowStateMap = Record<string, WindowState>;

// ----------------------------------------------------------------------------
// Window-param normalization (2026-07-16)
// ----------------------------------------------------------------------------
//
// The slug-normalization above (LEGACY_SLUG_ALIASES / DOCK_RETIRED_SLUGS) has a
// twin gap: WindowState.params is a free-form Record<string,string> that is
// never checked against the keys its surface actually reads. reconcileUrl
// re-applies the remembered params to the URL VERBATIM on every foreground, so
// a param key written under an old topology outlives it forever.
//
// The observed bug: `?agents.pane=autonomy`. `autonomy` was `pane_of: agents`
// until 2026-07-06 (ADR-412 D5 re-homed it to workspace-settings, then ADR-426
// → system-agent, then ADR-454 D4 → back to workspace-settings). A member who
// opened that pane before the first move has `{pane:'autonomy'}` persisted on
// the agents window. AgentsSurface never reads `pane` — its only depth is
// `?agents.agent={slug}` — so the param is INERT, but it is replayed into the
// address bar on every foreground. The URL claims a depth the surface has no
// concept of, which is exactly the dishonest-address-bar class reconcileUrl was
// written to end.
//
// Declare the param keys each surface OWNS. A key not listed is dropped on read.
// This is an allowlist, not an alias map: a stale param has no live equivalent
// to remap to (unlike a renamed slug, which still names a real surface).
// Surfaces absent from this map are unconstrained — only surfaces whose param
// vocabulary is settled need pinning down, and a wrong entry here would silently
// eat live deep-links.
const SURFACE_PARAM_KEYS: Record<string, readonly string[]> = {
  // ADR-167 list/detail: `?agents.agent={slug}`. There are no panes here.
  agents: ['agent'],
};

/** Drop persisted param keys a surface doesn't own (see SURFACE_PARAM_KEYS). */
export function normalizeWindowParams(
  slug: string,
  params: Record<string, string> | undefined
): Record<string, string> | undefined {
  if (!params) return params;
  const allowed = SURFACE_PARAM_KEYS[slug];
  if (!allowed) return params; // unconstrained surface — leave as-is
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(params)) {
    if (allowed.includes(k)) out[k] = v;
  }
  return out;
}

export function getWindowStates(userId: string): WindowStateMap {
  if (!isBrowser() || !userId) return {};
  try {
    const raw = localStorage.getItem(key(WINDOW_STATE_KEY_PREFIX, userId));
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      const states = parsed as WindowStateMap;
      // Strip stale param keys on READ, mirroring normalizeSlugList — the same
      // boundary, for the same reason: persisted shell state can name a topology
      // that no longer exists.
      for (const [slug, state] of Object.entries(states)) {
        if (state?.params) {
          states[slug] = { ...state, params: normalizeWindowParams(slug, state.params) };
        }
      }
      return states;
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
 *  available desktop area inside the Desktop layer. macOS "zoom"
 *  target — fills the work area, NOT the entire viewport.
 *
 *  D19.3 (2026-05-22) — geometry frame correction: windows are
 *  absolute-positioned inside the Desktop component (which is the
 *  nearest positioned ancestor); Desktop itself is below the TopBar
 *  in the flex column. The pre-D19.3 calculation double-counted the
 *  TopBar height (56px) on top of Desktop padding, producing a
 *  visible gap between the maximized window's top edge and the
 *  TopBar's bottom. The correct vertical offset is just the
 *  Desktop's own padding (16px on sm:p-4); the TopBar's height is
 *  already handled by the flex layout above Desktop.
 *
 *  D19.5.1 (2026-05-22) — FAB reserved zone DELETED. The FAB moved
 *  from Desktop-fixed bottom-center (z=5, below windows) to viewport-
 *  fixed bottom-right (Z_FAB=150, above windows). Maximized windows
 *  can now extend across the full Desktop bottom edge; the FAB still
 *  floats above. Bottom inset is now just Desktop padding.
 */
export function computeMaximizedGeometry(
  viewportWidth: number,
  viewportHeight: number
): { x: number; y: number; width: number; height: number } {
  const TOP_BAR_PX = 56;       // outside Desktop's coordinate frame
  const usableHeight = Math.max(WINDOW_MIN_HEIGHT, viewportHeight - TOP_BAR_PX);
  return computeMaximizedGeometryFromBounds(viewportWidth, usableHeight);
}

/**
 * ADR-316: maximize geometry from the DESKTOP's own measured box
 * (already excludes the top-bar and the command rail — the Desktop is
 * the flex-1 sibling of the rail, below the top-bar). The input is the
 * usable Desktop area; this only insets the Desktop's own padding. The
 * viewport-based computeMaximizedGeometry above delegates here after
 * subtracting the top-bar, so both share one inset rule.
 */
export function computeMaximizedGeometryFromBounds(
  desktopWidth: number,
  desktopHeight: number
): { x: number; y: number; width: number; height: number } {
  const DESKTOP_PAD = 16;      // sm:p-4 — Desktop's own padding
  return {
    x: DESKTOP_PAD,
    y: DESKTOP_PAD,
    width: Math.max(WINDOW_MIN_WIDTH, desktopWidth - DESKTOP_PAD * 2),
    height: Math.max(WINDOW_MIN_HEIGHT, desktopHeight - DESKTOP_PAD * 2),
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
 *  D19.5.1 (2026-05-22) — pre-D19.5.1 the clamp tightened maxY by
 *  FAB_RESERVED_HEIGHT when a window's horizontal extent overlapped
 *  the central FAB column (kept the FAB reachable when it lived at
 *  z=5 below windows). With the D19.5.1 FAB move (viewport-fixed
 *  bottom-right at Z_FAB=150, above windows), windows can extend
 *  fully across the bottom edge and the FAB still floats above —
 *  the overlap check + tightened maxY are now dead logic. Deleted.
 *  Singular Implementation — one clamp rule, no FAB special case. */
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
  const maxY = viewportHeight - desktopPaddingPx - titleBarHeightPx;
  const x = Math.min(maxX, Math.max(minX, state.x));
  const y = Math.min(maxY, Math.max(minY, state.y));

  return { x, y, width, height, z: state.z };
}
