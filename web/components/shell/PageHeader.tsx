'use client';

/**
 * PageHeader — In-page navigation + title header (ADR-167 v3 amendment).
 *
 * Two-band layout. The previous v2 version stacked breadcrumb + metadata +
 * actions above a single thin divider, then handed off to page content. The
 * result was a dense chrome strip where the breadcrumb's last segment was
 * trying to be both a nav link AND a title, while the metadata + actions
 * that belonged to the page content sat visually detached from it.
 *
 *   v2 (deleted)                        v3 (this file)
 *   ──────────────────────              ──────────────────────
 *   Work › X › Daily [Run]              Work › X › Daily           ← nav strip
 *   Recurring · Daily · …               ──────────────────────
 *   ──────────────────────              Daily Update       [Run]   ← title band
 *   H1 (content)                        Recurring · Daily · …
 *                                       ──────────────────────
 *                                       H1 (content)
 *
 * Band 1 ("nav strip"): breadcrumb path only. Muted, compact, full-width
 * chevron trail. No bold last segment, no metadata, no actions. This is pure
 * navigation — it tells you where you are, not what you're looking at.
 *
 * Band 2 ("title header"): the last breadcrumb segment rendered as a larger
 * title (anchors the page content below it), with `subtitle` as a metadata
 * strip directly under it, and `actions` inline on the right. This is the
 * header that introduces the content — structurally part of the content
 * block, not the chrome.
 *
 * List mode (one segment, or no segments with `defaultLabel`): the nav strip
 * is suppressed — there's nothing to navigate back through, so the title
 * band stands alone.
 *
 * Reads from BreadcrumbContext (commit b033513) — pages still call
 * `setBreadcrumb()` with the same segment shape. Only the renderer changes.
 */

import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { ChevronRight } from 'lucide-react';
import Link from 'next/link';
import type { ReactNode } from 'react';

interface PageHeaderProps {
  /**
   * Fallback label rendered when BreadcrumbContext has no segments.
   * Used by list-mode pages whose breadcrumb is the surface name only.
   * Detail-mode pages set the full path via `setBreadcrumb()` and ignore
   * this prop.
   */
  defaultLabel?: string;
  /** Compact metadata strip rendered directly under the title */
  subtitle?: ReactNode;
  /** Inline actions on the right side of the title band */
  actions?: ReactNode;
}

export function PageHeader({ defaultLabel, subtitle, actions }: PageHeaderProps) {
  const { segments } = useBreadcrumb();
  const hasSegments = segments.length > 0;
  const showNavStrip = segments.length > 1; // only show breadcrumb when there IS a path to show

  // Title = last segment, or defaultLabel for list-mode pages
  const title = hasSegments ? segments[segments.length - 1].label : (defaultLabel ?? '');
  const trailSegments = segments.slice(0, -1); // everything except the current page

  return (
    <div className="shrink-0 bg-background">
      {/* ── Band 1: nav strip (breadcrumb path) ── */}
      {showNavStrip && (
        <nav
          aria-label="Breadcrumb"
          className="flex items-center gap-1.5 px-6 py-1.5 text-xs text-muted-foreground border-b border-border/40"
        >
          {trailSegments.map((seg, i) => (
            <div key={`${seg.label}-${i}`} className="flex items-center gap-1.5 min-w-0">
              {i > 0 && <ChevronRight className="w-3 h-3 text-muted-foreground/30 shrink-0" />}
              {seg.href ? (
                <Link
                  href={seg.href}
                  className="hover:text-foreground transition-colors truncate max-w-[200px]"
                  title={seg.label}
                >
                  {seg.label}
                </Link>
              ) : seg.onClick ? (
                <button
                  onClick={seg.onClick}
                  className="hover:text-foreground transition-colors truncate max-w-[200px]"
                  title={seg.label}
                >
                  {seg.label}
                </button>
              ) : (
                <span className="truncate max-w-[200px]" title={seg.label}>
                  {seg.label}
                </span>
              )}
            </div>
          ))}
          <ChevronRight className="w-3 h-3 text-muted-foreground/30 shrink-0" />
          <span className="text-muted-foreground/60 truncate max-w-[240px]" title={title}>
            {title}
          </span>
        </nav>
      )}

      {/* ── Band 2: title header (anchors the content below) ── */}
      <div className="px-6 py-3 border-b border-border">
        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-semibold text-foreground truncate" title={title}>
              {title}
            </h1>
            {subtitle && (
              <div className="mt-1 text-xs text-muted-foreground">
                {subtitle}
              </div>
            )}
          </div>
          {actions && <div className="flex items-center gap-2 shrink-0 pt-0.5">{actions}</div>}
        </div>
      </div>
    </div>
  );
}
