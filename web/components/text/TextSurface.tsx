'use client';

/**
 * TextSurface — the Text app (ADR-571).
 *
 * The prose currency gets a door of its own: `.md`/`.markdown`/`.txt`
 * opened with a cursor, Editor (the app's name for the designer resident —
 * ADR-562, the Docs/"Writer" shape) in a bound lane beside the canvas.
 *
 * Docs-shaped, deliberately: a landing of recent prose documents + a New
 * gesture, then an open state whose canvas is the editor. It rides the
 * shared DeskHousing (ADR-518's move, generalized by ADR-569) rather than
 * re-implementing the chrome — subject = the open document, artifactPath =
 * the same path, so the lane binds to exactly the file being edited.
 *
 * The write path is ADR-570's, unchanged: `PATCH /workspace/file` under the
 * prose class ∧ carve law ∧ principal gate, CAS-guarded — a connector
 * revising the same file mid-edit surfaces as a conflict naming who moved
 * the head, never a silent clobber.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { FileText, Loader2, Plus } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { DeskHousing } from '@/components/desk/DeskHousing';
import { TextCanvas } from '@/components/text/TextCanvas';
import { formatTimestamp } from '@/lib/formatting';
import { cn } from '@/lib/utils';

/** Recents come from the substrate revision feed — types derived, never restated. */
type RevisionRow = Awaited<ReturnType<typeof api.workspace.recentRevisions>>['revisions'][number];

const WORKSPACE_PREFIX = '/workspace/';
const PROSE_RE = /\.(md|markdown|txt)$/i;

const relPath = (p: string) => (p.startsWith(WORKSPACE_PREFIX) ? p.slice(WORKSPACE_PREFIX.length) : p);
const absPath = (p: string) => (p.startsWith('/') ? p : `${WORKSPACE_PREFIX}${p}`);
const leafOf = (p: string) => p.split('/').pop() || p;
/** The document's name — its leaf without the extension, title-cased lightly. */
const nameOf = (p: string) => leafOf(p).replace(PROSE_RE, '');

const SUGGESTIONS = [
  'Tighten this — same meaning, fewer words',
  'What is unclear to someone reading this cold?',
  'Restructure it so the main point lands first',
];

