'use client';

/**
 * GlobalBreadcrumb - centered scope path below the main navigation.
 *
 * SURFACE-ARCHITECTURE.md v7.2: Always-present structure on pages with depth.
 * Not inline with logo — sits as its own bar below the header. Pages set
 * segments via BreadcrumbContext; this component reads and renders them.
 *
 * When segments are empty, renders nothing (no empty bar).
 * When segments exist, renders a responsive scope path with linkable segments.
 *
 * Examples:
 *   Agents + CI selected:     Competitive Intelligence
 *   Context + domain + file:  Competitors / cursor / profile.md
 *   Home:                     (hidden — no segments)
 */

import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { ChevronRight } from 'lucide-react';
import Link from 'next/link';

export function GlobalBreadcrumb() {
  const { segments } = useBreadcrumb();

  if (segments.length === 0) return null;

  return (
    <div className="border-b border-border/50 bg-background px-3 py-1.5 shrink-0">
      <nav
        aria-label="Breadcrumb"
        className="mx-auto flex max-w-4xl items-center gap-1 overflow-x-auto text-xs sm:text-sm"
      >
        {segments.map((seg, i) => (
          <div key={`${seg.label}-${i}`} className="flex items-center gap-1 shrink-0">
            {i > 0 && <ChevronRight className="w-3 h-3 text-muted-foreground/30 shrink-0" />}
            {seg.href ? (
              <Link
                href={seg.href}
                className="text-muted-foreground hover:text-foreground transition-colors truncate max-w-[180px] sm:max-w-[240px]"
              >
                {seg.label}
              </Link>
            ) : seg.onClick ? (
              <button
                onClick={seg.onClick}
                className="text-muted-foreground hover:text-foreground transition-colors truncate max-w-[180px] sm:max-w-[240px]"
              >
                {seg.label}
              </button>
            ) : (
              <span className="text-foreground truncate max-w-[180px] sm:max-w-[240px]">
                {seg.label}
              </span>
            )}
          </div>
        ))}
      </nav>
    </div>
  );
}
