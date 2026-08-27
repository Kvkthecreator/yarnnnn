'use client';


/**
 * WorkspaceTree — the left pane's FOLDER NAVIGATOR.
 *
 * TWO PANES, TWO GRAMMARS (2026-08-20, second cut). The first cut of the
 * select/open split applied ONE grammar to both panes, and that was the error:
 * they are not two renderers of the same thing.
 *
 *   left tree    a NAVIGATOR — the folder hierarchy you move THROUGH.
 *                FOLDERS ONLY. A single click navigates the centre pane to that
 *                folder and toggles its disclosure. One gesture, one meaning.
 *                No selection, no multi-select, no open.
 *
 *   centre pane  a FILE BROWSER — the contents of the folder you are standing
 *                in. Single click selects · ⌘/shift multi-select · double click
 *                opens. That grammar lives in the Files surface + ContentViewer.
 *
 * Windows Explorer and macOS Finder both show FOLDERS ONLY in the left tree.
 * Files never appear there, so "does clicking a file in the tree open it?"
 * never arises — the question the first cut had to keep answering, and answered
 * by bleeding the selection model into a pane that has nothing to select.
 * (Operator-observed: clicking a FILE in the tree raised a floating
 * Move…/Open/Clear chip next to Properties.)
 *
 * The consequence is deliberate and correct: THE TREE CAN NO LONGER OPEN A
 * FILE AT ALL. The centre pane is the only route to a document.
 *
 * The one highlight this pane draws follows the centre pane — whichever folder
 * it is currently standing in. It is a "you are here", not a selection; nothing
 * here is pickable, so there is nothing for a second treatment to say.
 *
 * "Standing in" is the load-bearing phrase, and it is NOT `viewPath` verbatim:
 * the centre pane can be showing a FILE, and this pane has no file rows. The
 * incoming path is resolved to its containing folder ONCE (`containingFolder`)
 * and the highlight + the auto-expand both read that one answer — see the note
 * there for the defect that made it necessary.
 */

import { useEffect, useMemo, useState } from 'react';
import { ChevronRight, ChevronDown, Folder, Bot, ListChecks, Settings, Upload, Boxes } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WorkspaceTreeNode } from '@/types';
import { TILE_DRAG_MIME } from '@/components/workspace/FileTile';
import { useFileContextMenu, type FileVerbs } from '@/components/workspace/FileContextMenu';
import { resolveRootIcon } from '@/lib/workspace/root-icons';

interface WorkspaceTreeProps {
  /**
   * The workspace tree AS LOADED — files included. This component filters them
   * out itself (`foldersOnly` below) rather than asking its caller to hand over
   * a pre-pruned tree, because the SAME `treeNodes` array feeds the Move
   * picker and resolves what the centre pane shows. Pruning at the source
   * would take folders' file children away from those consumers too.
   */
  nodes: WorkspaceTreeNode[];
  /**
   * What the centre pane is SHOWING — a folder OR A FILE. Both are accepted
   * deliberately: the caller holds one `viewPath` for both kinds, and making it
   * pre-resolve the folder would put the tree's own rendering rule in the
   * surface. This pane resolves it (`containingFolder`) and points at the
   * folder that path lives in.
   */
  viewPath?: string;
  /**
   * Navigate the centre pane to this folder. No event, no modifiers: a tree
   * click has exactly one meaning, so there is no intent for the surface to
   * disambiguate.
   */
  onNavigate: (node: WorkspaceTreeNode) => void;
  /**
   * ADR-514 D2.6 — the verb bundle, WHOLE. This prop replaced a hand-listed
   * subset (`onGetInfo`/`onRename`/`onMove`/`onDelete`/`onDuplicate`), which was
   * a standing defect generator: every new verb had to be threaded through the
   * wall by hand, and one that wasn't simply vanished from this mount.
   *
   * Every target here is a FOLDER, so the file-only entries in the shared menu
   * (Rename… / Move to… / Duplicate / Move to Trash / Download / Open With)
   * self-suppress on `isFile: false` — the tree offers Open · Properties ·
   * Share… · New Folder, which is exactly the Explorer folder-row menu.
   *
   * The menu stays OPTIMISTIC (ADR-400 Amendment 1): it offers the verb; the
   * parent's handler + the backend decide and surface an honest error on the
   * rare carve. No defensive greying.
   */
  verbs?: FileVerbs;
  /**
   * ADR-400 Wave B (2026-07-03) — drag-and-drop move. A file dragged from the
   * CENTRE PANE onto a folder row here calls this with (fromPath,
   * destFolderPath). The tree is a drop DESTINATION only: with no files in it,
   * nothing here is draggable, and the drag SOURCE is the listing.
   */
  onMoveByDrag?: (fromPath: string, destFolder: string) => void | Promise<void>;
  /**
   * OS files were dropped on a folder row — import them THERE (ADR-555 D3).
   * Absent, a folder row ignores file drops and only accepts internal moves.
   */
  onDropFiles?: (files: File[], folder: { path: string; name: string }) => void;
  /** True iff the operator may organize `path` — gates droppable. */
  canOrganize?: (path: string) => boolean;
}

