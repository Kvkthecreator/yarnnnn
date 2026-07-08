'use client';

/**
 * TopBarSurface — ADR-297 D11 chrome surface (region: top) +
 * D12 (top-center merged dock-bar — superseded by D19.5) +
 * D13 (open-state dots + click foregrounds) +
 * D14 (Dock = kept ∪ open; pin reframed as Keep-in-Dock) +
 * D19.5 (2026-05-22): three-region macOS-faithful layout.
 *
 * D19.5 region structure (left → right):
 *
 *   [ Left:  Pacifico "yarnnn" wordmark ] [ Center: Launcher · Dock icons ] [ Right: UserMenu ]
 *
 * Pre-D19.5 the header was a single centered cluster (D12 merged dock-
 * bar). Operator-felt conflation: brand, launcher, dock, and account
 * affordance all lived in one row with dividers between, which read
 * as "navigation chrome" but not as a structured top bar. D19.5
 * splits into three macOS-faithful regions:
 *
 *   - LEFT: brand mark. Pacifico wordmark "yarnnn" (font-brand class,
 *     same brand mark as Feed surface internal logo + marketing site).
 *     Click → /desktop (HOME_ROUTE). macOS-equivalent: Apple logo top-
 *     left. shrink-0 + fixed width.
 *   - CENTER: Dock cluster. Launcher trigger pinned at the LEFTMOST
 *     position of the cluster (operator decision Q2 — Launcher is the
 *     "open more surfaces" affordance, sits with the surface icons,
 *     not standalone). Dock icons follow in kept-then-open order with
 *     subtle inner divider. flex-1 min-w-0 lets the cluster claim
 *     available width and overflow-x scroll on mobile.
 *   - RIGHT: UserMenu (initials avatar dropdown). Account/settings
 *     affordance per D19.4. shrink-0 + fixed width.
 *
 * D14 Dock contents: the UNION of kept ∪ open surfaces. Kept surfaces
 * (the macOS "Keep in Dock" semantic) appear in their kept-order. Open
 * surfaces that are NOT kept appear after the kept set, in open-order,
 * separated by a subtle inner divider. macOS Dock convention.
 *
 * Icon appearance by combined state:
 *   - Kept + Open      — solid icon + indicator dot (persists across
 *                        sessions; foregrounding highlights it)
 *   - Open + Not-Kept  — solid icon + indicator dot, separated from the
 *                        kept set by a divider, disappears on close
 *   - Kept + Not-Open  — muted/gray icon, no dot, persists. Click opens.
 *
 * Click semantics (any Dock icon, regardless of kept/open) — extended
 * by D19.3 (minimize-to-Dock semantics):
 *   - Not open                 — open + foreground (foregroundSurface)
 *   - Minimized                — restore (foregroundSurface clears minimized + raises)
 *   - Open + not-foreground    — raise to foreground (raiseWindow)
 *   - Open + foreground        — minimize (minimizeWindow) — macOS Dock-click-on-active-app
 *
 * Right-click menus (reshaped by D14):
 *   - Open + Kept       — Close / Remove from Dock
 *   - Open + Not-Kept   — Close / Keep in Dock
 *   - Kept + Not-Open   — Open / Remove from Dock
 */

