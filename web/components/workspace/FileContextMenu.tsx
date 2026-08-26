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
 *
 * WHAT `isFile` STILL GATES, after 2026-08-21. It is no longer the organize
 * gate — Rename / Move / Move to Trash are offered on folders too, because the
 * fan-out that makes a folder verb possible now exists. Three things still
 * branch on it, each for its own reason:
 *   - Duplicate (file-only): duplicating a folder means deep-copying a subtree
 *     with a derived_from edge per file. A different act, out of scope.
 *   - New Folder (folder-only): the Explorer "New > Folder" grammar — you
 *     create INSIDE a folder.
 *   - Download (file-only, and enforced by the surface returning null): there
 *     is no folder download, and there will not be one — see the Files page's
 *     `downloadFor` for the ADR-417 reasoning and the export door that replaces
 *     it. No dead affordance, no disabled-looking row: the entry simply does
 *     not render.
 */

import { useCallback, useEffect, useState } from 'react';
import { Info, ExternalLink, Pencil, FolderInput, FolderPlus, Trash2, Share2, MoreVertical, CopyPlus, ChevronRight, Download } from 'lucide-react';
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
  // Rename / Move / Delete take the FULL target, `isFile` included (2026-08-21):
  // a folder verb fans out over the subtree and a file verb does not, so the
  // handler cannot pick the right act from a {path, name} pair alone. The
  // surface already holds the kind; passing it is cheaper and more honest than
  // re-deriving it from the path shape.
  onRename?: (t: FileMenuTarget) => void;
  onMove?: (t: FileMenuTarget) => void;
  onDelete?: (t: FileMenuTarget) => void;
  /**
   * Save the file to the operator's computer (2026-08-20). Follows the
   * cloud-provider convention (Dropbox / Drive / OneDrive): downloading is a
   * RIGHT-CLICK verb, not a button bolted into the preview header — which is
   * where it used to live, and where the operator did not think to look.
   *
   * ASYNC, because a blob's href does not exist until it is minted: the file's
   * `content_url` is a relative, AUTHENTICATED reference, and the directly
   * fetchable URL is a signed Supabase URL the surface must ask for. So this
   * resolves the target to a `{ href, filename }` — or null when there is
   * nothing to save (a folder, a text file with no blob), in which case the
   * entry does not render at all. An entry that does nothing when clicked
   * would be the same defect at a different address.
   *
   * The FILENAME is load-bearing, not cosmetic. The href points at the
   * `workspace-cas` bucket, which is keyed by CONTENT ADDRESS — a bare
   * `download` attribute defers to the server's name and saved the blob as its
   * 64-char SHA with no extension ("Kind: Document", generic icon, no
   * preview). Fixed in 1069fe3; it must survive every move of this verb, which
   * is why the pair travels together and the href alone is never enough.
   */
  downloadFor?: (t: FileMenuTarget) => Promise<{ href: string; filename: string } | null>;
  /**
   * The BLAST RADIUS of Move to Trash on this target, resolved when the menu
   * OPENS (2026-08-21) — the same async shape as `downloadFor`, and for the
   * same reason: a menu item that names a consequence has to know the
   * consequence before it is clicked.
   *
   * A folder verb FANS OUT. Trashing a folder writes one attributed archive
   * revision per file under it, so "Move to Trash" on a folder can be forty
   * acts wearing a one-act label. The count goes IN THE LABEL — "Move to Trash
   * (40 items)" — so the size of the act is visible BEFORE the click, not
   * discovered in a toast afterwards.
   *
   * Returns null for anything with no count worth naming (a single file, an
   * unresolvable target), in which case the plain label renders. The label is
   * additive: the verb is never gated on this resolving.
   */
  blastRadiusFor?: (t: FileMenuTarget) => Promise<number | null>;
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
  /**
   * Per-target extra entries (ADR-455's extension point), riding the VERBS
   * bundle so one wiring reaches every surface the bundle is threaded to
   * (tree · grid · listing) — the same reason the bundle exists (a second
   * arg per surface would be the ADR-514 D2.6 prop wall again). First
   * consumer: the Files door into the standing-work desk ("Keep this current…",
   * ADR-569 D7 — the gesture lives where the file does; the management
   * does not).
   */
  extraItemsFor?: (t: FileMenuTarget) => FileMenuExtraItem[];
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
  /** Rename — files AND folders (a folder rename fans out over its subtree). */
  onRename?: (t: FileMenuTarget) => void;
  /** Move to… — files AND folders. */
  onMove?: (t: FileMenuTarget) => void;
  /** Move to Trash — files AND folders. */
  onDelete?: (t: FileMenuTarget) => void;
  /** The resolved Move-to-Trash label, count included ("Move to Trash (40
   *  items)"). Undefined → the plain label. */
  deleteLabel?: string;
  /** The resolved download for the target, or null when there is nothing to
   *  save. `filename` carries the file's OWN name (the CAS href does not). */
  download?: { href: string; filename: string } | null;
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
  onDuplicate, onOpenWith, handlers, onNewFolder, extraItems, download, deleteLabel,
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
      {/* Download — an ANCHOR, not a button: the browser's own save path, so
          the signed CAS URL is fetched by the navigation rather than by us.
          `download={filename}` is the fix from 1069fe3 and the whole reason
          this entry carries a resolved pair instead of a bare href. */}
      {download && (
        <a
          href={download.href}
          download={download.filename}
          onClick={() => onClose()}
          className="w-full flex items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors hover:bg-accent/60"
        >
          <Download className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="flex-1">Download</span>
        </a>
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
      {/* ── THE ORGANIZE GROUP ───────────────────────────────────────────
          Rename / Move / Move to Trash are offered on FILES AND FOLDERS
          (2026-08-21). They were file-only until now for a STRUCTURAL reason,
          not an arbitrary one: since ADR-588 a folder is a marker row plus
          whatever files share its path prefix, so a folder verb is a FAN-OUT
          over the subtree rather than one act — and the fan did not exist. It
          does now (services/folder_organize.py), so the gate comes off.

          DUPLICATE stays file-only, deliberately: duplicating a folder means
          deep-copying a subtree and minting a derived_from edge per file, which
          is a different act with its own naming and attribution questions. Out
          of scope, and an entry that half-works would be worse than its absence.

          The BLAST RADIUS is in the LABEL, never discovered after the click —
          `deleteLabel` carries the resolved count ("Move to Trash (40 items)").
          A folder verb that reads the same as a file verb is a promise the act
          does not keep. */}
      {(onRename || onMove || onDelete || (isFile && onDuplicate)) && <div className="my-1 h-px bg-border/60" />}
      {isFile && onDuplicate && (
        <MenuItem icon={<CopyPlus className="w-3.5 h-3.5 text-muted-foreground" />} onClick={() => run(onDuplicate)}>
          Duplicate
        </MenuItem>
      )}
      {onRename && (
        <MenuItem icon={<Pencil className="w-3.5 h-3.5 text-muted-foreground" />} onClick={() => run(onRename)}>
          Rename…
        </MenuItem>
      )}
      {onMove && (
        <MenuItem icon={<FolderInput className="w-3.5 h-3.5 text-muted-foreground" />} onClick={() => run(onMove)}>
          Move to…
        </MenuItem>
      )}
      {onDelete && (
        <MenuItem icon={<Trash2 className="w-3.5 h-3.5 text-destructive" />} onClick={() => run(onDelete)} danger>
          {deleteLabel ?? 'Move to Trash'}
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
  // The resolved download for the OPEN menu's target. Minted per open (a signed
  // URL is short-lived; caching one across opens would hand the operator an
  // expired link), cleared on close, and dropped if the menu moved on before
  // the mint landed.
  const [download, setDownload] = useState<{ href: string; filename: string } | null>(null);
  // The resolved Move-to-Trash count for the OPEN menu's target (2026-08-21).
  // Same lifecycle as `download` — minted per open, cleared on close, dropped
  // if the menu moved on before it landed. Null = no count worth naming, and
  // the plain label renders; the verb never waits on this.
  const [blastRadius, setBlastRadius] = useState<number | null>(null);
  // Touch parity (2026-07-12): on a coarse pointer there is no right-click, so
  // the surfaces render a tappable kebab that opens this same menu. `coarse`
  // tells a surface whether to show the kebab; the menu + verbs are identical.
  const coarse = useCoarsePointer();

  // Any wired verb earns the menu. Enumerating them here was the same defect
  // shape as WorkspaceTree's prop wall (ADR-514 D2.6) — a verb added to the
  // bundle but forgotten in the list would leave the menu silently unopenable
  // on surfaces that wire only that verb.
  const hasVerbs = !!(verbs && Object.values(verbs).some(Boolean));

  // The two per-open resolutions, in ONE place: an entry that names something
  // about the target (its downloadable href, its blast radius) has to learn it
  // when the menu opens. Both are best-effort and neither gates its verb.
  const resolveOnOpen = useCallback((target: FileMenuTarget) => {
    setDownload(null);
    setBlastRadius(null);
    // Only apply a result if this is still the target on screen — the menu can
    // move on (another right-click) before an in-flight resolve lands.
    const ifStillOpen = (apply: () => void) =>
      setState((cur) => { if (cur && cur.target.path === target.path) apply(); return cur; });
    if (verbs?.downloadFor) {
      void verbs.downloadFor(target)
        .then((d) => ifStillOpen(() => setDownload(d)))
        .catch(() => setDownload(null));
    }
    if (verbs?.blastRadiusFor) {
      void verbs.blastRadiusFor(target)
        .then((n) => ifStillOpen(() => setBlastRadius(n)))
        .catch(() => setBlastRadius(null));
    }
  }, [verbs]);

  const openMenu = useCallback((target: FileMenuTarget, e: React.MouseEvent) => {
    if (!hasVerbs) return;
    e.preventDefault();
    setState({ target, x: e.clientX, y: e.clientY });
    resolveOnOpen(target);
  }, [hasVerbs, resolveOnOpen]);

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
    resolveOnOpen(target);
  }, [hasVerbs, resolveOnOpen]);

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
      onClose={() => { setState(null); setDownload(null); setBlastRadius(null); }}
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
      extraItems={(extraItemsFor ?? verbs.extraItemsFor)?.(state.target)}
      download={download}
      deleteLabel={
        blastRadius === null
          ? undefined
          : `Move to Trash (${blastRadius} item${blastRadius === 1 ? '' : 's'})`
      }
    />
  ) : null;

  // `openMenuFromButton` is returned (ADR-572 D10) so a surface can anchor
  // this menu under its OWN kebab on any pointer — the Properties-pane `⋯`
  // that Docs hand-rolls as ~90 lines of inline popover. `Kebab` stays the
  // convenience wrapper for the coarse-pointer ROW case; a pane that always
  // shows its kebab needs the opener, not the conditional button.
  return { openMenu, openMenuFromButton, menu, hasVerbs, coarse, Kebab };
}
