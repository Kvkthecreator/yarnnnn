'use client';

/**
 * TopBarSurface — ADR-297 D11 chrome surface (region: top) +
 * D12 amendment (top-center merged dock-bar).
 *
 * D12 (2026-05-21) collapsed the prior three-region top bar (brand
 * left · launcher+user-menu right) and the bottom-floating Dock into
 * a single centered top dock-bar with this left-to-right ordering:
 *
 *   brand · | · launcher trigger · | · pinned surfaces · | · user menu
 *
 * The Dock kernel surface is DELETED (see ADR-297 §D12 + kernel_surfaces.py).
 * Its responsibility (rendering pinned-surface icons + dispatching
 * setSurface on click) absorbs into this surface's body. The launcher
 * overlay still mounts in `floating-overlay`; only the *trigger button*
 * lives here, as slot #3 in the centered bar.
 *
 * Pinned-surface mechanics preserved verbatim from the deleted DockSurface:
 *   - Reads pinned slugs from useSurfacePreferences (localStorage).
 *   - Resolves each slug to a Surface entry via composition.surfaces[].
 *   - Click dispatches setSurface (canonical axiom — DeskContext owns
 *     surface identity, URL is transport).
 *   - Active surface highlighted by pathname match.
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
  const { pinned, foregrounded, isOpen, foregroundSurface, closeSurface, unpin } =
    useSurfacePreferences();
  const { setSurface } = useDesk();
  const { userEmail, openLauncher } = useShellChrome();

  // ADR-297 D13: brand-mark click navigates to the currently
  // foregrounded surface's route. If nothing is foregrounded (desktop
  // empty state), the click is a no-op — the operator is already at
  // the canonical home. Falls back to HOME_ROUTE if the registry isn't
  // loaded yet.
  const navigateToHome = useCallback(() => {
    if (!foregrounded) return; // already on desktop
    const surface = composition.surfaces?.find((s) => s.slug === foregrounded);
    const target = surface?.route || HOME_ROUTE;
    if (pathname !== target) router.push(target);
  }, [router, pathname, composition.surfaces, foregrounded]);

  // Resolve pinned slugs to Surface entries in operator's pin order
  // (D12 — same mechanic the deleted DockSurface used). Surfaces not
  // in the registry (e.g., stale pin from a deleted bundle) are silently
  // skipped — the registry is source of truth.
  const surfaceBySlug = useMemo(() => {
    const map = new Map<string, Surface>();
    (composition.surfaces || []).forEach((s) => map.set(s.slug, s));
    return map;
  }, [composition.surfaces]);

  const pinnedSurfaces: Surface[] = useMemo(
    () =>
      pinned
        .map((slug) => surfaceBySlug.get(slug))
        .filter((s): s is Surface => Boolean(s)),
    [pinned, surfaceBySlug]
  );

  // ADR-297 D13: right-click context menu state. Single slug shown at
  // a time; click-anywhere or Escape closes. Minimum-viable shape —
  // one menu item: "Close". Future v2 may add "Unpin", "Move".
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

  return (
    <header className="h-14 border-b border-border bg-background flex items-center justify-center px-4 shrink-0">
      {/* Centered merged dock-bar (D12). Single horizontal strip with
          four slot groups, separated by subtle vertical dividers. */}
      <nav
        aria-label="Workspace dock"
        className="flex items-center gap-1.5"
      >
        {/* Slot 1 — Brand mark (yarnnn circle, leftmost like macOS Apple
            menu / Finder anchor). Clickable → last-active home (D6). */}
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

        {/* Slot 2 — Launcher trigger (four-box icon; opens the full
            surface-index overlay). Per D12 this is the leftmost
            interactive Dock affordance after the brand mark, mirroring
            macOS Finder's leftmost-anchor position. */}
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

        {/* Slot 3 — Pinned surfaces row (inherits D5 default-pinned: Feed
            only). D13 click semantics:
              - Click an open surface → foreground it (no remount).
              - Click a not-yet-open surface → openSurface + foreground
                in one action (foregroundSurface combines both).
              - Right-click → context menu with "Close" affordance.
            Open-state dot indicator shown below icons whose slug is in
            the open-surfaces registry (macOS Dock convention). */}
        {pinnedSurfaces.length > 0 && (
          <div className="flex items-center gap-0.5">
            {pinnedSurfaces.map((surface) => {
              const Icon = resolveSurfaceIcon(surface.icon_key);
              const isForegrounded = foregrounded === surface.slug;
              const surfaceIsOpen = isOpen(surface.slug);
              const handleClick = () => {
                if (isKernelSurfaceSlug(surface.slug)) {
                  // D13: foregroundSurface opens + foregrounds in one
                  // action. The legacy setSurface (DeskContext) is
                  // kept in sync below for any consumers that still
                  // read DeskState.surface directly.
                  foregroundSurface(surface.slug);
                  setSurface({ type: 'atomic', slug: surface.slug });
                }
              };
              const handleContextMenu = (e: React.MouseEvent) => {
                e.preventDefault();
                if (surfaceIsOpen) {
                  setContextMenu({ slug: surface.slug, x: e.clientX, y: e.clientY });
                }
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
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </button>
                  {/* Open-state indicator dot (D13). macOS Dock
                      convention: small dot under icons whose
                      corresponding app is currently running. */}
                  {surfaceIsOpen && (
                    <div
                      aria-hidden
                      className={cn(
                        'absolute -bottom-0.5 h-1 w-1 rounded-full',
                        isForegrounded ? 'bg-background' : 'bg-foreground/70'
                      )}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* D13 right-click context menu — shown when an open pinned
            surface is right-clicked. Minimum-viable shape: one item
            ("Close"). Future v2: "Unpin", "Move", etc. */}
        {contextMenu && (
          <div
            ref={menuRef}
            role="menu"
            aria-label={`Surface actions for ${contextMenu.slug}`}
            style={{ top: contextMenu.y, left: contextMenu.x }}
            className="fixed z-50 min-w-[140px] rounded-md border border-border bg-background shadow-lg py-1"
          >
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                closeSurface(contextMenu.slug);
                setContextMenu(null);
              }}
              className="block w-full px-3 py-1.5 text-left text-xs text-foreground hover:bg-muted transition-colors"
            >
              Close
            </button>
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                unpin(contextMenu.slug);
                setContextMenu(null);
              }}
              className="block w-full px-3 py-1.5 text-left text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              Unpin from dock
            </button>
          </div>
        )}

        {pinnedSurfaces.length > 0 && <Divider />}

        {/* Slot 4 — User menu (rightmost — preserved from pre-D12
            top-right placement; only its parent container changed). */}
        <UserMenu email={userEmail} />
      </nav>
    </header>
  );
}

/**
 * Subtle vertical divider between dock-bar slot groups. Sized to match
 * the 36px (h-9) icon row with a small inset.
 */
function Divider() {
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      className="h-6 w-px bg-border/60"
    />
  );
}
