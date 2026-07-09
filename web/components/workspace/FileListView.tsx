'use client';

/**
 * FileListView — the ONE Finder/Explorer details list for the Files surface
 * (Finder-parity, 2026-07-09).
 *
 * Before this, two list views had diverged: RecentsView rendered a <table>
 * (Name · Where · Author · When) and ContentViewer's folder listing rendered a
 * CSS grid with a DIFFERENT column set (Name · Author · Modified) and different
 * row height. Finder has one list-view column model everywhere. This is that
 * one model: a shared header + row grammar both callers render.
 *
 * Columns (Finder's "Name / Date Modified / Kind"-shaped, adapted to our
 * attribution-first substrate): NAME · WHERE · AUTHOR · WHEN. A caller that has
 * no meaningful "where" (a folder listing — every row lives in the same folder)
 * passes a per-row subtitle instead, shown under the name; the WHERE column
 * simply stays empty for those rows, so the grid geometry never changes.
 *
 * One <FileListRow>, one header, one set of column widths, one row height. The
 * click/right-click dispatch is the caller's (each row is a button-shaped cell),
 * kept generic so Recents (selection state), the folder listing (navigate), and
 * the Home deep-link all reuse it.
 */

import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { FileIcon } from './FileIcon';
import { Folder } from 'lucide-react';
import { SurfaceLink } from '@/components/shell/SurfaceLink';

// The single column grid — Name (flex) · Where (fixed) · Author (fixed) · When
// (fixed). `md:` drops the Where column on narrow widths (Finder collapses
// columns the same way). Header and rows share this template verbatim.
const GRID = 'grid grid-cols-[minmax(0,1fr)_120px] gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,14rem)_130px_120px]';

export function FileListHeader() {
  return (
    <div className={cn(GRID, 'border-b border-border/60 px-4 py-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground')}>
      <span>Name</span>
      <span className="hidden md:block">Where</span>
      <span>Author</span>
      <span className="text-right">When</span>
    </div>
  );
}

export interface FileListRowProps {
  name: string;
  kind: 'file' | 'folder';
  /** The "Where" column (Recents). Omit for folder listings (stays empty). */
  where?: string;
  /** A subtitle under the name (folder listing summary). */
  subtitle?: string;
  /** Author cell — a label + accent dot node built by the caller. */
  author?: ReactNode;
  /** The "When" column, right-aligned. */
  when?: string;
  selected?: boolean;
  /** De-emphasize machine-config `_*` files (kept, not hidden — ADR-320). */
  dim?: boolean;
  /**
   * Click dispatch, mirroring <FileTile>: onClick (Files/folder mount owns
   * selection) OR linkTo (Home mount deep-links to the Files surface). Provide
   * one or the other.
   */
  onClick?: () => void;
  linkTo?: string;
  onContextMenu?: (e: React.MouseEvent) => void;
  title?: string;
}

export function FileListRow({
  name, kind, where, subtitle, author, when,
  selected = false, dim = false, onClick, linkTo, onContextMenu, title,
}: FileListRowProps) {
  const rowClass = cn(
    GRID,
    'w-full items-center px-4 py-2 text-left text-sm transition-colors',
    selected ? 'bg-primary/10 hover:bg-primary/15' : 'hover:bg-muted/40',
    dim && !selected && 'opacity-70',
  );

  const inner = (
    <>
      {/* Name */}
      <div className="flex min-w-0 items-center gap-2.5">
        {kind === 'folder'
          ? <Folder className="h-4 w-4 shrink-0 text-sky-600" />
          : <FileIcon filename={name} size="md" />}
        <div className="min-w-0">
          <span className={cn('block truncate text-foreground', dim && 'text-muted-foreground')}>{name}</span>
          {subtitle && <span className="block truncate text-xs text-muted-foreground">{subtitle}</span>}
        </div>
      </div>
      {/* Where */}
      <span className="hidden min-w-0 truncate text-muted-foreground md:block">{where ?? ''}</span>
      {/* Author */}
      <span className="min-w-0 truncate text-muted-foreground">{author}</span>
      {/* When */}
      <span className="truncate text-right text-muted-foreground/80">{when ?? ''}</span>
    </>
  );

  if (linkTo && !onClick) {
    return (
      <SurfaceLink to="files" params={{ path: linkTo }} className={rowClass} title={title ?? name} onContextMenu={onContextMenu}>
        {inner}
      </SurfaceLink>
    );
  }
  return (
    <button type="button" onClick={onClick} onContextMenu={onContextMenu} title={title ?? name} className={rowClass}>
      {inner}
    </button>
  );
}
