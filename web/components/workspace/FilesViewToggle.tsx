'use client';

/**
 * FilesViewToggle — the ONE icon/list segmented switcher for the Files surface
 * (Finder-parity, 2026-07-09).
 *
 * Before this, two near-identical toggles existed: one inside RecentsView (its
 * own localStorage key + hook) and one hand-rolled in files/page.tsx (a second
 * key). Toggling one didn't move the other — the surface had two memories of one
 * preference. This is the single control; it reads/writes the single
 * `useFilesViewMode` hook (one localStorage key, module-synced across mounts).
 * Finder has one view control; so do we.
 */

import { LayoutGrid, List as ListIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FilesViewMode } from '@/lib/workspace/useFilesViewMode';

export function FilesViewToggle({
  mode,
  onChange,
}: {
  mode: FilesViewMode;
  onChange: (m: FilesViewMode) => void;
}) {
  return (
    <div className="inline-flex items-center rounded-md border border-border p-0.5" role="group" aria-label="View">
      <button
        type="button"
        aria-label="Icon view"
        aria-pressed={mode === 'icon'}
        onClick={() => onChange('icon')}
        className={cn(
          'rounded p-1 transition-colors',
          mode === 'icon' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground',
        )}
      >
        <LayoutGrid className="h-3.5 w-3.5" />
      </button>
      <button
        type="button"
        aria-label="List view"
        aria-pressed={mode === 'list'}
        onClick={() => onChange('list')}
        className={cn(
          'rounded p-1 transition-colors',
          mode === 'list' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground',
        )}
      >
        <ListIcon className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
