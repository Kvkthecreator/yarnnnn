'use client';

/**
 * OpenArtifactModal — the Studio's "Open…" file browser (ADR-459 follow-on).
 *
 * Replaces a bare `<details>` disclosure holding a font-mono path input
 * ("operation/…/deck.html"). Typing a raw workspace path is the same
 * workbench gesture ADR-400 Q2 already refused for Move ("move to shouldn't
 * be a URL path input") — the member picks their work from a tree, the way
 * an OS Open dialog works. Same reasoning, same shell: this is a sibling of
 * `MoveToFolderModal`, deliberately mirroring its portal + z-tier + row
 * structure rather than inventing a second modal grammar.
 *
 * The inversion vs. Move: Move picks a FOLDER (you move INTO one) and hides
 * files; Open picks a FILE and shows folders only as the path to one.
 *
 * What's openable is NOT a Studio-local rule — it's ADR-451's
 * `resolveSurfaceApplication`, the same registry that routes the Files
 * surface's open verb (Finder → PowerPoint). The Studio never hardcodes
 * ".html": it asks the OS which app owns the type, and shows what it owns.
 * A folder with nothing openable inside is pruned rather than shown as a
 * dead end — an Open dialog that offers empty branches is lying about where
 * work is.
 *
 * Named by ADR-459's rule: the row shows what the artifact IS (its titleized
 * meaning folder), never its `.html` storage encoding. This modal is a
 * COMPOSITION (one operator act: open my work), so it reads like a Mac.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { ChevronRight, ChevronDown, Folder, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import type { WorkspaceTreeNode } from '@/types';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';
import { resolveSurfaceApplication } from '@/lib/file-types';
import { studioShapeStyle } from './studioShapes';
import { artifactNameFromPath, kindGuessFromPath } from './artifactNaming';

interface OpenArtifactModalProps {
  open: boolean;
  onClose: () => void;
  /** Called with the chosen artifact's workspace path. */
  onOpen: (path: string) => void;
}

/** True iff this file is one the Studio owns — asked of the OS's type→app
 *  registry (ADR-451), never of a local extension test. */
function isOpenable(node: WorkspaceTreeNode): boolean {
  return node.type === 'file' && resolveSurfaceApplication(node.path)?.surface === 'studio';
}

/** Does this subtree hold anything the Studio can open? Folders that don't are
 *  pruned — an Open dialog shouldn't offer branches with no work in them. */
function hasOpenable(node: WorkspaceTreeNode): boolean {
  if (isOpenable(node)) return true;
  return (node.children || []).some(hasOpenable);
}

