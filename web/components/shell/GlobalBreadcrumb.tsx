'use client';

/**
 * GlobalBreadcrumb — Renders breadcrumb segments in the top header bar.
 *
 * Sits under the yarnnn logo. Shows location depth:
 *   yarnnn / Competitive Intelligence / cursor
 *
 * Max depth: 2 segments (beyond that, link to Context page file browser).
 * Empty segments = nothing rendered (just the logo).
 */

import { useBreadcrumb } from '@/contexts/BreadcrumbContext';

export function GlobalBreadcrumb() {
  const { segments } = useBreadcrumb();

  if (segments.length === 0) return null;

  return (
    <div className="flex items-center gap-1">
      {segments.map((seg, i) => (
        <div key={i} className="flex items-center gap-1 shrink-0">
          <span className="text-muted-foreground/30 text-sm">/</span>
          {seg.onClick ? (
            <button
              onClick={seg.onClick}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors truncate max-w-[200px]"
            >
              {seg.label}
            </button>
          ) : (
            <span className="text-sm text-foreground truncate max-w-[200px]">
              {seg.label}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
