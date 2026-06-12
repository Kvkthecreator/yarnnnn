'use client';

/**
 * Surface preferences — ADR-297 D5 + D6 + D13 + D14 + D14.1.
 *
 * Context-backed source of truth for operator surface preferences:
 *   - kept         — Dock-permanence surfaces (D14)
 *   - open         — currently-open surface slugs (D13)
 *   - foregrounded — the open slug currently visible in main (D13)
 *
 * D14.1 (2026-05-22) moved the implementation from a per-call useState
 * to a single Provider-backed Context. Pre-D14.1 each consumer of
 * useSurfacePreferences held its own copy of (kept, open, foregrounded)
 * in local useState — so when TopBarSurface and SurfaceViewport both
 * mounted, they had independent registries, and a write through one
 * (e.g. AuthenticatedLayout's pathname watcher calling
 * foregroundSurface) didn't propagate to the others. The Dock failed to
 * show open-but-not-kept surfaces because TopBarSurface's `open` slice
 * was always its own stale [].
 *
 * D14.1 fixes that by making one Provider near the top of the tree
 * (AuthenticatedLayout) hold the canonical state; every useSurfacePreferences
 * call reads from + writes through the same context value.
 *
 * D14 reframed pin → keep. D13 introduced multi-mount lifecycle. See
 * ADR-297 §D13, §D14, §D14.1.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { useComposition } from '@/lib/compositor/useComposition';
import {
  DEFAULT_FOREGROUNDED_SURFACE,
  DEFAULT_KEPT_SURFACES,
  DEFAULT_OPEN_SURFACES,
  MAX_OPEN_WINDOWS,
  closeSurface as closeSurfaceWrite,
  computeDefaultWindowState,
  computeMaximizedGeometry,
  computeMaximizedGeometryFromBounds,
  getForegroundedSurface,
  getKeptSurfaces,
  getOpenSurfaces,
  getWindowStates,
  keepSurface as keepSurfaceWrite,
  openSurface as openSurfaceWrite,
  releaseSurface as releaseSurfaceWrite,
  setForegroundedSurface as setForegroundedWrite,
  setKeptSurfaces as setKeptWrite,
  setWindowStates,
  type WindowState,
  type WindowStateMap,
} from './surface-preferences';
import { WINDOW_Z_MAX } from './z-tiers';

export interface SurfacePreferences {
  userId: string | null;
  /** Dock-permanence surfaces (D14). The macOS "Keep in Dock" semantic. */
  kept: string[];
  /** Currently-open surfaces (D13). */
  open: string[];
  /** The slug currently visible / raised-to-top in main; null = desktop. */
  foregrounded: string | null;
  /** Per-slug window geometry + z-order (D15). */
  windowStates: WindowStateMap;
  keep: (slug: string) => void;
  release: (slug: string) => void;
  reorder: (slugs: string[]) => void;
  openSurface: (slug: string) => void;
  closeSurface: (slug: string) => void;
  /**
   * Bring an open surface to the foreground. If not yet open, also
   * open it. If the soft cap (MAX_OPEN_WINDOWS) is reached when
   * opening, returns false and surfaces the cap-hit signal via
   * `capHit` below — caller decides UX (prompt operator to close one).
   * Returns true on success.
   */
  foregroundSurface: (slug: string) => boolean;
  /**
   * ADR-297 D19.5 (navigation enactment, 2026-05-30): the SINGLE
   * sanctioned cross-surface navigation verb. Components MUST use this
   * instead of `router.push('/{slug}')` — the compositor (window
   * manager) owns navigation; the browser router is transport, not
   * control (ADR-222: compositor IS the window manager).
   *
   * Behaviour:
   *   - bare slug: foregroundSurface(slug). URL stays as-is per D19.2
   *     (the Dock indicator dot is the canonical "what's foregrounded"
   *     signal, not the URL).
   *   - with params: foregroundSurface(slug) AND write the URL
   *     (`/{route}?k=v`). Required because atomic surfaces read their
   *     deep-link state from `useSearchParams()` (cadence reads
   *     `?task=`, agents reads `?agent=`), NOT from window-manager
   *     state — so the param only reaches the target window via the URL.
   *
   * Returns foregroundSurface's boolean (false if the open soft-cap was
   * hit — caller consumes `capHit` for UX).
   */
  navigateToSurface: (slug: string, params?: Record<string, string>) => boolean;
  /**
   * ADR-297 D19.6 (2026-06-12): the sanctioned INTRA-surface deep-link
   * verb. Updates the foregrounded surface's URL params (`?agent=X`,
   * `?task=Y`, `?slug=Z`) WITHOUT a pathname flip — the window-manager
   * baseline (pathname `/desktop`) is preserved.
   *
   * Distinct from `navigateToSurface` (cross-surface): that verb flips
   * pathname to the target surface route (correct when you genuinely
   * move surfaces). `setSurfaceParams` is for "I'm already in this
   * surface, change which entity it shows" — switching agents in the
   * Agents window, selecting a recurrence in the Recurrence window. A
   * pathname flip there is the disruption: it trips the pathname→
   * foreground effect + SurfaceViewport pathnameSlug resolution +
   * closeSurface URL-sync, all of which branch on whether pathname is
   * the `/desktop` baseline (operator-observed KVK 2026-06-12).
   *
   * Mechanism: `window.history.replaceState(null, '', <current-pathname>?<params>)`.
   * Next 14.2 natively patches replaceState (app-router.js) so the Next
   * router syncs — `useSearchParams()` re-renders with the new param —
   * but NO navigation event fires, so the shell effects stay quiet.
   * Surfaces keep reading `useSearchParams()` as their single source of
   * truth (no parallel component state; Singular Implementation).
   *
   * Pass a param value of `null` (or '') to DELETE that key (e.g.
   * back-to-list clears `?task=`). Keys not mentioned are preserved.
   * No-op on the server (guards `typeof window`).
   */
  setSurfaceParams: (params: Record<string, string | null>) => void;
  isKept: (slug: string) => boolean;
  isOpen: (slug: string) => boolean;
  /** D15: update a single window's geometry (called from drag + resize). */
  setWindowState: (slug: string, state: WindowState) => void;
  /** D15: raise a window to the top of the z-stack (foreground it
   *  without re-positioning). Updates foregrounded + bumps z. */
  raiseWindow: (slug: string) => void;
  /** D19.1 (2026-05-22): toggle macOS-style zoom for a window. If the
   *  window is currently zoomed (windowStates[slug].prevGeometry is
   *  defined), restore the prior geometry and clear prevGeometry.
   *  Otherwise save the current geometry into prevGeometry and snap
   *  to computeMaximizedGeometry(viewport). Raises the window (zoom
   *  is a focus gesture). No-op if the window has no entry in
   *  windowStates (e.g. in single-window mobile mode). */
  toggleMaximize: (slug: string) => void;
  /** D19.3 (2026-05-22): macOS-style minimize. Sets
   *  windowStates[slug].minimized = true; SurfaceViewport then
   *  skips rendering the WindowFrame. Slug stays in `open` so the
   *  Dock icon persists as an open-indicator. Foreground falls
   *  through to the next-non-minimized open slug; if none, foreground
   *  becomes null (Desktop is visible). Restore by calling
   *  foregroundSurface(slug) — typically via Dock-icon click.
   *  Replaces the D15 hideForegrounded verb (deleted in D19.3
   *  because its silent no-op-on-last-window semantic was the
   *  root cause of "minimize doesn't work" + Dock-click-on-only-
   *  app-does-nothing). */
  minimizeWindow: (slug: string) => void;
  /** D15: viewport-cap signal — when foregroundSurface refuses to
   *  open a new window because MAX_OPEN_WINDOWS is reached, this
   *  carries the attempted slug. Operator UX consumes it to prompt
   *  "Close another to open this." Caller clears via clearCapHit. */
  capHit: string | null;
  clearCapHit: () => void;
  /**
   * ADR-316: the Desktop container's measured inner bounds. Window
   * geometry (cascade origin, maximize snap, drag-clamp) is relative to
   * the DESKTOP, not the raw viewport — because the command rail
   * (chat) and any future docked chrome reduce the Desktop's width.
   * The Desktop component reports its bounds here via a ResizeObserver;
   * the geometry math reads from here instead of `window.innerWidth`.
   * Null until the Desktop mounts + measures (geometry falls back to
   * window dims until then). */
  desktopBounds: { width: number; height: number } | null;
  setDesktopBounds: (width: number, height: number) => void;
}

