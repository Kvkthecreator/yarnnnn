'use client';

/**
 * RecentsView — the SINGLE recents renderer (extracted 2026-06-25).
 *
 * Before this, two recents views had diverged: the Files surface's columnar
 * table (RecentRevisions) and the Home front-page cards (HomeRecents), each
 * with its own copy of the author-label / accent / path helpers. The operator
 * asked for a consistent Finder/Explorer view across both. This is that one
 * component — mounted in both surfaces — with two view modes:
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
 * Each row/tile deep-links into the file it changed. The Files mount passes its
 * own `onSelectPath` (selection is component state there); the Home mount omits
 * it, so RecentsView navigates to the Files surface via SurfaceLink.
 */

import { useEffect, useState, useCallback } from 'react';
import { History, Loader2, LayoutGrid, List as ListIcon } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/formatting';
import { formatAuthorLabelOrSystem, authorAccent } from '@/lib/workspace/attribution';
import { FileIcon } from './FileIcon';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { useFileContextMenu, type FileVerbs, type FileMenuTarget } from './FileContextMenu';

interface Revision {
  path: string;
  authored_by: string | null;
  message: string | null;
  created_at: string | null;
  // Explorer thumbnails (2026-07-02): per-format preview material from the feed.
  content_url?: string | null;   // image blob → real thumbnail (resolved to signed URL)
  content_type?: string | null;  // format hint
  preview?: string | null;       // short text snippet for md/text tiles
}

export type RecentsViewMode = 'icon' | 'list';

const VIEW_PREF_KEY = 'yarnnn:recents:view-mode';
const DEFAULT_MODE: RecentsViewMode = 'icon';

function loadViewMode(): RecentsViewMode {
  if (typeof window === 'undefined') return DEFAULT_MODE;
  const raw = window.localStorage.getItem(VIEW_PREF_KEY);
  return raw === 'list' || raw === 'icon' ? raw : DEFAULT_MODE;
}

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
  /** Max rows/tiles to fetch. Files explorer shows 30; Home glance shows ~12. */
  limit?: number;
  /**
   * Files mount: selection is component state, so the page owns the click.
   * Home mount: omit → RecentsView deep-links to the Files surface itself.
   */
  onSelectPath?: (path: string) => void;
  /**
   * The currently-open file path (Files mount) — its tile/row gets a
   * Windows-Explorer selection highlight. Omitted on the Home mount (nothing is
   * "selected" there; every row is a deep-link).
   */
  selectedPath?: string | null;
  /** Hide the header (caller renders its own title chrome). */
  hideHeader?: boolean;
  /** Header label (default "Recents"). */
  title?: string;
  /**
   * Self-hide instead of showing the cold-start empty state. The Home
   * front-page slot uses this (a kernel slot self-hides when empty — ADR-312);
   * the Files center pane shows the empty state (it's the pane's whole job).
   */
  hideWhenEmpty?: boolean;
  /** Header description shown after the title (Home: "recent changes…"). */
  subtitle?: string;
  /**
   * ADR-400 Amendment 1: the operator's file verbs (Properties/Rename/Move/
   * Trash). When wired (Files mount), right-clicking a tile/row opens the shared
   * context menu — the main-panel right-click the macOS/Explorer reference has.
   * Omitted on the Home mount (glance-only, no organize verbs).
   */
  verbs?: FileVerbs;
}

export function RecentsView({
  limit = 30,
  onSelectPath,
  selectedPath = null,
  hideHeader = false,
  title = 'Recents',
  hideWhenEmpty = false,
  verbs,
  subtitle,
}: RecentsViewProps) {
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<RecentsViewMode>(DEFAULT_MODE);
  // ADR-400: right-click a tile/row → the shared file context menu (main-panel).
  const { openMenu, menu } = useFileContextMenu(verbs);

  // SSR-safe: start at the default, apply the stored choice post-mount.
  useEffect(() => { setMode(loadViewMode()); }, []);

  const setView = useCallback((m: RecentsViewMode) => {
    setMode(m);
    try { window.localStorage.setItem(VIEW_PREF_KEY, m); } catch { /* ignore */ }
  }, []);

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

  if (loading && revisions.length === 0) {
    // Self-hiding slot (Home): stay silent until the first batch resolves.
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
            <ViewToggle mode={mode} onChange={setView} />
          </div>
        </div>
      )}
      {hideHeader && (
        <div className="mb-2 flex justify-end">
          <ViewToggle mode={mode} onChange={setView} />
        </div>
      )}

      {mode === 'icon' ? (
        <IconGrid revisions={revisions} onSelectPath={onSelectPath} selectedPath={selectedPath} onContextMenu={openMenu} />
      ) : (
        <ListTable revisions={revisions} onSelectPath={onSelectPath} selectedPath={selectedPath} onContextMenu={openMenu} />
      )}
      {menu}
    </div>
  );
}

