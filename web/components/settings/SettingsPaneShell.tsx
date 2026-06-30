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
 *     full-width body. The iOS-Settings model. One thing on screen at a time;
 *     the body always gets full width. Drill-in state is LOCAL (`drilledIn`) —
 *     it does not touch the URL; the `pane` param is still the source of truth
 *     for WHICH pane.
 *
 *     The "‹ back to the list" affordance is NOT a shell-rendered row — it is
 *     the OS's single always-mounted locator (`GlobalLocatorStrip`, fed by
 *     `useWindowCrumb`). In paneGroups mode the shell REGISTERS the active
 *     pane as this window's crumb (leaf `onClick` drills out), so the one OS
 *     locator shows `‹ {paneLabel}` on mobile — no parallel Back row (that
 *     stacked a second identical `‹ leaf` chip over the locator's). In
 *     navContent mode the SURFACE owns its crumb (Files registers the selected
 *     node); it drives drill-out via the `onDrillOut` the shell hands back.
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
 * pane selection itself (Files uses internal `selectedPath`) AND its own OS
 * locator crumb. It reports `hasSelection` so the narrow view knows the body is
 * worth drilling into; `onActivateRef`/`onDrillOutRef` hand the surface the
 * shell's drill-in / drill-out fns (a tree click drills in; the locator's
 * "back" drills out). Optional `resizable` enables a drag handle + the
 * persisted width (Files' explorer).
 */

import { useState, useEffect, useRef, useCallback, type ComponentType, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { useSurfaceParam, useSurfacePreferences } from "@/lib/shell/useSurfacePreferences";
import { useViewport } from "@/lib/shell/useViewport";
import { useWindowCrumb } from "@/contexts/BreadcrumbContext";

export interface PaneDef {
  /** Pane key — matches the registry slug for pane-grade surfaces, or a
   *  door-local tab key (billing/usage/account) for the General group. */
  key: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
}

/**
 * PaneHeader — THE canonical title block at the top of a pane body inside the
 * shell (2026-07-01 unification). One `<h2>` size/weight/spacing for EVERY
 * split-nav pane, replacing the per-surface hand-rolled copies that had drifted
 * (Channels + Notifications each defined their own identical-but-separate
 * `PaneHeader`; the body cards then often rendered a SECOND header of their own
 * — the Connectors double-header).
 *
 * Distinct from `SurfaceIdentityHeader` (the page-level `<h1>` hero for DETAIL
 * surfaces — "what is this page about"). This is the pane-level `<h2>` — "what
 * is this pane" — inside a multi-pane shell. The two never both apply to one
 * region, so they stay separate components.
 *
 * Slots:
 *   - `icon` (optional) — renders left of the title. Most panes omit it (the
 *     nav already carries the pane icon); keep it for parity where a body
 *     component used to self-render an icon'd header.
 *   - `subtitle` (optional) — the one-line description under the title.
 *   - `action` (optional) — right-aligned escape-hatch link / button
 *     (Notifications' "Open full Queue →" mirror links).
 *
 * The body card mounted UNDER this header should NOT render its own title +
 * description — this header owns them. (A card may still render finer-grained
 * sub-section labels inside its content.)
 */
export function PaneHeader({
  title,
  subtitle,
  icon: Icon,
  action,
}: {
  title: string;
  subtitle?: string;
  icon?: ComponentType<{ className?: string }>;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border/60 px-6 py-3 shrink-0">
      <div className="flex items-center gap-2 min-w-0">
        {Icon && <Icon className="w-4 h-4 shrink-0 text-muted-foreground" />}
        <div className="min-w-0">
          <h2 className="text-sm font-medium text-foreground">{title}</h2>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
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
  /** navContent mode: whether the surface currently has something selected to
   *  show in the body. Drives whether the narrow view drills in. When false,
   *  narrow stays on the nav list. */
  hasSelection?: boolean;
  /** Custom nav signals a selection was made → drill into the body (narrow).
   *  The shell hands back its `activate` fn via this ref-setter. */
  onActivateRef?: (activate: () => void) => void;
  /** Custom nav requests drill-OUT (its crumb "back" action) → return to the
   *  nav list on narrow. The shell hands back its `drillOut` fn here. */
  onDrillOutRef?: (drillOut: () => void) => void;
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
   *
   * Equivalent to `contentWidth="fill"` — kept as the legacy boolean alias.
   * When both are passed, `contentWidth` wins.
   */
  fullBleed?: boolean;
  /**
   * Body-width policy (2026-06-30 — the missing third leg of the shared-shell
   * contract). Resolves the awkward "narrow column floating dead-center in a
   * wide window" gap by making readable-width an explicit property of the
   * content TYPE, instead of each surface improvising `mx-auto max-w-3xl`:
   *   - `form` (DEFAULT) — `max-w-3xl mx-auto p-6`: centered card column. Right
   *     for settings/config forms (workspace-settings, account, channels config
   *     panes) — a centered narrow column reads well for short forms.
   *   - `reading` — `max-w-3xl p-6` WITHOUT `mx-auto`: a readable column
   *     LEFT-PINNED next to the nav (no center gap). Right for prose/doc panes
   *     (Freddie's persona/governance panes).
   *   - `fill` — edge-to-edge; the pane owns its own layout (= `fullBleed`).
   *     Right for viewers/timelines that should use the width (Files viewer,
   *     FeedSurface, RecurrenceList).
   */
  contentWidth?: "form" | "reading" | "fill";
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
  hasSelection = false,
  onActivateRef,
  onDrillOutRef,
  resizable = false,
  navPadded = true,
  banner,
  header,
  fullBleed = false,
  contentWidth,
  navLabel = "Settings panes",
}: SettingsPaneShellProps) {
  // Resolve the body-width policy. `contentWidth` is canonical; `fullBleed`
  // is the legacy boolean alias (→ `fill`). Default is `form` (centered card
  // column) to preserve the config-door behavior.
  const widthMode: "form" | "reading" | "fill" =
    contentWidth ?? (fullBleed ? "fill" : "form");
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

  // navContent mode: expose drill-in / drill-out triggers to the custom nav.
  const activateFromNav = useCallback(() => {
    if (isNarrow) setDrilledIn(true);
  }, [isNarrow]);
  const drillOut = useCallback(() => setDrilledIn(false), []);
  useEffect(() => {
    onActivateRef?.(activateFromNav);
  }, [onActivateRef, activateFromNav]);
  useEffect(() => {
    onDrillOutRef?.(drillOut);
  }, [onDrillOutRef, drillOut]);

  // The active pane's label (paneGroups mode) — used for the OS locator crumb.
  const activePaneLabel =
    (paneGroups ?? []).flatMap((g) => g.panes).find((p) => p.key === activePane)?.label ?? null;

  // SINGLE-LOCATOR contract: in paneGroups mode, register THIS window's crumb
  // for the active pane while drilled in on narrow, so the OS's one locator
  // (`GlobalLocatorStrip`) shows `‹ {paneLabel}` — instead of the shell drawing
  // a SECOND parallel back row. The leaf `onClick` drills out (= the locator's
  // "back to list"). navContent surfaces own their own crumb (Files), so the
  // shell registers nothing for them (empty array, no double-registration).
  useWindowCrumb(
    windowSlug,
    !navMode && isNarrow && drilledIn && activePaneLabel
      ? [{ label: activePaneLabel, onClick: drillOut }]
      : []
  );

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
  // Three width modes (2026-06-30): fill = edge-to-edge (viewers/timelines);
  // reading = readable column LEFT-pinned next to the nav (prose/docs, no
  // center gap); form = centered card column (config forms).
  const bodyChildren = navMode ? (
    children
  ) : widthMode === "fill" ? (
    <div className="flex-1 min-w-0 min-h-0 overflow-hidden flex flex-col">
      {banner}
      {renderPane?.(activePane)}
    </div>
  ) : (
    <div className="flex-1 overflow-y-auto">
      <div className={widthMode === "reading" ? "max-w-3xl p-6" : "max-w-3xl mx-auto p-6"}>
        {banner}
        {renderPane?.(activePane)}
      </div>
    </div>
  );

  // === NARROW: list→detail drill-in ==========================================
  if (isNarrow) {
    // Drill in whenever a selection has been made. paneGroups: drilledIn is set
    // by selectPane. navContent: the custom nav calls onActivate (which sets
    // drilledIn) on any selection — including a deselect-to-Recents. The
    // navContent body is only worth showing when the surface reports a
    // selection (else there is nothing to drill into — stay on the list).
    const showBody = drilledIn && (navMode ? hasSelection : true);

    // NO shell-rendered back row — the OS's single locator (GlobalLocatorStrip)
    // owns the `‹ {leaf}` back affordance (paneGroups: the crumb registered
    // above; navContent: the surface's own crumb). One locator, not two.
    return (
      <div className="h-full flex flex-col min-h-0">
        {header}
        {showBody ? (
          <div className="flex-1 min-h-0 overflow-hidden flex flex-col">{bodyChildren}</div>
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
