'use client';

/**
 * TextSurface — the Text app (ADR-571).
 *
 * The prose currency gets a door of its own, shaped like Docs because it IS
 * Docs' peer: two states — a LANDING (the member's own recent documents,
 * with the Open/New pair) and an OPEN state (the editor canvas + a
 * Properties|Chat rail carrying Editor's lane). The difference from Docs is
 * the medium and only the medium: plain markdown, a textarea, no block
 * grammar (ADR-456 D1's grade constraint).
 *
 * It deliberately does NOT ride `DeskHousing` — that is the DASHBOARD
 * housing (Radar/Strings: a rail of subjects over a projected view). A
 * document app's shape is the one StudioSurface already established, and
 * copying the wrong housing is what made the first cut read as "lazily
 * applied" beside Docs.
 *
 * The write path is ADR-570's, unchanged: `PATCH /workspace/file` under the
 * prose class ∧ carve law ∧ principal gate, CAS-guarded — a connector
 * revising the same file mid-edit surfaces as a conflict naming who moved
 * the head, never a silent clobber.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FileText, FolderOpen, Loader2, MoreHorizontal, Plus, ScrollText } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { useFileOrganizeVerbs } from '@/hooks/useFileOrganizeVerbs';
import { useFileContextMenu } from '@/components/workspace/FileContextMenu';
import { OpenArtifactModal } from '@/components/authoring/OpenArtifactModal';
import { formatRelativeTime, formatAbsolute } from '@/lib/formatting';
import { TextEditor } from '@/components/text/TextEditor';
import { NameDocumentModal } from '@/components/text/NameDocumentModal';
import { cn } from '@/lib/utils';

/** Recents come from the substrate revision feed — types derived, never restated. */
type RevisionRow = Awaited<ReturnType<typeof api.workspace.recentRevisions>>['revisions'][number];

const WORKSPACE_PREFIX = '/workspace/';
const PROSE_RE = /\.(md|markdown|txt)$/i;

const relPath = (p: string) => (p.startsWith(WORKSPACE_PREFIX) ? p.slice(WORKSPACE_PREFIX.length) : p);
const absPath = (p: string) => (p.startsWith('/') ? p : `${WORKSPACE_PREFIX}${p}`);
export const leafOf = (p: string) => p.split('/').pop() || p;

/**
 * The document's NAME — ADR-459's rule, applied to prose: what the document
 * IS, never its storage encoding. A prose file is named by its LEAF (the
 * member typed `transcript.md`), so the extension comes off and separators
 * become spaces; Docs titleizes the meaning FOLDER instead because its leaf
 * is a type marker (`document.html`).
 */
export function documentName(path: string): string {
  const bare = leafOf(path).replace(PROSE_RE, '').replace(/[-_]+/g, ' ').trim();
  if (!bare) return leafOf(path);
  return bare.charAt(0).toUpperCase() + bare.slice(1);
}