export function OpenArtifactModal({ open, onClose, onOpen }: OpenArtifactModalProps) {
  const [roots, setRoots] = useState<WorkspaceTreeNode[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  // Lazy-fetch the tree on first open — a member who never browses never pays
  // for it (the `loadMoveRoots` shape from useFileOrganizeVerbs).
  const loadRoots = useCallback(async () => {
    try {
      const rs = await api.workspace.getRoots();
      const subtrees = await Promise.all(
        rs.map(async (r) => {
          if (!r.exists) return { root: r, tree: [] as WorkspaceTreeNode[] };
          const tree = await api.workspace.getTree(r.path).catch(() => [] as WorkspaceTreeNode[]);
          return { root: r, tree };
        }),
      );
      setRoots(
        subtrees.map(({ root, tree }) => ({
          name: root.display_name || root.name,
          path: root.path,
          type: 'folder' as const,
          children: tree,
        })),
      );
    } catch {
      setRoots([]); // an empty picker still cancels cleanly
    }
  }, []);

  useEffect(() => {
    if (open) {
      setSelected(null);
      if (roots === null) void loadRoots();
    }
  }, [open, roots, loadRoots]);

  // Only roots holding openable work — computed once per tree, not per render.
  const shown = useMemo(() => (roots || []).filter(hasOpenable), [roots]);

  if (!open) return null;

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-black/50 animate-in fade-in duration-150"
        style={{ zIndex: Z_CONFIRM_BACKDROP }}
        onClick={onClose}
      />
      <div
        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          className="pointer-events-auto flex w-full max-w-md flex-col rounded-lg border border-border bg-card shadow-xl animate-in fade-in zoom-in-95 duration-150"
          role="dialog"
          aria-modal="true"
          aria-label="Open an artifact"
          style={{ maxHeight: '70vh' }}
        >
          <div className="flex items-start justify-between border-b border-border px-5 py-3.5">
            <div className="min-w-0">
              <h3 className="text-base font-semibold text-card-foreground">Open…</h3>
              <p className="mt-0.5 truncate text-xs text-muted-foreground">
                Pick something you&rsquo;ve made
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
            {roots === null ? (
              <p className="px-3 py-6 text-center text-xs text-muted-foreground">Looking…</p>
            ) : shown.length === 0 ? (
              <p className="px-3 py-6 text-center text-xs text-muted-foreground">
                Nothing to open yet — hit New to make something.
              </p>
            ) : (
              shown.map((root) => (
                <PickerRow
                  key={root.path}
                  node={root}
                  depth={0}
                  selected={selected}
                  onSelect={setSelected}
                  onOpen={onOpen}
                />
              ))
            )}
          </div>

          <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-border px-3.5 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={!selected}
              onClick={() => selected && onOpen(selected)}
              className={cn(
                'rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors',
                selected
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'cursor-not-allowed bg-muted text-muted-foreground',
              )}
            >
              Open
            </button>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}

/** One row: a folder (navigable) or an openable artifact (selectable).
 *  Non-openable files are omitted — this dialog opens Studio work, and the
 *  Files surface remains the mirror that shows everything. */
function PickerRow({
  node,
  depth,
  selected,
  onSelect,
  onOpen,
}: {
  node: WorkspaceTreeNode;
  depth: number;
  selected: string | null;
  onSelect: (path: string) => void;
  onOpen: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState(depth < 2);

  if (node.type === 'file') {
    if (!isOpenable(node)) return null;
    const isSelected = selected === node.path;
    // ADR-459: the row is named by what it IS — the meaning folder — never
    // by `deck.html`. The kind's glyph carries the shape at a glance.
    const style = studioShapeStyle(kindGuessFromPath(node.path));
    const Glyph = style.icon;
    return (
      <div
        className={cn(
          'flex items-center gap-1 rounded-sm py-1 pr-2 text-sm transition-colors',
          isSelected && 'bg-primary/10 font-medium text-primary',
        )}
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
      >
        <span className="w-3.5 shrink-0" />
        <button
          type="button"
          onClick={() => onSelect(node.path)}
          onDoubleClick={() => onOpen(node.path)}
          className="flex min-w-0 flex-1 items-center gap-1.5 text-left"
          title={node.path}
        >
          <Glyph className={cn('h-3.5 w-3.5 shrink-0', style.color)} />
          <span className="truncate">{artifactNameFromPath(node.path)}</span>
        </button>
      </div>
    );
  }

  const children = (node.children || []).filter(hasOpenable);
  if (children.length === 0) return null;

  return (
    <div>
      <div
        className="flex items-center gap-1 rounded-sm py-1 pr-2 text-sm"
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
      >
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="shrink-0 text-muted-foreground hover:text-foreground"
          aria-label={expanded ? 'Collapse' : 'Expand'}
        >
          {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </button>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="flex min-w-0 flex-1 items-center gap-1.5 text-left"
          title={node.path}
        >
          <Folder className="h-3.5 w-3.5 shrink-0 text-blue-500" />
          <span className="truncate text-muted-foreground">{node.name}</span>
        </button>
      </div>
      {expanded &&
        children.map((child) => (
          <PickerRow
            key={child.path}
            node={child}
            depth={depth + 1}
            selected={selected}
            onSelect={onSelect}
            onOpen={onOpen}
          />
        ))}
    </div>
  );
}

