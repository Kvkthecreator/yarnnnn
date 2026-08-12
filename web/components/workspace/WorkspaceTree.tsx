'use client';


/**
 * WorkspaceTree — Left panel file explorer
 *
 * Recursive tree component that mirrors workspace_files paths.
 * Click folder → expand/collapse. Click file → notify parent to open in main panel.
 */

import { useEffect, useMemo, useState } from 'react';
import { ChevronRight, ChevronDown, Folder, Bot, ListChecks, Settings, Upload, Boxes, Lock, Archive } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WorkspaceTreeNode } from '@/types';
import { FileIcon } from '@/components/workspace/FileIcon';
import { TILE_DRAG_MIME } from '@/components/workspace/FileTile';
import { useFileContextMenu, type FileVerbs } from '@/components/workspace/FileContextMenu';
import { fileLegibilityState, type FileLegibilityState } from '@/lib/workspace/legibility';
import { resolveRootIcon } from '@/lib/workspace/root-icons';

interface WorkspaceTreeProps {
  nodes: WorkspaceTreeNode[];
  selectedPath?: string;
  onSelect: (node: WorkspaceTreeNode, e?: { metaKey?: boolean; ctrlKey?: boolean }) => void;
  /**
   * ADR-514 D2.6 — the verb bundle, WHOLE. This prop replaced a hand-listed
   * subset (`onGetInfo`/`onRename`/`onMove`/`onDelete`/`onDuplicate`), which was
   * a standing defect generator: every new verb had to be threaded through the
   * wall by hand, and one that wasn't simply vanished from this mount. That is
   * exactly how Duplicate shipped absent from the Explorer while the grid — same
   * FileContextMenu — offered it (found live 2026-08-03), and why Share… was
   * missing here too. Taking `FileVerbs` whole means a verb wired once reaches
   * every mount, and Open With (a variable-length submenu, not a single
   * callback) becomes expressible at all.
   *
   * The menu stays OPTIMISTIC (ADR-400 Amendment 1): it offers the verb; the
   * parent's handler + the backend decide and surface an honest error on the
   * rare carve. No defensive greying.
   */
  verbs?: FileVerbs;
  /**
   * ADR-400 Wave B (2026-07-03) — drag-and-drop move. A file dragged onto a
   * folder calls this with (fromPath, destFolderPath). The native muscle-memory
   * gesture; the menu "Move to…" folder-picker is the deliberate/accessible
   * path. Enabled only when both this + `canOrganize` are provided.
   */
  onMoveByDrag?: (fromPath: string, destFolder: string) => void | Promise<void>;
  /**
   * OS files were dropped on a folder row — import them THERE (ADR-555 D3).
   * Absent, a folder row ignores file drops and only accepts internal moves.
   */
  onDropFiles?: (files: File[], folder: { path: string; name: string }) => void;
  /** True iff the operator may organize `path` — gates draggable + droppable. */
  canOrganize?: (path: string) => boolean;
}

