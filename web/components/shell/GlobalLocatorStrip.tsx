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
 *
 * ADR-442 (2026-07-11): this strip IS the SURFACE BAR — the one authority for
 * surface chrome, both halves: identity/location on the left (the crumb) and
 * the foreground surface's DECLARED whole-surface verbs on the right
 * (`useSurfaceActions` — data, never JSX; link-shaped actions render through
 * SurfaceLink for native affordances). Surface-scoped header rows inside
 * surface bodies die as their surfaces adopt (the Studio first); rows that
 * describe a selection within a surface stay in-body (ADR-442 D3).
 */

import { ChevronRight, ChevronLeft } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import {
  useWindowCrumbRegistry,
  type BreadcrumbSegment,
  type SurfaceAction,
} from '@/contexts/BreadcrumbContext';
import { useComposition } from '@/lib/compositor/useComposition';
import { useViewport } from '@/lib/shell/useViewport';
import { surfaceTitleFor } from '@/lib/compositor/surfaceTitle';
import { SurfaceLink } from '@/components/shell/SurfaceLink';

const ACTION_CLS =
  'inline-flex items-center gap-1 rounded-md border border-border px-2 py-0.5 text-[11px] text-muted-foreground hover:bg-muted/40 hover:text-foreground';

/** One declared action — the bar owns the rendering (ADR-442 D2). */
function ActionChip({ action }: { action: SurfaceAction }) {
  const Icon = action.icon;
  const body = (
    <>
      {Icon && <Icon className="h-3 w-3" />}
      {action.label}
    </>
  );
  return action.to ? (
    <SurfaceLink to={action.to} params={action.params} className={ACTION_CLS}>
      {body}
    </SurfaceLink>
  ) : (
    <button type="button" onClick={action.onClick} className={ACTION_CLS}>
      {body}
    </button>
  );
}

export function GlobalLocatorStrip() {
  const { foregrounded } = useSurfacePreferences();
  const { getCrumb, getActions, isSelfLocated } = useWindowCrumbRegistry();
  const { data: composition } = useComposition();
  const viewport = useViewport();

  // 2026-07-14: a surface that renders its OWN locator in its own chrome row
  // (Studio's workbench toolbar, Chat's lane headers) suppresses the OS strip —
  // one "you are here", never two (the native-app pattern; the strip was a
  // redundant ~28px band above a surface that already names its location).
  // Declared per-surface via useSelfLocatedSurface (no slug hardcoded here).
  if (foregrounded && isSelfLocated(foregrounded)) return null;

  const title = surfaceTitleFor(composition.surfaces, foregrounded ?? null);
  const isEmpty = !foregrounded;
  // Detail segments BELOW the surface name, for the foregrounded slug only.
  const crumb: BreadcrumbSegment[] = foregrounded ? getCrumb(foregrounded) : [];
  // The foreground surface's declared whole-surface verbs (ADR-442 D2).
  const actions: SurfaceAction[] = foregrounded ? getActions(foregrounded) : [];
  // The "back to list" action surfaces register on the leaf (clears the
  // deep-link param). Used to make the ROOT title navigational.
  const backToList = crumb.length > 0 ? crumb[crumb.length - 1].onClick : undefined;

  // ── Mobile: leaf-only back-chip. List mode → nothing (the surface header
  //    already names the surface; a root-only strip would just duplicate it).
  if (viewport.isMobile) {
    if (crumb.length === 0 && actions.length === 0) return null;
    const leaf = crumb.length > 0 ? crumb[crumb.length - 1] : null;
    return (
      <div
        className="flex h-7 shrink-0 items-center gap-1 overflow-hidden bg-background px-3 text-xs font-medium text-foreground/80"
        aria-label="Location"
      >
        {leaf &&
          (backToList ? (
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
          ))}
        {actions.length > 0 && (
          <div className="ml-auto flex shrink-0 items-center gap-1.5">
            {actions.map((a) => (
              <ActionChip key={a.id} action={a} />
            ))}
          </div>
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
      {/* The foreground surface's declared verbs — right-aligned (ADR-442). */}
      {actions.length > 0 && (
        <div className="ml-auto flex shrink-0 items-center gap-1.5 pl-3">
          {actions.map((a) => (
            <ActionChip key={a.id} action={a} />
          ))}
        </div>
      )}
    </div>
  );
}
