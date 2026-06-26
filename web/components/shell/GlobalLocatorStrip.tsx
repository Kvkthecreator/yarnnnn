'use client';

/**
 * GlobalLocatorStrip — the OS "you are here" indicator (2026-06-26).
 *
 * ONE always-visible locator, mounted once in the shell chrome
 * (ShellCompositor, between the top bar and the content row). It shows the
 * FOREGROUNDED surface's location in EVERY layout (canvas, desktop multi-
 * window, mobile):
 *
 *     <SurfaceTitle> › <segment> › <segment>
 *
 * REPLACES the per-window title-bar crumb (formerly in WindowFrame). That
 * model was conditional three ways — desktop multi-window mode only, detail
 * mode only, 3 surfaces only — and was SUPPRESSED entirely in canvas mode
 * (`chromeless`, ADR-358), so the operator saw no locator at all.
 *
 * Segment SOURCE is unchanged: surfaces register their in-window position
 * per-slug via `useWindowCrumb(slug, segments)` (BreadcrumbContext). Only the
 * RENDER lives here — keyed on `foregrounded`. This is the single consumer of
 * `getCrumb` (Singular Implementation).
 *
 * NAVIGATIONAL (2026-06-26): when there are detail segments, the ROOT
 * surface-title is a clickable "back to list" link (it fires the leaf
 * segment's onClick — the surfaces register that as "clear the deep-link
 * param", i.e. return to list mode). Intermediate segments with onClick are
 * clickable too; the leaf is non-interactive (you're already there).
 *
 * SEAMLESS (2026-06-26): no border, no tinted background — the strip sits in
 * the same plane as the content below it, not as a separate bar.
 *
 * RESPONSIVE:
 *   - Desktop / tablet: full `Title › segments`, ALWAYS present (empty Desktop
 *     reads a muted "Desktop" so the height never collapses / content never
 *     jumps).
 *   - Mobile: a LEAF-ONLY back-chip ("‹ report.md") — the redundant root name
 *     is dropped (the surface's own header already names it; showing it twice
 *     wastes scarce vertical space). In list mode (no segments) the strip
 *     collapses to nothing on mobile.
 */

import { ChevronRight, ChevronLeft } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { useWindowCrumbRegistry, type BreadcrumbSegment } from '@/contexts/BreadcrumbContext';
import { useComposition } from '@/lib/compositor/useComposition';
import { useViewport } from '@/lib/shell/useViewport';
import { surfaceTitleFor } from '@/lib/compositor/surfaceTitle';

export function GlobalLocatorStrip() {
  const { foregrounded } = useSurfacePreferences();
  const { getCrumb } = useWindowCrumbRegistry();
  const { data: composition } = useComposition();
  const viewport = useViewport();

  const title = surfaceTitleFor(composition.surfaces, foregrounded ?? null);
  const isEmpty = !foregrounded;
  // Detail segments BELOW the surface name, for the foregrounded slug only.
  const crumb: BreadcrumbSegment[] = foregrounded ? getCrumb(foregrounded) : [];
  // The "back to list" action surfaces register on the leaf (clears the
  // deep-link param). Used to make the ROOT title navigational.
  const backToList = crumb.length > 0 ? crumb[crumb.length - 1].onClick : undefined;

  // ── Mobile: leaf-only back-chip. List mode → nothing (the surface header
  //    already names the surface; a root-only strip would just duplicate it).
  if (viewport.isMobile) {
    if (crumb.length === 0) return null;
    const leaf = crumb[crumb.length - 1];
    return (
      <div
        className="flex h-7 shrink-0 items-center gap-1 overflow-hidden bg-background px-3 text-xs font-medium text-foreground/80"
        aria-label="Location"
      >
        {backToList ? (
          <button
            type="button"
            onClick={() => backToList()}
            className="flex min-w-0 items-center gap-0.5 text-muted-foreground hover:text-foreground"
            title={`Back to ${title}`}
          >
            <ChevronLeft className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{leaf.label}</span>
          </button>
        ) : (
          <span className="truncate">{leaf.label}</span>
        )}
      </div>
    );
  }

  // ── Desktop / tablet: full `Title › segments`, always present.
  return (
    <div
      className={cn(
        'flex h-7 shrink-0 items-center gap-1 overflow-hidden bg-background px-3 text-xs font-medium',
        isEmpty ? 'text-muted-foreground/60' : 'text-foreground/80'
      )}
      aria-label="Location"
    >
      {backToList ? (
        // Root is navigational when drilled in — click returns to list mode.
        <button
          type="button"
          onClick={() => backToList()}
          className="truncate underline-offset-2 hover:text-foreground hover:underline"
          title={`Back to ${title}`}
        >
          {title}
        </button>
      ) : (
        <span className="truncate">{title}</span>
      )}
      {crumb.map((seg, i) => {
        const isLeaf = i === crumb.length - 1;
        return (
          <span key={`${seg.label}-${i}`} className="flex min-w-0 items-center gap-1">
            <ChevronRight className="h-3 w-3 shrink-0 opacity-40" />
            {seg.onClick && !isLeaf ? (
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
      })}
    </div>
  );
}
