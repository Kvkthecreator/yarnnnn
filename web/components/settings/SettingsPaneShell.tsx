"use client";

/**
 * SettingsPaneShell — the ONE split-nav surface shell.
 *
 * Original home: ADR-341 (2026-06-18) — the shared pane-container behind the
 * Settings doors. Now (2026-06-30) the SINGULAR responsive split-nav shell
 * for EVERY "nav-list + detail-pane" surface in the authenticated shell:
 *   - Workspace Settings (`/workspace-settings`)
 *   - System Settings (`/settings`)
 *   - Channels (`/channels`)
 *   - Notifications (`/notifications`)
 *   - Freddie's pane (AgentContentView ReviewerDetail) — was a forked copy of
 *     this sidebar; now mounts the shell (Singular Implementation, CLAUDE.md §2)
 *   - Files (`/files`) — the explorer tree mode (custom `navContent` + resize)
 *
 * Singular Implementation (ADR-341 D5 + the 2026-06-30 unification): one
 * sidebar + pane-switch + responsive contract, six mounts. Each surface passes
 * EITHER `paneGroups` (the standard grouped pane list) OR `navContent` (custom
 * nav JSX, e.g. the Files tree). Both flow through the same responsive frame.
 *
 * RESPONSIVE CONTRACT (the 2026-06-30 fix — the prior fixed-width `w-44 sm:w-52`
 * nav crushed the body on narrow screens; some surfaces had a collapse button,
 * most did not — inconsistent + unstable):
 *   - WIDE (≥ MOBILE_BREAKPOINT_PX): two-pane row — nav | body, unchanged.
 *   - NARROW (< MOBILE_BREAKPOINT_PX, the existing `useViewport().isMobile`
 *     signal that already drives single-window mode): a list→detail DRILL-IN.
 *     The nav fills the width as a list; selecting a pane swaps to the
 *     full-width body with a `‹ Back` row. The iOS-Settings model. One thing
 *     on screen at a time; the body always gets full width. Drill-in state is
 *     LOCAL (`drilledIn`) — it does not touch the URL; the `pane` param is
 *     still the source of truth for WHICH pane.
 *
 * Mechanism (ADR-340 P2 + ADR-358 D6):
 *   - macOS System Settings shape: one door, sidebar of grouped panes.
 *   - The pane is a WINDOW-NAMESPACED deep-link param (`{windowSlug}.pane=`,
 *     ADR-358 D6) — `settings.pane`, `workspace-settings.pane`, etc. Both doors
 *     can be open at once without their pane selections colliding. (`?tab=`
 *     kept as a legacy alias for the account door's General tabs.) Read/written
 *     via `useSurfaceParam(windowSlug)`.
 *   - foregroundSurface(pane-slug) → parent container + `{parent}.pane=`; the
 *     pane resolution is generic (useSurfacePreferences reads `pane_of`).
 *
 * NAV-CONTENT MODE (Files): when `navContent` is supplied the shell renders it
 * verbatim in the nav region instead of the grouped pane list. The surface owns
 * pane selection itself (Files uses internal `selectedPath`); it tells the shell
 * the current leaf label via `activeLabel` so the narrow Back row reads right.
 * `onActivate` lets a custom nav request the drill-in (push to the body) when
 * the operator picks an item. Optional `resizable` enables a drag handle + the
 * persisted width (Files' explorer).
 */

