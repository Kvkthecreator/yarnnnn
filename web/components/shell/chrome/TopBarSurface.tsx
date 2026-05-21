'use client';

/**
 * TopBarSurface — ADR-297 D11 chrome surface (region: top) +
 * D12 amendment (top-center merged dock-bar) +
 * D13 (open-state dots + click foregrounds) +
 * D14 (Dock = kept ∪ open; pin reframed as Keep-in-Dock).
 *
 * Left-to-right ordering:
 *
 *   brand · | · launcher trigger · | · Dock icons · | · user menu
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
 * Click semantics (any Dock icon, regardless of kept/open):
 *   - If foregrounded     — no-op (already visible)
 *   - If open + not-foreground — foreground it
 *   - If not open         — open + foreground (foregroundSurface)
 *
 * Right-click menus (reshaped by D14):
 *   - Open + Kept       — Close / Remove from Dock
 *   - Open + Not-Kept   — Close / Keep in Dock
 *   - Kept + Not-Open   — Open / Remove from Dock
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { LayoutGrid } from 'lucide-react';
import { useComposition } from '@/lib/compositor/useComposition';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { resolveSurfaceIcon } from '@/lib/shell/surface-icons';
import { useDesk } from '@/contexts/DeskContext';
import { isKernelSurfaceSlug } from '@/types/desk';
import { HOME_ROUTE } from '@/lib/routes';
import { UserMenu } from '../UserMenu';
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
    isKept,
    isOpen,
    keep,
    release,
    foregroundSurface,
    closeSurface,
  } = useSurfacePreferences();
  const { setSurface } = useDesk();
  const { userEmail, openLauncher } = useShellChrome();

  // D13: brand-mark click navigates to the foregrounded surface's
  // route. If nothing is foregrounded (desktop empty state), the click
  // is a no-op — the operator is already at the canonical home.
  const navigateToHome = useCallback(() => {
    if (!foregrounded) return;
    const surface = composition.surfaces?.find((s) => s.slug === foregrounded);
    const target = surface?.route || HOME_ROUTE;
    if (pathname !== target) router.push(target);
  }, [router, pathname, composition.surfaces, foregrounded]);

  // Resolve composition.surfaces[] to a slug → Surface map.
  const surfaceBySlug = useMemo(() => {
    const map = new Map<string, Surface>();
    (composition.surfaces || []).forEach((s) => map.set(s.slug, s));
    return map;
  }, [composition.surfaces]);

  // D14: compute the two Dock segments — kept-in-order, then
  // open-but-not-kept in open-order. Unknown slugs (e.g. stale entries
  // for a deleted bundle) are silently skipped.
  const keptSurfaces: Surface[] = useMemo(
    () =>
      kept
        .map((slug) => surfaceBySlug.get(slug))
        .filter((s): s is Surface => Boolean(s)),
    [kept, surfaceBySlug]
  );

  const openOnlySurfaces: Surface[] = useMemo(
    () =>
      open
        .filter((slug) => !kept.includes(slug))
        .map((slug) => surfaceBySlug.get(slug))
        .filter((s): s is Surface => Boolean(s)),
    [open, kept, surfaceBySlug]
  );

  // D13: right-click context menu state. Single slug shown at a time;
  // click-anywhere or Escape closes.
  const [contextMenu, setContextMenu] = useState<
    { slug: string; x: number; y: number } | null
  >(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!contextMenu) return;
    const close = (e: MouseEvent) => {
      if (menuRef.current && menuRef.current.contains(e.target as Node)) return;
      setContextMenu(null);
    };
    const closeOnEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setContextMenu(null);
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', closeOnEsc);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', closeOnEsc);
    };
  }, [contextMenu]);

  // Render helper for one Dock-row icon (single source of truth for
  // both kept and open-only segments).
  const renderDockIcon = (surface: Surface) => {
    const Icon = resolveSurfaceIcon(surface.icon_key);
    const isForegrounded = foregrounded === surface.slug;
    const surfaceIsOpen = isOpen(surface.slug);
    const surfaceIsKept = isKept(surface.slug);

    const handleClick = () => {
      if (isKernelSurfaceSlug(surface.slug)) {
        foregroundSurface(surface.slug);
        // Keep DeskContext.surface in sync for any consumer still
        // reading the legacy DeskState.
        setSurface({ type: 'atomic', slug: surface.slug });
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
        {/* D13 open-state indicator dot (macOS Dock convention). */}
        {surfaceIsOpen && (
          <div
            aria-hidden
            className={cn(
              'absolute -bottom-0.5 h-1 w-1 rounded-full',
              isForegrounded ? 'bg-background' : 'bg-foreground/70'
            )}
          />
        )}
        {/* Subtle visual differentiation for kept-not-open vs the kept-
            and-open: dot below only when open; no badge needed for
            kept-not-open beyond the muted color. */}
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
          if (isKernelSurfaceSlug(contextMenu.slug)) {
            foregroundSurface(contextMenu.slug);
            setSurface({ type: 'atomic', slug: contextMenu.slug });
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
  }, [contextMenu, isOpen, isKept, closeSurface, release, keep, foregroundSurface, setSurface]);

  const hasAnyDockEntries = keptSurfaces.length > 0 || openOnlySurfaces.length > 0;

  return (
    <header className="h-14 border-b border-border bg-background flex items-center justify-center px-4 shrink-0">
      <nav aria-label="Workspace dock" className="flex items-center gap-1.5">
        {/* Slot 1 — Brand mark (yarnnn circle). */}
        <button
          onClick={navigateToHome}
          aria-label="Go to last-active surface"
          title="Home (last-active surface)"
          className="flex h-9 w-9 items-center justify-center rounded-md hover:opacity-80 transition-opacity"
        >
          <img
            src="/assets/logos/circleonly_yarnnn_1.svg"
            alt="yarnnn"
            className="h-7 w-7"
          />
        </button>

        <Divider />

        {/* Slot 2 — Launcher trigger. */}
        <button
          type="button"
          onClick={openLauncher}
          aria-label="Open surface launcher"
          title="Open surface launcher"
          className="flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <LayoutGrid className="h-4 w-4" />
        </button>

        <Divider />

        {/* Slot 3 — Dock icons: kept set, then (if any) an inner divider,
            then open-but-not-kept set. macOS convention. */}
        {hasAnyDockEntries && (
          <div className="flex items-center gap-0.5">
            {keptSurfaces.map(renderDockIcon)}
            {keptSurfaces.length > 0 && openOnlySurfaces.length > 0 && (
              <div
                aria-hidden
                role="separator"
                aria-orientation="vertical"
                className="mx-1 h-4 w-px bg-border/40"
              />
            )}
            {openOnlySurfaces.map(renderDockIcon)}
          </div>
        )}

        {hasAnyDockEntries && <Divider />}

        {/* Slot 4 — User menu. */}
        <UserMenu email={userEmail} />
      </nav>

      {/* D13 + D14 right-click context menu. */}
      {contextMenu && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={`Surface actions for ${contextMenu.slug}`}
          style={{ top: contextMenu.y, left: contextMenu.x }}
          className="fixed z-50 min-w-[160px] rounded-md border border-border bg-background shadow-lg py-1"
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
  );
}

function Divider() {
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      className="h-6 w-px bg-border/60"
    />
  );
}
