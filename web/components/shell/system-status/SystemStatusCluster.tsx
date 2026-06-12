'use client';

/**
 * SystemStatusCluster — agent-OS menu-bar status cluster (ADR-297 D20;
 * consolidated by ADR-340 P1).
 *
 * Three kernel-general status chips in the Right region of the top bar,
 * between the Dock and UserMenu. macOS Control Center / menu-bar-extras
 * analog: always-visible operator-level standing STATE about the
 * system's capacity to do work. Events that demand the operator are a
 * different chrome role — the AttentionCenter (Notification Center
 * analog, ADR-340 D3), a sibling top-bar item, never a chip here.
 *
 * Order (kernel-priority, left-to-right):
 *   1. Autonomy    — governance (what the agent CAN do)
 *   2. Money       — budget envelope + balance runway (battery analog;
 *                    Budget absorbed Balance per ADR-340 P1)
 *   3. Connections — reach (Wi-Fi analog)
 *
 * Responsive collapse:
 *   md+   → all three chips inline
 *   <md   → single rollup chip (Cpu icon) → popover with all three
 *           items stacked vertically. Mirrors macOS Control Center.
 *
 * Read-only popovers per D20 §D2 — every mutation routes to the
 * corresponding atomic surface via the popover footer link.
 */

import { useState, useRef, useEffect } from 'react';
import { Cpu } from 'lucide-react';
import { Z_POPOVER } from '@/lib/shell/z-tiers';
import { cn } from '@/lib/utils';
import { AutonomyStatusItem } from './AutonomyStatusItem';
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
        <AutonomyStatusItem />
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

  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen]);

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
            <AutonomyStatusItem />
            <BudgetStatusItem />
            <ConnectionsStatusItem />
          </div>
        </div>
      )}
    </div>
  );
}
