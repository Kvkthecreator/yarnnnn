'use client';

/**
 * WindowCrumbContext — per-window locator state for the OS-desktop shell.
 *
 * REPLACES the pre-ADR-297 global single-segment BreadcrumbContext. That
 * model assumed ONE page filled the viewport, so one global `segments`
 * array was the page's breadcrumb. Under the OS-desktop shell (ADR-297 D19
 * + ADR-358) N surfaces are open as windows simultaneously on the one
 * `/desktop` baseline — a single global crumb can't say where each window
 * is. Worse, when surfaces became windows every page DELETED its
 * `setBreadcrumb()` call (see the docblocks in agents/recurrence/files
 * page.tsx), so the old context went dark: `BreadcrumbProvider` wrapped the
 * tree but nothing wrote to it, and the WindowFrame title bar showed only a
 * flat surface name ("Agents", never "Agents › Reviewer › Activity").
 *
 * The fix (2026-06-25): make the crumb PER-SLUG. Each surface, in detail
 * mode, registers its own in-window position under its kernel slug via
 * `useWindowCrumb(slug, segments)`. `SurfaceViewport` reads the crumb for
 * each open window's slug and passes it to that window's `WindowFrame`, so
 * every window's title bar shows its own locator independently.
 *
 * Segments are the in-window path BELOW the surface name (the WindowFrame
 * already renders the surface title from the registry). A surface in LIST
 * mode registers `[]` (or simply doesn't register) — the flat title stands.
 * In DETAIL mode it registers e.g. `[{ label: 'Reviewer' }]` →
 * "Agents › Reviewer". The optional `onClick` on a segment (typically the
 * back-to-list crumb) clears the window's deep-link param.
 *
 * Mobile: the WindowFrame title bar collapses the crumb (drops intermediate
 * segments, keeps the leaf) under a width threshold — the title bar is a
 * locator, not a navigator; the in-body back affordance carries "go back"
 * on small screens. See WindowFrame.
 *
 * ADR-442 D2 (2026-07-11): this context is THE surface-chrome declaration
 * channel, and it carries BOTH halves — identity (`useWindowCrumb`, above)
 * and whole-surface verbs (`useSurfaceActions`, below). The surface bar
 * (GlobalLocatorStrip) renders both for the foregrounded surface; actions
 * are DATA, never JSX — the surface declares, the bar owns the rendering.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ComponentType,
  type ReactNode,
} from 'react';
import type { KernelSurfaceSlug } from '@/types/desk';

export interface BreadcrumbSegment {
  label: string;
  /** Local handler — typically "back to the window's list mode" (clears the
   *  surface's deep-link param via useSurfaceParam). Prefer this over href:
   *  the crumb is intra-window state, not a route navigation. */
  onClick?: () => void;
  kind?: 'surface' | 'entity' | 'task' | 'agent' | 'context' | 'output' | 'artifact';
}

/**
 * A surface-declared whole-surface verb (ADR-442 D2). Data, never JSX.
 * Link-shaped actions (`to` set) render through SurfaceLink so native link
 * affordances (middle-click, new tab, a11y) survive; button-shaped actions
 * (`onClick`) render as buttons. The surface bar owns style and placement.
 */
export interface SurfaceAction {
  id: string;
  label: string;
  icon?: ComponentType<{ className?: string }>;
  /** Button-shaped action. Ignored when `to` is present. */
  onClick?: () => void;
  /** Link-shaped action — the target surface slug (renders via SurfaceLink). */
  to?: KernelSurfaceSlug;
  /** Params for a link-shaped action (bare keys — namespaced downstream). */
  params?: Record<string, string>;
}

type CrumbMap = Record<string, BreadcrumbSegment[]>;
type ActionMap = Record<string, SurfaceAction[]>;

/** Identity key for the equality guard — link-shaped actions re-register when
 *  their target changes; button handlers (recreated per render) don't churn. */
function actionKey(a: SurfaceAction): string {
  return `${a.id}␟${a.label}␟${a.to ?? ''}␟${JSON.stringify(a.params ?? null)}`;
}