/**
 * FOLDERS ONLY, at every depth — the whole point of this pane.
 *
 * Applied to the RENDER, not to the data: `nodes` is shared with the Move
 * picker and with the centre pane's node resolution, and both of those need
 * the files.
 *
 * One subtlety worth stating, because it is the case that looks like a bug: a
 * folder whose children are ALL files (a report folder, a domain leaf) keeps
 * its row and simply has no branch to unfold. That is correct — it is still a
 * place you navigate to, and its contents show in the centre pane, which is
 * where files live now.
 */
function foldersOnly(nodes: WorkspaceTreeNode[] | undefined): WorkspaceTreeNode[] {
  return (nodes ?? [])
    .filter((n) => n.type === 'folder')
    .map((n) => ({ ...n, children: foldersOnly(n.children) }));
}

/**
 * The FOLDER the tree should point at, for any `viewPath` (2026-08-27).
 *
 * `viewPath` is whatever the centre pane is showing — a folder OR A FILE. This
 * pane renders folders only, so a file path matched no node, and BOTH halves of
 * "you are here" silently went false: the row stopped highlighting AND the
 * branch stopped revealing itself. Open a file and the tree forgot where you
 * were standing (operator-observed: "sometimes its highlight, other times its
 * not").
 *
 * Resolved ONCE, here, so the highlight and the auto-expand cannot answer that
 * question differently again — they were already inconsistent (`===` vs an
 * ancestor walk), which is how one pane came to hold two ideas of where it was.
 *
 * A folder path resolves to itself: `/w/a/b` has no live row at `/w/a/b` unless
 * it is a file, and the tree's own nodes are the authority on which it is. So
 * the trim happens only when the path is NOT a folder in this tree.
 */
function containingFolder(
  nodes: WorkspaceTreeNode[],
  viewPath: string | undefined,
): string | undefined {
  if (!viewPath) return undefined;
  if (findNodeByPath(nodes, viewPath)) return viewPath; // already a folder here
  const parent = viewPath.slice(0, viewPath.lastIndexOf('/'));
  return parent || undefined;
}

