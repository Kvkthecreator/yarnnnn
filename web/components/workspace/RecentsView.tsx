'use client';

/**
 * RecentsView — the SINGLE recents renderer (extracted 2026-06-25).
 *
 * Before this, two recents views had diverged: the Files surface's columnar
 * table (RecentRevisions) and the Home front-page cards (HomeRecents), each
 * with its own copy of the author-label / accent / path helpers. The operator
 * asked for a consistent Finder/Explorer view across both. This is that one
 * component — with two view modes:
 *
 *   - 'icon' (DEFAULT) — a Finder-style grid of file-type icon tiles.
 *   - 'list'           — the macOS list / Windows-Explorer-details table
 *                        (Name · Where · Author · When).
 *
 * A small segmented switcher toggles the two; the choice persists per-operator
 * in localStorage and is shared across every mount (one global recents-view
 * preference, the Finder model). Default 'icon' per the operator's direction.
 *
 * Data source (Singular Implementation): the ADR-209 revision chain via
 * `api.workspace.recentRevisions` — the same feed the Files explorer reads. The
 * helpers (author label/accent, filename, where) live here, deduped from the
 * two prior copies. File-type glyphs come from the shared <FileIcon>.
 *
 * ── RECENTS IS A FILE BROWSER (2026-08-20, third cut) ────────────────────────
 *
 * It is a grid/list of FILES in the centre pane, gathered by RECENCY instead of
 * by folder. That is the only difference from the folder listing, and it is not
 * a difference the member's HANDS can feel — so it takes the identical grammar:
 *
 *   single click  SELECT (inert) · ⌘/Ctrl toggle · shift RANGE over the view's
 *   own visual order · double click OPEN · Escape / background click CLEAR ·
 *   coarse pointer opens on a single tap · right-click gives the verbs.
 *
 * Operator-observed on production (the third defect of the same day): a single
 * click on a Recents tile OPENED the file. Recents was a THIRD file surface the
 * select/open split never reached — it took an `onSelectPath` callback that WAS
 * `openPath`, so every tap went straight through the one door. That prop is
 * DELETED. Recents now speaks the same `(path, FileClickIntent)` contract the
 * folder listing speaks, and the SURFACE applies the grammar — one place the
 * grammar lives, per pane-kind, not per renderer.
 *
 * The deep-link (`linkTo`) branch is DELETED with it. It served a Home mount
 * that no longer exists (Home was deleted by ADR-435); the ternary that chose
 * it had been permanently parked in the `undefined` arm. A branch no caller can
 * reach is not a second mode, it is dead code claiming to be one.
 */

