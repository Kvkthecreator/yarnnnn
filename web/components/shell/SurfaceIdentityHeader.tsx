'use client';

/**
 * SurfaceIdentityHeader — The real H1 for detail surfaces (ADR-167 v5).
 *
 * Renders the identity block that used to live inside PageHeader: the page
 * title as a proper `h1.text-2xl`, the metadata strip directly under it, and
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
 *
 * The title is deliberately larger than any H1 likely to appear in nested
 * output content. Combined with the nested-card framing around the output
 * itself (rounded-lg + border + muted background), this establishes
 * unambiguous hierarchy: surface identity > nested document > document body.
 */

import type { ReactNode } from 'react';

interface SurfaceIdentityHeaderProps {
  /** Page title — rendered as h1.text-2xl.font-semibold */
  title: string;
  /** Compact metadata strip rendered directly under the title */
  metadata?: ReactNode;
  /** Inline actions on the right side of the title row */
  actions?: ReactNode;
}

export function SurfaceIdentityHeader({ title, metadata, actions }: SurfaceIdentityHeaderProps) {
  return (
    <div className="px-6 pt-6 pb-5 border-b border-border/40">
      <div className="flex items-start gap-4">
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-semibold text-foreground truncate" title={title}>
            {title}
          </h1>
          {metadata && (
            <div className="mt-1.5 text-xs text-muted-foreground">
              {metadata}
            </div>
          )}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0 pt-1">{actions}</div>}
      </div>
    </div>
  );
}