export default function TextSurface() {
  const { get: getParam, set: setParam } = useSurfaceParam('text');
  const fileParam = getParam('file');
  const openPath = fileParam ? absPath(fileParam) : null;

  const [recents, setRecents] = useState<RevisionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  // Bumped after a save so the landing's recents re-read on return.
  const [feedKey, setFeedKey] = useState(0);

  // ── Recents: the substrate revision feed, deduped by path and filtered to
  //    the prose class. The feed is REVISIONS (one row per write), so a
  //    document edited sixteen times would otherwise fill the landing.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.workspace
      .recentRevisions(60)
      .then((res) => {
        if (cancelled) return;
        const seen = new Set<string>();
        const rows: RevisionRow[] = [];
        for (const r of res.revisions) {
          if (!r.path || !PROSE_RE.test(r.path) || seen.has(r.path)) continue;
          seen.add(r.path);
          rows.push(r);
        }
        setRecents(rows);
      })
      .catch(() => { if (!cancelled) setRecents([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [feedKey]);

  const open = useCallback((path: string) => setParam({ file: relPath(path) }), [setParam]);
  const close = useCallback(() => setParam({ file: null }), [setParam]);

  // ── New: a named document in Documents/, created through the SAME member
  //    door every save uses (ADR-570 D4) — no second write path, and the
  //    placement gate answers identically for creation and for editing.
  const createDocument = useCallback(async () => {
    const typed = window.prompt('Name this document');
    const name = (typed || '').trim();
    if (!name) return;
    const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'untitled';
    const path = `${WORKSPACE_PREFIX}Documents/${slug}.md`;
    setCreating(true);
    setCreateError(null);
    try {
      await api.workspace.editFile(path, `# ${name}\n\n`, undefined, `create ${slug}.md`);
      setFeedKey((n) => n + 1);
      open(path);
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : 'Could not create the document.');
    } finally {
      setCreating(false);
    }
  }, [open]);

  const laneName = useMemo(() => (openPath ? nameOf(openPath).slice(0, 60) : ''), [openPath]);

  return (
    <DeskHousing
      app="text"
      subject={openPath}
      artifactPath={openPath}
      laneReady={!!openPath}
      laneName={laneName}
      laneTabLabel="Editor"
      suggestions={SUGGESTIONS}
      laneFallbackLabel="Editor could not be opened for this document."
      laneEmptyState={
        <>
          <p className="font-medium text-foreground/80">Editor is reading this document.</p>
          <p className="mt-1">
            Ask for a tighter draft, a restructure, or a second opinion — every
            change Editor makes lands as a signed revision you can see and revert.
          </p>
        </>
      }
      onLaneWrite={() => setFeedKey((n) => n + 1)}
      renderRail={() => (
        <RecentList
          rows={recents}
          loading={loading}
          activePath={openPath}
          onOpen={open}
          onNew={createDocument}
          creating={creating}
          compact
        />
      )}
      renderFrontDoor={() => (
        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-auto">
          <div className="mx-auto w-full max-w-3xl space-y-6 p-6">
            <div className="space-y-2">
              <h1 className="text-lg font-semibold">Text</h1>
              <p className="text-sm text-muted-foreground">
                Plain-text prose — transcripts, notes, briefs, every{' '}
                <span className="font-mono text-xs">.md</span> in the workspace.
                Open one with a cursor, refine it with Editor beside you, and
                every save lands as a signed revision your connectors read back.
              </p>
              <div className="flex items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={createDocument}
                  disabled={creating}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border bg-foreground px-3 py-1.5 text-sm text-background disabled:opacity-50"
                >
                  {creating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                  New document
                </button>
              </div>
              {createError && <p className="text-xs text-destructive">{createError}</p>}
            </div>
            <RecentList
              rows={recents}
              loading={loading}
              activePath={null}
              onOpen={open}
              heading="Recent documents"
            />
          </div>
        </main>
      )}
    >
      {() =>
        openPath ? (
          <TextCanvas
            path={openPath}
            onClose={close}
            onSaved={() => setFeedKey((n) => n + 1)}
          />
        ) : null
      }
    </DeskHousing>
  );
}

function RecentList({
  rows,
  loading,
  activePath,
  onOpen,
  onNew,
  creating,
  compact,
  heading,
}: {
  rows: RevisionRow[];
  loading: boolean;
  activePath: string | null;
  onOpen: (path: string) => void;
  onNew?: () => void;
  creating?: boolean;
  compact?: boolean;
  heading?: string;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        {heading ? (
          <h2 className="text-sm font-medium">{heading}</h2>
        ) : (
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Documents
          </span>
        )}
        {onNew && (
          <button
            type="button"
            onClick={onNew}
            disabled={creating}
            title="New document"
            className="inline-flex items-center gap-1 rounded-md border border-border px-1.5 py-1 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground disabled:opacity-50"
          >
            <Plus className="h-3 w-3" /> New
          </button>
        )}
      </div>
      {loading ? (
        <div className="flex items-center gap-2 p-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" /> Reading recent documents…
        </div>
      ) : rows.length === 0 ? (
        <p className="p-2 text-xs text-muted-foreground">
          No prose documents yet. New document starts one, or write a{' '}
          <span className="font-mono">.md</span> from chat or a connector.
        </p>
      ) : (
        <ul className="space-y-0.5">
          {rows.map((r) => {
            const active = activePath === r.path;
            return (
              <li key={r.path}>
                <button
                  type="button"
                  onClick={() => onOpen(r.path!)}
                  className={cn(
                    'flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left hover:bg-muted/40',
                    active && 'bg-muted/60',
                  )}
                >
                  <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm">{nameOf(r.path || '')}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {compact
                        ? relPath(r.path || '').split('/').slice(0, -1).join('/') || 'workspace'
                        : r.preview || relPath(r.path || '')}
                    </span>
                    {!compact && r.created_at && (
                      <span className="mt-0.5 block text-[11px] text-muted-foreground/80">
                        {formatTimestamp(r.created_at, true)}
                      </span>
                    )}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
