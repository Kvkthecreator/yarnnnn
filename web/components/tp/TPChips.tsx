'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * TPChips - Quick action chips for TP input
 */

import { Chip } from '@/types/desk';

interface TPChipsProps {
  chips: Chip[];
  onSelect: (prompt: string) => void;
  disabled?: boolean;
}

export function TPChips({ chips, onSelect, disabled }: TPChipsProps) {
  if (chips.length === 0) return null;

  return (
    <div className="flex gap-2 flex-wrap">
      {chips.map((chip) => (
        <button
          key={chip.label}
          onClick={() => onSelect(chip.prompt)}
          disabled={disabled}
          className="px-3 py-1.5 text-xs border border-border rounded-full hover:bg-muted hover:border-primary/50 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap transition-colors"
        >
          {chip.label}
        </button>
      ))}
    </div>
  );
}