interface WindowCrumbContextValue {
  /** All registered window crumbs, keyed by kernel slug. */
  crumbs: CrumbMap;
  /** Read one window's crumb segments (empty array if none registered). */
  getCrumb: (slug: string) => BreadcrumbSegment[];
  /** Register/replace a window's crumb. Pass `[]` to clear. */
  setCrumb: (slug: string, segments: BreadcrumbSegment[]) => void;
  /** Drop a window's crumb entirely (on unmount / window close). */
  clearCrumb: (slug: string) => void;
  /** Read one surface's declared actions (ADR-442; empty if none). */
  getActions: (slug: string) => SurfaceAction[];
  /** Register/replace a surface's declared actions. Pass `[]` to clear. */
  setActions: (slug: string, actions: SurfaceAction[]) => void;
  /** Drop a surface's actions entirely (on unmount). */
  clearActions: (slug: string) => void;
  /** True when THIS surface renders its own locator in its own chrome row —
   *  the OS strip suppresses for it to avoid a doubled "you are here"
   *  (2026-07-14; the native-app pattern — the app's window carries its own
   *  title, the OS chrome doesn't duplicate it). */
  isSelfLocated: (slug: string) => boolean;
  /** Declare/withdraw THIS surface as self-located. */
  setSelfLocated: (slug: string, on: boolean) => void;
}

const WindowCrumbCtx = createContext<WindowCrumbContextValue>({
  crumbs: {},
  getCrumb: () => [],
  setCrumb: () => {},
  clearCrumb: () => {},
  getActions: () => [],
  setActions: () => {},
  clearActions: () => {},
  isSelfLocated: () => false,
  setSelfLocated: () => {},
});

