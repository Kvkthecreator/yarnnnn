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
import { Info, ExternalLink, Pencil, FolderInput, FolderPlus, Trash2, Share2, MoreVertical, CopyPlus, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCoarsePointer } from '@/hooks/useCoarsePointer';

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
  /**
   * OPEN the share dialog for this artifact (ADR-529 D1). It does not mint and
   * it does not copy: the surface raises the one `ShareDialog`, where the two
   * shapes are stated as consequence and nothing fires without a click. The
   * previous one-click mint always granted full membership — the over-grant is
   * closed by the dialog's existence, not by a check.
   */
  onShare?: (t: { path: string; name: string }) => void;
  /** Duplicate as an attributed derivation (ADR-514 D1) — the kernel resolves
   *  the copy's name and writes the derived_from edge. */
  onDuplicate?: (t: { path: string; name: string }) => void;
  /**
   * ADR-514 D2.2 — open with a NON-default handler. `Open` already fires the
   * default; this is the submenu's pick. The surface resolves the handler set
   * (`resolveHandlers`) and performs the open, because how a handler opens —
   * surface navigation vs inline mount — is the surface's business.
   */
  onOpenWith?: (t: { path: string; name: string }, handlerId: string) => void;
  /**
   * The ordered handler set for the target, `[0]` = default. Supplied by the
   * surface (it knows the file's kind); the menu only renders it. Absent or
   * length ≤ 1 → no Open With submenu, which is most files.
   */
  handlersFor?: (t: { path: string; name: string; isFile: boolean }) => MenuHandler[];
  /**
   * Create a folder INSIDE the target (folders only — the Explorer "New >
   * Folder" grammar; Finder reaches the same act via the folder window's
   * background menu, which a tree row cannot express). Optimistic like every
   * organize verb: the handler + backend decide, and refuse honestly on the
   * carve (system/, inbound/, virtual groups).
   */
  onNewFolder?: (t: { path: string; name: string }) => void;
}


/** The shape Open With needs from a handler — id + label, already ordered. */
export interface MenuHandler {
  id: string;
  label: string;
}

/** A caller-supplied menu entry (ADR-455) — the additive extension point so a
 *  surface (the Studio's ⋯) can offer surface-specific verbs (Copy link,
 *  Duplicate) without forking the shared menu. Rendered above the organize
 *  group, in the given order. */
export interface FileMenuExtraItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
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
  /** Duplicate the target as an attributed derivation (ADR-514 D1, files only). */
  onDuplicate?: (t: FileMenuTarget) => void;
  /** Open the target with a non-default handler (ADR-514 D2.2). */
  onOpenWith?: (t: FileMenuTarget, handlerId: string) => void;
  /** The target's ordered handler set, `[0]` = default (ADR-514 D2.2). */
  handlers?: MenuHandler[];
  /** Create a folder inside the target (folders only). */
  onNewFolder?: (t: FileMenuTarget) => void;
  /** Surface-specific verbs (ADR-455) — rendered above the organize group. */
  extraItems?: FileMenuExtraItem[];
}