const Ctx = createContext<SurfacePreferences | null>(null);

export function SurfacePreferencesProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { data: composition } = useComposition();
  const [userId, setUserId] = useState<string | null>(null);
  const [kept, setKept] = useState<string[]>(DEFAULT_KEPT_SURFACES);
  const [open, setOpen] = useState<string[]>(DEFAULT_OPEN_SURFACES);
  const [foregrounded, setForegrounded] = useState<string | null>(
    DEFAULT_FOREGROUNDED_SURFACE
  );
  // D15 — window manager state.
  const [windowStates, setWindowStatesState] = useState<WindowStateMap>({});
  const [capHit, setCapHit] = useState<string | null>(null);
  // ADR-316: Desktop-measured bounds (see interface docstring). Held in
  // a ref so geometry callbacks read the latest value without being
  // re-created on every Desktop resize (which would thrash window
  // callbacks). A state mirror is also exposed for consumers that need
  // to re-render on bounds change.
  const desktopBoundsRef = useRef<{ width: number; height: number } | null>(null);
  const [desktopBounds, setDesktopBoundsState] = useState<{ width: number; height: number } | null>(null);
  const setDesktopBounds = useCallback((width: number, height: number) => {
    const prev = desktopBoundsRef.current;
    if (prev && prev.width === width && prev.height === height) return;
    desktopBoundsRef.current = { width, height };
    setDesktopBoundsState({ width, height });
  }, []);
  // Monotonic cascade counter — increments per newly-opened window
  // without prior state. Used to compute cascade x/y offset.
  const cascadeCounter = useRef(0);

  useEffect(() => {
    let mounted = true;
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      if (!mounted) return;
      const uid = data.user?.id ?? null;
      setUserId(uid);
      if (uid) {
        setKept(getKeptSurfaces(uid));
        setOpen(getOpenSurfaces(uid));
        setForegrounded(getForegroundedSurface(uid));
        setWindowStatesState(getWindowStates(uid));
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  // Persist window-state changes to localStorage.
  const persistWindowStates = useCallback(
    (next: WindowStateMap) => {
      if (!userId) return;
      setWindowStates(userId, next);
    },
    [userId]
  );

  // Compute the highest z across all open windows + 1 (raises to top).
  // D18: capped at WINDOW_Z_MAX. Caller responsible for compaction
  // when the value reaches cap (see compactWindowZ).
  const computeNextZ = useCallback((states: WindowStateMap, openSlugs: string[]): number => {
    let maxZ = 0;
    openSlugs.forEach((slug) => {
      const s = states[slug];
      if (s && s.z > maxZ) maxZ = s.z;
    });
    return Math.min(WINDOW_Z_MAX, maxZ + 1);
  }, []);

  // D18: re-rank all open windows' z values from 1..N preserving their
  // current relative order. Called when computeNextZ would return
  // WINDOW_Z_MAX — prevents permanent stuck-at-cap drift across all
  // windows. Returns a new WindowStateMap with compacted z values.
  const compactWindowZ = useCallback(
    (states: WindowStateMap, openSlugs: string[]): WindowStateMap => {
      // Sort open slugs by current z (ascending); preserves relative
      // ordering. Slugs that exist in `states` but not in `openSlugs`
      // (rare; cleanup hole) keep their values untouched.
      const sortable = openSlugs
        .filter((s) => states[s])
        .map((s) => ({ slug: s, z: states[s].z }))
        .sort((a, b) => a.z - b.z);
      const next: WindowStateMap = { ...states };
      sortable.forEach((entry, i) => {
        next[entry.slug] = { ...states[entry.slug], z: i + 1 };
      });
      return next;
    },
    []
  );

  const keep = useCallback(
    (slug: string) => {
      if (!userId) return;
      const next = keepSurfaceWrite(userId, slug);
      setKept(next);
    },
    [userId]
  );

  const release = useCallback(
    (slug: string) => {
      if (!userId) return;
      const next = releaseSurfaceWrite(userId, slug);
      setKept(next);
    },
    [userId]
  );

  const reorder = useCallback(
    (slugs: string[]) => {
      if (!userId) return;
      setKeptWrite(userId, slugs);
      setKept(slugs);
    },
    [userId]
  );

  const doOpenSurface = useCallback(
    (slug: string) => {
      if (!userId) return;
      const next = openSurfaceWrite(userId, slug);
      setOpen(next);
    },
    [userId]
  );

  const doCloseSurface = useCallback(
    (slug: string) => {
      if (!userId) return;
      const next = closeSurfaceWrite(userId, slug);
      setOpen(next);
      // If we just closed the foregrounded surface, foreground falls
      // through to the tail of the remaining list (most-recently-
      // opened), or null if nothing left.
      //
      // D18.2 (2026-05-22) — URL-sync race fix: the foregrounded close
      // must also navigate the URL synchronously to either the fallback
      // surface's route OR /desktop. Pre-fix, closing the foregrounded
      // window left pathname stale (e.g. /feed) while the registry
      // emptied; AuthenticatedLayout's pathname→foreground effect
      // (Effect A) then re-fired because `foregroundSurface`'s callback
      // identity changes when `open` changes, instantly re-opening the
      // just-closed surface. Operator could not close the topmost
      // window — the empty Desktop was structurally unreachable
      // (operator-observed KVK 2026-05-22). Doing the navigate here
      // means the pathname is updated in the same React batch as the
      // close, so Effect A's pathname check finds either /desktop or
      // the fallback route on its next run — no resurrection.
      //
      // Only navigate when the current pathname matches a kernel
      // surface route. Legacy non-atomic routes (/settings, /docs/...)
      // close their attached surface without touching the URL.
      setForegrounded((current) => {
        if (current !== slug) return current;
        const fallback = next.length > 0 ? next[next.length - 1] : null;
        setForegroundedWrite(userId, fallback);

        // URL-sync. Only fires when current pathname IS a surface route
        // (the case where the stale URL would otherwise resurrect the
        // closed surface via Effect A in AuthenticatedLayout).
        const surfaces = composition.surfaces || [];
        const pathnameIsSurfaceRoute = surfaces.some(
          (s) =>
            s.route &&
            (pathname === s.route || pathname.startsWith(s.route + '/')),
        );
        if (pathnameIsSurfaceRoute) {
          if (fallback) {
            const fallbackSurface = surfaces.find((s) => s.slug === fallback);
            const target = fallbackSurface?.route || '/desktop';
            if (pathname !== target) router.push(target);
          } else {
            if (pathname !== '/desktop') router.push('/desktop');
          }
        }

        return fallback;
      });
    },
    [userId, composition.surfaces, pathname, router]
  );

  // Window-grade open/raise/restore (the pre-ADR-340 foregroundSurface
  // body). Internal — call sites use foregroundSurface, which resolves
  // pane-grade slugs to their parent before delegating here.
  const foregroundWindowGrade = useCallback(
    (slug: string): boolean => {
      if (!userId) return false;
      const alreadyOpen = open.includes(slug);

      // D15 soft cap: only enforced when opening a NEW surface (not
      // when re-foregrounding an already-open one).
      if (!alreadyOpen && open.length >= MAX_OPEN_WINDOWS) {
        setCapHit(slug);
        return false;
      }

      const nextOpen = openSurfaceWrite(userId, slug);
      setOpen(nextOpen);
      setForegroundedWrite(userId, slug);
      setForegrounded(slug);

      // D15: ensure window has a state entry; cascade-position if new.
      // Always bump z so the foregrounded window sits on top.
      // D18: when z reaches WINDOW_Z_MAX, compact first so the new z
      // sits cleanly above the (compacted) set without overflow.
      setWindowStatesState((current) => {
        let base: WindowStateMap = { ...current };
        let newZ = computeNextZ(base, nextOpen);
        if (newZ >= WINDOW_Z_MAX) {
          base = compactWindowZ(base, nextOpen);
          newZ = computeNextZ(base, nextOpen);
        }
        const next: WindowStateMap = base;
        if (!next[slug]) {
          // Cascade-position a brand-new window. D19.3 (2026-05-22)
          // geometry frame correction: windows are absolute-positioned
          // inside the Desktop component (the nearest positioned
          // ancestor), which is itself below the TopBar in the flex
          // column. Coordinates are Desktop-local, NOT viewport-local —
          // the TopBar offset must NOT be in the y origin (it was
          // double-counted pre-D19.3, producing a gap between window
          // top edges and the TopBar bottom most visible on maximize).
          // D19.5.1 (2026-05-22) — FAB_BOTTOM_RESERVED constant
          // DELETED. Pre-D19.5.1 the FAB lived at Desktop-fixed
          // bottom-center below windows; cascade reserved bottom
          // space to keep the FAB visible. With FAB moved to
          // viewport-fixed bottom-right above windows (Z_FAB=150),
          // the cascade origin returns to a simple viewport-padded
          // box. Singular Implementation.
          // ADR-316: prefer the Desktop-measured bounds (already excludes
          // the top-bar AND the command rail, since the Desktop is the
          // flex-1 sibling of the rail). Fall back to window dims minus
          // chrome only before the Desktop has measured.
          const bounds = desktopBoundsRef.current;
          const DESKTOP_PAD = 16;
          let usableW: number;
          let usableH: number;
          if (bounds) {
            usableW = bounds.width - DESKTOP_PAD * 2;
            usableH = bounds.height - DESKTOP_PAD * 2;
          } else {
            const vw = typeof window !== 'undefined' ? window.innerWidth : 1280;
            const vh = typeof window !== 'undefined' ? window.innerHeight : 800;
            const TOP_BAR_PX = 56;
            usableW = vw - DESKTOP_PAD * 2;
            usableH = vh - TOP_BAR_PX - DESKTOP_PAD * 2;
          }
          const cascadeIndex = cascadeCounter.current++;
          const computed = computeDefaultWindowState(
            usableW,
            usableH,
            0,
            cascadeIndex
          );
          next[slug] = {
            x: DESKTOP_PAD + computed.x,
            y: DESKTOP_PAD + computed.y,
            width: computed.width,
            height: computed.height,
            z: newZ,
          };
        } else {
          // D19.3 (2026-05-22): clearing `minimized` is the macOS
          // restore-from-Dock gesture — clicking a minimized app's
          // Dock icon un-hides + raises the window. foregroundSurface
          // is the unified "open + raise + restore-if-minimized" verb.
          next[slug] = { ...next[slug], z: newZ, minimized: false };
        }
        persistWindowStates(next);
        return next;
      });

      return true;
    },
    [userId, open, computeNextZ, compactWindowZ, persistWindowStates]
  );

  // ADR-340 P2 — pane-grade resolution wrapper. A surface carrying
  // `pane_of` is not window-grade: foreground its PARENT window and
  // deliver the pane selection via the parent's route + `?pane=` param
  // (atomic surfaces read deep-link state from useSearchParams, so the
  // param must reach the URL — the same Effect-A transport
  // navigateToSurface uses). Call sites stay pane-blind:
  // foregroundSurface('budget') just works whether budget is a window
  // or a pane of System Settings.
  const foregroundSurface = useCallback(
    (slug: string): boolean => {
      const surfaces = composition.surfaces || [];
      const entry = surfaces.find((s) => s.slug === slug);
      const parentSlug = entry?.pane_of;
      if (parentSlug && parentSlug !== slug) {
        const parent = surfaces.find((s) => s.slug === parentSlug);
        const parentRoute = parent?.route || `/${parentSlug}`;
        const ok = foregroundWindowGrade(parentSlug);
        if (ok) router.push(`${parentRoute}?pane=${slug}`);
        return ok;
      }
      return foregroundWindowGrade(slug);
    },
    [composition.surfaces, foregroundWindowGrade, router]
  );

  // ADR-297 D19.5 (navigation enactment, 2026-05-30): the single
  // sanctioned cross-surface navigation verb. Wraps foregroundSurface;
  // adds URL-param transport when params are present (atomic surfaces
  // read deep-link state from useSearchParams, so params must reach
  // the URL to land in the target window). See interface docstring.
  const navigateToSurface = useCallback(
    (slug: string, params?: Record<string, string>): boolean => {
      const ok = foregroundSurface(slug);
      // Only write the URL when there are params to deliver. Bare
      // navigation leaves the URL as-is per D19.2 (Dock dot is the
      // canonical foreground signal, not the URL).
      if (ok && params && Object.keys(params).length > 0) {
        const surfaces = composition.surfaces || [];
        const target = surfaces.find((s) => s.slug === slug);
        const route = target?.route || `/${slug}`;
        const sp = new URLSearchParams();
        Object.entries(params).forEach(([k, v]) => {
          if (v != null && v !== '') sp.set(k, v);
        });
        const qs = sp.toString();
        router.push(qs ? `${route}?${qs}` : route);
      }
      return ok;
    },
    [foregroundSurface, composition.surfaces, router]
  );

  // ADR-297 D19.6 (2026-06-12): intra-surface deep-link update with NO
  // pathname flip. See interface docstring. Uses the native History API
  // (Next 14.2 patches replaceState → router syncs useSearchParams,
  // no navigation event) to keep the window-manager pathname baseline.
  const setSurfaceParams = useCallback(
    (params: Record<string, string | null>): void => {
      if (typeof window === 'undefined') return;
      const url = new URL(window.location.href);
      Object.entries(params).forEach(([k, v]) => {
        if (v == null || v === '') url.searchParams.delete(k);
        else url.searchParams.set(k, v);
      });
      // Preserve current pathname; only the query changes. replaceState
      // (not pushState) — switching the shown entity is not a new history
      // entry the operator should Back-button through.
      window.history.replaceState(
        null,
        '',
        url.pathname + (url.search ? url.search : '') + url.hash
      );
    },
    []
  );

  // D19.1: toggle macOS-style zoom for a window. Saves prior geometry
  // on the way up; restores it on the way down. Raises the window
  // (zoom is a focus gesture).
  const toggleMaximize = useCallback(
    (slug: string) => {
      if (!userId) return;
      if (!open.includes(slug)) return;
      setWindowStatesState((current) => {
        const existing = current[slug];
        if (!existing) return current;
        const isZoomed = existing.prevGeometry != null;
        let next: WindowState;
        if (isZoomed && existing.prevGeometry) {
          // Restore. Clear prevGeometry; keep z.
          next = {
            x: existing.prevGeometry.x,
            y: existing.prevGeometry.y,
            width: existing.prevGeometry.width,
            height: existing.prevGeometry.height,
            z: existing.z,
          };
        } else {
          // Zoom. Save current geometry into prevGeometry, snap to max.
          // ADR-316: maximize snaps to the DESKTOP bounds (already
          // exclude the top-bar AND the command rail) when measured, so a
          // zoomed window fills the surface area beside the rail, never
          // under it. Falls back to the viewport-based helper pre-measure.
          const bounds = desktopBoundsRef.current;
          const max = bounds
            ? computeMaximizedGeometryFromBounds(bounds.width, bounds.height)
            : computeMaximizedGeometry(
                typeof window !== 'undefined' ? window.innerWidth : 1280,
                typeof window !== 'undefined' ? window.innerHeight : 800,
              );
          next = {
            x: max.x,
            y: max.y,
            width: max.width,
            height: max.height,
            z: existing.z,
            prevGeometry: {
              x: existing.x,
              y: existing.y,
              width: existing.width,
              height: existing.height,
            },
          };
        }
        const updated: WindowStateMap = { ...current, [slug]: next };
        persistWindowStates(updated);
        return updated;
      });
      // Raise to foreground — zoom is a focus gesture.
      setForegroundedWrite(userId, slug);
      setForegrounded(slug);
    },
    [userId, open, persistWindowStates]
  );

  // D19.3 (2026-05-22) — macOS-style minimize. Sets minimized=true on
  // the window's state; SurfaceViewport skips rendering when this flag
  // is set. Slug stays in `open` (Dock keeps showing the open-indicator
  // dot). Foreground falls through to the next-non-minimized open
  // slug, or null if nothing remains visible (Desktop shows through).
  const minimizeWindow = useCallback(
    (slug: string) => {
      if (!userId) return;
      if (!open.includes(slug)) return;
      setWindowStatesState((current) => {
        const existing = current[slug];
        if (!existing) return current;
        const updated: WindowStateMap = {
          ...current,
          [slug]: { ...existing, minimized: true },
        };
        persistWindowStates(updated);
        return updated;
      });
      // Foreground falls through to next non-minimized open window.
      setForegrounded((currentForeground) => {
        if (currentForeground !== slug) return currentForeground;
        // Pick next-highest-z open window that isn't itself minimized.
        const candidates = open.filter((s) => s !== slug);
        let nextSlug: string | null = null;
        let maxZ = -Infinity;
        candidates.forEach((s) => {
          const st = windowStates[s];
          if (!st || st.minimized) return;
          if (st.z > maxZ) {
            maxZ = st.z;
            nextSlug = s;
          }
        });
        setForegroundedWrite(userId, nextSlug);
        return nextSlug;
      });
    },
    [userId, open, windowStates, persistWindowStates]
  );

  // D15: raise an already-open window to the foreground without
  // re-cascading. Bumps z; updates foregrounded slug. D18: compact
  // before bumping if z would hit cap.
  const raiseWindow = useCallback(
    (slug: string) => {
      if (!userId) return;
      if (!open.includes(slug)) return;
      setForegroundedWrite(userId, slug);
      setForegrounded(slug);
      setWindowStatesState((current) => {
        let base = current;
        let newZ = computeNextZ(base, open);
        if (newZ >= WINDOW_Z_MAX) {
          base = compactWindowZ(base, open);
          newZ = computeNextZ(base, open);
        }
        const next: WindowStateMap = { ...base };
        const existing = next[slug] ?? null;
        if (existing) {
          next[slug] = { ...existing, z: newZ };
          persistWindowStates(next);
          return next;
        }
        return current;
      });
    },
    [userId, open, computeNextZ, compactWindowZ, persistWindowStates]
  );

  // D19.3 (2026-05-22): the prior hideForegrounded verb was DELETED.
  // It was a "send foregrounded window to background, fall through to
  // next" semantic from D15 that no-op'd silently when there was only
  // one open window. That silent no-op was the root cause of two
  // operator-felt bugs: the minimize yellow button "doesn't work at
  // all" on the only window, and the Dock-click-on-active-app gesture
  // doing nothing when there was nothing to fall through to.
  // Replaced by minimizeWindow(slug) which always works (sets
  // minimized:true; SurfaceViewport then skips rendering this slug).
  // Singular Implementation: one minimize verb.

  // D15: update a single window's geometry (called from drag + resize).
  const updateWindowState = useCallback(
    (slug: string, state: WindowState) => {
      setWindowStatesState((current) => {
        const next: WindowStateMap = { ...current, [slug]: state };
        persistWindowStates(next);
        return next;
      });
    },
    [persistWindowStates]
  );

  const clearCapHit = useCallback(() => setCapHit(null), []);

  const isKept = useCallback((slug: string) => kept.includes(slug), [kept]);
  const isOpen = useCallback((slug: string) => open.includes(slug), [open]);

  const value = useMemo<SurfacePreferences>(
    () => ({
      userId,
      kept,
      open,
      foregrounded,
      windowStates,
      keep,
      release,
      reorder,
      openSurface: doOpenSurface,
      closeSurface: doCloseSurface,
      foregroundSurface,
      navigateToSurface,
      setSurfaceParams,
      isKept,
      isOpen,
      setWindowState: updateWindowState,
      raiseWindow,
      toggleMaximize,
      minimizeWindow,
      capHit,
      clearCapHit,
      desktopBounds,
      setDesktopBounds,
    }),
    [
      userId,
      kept,
      open,
      foregrounded,
      windowStates,
      keep,
      release,
      reorder,
      doOpenSurface,
      doCloseSurface,
      foregroundSurface,
      navigateToSurface,
      setSurfaceParams,
      isKept,
      isOpen,
      updateWindowState,
      raiseWindow,
      toggleMaximize,
      minimizeWindow,
      capHit,
      clearCapHit,
      desktopBounds,
      setDesktopBounds,
    ]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSurfacePreferences(): SurfacePreferences {
  const ctx = useContext(Ctx);
  if (!ctx) {
    throw new Error(
      'useSurfacePreferences must be used inside <SurfacePreferencesProvider> ' +
        '(AuthenticatedLayout mounts the provider per ADR-297 D14.1)'
    );
  }
  return ctx;
}