// ---------------------------------------------------------------------------
// View toggle (Finder-style segmented switcher)
// ---------------------------------------------------------------------------

function ViewToggle({ mode, onChange }: { mode: RecentsViewMode; onChange: (m: RecentsViewMode) => void }) {
  return (
    <div className="inline-flex items-center rounded-md border border-border/60 p-0.5" role="group" aria-label="Recents view">
      <button
        type="button"
        aria-label="Icon view"
        aria-pressed={mode === 'icon'}
        onClick={() => onChange('icon')}
        className={cn(
          'rounded p-1 transition-colors',
          mode === 'icon' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground',
        )}
      >
        <LayoutGrid className="h-3.5 w-3.5" />
      </button>
      <button
        type="button"
        aria-label="List view"
        aria-pressed={mode === 'list'}
        onClick={() => onChange('list')}
        className={cn(
          'rounded p-1 transition-colors',
          mode === 'list' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground',
        )}
      >
        <ListIcon className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// A single row's click target — Files-mount uses onSelectPath, Home-mount
// deep-links to the Files surface. One <RowShell> keeps the dispatch in one
// place so icon + list modes share it.
// ---------------------------------------------------------------------------

function RowShell({
  path,
  onSelectPath,
  onContextMenu,
  className,
  title,
  children,
}: {
  path: string;
  onSelectPath?: (path: string) => void;
  onContextMenu?: (target: FileMenuTarget, e: React.MouseEvent) => void;
  className?: string;
  title?: string;
  children: React.ReactNode;
}) {
  // Every Recents row is a FILE (the feed is workspace_file_versions), so the
  // menu target is always isFile: true.
  const ctx = onContextMenu
    ? (e: React.MouseEvent) => onContextMenu(
        { path, name: path.split('/').filter(Boolean).pop() || path, isFile: true }, e,
      )
    : undefined;
  if (onSelectPath) {
    return (
      <button type="button" onClick={() => onSelectPath(path)} onContextMenu={ctx} className={className} title={title}>
        {children}
      </button>
    );
  }
  return (
    <SurfaceLink to="files" params={{ path }} className={className} title={title}>
      {children}
    </SurfaceLink>
  );
}

// ---------------------------------------------------------------------------
// Icon view — Finder small-icon grid
// ---------------------------------------------------------------------------

const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg']);
function fileExt(path: string): string {
  return (fileName(path).split('.').pop() || '').toLowerCase();
}

/** Resolve an image blob's content_url → signed URL, then render a cover
 * thumbnail. Absolute URLs (output gateway) render directly. Falls back to the
 * format glyph while loading or on error. (ADR-395 authed blob resolution.) */
function ThumbImage({ contentUrl, filename }: { contentUrl: string; filename: string }) {
  const [url, setUrl] = useState<string>('');
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (/^(https?:|data:|blob:)/i.test(contentUrl)) { setUrl(contentUrl); return; }
    let cancelled = false;
    api.documents.blobUrl(contentUrl)
      .then((r) => { if (!cancelled) setUrl(r.url); })
      .catch(() => { if (!cancelled) setFailed(true); });
    return () => { cancelled = true; };
  }, [contentUrl]);
  if (failed || (!url && !/^(https?:|data:|blob:)/i.test(contentUrl))) {
    // still resolving or failed → keep the glyph so the tile never looks broken
    return <FileIcon filename={filename} size="2xl" />;
  }
  if (!url) return <FileIcon filename={filename} size="2xl" />;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt={filename} className="h-full w-full rounded object-cover" onError={() => setFailed(true)} />;
}

/** The per-format tile preview (Explorer-style): real image thumbnail · text
 * snippet card for md/text · branded format glyph otherwise. */
function Thumbnail({ rev }: { rev: Revision }) {
  const ext = fileExt(rev.path);
  if (IMAGE_EXTS.has(ext) && rev.content_url) {
    return <ThumbImage contentUrl={rev.content_url} filename={fileName(rev.path)} />;
  }
  if (rev.preview && (ext === 'md' || ext === 'txt')) {
    // A content-snippet card — the first real line of the doc, like a mini page.
    return (
      <span className="flex h-full w-full flex-col gap-0.5 overflow-hidden rounded bg-background/70 px-2 py-1.5 text-left">
        <span className="line-clamp-4 text-[9px] leading-[1.35] text-muted-foreground">
          {rev.preview}
        </span>
      </span>
    );
  }
  return <FileIcon filename={fileName(rev.path)} size="2xl" />;
}

