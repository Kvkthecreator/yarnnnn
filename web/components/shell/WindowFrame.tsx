'use client';

/**
 * WindowFrame — ADR-297 D14.
 *
 * Wraps each open content surface in a visible window: a 32px title
 * bar (surface name left, close × right) above the surface body, with
 * a subtle 1px border + rounded corners + inset from the desktop edges.
 *
 * The window IS the visual affordance of "this surface is open." Pre-
 * D14 surfaces filled the viewport edge-to-edge with no indication
 * they were windows; D13 made the lifecycle multi-mount but the
 * appearance stayed page-shaped. D14 closes the gap.
 *
 * Reconciliation with per-surface PageHeader (per ADR-297 §D14 title-
 * bar reconciliation choice "subtle title bar + PageHeader survives"):
 * the title bar shows the surface name only. The per-surface
 * PageHeader inside the surface body continues to render its breadcrumb
 * + per-surface action buttons. Minor visual redundancy (the name
 * appears once in the title bar, once in PageHeader) is accepted as
 * the price for not invading every surface's existing chrome.
 *
 * The desktop empty state (D13 §5 / web/components/shell/Desktop.tsx)
 * deliberately does NOT use this frame — there is no window when
 * nothing is open, only the desktop wallpaper.
 */

import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface WindowFrameProps {
  /** Surface name shown in the title bar (e.g. "Feed", "Cockpit"). */
  title: string;
  /** Whether this window is the currently-foregrounded one. */
  isForegrounded: boolean;
  /** Called when the operator clicks the title bar's × close button. */
  onClose: () => void;
  /** The surface body. */
  children: React.ReactNode;
}

export function WindowFrame({
  title,
  isForegrounded,
  onClose,
  children,
}: WindowFrameProps) {
  return (
    <div
      className={cn(
        'flex h-full w-full flex-col overflow-hidden rounded-lg border bg-background shadow-sm transition-shadow',
        isForegrounded
          ? 'border-border shadow-md'
          : 'border-border/60'
      )}
    >
      {/* Title bar — 32px, surface name left, × close right. macOS-
          style. The title bar is part of the frame; it does NOT
          replace the per-surface PageHeader inside `children` (which
          owns breadcrumb + actions). */}
      <div className="flex h-8 shrink-0 items-center justify-between border-b border-border bg-muted/30 px-3">
        <div className="text-xs font-medium text-foreground/80 truncate">
          {title}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label={`Close ${title}`}
          title={`Close ${title}`}
          className="rounded p-0.5 text-muted-foreground/70 transition-colors hover:bg-destructive/15 hover:text-destructive"
        >
          <X className="h-3 w-3" />
        </button>
      </div>

      {/* Surface body — flex-1 so the surface's own scroll containers
          work correctly inside the frame. min-h-0 prevents flex
          children from forcing the frame taller than its parent. */}
      <div className="flex-1 min-h-0 overflow-hidden">{children}</div>
    </div>
  );
}
