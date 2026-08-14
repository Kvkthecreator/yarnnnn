'use client';

/**
 * TextEditor — Text's open state (ADR-571).
 *
 * The Docs open-state shape, one medium down: a crumb row (app · document
 * name, click to rename) with the boundary acts (Share · Export) on the
 * right, the canvas in the middle, and the Properties|Chat rail carrying
 * Editor's bound lane — the same two tabs, the same never-unmount rule so a
 * streaming turn survives a tab switch.
 *
 * The canvas is a textarea by decision (ADR-456 D1): never block-grade, no
 * Studio machinery. What it DOES carry is everything the medium can honestly
 * support — the reading face, a word count, ⌘S, and the CAS conflict banner.
 *
 * The save path is ADR-570's, unchanged: `PATCH /workspace/file` (prose class
 * ∧ carve law ∧ principal gate), CAS-guarded on the head the document was
 * loaded with. The 409 is a product surface, not an edge case — the commons
 * is multi-principal, and a connector may revise this same file mid-session,
 * so the conflict names WHO moved the head and offers two explicit exits.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  FileText,
  Loader2,
  PanelRight,
} from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { useFileLoad } from '@/components/workspace/useFileLoad';
import { useFileOrganizeVerbs } from '@/hooks/useFileOrganizeVerbs';
import { formatAuthorLabel } from '@/lib/workspace/attribution';
import { formatRelativeTime } from '@/lib/formatting';
import { LanePanel } from '@/components/chat-surface/LanePanel';
import { ShareDialog } from '@/components/workspace/ShareDialog';
import { TextExport } from '@/components/text/TextExport';
import { documentName, leafOf } from '@/components/text/TextSurface';
import { useWorkbenchWidth } from '@/lib/authoring/workbench-width';
import { cn } from '@/lib/utils';

type LanesEnv = Awaited<ReturnType<typeof api.lanes.list>>;
type LaneRow = LanesEnv['lanes'][number];

const WORKSPACE_PREFIX = '/workspace/';
const relPath = (p: string) => (p.startsWith(WORKSPACE_PREFIX) ? p.slice(WORKSPACE_PREFIX.length) : p);

interface ConflictState {
  actor: string;
  currentHeadId: string | null;
}

const SUGGESTIONS = [
  'Tighten this — same meaning, fewer words',
  'What is unclear to someone reading this cold?',
  'Restructure so the main point lands first',
];

export function TextEditor({
  path,
  onClose,
  onSaved,
  onRenamed,
}: {
  path: string;
  onClose: () => void;
  onSaved?: () => void;
  onRenamed?: (nextPath: string) => void;
}) {
  const [setWorkbenchNode, wb] = useWorkbenchWidth();
  const [reloadKey, setReloadKey] = useState(0);
  const { file, loading, notFound, error, headRevision } = useFileLoad(path, {
    withRevision: true,
    reloadKey,
  });

  const [text, setText] = useState('');
  const [baseline, setBaseline] = useState('');
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<ConflictState | null>(null);
  const baseHead = useRef<string | null>(null);

  // Rail: Properties | Chat, the Docs grammar. The lane stays MOUNTED while
  // Properties is up (CSS-hidden) so a streaming turn survives the switch.
  const [rightTab, setRightTab] = useState<'properties' | 'chat'>('properties');
  const [sideOpen, setSideOpen] = useState(true);
  const { sideIsOverlay, fullLabels } = wb;

  const [shareTarget, setShareTarget] = useState<{ path: string; name: string } | null>(null);

  useEffect(() => {
    if (!file) return;
    const content = file.content ?? '';
    setText(content);
    setBaseline(content);
    baseHead.current = file.head_version_id ?? null;
    setConflict(null);
  }, [file]);

  const dirty = text !== baseline;

  const save = useCallback(
    async (expectedHead: string | null = baseHead.current) => {
      if (saving) return;
      setSaving(true);
      setSaveError(null);
      try {
        const res = await api.workspace.editFile(
          path, text, undefined, 'Edited in Text', expectedHead,
        );
        baseHead.current = (res as { head_version_id?: string }).head_version_id ?? null;
        setBaseline(text);
        setConflict(null);
        setSavedAt(Date.now());
        onSaved?.();
      } catch (err) {
        if (err instanceof APIError && err.status === 409) {
          const detail = (err.data as {
            detail?: { current_head?: { id?: string; authored_by?: string } };
          } | null)?.detail;
          const head = detail?.current_head;
          setConflict({
            actor: formatAuthorLabel(head?.authored_by ?? '') || 'Someone else',
            currentHeadId: head?.id ?? null,
          });
        } else {
          setSaveError(err instanceof Error ? err.message : 'Save failed');
        }
      } finally {
        setSaving(false);
      }
    },
    [path, text, saving, onSaved],
  );

  useEffect(() => {
    if (savedAt === null) return;
    const t = setTimeout(() => setSavedAt(null), 2200);
    return () => clearTimeout(t);
  }, [savedAt]);

  // ⌘S anywhere in the surface, not just the textarea — the document is the
  // subject of the whole window (the Docs reflex).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        void save();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [save]);

  // Rename through the shared organize grammar; the surface follows the file
  // to its new path (the Docs `setParam({ file })` reflex).
  const { verbs: organizeVerbs, modals: organizeModals } = useFileOrganizeVerbs({
    onAfterMutate: (newPath) => {
      onSaved?.();
      // Follow the file to its new path; a trashed document has no open
      // state to return to, so the surface goes back to the landing.
      if (newPath && newPath !== path) onRenamed?.(newPath);
      else if (!newPath) onClose();
      else setReloadKey((n) => n + 1);
    },
  });

  // ── The bound lane (find-or-create) — the ADR-567 D4 binding contract,
  //    same two-field call every app makes. `app: 'text'` selects Editor
  //    server-side (ADR-562) and the Text job posture (ADR-571 D4).
  const [lanesEnabled, setLanesEnabled] = useState<boolean | null>(null);
  const [lanes, setLanes] = useState<LaneRow[]>([]);
  const [agents, setAgents] = useState<LanesEnv['agents']>([]);
  const [apps, setApps] = useState<NonNullable<LanesEnv['apps']>>([]);
  const [models, setModels] = useState<LanesEnv['models']>([]);
  const [creatingLane, setCreatingLane] = useState(false);

  const refreshLanes = useCallback(async () => {
    try {
      const env = await api.lanes.list(true);
      setLanesEnabled(env.enabled);
      setLanes(env.lanes ?? []);
      setAgents(env.agents ?? []);
      setApps(env.apps ?? []);
      setModels(env.models ?? []);
    } catch {
      setLanesEnabled(false);
    }
  }, []);

  useEffect(() => { void refreshLanes(); }, [refreshLanes]);

  const boundLane = useMemo(
    () => lanes.find((l) => l.status === 'active' && l.artifact_path === path) ?? null,
    [lanes, path],
  );

  useEffect(() => {
    if (!path || !lanesEnabled || boundLane || creatingLane) return;
    setCreatingLane(true);
    api.lanes
      .create({ name: documentName(path).slice(0, 60), app: 'text', artifact_path: path })
      .then(() => refreshLanes())
      .catch(() => { /* the rail states why below */ })
      .finally(() => setCreatingLane(false));
  }, [path, lanesEnabled, boundLane, creatingLane, refreshLanes]);

  const modelLabel = useMemo(() => {
    const id = boundLane?.model;
    return models.find((m) => m.id === id)?.label || id || 'Editor';
  }, [models, boundLane]);

  // ADR-562 D5 — WHO the member reads: the app's name for its resident, read
  // back from the wire, never asserted here.
  const speakerLabel = useMemo(() => {
    const slug = boundLane?.agent;
    if (slug) {
      const appName = apps.find((a) => a.slug === 'text')?.name;
      if (appName) return appName;
      const named = agents.find((a) => a.slug === slug)?.name;
      if (named) return named;
    }
    return modelLabel;
  }, [agents, apps, boundLane, modelLabel]);

  const words = useMemo(
    () => (text.trim() ? text.trim().split(/\s+/).length : 0),
    [text],
  );

  const name = documentName(path);

  return (
    <div ref={setWorkbenchNode} className="flex h-full min-h-0 flex-col">
      {/* ── The crumb row + boundary acts ─────────────────────────────── */}
      <div className="flex shrink-0 items-center gap-2 border-b border-border px-3 py-1.5">
        <button
          type="button"
          onClick={onClose}
          title="Back to documents"
          aria-label="Back to documents"
          className="inline-flex shrink-0 items-center rounded px-1.5 py-1 text-muted-foreground hover:bg-muted/50 hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
        </button>
        <div className="flex min-w-0 items-center gap-1.5 text-sm">
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 text-muted-foreground hover:text-foreground"
          >
            Text
          </button>
          <span className="text-muted-foreground/60">/</span>
          <button
            type="button"
            onClick={() => organizeVerbs.onRename?.({ path, name: leafOf(path) })}
            title={`${relPath(path)} — click to rename`}
            className="flex max-w-[26ch] items-center gap-1.5 truncate rounded px-1 py-0.5 font-medium text-foreground/80 hover:bg-muted/50"
          >
            <FileText className="h-3.5 w-3.5 shrink-0 text-sky-600 dark:text-sky-400" aria-hidden />
            <span className="truncate">{name}</span>
          </button>
        </div>

        <div className="min-w-0 flex-1" />

        {/* Save state — the quiet half of the header, like Docs' zoom. */}
        <span className="hidden shrink-0 text-[11px] text-muted-foreground sm:block">
          {saving ? 'Saving…' : dirty ? 'Unsaved changes' : savedAt ? 'Saved' : `${words} words`}
        </span>
        <button
          type="button"
          onClick={() => void save()}
          disabled={saving || !dirty}
          title="Save (⌘S)"
          className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-foreground px-2.5 py-1 text-xs text-background disabled:opacity-40"
        >
          {saving ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : savedAt && !dirty ? (
            <Check className="h-3 w-3" />
          ) : null}
          Save
        </button>

        <TextExport
          share={() => setShareTarget({ path, name: leafOf(path) })}
          text={text}
          name={name}
          path={path}
          compact={!fullLabels}
        />

        {sideIsOverlay && (
          <button
            type="button"
            onClick={() => setSideOpen((v) => !v)}
            title="Properties and chat"
            aria-label="Properties and chat"
            aria-expanded={sideOpen}
            className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded border border-border text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
          >
            <PanelRight className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* ── Canvas + rail ─────────────────────────────────────────────── */}
      <div className="relative flex min-h-0 flex-1">
        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-auto">
          {conflict && (
            <div className="border-b border-amber-500/40 bg-amber-500/10 px-4 py-2 text-xs">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
                <div className="space-y-2">
                  <p>
                    <span className="font-medium">{conflict.actor}</span> revised this
                    document while you were editing. Your text is still here — nothing
                    was lost, and nothing merges silently.
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => { setConflict(null); setReloadKey((n) => n + 1); }}
                      className="rounded-md border border-border px-2 py-1 hover:bg-muted/40"
                    >
                      Discard mine, show theirs
                    </button>
                    {conflict.currentHeadId && (
                      <button
                        type="button"
                        onClick={() => void save(conflict.currentHeadId)}
                        className="rounded-md border border-border px-2 py-1 hover:bg-muted/40"
                      >
                        Save mine over theirs
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
          {saveError && (
            <p className="border-b border-destructive/30 bg-destructive/5 px-4 py-2 text-xs text-destructive">
              {saveError}
            </p>
          )}

          {loading ? (
            <div className="flex flex-1 items-center justify-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Opening…
            </div>
          ) : notFound ? (
            <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-muted-foreground">
              Nothing exists at <span className="mx-1 font-mono text-xs">{relPath(path)}</span> —
              it may have been moved or never written.
            </div>
          ) : error ? (
            <div className="flex flex-1 items-center justify-center p-8 text-sm text-destructive">
              {error}
            </div>
          ) : (
            // The reading measure Docs gives its canvas: a centered column,
            // generous leading, the page ground behind it.
            <div className="mx-auto w-full max-w-3xl flex-1 px-6 py-8">
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                spellCheck
                placeholder="Start writing…"
                className={cn(
                  'min-h-[70vh] w-full resize-none bg-transparent font-mono text-[13px] leading-[1.75]',
                  'text-foreground outline-none placeholder:text-muted-foreground/50',
                )}
              />
            </div>
          )}
        </main>

        {/* The rail — Properties | Chat, Docs' grammar. At the narrow rungs it
            becomes an overlay with a header door (never an unreachable pane). */}
        <aside
          className={cn(
            'flex min-h-0 flex-col border-l border-border bg-background',
            sideIsOverlay
              ? cn('absolute inset-y-0 right-0 z-20 w-[min(22rem,85vw)] shadow-lg', sideOpen ? 'flex' : 'hidden')
              : 'w-80 shrink-0',
          )}
        >
          <div className="flex shrink-0 border-b border-border">
            {([['properties', 'Properties'], ['chat', 'Chat']] as const).map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                onClick={() => setRightTab(tab)}
                className={cn(
                  'flex-1 py-1.5 text-[11px] font-medium transition-colors',
                  rightTab === tab
                    ? 'border-b-2 border-foreground text-foreground'
                    : 'border-b-2 border-transparent text-muted-foreground hover:text-foreground',
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Properties — what a prose document HAS. Docs' inspector answers
              block properties; a plain-text document has no blocks, so this
              answers the document itself: where it lives, who touched it
              last, how long it is. */}
          <div className={cn('min-h-0 flex-1 overflow-auto', rightTab === 'properties' ? 'block' : 'hidden')}>
            <div className="space-y-4 p-3 text-xs">
              <section className="space-y-1">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">File</p>
                <p className="flex items-center gap-1.5 font-medium">
                  <FileText className="h-3.5 w-3.5 shrink-0 text-sky-600 dark:text-sky-400" />
                  <span className="truncate" title={relPath(path)}>{leafOf(path)}</span>
                </p>
                <p className="break-all font-mono text-[10px] text-muted-foreground">{relPath(path)}</p>
              </section>

              <section className="space-y-1">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Last edited
                </p>
                {headRevision ? (
                  <p className="text-muted-foreground">
                    {formatAuthorLabel(headRevision.authored_by) || headRevision.authored_by}
                    {headRevision.created_at
                      ? ` · ${formatRelativeTime(headRevision.created_at, { rollToDate: true })}`
                      : ''}
                  </p>
                ) : (
                  <p className="text-muted-foreground">No revisions yet.</p>
                )}
                <p className="text-muted-foreground/80">
                  Every save is signed and revertible — the full history lives in
                  Files → Get Info.
                </p>
              </section>

              <section className="space-y-1">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Length
                </p>
                <p className="text-muted-foreground">
                  {words.toLocaleString()} words · {text.length.toLocaleString()} characters
                </p>
              </section>

              <section className="space-y-1">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Format
                </p>
                <p className="text-muted-foreground">
                  Markdown, plain text. It stays a <span className="font-mono">.md</span> file —
                  the same one your connectors read and write.
                </p>
              </section>
            </div>
          </div>

          {/* Chat — Editor's bound lane. Mounted always, hidden by CSS. */}
          <div className={cn('min-h-0 flex-1 flex-col', rightTab === 'chat' ? 'flex' : 'hidden')}>
            {lanesEnabled === false ? (
              <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
                Lanes are not enabled on this deployment — Editor needs the model
                router. The document still opens and saves.
              </div>
            ) : boundLane ? (
              <LanePanel
                key={boundLane.id}
                laneId={boundLane.id}
                laneName={boundLane.name}
                modelLabel={modelLabel}
                speakerLabel={speakerLabel}
                artifactWrite="none"
                onArtifactWrite={() => setReloadKey((n) => n + 1)}
                suggestions={SUGGESTIONS}
                emptyState={
                  <div className="space-y-2 text-center text-xs text-muted-foreground">
                    <p className="text-sm font-medium text-foreground/80">Editor is reading this document.</p>
                    <p>
                      Ask for a tighter draft, a restructure, or a second opinion —
                      every change lands as a signed revision on{' '}
                      <span className="font-medium text-foreground/70">{leafOf(path)}</span>,
                      and the page updates as it works.
                    </p>
                  </div>
                }
              />
            ) : (
              <div className="flex flex-1 items-center justify-center gap-2 p-6 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Opening Editor…
              </div>
            )}
          </div>
        </aside>
      </div>

      {organizeModals}
      <ShareDialog target={shareTarget} onClose={() => setShareTarget(null)} />
    </div>
  );
}
