'use client';

/**
 * WorkspacePicker — the ONE tree picker (2026-07-20 collapse).
 *
 * The OS "Open / Save-As / Move to…" gesture, written once. Before this,
 * `OpenArtifactModal` (pick a file) and `MoveToFolderModal` (pick a folder)
 * each hand-rolled the same portal + z-tier + recursive row + lazy tree fetch
 * + prune-empty-branches grammar — two copies of the Finder's navigable view.
 * `OpenArtifactModal`'s own comment already argued they were siblings; this
 * makes the sibling a single component (CLAUDE.md §2, Singular Implementation).
 *
 * Two axes of variation, both DATA not grammar:
 *   • mode='file'   — leaf files are the selectable target (Open). Folders are
 *                     the path to one. Branches with no selectable leaf are
 *                     pruned — an Open dialog shouldn't offer empty branches.
 *   • mode='folder' — folders are the selectable target (Move / New-destination).
 *                     Files are hidden entirely (you pick a container).
 *
 *   • selectable(node) — the per-act predicate. File mode: is this file openable
 *                        (Open asks ADR-451's resolveSurfaceApplication). Folder
 *                        mode: may the operator organize into here (canOrganize);
 *                        a false folder renders disabled, the honest 403 pre-empt.
 *
 * What this is NOT: a window in the window manager (ADR-297 D15). It's the
 * shared modal PRIMITIVE — the parent modal (Open…/Move…/New) owns the portal,
 * header, footer, and the act-specific copy; this renders only the tree body.
 * Callers that need the whole shell use `WorkspacePickerModal` below.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { ChevronRight, ChevronDown, Folder, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import type { WorkspaceTreeNode } from '@/types';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

export type PickerMode = 'file' | 'folder';

/** How a leaf is labelled + iconed. Open names by ADR-459 meaning + a kind
 *  glyph; the default is the raw leaf name. Folder mode never labels leaves. */
export interface LeafPresenter {
  label: (node: WorkspaceTreeNode) => string;
  icon: (node: WorkspaceTreeNode) => { Glyph: React.ComponentType<{ className?: string }>; className?: string };
}

interface WorkspacePickerBodyProps {
  mode: PickerMode;
  /** File mode: is this file a selectable target? Folder mode: may we organize
   *  into this folder? (false folders render disabled; false files are hidden). */
  selectable: (node: WorkspaceTreeNode) => boolean;
  /** Optional per-folder disable label for folder mode (e.g. "system-managed"). */
  folderDisabledTitle?: (node: WorkspaceTreeNode) => string | undefined;
  /** Optional leaf presenter for file mode (label + icon). */
  leaf?: LeafPresenter;
  /** Roots to render. When omitted, the picker lazy-fetches its own tree. */
  roots?: WorkspaceTreeNode[];
  selected: string | null;
  onSelect: (path: string) => void;
  /** Double-click a file to open immediately (file mode only). */
  onCommit?: (path: string) => void;
  emptyMessage: string;
}

/** The lazy tree fetch both pickers used verbatim — deduped to here. Present
 *  each real root as a folder node carrying its subtree. */
async function fetchRoots(): Promise<WorkspaceTreeNode[]> {
  try {
    const rs = await api.workspace.getRoots();
    const subtrees = await Promise.all(
      rs.map(async (r) => {
        if (!r.exists) return { root: r, tree: [] as WorkspaceTreeNode[] };
        const tree = await api.workspace.getTree(r.path).catch(() => [] as WorkspaceTreeNode[]);
        return { root: r, tree };
      }),
    );
    return subtrees.map(({ root, tree }) => ({
      name: root.display_name || root.name,
      path: root.path,
      type: 'folder' as const,
      children: tree,
    }));
  } catch {
    return [];
  }
}

/** Does this subtree hold anything selectable? (file mode prune). A folder is
 *  itself selectable in folder mode, so folder mode never prunes on this. */