export function WorkspaceTree({ nodes, selectedPath, onSelect, verbs, onMoveByDrag, onDropFiles, canOrganize }: WorkspaceTreeProps) {
  // ADR-400 Wave B: which folder path is the current drag-over drop target
  // (for the highlight). Lifted here so only one row highlights at a time.
  const [dropTarget, setDropTarget] = useState<string | null>(null);

  // The menu's Open falls back to the tree's own select, so a click and the
  // menu's Open are the same act even when the caller wired no onOpen.
  const menuVerbs = useMemo<FileVerbs | undefined>(() => {
    if (!verbs || verbs.onOpen) return verbs;
    return {
      ...verbs,
      onOpen: (t) => {
        const node = findNodeByPath(nodes, t.path);
        if (node) onSelect(node);
      },
    };
  }, [verbs, nodes, onSelect]);

  // The SHARED open-state machine (useFileContextMenu) — the same one the
  // folder listing, RecentsView grid and Studio recents mount. The tree
  // previously kept a local useState + a raw spread of the bundle straight
  // into the menu component, which could not translate `handlersFor` (a
  // function on FileVerbs) into `handlers` (the resolved array the menu
  // renders) — so Open With ▸ silently never appeared on this mount. Third
  // recurrence of the per-mount drift class (Duplicate, Share…, then Open
  // With); the hook is the one translation site, so a verb wired once now
  // reaches every mount identically.
  const { openMenu, menu, hasVerbs } = useFileContextMenu(menuVerbs);
  const onNodeContextMenu = hasVerbs
    ? (node: WorkspaceTreeNode, e: React.MouseEvent) => {
        openMenu({ path: node.path, name: node.name, isFile: node.type === 'file' }, e);
      }
    : undefined;

  // Drag-and-drop is enabled only when both the callback + the ownership
  // predicate are wired. A file is draggable iff the operator can organize it;
  // a folder is a drop target iff the operator can organize into it.
  const dnd = onMoveByDrag && canOrganize
    ? {
        canOrganize,
        dropTarget,
        setDropTarget,
        onDropFiles,
        onDrop: (fromPath: string, destFolder: string) => {
          setDropTarget(null);
          if (fromPath === destFolder) return;
          // No-op if already the direct parent.
          const parent = fromPath.slice(0, fromPath.lastIndexOf('/'));
          if (parent === destFolder) return;
          onMoveByDrag(fromPath, destFolder);
        },
      }
    : undefined;

  return (
    <div className="text-sm">
      {nodes.map((node) => (
        <TreeItem
          key={node.path}
          node={node}
          depth={0}
          selectedPath={selectedPath}
          onSelect={onSelect}
          onContextMenu={onNodeContextMenu}
          dnd={dnd}
        />
      ))}

      {menu}
    </div>
  );
}

interface DndBundle {
  canOrganize: (path: string) => boolean;
  dropTarget: string | null;
  setDropTarget: (path: string | null) => void;
  onDrop: (fromPath: string, destFolder: string) => void;
  /** OS files dropped on a folder row — import them there (ADR-555 D3). */
  onDropFiles?: (files: File[], folder: { path: string; name: string }) => void;
}

interface TreeItemProps {
  node: WorkspaceTreeNode;
  depth: number;
  selectedPath?: string;
  onSelect: (node: WorkspaceTreeNode, e?: { metaKey?: boolean; ctrlKey?: boolean }) => void;
  onContextMenu?: (node: WorkspaceTreeNode, e: React.MouseEvent) => void;
  dnd?: DndBundle;
}

// The dataTransfer key for a dragged workspace file path (ADR-400 Wave B).
// IMPORTED, not re-declared (ADR-552): the grid and the tree are two halves of
// one surface, and two independent literals of the same string would let a
// rename silently make them refuse each other's drags.
const DRAG_MIME = TILE_DRAG_MIME;

// ADR-422 D1: a file's legibility state (machine-config / raw-intake /
// agent-authored / operator) drives its tree affordance. This REPLACES the old
// coarse `_`-prefix `isSystemFile` heuristic, which mislabeled prose files like
// `_notes.md` as "system". machine-config + raw-intake render de-emphasized with
// a distinct glyph (lock / archive); agent-authored + operator render normally.
// Derived from path + authored_by already on the node — no new backend data.

// A file is de-emphasized (dimmer) iff it's system-managed config or an
// immutable record — not the operator's freely-editable prose.
function isDeEmphasized(state: FileLegibilityState): boolean {
  return state === 'machine-config' || state === 'raw-intake';
}

// ADR-423 follow-on: the collapsed "System files" disclosure (the OS
// "Show system files" model) — kernel residue folded out of the operator's way.
// It must start COLLAPSED even though it's a depth-0 node, so it doesn't spill
// the residue the fold exists to hide. Mirrors SYSTEM_FILES_NODE_PATH in the
// Files page (a virtual /explorer/ handle).
const SYSTEM_FILES_NODE_PATH = '/explorer/system-files';

