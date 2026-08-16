'use client';

/**
 * TextEditor — Text's open state (ADR-571, deepened to Docs parity by ADR-572).
 *
 * The Docs open-state shape, one medium down: a crumb row (app · document
 * name, click to rename) with the view controls and boundary acts (Read/Write ·
 * zoom · Share · Export) on the right, the canvas in the middle, and the
 * Properties|Chat rail carrying Editor's bound lane — the same two tabs, the
 * same never-unmount rule so a streaming turn survives a tab switch.
 *
 * ## The canvas has two faces, and neither is a block model
 *
 * ADR-572 D1: **Read** renders the markdown (`ProseReader` — serif headings,
 * styled tables, a real reading measure); **Write** is the textarea ADR-456 D1
 * requires. One source of truth (`text`), one direction of flow (source →
 * render). The rendered view never writes, holds no ids, and annotates
 * nothing; delete it and the file is unchanged. That is what makes it a view.
 *
 * Read is the DEFAULT on open, because a document that already exists is
 * something you arrive to read; Write is one click (or a keystroke) away.
 *
 * ## What is deliberately NOT Docs
 *
 * Docs autosaves on a 2s idle timer with no Save button and no dirty state.
 * Text keeps an explicit Save + ⌘S + a dirty indicator, because the CAS
 * conflict here is a PRODUCT surface (a connector may hold the same file) and
 * a member needs to know which bytes are theirs before a 409 names someone
 * else. Divergence recorded in ADR-572 D5.
 *
 * The save path is ADR-570's, unchanged: `PATCH /workspace/file` (prose class
 * ∧ carve law ∧ principal gate), CAS-guarded on the head the document was
 * loaded with.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  Eye,
  FileText,
  Loader2,
  PanelRight,
  Pencil,
  Search,
} from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { useFileLoad } from '@/components/workspace/useFileLoad';
import { useFileOrganizeVerbs } from '@/hooks/useFileOrganizeVerbs';
import { formatAuthorLabel } from '@/lib/workspace/attribution';
import { formatRelativeTime } from '@/lib/formatting';
import { LanePanel } from '@/components/chat-surface/LanePanel';
import { ShareDialog } from '@/components/workspace/ShareDialog';
import { TextExport } from '@/components/text/TextExport';
import { ProseReader } from '@/components/text/ProseReader';
import { MarkdownToolbar, type ToolbarAction } from '@/components/text/MarkdownToolbar';
import { FindReplaceBar } from '@/components/text/FindReplaceBar';
import { parseOutline, readingMinutes } from '@/components/text/outline';
import {
  insertLink,
  insertRule,
  insertTable,
  offsetOfLine,
  replaceAll as replaceAllIn,
  replaceOne,
  toggleHeading,
  toggleList,
  toggleQuote,
  toggleWrap,
  type Edit,
} from '@/components/text/markdownEdits';
import { documentName, leafOf } from '@/components/text/TextSurface';
import { useWorkbenchWidth } from '@/lib/authoring/workbench-width';
import { cn } from '@/lib/utils';

type LanesEnv = Awaited<ReturnType<typeof api.lanes.list>>;
type LaneRow = LanesEnv['lanes'][number];

const WORKSPACE_PREFIX = '/workspace/';
const relPath = (p: string) => (p.startsWith(WORKSPACE_PREFIX) ? p.slice(WORKSPACE_PREFIX.length) : p);

/** Docs' clamp (`StudioSurface`: 0.25–2), so the two apps zoom alike. */
const ZOOM_MIN = 0.25;
const ZOOM_MAX = 2;

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
  const taRef = useRef<HTMLTextAreaElement | null>(null);

  // ── View state (ADR-572 D1/D2) — none of it touches the file.
  const [mode, setMode] = useState<'read' | 'write'>('read');
  const [zoom, setZoom] = useState(1);
  const [finding, setFinding] = useState(false);

  // Rail: Properties | Chat, the Docs grammar. The lane stays MOUNTED while
  // Properties is up (CSS-hidden) so a streaming turn survives the switch.
  const [rightTab, setRightTab] = useState<'properties' | 'chat'>('properties');
  const [sideOpen, setSideOpen] = useState(true);
  const { sideIsOverlay, singlePane, fullLabels } = wb;
  // The single-pane rung shows ONE pane at a time with a bottom tab bar — the
  // Docs ladder's last rung. Without it the rail would be unreachable on a
  // phone (the ADR-519 lesson: never ship an inescapable state).
  const [activePane, setActivePane] = useState<'canvas' | 'chat'>('canvas');

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

  // ── Applying a source edit ──────────────────────────────────────────────
  // Every formatting/insert/replace path funnels through here: set the text,
  // then restore the caret the pure function computed. The restore has to wait
  // for React to paint the new value, hence the rAF — setting
  // selectionStart before the DOM holds the new string clamps it to the old
  // length and the caret jumps to the end.
  const applyEdit = useCallback((edit: Edit) => {
    setText(edit.text);
    requestAnimationFrame(() => {
      const ta = taRef.current;
      if (!ta) return;
      ta.focus();
      ta.setSelectionRange(edit.selectionStart, edit.selectionEnd);
    });
  }, []);

  const runAction = useCallback(
    (action: ToolbarAction) => {
      const ta = taRef.current;
      // With no textarea (Read mode), an edit has no caret to act on.
      if (!ta) return;
      const s = ta.selectionStart;
      const e = ta.selectionEnd;
      switch (action.kind) {
        case 'wrap': return applyEdit(toggleWrap(text, s, e, action.marker));
        case 'heading': return applyEdit(toggleHeading(text, s, e, action.level));
        case 'list': return applyEdit(toggleList(text, s, e, action.ordered));
        case 'quote': return applyEdit(toggleQuote(text, s, e));
        case 'link': return applyEdit(insertLink(text, s, e));
        case 'table': return applyEdit(insertTable(text, s, e));
        case 'rule': return applyEdit(insertRule(text, s, e));
      }
    },
    [text, applyEdit],
  );

  /** Select a source span and scroll it into view (find + outline jump). */
  const reveal = useCallback((span: [number, number]) => {
    setMode('write');
    requestAnimationFrame(() => {
      const ta = taRef.current;
      if (!ta) return;
      ta.focus();
      ta.setSelectionRange(span[0], span[1]);
      // Approximate scroll: the fraction of the document before the match.
      const ratio = span[0] / Math.max(1, ta.value.length);
      ta.scrollTop = Math.max(0, ratio * ta.scrollHeight - ta.clientHeight / 3);
    });
  }, []);

  // ── Keyboard: ⌘S save · ⌘F find · ⌘B/⌘I/⌘K formatting ──────────────────
  // Window-level, because the document is the subject of the whole surface
  // (the Docs reflex). Formatting keys only bite in Write mode — in Read mode
  // there is no caret and ⌘B should fall through to the browser.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey)) return;
      const k = e.key.toLowerCase();
      if (k === 's') { e.preventDefault(); void save(); return; }
      if (k === 'f') { e.preventDefault(); setMode('write'); setFinding(true); return; }
      if (mode !== 'write') return;
      if (k === 'b') { e.preventDefault(); runAction({ kind: 'wrap', marker: '**' }); }
      else if (k === 'i') { e.preventDefault(); runAction({ kind: 'wrap', marker: '_' }); }
      else if (k === 'k') { e.preventDefault(); runAction({ kind: 'link' }); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [save, runAction, mode]);

  // Rename through the shared organize grammar; the surface follows the file
  // to its new path (the Docs `setParam({ file })` reflex).
  const { verbs: organizeVerbs, modals: organizeModals } = useFileOrganizeVerbs({
    onAfterMutate: (newPath) => {
      onSaved?.();
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
  const outline = useMemo(() => parseOutline(text), [text]);

  const name = documentName(path);
  // On the single-pane rung the rail becomes a tabbed pane; above it, an
  // overlay drawer or a resting column.
  const showCanvas = !singlePane || activePane === 'canvas';
  const showRail = singlePane ? activePane === 'chat' : true;

  return (
    <div ref={setWorkbenchNode} className="flex h-full min-h-0 flex-col">
      {/* ── The crumb row + view controls + boundary acts ───────────────── */}
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

        {/* Read | Write — the two faces of one source (ADR-572 D1). */}
        <div
          role="group"
          aria-label="View mode"
          className="flex shrink-0 items-center rounded-md border border-border p-0.5"
        >
          {([['read', 'Read', Eye], ['write', 'Write', Pencil]] as const).map(([m, label, Icon]) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              aria-pressed={mode === m}
              title={m === 'read' ? 'Read the rendered document' : 'Edit the markdown source'}
              className={cn(
                'inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] transition-colors',
                mode === m
                  ? 'bg-foreground text-background'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <Icon className="h-3 w-3" />
              {fullLabels && label}
            </button>
          ))}
        </div>

        {/* Find — the source search (⌘F). Write-mode act, shown always so the
            affordance is discoverable; pressing it switches mode. */}
        <button
          type="button"
          onClick={() => { setMode('write'); setFinding((v) => !v); }}
          title="Find and replace (⌘F)"
          aria-label="Find and replace"
          aria-expanded={finding}
          className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded text-muted-foreground hover:bg-muted/50 hover:text-foreground"
        >
          <Search className="h-3.5 w-3.5" />
        </button>

        {/* Zoom — a VIEW control (doesn't touch the file), Docs' own clamp. */}
        <div className="hidden shrink-0 items-center gap-0.5 sm:flex">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(ZOOM_MIN, Math.round((z - 0.1) * 100) / 100))}
            className="rounded px-1.5 py-0.5 text-sm text-muted-foreground hover:bg-muted/40"
            title="Zoom out"
            aria-label="Zoom out"
          >
            −
          </button>
          <button
            type="button"
            onClick={() => setZoom(1)}
            className="min-w-[3ch] rounded px-1 py-0.5 text-[11px] tabular-nums text-muted-foreground hover:bg-muted/40"
            title="Reset zoom to 100%"
          >
            {Math.round(zoom * 100)}%
          </button>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(ZOOM_MAX, Math.round((z + 0.1) * 100) / 100))}
            className="rounded px-1.5 py-0.5 text-sm text-muted-foreground hover:bg-muted/40"
            title="Zoom in"
            aria-label="Zoom in"
          >
            +
          </button>
        </div>

        {/* Save state — the quiet half of the header. */}
        <span className="hidden shrink-0 text-[11px] text-muted-foreground lg:block">
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

        {sideIsOverlay && !singlePane && (
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
        {showCanvas && (
        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
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
            /* A real failure says so, and offers the retry — never "it doesn't
               exist", which reads as data loss (the Docs honesty rule). */
            <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
              <p className="text-sm text-muted-foreground">
                Couldn’t load {relPath(path)}. The document is still there — the
                request failed.
              </p>
              <button
                type="button"
                onClick={() => setReloadKey((n) => n + 1)}
                className="rounded border border-border px-2.5 py-1 text-xs hover:bg-muted/40"
              >
                Try again
              </button>
            </div>
          ) : mode === 'read' ? (
            // ── Read: the rendered document. A VIEW — never writes, holds no
            //    ids, annotates nothing (ADR-572 D1).
            <div className="min-h-0 flex-1 overflow-auto">
              <div className="mx-auto w-full max-w-[68ch] px-8 py-10">
                <ProseReader text={text} zoom={zoom} />
              </div>
            </div>
          ) : (
            // ── Write: the textarea ADR-456 D1 requires, with the source
            //    affordances (formatting row, find) above it.
            <>
              <MarkdownToolbar onAction={runAction} />
              {finding && (
                <FindReplaceBar
                  text={text}
                  onReveal={reveal}
                  onReplaceOne={(span, w) => applyEdit(replaceOne(text, span, w))}
                  onReplaceAll={(n, w) => applyEdit(replaceAllIn(text, n, w))}
                  onClose={() => setFinding(false)}
                />
              )}
              <div className="min-h-0 flex-1 overflow-auto">
                <div
                  className="mx-auto w-full max-w-3xl px-6 py-8"
                  style={zoom === 1 ? undefined : { zoom }}
                >
                  <textarea
                    ref={taRef}
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
              </div>
            </>
          )}
        </main>
        )}

        {/* The rail — Properties | Chat, Docs' grammar. At the narrow rungs it
            becomes an overlay with a header door; at the narrowest it is a
            pane the bottom bar switches to (never an unreachable pane). */}
        {showRail && (
        <aside
          className={cn(
            'flex min-h-0 flex-col border-border bg-background',
            singlePane
              ? 'min-w-0 flex-1'
              : sideIsOverlay
                ? cn('absolute inset-y-0 right-0 z-20 w-[min(22rem,85vw)] border-l shadow-lg', sideOpen ? 'flex' : 'hidden')
                : 'w-80 shrink-0 border-l',
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
              block properties AND carries the document's Outline (ADR-526 D2
              put the outline in the pane, not a rail); Text mirrors the
              outline and answers the document itself for the rest. */}
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

              {/* The OUTLINE — Docs' own pane section, addressed by SOURCE
                  LINE rather than by block id (ADR-572 D3). A line number is
                  a coordinate into the bytes, not an annotation on them. */}
              <section className="space-y-1">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Outline
                </p>
                {outline.length > 0 ? (
                  <ul className="space-y-px">
                    {outline.map((h) => (
                      <li key={`${h.line}-${h.text}`}>
                        <button
                          type="button"
                          onClick={() => {
                            const off = offsetOfLine(text, h.line);
                            reveal([off, off + h.text.length]);
                          }}
                          title={h.text}
                          style={{ paddingLeft: `${(h.level - 1) * 10}px` }}
                          className="flex w-full items-baseline truncate rounded px-1 py-px text-left text-[10px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
                        >
                          <span className="truncate">{h.text}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  // The honest empty state — never invent a structure the
                  // document doesn't have (Docs' rule, ADR-526 §7).
                  <p className="text-[10px] text-muted-foreground">
                    No headings yet — add one and it appears here.
                  </p>
                )}
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
                <p className="text-muted-foreground">
                  {outline.length.toLocaleString()} heading{outline.length === 1 ? '' : 's'} ·
                  {' '}about {readingMinutes(words)} min read
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
        )}
      </div>

      {/* The single-pane rung's bottom tab bar: one pane at a time. 44px is
          the touch floor (Apple/Google) and this is the PRIMARY navigation on
          a phone — the Docs ladder's last rung, ported. */}
      {singlePane && (
        <nav className="flex shrink-0 border-t border-border">
          {([['canvas', 'Document'], ['chat', 'Editor']] as const).map(([pane, label]) => (
            <button
              key={pane}
              type="button"
              onClick={() => setActivePane(pane)}
              className={cn(
                'min-h-[44px] flex-1 py-2 text-xs font-medium transition-colors',
                activePane === pane
                  ? 'border-t-2 border-foreground text-foreground'
                  : 'border-t-2 border-transparent text-muted-foreground',
              )}
            >
              {label}
            </button>
          ))}
        </nav>
      )}

      {organizeModals}
      <ShareDialog target={shareTarget} onClose={() => setShareTarget(null)} />
    </div>
  );
}
