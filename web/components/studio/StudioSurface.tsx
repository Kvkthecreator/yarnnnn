'use client';

/**
 * StudioSurface — the first authoring app (ADR-440).
 *
 * One surface ↔ one operator act: AUTHOR AN ARTIFACT — the first honest DP29
 * composition since ADR-435 deleted Home. Two states:
 *
 *  - No `studio.file` param → the START state: pick a template (Document ·
 *    Deck · Article), name it, place it (meaning-placed under operation/ —
 *    the Studio owns no namespace, D6), or open an existing artifact.
 *  - `studio.file` set → the WORKBENCH, three columns (ADR-447): the per-type
 *    NAVIGATOR (left — a slide strip for a deck, an outline for a doc/article)
 *    · the CANVAS (center — sandboxed projection, edited in place) with the
 *    Add/Arrange toolbar over it · the BOUND chat LANE (right — full ADR-411
 *    machinery via LanePanel; its turns carry the authoring posture). Freddie's
 *    floating rail is suppressed on `studio` (Desktop.tsx onOwnChatSurface), so
 *    the Studio's own chat owns the right edge.
 *
 * Two write paths, one door (ADR-444/446): the lane writes judgment edits; the
 * member writes mechanical ones (toolbar ops + in-place text). Both bump
 * `reloadKey`, so the member watches the document change live.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2, Palette, Plus } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { useFileLoad } from '@/components/workspace/useFileLoad';
import { useSurfaceActions, useWindowCrumb } from '@/contexts/BreadcrumbContext';
import { LanePanel } from '@/components/chat-surface/LanePanel';
import { StudioCanvas, type PointerEvent2 } from './StudioCanvas';
import { StudioInsertMenu, type StudioVocabulary } from './StudioInsertMenu';
import { StudioNavigator } from './StudioNavigator';
import { applyArrangement, editBlockText, insertArrangement, insertBlock, type OpResult } from './artifactOps';

interface LaneInfo {
  id: string;
  name: string;
  model: string;
  artifact_path?: string | null;
  status: string;
}

interface TemplateInfo {
  slug: string;
  label: string;
  description: string;
}

/** Strip the /workspace/ prefix for display + comparison. */
function relPath(p: string): string {
  return p.replace(/^\/workspace\//, '');
}

function baseName(p: string): string {
  const parts = p.split('/');
  return parts[parts.length - 1] || p;
}

/** The artifact's declared template (data-template root attr). */
function extractTemplate(html: string): string {
  const m = /data-template="([a-z-]+)"/.exec(html);
  return m?.[1] ?? 'document';
}

/** Starter prompts per template — clickable chips while the lane is empty.
 *  Plain words, no model-speak: they teach what the Studio DOES. */
const TEMPLATE_SUGGESTIONS: Record<string, string[]> = {
  document: [
    'Draft this document from these points: ',
    'Add a section on ',
    'Tighten the wording throughout — keep the structure',
  ],
  deck: [
    'Draft a 6-slide deck that argues: ',
    'Rewrite the title slide to lead with the strongest number',
    'Add a slide that shows the table from a workspace file',
  ],
  article: [
    'Draft this article from my rough notes: ',
    'Give it a sharper title and subtitle',
    'Add a closing section with a call to action',
  ],
};

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48) || 'untitled';
}

