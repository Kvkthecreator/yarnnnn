'use client';

/**
 * WorkspaceTree — Left panel file explorer
 *
 * Recursive tree component that mirrors workspace_files paths.
 * Click folder → expand/collapse. Click file → notify parent to open in main panel.
 */

import { useEffect, useState } from 'react';
import { ChevronRight, ChevronDown, Folder, Bot, ListChecks, Settings, Upload, Boxes, Lock, Archive } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WorkspaceTreeNode } from '@/types';
import { FileIcon } from '@/components/workspace/FileIcon';
import { FileContextMenu, type FileMenuTarget } from '@/components/workspace/FileContextMenu';
import { fileLegibilityState, type FileLegibilityState } from '@/lib/workspace/legibility';
import { resolveRootIcon } from '@/lib/workspace/root-icons';

interface WorkspaceTreeProps {
  nodes: WorkspaceTreeNode[];
  selectedPath?: string;
  onSelect: (node: WorkspaceTreeNode) => void;
  /**
   * Right-click "Properties" → open the node Details panel (ADR-400).
   */
  onGetInfo?: (node: WorkspaceTreeNode) => void;
  /**
   * ADR-400 operator verbs — the human reorganizes their workspace. The menu is
   * OPTIMISTIC (Amendment 1): it offers the verb; the parent's handler + the
   * backend decide + surface an honest error on the rare carve. No defensive
   * greying.
   */
  onRename?: (node: WorkspaceTreeNode) => void;
  onMove?: (node: WorkspaceTreeNode) => void;
  onDelete?: (node: WorkspaceTreeNode) => void;
  /**
   * ADR-400 Wave B (2026-07-03) — drag-and-drop move. A file dragged onto a
   * folder calls this with (fromPath, destFolderPath). The native muscle-memory
   * gesture; the menu "Move to…" folder-picker is the deliberate/accessible
   * path. Enabled only when both this + `canOrganize` are provided.
   */
  onMoveByDrag?: (fromPath: string, destFolder: string) => void | Promise<void>;
  /** True iff the operator may organize `path` — gates draggable + droppable. */
  canOrganize?: (path: string) => boolean;
}

interface ContextMenuState {
  target: FileMenuTarget;
  node: WorkspaceTreeNode;
  x: number;
  y: number;
}

export function WorkspaceTree({ nodes, selectedPath, onSelect, onGetInfo, onRename, onMove, onDelete, onMoveByDrag, canOrganize }: WorkspaceTreeProps) {
  const [menu, setMenu] = useState<ContextMenuState | null>(null);
  // ADR-400 Wave B: which folder path is the current drag-over drop target
  // (for the highlight). Lifted here so only one row highlights at a time.
  const [dropTarget, setDropTarget] = useState<string | null>(null);

  const hasMenu = !!(onGetInfo || onRename || onMove || onDelete);
  const openMenu = hasMenu
    ? (node: WorkspaceTreeNode, e: React.MouseEvent) => {
        e.preventDefault();
        setMenu({
          target: { path: node.path, name: node.name, isFile: node.type === 'file' },
          node, x: e.clientX, y: e.clientY,
        });
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
          onContextMenu={openMenu}
          dnd={dnd}
        />
      ))}

      {menu && (
        <FileContextMenu
          target={menu.target}
          x={menu.x}
          y={menu.y}
          onClose={() => setMenu(null)}
          onOpen={() => onSelect(menu.node)}
          onProperties={onGetInfo ? () => onGetInfo(menu.node) : undefined}
          onRename={onRename ? () => onRename(menu.node) : undefined}
          onMove={onMove ? () => onMove(menu.node) : undefined}
          onDelete={onDelete ? () => onDelete(menu.node) : undefined}
        />
      )}
    </div>
  );
}

interface DndBundle {
  canOrganize: (path: string) => boolean;
  dropTarget: string | null;
  setDropTarget: (path: string | null) => void;
  onDrop: (fromPath: string, destFolder: string) => void;
}

interface TreeItemProps {
  node: WorkspaceTreeNode;
  depth: number;
  selectedPath?: string;
  onSelect: (node: WorkspaceTreeNode) => void;
  onContextMenu?: (node: WorkspaceTreeNode, e: React.MouseEvent) => void;
  dnd?: DndBundle;
}

// The dataTransfer key for a dragged workspace file path (ADR-400 Wave B).
const DRAG_MIME = 'application/x-yarnnn-path';

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
          if (!e.dataTransfer.types.includes(DRAG_MIME)) return;
          e.preventDefault();
          e.dataTransfer.dropEffect = 'move';
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
          }
        },
      }
    : {};

  useEffect(() => {
    if (isFolder && selectedPath && nodeContainsPath(node, selectedPath)) {
      setExpanded(true);
    }
  }, [isFolder, node, selectedPath]);

  const handleClick = () => {
    if (isFolder) {
      setExpanded(!expanded);
    }
    onSelect(node);
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