import { useEffect, useState, useCallback, useMemo } from 'react';
import { History, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/formatting';
import { formatAuthorLabelOrSystem, authorAccent } from '@/lib/workspace/attribution';
import { FileTile } from './FileTile';
import { FileListHeader, FileListRow } from './FileListView';
import { FilesViewToggle } from './FilesViewToggle';
import { useFilesViewMode } from '@/lib/workspace/useFilesViewMode';
import { useFileContextMenu, type FileVerbs, type FileMenuTarget } from './FileContextMenu';
import type { FileClickIntent } from '@/types';

interface Revision {
  path: string;
  authored_by: string | null;
  message: string | null;
  created_at: string | null;
  // Explorer thumbnails (2026-07-02): per-format preview material from the feed.
  content_url?: string | null;   // image blob → real thumbnail (resolved to signed URL)
  content_type?: string | null;  // format hint
  preview?: string | null;       // short text snippet for md/text tiles
  svg_text?: string | null;      // inline SVG markup (no blob) → drawn as thumbnail
}

// View mode is the ONE shared Files-surface preference (useFilesViewMode) — no
// Recents-private key. Toggling here moves the folder-listing toggle too, and
// vice-versa (one memory of the preference, the Finder model).

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------
// ADR-388 D3: author label + accent come from the ONE shared attribution
// module (was duplicated here, in files/page, ContentViewer, NodeDetailsPanel).
// formatAuthorLabelOrSystem keeps RecentsView's never-null glance behavior.

function fileName(path: string): string {
  return path.split('/').filter(Boolean).pop() || path;
}

// "Where" — the substrate section the file lives in, sans the /workspace/ root
// (reads "operation/reports/weekly", not the absolute path).
function whereLabel(path: string): string {
  const parts = path.split('/').filter(Boolean);
  const dirs = parts.slice(0, -1);
  if (dirs[0] === 'workspace') dirs.shift();
  return dirs.join('/');
}

// System file (ADR-254 machine-config _*.yaml / _*.md) — de-emphasized, not
// hidden (ADR-320). Carries the same treatment the Files tree applies.
function isSystemFile(path: string): boolean {
  return fileName(path).startsWith('_');
}

// ---------------------------------------------------------------------------

interface RecentsViewProps {
  /** Max rows/tiles to fetch. The Files centre pane shows 30. */
  limit?: number;
  /**
   * THE CLICK, reported as an INTENT — never as a decision. Identical in shape
   * to the folder listing's `onNavigate`: the renderer says what the click was,
   * the surface says what it means. Recents decides nothing.
   */
  onNavigate: (path: string, e?: FileClickIntent) => void;
  /** The picked SET — every member rings. Recents renders it; it never edits it. */
  selection?: readonly string[];
  /**
   * PUBLISH THE VISUAL ORDER. A shift-range is over what the member SEES, and
   * what they see here is recency order — not the folder listing's
   * folders-first alphabetical. Without this the range would run over whichever
   * listing published last.
   */
  onPublishOrder?: (paths: string[]) => void;
  /** A click on the grid's empty GROUND drops the selection. */
  onClearSelection?: () => void;
  /**
   * Replace the selection with exactly this path. Called when a right-click
   * lands OUTSIDE the current selection — the OS rule, so the menu can never
   * name one file while a set-taking verb moves nine.
   */
  onSelectRow?: (path: string) => void;
  /** Hide the header (caller renders its own title chrome). */
  hideHeader?: boolean;
  /** Header label (default "Recents"). */
  title?: string;
  /**
   * Self-hide instead of showing the cold-start empty state. A kernel slot
   * self-hides when empty (ADR-312); the Files centre pane shows the empty
   * state (it's the pane's whole job).
   */
  hideWhenEmpty?: boolean;
  /** Header description shown after the title. */
  subtitle?: string;
  /**
   * ADR-400 Amendment 1: the operator's file verbs (Properties/Rename/Move/
   * Trash). Right-clicking a tile/row opens the shared context menu — the
   * main-panel right-click the macOS/Explorer reference has.
   */
  verbs?: FileVerbs;
}

export function RecentsView({
  limit = 30,
  onNavigate,
  selection,
  onPublishOrder,
  onClearSelection,
  onSelectRow,
  hideHeader = false,
  title = 'Recents',
  hideWhenEmpty = false,
  verbs,
  subtitle,
}: RecentsViewProps) {
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [loading, setLoading] = useState(true);
  // The ONE shared Files view mode (icon/list) — synced with the folder-listing
  // toggle across every mount (useFilesViewMode's module-level subscriber set).
  const { mode, setMode: setView } = useFilesViewMode();
  // ADR-400: right-click a tile/row → the shared file context menu (main-panel).
  const { openMenu, menu, Kebab } = useFileContextMenu(verbs);

  const load = useCallback(async () => {
    try {
      const result = await api.workspace.recentRevisions(limit);
      setRevisions(Array.isArray(result?.revisions) ? result.revisions : []);
    } catch {
      setRevisions([]);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    const onFocus = () => { if (document.visibilityState === 'visible') load(); };
    document.addEventListener('visibilitychange', onFocus);
    return () => { clearInterval(interval); document.removeEventListener('visibilitychange', onFocus); };
  }, [load]);

  const selectedSet = useMemo(() => new Set(selection ?? []), [selection]);

  // The feed can carry the same path more than once (a file edited twice is two
  // revisions). The SELECTION is a set of paths, so the visual order it ranges
  // over must be de-duplicated the same way — otherwise `indexOf` finds the
  // first tile while the member clicked the second, and the range runs to the
  // wrong end.
  const orderedPaths = useMemo(() => {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const r of revisions) {
      if (seen.has(r.path)) continue;
      seen.add(r.path);
      out.push(r.path);
    }
    return out;
  }, [revisions]);

  // PUBLISH THE VISUAL ORDER — recency, exactly as drawn. From an effect (not
  // during render) because it writes to the surface's ref.
  useEffect(() => {
    onPublishOrder?.(orderedPaths);
  }, [orderedPaths, onPublishOrder]);

  // A click on the grid's empty GROUND drops the selection — the same exit the
  // folder listing offers, and the half of ADR-519's trap-withdrawal that
  // Escape alone does not cover (a member who reaches for the mouse, not a key).
  const onGroundClick = (e: React.MouseEvent) => {
    if (e.currentTarget !== e.target) return;
    onClearSelection?.();
  };

  // Right-click scope, the OS rule: INSIDE a multi-selection the menu acts on
  // the whole set and leaves it intact; OUTSIDE it, the selection is REPLACED
  // by the row you hit first.
  const rowContext = (path: string) => (e: React.MouseEvent) => {
    if (!selectedSet.has(path)) onSelectRow?.(path);
    openMenu({ path, name: fileName(path), isFile: true }, e);
  };

  if (loading && revisions.length === 0) {
    // Self-hiding slot: stay silent until the first batch resolves.
    if (hideWhenEmpty) return null;
    return (
      <div className="flex items-center gap-2 px-1 py-3 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading recent changes…
      </div>
    );
  }

  // Cold-start honest: nothing authored yet.
  if (!loading && revisions.length === 0) {
    if (hideWhenEmpty) return null;
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center px-6">
        <History className="h-8 w-8 text-muted-foreground/40 mb-3" />
        <p className="text-sm text-muted-foreground">
          Nothing authored yet. As the system writes to your workspace, recent
          changes show here — who wrote what, and when.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      {!hideHeader && (
        <div className="mb-3 flex items-center gap-2">
          <History className="h-4 w-4 text-muted-foreground shrink-0" />
          <h2 className="text-sm font-medium text-foreground">{title}</h2>
          <span className="text-[11px] text-muted-foreground">
            {subtitle ?? `${revisions.length} change${revisions.length === 1 ? '' : 's'}`}
          </span>
          <div className="ml-auto">
            <FilesViewToggle mode={mode} onChange={setView} />
          </div>
        </div>
      )}
      {hideHeader && (
        <div className="mb-2 flex justify-end">
          <FilesViewToggle mode={mode} onChange={setView} />
        </div>
      )}

      {mode === 'icon' ? (
        <IconGrid
          revisions={revisions}
          onNavigate={onNavigate}
          selectedSet={selectedSet}
          onGroundClick={onGroundClick}
          rowContext={rowContext}
          Kebab={Kebab}
        />
      ) : (
        <ListTable
          revisions={revisions}
          onNavigate={onNavigate}
          selectedSet={selectedSet}
          onGroundClick={onGroundClick}
          rowContext={rowContext}
          Kebab={Kebab}
        />
      )}
      {menu}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Icon view — the shared <FileTile> grid (Singular Implementation, 2026-07-09).
// The tile geometry, preview zone, radius, and thumbnail logic all live in
// FileTile now; the Recents grid just maps rows onto it. The folder-listing icon
// view (ContentViewer) renders the SAME tile — one look across the surface, and
// (since 2026-08-20) one click grammar behind it.
// ---------------------------------------------------------------------------

function IconGrid({
  revisions, onNavigate, selectedSet, onGroundClick, rowContext, Kebab,
}: {
  revisions: Revision[];
  onNavigate: (path: string, e?: FileClickIntent) => void;
  selectedSet: Set<string>;
  onGroundClick: (e: React.MouseEvent) => void;
  rowContext: (path: string) => (e: React.MouseEvent) => void;
  Kebab: (props: { target: FileMenuTarget; className?: string }) => React.ReactNode;
}) {
  return (
    <div
      className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5"
      onClick={onGroundClick}
    >
      {revisions.map((rev, i) => {
        const sys = isSystemFile(rev.path);
        // Every Recents row is a FILE (the feed is workspace_file_versions).
        const menuTarget: FileMenuTarget = {
          path: rev.path, name: fileName(rev.path), isFile: true,
        };
        return (
          <FileTile
            key={`${rev.path}-${rev.created_at}-${i}`}
            path={rev.path}
            kind="file"
            selected={selectedSet.has(rev.path)}
            dim={sys}
            thumb={{
              content_url: rev.content_url,
              content_type: rev.content_type,
              preview: rev.preview,
              svgText: rev.svg_text,
            }}
            subtext={rev.created_at ? formatRelativeTime(rev.created_at) : ''}
            onClick={(e) => onNavigate(rev.path, e)}
            onContextMenu={rowContext(rev.path)}
            actions={<Kebab target={menuTarget} />}
          />
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// List view — the shared <FileListRow> details list (Singular Implementation,
// 2026-07-09). Same header + column model + row height as the folder-listing
// list view (ContentViewer): Name · Where · Author · When. Recents fills the
// Where column with the substrate section; the folder listing leaves it empty.
// ---------------------------------------------------------------------------

function ListTable({
  revisions, onNavigate, selectedSet, onGroundClick, rowContext, Kebab,
}: {
  revisions: Revision[];
  onNavigate: (path: string, e?: FileClickIntent) => void;
  selectedSet: Set<string>;
  onGroundClick: (e: React.MouseEvent) => void;
  rowContext: (path: string) => (e: React.MouseEvent) => void;
  Kebab: (props: { target: FileMenuTarget; className?: string }) => React.ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-border/60">
      <FileListHeader />
      <div className="divide-y divide-border/40" onClick={onGroundClick}>
        {revisions.map((rev, i) => {
          const sys = isSystemFile(rev.path);
          const menuTarget: FileMenuTarget = { path: rev.path, name: fileName(rev.path), isFile: true };
          return (
            <FileListRow
              key={`${rev.path}-${rev.created_at}-${i}`}
              name={fileName(rev.path)}
              kind="file"
              where={whereLabel(rev.path)}
              when={rev.created_at ? formatRelativeTime(rev.created_at) : ''}
              selected={selectedSet.has(rev.path)}
              dim={sys}
              author={
                <span className="inline-flex items-center gap-1.5">
                  <span className={cn('h-1.5 w-1.5 rounded-full', authorAccent(rev.authored_by))} />
                  {formatAuthorLabelOrSystem(rev.authored_by)}
                </span>
              }
              title={rev.path}
              onClick={(e) => onNavigate(rev.path, e)}
              onContextMenu={rowContext(rev.path)}
              actions={<Kebab target={menuTarget} />}
            />
          );
        })}
      </div>
    </div>
  );
}