import { useCallback, useMemo, useRef, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { LayoutGrid } from 'lucide-react';
import { useComposition } from '@/lib/compositor/useComposition';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { resolveSurfaceIcon } from '@/lib/shell/surface-icons';
import { Z_POPOVER } from '@/lib/shell/z-tiers';
import { usePopoverDismissal } from '@/lib/shell/usePopoverDismissal';
import { isKernelSurfaceSlug } from '@/types/desk';
import { HOME_ROUTE } from '@/lib/routes';
import { UserMenu } from '../UserMenu';
import { AttentionCenter } from '../AttentionCenter';
import { useShellChrome } from '../ShellChromeContext';
import type { Surface } from '@/lib/compositor/types';
import { cn } from '@/lib/utils';

export function TopBarSurface() {
  const router = useRouter();
  const pathname = usePathname();
  const { data: composition } = useComposition();
  const {
    kept,
    open,
    foregrounded,
    windowStates,
    isKept,
    isOpen,
    keep,
    release,
    foregroundSurface,
    closeSurface,
    raiseWindow,
    minimizeWindow,
  } = useSurfacePreferences();
  const { userEmail, openLauncher } = useShellChrome();

  // D17 (2026-05-22): brand-mark click navigates to /desktop (the
  // authenticated Desktop layer) — the macOS "click the wallpaper /
  // show desktop" equivalent. Pre-D17 (D6) this navigated to the
  // foregrounded surface's route; that conflicted with the D17
  // Desktop ratification (operator should be able to return to
  // Desktop regardless of which window is foregrounded).
  //
  // The foregrounded window stays mounted in the registry — when
  // operator clicks its Dock icon they're back to it instantly per
  // D15 click-to-foreground. The brand mark is for "show me the
  // Desktop layer."
  const navigateToHome = useCallback(() => {
    if (pathname !== HOME_ROUTE) router.push(HOME_ROUTE);
  }, [router, pathname]);

  // Resolve composition.surfaces[] to a slug → Surface map.
  const surfaceBySlug = useMemo(() => {
    const map = new Map<string, Surface>();
    (composition.surfaces || []).forEach((s) => map.set(s.slug, s));
    return map;
  }, [composition.surfaces]);

  // Home is the fixed anchor slot (2026-06-04). It renders as a
  // dedicated, un-releasable Dock entry pinned immediately after the
  // Launcher — the macOS Finder analog (always-leftmost, can't be
  // removed). Per ADR-312 the Home is the most important content surface
  // (the operation, rendered); it earns a permanent one-tap affordance
  // on every screen size, independent of the mutable kept/open registry.
  // It is excluded from the kept/open segments below so it never
  // double-renders.
  const HOME_SLUG = 'home';
  const homeSurface = surfaceBySlug.get(HOME_SLUG) ?? null;

  // D14: compute the two Dock segments — kept-in-order, then
  // open-but-not-kept in open-order. Unknown slugs (e.g. stale entries
  // for a deleted bundle) are silently skipped. Home is filtered out of
  // both — its render is owned by the fixed anchor slot, not the
  // kept/open registry.
  // ADR-340 P2: pane-grade surfaces (pane_of set) never render as Dock
  // icons — they're sidebar panes inside their parent's window, not
  // windows. Stale persisted kept/open entries from before the System
  // Settings fold are filtered the same way the viewport filters them.
  // 2026-07-08: chrome-fronted surfaces (Notifications → the AttentionCenter
  // bell) are filtered the same way — their door is dedicated top-bar chrome,
  // so a Dock tile would be a second door for one thing. Without this, opening
  // the window drops the slug into `open` (D14 kept ∪ open) and paints a
  // redundant tile; the bell carries the foregrounded highlight instead.
  const isDockable = (s: Surface | undefined): s is Surface =>
    Boolean(s) && !s!.pane_of && !s!.chrome_fronted;
  const keptSurfaces: Surface[] = useMemo(
    () =>
      kept
        .filter((slug) => slug !== HOME_SLUG)
        .map((slug) => surfaceBySlug.get(slug))
        .filter(isDockable),
    [kept, surfaceBySlug]
  );

  const openOnlySurfaces: Surface[] = useMemo(
    () =>
      open
        .filter((slug) => !kept.includes(slug) && slug !== HOME_SLUG)
        .map((slug) => surfaceBySlug.get(slug))
        .filter(isDockable),
    [open, kept, surfaceBySlug]
  );

  // D13: right-click context menu state. Single slug shown at a time;
  // click-anywhere or Escape closes.
  const [contextMenu, setContextMenu] = useState<
    { slug: string; x: number; y: number } | null
  >(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Click-outside + Escape close (shared dismissal contract, 2026-07-01).
  usePopoverDismissal(menuRef, contextMenu !== null, () => setContextMenu(null));

  // Render helper for one Dock-row icon (single source of truth for
  // both kept and open-only segments).
  const renderDockIcon = (surface: Surface) => {
    const Icon = resolveSurfaceIcon(surface.icon_key);
    const isForegrounded = foregrounded === surface.slug;
    const surfaceIsOpen = isOpen(surface.slug);
    const surfaceIsKept = isKept(surface.slug);

    const handleClick = () => {
      if (!isKernelSurfaceSlug(surface.slug)) return;
      // Dock click semantics (D15 + D19.3):
      //   - Not open               → open + foreground (cap-checked)
      //   - Minimized              → restore (foregroundSurface clears
      //                              minimized + raises + foregrounds)
      //   - Open + not-foreground  → raise to foreground
      //   - Open + foreground      → minimize (macOS Dock-click-on-
      //                              active-app sends to Dock)
      //
      // D19.2 (2026-05-22): URL is not rewritten on Dock click —
      // informational add-on, not a tracker of the foregrounded
      // window. D19.3 (2026-05-22): the "send to background" verb
      // hideForegrounded was replaced by real minimizeWindow on the
      // foregrounded-click branch; same Dock-click-on-active-app
      // gesture but now structurally hides the window (the
      // operator-observed "yellow button doesn't work" bug shared
      // the same root cause).
      const isMinimized = !!windowStates[surface.slug]?.minimized;
      if (!surfaceIsOpen) {
        // ADR-369 follow-on: opening always succeeds — if at the window
        // cap, foregroundSurface auto-recedes the least-recently-used
        // window (LRU), never refuses.
        foregroundSurface(surface.slug);
      } else if (isMinimized) {
        foregroundSurface(surface.slug); // restore + raise + foreground
      } else if (isForegrounded) {
        minimizeWindow(surface.slug);
      } else {
        raiseWindow(surface.slug);
      }
    };
    const handleContextMenu = (e: React.MouseEvent) => {
      e.preventDefault();
      setContextMenu({ slug: surface.slug, x: e.clientX, y: e.clientY });
    };

    return (
      <div key={surface.slug} className="relative flex flex-col items-center">
        <button
          type="button"
          onClick={handleClick}
          onContextMenu={handleContextMenu}
          title={surface.title}
          aria-label={surface.title}
          aria-current={isForegrounded ? 'page' : undefined}
          className={cn(
            'flex h-9 w-9 items-center justify-center rounded-md transition-colors',
            isForegrounded
              ? 'bg-foreground text-background'
              : surfaceIsOpen
              ? 'text-muted-foreground hover:bg-muted hover:text-foreground'
              : // Kept + not-open: muted/gray launcher anchor.
                'text-muted-foreground/50 hover:bg-muted hover:text-foreground'
          )}
        >
          <Icon className="h-4 w-4" />
        </button>
        {/* Open/foreground state is carried by the icon button's own fill
            (foregrounded → solid; kept-not-open → muted) — the prior tiny
            open-state dot below the icon was redundant + read as visual noise,
            removed per operator direction. */}
      </div>
    );
  };

  // Render the fixed Home anchor (2026-06-04). Same click semantics as a
  // Dock icon (open / foreground / minimize / restore), but: NO right-
  // click context menu — Home cannot be removed from the Dock (the
  // Finder analog). It is always present, regardless of kept/open state,
  // which is why it lives outside the kept/open registry. On mobile this
  // is the single one-tap path to the Home composition surface (the
  // wordmark brand mark is hidden < sm).
  const renderHomeAnchor = (surface: Surface) => {
    const Icon = resolveSurfaceIcon(surface.icon_key);
    const isForegrounded = foregrounded === surface.slug;
    const surfaceIsOpen = isOpen(surface.slug);

    const handleClick = () => {
      if (!isKernelSurfaceSlug(surface.slug)) return;
      const isMinimized = !!windowStates[surface.slug]?.minimized;
      if (!surfaceIsOpen) {
        foregroundSurface(surface.slug);
      } else if (isMinimized) {
        foregroundSurface(surface.slug);
      } else if (isForegrounded) {
        minimizeWindow(surface.slug);
      } else {
        raiseWindow(surface.slug);
      }
    };

    return (
      <div key={surface.slug} className="relative flex shrink-0 flex-col items-center">
        <button
          type="button"
          onClick={handleClick}
          title={surface.title}
          aria-label={surface.title}
          aria-current={isForegrounded ? 'page' : undefined}
          className={cn(
            'flex h-9 w-9 items-center justify-center rounded-md transition-colors',
            isForegrounded
              ? 'bg-foreground text-background'
              : // Anchor is never "muted/gray not-open" like a kept-not-open
                // surface — it's the permanent home affordance, so it stays
                // at full foreground tint whether open or not.
                'text-foreground hover:bg-muted'
          )}
        >
          <Icon className="h-4 w-4" />
        </button>
        {/* Open-state dot removed — the icon fill already carries the state. */}
      </div>
    );
  };

  // Determine context-menu items based on the right-clicked slug's
  // combined kept/open state. Exhaustive over three (open, kept) cells
  // — the fourth (not-kept, not-open) is unreachable because the icon
  // wouldn't be in the Dock at all.
  const contextMenuItems = useMemo(() => {
    if (!contextMenu) return [];
    const surfaceIsOpen = isOpen(contextMenu.slug);
    const surfaceIsKept = isKept(contextMenu.slug);
    const items: Array<{ label: string; action: () => void; tone?: 'default' | 'muted' }> = [];

    if (surfaceIsOpen) {
      items.push({
        label: 'Close',
        action: () => closeSurface(contextMenu.slug),
      });
    } else {
      items.push({
        label: 'Open',
        action: () => {
          // D19.2: foregroundSurface is the singular action; URL is
          // informational add-on, not rewritten on summon.
          if (isKernelSurfaceSlug(contextMenu.slug)) {
            foregroundSurface(contextMenu.slug);
          }
        },
      });
    }

    if (surfaceIsKept) {
      items.push({
        label: 'Remove from Dock',
        action: () => release(contextMenu.slug),
        tone: 'muted',
      });
    } else {
      items.push({
        label: 'Keep in Dock',
        action: () => keep(contextMenu.slug),
        tone: 'muted',
      });
    }

    return items;
  }, [contextMenu, isOpen, isKept, closeSurface, release, keep, foregroundSurface]);

  const hasAnyDockEntries = keptSurfaces.length > 0 || openOnlySurfaces.length > 0;

  return (
    <>
    {/* D19.5 (2026-05-22) — TopBar three-region layout. Pre-D19.5 the
        header was a single centered nav cluster (D12 merged dock-bar
        shape). Operator request KVK 2026-05-22: split into macOS-
        faithful Left | Center | Right regions.
          Left   : Pacifico "yarnnn" wordmark (brand mark, click → /desktop)
          Center : Launcher trigger (fixed left of the cluster) + Dock icons
                   (kept ∪ open). macOS-Dock-shaped center column.
          Right  : UserMenu (initials avatar dropdown).
        Mobile: Center region overflow-x scrolls when icons exceed width;
        Left + Right stay fixed-width siblings of the scrollable Center. */}
    <header className="h-14 border-b border-border bg-background flex items-center justify-between gap-2 px-4 shrink-0">
      {/* Left region — Pacifico wordmark brand mark. macOS convention
          puts the Apple logo top-left; YARNNN puts its brand here too,
          but uses the Pacifico wordmark (same as Feed surface internal
          logo + marketing site) for brand recognition vs Apple's
          mature-OS minimal icon. Click → /desktop (HOME_ROUTE).
          shrink-0 + fixed width so it doesn't compress when the
          center Dock has many icons.

          2026-06-03: hidden on phones (< sm). The wordmark eats the
          fixed-width real estate the center Dock needs on narrow
          screens — the Dock could overflow-scroll behind it. The
          Desktop is still reachable on mobile via the Dock + Launcher;
          the brand mark is a desktop-class affordance. */}
      <div className="hidden sm:flex shrink-0 items-center">
        <button
          onClick={navigateToHome}
          aria-label="yarnnn — go to Desktop"
          title="Desktop"
          className="rounded-md px-2 py-1 transition-opacity hover:opacity-70"
        >
          <span className="font-brand text-2xl text-foreground leading-none">
            yarnnn
          </span>
        </button>
      </div>

      {/* Center region — Dock (Launcher + surface icons). The Launcher
          trigger is fixed at the leftmost position of the Center
          cluster (per operator decision Q2). Dock icons follow:
          kept set, optional inner divider, then open-but-not-kept set.
          macOS Dock convention.
          flex-1 min-w-0 lets the region claim available width and
          overflow-scroll horizontally when icons exceed it (mobile). */}
      <nav
        aria-label="Workspace dock"
        // D19.5.1 (2026-05-22): scrollbar visually hidden. Pacifico
        // wordmark widened the LEFT region just enough that the
        // CENTER's overflow-x-auto rendered a 1px scrollbar even at
        // common viewports. macOS Dock never shows a scrollbar; scroll
        // capability preserved for mobile (when icon count overflows
        // available width) but the indicator is suppressed via webkit
        // + firefox + ms scrollbar-width: none.
        className="flex flex-1 min-w-0 items-center justify-center gap-0.5 overflow-x-auto [&::-webkit-scrollbar]:hidden [scrollbar-width:none]"
      >
        <button
          type="button"
          onClick={openLauncher}
          aria-label="Open surface launcher"
          title="Open surface launcher"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <LayoutGrid className="h-4 w-4" />
        </button>

        {/* Fixed Home anchor — pinned immediately after the Launcher,
            always present, un-releasable (ADR-312: Home is the primary
            content surface). The macOS Finder analog. */}
        {homeSurface && renderHomeAnchor(homeSurface)}

        {hasAnyDockEntries && (
          <>
            <div
              aria-hidden
              role="separator"
              aria-orientation="vertical"
              className="mx-1 h-4 w-px shrink-0 bg-border/40"
            />
            {keptSurfaces.map(renderDockIcon)}
            {keptSurfaces.length > 0 && openOnlySurfaces.length > 0 && (
              <div
                aria-hidden
                role="separator"
                aria-orientation="vertical"
                className="mx-1 h-4 w-px shrink-0 bg-border/40"
              />
            )}
            {openOnlySurfaces.map(renderDockIcon)}
          </>
        )}
      </nav>

      {/* Right region — AttentionCenter (ADR-340 D3 — the Notification Center
          analog: EVENTS demanding the operator) + UserMenu. shrink-0 + fixed
          width pinned to viewport right edge.
          2026-07-08 (operator ruling): the SystemStatusCluster (Budget +
          Connections standing-state chips) is RETIRED — both fold into the
          UserMenu (Budget = a usage row, Connectors = a link), where the
          ambient workspace context already lives (ADR-412 D6). The top bar
          keeps only the load-bearing items: Dock, bell, avatar. */}
      <div className="flex shrink-0 items-center gap-2">
        <AttentionCenter />
        <UserMenu email={userEmail} />
      </div>

      {/* D13 + D14 right-click context menu. */}
      {contextMenu && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={`Surface actions for ${contextMenu.slug}`}
          style={{ top: contextMenu.y, left: contextMenu.x, zIndex: Z_POPOVER }}
          className="fixed min-w-[160px] rounded-md border border-border bg-background shadow-lg py-1"
        >
          {contextMenuItems.map((item, i) => (
            <button
              key={i}
              type="button"
              role="menuitem"
              onClick={() => {
                item.action();
                setContextMenu(null);
              }}
              className={cn(
                'block w-full px-3 py-1.5 text-left text-xs transition-colors hover:bg-muted',
                item.tone === 'muted'
                  ? 'text-muted-foreground hover:text-foreground'
                  : 'text-foreground'
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </header>
    </>
  );
}