import { useState, useEffect, useRef, useCallback, type ComponentType, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { useSurfaceParam, useSurfacePreferences } from "@/lib/shell/useSurfacePreferences";
import { useViewport } from "@/lib/shell/useViewport";

export interface PaneDef {
  /** Pane key — matches the registry slug for pane-grade surfaces, or a
   *  door-local tab key (billing/usage/account) for the General group. */
  key: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
}

export interface PaneGroup {
  label: string;
  panes: PaneDef[];
}

interface SettingsPaneShellProps {
  /**
   * ADR-358 D6 — the kernel slug of the WINDOW this shell renders inside
   * (`settings`, `workspace-settings`, `channels`, `notifications`, `agents`,
   * `files`). The pane is namespaced under it (`{windowSlug}.pane=`) so two
   * shells never collide on a shared `?pane=`.
   */
  windowSlug: string;

  // --- paneGroups mode (the 4 config surfaces + Freddie) -------------------
  /** Sidebar sections, top→bottom. Omit when using `navContent`. */
  paneGroups?: PaneGroup[];
  /** Default pane when no namespaced pane/`?tab=` is present. */
  defaultPane?: string;
  /** Render the active pane's body (paneGroups mode). */
  renderPane?: (activePane: string) => ReactNode;

  // --- navContent mode (Files explorer) ------------------------------------
  /** Custom nav region (e.g. the Files tree). Mutually exclusive with
   *  `paneGroups`. The surface owns selection; the shell owns the frame. */
  navContent?: ReactNode;
  /** Body to render alongside `navContent`. */
  children?: ReactNode;
  /** Current selection label for the narrow Back row (navContent mode).
   *  When falsy, narrow mode stays on the nav list (nothing selected). */
  activeLabel?: string | null;
  /** Custom nav signals a selection was made → drill into the body (narrow). */
  onActivateRef?: (activate: () => void) => void;
  /** Enable a draggable resize handle + persisted width (Files). */
  resizable?: boolean;
  /** navContent mode: drop the default nav padding so custom nav (the Files
   *  explorer header + tree) fills the region edge-to-edge. Default true
   *  (the grouped pane list wants padding). */
  navPadded?: boolean;

  // --- shared ----------------------------------------------------------------
  /** Optional banner row above the body (e.g. subscription success). */
  banner?: ReactNode;
  /** Optional header rendered ABOVE the whole split (Freddie's identity bar). */
  header?: ReactNode;
  /**
   * ADR-346 — drop the centered `max-w-3xl mx-auto p-6` body wrapper so the
   * pane owns its own layout. Config doors want the constrained card column
   * (default false); full-bleed panes (FeedSurface, RecurrenceList, the Files
   * viewer) fill the pane region.
   */
  fullBleed?: boolean;
  /** Sidebar section header label (default "Settings panes" for a11y). */
  navLabel?: string;
}

const RESIZE_KEY_PREFIX = "yarnnn:pane-shell:nav-width:";
const NAV_WIDTH_DEFAULT = 280;
const NAV_WIDTH_MIN = 200;
const NAV_WIDTH_MAX = 560;

export function SettingsPaneShell({
  windowSlug,
  paneGroups,
  defaultPane,
  renderPane,
  navContent,
  children,
  activeLabel,
  onActivateRef,
  resizable = false,
  navPadded = true,
  banner,
  header,
  fullBleed = false,
  navLabel = "Settings panes",
}: SettingsPaneShellProps) {
  const viewport = useViewport();
  const isNarrow = viewport.isMobile;

  // ADR-358 D6 — read/write this window's OWN namespaced pane key
  // (`{windowSlug}.pane`). `useSurfaceParam` handles the prefix; `?tab=`
  // stays a flat legacy alias read directly.
  const surfaceParam = useSurfaceParam(windowSlug);
  const { setSurfaceParams } = useSurfacePreferences();
  const searchParams = useSearchParams();
  // Legacy aliases for `pane`: the flat `?tab=` (account door's General tabs)
  // AND this window's namespaced `{windowSlug}.tab=` (e.g. an in-flight
  // `agents.tab=identity` deep-link from before the pane rename). Canonical is
  // the namespaced `{windowSlug}.pane=`.
  const flatTabParam = searchParams.get("tab");
  const namespacedTabParam = surfaceParam.get("tab");
  const paneParam = surfaceParam.get("pane"); // canonical, window-namespaced

  const navMode = !!navContent;

  const allPanes = (paneGroups ?? []).flatMap((g) => g.panes.map((p) => p.key));
  const requestedPane = paneParam ?? namespacedTabParam ?? flatTabParam;
  const initial =
    requestedPane && allPanes.includes(requestedPane) ? requestedPane : (defaultPane ?? "");

  const [activePane, setActivePane] = useState<string>(initial);

  // NARROW drill-in: local UI state (not URL). In paneGroups mode it's derived
  // from whether the operator has tapped a pane this session; in navContent
  // mode the custom nav requests it via onActivate.
  const [drilledIn, setDrilledIn] = useState(false);

  // Sync active pane when a deep-link arrives while the window is already
  // mounted (foregroundSurface('budget') sets workspace-settings.pane=budget).
  useEffect(() => {
    if (!navMode && requestedPane && allPanes.includes(requestedPane)) {
      setActivePane(requestedPane);
      // A deep-link to a specific pane should land ON that pane (drilled in)
      // on narrow screens — the operator asked for it by name.
      if (isNarrow) setDrilledIn(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedPane]);

  // Leaving narrow mode (rotate / resize up) clears the drill-in so the wide
  // two-pane view always shows both panes.
  useEffect(() => {
    if (!isNarrow) setDrilledIn(false);
  }, [isNarrow]);

  const selectPane = (pane: string) => {
    setActivePane(pane);
    if (isNarrow) setDrilledIn(true);
    // Set this window's namespaced pane; clear the flat legacy `?tab=`.
    surfaceParam.set({ pane });
    setSurfaceParams({ tab: null });
  };

  // navContent mode: expose a drill-in trigger to the custom nav.
  const activateFromNav = useCallback(() => {
    if (isNarrow) setDrilledIn(true);
  }, [isNarrow]);
  useEffect(() => {
    onActivateRef?.(activateFromNav);
  }, [onActivateRef, activateFromNav]);

  // --- resizable nav (Files) -------------------------------------------------
  const resizeStorageKey = RESIZE_KEY_PREFIX + windowSlug;
  const [navWidth, setNavWidth] = useState(NAV_WIDTH_DEFAULT);
  const dragging = useRef(false);

  useEffect(() => {
    if (!resizable) return;
    try {
      const raw = window.localStorage.getItem(resizeStorageKey);
      if (raw) {
        const n = parseInt(raw, 10);
        if (!Number.isNaN(n)) setNavWidth(Math.max(NAV_WIDTH_MIN, Math.min(NAV_WIDTH_MAX, n)));
      }
    } catch {}
  }, [resizable, resizeStorageKey]);

  useEffect(() => {
    if (!resizable) return;
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      setNavWidth(Math.max(NAV_WIDTH_MIN, Math.min(NAV_WIDTH_MAX, e.clientX)));
    };
    const onUp = () => {
      if (!dragging.current) return;
      dragging.current = false;
      try {
        window.localStorage.setItem(resizeStorageKey, String(navWidth));
      } catch {}
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [resizable, navWidth, resizeStorageKey]);

  const onDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  // === nav region ============================================================
  const navListChildren = navMode ? (
    navContent
  ) : (
    (paneGroups ?? []).map((group) => (
      <div key={group.label}>
        <div className="px-2 pb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
          {group.label}
        </div>
        {group.panes.map((pane) => {
          const Icon = pane.icon;
          const isActive = activePane === pane.key;
          return (
            <button
              key={pane.key}
              onClick={() => selectPane(pane.key)}
              className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors ${
                isActive
                  ? "bg-muted text-foreground font-medium"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {pane.label}
            </button>
          );
        })}
      </div>
    ))
  );

  // === body region ===========================================================
  const bodyChildren = navMode ? (
    children
  ) : fullBleed ? (
    <div className="flex-1 min-w-0 min-h-0 overflow-hidden flex flex-col">
      {banner}
      {renderPane?.(activePane)}
    </div>
  ) : (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto p-6">
        {banner}
        {renderPane?.(activePane)}
      </div>
    </div>
  );

  // === NARROW: list→detail drill-in ==========================================
  if (isNarrow) {
    // The label that heads the Back row. paneGroups: the active pane's label;
    // navContent: the surface-provided activeLabel (falls back to navLabel).
    const activeMeta = (paneGroups ?? []).flatMap((g) => g.panes).find((p) => p.key === activePane);
    const backLabel = navMode ? (activeLabel ?? navLabel) : (activeMeta?.label ?? null);

    // Drill in whenever a selection has been made. paneGroups: drilledIn is set
    // by selectPane. navContent: the custom nav calls onActivate (which sets
    // drilledIn) on any selection — including a deselect-to-Recents.
    const showBody = drilledIn;

    return (
      <div className="h-full flex flex-col min-h-0">
        {header}
        {showBody ? (
          <div className="flex-1 min-h-0 flex flex-col">
            <button
              onClick={() => setDrilledIn(false)}
              className="flex items-center gap-1 px-3 py-2 text-sm text-muted-foreground hover:text-foreground border-b border-border shrink-0"
            >
              <ChevronLeft className="w-4 h-4" />
              {backLabel ?? navLabel}
            </button>
            <div className="flex-1 min-h-0 overflow-hidden flex flex-col">{bodyChildren}</div>
          </div>
        ) : (
          <nav
            aria-label={navLabel}
            className={`flex-1 overflow-y-auto ${navPadded ? "py-3 px-2 space-y-4" : ""}`}
          >
            {navListChildren}
          </nav>
        )}
      </div>
    );
  }

  // === WIDE: two-pane row ====================================================
  return (
    <div className="h-full flex flex-col min-h-0">
      {header}
      <div className="flex-1 flex min-h-0">
        <nav
          aria-label={navLabel}
          className={`${resizable ? "" : "w-44 sm:w-52"} shrink-0 border-r border-border overflow-y-auto ${navPadded ? "py-3 px-2 space-y-4" : ""}`}
          style={resizable ? { width: navWidth } : undefined}
        >
          {navListChildren}
        </nav>
        {resizable && (
          <div
            onMouseDown={onDragStart}
            className="w-1 shrink-0 cursor-col-resize bg-transparent hover:bg-primary/20 active:bg-primary/30 transition-colors"
            title="Drag to resize"
          />
        )}
        {bodyChildren}
      </div>
    </div>
  );
}
