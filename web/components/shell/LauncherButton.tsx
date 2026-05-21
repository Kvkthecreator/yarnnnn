'use client';

/**
 * LauncherButton — ADR-297 D4.
 *
 * The always-visible affordance that summons the Launcher overlay. Lives
 * in the top-right of the shell chrome alongside the user menu.
 *
 * Operator preference (KVK 2026-05-21): summon-first, not keyboard-first.
 * Voice forward-direction beyond keyboard. Hence the icon is the primary
 * affordance. A ⌘K hotkey is a power-user enhancement, easy to add later
 * if pressure surfaces.
 */

import { LayoutGrid } from 'lucide-react';

interface LauncherButtonProps {
  onClick: () => void;
}

export function LauncherButton({ onClick }: LauncherButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Open surface launcher"
      title="Open surface launcher"
      className="flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
    >
      <LayoutGrid className="h-4 w-4" />
    </button>
  );
}
