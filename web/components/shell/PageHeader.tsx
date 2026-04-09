'use client';

/**
 * PageHeader — Breadcrumb chrome strip (ADR-167 v5).
 *
 * The page header is PURE chrome. One job: show where you are. It does not
 * carry the page title, metadata, or action buttons — those live inside the
 * surface content as a `<SurfaceIdentityHeader />` block, where they belong
 * alongside the content they describe.
 *
 * Why chrome-only. Earlier amendments (v2/v3/v4) kept trying to put the page
 * title and its metadata inside PageHeader, which created two problems:
 *
 *   1. Duplicate titles. Pages whose content already renders an H1 (e.g.
 *      `/work?task=daily-update` whose output iframe starts with
 *      `<h1>Daily Workspace Update — April 8, 2026</h1>`) ended up with
 *      PageHeader's promoted title stacked against the content's H1 —
 *      two headers fighting to be "the page title."
 *   2. Metadata in the wrong place. Task metadata (status, schedule, next run)
 *      and actions (Run / Pause / Edit via chat) describe the task, not the
 *      navigation. Putting them up in the chrome strip separated them from
 *      the task content visually. v5 moves them down into WorkDetail where
 *      they sit directly above the task's content — one cohesive "page
 *      identity block" that owns the real H1.
 *
 * v5 invariants:
 *   - Breadcrumb always present with the same muted tone across all states.
 *   - No title promotion — the last segment is chrome, not a bold h1.
 *   - No subtitle or actions props — those moved to SurfaceIdentityHeader.
 *   - List pages render `defaultLabel` as a single-segment breadcrumb.
 *
 * Reads from BreadcrumbContext (commit b033513) — pages still call
 * `setBreadcrumb()` with the same segment shape.
 */

import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { ChevronRight } from 'lucide-react';
import Link from 'next/link';

interface PageHeaderProps {
  /**
   * Fallback label rendered when BreadcrumbContext has no segments.
   * Used by list-mode pages whose breadcrumb is the surface name only.
   * Detail-mode pages set the full path via `setBreadcrumb()` and ignore
   * this prop.
   */
  defaultLabel?: string;
}

export function PageHeader({ defaultLabel }: PageHeaderProps) {
  const { segments } = useBreadcrumb();

  const trail = segments.length > 0
    ? segments
    : (defaultLabel ? [{ label: defaultLabel, href: undefined, onClick: undefined }] : []);

  if (trail.length === 0) return null;

  return (
    <nav
      aria-label="Breadcrumb"
      className="shrink-0 flex items-center gap-1.5 px-6 py-2 text-xs text-muted-foreground bg-background border-b border-border/60"
    >
      {trail.map((seg, i) => {
        const isLast = i === trail.length - 1;
        return (
          <div key={`${seg.label}-${i}`} className="flex items-center gap-1.5 min-w-0">
            {i > 0 && <ChevronRight className="w-3 h-3 text-muted-foreground/30 shrink-0" />}
            {!isLast && seg.href ? (
              <Link
                href={seg.href}
                className="hover:text-foreground transition-colors truncate max-w-[200px]"
                title={seg.label}
              >
                {seg.label}
              </Link>
            ) : !isLast && seg.onClick ? (
              <button
                onClick={seg.onClick}
                className="hover:text-foreground transition-colors truncate max-w-[200px]"
                title={seg.label}
              >
                {seg.label}
              </button>
            ) : (
              <span
                className={isLast ? 'text-foreground/80 truncate max-w-[280px]' : 'truncate max-w-[200px]'}
                title={seg.label}
              >
                {seg.label}
              </span>
            )}
          </div>
        );
      })}
    </nav>
  );
}
