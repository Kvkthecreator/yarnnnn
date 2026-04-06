'use client';

/**
 * GlobalBreadcrumb — Thin secondary location bar below the main header.
 *
 * SURFACE-ARCHITECTURE.md v7.2: Always-present structure on pages with depth.
 * Not inline with logo — sits as its own bar below the header. Pages set
 * segments via BreadcrumbContext; this component reads and renders them.
 *
 * When segments are empty, renders nothing (no empty bar).
 * When segments exist, renders a thin h-8 bar with path segments.
 *
 * Examples:
 *   Agents + CI selected:     Competitive Intelligence
 *   Context + domain + file:  Competitors / cursor / profile.md
 *   Home:                     (hidden — no segments)
 */

import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { ChevronRight } from 'lucide-react';

export function GlobalBreadcrumb() {
  const { segments } = useBreadcrumb();

  if (segments.length === 0) return null;

  return (
    <div className="h-8 border-b border-border/50 bg-muted/20 flex items-center px-4 shrink-0">
      <nav className="flex items-center gap-1 min-w-0 text-sm">
        {segments.map((seg, i) => (
          <div key={i} className="flex items-center gap-1 shrink-0">
            {i > 0 && <ChevronRight className="w-3 h-3 text-muted-foreground/30 shrink-0" />}
            {seg.onClick ? (
              <button
                onClick={seg.onClick}
                className="text-muted-foreground hover:text-foreground transition-colors truncate max-w-[200px]"
              >
                {seg.label}
              </button>
            ) : (
              <span className="text-foreground truncate max-w-[200px]">
                {seg.label}
              </span>
            )}
          </div>
        ))}
      </nav>
    </div>
  );
}
