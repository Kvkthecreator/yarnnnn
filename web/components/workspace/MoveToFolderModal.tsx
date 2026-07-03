'use client';

/**
 * MoveToFolderModal — the folder-picker for the operator's "Move to…" verb
 * (ADR-400 Q2 / polish, 2026-07-03). Replaces the old
 * `window.prompt('Move to folder (a /workspace/… path):')` — the operator NEVER
 * types a raw workspace path (operator feedback: "move to shouldn't be a URL
 * path input; users will find that discussing"). Instead they pick a destination
 * FOLDER from a compact tree, the way Finder/Explorer's "Move to…" works.
 *
 * Only folders are selectable (you move a file INTO a folder). The current
 * parent is disabled (moving there is a no-op), and any folder the operator
 * can't organize into (system/ + machine-config parents) is disabled via the
 * `canOrganize` predicate — pre-empting the backend 403 with a greyed row, the
 * one place greying is honest (you're choosing a target, not being denied a
 * verb you already invoked).
 *
 * This is also the keyboard/accessibility path for the drag-and-drop the tree
 * offers directly — drag is the fast gesture, this modal is the deliberate one.
 */

import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { ChevronRight, ChevronDown, Folder, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WorkspaceTreeNode } from '@/types';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

interface MoveToFolderModalProps {
  /** The file being moved (null = closed). */
  target: { path: string; name: string } | null;
  /** The workspace root nodes (same tree the explorer renders). */
  roots: WorkspaceTreeNode[];
  /** True iff the operator may organize into this destination path. */
  canOrganize: (path: string) => boolean;
  onClose: () => void;
  /** Called with the chosen destination FOLDER path. */
  onMove: (destFolder: string) => void | Promise<void>;
}

export function MoveToFolderModal({ target, roots, canOrganize, onClose, onMove }: MoveToFolderModalProps) {
  const [selected, setSelected] = useState<string | null>(null);

  // Reset the picked destination whenever the modal opens for a NEW file. The
  // modal stays mounted (target toggles null↔value), so without this a prior
  // move's destination would leak into the next file's move — enabling the
  // "Move here" button with a folder the operator never picked for THIS file.
  useEffect(() => {
    if (target) setSelected(null);
  }, [target]);

  // The file's current parent — moving there is a no-op, so disable it.
  const currentParent = useMemo(
    () => (target ? target.path.slice(0, target.path.lastIndexOf('/')) : null),
    [target],
  );

  if (!target) return null;

  const canMove = selected && selected !== currentParent && canOrganize(`${selected}/x`);

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-black/50 animate-fade-in"
        style={{ zIndex: Z_CONFIRM_BACKDROP }}
        onClick={onClose}
      />
      <div
        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          className="pointer-events-auto flex w-full max-w-md flex-col rounded-lg border border-border bg-card shadow-xl animate-dialog-in"
          role="dialog"
          aria-modal="true"
          style={{ maxHeight: '70vh' }}
        >
          <div className="flex items-start justify-between border-b border-border px-5 py-3.5">
            <div className="min-w-0">
              <h3 className="text-base font-semibold text-card-foreground">Move to…</h3>
              <p className="mt-0.5 truncate text-xs text-muted-foreground">
                Moving “{target.name}”
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="shrink-0 text-muted-foreground/60 transition-colors hover:text-foreground"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
            {roots.map((root) => (
              <FolderRow
                key={root.path}
                node={root}
                depth={0}
                selected={selected}
                onSelect={setSelected}
                currentParent={currentParent}
                canOrganize={canOrganize}
              />
            ))}
          </div>

          <div className="flex items-center justify-between gap-2 border-t border-border px-5 py-3">
            <p className="truncate text-xs text-muted-foreground">
              {selected ? <>Into <span className="font-mono">{shortPath(selected)}</span></> : 'Pick a destination folder'}
            </p>
            <div className="flex shrink-0 gap-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-border px-3.5 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!canMove}
                onClick={() => selected && onMove(selected)}
                className={cn(
                  'rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors',
                  canMove
                    ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                    : 'cursor-not-allowed bg-muted text-muted-foreground',
                )}
              >
                Move here
              </button>
            </div>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}

// A folder-only row. Files are omitted (you move INTO a folder). Rows the
// operator can't organize into are shown disabled (honest pre-empt of the 403).
function FolderRow({
  node,
  depth,
  selected,
  onSelect,
  currentParent,
  canOrganize,
}: {
  node: WorkspaceTreeNode;
  depth: number;
  selected: string | null;
  onSelect: (path: string) => void;
  currentParent: string | null;
  canOrganize: (path: string) => boolean;
}) {
  const [expanded, setExpanded] = useState(depth < 1);
  if (node.type !== 'folder') return null;

  const childFolders = (node.children || []).filter((c) => c.type === 'folder');
  const isCurrent = node.path === currentParent;
  // Can we drop a file into this folder? Probe with a synthetic child path.
  const allowed = canOrganize(`${node.path}/x`) && !isCurrent;
  const isSelected = selected === node.path;

  return (
    <div>
      <div
        className={cn(
          'flex items-center gap-1 rounded-sm py-1 pr-2 text-sm transition-colors',
          isSelected && 'bg-primary/10 font-medium text-primary',
          !allowed && 'opacity-45',
        )}
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
      >
        {childFolders.length > 0 ? (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="shrink-0 text-muted-foreground hover:text-foreground"
            aria-label={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </button>
        ) : (
          <span className="w-3.5 shrink-0" />
        )}
        <button
          type="button"
          disabled={!allowed}
          onClick={() => allowed && onSelect(node.path)}
          className={cn('flex min-w-0 flex-1 items-center gap-1.5 text-left', allowed ? 'cursor-pointer' : 'cursor-not-allowed')}
          title={isCurrent ? 'The file is already here' : !allowed ? 'This folder is managed by the system' : node.path}
        >
          <Folder className="h-3.5 w-3.5 shrink-0 text-blue-500" />
          <span className="truncate">{node.name}</span>
          {isCurrent && <span className="shrink-0 text-[10px] text-muted-foreground">(current)</span>}
        </button>
      </div>
      {expanded && childFolders.map((child) => (
        <FolderRow
          key={child.path}
          node={child}
          depth={depth + 1}
          selected={selected}
          onSelect={onSelect}
          currentParent={currentParent}
          canOrganize={canOrganize}
        />
      ))}
    </div>
  );
}

function shortPath(p: string): string {
  return p.replace(/^\/workspace\//, '');
}
