'use client';

/**
 * FileContextMenu — the shared right-click menu for a workspace file/folder
 * (ADR-400 Amendment 1). ONE menu, mounted on every file surface: the left tree,
 * the RecentsView icon grid, and the ContentViewer folder listing — so the
 * operator can right-click a file wherever its thumbnail is (the macOS/Explorer
 * reference), not only in the left rail.
 *
 * Optimistic model (Windows-Explorer): the verbs are NOT defensively greyed by a
 * client-side topology guess. The operator can invoke them; the backend is
 * authoritative and 403s the rare carve (system/ + machine-config), which the
 * handler surfaces as a clean alert. The FE offers the action; the backend
 * decides. (`operatorCanOrganize` is used only to pre-empt the obvious carve with
 * a nicer message, never to hide the verb — see the handlers in the Files page.)
 *
 * Path-based, not node-based, so any surface can trigger it: a tree node, a
 * RecentsView revision, or a folder-listing child all reduce to { path, name,
 * isFile }.
 */

import { useCallback, useEffect, useState } from 'react';
import { Info, ExternalLink, Pencil, FolderInput, Trash2, Share2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface FileMenuTarget {
  path: string;
  name: string;
  isFile: boolean;
}

/**
 * The operator's file verbs, as a bundle threaded to every file surface (tree,
 * RecentsView grid, ContentViewer listing). Each takes a minimal {path, name}
 * so a surface can build the target from whatever node shape it holds.
 * `onOpen`/`onProperties` are the reads; rename/move/delete are the organize
 * verbs (optimistic — the handler + backend decide, ADR-400 Amendment 1).
 */
export interface FileVerbs {
  onOpen?: (t: { path: string; name: string }) => void;
  onProperties?: (t: { path: string; name: string }) => void;
  onRename?: (t: { path: string; name: string }) => void;
  onMove?: (t: { path: string; name: string }) => void;
  onDelete?: (t: { path: string; name: string }) => void;
  /** Share a link to this artifact (ADR-437 D4 — the cockpit share origin). */
  onShare?: (t: { path: string; name: string }) => void;
}

export interface FileContextMenuProps {
  target: FileMenuTarget;
  x: number;
  y: number;
  onClose: () => void;
  /** Open the file/folder (navigate to it). */
  onOpen?: (t: FileMenuTarget) => void;
  /** Open Properties for the target. */
  onProperties?: (t: FileMenuTarget) => void;
  /** Rename (files only). */
  onRename?: (t: FileMenuTarget) => void;
  /** Move to… (files only). */
  onMove?: (t: FileMenuTarget) => void;
  /** Move to Trash (files only). */
  onDelete?: (t: FileMenuTarget) => void;
  /** Share a link to the target (ADR-437 D4). */
  onShare?: (t: FileMenuTarget) => void;
}

export function FileContextMenu({
  target, x, y, onClose, onOpen, onProperties, onRename, onMove, onDelete, onShare,
}: FileContextMenuProps) {
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

  const run = (fn?: (t: FileMenuTarget) => void) => { fn?.(target); onClose(); };
  const isFile = target.isFile;

  // Clamp within the viewport so a right-click near the edge stays visible.
  const left = typeof window !== 'undefined' ? Math.min(x, window.innerWidth - 200) : x;
  const top = typeof window !== 'undefined' ? Math.min(y, window.innerHeight - 240) : y;

  return (
    <div
      className="fixed z-50 min-w-[180px] rounded-md border border-border bg-popover py-1 shadow-md"
      style={{ left, top }}
      onClick={(e) => e.stopPropagation()}
      onContextMenu={(e) => e.preventDefault()}
    >
      {onOpen && (
        <MenuItem icon={<ExternalLink className="w-3.5 h-3.5 text-muted-foreground" />} onClick={() => run(onOpen)}>
          Open
        </MenuItem>
      )}
      {onProperties && (
        <MenuItem icon={<Info className="w-3.5 h-3.5 text-muted-foreground" />} onClick={() => run(onProperties)}>
          Properties
        </MenuItem>
      )}
      {onShare && (
        <MenuItem icon={<Share2 className="w-3.5 h-3.5 text-muted-foreground" />} onClick={() => run(onShare)}>
          Share…
        </MenuItem>
      )}
      {isFile && (onRename || onMove || onDelete) && <div className="my-1 h-px bg-border/60" />}
      {isFile && onRename && (
        <MenuItem icon={<Pencil className="w-3.5 h-3.5 text-muted-foreground" />} onClick={() => run(onRename)}>
          Rename…
        </MenuItem>
      )}
      {isFile && onMove && (
        <MenuItem icon={<FolderInput className="w-3.5 h-3.5 text-muted-foreground" />} onClick={() => run(onMove)}>
          Move to…
        </MenuItem>
      )}
      {isFile && onDelete && (
        <MenuItem icon={<Trash2 className="w-3.5 h-3.5 text-destructive" />} onClick={() => run(onDelete)} danger>
          Move to Trash
        </MenuItem>
      )}
    </div>
  );
}

function MenuItem({
  icon, children, onClick, danger,
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors',
        danger ? 'text-destructive hover:bg-destructive/10' : 'hover:bg-accent/60',
      )}
    >
      {icon}
      <span className="flex-1">{children}</span>
    </button>
  );
}

/**
 * useFileContextMenu — the shared right-click wiring for a file surface.
 * A surface calls `openMenu(target, event)` on a row/tile's onContextMenu and
 * renders `menu` at the end of its JSX. Keeps the open-state + verb dispatch in
 * one place so the tree, RecentsView grid, and ContentViewer listing don't each
 * re-implement it. Returns null menu when no verbs are wired.
 */
export function useFileContextMenu(verbs: FileVerbs | undefined) {
  const [state, setState] = useState<{ target: FileMenuTarget; x: number; y: number } | null>(null);

  const hasVerbs = !!(verbs && (verbs.onOpen || verbs.onProperties || verbs.onRename || verbs.onMove || verbs.onDelete || verbs.onShare));

  const openMenu = useCallback((target: FileMenuTarget, e: React.MouseEvent) => {
    if (!hasVerbs) return;
    e.preventDefault();
    setState({ target, x: e.clientX, y: e.clientY });
  }, [hasVerbs]);

  const menu = state && verbs ? (
    <FileContextMenu
      target={state.target}
      x={state.x}
      y={state.y}
      onClose={() => setState(null)}
      onOpen={verbs.onOpen ? () => verbs.onOpen!(state.target) : undefined}
      onProperties={verbs.onProperties ? () => verbs.onProperties!(state.target) : undefined}
      onRename={verbs.onRename ? () => verbs.onRename!(state.target) : undefined}
      onMove={verbs.onMove ? () => verbs.onMove!(state.target) : undefined}
      onDelete={verbs.onDelete ? () => verbs.onDelete!(state.target) : undefined}
      onShare={verbs.onShare ? () => verbs.onShare!(state.target) : undefined}
    />
  ) : null;

  return { openMenu, menu, hasVerbs };
}
