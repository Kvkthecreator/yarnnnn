'use client';

/**
 * PageHeader — In-page breadcrumb + title row (ADR-167 v2 amendment).
 *
 * Replaces the separate `<GlobalBreadcrumb />` bar that sat between the global
 * header and main content. Two reasons for the move:
 *
 * 1. The breadcrumb's last segment IS the page title. Rendering both a
 *    floating breadcrumb bar AND a page title inside the surface stacks two
 *    bands doing the same job. Collapse them into one.
 *
 * 2. On lists like `/agents` the page-title slot was empty (the first thing
 *    inside the surface was a roster section header). The breadcrumb bar
 *    above looked detached because there was no title to anchor to.
 *
 * Reads from BreadcrumbContext (commit b033513) — pages still call
 * `setBreadcrumb()` with the same segment shape, only the renderer location
 * changes. Single-segment surfaces (e.g. `[{ label: 'Work', kind: 'surface' }]`)
 * render as a single bold title. Multi-segment paths render as
 * `Surface › ancestor › current` with chevrons.
 *
 * Optional `subtitle` slot lets detail pages put their compact metadata strip
 * (`Recurring · Active · Daily · Reporting · Next: in 1h`) right under the
 * breadcrumb instead of repeating the title in a separate header band below.
 *
 * Optional `actions` slot puts buttons on the right (Run / Pause / Edit via
 * chat) inline with the breadcrumb so the page header is one visual unit.
 *
 * If pages don't call `setBreadcrumb()` (or call `clearBreadcrumb()`),
 * PageHeader still renders the surface label from `defaultLabel` so the
 * page never has an empty title slot.
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
  /** Compact metadata strip rendered as a second row under the breadcrumb */
  subtitle?: ReactNode;
  /** Inline actions on the right side of the breadcrumb row */
  actions?: ReactNode;
}

export function PageHeader({ defaultLabel, subtitle, actions }: PageHeaderProps) {
  const { segments } = useBreadcrumb();
  const hasSegments = segments.length > 0;

  return (
    <div className="border-b border-border/60 bg-background px-6 py-3 shrink-0">
      <div className="flex items-center gap-2">
        <nav
          aria-label="Breadcrumb"
          className="flex flex-1 items-center gap-1.5 min-w-0 text-sm"
        >
          {hasSegments ? (
            segments.map((seg, i) => {
              const isLast = i === segments.length - 1;
              return (
                <div key={`${seg.label}-${i}`} className="flex items-center gap-1.5 min-w-0">
                  {i > 0 && <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/30 shrink-0" />}
                  {isLast ? (
                    <span className="font-semibold text-foreground truncate max-w-[280px]" title={seg.label}>
                      {seg.label}
                    </span>
                  ) : seg.href ? (
                    <Link
                      href={seg.href}
                      className="text-muted-foreground hover:text-foreground transition-colors truncate max-w-[200px]"
                      title={seg.label}
                    >
                      {seg.label}
                    </Link>
                  ) : seg.onClick ? (
                    <button
                      onClick={seg.onClick}
                      className="text-muted-foreground hover:text-foreground transition-colors truncate max-w-[200px]"
                      title={seg.label}
                    >
                      {seg.label}
                    </button>
                  ) : (
                    <span className="text-muted-foreground truncate max-w-[200px]" title={seg.label}>
                      {seg.label}
                    </span>
                  )}
                </div>
              );
            })
          ) : (
            <span className="font-semibold text-foreground">{defaultLabel ?? ''}</span>
          )}
        </nav>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
      {subtitle && (
        <div className="mt-1.5 text-xs text-muted-foreground">
          {subtitle}
        </div>
      )}
    </div>
  );
}