export function BreadcrumbProvider({ children }: { children: ReactNode }) {
  const [crumbs, setCrumbs] = useState<CrumbMap>({});
  const [actions, setActionsMap] = useState<ActionMap>({});
  const [selfLocated, setSelfLocatedMap] = useState<Record<string, true>>({});

  const getCrumb = useCallback(
    (slug: string): BreadcrumbSegment[] => crumbs[slug] ?? [],
    [crumbs]
  );

  const getActions = useCallback(
    (slug: string): SurfaceAction[] => actions[slug] ?? [],
    [actions]
  );

  const setActions = useCallback((slug: string, next: SurfaceAction[]) => {
    setActionsMap((prev) => {
      const existing = prev[slug];
      if (
        existing &&
        existing.length === next.length &&
        existing.every((a, i) => actionKey(a) === actionKey(next[i]))
      ) {
        return prev;
      }
      return { ...prev, [slug]: next };
    });
  }, []);

  const clearActions = useCallback((slug: string) => {
    setActionsMap((prev) => {
      if (!(slug in prev)) return prev;
      const next = { ...prev };
      delete next[slug];
      return next;
    });
  }, []);

  const setCrumb = useCallback((slug: string, segments: BreadcrumbSegment[]) => {
    setCrumbs((prev) => {
      const existing = prev[slug];
      // Cheap equality guard so an effect re-running with the same labels
      // doesn't churn the map (and re-render every WindowFrame).
      if (
        existing &&
        existing.length === segments.length &&
        existing.every((s, i) => s.label === segments[i].label)
      ) {
        return prev;
      }
      return { ...prev, [slug]: segments };
    });
  }, []);

  const clearCrumb = useCallback((slug: string) => {
    setCrumbs((prev) => {
      if (!(slug in prev)) return prev;
      const next = { ...prev };
      delete next[slug];
      return next;
    });
  }, []);

  const isSelfLocated = useCallback(
    (slug: string): boolean => Boolean(selfLocated[slug]),
    [selfLocated]
  );

  const setSelfLocated = useCallback((slug: string, on: boolean) => {
    setSelfLocatedMap((prev) => {
      const has = Boolean(prev[slug]);
      if (has === on) return prev; // no churn
      const next = { ...prev };
      if (on) next[slug] = true;
      else delete next[slug];
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({
      crumbs,
      getCrumb,
      setCrumb,
      clearCrumb,
      getActions,
      setActions,
      clearActions,
      isSelfLocated,
      setSelfLocated,
    }),
    [
      crumbs,
      getCrumb,
      setCrumb,
      clearCrumb,
      getActions,
      setActions,
      clearActions,
      isSelfLocated,
      setSelfLocated,
    ]
  );

  return <WindowCrumbCtx.Provider value={value}>{children}</WindowCrumbCtx.Provider>;
}

export function useWindowCrumbRegistry(): WindowCrumbContextValue {
  return useContext(WindowCrumbCtx);
}

/**
 * Surface-side hook: register THIS window's in-window crumb. Call it from a
 * surface page with the segments for the current deep-link position. Pass
 * `[]` (or omit segments via an empty array) in list mode — the flat
 * WindowFrame title stands. The crumb auto-clears when the surface unmounts.
 *
 *   // agents/page.tsx, detail mode:
 *   useWindowCrumb('agents', selectedAgent
 *     ? [{ label: agentName, onClick: () => p.set({ agent: null }) }]
 *     : []);
 */
export function useWindowCrumb(slug: string, segments: BreadcrumbSegment[]): void {
  const { setCrumb, clearCrumb } = useWindowCrumbRegistry();
  // Serialize the labels so the effect only re-fires when the crumb's text
  // changes — handlers are re-created each render but we don't want to churn
  // on that (the registry's equality guard also protects, this avoids the
  // effect body entirely).
  const labelKey = segments.map((s) => s.label).join('␟');
  useEffect(() => {
    setCrumb(slug, segments);
    return () => clearCrumb(slug);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, labelKey, setCrumb, clearCrumb]);
}

/**
 * Surface-side hook: declare THIS surface's whole-surface verbs into the
 * surface bar (ADR-442 D2). Actions are data ({id, label, icon?, onClick |
 * to+params}); the bar renders them right-aligned for the foregrounded
 * surface only. Pass `[]` when the surface has no verbs in its current state
 * (e.g. the Studio's start state). Auto-clears on unmount.
 *
 *   // StudioSurface, workbench state:
 *   useSurfaceActions('studio', artifactPath
 *     ? [{ id: 'open-in-files', label: 'Open in Files', icon: ExternalLink,
 *          to: 'files', params: { path: artifactPath } }]
 *     : []);
 */
export function useSurfaceActions(slug: string, actions: SurfaceAction[]): void {
  const { setActions, clearActions } = useWindowCrumbRegistry();
  // Same churn discipline as useWindowCrumb: re-fire only when the actions'
  // identity (id/label/target) changes, not on handler re-creation.
  const identityKey = actions.map(actionKey).join('␞');
  useEffect(() => {
    setActions(slug, actions);
    return () => clearActions(slug);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, identityKey, setActions, clearActions]);
}

/**
 * Surface-side hook: declare that THIS surface renders its own "you are here"
 * locator in its own chrome row, so the OS surface bar (GlobalLocatorStrip)
 * SUPPRESSES for it — one locator, never two (2026-07-14, operator ruling).
 *
 * The native-app pattern: an app's own window carries its title/location in
 * its toolbar; the OS chrome doesn't repeat it. Studio (its workbench toolbar
 * already spans a full row) and Chat (its lane-list + conversation headers
 * already name the lane) both adopt this — the OS strip was a redundant
 * ~28px band above a surface that already said where you are. Surfaces that
 * do NOT self-locate keep the OS strip unchanged (Files, Channels, Settings…).
 *
 * The surface renders the crumb ITSELF from `useWindowCrumb`'s segments (or
 * its own state) inside its chrome — this hook only governs the OS strip's
 * visibility, it does not move the crumb. Auto-withdraws on unmount.
 *
 *   // StudioSurface, workbench state (start state passes false):
 *   useSelfLocatedSurface('studio', Boolean(artifactPath));
 */
export function useSelfLocatedSurface(slug: string, on: boolean = true): void {
  const { setSelfLocated } = useWindowCrumbRegistry();
  useEffect(() => {
    setSelfLocated(slug, on);
    return () => setSelfLocated(slug, false);
  }, [slug, on, setSelfLocated]);
}

/**
 * @deprecated Legacy global-breadcrumb hook. Returns a no-op shim so any
 * un-migrated caller compiles. Use `useWindowCrumb(slug, segments)` instead —
 * the global single-crumb model can't represent N open windows (ADR-297 D19).
 * Remove once no callers remain.
 */
export function useBreadcrumb(): {
  segments: BreadcrumbSegment[];
  setBreadcrumb: (segments: BreadcrumbSegment[]) => void;
  clearBreadcrumb: () => void;
} {
  return { segments: [], setBreadcrumb: () => {}, clearBreadcrumb: () => {} };
}
