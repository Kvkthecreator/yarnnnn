'use client';

/**
 * CanvasContextMenu — the background right-click menu for the Files center pane
 * (Finder-parity, 2026-07-09).
 *
 * Finder has no visible "New Folder" / "Add Files" buttons; both verbs live in
 * the right-click menu on empty canvas (plus ⌘⇧N / drag-drop). This is that
 * menu. It carries CANVAS-level verbs (create a folder here, add files here) —
 * distinct from <FileContextMenu>, which acts on a specific file/folder TARGET.
 *
 * The Files page owns the verbs and the open-state; this component only paints
 * the menu at the click point and dismisses on outside-click / Escape (the same
 * lifecycle contract as FileContextMenu, kept deliberately identical).
 */

import { useEffect } from 'react';
import { useViewportClamp } from '@/hooks/useViewportClamp';
import { FolderPlus, Upload, XSquare } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface CanvasContextMenuProps {
  x: number;
  y: number;
  onClose: () => void;
  onNewFolder: () => void;
  onAddFiles: () => void;
  /**
   * Drop the current selection — rendered ONLY while something is picked
   * (`selectionCount > 0`), and it names the count so the operator can see
   * what they are leaving.
   *
   * This is the VISIBLE exit (2026-08-20). The floating Move…/Open/Clear chip
   * that used to carry one is deleted: a selection should look selected, not
   * announce itself in a toolbar. But ADR-519 shipped an inescapable
   * multi-selection to production once, and withdrawal is part of the feature —
   * so the exit moved rather than vanished. Escape serves the keyboard, a
   * background click serves the hand already on the mouse, and this serves the
   * operator who learned neither. The background menu is where Finder puts
   * "Deselect All" too.
   */
  onDeselect?: () => void;
  selectionCount?: number;
}

export function CanvasContextMenu({ x, y, onClose, onNewFolder, onAddFiles, onDeselect, selectionCount = 0 }: CanvasContextMenuProps) {
  useEffect(() => {
    const close = () => onClose();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('click', close);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('click', close);
      window.removeEventListener('keydown', onKey);
    };
  }, [onClose]);

  // Keep the whole menu on screen — MEASURED, not guessed (2026-08-27). This
  // was `innerHeight - 120`, a third hand-picked constant for the same
  // question its two siblings also answered by guessing. Shared hook now.
  const { ref: boxRef, left, top } = useViewportClamp<HTMLDivElement>(x, y);

  const run = (fn: () => void) => { fn(); onClose(); };

  return (
    <div
      ref={boxRef}
      className="fixed z-50 min-w-[180px] max-h-[calc(100vh-16px)] overflow-y-auto rounded-md border border-border bg-popover py-1 shadow-md"
      style={{ left, top }}
      onClick={(e) => e.stopPropagation()}
      onContextMenu={(e) => e.preventDefault()}
    >
      <Item icon={<FolderPlus className="h-3.5 w-3.5 text-muted-foreground" />} onClick={() => run(onNewFolder)}>
        New Folder
      </Item>
      <Item icon={<Upload className="h-3.5 w-3.5 text-muted-foreground" />} onClick={() => run(onAddFiles)}>
        Add Files…
      </Item>
      {onDeselect && selectionCount > 0 && (
        <>
          <div className="my-1 h-px bg-border/60" />
          <Item icon={<XSquare className="h-3.5 w-3.5 text-muted-foreground" />} onClick={() => run(onDeselect)}>
            {selectionCount === 1 ? 'Deselect' : `Deselect ${selectionCount} items`}
          </Item>
        </>
      )}
    </div>
  );
}

function Item({ icon, children, onClick }: { icon: React.ReactNode; children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn('flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors hover:bg-accent/60')}
    >
      {icon}
      <span className="flex-1">{children}</span>
    </button>
  );
}