function subtreeHasSelectable(node: WorkspaceTreeNode, selectable: (n: WorkspaceTreeNode) => boolean): boolean {
  if (node.type === 'file') return selectable(node);
  return (node.children || []).some((c) => subtreeHasSelectable(c, selectable));
}

/** The scrollable tree body — the reusable core, no chrome. */
export function WorkspacePickerBody({
  mode,
  selectable,
  folderDisabledTitle,
  leaf,
  roots: providedRoots,
  selected,
  onSelect,
  onCommit,
  emptyMessage,
}: WorkspacePickerBodyProps) {
  const [fetched, setFetched] = useState<WorkspaceTreeNode[] | null>(providedRoots ? providedRoots : null);

  const load = useCallback(async () => {
    setFetched(await fetchRoots());
  }, []);

  useEffect(() => {
    if (providedRoots) {
      setFetched(providedRoots);
    } else if (fetched === null) {
      void load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [providedRoots]);

  // File mode prunes roots with nothing openable inside; folder mode shows all
  // (every folder is a candidate container).
  const shown = useMemo(() => {
    const rs = fetched || [];
    return mode === 'file' ? rs.filter((r) => subtreeHasSelectable(r, selectable)) : rs;
  }, [fetched, mode, selectable]);

  if (fetched === null) {
    return <p className="px-3 py-6 text-center text-xs text-muted-foreground">Looking…</p>;
  }
  if (shown.length === 0) {
    return <p className="px-3 py-6 text-center text-xs text-muted-foreground">{emptyMessage}</p>;
  }

  return (
    <>
      {shown.map((root) => (
        <PickerRow
          key={root.path}
          node={root}
          depth={0}
          mode={mode}
          selectable={selectable}
          folderDisabledTitle={folderDisabledTitle}
          leaf={leaf}
          selected={selected}
          onSelect={onSelect}
          onCommit={onCommit}
        />
      ))}
    </>
  );
}

/** One row — a folder (navigable, selectable in folder mode) or a leaf file
 *  (selectable in file mode). File mode hides non-selectable files and empty
 *  branches; folder mode hides files and disables non-organizable folders. */
function PickerRow({
  node,
  depth,
  mode,
  selectable,
  folderDisabledTitle,
  leaf,
  selected,
  onSelect,
  onCommit,
}: {
  node: WorkspaceTreeNode;
  depth: number;
  mode: PickerMode;
  selectable: (node: WorkspaceTreeNode) => boolean;
  folderDisabledTitle?: (node: WorkspaceTreeNode) => string | undefined;
  leaf?: LeafPresenter;
  selected: string | null;
  onSelect: (path: string) => void;
  onCommit?: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState(depth < (mode === 'folder' ? 1 : 2));

  // ── Leaf file ──────────────────────────────────────────────────────────
  if (node.type === 'file') {
    if (mode === 'folder' || !selectable(node)) return null; // files hidden in folder mode
    const isSelected = selected === node.path;
    const pres = leaf?.icon(node);
    const Glyph = pres?.Glyph;
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
          onDoubleClick={() => onCommit?.(node.path)}
          className="flex min-w-0 flex-1 items-center gap-1.5 text-left"
          title={node.path}
        >
          {Glyph && <Glyph className={cn('h-3.5 w-3.5 shrink-0', pres?.className)} />}
          <span className="truncate">{leaf ? leaf.label(node) : node.name}</span>
        </button>
      </div>
    );
  }

  // ── Folder ─────────────────────────────────────────────────────────────
  // File mode: prune folders with no selectable leaf. Folder mode: keep all.
  const children =
    mode === 'file'
      ? (node.children || []).filter((c) => subtreeHasSelectable(c, selectable))
      : (node.children || []).filter((c) => c.type === 'folder');

  // File mode prunes empties; folder mode always shows the folder (it's a target).
  if (mode === 'file' && children.length === 0) return null;

  const isFolderSelectable = mode === 'folder' && selectable(node);
  const isSelected = selected === node.path;
  const disabledTitle = mode === 'folder' ? folderDisabledTitle?.(node) : undefined;
  const hasChildren = children.length > 0;

  return (
    <div>
      <div
        className={cn(
          'flex items-center gap-1 rounded-sm py-1 pr-2 text-sm transition-colors',
          isSelected && 'bg-primary/10 font-medium text-primary',
          mode === 'folder' && !isFolderSelectable && 'opacity-45',
        )}
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
      >
        {hasChildren ? (
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
          // Folder mode: click selects an organizable folder (or toggles a
          // disabled one open). File mode: the folder is only a path — toggle it.
          disabled={mode === 'folder' && !isFolderSelectable && !hasChildren}
          onClick={() => {
            if (mode === 'folder' && isFolderSelectable) onSelect(node.path);
            else setExpanded((v) => !v);
          }}
          className={cn(
            'flex min-w-0 flex-1 items-center gap-1.5 text-left',
            mode === 'folder' && !isFolderSelectable && !hasChildren && 'cursor-not-allowed',
          )}
          title={disabledTitle || node.path}
        >
          <Folder className="h-3.5 w-3.5 shrink-0 text-blue-500" />
          <span className={cn('truncate', mode === 'file' && 'text-muted-foreground')}>{node.name}</span>
        </button>
      </div>
      {expanded &&
        children.map((child) => (
          <PickerRow
            key={child.path}
            node={child}
            depth={depth + 1}
            mode={mode}
            selectable={selectable}
            folderDisabledTitle={folderDisabledTitle}
            leaf={leaf}
            selected={selected}
            onSelect={onSelect}
            onCommit={onCommit}
          />
        ))}
    </div>
  );
}

interface WorkspacePickerModalProps extends Omit<WorkspacePickerBodyProps, 'selected' | 'onSelect' | 'onCommit'> {
  open: boolean;
  title: string;
  subtitle?: string;
  confirmLabel: string;
  onClose: () => void;
  onConfirm: (path: string) => void;
  /** A footer hint on the left (Move shows the chosen destination path). */
  footerHint?: (selected: string | null) => React.ReactNode;
  /** Reject a selection at confirm time (Move disables the current parent). */
  canConfirm?: (selected: string) => boolean;
}

/** The full Finder-style dialog: backdrop + header + tree body + footer. Open…,
 *  Move to…, and New's destination picker are all thin configs of this. */
export function WorkspacePickerModal({
  open,
  title,
  subtitle,
  confirmLabel,
  onClose,
  onConfirm,
  footerHint,
  canConfirm,
  ...body
}: WorkspacePickerModalProps) {
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (open) setSelected(null);
  }, [open]);

  if (!open) return null;

  const ok = selected && (!canConfirm || canConfirm(selected));

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
          aria-label={title}
          style={{ maxHeight: '70vh' }}
        >
          <div className="flex items-start justify-between border-b border-border px-5 py-3.5">
            <div className="min-w-0">
              <h3 className="text-base font-semibold text-card-foreground">{title}</h3>
              {subtitle && <p className="mt-0.5 truncate text-xs text-muted-foreground">{subtitle}</p>}
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
            <WorkspacePickerBody
              {...body}
              selected={selected}
              onSelect={setSelected}
              onCommit={(p) => (!canConfirm || canConfirm(p)) && onConfirm(p)}
            />
          </div>

          <div className="flex items-center justify-between gap-2 border-t border-border px-5 py-3">
            <div className="min-w-0 truncate text-xs text-muted-foreground">
              {footerHint ? footerHint(selected) : <span />}
            </div>
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
                disabled={!ok}
                onClick={() => ok && onConfirm(selected!)}
                className={cn(
                  'rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors',
                  ok
                    ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                    : 'cursor-not-allowed bg-muted text-muted-foreground',
                )}
              >
                {confirmLabel}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
