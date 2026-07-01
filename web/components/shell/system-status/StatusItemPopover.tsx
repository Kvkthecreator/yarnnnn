'use client';

/**
 * StatusItemPopover — shared popover shell for the agent-OS menu-bar
 * status cluster (ADR-297 D20).
 *
 * Renders an icon-only trigger button (macOS Wi-Fi pattern) that opens
 * a dropdown popover anchored to the trigger. Popover body is rendered
 * read-only by the caller; the popover provides framing + footer link
 * to an atomic surface for editing.
 *
 * Click-outside + Escape close the popover. Z-tier follows Z_POPOVER
 * (200) to match UserMenu + TopBar context menu.
 */

import { useState, useRef, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import type { LucideIcon } from 'lucide-react';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { Z_POPOVER } from '@/lib/shell/z-tiers';
import { usePopoverDismissal } from '@/lib/shell/usePopoverDismissal';
import { cn } from '@/lib/utils';
import type { KernelSurfaceSlug } from '@/types/desk';

export type StatusTone = 'ok' | 'warn' | 'paused' | 'muted';

interface StatusItemPopoverProps {
  /** Lucide icon for the trigger chip */
  icon: LucideIcon;
  /** Hover tooltip on the trigger button */
  tooltip: string;
  /** Visual tone — drives chip background/foreground tint */
  tone: StatusTone;
  /** ARIA label for the trigger (defaults to tooltip if omitted) */
  ariaLabel?: string;
  /** Header rendered at the top of the popover */
  popoverHeader: ReactNode;
  /** Rich body content rendered inside the popover */
  popoverBody: ReactNode;
  /**
   * Atomic surface to open from the footer. Either a kernel surface
   * slug (opens via foregroundSurface per D19.2) or a route string
   * with optional query params (opens via router.push for intra-surface
   * deep-links like /settings?tab=billing).
   */
  footerTarget: { kind: 'surface'; slug: KernelSurfaceSlug } | { kind: 'route'; href: string };
  /** Footer link copy (e.g. "Autonomy Settings…") */
  footerLabel: string;
  /** Optional class override for the trigger button */
  className?: string;
}

const TONE_CLASSES: Record<StatusTone, string> = {
  ok: 'text-primary/80 hover:bg-primary/10 hover:text-primary',
  warn: 'text-amber-700 hover:bg-amber-100 dark:text-amber-300 dark:hover:bg-amber-900/30',
  paused: 'text-amber-700 hover:bg-amber-100 dark:text-amber-300 dark:hover:bg-amber-900/30',
  muted: 'text-muted-foreground hover:bg-muted hover:text-foreground',
};

export function StatusItemPopover({
  icon: Icon,
  tooltip,
  tone,
  ariaLabel,
  popoverHeader,
  popoverBody,
  footerTarget,
  footerLabel,
  className,
}: StatusItemPopoverProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const { foregroundSurface } = useSurfacePreferences();
  const router = useRouter();

  // Click-outside + Escape close (shared dismissal contract, 2026-07-01).
  usePopoverDismissal(containerRef, isOpen, () => setIsOpen(false));

  const handleFooterClick = (
    target: { kind: 'surface'; slug: KernelSurfaceSlug } | { kind: 'route'; href: string },
  ) => {
    setIsOpen(false);
    if (target.kind === 'surface') {
      // ADR-297 D19.2: kernel-surface nav via foregroundSurface
      foregroundSurface(target.slug);
    } else {
      // ADR-297 D19.2 Effect A: route with query params mounts the
      // surface as a window on first paint. Used for intra-surface
      // deep-links like /settings?tab=billing.
      router.push(target.href);
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={cn(
          'w-8 h-8 rounded-md flex items-center justify-center transition-colors',
          TONE_CLASSES[tone],
          isOpen && 'bg-muted',
          className,
        )}
        title={tooltip}
        aria-label={ariaLabel ?? tooltip}
        aria-expanded={isOpen}
      >
        <Icon className="w-4 h-4 shrink-0" />
      </button>

      {isOpen && (
        <div
          style={{ zIndex: Z_POPOVER }}
          // 2026-06-03: `max-w-[calc(100vw-1rem)]` clamps the 18rem
          // popover to the viewport on phones. Pre-fix the fixed w-72
          // anchored right-0 to a ~24px-wide trigger overflowed the LEFT
          // viewport edge on narrow screens — the popover read as
          // "crossing the screen" and was clipped/unreadable. The right
          // edge stays pinned to the trigger; only the left edge clamps.
          className="absolute top-full right-0 mt-1 w-72 max-w-[calc(100vw-1rem)] bg-background border border-border rounded-lg shadow-lg overflow-hidden"
          role="dialog"
        >
          <div className="px-3 py-2 border-b border-border bg-muted/30">
            {popoverHeader}
          </div>
          <div className="px-3 py-2 text-sm">{popoverBody}</div>
          <button
            type="button"
            onClick={() => handleFooterClick(footerTarget)}
            className="w-full text-left px-3 py-2 text-xs text-primary hover:bg-muted border-t border-border transition-colors"
          >
            {footerLabel} →
          </button>
        </div>
      )}
    </div>
  );
}