function IconGrid({
  revisions, onSelectPath, selectedPath, onContextMenu,
}: {
  revisions: Revision[];
  onSelectPath?: (path: string) => void;
  selectedPath?: string | null;
  onContextMenu?: (target: FileMenuTarget, e: React.MouseEvent) => void;
}) {
  return (
    // Windows-Explorer icon grid: roomy tiles, real per-format thumbnails, clear
    // hover + selection. No metadata dots — just the preview + name + time.
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {revisions.map((rev, i) => {
        const sys = isSystemFile(rev.path);
        const selected = !!selectedPath && rev.path === selectedPath;
        return (
          <RowShell
            key={`${rev.path}-${rev.created_at}-${i}`}
            path={rev.path}
            onSelectPath={onSelectPath}
            onContextMenu={onContextMenu}
            title={rev.path}
            className={cn(
              'group flex flex-col items-center gap-1.5 rounded-lg border p-2.5 text-center transition-colors',
              selected
                ? 'border-primary/50 bg-primary/10 ring-1 ring-primary/40'
                : 'border-transparent hover:border-border/70 hover:bg-muted/40',
              sys && !selected && 'opacity-70',
            )}
          >
            {/* Preview zone — a real Explorer-style thumbnail area. */}
            <span className={cn(
              'flex h-24 w-full items-center justify-center overflow-hidden rounded-md bg-muted/40 transition-colors group-hover:bg-muted/60',
              selected && 'bg-primary/10',
            )}>
              <Thumbnail rev={rev} />
            </span>
            <span className={cn(
              'mt-0.5 w-full truncate text-xs font-medium text-foreground',
              sys && !selected && 'text-muted-foreground',
            )}>
              {fileName(rev.path)}
            </span>
            <span className="w-full truncate text-[10px] text-muted-foreground/70">
              {rev.created_at ? formatRelativeTime(rev.created_at) : ''}
            </span>
          </RowShell>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// List view — macOS list / Windows-Explorer details table
// ---------------------------------------------------------------------------

function ListTable({
  revisions, onSelectPath, selectedPath, onContextMenu,
}: {
  revisions: Revision[];
  onSelectPath?: (path: string) => void;
  selectedPath?: string | null;
  onContextMenu?: (target: FileMenuTarget, e: React.MouseEvent) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border/60">
      <table className="w-full text-sm">
        <thead className="bg-background">
          <tr className="border-b border-border/60 text-[11px] uppercase tracking-wide text-muted-foreground">
            <th className="px-4 py-2 text-left font-medium">Name</th>
            <th className="hidden px-3 py-2 text-left font-medium md:table-cell">Where</th>
            <th className="px-3 py-2 text-left font-medium">Author</th>
            <th className="w-28 px-4 py-2 text-right font-medium">When</th>
          </tr>
        </thead>
        <tbody>
          {revisions.map((rev, i) => {
            const sys = isSystemFile(rev.path);
            const selected = !!selectedPath && rev.path === selectedPath;
            return (
              <tr
                key={`${rev.path}-${rev.created_at}-${i}`}
                className={cn(
                  'border-b border-border/40 transition-colors last:border-b-0',
                  selected ? 'bg-primary/10 hover:bg-primary/15' : 'hover:bg-muted/40',
                  sys && !selected && 'opacity-70',
                )}
              >
                <td className="px-4 py-2">
                  <RowShell
                    path={rev.path}
                    onSelectPath={onSelectPath}
                    onContextMenu={onContextMenu}
                    title={rev.path}
                    className="flex w-full min-w-0 items-center gap-2.5 text-left"
                  >
                    <FileIcon filename={fileName(rev.path)} size="md" />
                    <span className={cn('truncate text-foreground', sys && 'text-muted-foreground')}>
                      {fileName(rev.path)}
                    </span>
                  </RowShell>
                </td>
                <td className="hidden px-3 py-2 text-muted-foreground md:table-cell">
                  <span className="block max-w-[18rem] truncate">{whereLabel(rev.path)}</span>
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">
                  <span className="inline-flex items-center gap-1.5">
                    <span className={cn('h-1.5 w-1.5 rounded-full', authorAccent(rev.authored_by))} />
                    {formatAuthorLabelOrSystem(rev.authored_by)}
                  </span>
                </td>
                <td className="whitespace-nowrap px-4 py-2 text-right text-muted-foreground/80">
                  {rev.created_at ? formatRelativeTime(rev.created_at) : ''}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