export function FileContextMenu({
  target, x, y, onClose, onOpen, onProperties, onRename, onMove, onDelete, onShare,
  onDuplicate, onOpenWith, handlers, onNewFolder, extraItems,
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
      {/* ADR-514 D2.2 — Open With, directly under Open (the Finder ordering).
          Renders ONLY when the file has more than one handler; a single-handler
          file shows no submenu at all, so nothing changes for most files. */}
      {onOpenWith && handlers && handlers.length > 1 && (
        <OpenWithItem
          handlers={handlers}
          onPick={(id) => { onOpenWith(target, id); onClose(); }}
        />
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
      {extraItems?.map((it) => (
        <MenuItem
          key={it.id}
          icon={it.icon ?? <ExternalLink className="w-3.5 h-3.5 text-muted-foreground" />}
          onClick={() => { it.onClick(); onClose(); }}
        >
          {it.label}
        </MenuItem>
      ))}
      {/* Folder-scoped create (Explorer "New > Folder"): a folder target offers
          creating INSIDE it. Files never do — creating a sibling is the canvas
          menu's act on the folder you're looking at. */}
      {!isFile && onNewFolder && (
        <>
          <div className="my-1 h-px bg-border/60" />
          <MenuItem icon={<FolderPlus className="w-3.5 h-3.5 text-muted-foreground" />} onClick={() => run(onNewFolder)}>
            New Folder
          </MenuItem>
        </>
      )}
      {isFile && (onRename || onMove || onDelete || onDuplicate) && <div className="my-1 h-px bg-border/60" />}
      {isFile && onDuplicate && (
        <MenuItem icon={<CopyPlus className="w-3.5 h-3.5 text-muted-foreground" />} onClick={() => run(onDuplicate)}>
          Duplicate
        </MenuItem>
      )}
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

/**
 * Open With ▸ — the handler submenu (ADR-514 D2.2).
 *
 * The Finder grammar: the ordered handler set, the first marked `(default)`,
 * opening on hover like a native submenu. It is deliberately NOT a flat list of
 * rows in the parent menu — Open stays the one-click act, and this is secondary
 * optionality the operator has to reach for.
 */
function OpenWithItem({
  handlers, onPick,
}: {
  handlers: MenuHandler[];
  onPick: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className="relative"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="w-full flex items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors hover:bg-accent/60"
        onClick={() => setOpen((v) => !v)}
      >
        <ExternalLink className="w-3.5 h-3.5 text-muted-foreground" />
        <span className="flex-1">Open With</span>
        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
      </button>
      {open && (
        <div className="absolute left-full top-0 -mt-1 ml-px min-w-[180px] rounded-md border border-border bg-popover py-1 shadow-md">
          {handlers.map((h, i) => (
            <button
              key={h.id}
              type="button"
              onClick={() => onPick(h.id)}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors hover:bg-accent/60"
            >
              <span className="flex-1">{h.label}</span>
              {i === 0 && (
                <span className="text-xs text-muted-foreground">(default)</span>
              )}
            </button>
          ))}
        </div>
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
export function useFileContextMenu(
  verbs: FileVerbs | undefined,
  /**
   * Surface-specific verbs (ADR-455), built per-open so they can close over the
   * target (e.g. the Studio's "Copy link" / "Duplicate" for THIS recent). The
   * shared organize verbs stay in `verbs`; this is the additive extension point.
   */
  extraItemsFor?: (target: FileMenuTarget) => FileMenuExtraItem[],
) {
  const [state, setState] = useState<{ target: FileMenuTarget; x: number; y: number } | null>(null);
  // Touch parity (2026-07-12): on a coarse pointer there is no right-click, so
  // the surfaces render a tappable kebab that opens this same menu. `coarse`
  // tells a surface whether to show the kebab; the menu + verbs are identical.
  const coarse = useCoarsePointer();

  // Any wired verb earns the menu. Enumerating them here was the same defect
  // shape as WorkspaceTree's prop wall (ADR-514 D2.6) — a verb added to the
  // bundle but forgotten in the list would leave the menu silently unopenable
  // on surfaces that wire only that verb.
  const hasVerbs = !!(verbs && Object.values(verbs).some(Boolean));

  const openMenu = useCallback((target: FileMenuTarget, e: React.MouseEvent) => {
    if (!hasVerbs) return;
    e.preventDefault();
    setState({ target, x: e.clientX, y: e.clientY });
  }, [hasVerbs]);

  // Kebab trigger: open the same menu anchored at the tapped button's box, so
  // touch reaches every verb the right-click menu offers. Stops propagation so
  // the tap doesn't also select/open the row. (`FileContextMenu` clamps the
  // final position within the viewport, so anchoring at the button is safe.)
  const openMenuFromButton = useCallback((target: FileMenuTarget, e: React.MouseEvent) => {
    if (!hasVerbs) return;
    e.preventDefault();
    e.stopPropagation();
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setState({ target, x: r.left, y: r.bottom + 4 });
  }, [hasVerbs]);

  /** The tappable ⋯ kebab a surface renders per row on coarse pointers. */
  const Kebab = useCallback(({ target, className }: { target: FileMenuTarget; className?: string }) => {
    if (!coarse || !hasVerbs) return null;
    return (
      <button
        type="button"
        aria-label="File actions"
        onClick={(e) => openMenuFromButton(target, e)}
        className={cn(
          'shrink-0 rounded p-1 text-muted-foreground hover:bg-accent/60 hover:text-foreground',
          className,
        )}
      >
        <MoreVertical className="h-4 w-4" />
      </button>
    );
  }, [coarse, hasVerbs, openMenuFromButton]);

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
      onDuplicate={verbs.onDuplicate ? () => verbs.onDuplicate!(state.target) : undefined}
      onOpenWith={verbs.onOpenWith}
      handlers={verbs.handlersFor?.(state.target)}
      onNewFolder={verbs.onNewFolder ? () => verbs.onNewFolder!(state.target) : undefined}
      extraItems={extraItemsFor?.(state.target)}
    />
  ) : null;

  return { openMenu, menu, hasVerbs, coarse, Kebab };
}
