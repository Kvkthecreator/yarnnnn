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
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export interface BreadcrumbSegment {
  label: string;
  /** Local handler — typically "back to the window's list mode" (clears the
   *  surface's deep-link param via useSurfaceParam). Prefer this over href:
   *  the crumb is intra-window state, not a route navigation. */
  onClick?: () => void;
  kind?: 'surface' | 'entity' | 'task' | 'agent' | 'context' | 'output' | 'artifact';
}

type CrumbMap = Record<string, BreadcrumbSegment[]>;

interface WindowCrumbContextValue {
  /** All registered window crumbs, keyed by kernel slug. */
  crumbs: CrumbMap;
  /** Read one window's crumb segments (empty array if none registered). */
  getCrumb: (slug: string) => BreadcrumbSegment[];
  /** Register/replace a window's crumb. Pass `[]` to clear. */
  setCrumb: (slug: string, segments: BreadcrumbSegment[]) => void;
  /** Drop a window's crumb entirely (on unmount / window close). */
  clearCrumb: (slug: string) => void;
}

const WindowCrumbCtx = createContext<WindowCrumbContextValue>({
  crumbs: {},
  getCrumb: () => [],
  setCrumb: () => {},
  clearCrumb: () => {},
});

export function BreadcrumbProvider({ children }: { children: ReactNode }) {
  const [crumbs, setCrumbs] = useState<CrumbMap>({});

  const getCrumb = useCallback(
    (slug: string): BreadcrumbSegment[] => crumbs[slug] ?? [],
    [crumbs]
  );

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

  const value = useMemo(
    () => ({ crumbs, getCrumb, setCrumb, clearCrumb }),
    [crumbs, getCrumb, setCrumb, clearCrumb]
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
