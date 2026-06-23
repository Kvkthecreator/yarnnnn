"use client";

/**
 * SettingsPaneShell — ADR-341 (2026-06-18).
 *
 * The shared pane-container shell behind BOTH Settings doors: System
 * Settings (`/settings`) and Workspace Settings (`/workspace-settings`).
 * Singular Implementation (ADR-341 D5) — one sidebar + pane-switch +
 * `?pane=` URL-sync mechanism, two mounts. Each door passes its own
 * `paneGroups` (the sidebar sections) + a `renderPane(activePane)`
 * body-renderer.
 *
 * Mechanism (ADR-340 P2 + ADR-358 D6):
 *   - macOS System Settings shape: one door, sidebar of grouped panes.
 *   - The pane is a WINDOW-NAMESPACED deep-link param (`{windowSlug}.pane=`,
 *     ADR-358 D6) — `settings.pane` for the account door, `workspace-settings.pane`
 *     for the operation door. Both doors can be open at once without their
 *     pane selections colliding. (`?tab=` kept as a legacy alias for the
 *     account door's General tabs.) Read/written via `useSurfaceParam(windowSlug)`.
 *   - foregroundSurface(pane-slug) → parent container + `{parent}.pane=`; the
 *     pane resolution is generic (useSurfacePreferences reads `pane_of`),
 *     so a second container works with zero new window-manager code.
 */

import { useState, useEffect, type ComponentType } from "react";
import { useSearchParams } from "next/navigation";
import { useSurfaceParam, useSurfacePreferences } from "@/lib/shell/useSurfacePreferences";

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
   * (`settings` or `workspace-settings`). The pane is namespaced under it
   * (`{windowSlug}.pane=`) so the two Settings doors never collide on a
   * shared `?pane=`.
   */
  windowSlug: string;
  /** Sidebar sections, top→bottom. */
  paneGroups: PaneGroup[];
  /** Default pane when no namespaced pane/`?tab=` is present. */
  defaultPane: string;
  /** Render the active pane's body. */
  renderPane: (activePane: string) => React.ReactNode;
  /** Optional banner row above the body (e.g. subscription success). */
  banner?: React.ReactNode;
  /**
   * ADR-346 — drop the centered `max-w-3xl mx-auto p-6` body wrapper so the
   * pane owns its own layout. Config doors (System / Workspace Settings) want
   * the constrained card column (default false); the Operation composition's
   * full-bleed panes (FeedSurface, RecurrenceList) fill the pane region.
   */
  fullBleed?: boolean;
  /** Sidebar section header label (default "Settings panes" for a11y). */
  navLabel?: string;
}

export function SettingsPaneShell({
  windowSlug,
  paneGroups,
  defaultPane,
  renderPane,
  banner,
  fullBleed = false,
  navLabel = "Settings panes",
}: SettingsPaneShellProps) {
  // ADR-358 D6 — read/write this window's OWN namespaced pane key
  // (`{windowSlug}.pane`). `useSurfaceParam` handles the prefix; `?tab=`
  // stays a flat legacy alias read directly.
  const surfaceParam = useSurfaceParam(windowSlug);
  const { setSurfaceParams } = useSurfacePreferences();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab"); // legacy flat alias (account door)
  const paneParam = surfaceParam.get("pane"); // canonical, window-namespaced

  const allPanes = paneGroups.flatMap((g) => g.panes.map((p) => p.key));
  const requestedPane = paneParam ?? tabParam;
  const initial = requestedPane && allPanes.includes(requestedPane) ? requestedPane : defaultPane;

  const [activePane, setActivePane] = useState<string>(initial);

  // Sync active pane when a deep-link arrives while the window is already
  // mounted (foregroundSurface('budget') sets workspace-settings.pane=budget).
  useEffect(() => {
    if (requestedPane && allPanes.includes(requestedPane)) {
      setActivePane(requestedPane);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedPane]);

  const selectPane = (pane: string) => {
    setActivePane(pane);
    // Set this window's namespaced pane; clear the flat legacy `?tab=`.
    surfaceParam.set({ pane });
    setSurfaceParams({ tab: null });
  };

  return (
    <div className="h-full flex">
      <nav
        aria-label={navLabel}
        className="w-44 sm:w-52 shrink-0 border-r border-border overflow-y-auto py-3 px-2 space-y-4"
      >
        {paneGroups.map((group) => (
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
        ))}
      </nav>

      {fullBleed ? (
        <div className="flex-1 min-w-0 min-h-0 overflow-hidden flex flex-col">
          {banner}
          {renderPane(activePane)}
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto p-6">
            {banner}
            {renderPane(activePane)}
          </div>
        </div>
      )}
    </div>
  );
}