export default function TextSurface() {
  const { get: getParam, set: setParam } = useSurfaceParam('text');
  const fileParam = getParam('file');
  const openPath = fileParam ? absPath(fileParam) : null;

  const [recents, setRecents] = useState<RevisionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedKey, setFeedKey] = useState(0);

  // ── Recents: the substrate revision feed, deduped by path and filtered to
  //    the prose class. The feed is REVISIONS (one row per write), so a
  //    document edited sixteen times would otherwise fill the landing.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.workspace
      .recentRevisions(80)
      .then((res) => {
        if (cancelled) return;
        const seen = new Set<string>();
        const rows: RevisionRow[] = [];
        for (const r of res.revisions) {
          const p = r.path || '';
          const leaf = leafOf(p);
          if (!PROSE_RE.test(leaf) || leaf.startsWith('_') || seen.has(p)) continue;
          if (p.includes('/inbound/')) continue; // arrivals are records, not documents
          seen.add(p);
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
  const refresh = useCallback(() => setFeedKey((n) => n + 1), []);

  if (openPath) {
    return (
      <TextEditor
        key={openPath}
        path={openPath}
        onClose={close}
        onSaved={refresh}
        onRenamed={(next) => setParam({ file: relPath(next) })}
      />
    );
  }
  return (
    <TextLanding
      recents={recents}
      loading={loading}
      onOpen={open}
      onChanged={refresh}
    />
  );
}

// ── The landing ─────────────────────────────────────────────────────────────
// Structural mirror of the Docs landing (StudioSurface's start state): the
// app's own glyph + invitation on the left, the Open/New pair on the right,
// then "Continue where you left off" as a thumbnail grid with a ⋯ menu per
// card. Same grid, same card anatomy, same organize verbs.

function TextLanding({
  recents,
  loading,
  onOpen,
  onChanged,
}: {
  recents: RevisionRow[];
  loading: boolean;
  onOpen: (path: string) => void;
  onChanged: () => void;
}) {
  const [openPickerOn, setOpenPickerOn] = useState(false);
  const [namingOpen, setNamingOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The same organize grammar every surface uses — rename/move/trash through
  // the shared hook, so a document reorganizes here exactly as in Files.
  const { verbs: organizeVerbs, modals: organizeModals } = useFileOrganizeVerbs({
    onAfterMutate: onChanged,
  });
  const { openMenu, menu: recentMenu } = useFileContextMenu({
    onOpen: (t) => onOpen(t.path),
    ...organizeVerbs,
  });

  const hasRecents = recents.length > 0;

  return (
    <div className="h-full overflow-y-auto p-6 sm:p-8">
      <div className="mx-auto w-full max-w-4xl space-y-6">
        {/* Header row — the app's glyph + invitation, the Open/New pair. */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <div className="flex items-center gap-2">
              <ScrollText className="h-5 w-5 text-muted-foreground" />
              <h1 className="text-lg font-semibold">Text</h1>
            </div>
            <p className="max-w-md text-sm text-muted-foreground">
              Plain-text prose — transcripts, notes, briefs. Open one with a
              cursor, refine it with Editor beside you, and every save lands as
              a signed revision your connectors read back.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setOpenPickerOn(true)}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60"
            >
              <FolderOpen className="h-3.5 w-3.5" />
              Open
            </button>
            <button
              type="button"
              onClick={() => setNamingOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-sm text-background transition-opacity hover:opacity-90"
            >
              <Plus className="h-3.5 w-3.5" />
              New
            </button>
          </div>
        </div>

        {/* Recents — the emphasis, the Docs card anatomy: a text preview
            thumbnail, the document's own name, then the kind + quiet date. */}
        {loading ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Reading your documents…
          </div>
        ) : hasRecents ? (
          <div className="space-y-3">
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Continue where you left off
            </p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {recents.map((r) => {
                const path = r.path || '';
                const target = { path, name: leafOf(path), isFile: true };
                return (
                  <div
                    key={path}
                    className="group relative rounded-lg border border-border p-2 transition-colors hover:bg-muted/20"
                    onContextMenu={(e) => openMenu(target, e)}
                  >
                    <button
                      type="button"
                      onClick={() => onOpen(path)}
                      className="block w-full text-left"
                    >
                      <ProseThumb preview={r.preview} />
                      <span className="mt-2 flex items-center gap-1.5">
                        <FileText className="h-4 w-4 shrink-0 text-sky-600 dark:text-sky-400" />
                        <span className="min-w-0 truncate text-sm font-medium">
                          {documentName(path)}
                        </span>
                      </span>
                      <span className="mt-1 block truncate text-[11px]">
                        <span className="font-medium text-sky-600 dark:text-sky-400">Document</span>
                        {r.created_at ? (
                          <span className="text-muted-foreground" title={formatAbsolute(r.created_at)}>
                            {` · ${formatRelativeTime(r.created_at, { rollToDate: true })}`}
                          </span>
                        ) : null}
                      </span>
                    </button>
                    <button
                      type="button"
                      aria-label={`Actions for ${documentName(path)}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        openMenu(target, e);
                      }}
                      className="absolute right-1.5 top-1.5 rounded-md bg-background/80 p-1 text-muted-foreground opacity-0 shadow-sm backdrop-blur transition-opacity hover:bg-muted hover:text-foreground focus:opacity-100 group-hover:opacity-100"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-border p-8 text-center">
            <ScrollText className="mx-auto mb-3 h-8 w-8 text-muted-foreground/60" />
            <p className="text-sm font-medium text-foreground/80">No documents yet</p>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
              New starts one. Anything written as <span className="font-mono">.md</span> —
              by you, by a colleague in chat, or by a connected AI — shows up here.
            </p>
          </div>
        )}

        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>

      {organizeModals}
      {recentMenu}
      <OpenArtifactModal
        open={openPickerOn}
        onClose={() => setOpenPickerOn(false)}
        onOpen={(p) => {
          setOpenPickerOn(false);
          onOpen(p);
        }}
        appSlug="text"
      />
      <NameDocumentModal
        open={namingOpen}
        onClose={() => setNamingOpen(false)}
        onCreated={(path) => {
          setNamingOpen(false);
          onChanged();
          onOpen(path);
        }}
        onError={setError}
      />
    </div>
  );
}

/**
 * The card thumbnail. Docs renders the artifact's real HTML in a scaled
 * iframe; prose has no rendered form to scale, so the honest analog is the
 * document's own opening lines set in the reading face — which is exactly
 * what `recent-revisions` already computes (`preview`), no extra read.
 */
function ProseThumb({ preview }: { preview?: string | null }) {
  return (
    <div
      className={cn(
        'relative h-[120px] w-full overflow-hidden rounded border border-border/60',
        'bg-[var(--surface-raised,theme(colors.background))] p-2.5',
      )}
    >
      {preview ? (
        <p className="whitespace-pre-wrap break-words text-[7px] leading-[1.5] text-foreground/70 line-clamp-[11]">
          {preview}
        </p>
      ) : (
        <div className="flex h-full items-center justify-center">
          <FileText className="h-6 w-6 text-muted-foreground/40" />
        </div>
      )}
      {/* The fade Docs' scaled iframe gets for free — the page continues. */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-6 bg-gradient-to-t from-background to-transparent" />
    </div>
  );
}