function TreeItem({ node, depth, selectedPath, onSelect, onContextMenu, dnd }: TreeItemProps) {
  // Auto-expand the first level — EXCEPT the "System files" fold, which stays
  // collapsed (it's the hidden residue; the operator opens it deliberately).
  const [expanded, setExpanded] = useState(
    depth < 1 && node.path !== SYSTEM_FILES_NODE_PATH,
  );
  const isFolder = node.type === 'folder';
  const isSelected = selectedPath === node.path;
  // ADR-422 D1: the file's legibility state → its affordance (folders are always
  // 'operator' — no not-editable treatment).
  const legibility = fileLegibilityState(node);
  const deEmphasized = isDeEmphasized(legibility);

  // ADR-400 Wave B drag-and-drop.
  // A FILE is draggable iff the operator can organize it (system/ + machine-
  // config are not draggable). A FOLDER is a drop target iff the operator can
  // organize into it — probed with a synthetic child path.
  const draggable = !!dnd && !isFolder && dnd.canOrganize(node.path);
  const isDropTarget = !!dnd && isFolder && dnd.canOrganize(`${node.path}/x`);
  const isDropHover = !!dnd && dnd.dropTarget === node.path;

  const dragProps = draggable
    ? {
        draggable: true as const,
        onDragStart: (e: React.DragEvent) => {
          e.dataTransfer.setData(DRAG_MIME, node.path);
          e.dataTransfer.effectAllowed = 'move';
        },
        // dragend fires on the SOURCE when the drag ends however it ends
        // (dropped, or aborted via Esc / released over a non-target). Clear the
        // highlight so an aborted drag never leaves a folder stuck highlighted.
        onDragEnd: () => dnd?.setDropTarget(null),
      }
    : {};

  const dropProps = isDropTarget && dnd
    ? {
        onDragOver: (e: React.DragEvent) => {
          // ADR-555: a folder row accepts BOTH an internal move (a workspace
          // path) and an OS-file import. Only the first was handled, so
          // dropping a PDF on `fundraising/` — the most direct expression of
          // "put this here" — was silently swallowed.
          const types = Array.from(e.dataTransfer.types || []);
          const internal = types.includes(DRAG_MIME);
          if (!internal && !(types.includes('Files') && dnd.onDropFiles)) return;
          e.preventDefault();
          e.dataTransfer.dropEffect = internal ? 'move' : 'copy';
          if (dnd.dropTarget !== node.path) dnd.setDropTarget(node.path);
        },
        onDragLeave: (e: React.DragEvent) => {
          // Only clear if we're actually leaving this row (not entering a child).
          if (!e.currentTarget.contains(e.relatedTarget as Node)) {
            if (dnd.dropTarget === node.path) dnd.setDropTarget(null);
          }
        },
        onDrop: (e: React.DragEvent) => {
          const from = e.dataTransfer.getData(DRAG_MIME);
          if (from) {
            e.preventDefault();
            dnd.onDrop(from, node.path);
            return;
          }
          const files = Array.from(e.dataTransfer.files || []);
          if (files.length && dnd.onDropFiles) {
            e.preventDefault();
            dnd.setDropTarget(null);
            dnd.onDropFiles(files, { path: node.path, name: node.name });
          }
        },
      }
    : {};

  useEffect(() => {
    if (isFolder && selectedPath && nodeContainsPath(node, selectedPath)) {
      setExpanded(true);
    }
  }, [isFolder, node, selectedPath]);

  const handleClick = (e?: React.MouseEvent) => {
    // ADR-553 D1: a ⌘/Ctrl-click is an ADDITIVE pick — it must not also toggle
    // the folder's disclosure, or the set gesture and the navigate gesture
    // fight over one click.
    const additive = !!(e && (e.metaKey || e.ctrlKey));
    if (isFolder && !additive) {
      setExpanded(!expanded);
    }
    onSelect(node, e ? { metaKey: e.metaKey, ctrlKey: e.ctrlKey } : undefined);
  };

  // Icon based on path/type
  const icon = isFolder ? (
    expanded ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
  ) : null;

  const fileIcon = getFileIcon(node);

  return (
    <div>
      <button
        onClick={handleClick}
        onContextMenu={onContextMenu ? (e) => onContextMenu(node, e) : undefined}
        {...dragProps}
        {...dropProps}
        className={cn(
          "w-full flex items-center gap-1.5 py-1 px-2 rounded-sm text-left hover:bg-accent/50 transition-colors",
          isSelected && "bg-primary/10 text-primary font-medium",
          // ADR-422 D1: machine-config + raw-intake render de-emphasized (dimmer
          // text) rather than hidden — present but visibly secondary (supersedes
          // the ADR-320 `_`-prefix de-emphasis, which mislabeled prose).
          deEmphasized && !isSelected && "text-muted-foreground/55",
          // ADR-400 Wave B: drop-target highlight while a file drags over.
          isDropHover && "ring-2 ring-inset ring-primary/60 bg-primary/5",
          draggable && "cursor-grab active:cursor-grabbing",
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {isFolder && icon}
        {!isFolder && <span className="w-3.5" />}
        {fileIcon}
        <span className="truncate flex-1">{node.name}</span>
        {/* ADR-422 D1: the not-editable-state affordance — a plain glyph, not the
            developer `sys` word (ADR-410 D4). A lock = system-managed config the
            operator tunes in Settings; an archive = an immutable record of what
            came in. agent-authored + operator files carry no tree glyph (their
            authorship lives in the header + Get-Info, ADR-388 D3). The glyph is a
            quiet trailing hint; the full "why" is stated in Get-Info (D4). */}
        {legibility === 'machine-config' && (
          <Lock className="shrink-0 w-3 h-3 text-muted-foreground/40 ml-1" aria-label="Managed by the system" />
        )}
        {legibility === 'raw-intake' && (
          <Archive className="shrink-0 w-3 h-3 text-muted-foreground/40 ml-1" aria-label="A record of what came in" />
        )}
        {/* ADR-388 follow-up: author dots removed from the tree. An unlabeled
            color dot is a riddle — "who wrote it" now lives where it's a full
            legible label (the file header + the Get-Info modal), not a color
            the operator must decode. The tree is for navigation. */}
      </button>
      {isFolder && expanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeItem
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelect={onSelect}
              onContextMenu={onContextMenu}
              dnd={dnd}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function findNodeByPath(nodes: WorkspaceTreeNode[], targetPath: string): WorkspaceTreeNode | null {
  for (const node of nodes) {
    if (node.path === targetPath) return node;
    const hit = findNodeByPath(node.children || [], targetPath);
    if (hit) return hit;
  }
  return null;
}

function nodeContainsPath(node: WorkspaceTreeNode, targetPath: string): boolean {
  if (node.path === targetPath) return true;
  for (const child of node.children || []) {
    if (nodeContainsPath(child, targetPath)) return true;
  }
  return false;
}

function getFileIcon(node: WorkspaceTreeNode) {
  const path = node.path.toLowerCase();

  if (node.type === 'folder') {
    // ADR-422 D3: a ROOT node carries the kernel-named glyph (WORKSPACE_ROOTS
    // in workspace_paths.py) — prefer it over the path-string guesses below, so
    // constitution/governance/contract/inbound get their real glyph (before,
    // they all fell to the generic folder). An unmapped root → generic folder
    // (forward-compat with re-founding roots, ADR-388 §6).
    if (node.icon_name) {
      const RootIcon = resolveRootIcon(node.icon_name);
      return <RootIcon className="w-3.5 h-3.5 text-muted-foreground" />;
    }
    // Virtual /explorer/* group nodes (no backend root behind them).
    if (path === '/explorer/settings') return <Settings className="w-3.5 h-3.5 text-slate-500" />;
    if (path === '/explorer/context') return <Boxes className="w-3.5 h-3.5 text-sky-600" />;
    if (path === '/explorer/outputs') return <ListChecks className="w-3.5 h-3.5 text-orange-500" />;
    if (path === '/explorer/uploads' || path === '/workspace/uploads') return <Upload className="w-3.5 h-3.5 text-emerald-600" />;
    if (path === '/workspace/persona') return <Bot className="w-3.5 h-3.5 text-rose-500" />;
    if (path === '/workspace/system') return <Settings className="w-3.5 h-3.5 text-zinc-500" />;
    if (path === '/workspace/agents') return <Bot className="w-3.5 h-3.5 text-purple-500" />;
    // Substrate folder children (ADR-320 topology).
    if (path.includes('/agents/')) return <Bot className="w-3.5 h-3.5 text-purple-500" />;
    if (path.includes('/operation/reports/')) return <ListChecks className="w-3.5 h-3.5 text-orange-500" />;
    if (path.startsWith('/workspace/operation/')) return <Folder className="w-3.5 h-3.5 text-blue-500" />;
    return <Folder className="w-3.5 h-3.5 text-muted-foreground" />;
  }

  return <FileIcon filename={node.name} size="sm" />;
}