export function WorkspaceTree({ nodes, viewPath, onNavigate, verbs, onMoveByDrag, onDropFiles, canOrganize }: WorkspaceTreeProps) {
  const folderNodes = useMemo(() => foldersOnly(nodes), [nodes]);
  // What the tree points at: the folder the centre pane is standing in, which
  // is the containing folder when the pane is showing a FILE.
  const shownFolder = useMemo(
    () => containingFolder(folderNodes, viewPath),
    [folderNodes, viewPath],
  );
  // ADR-400 Wave B: which folder path is the current drag-over drop target
  // (for the highlight). Lifted here so only one row highlights at a time.
  const [dropTarget, setDropTarget] = useState<string | null>(null);

  // The menu's Open falls back to the tree's own navigate, so a click and the
  // menu's Open are the same act even when the caller wired no onOpen. Both
  // mean "show me this folder" — there is no other thing Open could mean on a
  // pane that holds only folders.
  const menuVerbs = useMemo<FileVerbs | undefined>(() => {
    if (!verbs || verbs.onOpen) return verbs;
    return {
      ...verbs,
      onOpen: (t) => {
        const node = findNodeByPath(folderNodes, t.path);
        if (node) onNavigate(node);
      },
    };
  }, [verbs, folderNodes, onNavigate]);

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
        // `isFile: false` always — this pane renders nothing else.
        openMenu({ path: node.path, name: node.name, isFile: false }, e);
      }
    : undefined;

  // Drag-and-drop is enabled only when both the callback + the ownership
  // predicate are wired. A folder is a drop target iff the operator can
  // organize into it. Nothing in this pane is a drag SOURCE any more (the
  // sources were the file rows, which are gone) — the centre-pane listing and
  // the Recents grid carry the same MIME, so a drag started there still lands
  // here.
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
      {folderNodes.map((node) => (
        <TreeItem
          key={node.path}
          node={node}
          depth={0}
          shownFolder={shownFolder}
          onNavigate={onNavigate}
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
  /** The FOLDER the centre pane is standing in — already resolved from a
   *  file path by `containingFolder`, so this is always a folder or absent. */
  shownFolder?: string;
  onNavigate: (node: WorkspaceTreeNode) => void;
  onContextMenu?: (node: WorkspaceTreeNode, e: React.MouseEvent) => void;
  dnd?: DndBundle;
}

// The dataTransfer key for a dragged workspace file path (ADR-400 Wave B).
// IMPORTED, not re-declared (ADR-552): the grid and the tree are two halves of
// one surface, and two independent literals of the same string would let a
// rename silently make them refuse each other's drags.
const DRAG_MIME = TILE_DRAG_MIME;

// ADR-423 follow-on: the collapsed "System files" disclosure (the OS
// "Show system files" model) — kernel residue folded out of the operator's way.
// It must start COLLAPSED even though it's a depth-0 node, so it doesn't spill
// the residue the fold exists to hide. Mirrors SYSTEM_FILES_NODE_PATH in the
// Files page (a virtual /explorer/ handle).
const SYSTEM_FILES_NODE_PATH = '/explorer/system-files';

function TreeItem({ node, depth, shownFolder, onNavigate, onContextMenu, dnd }: TreeItemProps) {
  // Auto-expand the first level — EXCEPT the "System files" fold, which stays
  // collapsed (it's the hidden residue; the operator opens it deliberately).
  const [expanded, setExpanded] = useState(
    depth < 1 && node.path !== SYSTEM_FILES_NODE_PATH,
  );
  // The ONE state this pane draws: is the centre pane standing in this folder.
  const isShown = shownFolder === node.path;
  // A folder with only file children has no branch to unfold — draw no
  // disclosure chevron for it, so the affordance never promises a fold that
  // isn't there.
  const hasBranch = (node.children?.length ?? 0) > 0;

  // ADR-400 Wave B drop target. A FOLDER accepts a drop iff the operator can
  // organize into it — probed with a synthetic child path. There is no
  // `draggable` half any more: the tree holds no files, so it is a
  // destination only.
  const isDropTarget = !!dnd && dnd.canOrganize(`${node.path}/x`);
  const isDropHover = !!dnd && dnd.dropTarget === node.path;

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

  // Reveal the branch that holds what the pane is showing — a deep-link, an
  // upload landing, a just-created folder. Keyed on the RESOLVED folder: the tree
  // follows the centre pane, which is the whole relationship between the two.
  useEffect(() => {
    if (shownFolder && nodeContainsPath(node, shownFolder)) {
      setExpanded(true);
    }
  }, [node, shownFolder]);

  // ONE GESTURE, ONE MEANING. A single click on a folder row NAVIGATES the
  // centre pane to that folder AND unfolds its branch. Both, always, from the
  // same click — because in a navigator they are the same act said two ways:
  // "show me what is in here". The first cut split them behind modifiers, which
  // is a selection grammar, and this pane has nothing to select.
  const handleClick = () => {
    if (hasBranch) setExpanded((v) => !v);
    onNavigate(node);
  };

  return (
    <div>
      <button
        onClick={handleClick}
        onContextMenu={onContextMenu ? (e) => onContextMenu(node, e) : undefined}
        {...dropProps}
        className={cn(
          "w-full flex items-center gap-1.5 py-1 px-2 rounded-sm text-left hover:bg-accent/50 transition-colors",
          // ONE state, ONE treatment: the folder the centre pane is showing.
          // The selection ring is gone with the files it used to ring.
          isShown && "bg-accent text-foreground font-medium",
          // ADR-400 Wave B: drop-target highlight while a file drags over.
          isDropHover && "ring-2 ring-inset ring-primary/60 bg-primary/5",
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {hasBranch
          ? (expanded
              ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
              : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />)
          : <span className="w-3.5" />}
        {folderIcon(node)}
        <span className="truncate flex-1">{node.name}</span>
        {/* ADR-388 follow-up: author dots removed from the tree. An unlabeled
            color dot is a riddle — "who wrote it" now lives where it's a full
            legible label (the file header + the Get-Info modal), not a color
            the operator must decode. The tree is for navigation.

            The ADR-422 D1 lock / archive glyphs went with the file rows they
            annotated: they said "this FILE is machine-config / a raw record",
            and there are no file rows here. The same statement still reaches
            the operator on the centre-pane row and in Get-Info. */}
      </button>
      {expanded && hasBranch && (
        <div>
          {node.children!.map((child) => (
            <TreeItem
              key={child.path}
              node={child}
              depth={depth + 1}
              shownFolder={shownFolder}
              onNavigate={onNavigate}
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

/**
 * The folder glyph. (Was `getFileIcon`, a name that no longer describes
 * anything this pane renders — its FileIcon branch is deleted with the file
 * rows.)
 */
function folderIcon(node: WorkspaceTreeNode) {
  const path = node.path.toLowerCase();

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
