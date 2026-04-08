'use client';

/**
 * PageHeader — In-page navigation chrome (ADR-167 v4).
 *
 * Uniform "chrome strip" across every surface and every state. v3 rendered
 * the last breadcrumb segment as a large promoted title in its own band,
 * which created a visual duplicate against the content's own H1 (e.g.
 * daily-update's rendered HTML starts with `<h1>Daily Workspace Update —
 * April 8, 2026</h1>`, which then stacked against PageHeader's big "Daily
 * Update" title — two headers doing the same job). v3 also suppressed the
 * breadcrumb entirely in list mode, making the header's tone conditional:
 * sometimes there was a nav strip, sometimes there wasn't.
 *
 * v4 fixes both by treating PageHeader as secondary chrome, not content:
 *
 *   1. The breadcrumb is always present with the same small muted treatment,
 *      even in list mode (where it's just `Work` or `Agents` or `Context` —
 *      a single segment rendered identically to any other segment). Uniform
 *      tone across all states.
 *   2. The breadcrumb's last segment is NOT promoted to a bold title. The
 *      entire path reads as secondary chrome. The content below is the real
 *      visual hero — its own H1 owns the typographic hierarchy.
 *   3. The metadata strip (`subtitle`) and inline actions sit on a second
 *      compact row separated from the breadcrumb by a thin divider. When
 *      both are absent (list mode), the second row collapses — just the
 *      breadcrumb chrome strip is rendered.
 *
 * ```
 *   ┌──────────────────────────────────────────────────────────┐
 *   │ Work › reporting's work › Daily Update                   │  ← always present, muted
 *   ├──────────────────────────────────────────────────────────┤
 *   │ Recurring · Active · Daily · Next: 9h  [Run][Pause][Edit]│  ← metadata + actions (detail only)
 *   ├──────────────────────────────────────────────────────────┤
 *   │ (content — owns the real H1)                             │
 *   └──────────────────────────────────────────────────────────┘
 * ```
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
  /** Compact metadata strip rendered on the second row */
  subtitle?: ReactNode;
  /** Inline actions on the right side of the metadata row */
  actions?: ReactNode;
}

export function PageHeader({ defaultLabel, subtitle, actions }: PageHeaderProps) {
  const { segments } = useBreadcrumb();

  // Normalize to an always-non-empty trail: if no segments are set, render
  // the fallback label as a single-segment breadcrumb so tone stays uniform.
  const trail = segments.length > 0
    ? segments
    : (defaultLabel ? [{ label: defaultLabel, href: undefined, onClick: undefined }] : []);

  if (trail.length === 0) return null;

  const hasSecondRow = Boolean(subtitle || actions);

  return (
    <div className="shrink-0 bg-background border-b border-border">
      {/* ── Breadcrumb chrome strip (always present, uniform tone) ── */}
      <nav
        aria-label="Breadcrumb"
        className="flex items-center gap-1.5 px-6 py-2 text-xs text-muted-foreground"
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

      {/* ── Metadata + actions row (detail mode only) ── */}
      {hasSecondRow && (
        <div className="flex items-center gap-3 px-6 py-2 border-t border-border/40">
          <div className="flex-1 min-w-0 text-xs text-muted-foreground">
            {subtitle}
          </div>
          {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
        </div>
      )}
    </div>
  );
}
