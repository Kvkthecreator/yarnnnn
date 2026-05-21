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

import { useCallback, useMemo } from 'react';
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
  const { pinned, lastActive } = useSurfacePreferences();
  const { setSurface } = useDesk();
  const { userEmail, openLauncher } = useShellChrome();

  // ADR-297 D6: logo click → operator's last-active surface (macOS-
  // natural). Resolves the slug to a route via the compositor registry;
  // falls back to HOME_ROUTE if the registry isn't loaded yet or the
  // slug is unknown.
  const navigateToHome = useCallback(() => {
    const surface = composition.surfaces?.find((s) => s.slug === lastActive);
    const target = surface?.route || HOME_ROUTE;
    if (pathname !== target) router.push(target);
  }, [router, pathname, composition.surfaces, lastActive]);

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
            only). Each icon = setSurface dispatch via DeskContext (the
            canonical axiom from b5d1a1e — surface = viewport panel,
            URL is transport). */}
        {pinnedSurfaces.length > 0 && (
          <div className="flex items-center gap-0.5">
            {pinnedSurfaces.map((surface) => {
              const Icon = resolveSurfaceIcon(surface.icon_key);
              const isActive =
                surface.route &&
                (pathname === surface.route ||
                  pathname.startsWith(surface.route + '/'));
              const handleClick = () => {
                if (isKernelSurfaceSlug(surface.slug)) {
                  setSurface({ type: 'atomic', slug: surface.slug });
                }
              };
              return (
                <button
                  key={surface.slug}
                  type="button"
                  onClick={handleClick}
                  title={surface.title}
                  aria-label={surface.title}
                  aria-current={isActive ? 'page' : undefined}
                  className={cn(
                    'flex h-9 w-9 items-center justify-center rounded-md transition-colors',
                    isActive
                      ? 'bg-foreground text-background'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )}
                >
                  <Icon className="h-4 w-4" />
                </button>
              );
            })}
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
