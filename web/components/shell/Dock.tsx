'use client';

/**
 * Dock — ADR-297 D5.
 *
 * Persistent bottom-of-viewport row of operator-pinned surface icons.
 * Default-pinned: Feed only (D5). Operator pins more from the launcher
 * overlay (D4). Pinned-surfaces list is persisted to localStorage per
 * user (`lib/shell/surface-preferences.ts`).
 *
 * Clicking a dock icon navigates to that surface's route. The active
 * surface is highlighted by route match.
 *
 * Phase 2 implementation: icon-only display, click navigates, no
 * drag-reorder yet (would arrive in a follow-on commit if operator
 * demand surfaces). Right-click / long-press unpin is a Phase 2.1
 * enhancement; for now, unpinning happens from the launcher.
 */

import { usePathname } from 'next/navigation';
import { useMemo } from 'react';
import type { Surface } from '@/lib/compositor/types';
import { resolveSurfaceIcon } from '@/lib/shell/surface-icons';
import { useDesk } from '@/contexts/DeskContext';
import { isKernelSurfaceSlug } from '@/types/desk';
import { cn } from '@/lib/utils';

interface DockProps {
  surfaces: Surface[];
  pinned: string[];
}

export function Dock({ surfaces, pinned }: DockProps) {
  const pathname = usePathname();
  const { setSurface } = useDesk();

  // Resolve pinned slugs to Surface entries in the operator's pin order.
  // Surfaces not in the registry (e.g., stale pin from a deleted bundle)
  // are silently skipped — the registry is the source of truth.
  const surfaceBySlug = useMemo(() => {
    const map = new Map<string, Surface>();
    surfaces.forEach((s) => map.set(s.slug, s));
    return map;
  }, [surfaces]);

  const items: Surface[] = useMemo(
    () => pinned.map((slug) => surfaceBySlug.get(slug)).filter((s): s is Surface => Boolean(s)),
    [pinned, surfaceBySlug]
  );

  if (items.length === 0) return null;

  return (
    <nav
      aria-label="Pinned surfaces"
      className="pointer-events-auto fixed inset-x-0 bottom-3 z-40 flex justify-center"
    >
      <div className="flex items-center gap-1 rounded-2xl border border-border bg-background/95 px-2 py-1.5 shadow-lg backdrop-blur">
        {items.map((surface) => {
          const Icon = resolveSurfaceIcon(surface.icon_key);
          const isActive =
            pathname === surface.route ||
            pathname.startsWith(surface.route + '/');
          // ADR-297 axiom: setSurface is the canonical action. The Dock
          // dispatches surface state; the URL update is a side effect
          // managed inside DeskContext.
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
              className={cn(
                'flex h-10 w-10 items-center justify-center rounded-xl transition-colors',
                isActive
                  ? 'bg-foreground text-background'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              )}
            >
              <Icon className="h-5 w-5" />
            </button>
          );
        })}
      </div>
    </nav>
  );
}
