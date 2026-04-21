'use client';

/**
 * SurfaceIdentityHeader — The real H1 for detail surfaces (ADR-167 v5).
 *
 * Renders the identity block that used to live inside PageHeader: the page
 * title as a proper `h1`, the metadata strip directly under it, and
 * optional inline actions on the right. Unlike PageHeader (which is chrome),
 * this block is CONTENT — it sits inside the surface's own scroll area,
 * above whatever the surface content is (task output, agent mandate, etc.).
 *
 * Why it's separate from PageHeader. PageHeader is the breadcrumb chrome
 * strip — it answers "where am I?" and it's always present. This component
 * answers "what is this page ABOUT?" and it lives with the content.
 * Separating chrome from identity means:
 *
 *   - The content's own visual hero is the H1 that describes the page.
 *   - Nested content (output iframes, AGENT.md markdown) can safely render
 *     their own H1s inside bordered cards without competing with the chrome
 *     strip — because the chrome strip doesn't have an H1 anymore.
 *   - WorkDetail and AgentContentView share one shape. No drift.
 *
 * Used by:
 *   - WorkDetail (task title + mode/status/schedule strip + Run/Pause/Edit)
 *   - AgentContentView (agent title + class/domain/task count strip)
 *   - ChatSurface (agent title + workspace-state toggle action)
 *
 * Size presets:
 *   - "lg" (default): `text-2xl font-semibold` — full hero treatment for
 *     detail pages where the title IS the page subject (a specific task,
 *     a specific agent).
 *   - "md": `text-base font-semibold` — lighter treatment for surfaces
 *     where the title is more of an intro than a subject (the /chat page
 *     reads as "this is a conversation with Thinking Partner" — the
 *     conversation itself is the hero, not the H1).
 *
 * Icon slot: optional `icon` ReactNode renders to the left of the title.
 * Used by ChatSurface for the yarnnn circle logo next to "Thinking Partner"
 * — matching the sidebar chat panel's logo treatment for consistency.
 */

import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface SurfaceIdentityHeaderProps {
  /** Page title — rendered as the real H1 */
  title: string;
  /** Compact metadata strip rendered directly under the title */
  metadata?: ReactNode;
  /** Inline actions on the right side of the title row */
  actions?: ReactNode;
  /** Optional icon/logo rendered to the left of the title */
  icon?: ReactNode;
  /**
   * Size preset. "lg" (default) = detail-page hero (text-2xl).
   * "md" = lighter treatment for surfaces where the title is an intro
   * rather than the page's actual subject (e.g. /chat).
   */
  size?: 'lg' | 'md';
  /**
   * Whether to render a bottom divider. Default true. Set false when the
   * header is embedded inside a narrower column (e.g. /chat's max-w-3xl
   * wrapper) where a half-width border would float mid-page — the
   * PageHeader's own divider above already separates chrome from content.
   */
  bordered?: boolean;
  /**
   * When true, the title IS the yarnnn brand mark — render it in Pacifico
   * (font-brand) instead of the regular semibold sans. Only /chat uses this,
   * because only /chat's hero title is literally the product name.
   */
  brandTitle?: boolean;
}

export function SurfaceIdentityHeader({
  title,
  metadata,
  actions,
  icon,
  size = 'lg',
  bordered = true,
  brandTitle = false,
}: SurfaceIdentityHeaderProps) {
  const titleClass = brandTitle
    ? (size === 'md'
      ? 'text-xl font-brand text-foreground truncate'
      : 'text-3xl font-brand text-foreground truncate')
    : (size === 'md'
      ? 'text-base font-semibold text-foreground truncate'
      : 'text-2xl font-semibold text-foreground truncate');

  // When bordered (full-width, standalone mode) we own horizontal padding.
  // When unbordered (embedded inside a constrained column, e.g. /chat's
  // max-w-3xl wrapper) the outer layer owns horizontal padding so the
  // header aligns with whatever content sits in the same column.
  const paddingClass = bordered
    ? (size === 'md' ? 'px-6 py-3' : 'px-6 pt-6 pb-5')
    : (size === 'md' ? 'py-3' : 'pt-6 pb-5');

  return (
    <div className={cn(paddingClass, bordered && 'border-b border-border/40')}>
      <div className="flex items-center gap-3">
        {icon && <div className="shrink-0 flex items-center">{icon}</div>}
        <div className="flex-1 min-w-0">
          <h1 className={titleClass} title={title}>
            {title}
          </h1>
          {metadata && (
            <div className={cn('text-xs text-muted-foreground', size === 'md' ? 'mt-0.5' : 'mt-1.5')}>
              {metadata}
            </div>
          )}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
    </div>
  );
}