export function StudioSurface() {
  const { get: getParam, set: setParam } = useSurfaceParam('studio');
  const artifactParam = getParam('file');
  const artifactPath = artifactParam
    ? artifactParam.startsWith('/')
      ? artifactParam
      : `/workspace/${artifactParam}`
    : null;

  // ADR-442 D4: the Studio declares its surface chrome into the surface bar
  // instead of hand-rolling a header row. Identity = the crumb (the strip's
  // root-click fires the leaf onClick → back to the start state, which is
  // what "New / open…" did).
  useWindowCrumb(
    'studio',
    artifactPath
      ? [
          {
            label: baseName(artifactPath),
            kind: 'artifact',
            onClick: () => setParam({ file: null }),
          },
        ]
      : [],
  );
  // ADR-447 (2026-07-12): the type-switcher (formerly a surface-bar action)
  // is DELETED. It was a legacy misread — morphing a whole artifact from a
  // deck into a document (or vice versa) is not an operation the member wants;
  // the artifact's TYPE is fixed at creation. Composition happens WITHIN the
  // type via the Arrange menu (re-lay the current page/slide). No surface-bar
  // action for the type.

  // ── Lane environment (models + existing lanes) ─────────────────────────
  const [lanesEnabled, setLanesEnabled] = useState<boolean | null>(null);
  const [models, setModels] = useState<Array<{ id: string; label: string }>>([]);
  const [lanes, setLanes] = useState<LaneInfo[]>([]);
  const [laneError, setLaneError] = useState<string | null>(null);

  const refreshLanes = useCallback(async () => {
    try {
      const res = await api.lanes.list();
      setLanesEnabled(res.enabled);
      setModels(res.models);
      setLanes(res.lanes as LaneInfo[]);
    } catch {
      setLanesEnabled(false);
      setLaneError('Could not load lanes.');
    }
  }, []);

  useEffect(() => {
    void refreshLanes();
  }, [refreshLanes]);

  // ── The bound lane for the open artifact (find-or-create) ──────────────
  const boundLane = useMemo(() => {
    if (!artifactPath) return null;
    return (
      lanes.find(
        (l) =>
          l.status === 'active' &&
          l.artifact_path &&
          relPath(l.artifact_path.startsWith('/') ? l.artifact_path : `/workspace/${l.artifact_path}`) ===
            relPath(artifactPath),
      ) ?? null
    );
  }, [lanes, artifactPath]);

  const [creatingLane, setCreatingLane] = useState(false);
  useEffect(() => {
    if (!artifactPath || !lanesEnabled || boundLane || creatingLane || !models.length) return;
    setCreatingLane(true);
    api.lanes
      .create({
        name: baseName(artifactPath),
        model: models[0].id,
        artifact_path: artifactPath,
      })
      .then(() => refreshLanes())
      .catch(() => setLaneError('Could not create the authoring lane.'))
      .finally(() => setCreatingLane(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifactPath, lanesEnabled, boundLane, models.length]);

  // ── The artifact itself (the surface owns the load; canvas projects) ───
  const [reloadKey, setReloadKey] = useState(0);
  const { file, loading, notFound } = useFileLoad(artifactPath ?? '', { reloadKey });

  const onArtifactWrite = useCallback(
    (writtenPath: string) => {
      if (!artifactPath) return;
      if (relPath(writtenPath) === relPath(artifactPath)) {
        setReloadKey((k) => k + 1);
      }
    },
    [artifactPath],
  );

  // ── Composer seeding (v1.1): pointing + the insert menu ────────────────
  const [seed, setSeed] = useState<{ text: string; nonce: number } | null>(null);
  const seedComposer = useCallback(
    (text: string) => setSeed((s) => ({ text, nonce: (s?.nonce ?? 0) + 1 })),
    [],
  );
  // ── The selection (ADR-444): held by the surface, it anchors the toolbar's
  // deterministic ops AND informs the lane (via a visible composer seed). ──
  const [selection, setSelection] = useState<{
    blockId: string | null;
    blockKind: string | null;
    slideIndex: number | null;
    text: string;
  } | null>(null);

  // ADR-446 D5: a click SELECTS a block (anchors Add/Slide ops + gates edit
  // mode). It NO LONGER auto-seeds the composer — that produced the seed-append
  // spam ("Selected the h2…: Selected the p…: "). The lane hears the selection
  // only on the explicit "Ask about this" affordance below.
  const onPoint = useCallback((p: PointerEvent2) => {
    setSelection({
      blockId: p.blockId,
      blockKind: p.blockKind,
      slideIndex: p.slideIndex,
      text: p.text,
    });
  }, []);
  const onPointClear = useCallback(() => {
    setSelection(null);
    setEditingBlockId(null);
  }, []);

  // ADR-446: which block is being edited in place (surface-held; the canvas
  // commands its iframe runtime). Selecting a different block exits the prior
  // edit (the runtime commits on the enter of the next).
  const [editingBlockId, setEditingBlockId] = useState<string | null>(null);

  // The explicit ask (replaces the auto-seed): the member chose to bring the
  // selection to the lane — one seed, on purpose, in operator words.
  const askAboutSelection = useCallback(() => {
    if (!selection) return;
    const s = selection;
    if (s.blockId || s.blockKind) {
      const kind = s.blockKind ?? 'content';
      const id = s.blockId ? ` (id: ${s.blockId})` : '';
      seedComposer(`About the ${kind} block${id}${s.text ? ` — "${s.text}"` : ''}: `);
    } else if (s.slideIndex != null) {
      seedComposer(`About slide ${s.slideIndex + 1}: `);
    } else {
      seedComposer(`About the selection${s.text ? ` "${s.text}"` : ''}: `);
    }
  }, [selection, seedComposer]);

  const template = useMemo(() => extractTemplate(file?.content ?? ''), [file]);
  const modelLabel = useMemo(
    () => models.find((m) => m.id === boundLane?.model)?.label ?? boundLane?.model ?? '',
    [models, boundLane],
  );

  // ── The served kernel vocabulary (ADR-443 R4 + ADR-444 + ADR-447): blocks +
  // arrangements — the toolbar EXECUTES from it, the posture teaches from the
  // same source. One fetch per open. (Layouts are served too but the Studio no
  // longer switches type — ADR-447 deleted the format-switcher.) ──
  const [vocabulary, setVocabulary] = useState<StudioVocabulary | null>(null);
  useEffect(() => {
    if (!artifactPath || vocabulary) return;
    api.studio
      .vocabulary()
      .then(setVocabulary)
      .catch(() => {
        /* toolbar menus stay empty — chat authoring unaffected */
      });
  }, [artifactPath, vocabulary]);

  // ── The mechanical executor (ADR-444): compute a deterministic op FE-side,
  // land it as ONE operator-attributed CAS-guarded revision, re-render. ──
  const [opError, setOpError] = useState<string | null>(null);
  const applyOp = useCallback(
    async (compute: (html: string) => OpResult | null, message: string) => {
      if (!artifactPath || !file?.content) return;
      setOpError(null);
      const result = compute(file.content);
      if (!result) {
        setOpError('Could not apply that here — select something in the document first.');
        return;
      }
      try {
        await api.studio.writeArtifact(
          artifactPath,
          result.html,
          file.head_version_id ?? null,
          message,
        );
        setReloadKey((k) => k + 1);
      } catch (e) {
        // A 409 = the lane wrote under us — reload and let the member retry.
        setOpError(e instanceof Error ? e.message : 'The edit did not land — reloading.');
        setReloadKey((k) => k + 1);
      }
    },
    [artifactPath, file],
  );

  const anchor = useMemo(
    () => ({ blockId: selection?.blockId ?? null, slideIndex: selection?.slideIndex ?? null }),
    [selection],
  );

  const handleInsertBlock = useCallback(
    (fragment: string, label: string) =>
      applyOp((html) => insertBlock(html, fragment, anchor), `Studio: add ${label} block`),
    [applyOp, anchor],
  );
  const handleInsertCited = useCallback(
    (kind: 'figure' | 'table', path: string) => {
      const rel = relPath(path);
      const base = vocabulary?.blocks.find((b) => b.kind === kind)?.fragment;
      if (!base) return;
      const fragment = base.replace(/data-ref="[^"]*"/, `data-ref="${rel}"`);
      void applyOp(
        (html) => insertBlock(html, fragment, anchor),
        `Studio: insert ${kind === 'figure' ? 'image' : 'table'} ${rel}`,
      );
    },
    [applyOp, anchor, vocabulary],
  );
  const handleAddArrangement = useCallback(
    (fragment: string, label: string) =>
      applyOp((html) => insertArrangement(html, fragment, anchor), `Studio: add ${label}`),
    [applyOp, anchor],
  );
  const handleApplyArrangement = useCallback(
    (fragment: string, label: string) =>
      applyOp(
        (html) => applyArrangement(html, fragment, anchor),
        `Studio: change arrangement to ${label}`,
      ),
    [applyOp, anchor],
  );

  // ADR-446: a block edit committed on the canvas (blur/idle) — the newInner is
  // already source-mapped (citation islands restored). Land it through the same
  // mechanical door as every other op; editBlockText no-ops a byte-identical
  // edit (returns null → applyOp surfaces "select something" only on a real
  // miss, so guard the no-op here to stay silent).
  const onEdit = useCallback(
    (blockId: string, newInner: string) => {
      if (!file?.content) return;
      if (!editBlockText(file.content, blockId, newInner)) return; // no-op — no revision, no error
      void applyOp((html) => editBlockText(html, blockId, newInner), `Studio: edit ${blockId} block`);
    },
    [applyOp, file],
  );

  // ADR-447: selecting a slide in the left navigator sets the selection to that
  // slide (no block) — the toolbar's Arrange ops target it via slideIndex.
  const selectSlideFromNavigator = useCallback((index: number) => {
    setSelection({ blockId: null, blockKind: null, slideIndex: index, text: '' });
    setEditingBlockId(null);
  }, []);

  // ── START STATE ─────────────────────────────────────────────────────────
  if (!artifactPath) {
    return (
      <StudioStart
        onOpen={(path) => setParam({ file: relPath(path) })}
      />
    );
  }

  // ── WORKBENCH ───────────────────────────────────────────────────────────
  // Three columns (ADR-447): the per-type NAVIGATOR (left — slide strip for a
  // deck, outline for a doc/article) · the CANVAS (center — the artifact, edited
  // in place) with the Add/Arrange toolbar over it · the bound CHAT LANE (right
  // — the judgment path; Freddie's floating rail is suppressed here, so the
  // Studio's own chat owns the right edge). Identity + the crumb live in the
  // surface bar (ADR-442 D4).
  return (
    <div className="relative flex h-full min-h-0 flex-col">
      <div className="flex min-h-0 flex-1">
        {/* Left — the per-type navigator. */}
        <div className="w-56 shrink-0 border-r border-border">
          <StudioNavigator
            layout={template}
            html={file?.content ?? ''}
            selectedSlide={selection?.slideIndex ?? null}
            onSelectSlide={selectSlideFromNavigator}
          />
        </div>

        {/* Center — the toolbar over the canvas (renders, edits in place). */}
        <div className="flex min-w-0 flex-1 flex-col">
          <StudioInsertMenu
            vocabulary={vocabulary}
            layout={template}
            selection={selection}
            editing={editingBlockId != null}
            onClearSelection={onPointClear}
            onInsertBlock={handleInsertBlock}
            onInsertCited={handleInsertCited}
            onAddArrangement={handleAddArrangement}
            onApplyArrangement={handleApplyArrangement}
            onSeed={seedComposer}
            onAskAboutSelection={askAboutSelection}
            onToggleEdit={() =>
              setEditingBlockId((cur) =>
                cur === selection?.blockId ? null : (selection?.blockId ?? null),
              )
            }
          />
          {opError && (
            <p className="border-b border-border bg-red-50 px-3 py-1 text-[11px] text-red-700 dark:bg-red-950/30 dark:text-red-300">
              {opError}
            </p>
          )}
          {loading ? (
            <div className="flex flex-1 items-center justify-center text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : notFound || !file ? (
            <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
              This artifact does not exist yet — ask the lane to create it at{' '}
              {relPath(artifactPath)}.
            </div>
          ) : (
            <StudioCanvas
              file={file}
              artifactPath={artifactPath}
              onPoint={onPoint}
              onPointClear={onPointClear}
              editingBlockId={editingBlockId}
              onEdit={onEdit}
              onEditExited={() => setEditingBlockId(null)}
            />
          )}
        </div>

        {/* Right — the bound chat lane (the mind; the single judgment path). */}
        <div className="flex w-[380px] shrink-0 flex-col border-l border-border">
          {lanesEnabled === false ? (
            <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
              Lanes are not enabled on this deployment — the Studio&apos;s authoring
              chat needs the model router. The canvas still renders the artifact.
            </div>
          ) : boundLane ? (
            <LanePanel
              key={boundLane.id}
              laneId={boundLane.id}
              laneName={boundLane.name}
              modelLabel={modelLabel}
              onArtifactWrite={onArtifactWrite}
              composerSeed={seed}
              // ADR-443: the canvas (center) IS the artifact view — suppress
              // the transcript's inline ArtifactCard so the lane doesn't render
              // the very thing we're looking at twice. The authoring trail lives
              // in the artifact's revision history (trace), not in breadcrumbs.
              artifactWrite="none"
              emptyState={
                <div className="space-y-2 text-center text-xs text-muted-foreground">
                  <p className="text-sm font-medium text-foreground/80">Tell it what to write.</p>
                  <p>
                    Ask in plain words — every reply becomes an edit to{' '}
                    <span className="font-medium text-foreground/70">{baseName(artifactPath)}</span>,
                    and the page updates as it works. It can also pull in your
                    workspace files — images, tables, notes — as live references.
                  </p>
                </div>
              }
              suggestions={TEMPLATE_SUGGESTIONS[template] ?? TEMPLATE_SUGGESTIONS.document}
            />
          ) : (
            <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {laneError ?? 'Preparing the authoring lane…'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── The start state — template picker + meaning-placed creation ──────────

function StudioStart({ onOpen }: { onOpen: (path: string) => void }) {
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [recents, setRecents] = useState<
    Array<{ path: string; updated_at: string | null; summary: string | null }>
  >([]);
  const [selected, setSelected] = useState<string>('document');
  const [name, setName] = useState('');
  const [pathEdited, setPathEdited] = useState(false);
  const [path, setPath] = useState('');
  const [existing, setExisting] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.studio
      .templates()
      .then((res) => setTemplates(res.templates))
      .catch(() => setError('Could not load templates.'));
    api.studio
      .artifacts()
      .then((res) => setRecents(res.artifacts))
      .catch(() => {
        /* recents are a convenience — creation still works without them */
      });
  }, []);

  // Meaning-placed default (D6): under operation/, named by the work — the
  // member edits freely; the Studio never invents an app-named root.
  useEffect(() => {
    if (pathEdited) return;
    const slug = slugify(name);
    setPath(name ? `operation/${slug}/${selected}.html` : '');
  }, [name, selected, pathEdited]);

  const create = async () => {
    if (!path || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.studio.createArtifact(path, selected);
      onOpen(res.path);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Creation failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full items-center justify-center overflow-y-auto p-8">
      <div className="w-full max-w-lg space-y-6">
        <div className="space-y-1 text-center">
          <Palette className="mx-auto h-8 w-8 text-muted-foreground" />
          <h1 className="text-lg font-semibold">Studio</h1>
          <p className="text-sm text-muted-foreground">
            Pick a shape, name it, then describe what you want in plain words.
            The Studio writes it as a real document in your workspace — you
            watch it take shape live, and it can pull in your files, images,
            and data as it goes.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {templates.map((t) => (
            <button
              key={t.slug}
              type="button"
              onClick={() => setSelected(t.slug)}
              className={`rounded-lg border p-3 text-left transition-colors ${
                selected === t.slug
                  ? 'border-foreground/60 bg-muted/40'
                  : 'border-border hover:bg-muted/20'
              }`}
            >
              <p className="text-sm font-medium">{t.label}</p>
              <p className="mt-1 text-[11px] leading-snug text-muted-foreground">
                {t.description}
              </p>
            </button>
          ))}
        </div>

        <div className="space-y-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Name it (e.g. IR deck v3)"
            className="w-full rounded-md border border-border bg-transparent px-3 py-2 text-sm outline-none focus:border-foreground/40"
          />
          <input
            value={path}
            onChange={(e) => {
              setPathEdited(true);
              setPath(e.target.value);
            }}
            placeholder="operation/…/artifact.html (meaning-placed)"
            className="w-full rounded-md border border-border bg-transparent px-3 py-2 font-mono text-xs outline-none focus:border-foreground/40"
          />
          <button
            type="button"
            onClick={create}
            disabled={!path || busy}
            className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-foreground px-3 py-2 text-sm font-medium text-background disabled:opacity-40"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Create
          </button>
        </div>

        {recents.length > 0 && (
          <div className="space-y-2 border-t border-border pt-4">
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
              Continue where you left off
            </p>
            <ul className="space-y-1">
              {recents.slice(0, 6).map((r) => (
                <li key={r.path}>
                  <button
                    type="button"
                    onClick={() => onOpen(r.path)}
                    className="flex w-full items-center justify-between gap-3 rounded-md border border-border px-3 py-2 text-left transition-colors hover:bg-muted/30"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm">{baseName(r.path)}</span>
                      <span className="block truncate text-[11px] text-muted-foreground">
                        {relPath(r.path)}
                      </span>
                    </span>
                    {r.updated_at && (
                      <span className="shrink-0 text-[10px] text-muted-foreground">
                        {new Date(r.updated_at).toLocaleDateString()}
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <details className="border-t border-border pt-3">
          <summary className="cursor-pointer text-xs text-muted-foreground">
            Open by workspace path…
          </summary>
          <div className="mt-2 flex gap-2">
            <input
              value={existing}
              onChange={(e) => setExisting(e.target.value)}
              placeholder="operation/…/deck.html"
              className="flex-1 rounded-md border border-border bg-transparent px-3 py-2 font-mono text-xs outline-none focus:border-foreground/40"
            />
            <button
              type="button"
              onClick={() => existing.trim() && onOpen(existing.trim())}
              disabled={!existing.trim()}
              className="rounded-md border border-border px-3 py-2 text-sm disabled:opacity-40"
            >
              Open
            </button>
          </div>
        </details>

        {error && <p className="text-center text-xs text-red-500">{error}</p>}
      </div>
    </div>
  );
}
