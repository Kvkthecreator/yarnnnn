'use client';

/**
 * SystemStatusCluster — agent-OS menu-bar status cluster (ADR-297 D20;
 * consolidated by ADR-340 P1; conceptually reframed 2026-07-01).
 *
 * Three kernel-general status chips in the Right region of the top bar,
 * between the Dock and UserMenu. macOS Control Center / menu-bar-extras
 * analog: always-visible operator-level standing STATE about the
 * system's capacity to do work. Events that demand the operator are a
 * different chrome role — the AttentionCenter (Notification Center
 * analog, ADR-340 D3), a sibling top-bar item, never a chip here.
 *
 * THE MENTAL MODEL (2026-07-01 reframe): the substrate filesystem is the
 * service, and Freddie is the system agent latched onto it (GitHub ⇄ Copilot
 * — the substrate is the repo, Freddie is the agent working over it). The
 * cluster reads through that lens, left-to-right:
 *   1. Freddie      — the system agent's disposition (autonomy = how much it
 *                     acts on its own). The chip names the ENTITY, not an
 *                     abstract OS dial. Footer → Freddie's settings.
 *   2. Money        — the spend that backs the work (budget envelope + balance
 *                     runway, battery analog). Being reframed separately with
 *                     the pricing-model work — untouched in the 2026-07-01 pass.
 *   3. Connections  — the SUBSTRATE's reach: what feeds the service (Wi-Fi
 *                     analog). Not Freddie — the inputs the operation perceives.
 *
 * Responsive collapse:
 *   md+   → all three chips inline
 *   <md   → single rollup chip (Cpu icon) → popover with all three
 *           items stacked vertically. Mirrors macOS Control Center.
 *
 * Read-only popovers per D20 §D2 — every mutation routes to the
 * corresponding atomic surface via the popover footer link.
 */

import { useState, useRef } from 'react';
import { Cpu } from 'lucide-react';
import { Z_POPOVER } from '@/lib/shell/z-tiers';
import { usePopoverDismissal } from '@/lib/shell/usePopoverDismissal';
import { cn } from '@/lib/utils';
import { FreddieStatusItem } from './FreddieStatusItem';
import { BudgetStatusItem } from './BudgetStatusItem';
import { ConnectionsStatusItem } from './ConnectionsStatusItem';

export function SystemStatusCluster() {
  return (
    <>
      {/* md+ — all three chips inline */}
      <div
        className="hidden md:flex items-center gap-0.5 shrink-0"
        role="group"
        aria-label="System status"
      >
        <FreddieStatusItem />
        <BudgetStatusItem />
        <ConnectionsStatusItem />
      </div>

      {/* <md — collapsed rollup. Single Cpu chip opens a popover that
          stacks all three items in a row. Each item keeps its own
          popover trigger; operator can drill into any one for detail.
          Mirrors macOS Control Center on smaller displays. */}
      <div
        className="flex md:hidden items-center shrink-0"
        role="group"
        aria-label="System status (compact)"
      >
        <MobileRollup />
      </div>
    </>
  );
}

function MobileRollup() {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Click-outside + Escape close (shared dismissal contract, 2026-07-01).
  usePopoverDismissal(containerRef, isOpen, () => setIsOpen(false));

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={cn(
          'w-8 h-8 rounded-md flex items-center justify-center transition-colors',
          'text-muted-foreground hover:bg-muted hover:text-foreground',
          isOpen && 'bg-muted',
        )}
        title="System status"
        aria-label="System status"
        aria-expanded={isOpen}
      >
        <Cpu className="w-4 h-4 shrink-0" />
      </button>

      {isOpen && (
        <div
          style={{ zIndex: Z_POPOVER }}
          className="absolute top-full right-0 mt-1 w-auto bg-background border border-border rounded-lg shadow-lg p-2"
          role="dialog"
        >
          <div className="flex items-center gap-1">
            <FreddieStatusItem />
            <BudgetStatusItem />
            <ConnectionsStatusItem />
          </div>
        </div>
      )}
    </div>
  );
}
