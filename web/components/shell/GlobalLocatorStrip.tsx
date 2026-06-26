'use client';

/**
 * GlobalLocatorStrip — the OS "you are here" indicator (2026-06-26).
 *
 * ONE always-visible locator strip, mounted once in the shell chrome
 * (ShellCompositor, between the top bar and the content row). It shows the
 * FOREGROUNDED surface's location in EVERY layout (canvas, desktop multi-
 * window, mobile) and ALWAYS (list AND detail mode):
 *
 *     <SurfaceTitle> › <segment> › <segment>
 *
 * REPLACES the per-window title-bar crumb (formerly in WindowFrame). That
 * model was conditional three ways — only in desktop multi-window mode
 * (WindowFrame had a title bar), only in detail mode (segments registered),
 * and on 3 surfaces — and was SUPPRESSED entirely in canvas mode
 * (`chromeless`, ADR-358), so the operator saw no locator at all. A locator
 * that hides most of the time is more confusing than none; the operator
 * chose one global, unconditional strip (the macOS menu-bar model: the
 * active app + its location, always shown).
 *
 * Segment SOURCE is unchanged: surfaces still register their in-window
 * position per-slug via `useWindowCrumb(slug, segments)` (BreadcrumbContext).
 * Only the RENDER moves here — keyed on `foregrounded`, not per-window. This
 * is the single consumer of `getCrumb` (Singular Implementation).
 *
 * Empty Desktop (nothing foregrounded): the strip stays present and reads a
 * muted "Desktop" — the height never collapses, so the content below never
 * jumps (macOS Finder shows "Finder" when nothing else is active).
 *
 * Mobile / narrow viewports: intermediate segments collapse to a non-
 * clickable ellipsis, keeping only the leaf — the same precedent the per-
 * window crumb used (the strip is a locator, not a navigator; in-body back
 * affordances carry "go back" on small screens).
 */

import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { useWindowCrumbRegistry, type BreadcrumbSegment } from '@/contexts/BreadcrumbContext';
import { useComposition } from '@/lib/compositor/useComposition';
import { useViewport } from '@/lib/shell/useViewport';
import { surfaceTitleFor } from '@/lib/compositor/surfaceTitle';

// Below this viewport width intermediate crumb segments collapse to the leaf
// (ellipsis prefix). Mirrors WindowFrame's former TITLE_CRUMB_COLLAPSE_PX.
const STRIP_CRUMB_COLLAPSE_PX = 420;

export function GlobalLocatorStrip() {
  const { foregrounded } = useSurfacePreferences();
  const { getCrumb } = useWindowCrumbRegistry();
  const { data: composition } = useComposition();
  const viewport = useViewport();

  const title = surfaceTitleFor(composition.surfaces, foregrounded ?? null);
  const isEmpty = !foregrounded;
  // Detail segments BELOW the surface name, for the foregrounded slug only.
  const crumb: BreadcrumbSegment[] = foregrounded ? getCrumb(foregrounded) : [];

  return (
    <div
      className={cn(
        'flex h-7 shrink-0 items-center gap-1 overflow-hidden border-b border-border bg-muted/20 px-3 text-xs font-medium',
        isEmpty ? 'text-muted-foreground/60' : 'text-foreground/80'
      )}
      aria-label="Location"
    >
      <span className="truncate">{title}</span>
      {crumb.length > 0 && (() => {
        // Collapse on narrow viewports: keep the LEAF only, mark the elision
        // with a non-clickable ellipsis crumb.
        const collapsed = viewport.width < STRIP_CRUMB_COLLAPSE_PX;
        const shown: (BreadcrumbSegment | { ellipsis: true })[] =
          collapsed && crumb.length > 1
            ? [{ ellipsis: true }, crumb[crumb.length - 1]]
            : crumb;
        return shown.map((seg, i) => {
          const isLeaf = i === shown.length - 1;
          const key = 'ellipsis' in seg ? `ell-${i}` : `${seg.label}-${i}`;
          return (
            <span key={key} className="flex min-w-0 items-center gap-1">
              <ChevronRight className="h-3 w-3 shrink-0 opacity-40" />
              {'ellipsis' in seg ? (
                <span className="opacity-50">…</span>
              ) : seg.onClick && !isLeaf ? (
                <button
                  type="button"
                  onClick={() => seg.onClick!()}
                  className="truncate underline-offset-2 hover:text-foreground hover:underline"
                  title={`Back to ${seg.label}`}
                >
                  {seg.label}
                </button>
              ) : (
                <span className="truncate">{seg.label}</span>
              )}
            </span>
          );
        });
      })()}
    </div>
  );
}
