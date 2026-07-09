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
import { FolderPlus, Upload } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface CanvasContextMenuProps {
  x: number;
  y: number;
  onClose: () => void;
  onNewFolder: () => void;
  onAddFiles: () => void;
}

export function CanvasContextMenu({ x, y, onClose, onNewFolder, onAddFiles }: CanvasContextMenuProps) {
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

  // Clamp within the viewport so a right-click near the edge stays visible.
  const left = typeof window !== 'undefined' ? Math.min(x, window.innerWidth - 200) : x;
  const top = typeof window !== 'undefined' ? Math.min(y, window.innerHeight - 120) : y;

  const run = (fn: () => void) => { fn(); onClose(); };

  return (
    <div
      className="fixed z-50 min-w-[180px] rounded-md border border-border bg-popover py-1 shadow-md"
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
