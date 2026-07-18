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
 * member writes mechanical ones (toolbar ops + in-place text). A member's own
 * TEXT edit lands invisibly — the durable revision is POSTed but the canvas is
 * NOT reloaded (it already shows the typed result), so save feels ambient.
 * Structural ops + foreign (lane) writes reload, preserving scroll.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Copy, FolderOpen, Link2, Loader2, MoreHorizontal, Palette, PanelLeft } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useSurfaceParam, useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { LearnFromFlowModal } from './LearnFromFlowModal';
import { NewArtifactModal, slugify } from './NewArtifactModal';
import { StudioNewMenu } from './StudioNewMenu';
import { studioShapeStyle } from './studioShapes';
import { OpenArtifactModal } from './OpenArtifactModal';
import { useFileLoad } from '@/components/workspace/useFileLoad';
import { useFileContextMenu } from '@/components/workspace/FileContextMenu';
import { useSelfLocatedSurface, useSurfaceActions, useWindowCrumb } from '@/contexts/BreadcrumbContext';
import { useFileOrganizeVerbs } from '@/hooks/useFileOrganizeVerbs';
import { LanePanel } from '@/components/chat-surface/LanePanel';
import { StudioCanvas, type PointerEvent2, type StudioContextTarget } from './StudioCanvas';
import { StudioBlockMenu } from './StudioBlockMenu';
import { StudioSlashPalette } from './StudioSlashPalette';
import { StudioToolbar, type StudioSelection, type StudioVocabulary } from './StudioToolbar';
import { StudioDesignTab, type StructVerb } from './StudioDesignTab';
import { StudioNavigator } from './StudioNavigator';
import {
  applyArrangement,
  applySkin,
  convertBlock,
  deleteBlock,
  deletePage,
  duplicateBlock,
  pasteBlock,
  duplicatePage,
  editBlockText,
  galleryFragment,
  insertArrangement,
  insertBlock,
  insertBlockInSlot,
  mergeBlock,
  moveBlock,
  moveBlockTo,
  movePage,
  splitBlock,
  splitBlockAndInsert,
  removePageBackground,
  removeSkin,
  retrofitKernel,
  setPageBackground,
  setMeasure,
  setToken,
  type OpResult,
} from './artifactOps';

interface LaneInfo {
  id: string;
  name: string;
  model: string;
  artifact_path?: string | null;
  /** ADR-450/452 — the derive binding (a "Learn from" lane). */
  derive_recipe?: string | null;
  derive_source?: string | null;
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

/** The artifact's operator-facing NAME — the titleized meaning folder.
 *
 *  `operation/prd-for-yarnnn/document.html` → "Prd for yarnnn". The leaf is a
 *  TYPE marker (document/deck/article/page.html), not a name — which is why the
 *  crumb used to say "document.html" while the landing card, correctly, said
 *  "Prd for yarnnn". Three names for one artifact, and the two the member could
 *  see were the two that weren't its name.
 *
 *  Mirrors `artifact_name` in services/studio.py (the same resolver ADR-459
 *  already uses for the landing). Kept in sync by the layout-mode gate's
 *  parity check — the FE needs it synchronously for the crumb, and the
 *  workbench doesn't fetch the artifacts list. */
function artifactName(p: string): string {
  const parts = (p || '').split('/').filter(Boolean);
  if (!parts.length) return p;
  const parent = parts.length >= 2 ? parts[parts.length - 2] : null;
  // 'workspace' + 'operation' are the region, never the name.
  const stem =
    parent && parent !== 'operation' && parent !== 'workspace'
      ? parent
      : parts[parts.length - 1].replace(/\.[a-z0-9]+$/i, '');
  const spaced = stem.replace(/[-_]+/g, ' ').trim();
  return spaced ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : p;
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
            label: artifactName(artifactPath),
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

  // ADR-446 surface-bar action: a single ⋯ that opens the organize menu
  // ADR-458 D3: the surface bar is crumb-only — the "File actions" button is
  // deleted; the file verbs live in the Design tab's document scope (the one
  // settings home). Registering the empty set keeps the bar clean.
  useSurfaceActions('studio', []);
  // 2026-07-14 (operator ruling): in the WORKBENCH the toolbar row renders the
  // crumb itself (Studio · ‹artifact›), so the OS strip suppresses — one
  // locator, never two, and the ~28px band is reclaimed for the canvas. The
  // START state keeps the OS strip (it has no toolbar row of its own).
  useSelfLocatedSurface('studio', Boolean(artifactPath));

  // ── Lane environment (models + existing lanes) ─────────────────────────
  const [lanesEnabled, setLanesEnabled] = useState<boolean | null>(null);
  const [models, setModels] = useState<Array<{ id: string; label: string }>>([]);
  const [lanes, setLanes] = useState<LaneInfo[]>([]);
  const [laneError, setLaneError] = useState<string | null>(null);

  const refreshLanes = useCallback(async () => {
    try {
      // Studio's lanes ARE the bound ones — they left the /chat list, not this one.
      const res = await api.lanes.list(true);
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
    // `!models.length` was part of this guard until 2026-07-16 — a proxy for
    // "the router has an engine to bind", which was only ever true because the
    // next line reached into the array. The engine now resolves server-side
    // from the Agent, so `lanesEnabled` (the router-on signal) is the honest
    // condition and the array's contents are none of this surface's business.
    if (!artifactPath || !lanesEnabled || boundLane || creatingLane) return;
    setCreatingLane(true);
    api.lanes
      .create({
        name: baseName(artifactPath),
        // ADR-460 §4b — a bound lane carries an Agent like every other lane.
        // This was `model: models[0].id`: whatever engine happened to be FIRST
        // in the array. Nobody chose it; nobody named it. The Designer's engine
        // resolves server-side and IS models[0]'s engine (claude-sonnet-4-6),
        // so every bound lane runs exactly what it ran before — it just has a
        // colleague now, and a settle from here attributes to a person.
        agent: 'designer',
        artifact_path: artifactPath,
      })
      .then(() => refreshLanes())
      .catch(() => setLaneError('Could not create the authoring lane.'))
      .finally(() => setCreatingLane(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifactPath, lanesEnabled, boundLane]);

  // ── The artifact itself (the surface owns the load; canvas projects) ───
  const [reloadKey, setReloadKey] = useState(0);
  const { file: loadedFile, loading, notFound } = useFileLoad(artifactPath ?? '', { reloadKey });

  // ── Invisible save (the local CAS-base override) ──────────────────────────
  // A member's own edit lands as a revision, but the canvas ALREADY shows the
  // typed result — reloading the iframe to re-display an identical DOM is what
  // makes save feel like a jarring event (blank flash, caret jump, scroll
  // reset). Instead we keep a LOCAL override of the artifact's content +
  // head_version_id: an own-edit write advances both in place, WITHOUT a
  // refetch or an iframe reload. `file` below is the merged view the rest of
  // the surface reads.
  //
  // Validity anchor: an override descends from the loaded file it was FORKED
  // from — captured as `anchorHead` (the loadedFile head at fork time). It stays
  // valid as long as `loadedFile.head_version_id` still equals that anchor
  // (text edits never refetch, so the loaded head is stable through a whole
  // typing session — a chain of edits extends the SAME override, each advancing
  // `headVersionId` while `anchorHead` is pinned). A foreign reload lands a new
  // loadedFile with a DIFFERENT head → the anchor no longer matches → the
  // override is dropped and the authoritative state wins.
  const [localOverride, setLocalOverride] = useState<{
    anchorHead: string | null; // the loadedFile head this override chain forked from
    content: string;
    headVersionId: string; // the current (advancing) head after N chained edits
  } | null>(null);

  const file = useMemo(() => {
    if (!loadedFile) return loadedFile;
    if (localOverride && localOverride.anchorHead === (loadedFile.head_version_id ?? null)) {
      return {
        ...loadedFile,
        content: localOverride.content,
        head_version_id: localOverride.headVersionId,
      };
    }
    return loadedFile;
  }, [loadedFile, localOverride]);

  // The LIVE view of the artifact, readable inside a handler that fired in the
  // same tick as a previous write — before React re-rendered `file`. Two ops can
  // originate from one gesture (a drag's handle-press blurs a live edit: blur
  // commits, then the drop reorders), and both closures capture the SAME stale
  // `file`. The second then writes against a consumed head and 409s ("the edit
  // did not land") on a perfectly good drag. The queue below chains off this ref
  // so each op computes from the previous op's RESULT, not from a render.
  const liveRef = useRef<{ content: string; head: string | null } | null>(null);
  useEffect(() => {
    liveRef.current = file
      ? { content: file.content ?? '', head: file.head_version_id ?? null }
      : null;
  }, [file]);

  // Read through a ref for the same reason as liveRef: the write queue runs
  // async, so a render closure could hand it a stale (or not-yet-loaded)
  // vocabulary. Populated by the effect below, once the vocabulary lands.
  const kernelStyleRef = useRef<string | undefined>(undefined);

  // A path change or a foreign reload (reloadKey bump) starts fresh — drop any
  // override so it can't shadow the authoritative reload.
  useEffect(() => {
    setLocalOverride(null);
  }, [artifactPath, reloadKey]);

  const onArtifactWrite = useCallback(
    (writtenPath: string) => {
      if (!artifactPath) return;
      if (relPath(writtenPath) === relPath(artifactPath)) {
        // A FOREIGN write (the lane) genuinely changed the file — reload.
        setReloadKey((k) => k + 1);
      }
    },
    [artifactPath],
  );

  // ── Organize the open artifact (ADR-446): Rename / Move to… / Move to Trash.
  // The SAME shared implementation the Files surface uses (useFileOrganizeVerbs)
  // — the artifact-as-file is organized from the app that opened it (the macOS
  // window-titlebar model), not only from the Files explorer. Optimistic: an
  // inbound record / machine-config 403s with the honest reason; an ordinary
  // artifact (or an uploaded file under inbound/uploads/) organizes cleanly.
  // After the mutation: rename/move → re-point the surface at the new path;
  // trash → the artifact is gone, so fall to the Studio START state.
  // ── Rename (2026-07-15) ────────────────────────────────────────────────
  // The artifact's NAME is its meaning folder — `operation/prd-for-yarnnn/
  // document.html` is "Prd for yarnnn". The leaf is a TYPE marker naming the
  // layout, so the shared file-rename was renaming the TYPE: you could rename
  // `document.html` to `report.html` and the artifact's name would not move.
  //
  // So the Studio renames the FOLDER through its own endpoint (which moves
  // every file under it, then retitles so the h1 follows). Committed on Enter
  // or blur — never per-keystroke: a rename MOVES substrate identity, and each
  // intermediate state would be a real move ("Q", "Q3", "Q3 "…).
  const [renaming, setRenaming] = useState(false);
  const [renameBusy, setRenameBusy] = useState(false);
  const commitRename = useCallback(
    async (next: string) => {
      if (!artifactPath || renameBusy) return;
      const trimmed = next.trim();
      // No change / cleared → just close. Never rename to nothing.
      if (!trimmed || trimmed === artifactName(artifactPath)) {
        setRenaming(false);
        return;
      }
      setRenameBusy(true);
      setOpError(null);
      try {
        const r = await api.studio.renameArtifact(artifactPath, trimmed);
        if (r.renamed) {
          setParam({ file: relPath(r.path) }); // follow the artifact to its new path
          setReloadKey((k) => k + 1); // the retitle is a server-side write
        }
      } catch (e) {
        setOpError(e instanceof Error ? e.message : 'Rename failed.');
      } finally {
        setRenameBusy(false);
        setRenaming(false);
      }
    },
    [artifactPath, renameBusy, setParam],
  );

  const { verbs: organizeVerbs, modals: organizeModals } = useFileOrganizeVerbs({
    onAfterMutate: (newPath) => {
      setParam({ file: newPath === null ? null : relPath(newPath) });
      // NOTE: no retitle here. These verbs are MOVE and TRASH only — the
      // Studio's rename is `commitRename` (the crumb), which renames the
      // meaning folder and retitles server-side in one act. A move says nothing
      // about what an artifact is called, so nothing to retitle.
    },
  });

  // ── Composer seeding (v1.1): pointing + the insert menu ────────────────
  const [seed, setSeed] = useState<{ text: string; nonce: number } | null>(null);
  const seedComposer = useCallback(
    (text: string) => setSeed((s) => ({ text, nonce: (s?.nonce ?? 0) + 1 })),
    [],
  );
  // ── The selection (ADR-444; slot + page grains ADR-453): held by the
  // surface, it anchors the toolbar's deterministic ops, drives the Design
  // tab's scope, AND informs the lane (via a visible composer seed). ──
  const [selection, setSelection] = useState<StudioSelection | null>(null);

  // Reconcile a stale page selection against the live content: if a slide/page
  // is deleted (on the canvas, via the Design tab, or by a lane write) the
  // selected index can point PAST the end — the navigator ring silently
  // vanishes and every page-scope op resolves `querySelectorAll(...)[i]` to
  // null, so Duplicate/Delete/Re-arrange become no-ops with no feedback. When
  // the count shrinks below the selected index, drop the selection so the
  // grain ladder falls back cleanly rather than pointing at nothing.
  const content = file?.content;
  useEffect(() => {
    setSelection((sel) => {
      if (!sel || (sel.slideIndex == null && sel.pageIndex == null) || !content) return sel;
      const doc = new DOMParser().parseFromString(content, 'text/html');
      const slideCount = doc.querySelectorAll('section.slide').length;
      const pageCount = doc.querySelectorAll('section.slide, [data-arrange]').length;
      const staleSlide = sel.slideIndex != null && sel.slideIndex >= slideCount;
      const stalePage = sel.pageIndex != null && sel.pageIndex >= pageCount;
      return staleSlide || stalePage ? null : sel;
    });
  }, [content]);

  // ADR-453 D4: the right column's two tabs — Chat (the bound lane) | Design
  // (the scope-switching inspector). The lane stays MOUNTED under either tab.
  const [rightTab, setRightTab] = useState<'chat' | 'design'>('chat');

  // F2 (bottom-append fix): the last block the caret touched — the IMPLICIT
  // anchor for a toolbar/slash insert when nothing is explicitly selected. A
  // ref (no re-render): it's an anchor hint, folded into `anchor` below so a
  // no-selection insert lands after where the member last was, not at the END
  // of the document (the "adding happens on the bottom" complaint). Cleared on
  // a genuine deselect (click into empty margin).
  const lastCaretBlockId = useRef<string | null>(null);

  // ADR-446 D5: a click SELECTS (block → slot → page, the ADR-453 grain
  // ladder; anchors ops + gates edit mode). It NO LONGER auto-seeds the
  // composer — that produced the seed-append spam. The lane hears the
  // selection only on the explicit "Ask about this" affordance below.
  const onPoint = useCallback((p: PointerEvent2) => {
    setSelection({
      blockId: p.blockId,
      blockKind: p.blockKind,
      slideIndex: p.slideIndex,
      pageIndex: p.pageIndex,
      slot: p.slot,
      arrange: p.arrange,
      text: p.text,
    });
    if (p.blockId) lastCaretBlockId.current = p.blockId; // remember the anchor
    // ADR-458: the gutter's ⋮⋮ selects AND opens the Design tab (one home).
    if (p.design) setRightTab('design');
  }, []);
  const onPointClear = useCallback(() => {
    setSelection(null);
    setEditingBlockId(null);
    lastCaretBlockId.current = null; // a real deselect drops the implicit anchor
  }, []);

  // ADR-446: which block is being edited in place (surface-held; the canvas
  // commands its iframe runtime). Selecting a different block exits the prior
  // edit (the runtime commits on the enter of the next).
  const [editingBlockId, setEditingBlockId] = useState<string | null>(null);

  // The explicit ask (replaces the auto-seed): the member chose to bring the
  // selection to the lane — one seed, on purpose, in operator words. Lives in
  // the Design tab (ADR-453 D4); it flips back to Chat so the seed is seen.
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
    setRightTab('chat');
  }, [selection, seedComposer]);

  // ── The canvas context menu (ADR-462) ──────────────────────────────────
  // The runtime has already SELECTED the block under the cursor (D7), so this
  // holds only the anchor + the grain. Every row dispatches an op that already
  // exists — a second entrance, never a second write path (D1).
  const [ctxMenu, setCtxMenu] = useState<StudioContextTarget | null>(null);
  // Copy/paste is a BLOCK clipboard, not the OS text one: the unit is a block's
  // source HTML, so a paste can reconstruct it whole (kind + tokens + citations)
  // rather than smearing its text into another block. Session-scoped by design —
  // a cross-artifact block clipboard is a substrate question, not a menu one.
  const blockClip = useRef<string | null>(null);

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

  // The composition seam (kernel-named; see STUDIO_LAYOUT_MODES in
  // services/studio.py). `paged` (deck, page) = the CONTAINER is the unit, so
  // the New-‹noun› gallery and the navigator strip are native. `flow`
  // (document, article) = BLOCKS are the unit and they flow — there is no
  // section to insert, and insert is located at the pointer. The chrome derives
  // from this rather than testing for 'deck', so a new layout declares its mode
  // once in the kernel and the FE never learns another slug.
  //
  // Defaults to 'flow' until the vocabulary lands: the safe direction is the
  // one that shows LESS chrome, so nothing flashes in and back out.
  const layoutMode: 'flow' | 'paged' =
    vocabulary?.layouts.find((l) => l.slug === template)?.mode ?? 'flow';
  const isPaged = layoutMode === 'paged';
  // One payload, two lifetimes — and that was the bug (ADR-462 D12). Blocks /
  // arrangements / tokens are KERNEL CONSTANTS: fetch once, cache forever,
  // correct. `design_systems` is WORKSPACE STATE that changes while the member
  // is looking at it. The `|| vocabulary` guard cached both together, so a
  // design system imported during a session stayed invisible until a full
  // reload — the picker said "No design system in this workspace yet" while
  // the endpoint served one. Re-fetch when the ARTIFACT changes: cheap (one
  // read), and it makes the workspace half honest without a poll.
  useEffect(() => {
    if (!artifactPath) return;
    let live = true;
    api.studio
      .vocabulary()
      .then((v) => {
        if (live) setVocabulary(v);
      })
      .catch(() => {
        /* toolbar menus stay empty — chat authoring unaffected */
      });
    return () => {
      live = false;
    };
  }, [artifactPath]);

  // ── The mechanical executor (ADR-444): compute a deterministic op FE-side,
  // land it as ONE operator-attributed CAS-guarded revision, re-render. ──
  const [opError, setOpError] = useState<string | null>(null);

  // The shared write core: POST the computed html, advance the local CAS base
  // (content + head) so the NEXT write chains off it without a refetch. Returns
  // true on success. `reload` decides whether the iframe re-projects: STRUCTURAL
  // ops (insert/move/delete/arrange — the DOM shape changed) reload so the
  // canvas shows the new shape; TEXT edits do NOT (the member already typed the
  // result into the live DOM — reloading would only blank+reprint it and lose
  // the caret). Either way the override advances, so save is durable + CAS-safe.
  // Writes are SERIALIZED. Two ops can be emitted from one gesture in the same
  // tick (see liveRef); firing them concurrently means both carry the same
  // expected head, so the loser 409s even though nothing foreign happened. The
  // tail chains them: each waits for the previous to land, then computes its
  // html from the previous RESULT via liveRef.
  const writeTail = useRef<Promise<boolean>>(Promise.resolve(true));

  const writeAndAdvance = useCallback(
    (
      compute: (liveHtml: string) => string | null,
      message: string,
      reload: boolean,
    ): Promise<boolean> => {
      if (!artifactPath) return Promise.resolve(false);
      const run = async (): Promise<boolean> => {
        // Pin the chain's anchor to the LOADED head (stable through a typing
        // session). The first edit forks from the loaded head; every subsequent
        // edit keeps that same anchor so the override stays valid (the merge
        // guard in `file`).
        const anchorHead = loadedFile?.head_version_id ?? null;
        // Read the base head FRESH — a previous write in this chain may have
        // advanced it with no render in between. This ref, not a render
        // closure, is what governs the CAS base.
        const live = liveRef.current;
        const baseHead = live ? live.head : null;
        // Recompute against the LIVE content so an op that queued behind
        // another applies to that op's result, not to a stale render.
        const computed = compute(live?.content ?? '');
        if (computed == null) return false; // the op no-ops against live state
        // ADR-453 D2: the kernel element retrofits on first touch. Applied HERE,
        // at the one member write door, rather than op-by-op — only 5 of 21 ops
        // threaded it through, so every other write left an old artifact stale.
        // A no-op when the artifact is already current (byte-identical), so it
        // never turns a no-op edit into a revision.
        const html = retrofitKernel(computed, kernelStyleRef.current);
        try {
          const res = await api.studio.writeArtifact(artifactPath, html, baseHead, message);
          // Advance the CAS base BOTH synchronously (liveRef — the next queued
          // op reads it this tick) and in React state (the invisible-save spine).
          liveRef.current = { content: html, head: res.head_version_id };
          setLocalOverride({ anchorHead, content: html, headVersionId: res.head_version_id });
          if (reload) setReloadKey((k) => k + 1);
          return true;
        } catch (e) {
          // A 409 here is now a genuinely foreign write (the lane / another
          // member) — our own ops can no longer collide with each other.
          setOpError(e instanceof Error ? e.message : 'The edit did not land — reloading.');
          setLocalOverride(null);
          setReloadKey((k) => k + 1);
          return false;
        }
      };
      // Chain, and keep the tail alive even if this link fails.
      const next = writeTail.current.then(run, run);
      writeTail.current = next.catch(() => false);
      return next;
    },
    [artifactPath, loadedFile],
  );

  const applyOp = useCallback(
    async (compute: (html: string) => OpResult | null, message: string) => {
      if (!artifactPath || !file?.content) return;
      setOpError(null);
      // Guard against the CURRENT render so a genuine miss still reports; the
      // real computation re-runs against live state inside the write queue (an
      // op queued behind another must apply to the previous op's result).
      if (!compute(file.content)) {
        setOpError('Could not apply that here — select something in the document first.');
        return;
      }
      // A structural op does NOT reload. The old comment here said it must
      // "reload so the canvas re-projects the new DOM shape" — but the canvas
      // already re-projects on every CONTENT change, and the override carries
      // the new content into `file`. So the reload was redundant, and worse
      // than redundant: the [reloadKey] effect nulls the override, so `file`
      // fell back to the PRE-EDIT content, the canvas re-projected the old
      // shape, and the refetch then re-applied the very bytes we had computed
      // locally a moment earlier. Every insert/move/delete flashed backwards
      // and scrolled to the top — "I don't know if it was reflected."
      //
      // Same contract as a text edit now: compute → write → the override IS
      // the canvas. reloadKey stays for the two cases that genuinely need the
      // authoritative server state — a FOREIGN (lane) write, and a 409.
      await writeAndAdvance(
        (liveHtml) => compute(liveHtml)?.html ?? null,
        message,
        false,
      );
    },
    [artifactPath, file, writeAndAdvance],
  );

  const anchor = useMemo(
    () => ({
      blockId: selection?.blockId ?? null,
      slideIndex: selection?.slideIndex ?? null,
      pageIndex: selection?.pageIndex ?? null,
    }),
    [selection],
  );
  // The INSERT anchor (F2 bottom-append fix): blockId falls back to the last
  // block the caret touched, resolved FRESH at call time (a ref, not a memo —
  // so an Enter-then-Insert flow anchors on the just-created block, never the
  // document end). Only block inserts use this; page/token/arrange ops keep the
  // explicit-selection `anchor` above (an implicit page anchor would surprise).
  const insertAnchor = useCallback(
    () => ({
      blockId: selection?.blockId ?? lastCaretBlockId.current ?? null,
      slideIndex: selection?.slideIndex ?? null,
      pageIndex: selection?.pageIndex ?? null,
    }),
    [selection],
  );
  const kernelStyle = vocabulary?.kernel_style_element;
  // Mirror into the ref the async write queue reads (see kernelStyleRef).
  useEffect(() => {
    kernelStyleRef.current = kernelStyle;
  }, [kernelStyle]);

  const handleInsertBlock = useCallback(
    (fragment: string, label: string) =>
      applyOp((html) => insertBlock(html, fragment, insertAnchor()), `Studio: add ${label} block`),
    [applyOp, insertAnchor],
  );
  const handleInsertCited = useCallback(
    (kind: 'figure' | 'table', path: string, pin?: string | null) => {
      const rel = relPath(path);
      const base = vocabulary?.blocks.find((b) => b.kind === kind)?.fragment;
      if (!base) return;
      // The citation carries its PIN (ADR-440 D5) — the cited file's head
      // revision at the moment of citation. This used to be the lane's job
      // ("stamp it when you have the head revision id... otherwise leave it
      // empty") and so was never done: 0 populated pins across the live
      // workspace. A mechanical insert knows the rev; it stamps it.
      const fragment = base
        .replace(/data-ref="[^"]*"/, `data-ref="${rel}"`)
        .replace(/data-ref-rev="[^"]*"/, `data-ref-rev="${pin ?? ''}"`);
      void applyOp(
        (html) => insertBlock(html, fragment, insertAnchor()),
        `Studio: insert ${kind === 'figure' ? 'image' : 'table'} ${rel}`,
      );
    },
    [applyOp, insertAnchor, vocabulary],
  );
  // ADR-456 W1: N cited images land as ONE gallery block, one revision.
  const handleInsertGallery = useCallback(
    (paths: string[], pins?: Record<string, string | null>) => {
      const base = vocabulary?.blocks.find((b) => b.kind === 'gallery')?.fragment;
      if (!base) return;
      // Pins are keyed by the RELATIVE path the fragment will carry, so the
      // lookup inside galleryFragment matches what it stamps.
      const relPins: Record<string, string | null> = {};
      for (const p of paths) relPins[relPath(p)] = pins?.[p] ?? null;
      const fragment = galleryFragment(base, paths.map(relPath), relPins);
      if (!fragment) return;
      void applyOp(
        (html) => insertBlock(html, fragment, insertAnchor()),
        `Studio: insert gallery (${paths.length} images)`,
      );
    },
    [applyOp, insertAnchor, vocabulary],
  );
  const handleAddArrangement = useCallback(
    (fragment: string, label: string) =>
      applyOp(
        (html) => insertArrangement(html, fragment, anchor),
        `Studio: add ${label}`,
      ),
    [applyOp, anchor],
  );
  const handleApplyArrangement = useCallback(
    (fragment: string, label: string) => {
      // D9: applyArrangement REFUSES rather than deleting when the target has
      // nowhere to put the page's content (title/section-header/closing/hero/
      // cta carry no slot). applyOp's generic miss message would say "select
      // something first", which is wrong and unhelpful — a refusal that
      // protected the member's work should say so in their words.
      if (file?.content && !applyArrangement(file.content, fragment, anchor)) {
        setOpError(
          `"${label}" has no place for this slide's content — move or delete the blocks first, ` +
            `or pick a layout with a content area.`,
        );
        return Promise.resolve();
      }
      return applyOp(
        (html) => applyArrangement(html, fragment, anchor),
        `Studio: change arrangement to ${label}`,
      );
    },
    [applyOp, anchor, file],
  );

  // ── ADR-453: the property layer + the structural verbs (Design tab) ──────
  const handleSetToken = useCallback(
    (grain: 'block' | 'page' | 'document', key: string, value: string | null) =>
      applyOp(
        (html) => setToken(html, { grain, anchor }, key, value),
        value == null ? `Studio: clear ${key}` : `Studio: set ${key} to ${value}`,
      ),
    [applyOp, anchor],
  );
  // ADR-461 D3: the column divider landed on a STOP. It carries its OWN anchor
  // (the page it was dragged on), not the selection's — a divider drag is a
  // located gesture and must not depend on what happens to be selected. `null`
  // clears the token: 1-1 is the even DEFAULT, written by absence, never a
  // third value. The gesture composes setToken; it is not a second write path.
  const handleRatio = useCallback(
    (pageIndex: number, value: string | null) =>
      applyOp(
        (html) => setToken(html, { grain: 'page', anchor: { pageIndex } }, 'ratio', value),
        value == null ? 'Studio: even columns' : `Studio: columns ${value}`,
      ),
    [applyOp],
  );
  // ADR-461 D4: a measured block was resized. The bound comes from the KERNEL's
  // served registry — the FE never invents one (setMeasure clamps again at the
  // write, so a bad message can't author an unbounded value either). Width is
  // the axis members reach for; height stays available to the registry but the
  // corner grip drives w — one gesture, one intent.
  const handleMeasure = useCallback(
    (blockId: string, w: number) => {
      const spec = vocabulary?.measures?.find((m) => m.key === 'w');
      if (!spec) return;
      void applyOp(
        (html) =>
          setMeasure(html, blockId, spec.key, w, {
            cssVar: spec.css_var,
            unit: spec.unit,
            min: spec.min,
            max: spec.max,
          }),
        `Studio: width ${Math.max(spec.min, Math.min(spec.max, Math.round(w)))}${spec.unit}`,
      );
    },
    [applyOp, vocabulary],
  );
  const handleBlockVerb = useCallback(
    (verb: StructVerb) => {
      const id = selection?.blockId;
      if (!id) return;
      if (verb === 'delete') {
        void applyOp((html) => deleteBlock(html, id), `Studio: delete ${id} block`);
        onPointClear();
      } else if (verb === 'duplicate') {
        void applyOp((html) => duplicateBlock(html, id), `Studio: duplicate ${id} block`);
      } else {
        void applyOp((html) => moveBlock(html, id, verb), `Studio: move ${id} block ${verb}`);
      }
    },
    [applyOp, selection, onPointClear],
  );
  // Copy/paste take an explicit id rather than reading ctxMenu, because they
  // have TWO callers: the menu (which knows the right-clicked block) and the
  // keyboard (D10 — which carries the selected block's id in its message). One
  // implementation, two entrances — the same rule the verbs themselves follow.
  const copyBlock = useCallback(
    (id: string | null) => {
      if (!id || !file?.content) return;
      const doc = new DOMParser().parseFromString(file.content, 'text/html');
      const el = doc.querySelector(`[data-block-id="${CSS.escape(id)}"]`);
      if (el) blockClip.current = el.outerHTML;
    },
    [file],
  );

  const pasteAfter = useCallback(
    (after: string | null) => {
      const html = blockClip.current;
      if (!html) return;
      // Through the SAME door as every other insert — a fresh id is stamped so
      // a paste is a new block, never a second element wearing one address.
      void applyOp(
        (src) => pasteBlock(src, html, after),
        `Studio: paste block${after ? ` after ${after}` : ''}`,
      );
    },
    [applyOp],
  );

  const menuCopy = useCallback(() => copyBlock(ctxMenu?.blockId ?? null), [copyBlock, ctxMenu]);
  const menuPaste = useCallback(() => pasteAfter(ctxMenu?.blockId ?? null), [pasteAfter, ctxMenu]);

  // D10: the selected block's keyboard. Every verb already exists — the key is
  // a third entrance (after the menu and the Design tab), never a new op.
  const handleKeyVerb = useCallback(
    (verb: 'copy' | 'paste' | 'duplicate' | 'delete', blockId: string) => {
      if (verb === 'copy') return copyBlock(blockId);
      if (verb === 'paste') return pasteAfter(blockId);
      if (verb === 'duplicate') {
        void applyOp((html) => duplicateBlock(html, blockId), `Studio: duplicate ${blockId} block`);
        return;
      }
      void applyOp((html) => deleteBlock(html, blockId), `Studio: delete ${blockId} block`);
      onPointClear();
    },
    [copyBlock, pasteAfter, applyOp, onPointClear],
  );

  // Turn into / Re-arrange have HOMES already (the Design tab's block + page
  // scopes). The menu row is a doorway to them, not a second implementation —
  // which is exactly ADR-462 D1, and why neither needs new logic here.
  const menuOpenDesign = useCallback(() => setRightTab('design'), []);

  // D6: both AI rows SEED and send nothing. The seeds differ only in how much
  // they pre-fill; the member finishes the sentence and presses enter.
  const menuRewrite = useCallback(() => {
    const t = ctxMenu;
    if (!t) return;
    const kind = t.blockKind ?? 'content';
    const id = t.blockId ? ` (id: ${t.blockId})` : '';
    seedComposer(`Rewrite the ${kind} block${id}${t.text ? ` — "${t.text}"` : ''}: `);
    setRightTab('chat');
  }, [ctxMenu, seedComposer]);

  const menuCheck = useCallback(() => {
    const t = ctxMenu;
    if (!t) return;
    const kind = t.blockKind ?? 'content';
    const id = t.blockId ? ` (id: ${t.blockId})` : '';
    // Trailing "for" on purpose: "check for WHAT" is the member's question to
    // answer, and a complete sentence here would answer it for them.
    seedComposer(`Check the ${kind} block${id}${t.text ? ` — "${t.text}"` : ''} for `);
    setRightTab('chat');
  }, [ctxMenu, seedComposer]);

  // The two rows no reference can ship (D3): a block has a durable address, and
  // the revision chain joins by that same id.
  const menuCopyBlockLink = useCallback(() => {
    const id = ctxMenu?.blockId;
    if (!id || !artifactPath) return;
    const url = `${window.location.origin}/desktop?studio.file=${encodeURIComponent(
      relPath(artifactPath),
    )}&studio.block=${encodeURIComponent(id)}`;
    void navigator.clipboard.writeText(url);
  }, [ctxMenu, artifactPath]);

  const menuHistory = useCallback(() => setRightTab('design'), []);

  const handlePageVerb = useCallback(
    (verb: StructVerb) => {
      const noun = template === 'deck' ? 'slide' : 'section';
      if (verb === 'delete') {
        void applyOp((html) => deletePage(html, anchor), `Studio: delete ${noun}`);
        onPointClear();
      } else if (verb === 'duplicate') {
        void applyOp((html) => duplicatePage(html, anchor), `Studio: duplicate ${noun}`);
      } else {
        void applyOp((html) => movePage(html, anchor, verb), `Studio: move ${noun} ${verb}`);
      }
    },
    [applyOp, anchor, template, onPointClear],
  );
  // The design-system Apply/Remove (ADR-449 D5 homed): resolve the composed
  // MARKED skin element server-side, land it as ONE mechanical revision.
  const handleApplyDesignSystem = useCallback(
    async (manifestPath: string) => {
      const res = await api.studio.resolveDesignSystem(manifestPath);
      await applyOp(
        (html) => applySkin(html, res.skin_element),
        `Studio: apply design system ${res.name}`,
      );
    },
    [applyOp],
  );
  const handleRemoveDesignSystem = useCallback(
    () => void applyOp((html) => removeSkin(html), 'Studio: remove design system'),
    [applyOp],
  );
  // Slot-scoped adds (the Design tab's slot scope + the role-gated add-here).
  const insertProseInSlot = useCallback(
    (slot: string, slideIndex: number | null, pageIndex: number | null) => {
      const proseFragment = vocabulary?.blocks.find((b) => b.kind === 'prose')?.fragment;
      if (!proseFragment) return;
      // "+ Add text" adds TEXT. The prose block's registry markup is
      // `<h2>Heading</h2><p>…</p>` — the right default for the palette (where
      // the member picked "Text" as a section unit) and the wrong one here:
      // clicking an empty slot produced a heading nobody asked for, and it read
      // as the slot "defaulting to a specific format". Strip the heading for
      // the slot-add; the member can Turn into / type one if they want it.
      //
      // The registry is NOT changed — the lane and the palette share that
      // markup, and this is a property of the ADD GESTURE, not of the block.
      const bare = proseFragment.replace(/<h[1-6][^>]*>.*?<\/h[1-6]>/i, '');
      void applyOp(
        (html) => insertBlockInSlot(html, bare, slot, slideIndex, pageIndex),
        `Studio: add text to ${slot}`,
      );
    },
    [applyOp, vocabulary],
  );
  const insertImageInSlot = useCallback(
    (path: string, slot: string, slideIndex: number | null, pageIndex: number | null) => {
      const base = vocabulary?.blocks.find((b) => b.kind === 'figure')?.fragment;
      if (!base) return;
      const rel = relPath(path);
      const fragment = base.replace(/data-ref="[^"]*"/, `data-ref="${rel}"`);
      void applyOp(
        (html) => insertBlockInSlot(html, fragment, slot, slideIndex, pageIndex),
        `Studio: insert image ${rel} into ${slot}`,
      );
    },
    [applyOp, vocabulary],
  );

  // ADR-446: a block edit committed on the canvas (blur/idle) — the newInner is
  // already source-mapped (citation islands restored). Land it through the same
  // mechanical door as every other op; editBlockText no-ops a byte-identical
  // edit (returns null → applyOp surfaces "select something" only on a real
  // miss, so guard the no-op here to stay silent).
  const onEdit = useCallback(
    (blockId: string, newInner: string) => {
      if (!file?.content) return;
      if (!editBlockText(file.content, blockId, newInner)) return; // no-op — no revision
      // INVISIBLE SAVE: the member already typed the result into the live iframe
      // DOM, so this durable revision lands WITHOUT reloading the canvas
      // (reload: false) — no blank flash, no caret jump, no scroll reset.
      void writeAndAdvance(
        (liveHtml) => editBlockText(liveHtml, blockId, newInner)?.html ?? null,
        `Studio: edit ${blockId} block`,
        false,
      );
    },
    [file, writeAndAdvance],
  );

  // F2 — "writing is adding": ENTER at a block's end inserts a fresh empty prose
  // block after it and moves the caret in. We compute the insert locally to get
  // the NEW block's id (insertBlock returns landedId), write it, and set
  // editingBlockId to the new block so the canvas commands edit INTO it — the
  // caret lands in the empty block, ready to type. Enter always anchors on the
  // editing block, so it never hits the end-of-document append path.
  //
  // No reload (see applyOp): the override carries the new block into `file`,
  // the canvas re-projects on that content change, and srcDoc swaps. The caret
  // command races that swap — commandEdit fires on the [editingBlockId] render
  // while the frame still holds the OLD document, so enter() finds no block and
  // no-ops — but onLoad re-commands from editingRef once the new document
  // parses, and that is what lands the caret. (The race is identical under a
  // reload; onLoad has always been the backstop.)
  const onEnterBlock = useCallback(
    (afterBlockId: string) => {
      if (!file?.content) return;
      const proseFragment = vocabulary?.blocks.find((b) => b.kind === 'prose')?.fragment;
      if (!proseFragment) return;
      // Recompute inside the queue so this insert applies to the live source
      // (an Enter can queue behind the blur-commit of the very block it splits
      // from). `landedId` is read from the computed result, not a stale probe.
      let newId: string | null = null;
      void writeAndAdvance(
        (liveHtml) => {
          const r = insertBlock(liveHtml, proseFragment, { blockId: afterBlockId });
          if (!r?.landedId) return null;
          newId = r.landedId;
          return r.html;
        },
        `Studio: add block`,
        false, // the override re-projects; onLoad re-commands the caret
      ).then((ok) => {
        if (ok && newId) {
          setEditingBlockId(newId); // caret into the new block once it projects
          lastCaretBlockId.current = newId; // the new block is now the anchor
        }
      });
    },
    [file, vocabulary, writeAndAdvance],
  );

  // F1 — the ⋮⋮ drag dropped: move `blockId` before `beforeBlockId` (null =
  // end of its parent) as ONE structural revision. moveBlockTo filters a no-op
  // drop (onto itself / already in place) → null → applyOp stays silent.
  const handleReorder = useCallback(
    (blockId: string, beforeBlockId: string | null) => {
      void applyOp(
        (html) => moveBlockTo(html, blockId, beforeBlockId),
        `Studio: move block`,
      );
    },
    [applyOp],
  );

  // F6 — Enter-split / Backspace-merge, the OPTIMISTIC path. The runtime already
  // mutated the live DOM (split the block / merged into the previous) and moved
  // the caret; here we land the matching SOURCE revision WITHOUT a reload
  // (writeAndAdvance reload:false) — the canvas is already correct, so no
  // stutter. The source op uses the SAME newId the runtime generated, so the
  // written source matches the shown DOM exactly. A 409 (a lane wrote under us)
  // falls back to a reload inside writeAndAdvance.
  const handleSplitBlock = useCallback(
    (blockId: string, newId: string, beforeInner: string, afterInner: string) => {
      if (!file?.content) return;
      if (!splitBlock(file.content, blockId, newId, beforeInner, afterInner)) return;
      // If a half carries a CITATION, the optimistic DOM shows it as unresolved
      // SOURCE markup (the runtime put source-inner into the projected DOM) —
      // so re-project (reload:true) to resolve it. Plain-text splits (the common
      // case) stay optimistic (reload:false), no stutter.
      const hasCitation = /data-ref=/.test(beforeInner) || /data-ref=/.test(afterInner);
      void writeAndAdvance(
        (liveHtml) => splitBlock(liveHtml, blockId, newId, beforeInner, afterInner)?.html ?? null,
        `Studio: split block`,
        hasCitation,
      );
    },
    [file, writeAndAdvance],
  );
  const handleMergeBlock = useCallback(
    (blockId: string, prevBlockId: string, mergedInner: string) => {
      if (!file?.content) return;
      if (!mergeBlock(file.content, blockId, prevBlockId, mergedInner)) return;
      const hasCitation = /data-ref=/.test(mergedInner);
      void writeAndAdvance(
        (liveHtml) => mergeBlock(liveHtml, blockId, prevBlockId, mergedInner)?.html ?? null,
        `Studio: merge block`,
        hasCitation,
      );
    },
    [file, writeAndAdvance],
  );

  // ── ADR-456 W2: slash-insert + turn-into ─────────────────────────────────
  // The '/' lands as text and the caret keeps typing — the runtime mirrors the
  // run after it as this palette's filter (the palette has no input of its own;
  // focusing one would end the edit the gesture depends on). The palette renders
  // in the canvas wrapper (the iframe fills it, so frame-viewport coordinates ≈
  // wrapper coordinates, clamped).
  const canvasWrapRef = useRef<HTMLDivElement>(null);
  const [slash, setSlash] = useState<{
    blockId: string;
    empty: boolean;
    left: number;
    top: number;
    filter: string;
    highlight: number;
  } | null>(null);
  // The LAST open run, mirrored into a ref. A pick must survive the close that
  // races it: the runtime's in-frame mousedown fires (capture phase) on the very
  // press that IS the pick, posting yarnnn-slash-close → setSlash(null) before
  // React delivers the click. Reading `slash` from the closure then yields null
  // and the pick is swallowed. The ref is not cleared by the close, so the pick
  // still knows which run it belongs to; the runtime re-validates the run
  // against the live DOM before applying, so a stale ref can't misfire.
  const lastSlashRef = useRef<{ blockId: string; empty: boolean; filter: string } | null>(null);
  useEffect(() => {
    if (slash) lastSlashRef.current = { blockId: slash.blockId, empty: slash.empty, filter: slash.filter };
  }, [slash]);
  // The rows the palette is currently showing — the surface needs them because
  // the DOCUMENT owns the keyboard, so Enter/↑/↓ are handled here, not there.
  const slashItemsRef = useRef<Array<{ kind: string; label: string; fragment: string }>>([]);
  const onSlashItemsChange = useCallback(
    (items: Array<{ kind: string; label: string; fragment: string }>) => {
      slashItemsRef.current = items;
    },
    [],
  );
  const onSlashOpen = useCallback(
    (blockId: string, empty: boolean, rect: { left: number; top: number; bottom: number }) => {
      const wrap = canvasWrapRef.current;
      const maxLeft = Math.max(8, (wrap?.clientWidth ?? 640) - 296);
      const maxTop = Math.max(8, (wrap?.clientHeight ?? 480) - 320);
      setSlash({
        blockId,
        empty,
        left: Math.max(8, Math.min(rect.left, maxLeft)),
        top: Math.max(8, Math.min(rect.bottom + 6, maxTop)),
        filter: '',
        highlight: 0,
      });
    },
    [],
  );
  const onSlashFilter = useCallback((filter: string) => {
    setSlash((s) => (s ? { ...s, filter, highlight: 0 } : s));
  }, []);
  const onSlashClose = useCallback(() => setSlash(null), []);
  const onSlashHighlight = useCallback((i: number) => {
    setSlash((s) => (s ? { ...s, highlight: i } : s));
  }, []);
  const onSlashMove = useCallback((delta: number) => {
    setSlash((s) => {
      if (!s) return s;
      const n = slashItemsRef.current.length;
      if (n === 0) return s;
      return { ...s, highlight: Math.min(Math.max(s.highlight + delta, 0), n - 1) };
    });
  }, []);

  // The pick is a TWO-STEP handshake: tell the runtime to delete the '/'+filter
  // run (only it knows which text node holds it) and hand back the halves around
  // the caret; the op then lands from `onSlashTaken`. The pending pick parks here
  // between the two — one gesture, ONE op (a commit of our own would race it on
  // the same head).
  const pendingPick = useRef<{ kind: string; label: string; fragment: string; empty: boolean } | null>(
    null,
  );
  const [slashTake, setSlashTake] = useState<{ filterLen: number; nonce: number } | null>(null);
  const slashNonce = useRef(0);
  const onSlashPick = useCallback(
    (kind: string, label: string, fragment: string) => {
      // The ref, not the state: the close that races this pick has already
      // nulled `slash` (see lastSlashRef above).
      const s = slash ?? lastSlashRef.current;
      setSlash(null);
      if (!s) return;
      pendingPick.current = { kind, label, fragment, empty: s.empty };
      slashNonce.current += 1;
      setSlashTake({ filterLen: s.filter.length, nonce: slashNonce.current });
    },
    [slash],
  );
  // Enter picks the highlighted row. The runtime intercepted the key (the
  // document owns the caret) and stopped it reaching the Enter-split handler.
  const onSlashEnter = useCallback(() => {
    const s = slash;
    if (!s) return;
    const item = slashItemsRef.current[s.highlight];
    if (item) onSlashPick(item.kind, item.label, item.fragment);
  }, [slash, onSlashPick]);
  const onSlashTaken = useCallback(
    (blockId: string, beforeInner: string | null, afterInner: string | null) => {
      const p = pendingPick.current;
      pendingPick.current = null;
      if (!p) return;
      if (p.kind === 'chart') {
        seedComposer(
          'Create an SVG chart at ./assets/chart.svg, cite it in the document, showing: ',
        );
        return;
      }
      // An empty block CONVERTS in place — the Notion "empty line + /" gesture.
      if (p.empty) {
        void applyOp(
          (html) => convertBlock(html, blockId, p.kind, p.fragment),
          `Studio: turn block into ${p.label}`,
        );
        return;
      }
      // MID-TEXT: split at the '/' and put the new block between the halves, so
      // the sentence the member was writing keeps its tail. When the halves are
      // uncomputable (a citation island) fall back to insert-after — the text is
      // never lost, the block just lands below.
      if (beforeInner !== null && afterInner !== null && afterInner.trim() !== '') {
        void applyOp(
          (html) => splitBlockAndInsert(html, blockId, beforeInner, afterInner, p.fragment),
          `Studio: add ${p.label} block`,
        );
        return;
      }
      void applyOp(
        (html) => insertBlock(html, p.fragment, { blockId }),
        `Studio: add ${p.label} block`,
      );
    },
    [applyOp, seedComposer],
  );
  // ADR-456 W3: the page background — a cited image on the page element.
  const handleSetPageBackground = useCallback(
    (path: string) =>
      applyOp(
        (html) => setPageBackground(html, anchor, relPath(path)),
        `Studio: set page background ${relPath(path)}`,
      ),
    [applyOp, anchor],
  );
  const handleRemovePageBackground = useCallback(
    () => applyOp((html) => removePageBackground(html, anchor), 'Studio: remove page background'),
    [applyOp, anchor],
  );

  // Turn-into from the Design tab (same op, selection-anchored).
  const handleTurnInto = useCallback(
    (kind: string, label: string, fragment: string) => {
      const blockId = selection?.blockId;
      if (!blockId) return;
      void applyOp(
        (html) => convertBlock(html, blockId, kind, fragment),
        `Studio: turn block into ${label}`,
      );
    },
    [applyOp, selection],
  );

  // ADR-447: canvas view controls (view-only, never touch the file) + mobile
  // pane switching (below md, one pane at a time: nav · canvas · chat).
  const [zoom, setZoom] = useState(1);
  const [mobilePane, setMobilePane] = useState<'nav' | 'canvas' | 'chat'>('canvas');

  // ADR-455: the navigator collapses (desktop) — a member reclaims the width
  // when the outline/strip isn't earning it. Session-local state.
  //
  // DEFAULT BY LAYOUT (operator ruling 2026-07-14): a DECK's slide strip is its
  // primary navigation (PowerPoint) → open by default. A DOCUMENT/ARTICLE
  // outline is a thin table-of-contents that doesn't earn its width for the
  // short-to-medium artifacts the Studio actually produces → COLLAPSED by
  // default. The member can still show it (the PanelLeft toggle); once they
  // touch the toggle their choice sticks for the session (`navUserSet`), so the
  // per-layout default never fights a deliberate open/close. This is ADR-455 D4
  // resolving toward "gets out of the way" for documents while the deck keeps
  // its strip — the deletion ADR-455 deferred, taken as a default-hide instead.
  const [navCollapsed, setNavCollapsed] = useState(false);
  const [navUserSet, setNavUserSet] = useState(false);
  useEffect(() => {
    if (navUserSet) return; // the member's choice wins over the per-layout default
    // Gate on the artifact being LOADED: `template` reads 'document' from the
    // extract-fallback before content arrives, so acting on it early would
    // flash a deck's strip closed→open. Only seed the default once the real
    // template is known.
    if (!file?.content) return;
    // PAGED artifacts navigate by container — the strip IS the navigation, so
    // it opens. FLOW artifacts have no navigator at all now (the outline was a
    // derived table of contents that, per the 2026-07-14 ruling, "doesn't earn
    // its width" — an affordance defaulted off was the tell that it didn't
    // belong). Kept collapsed here as belt-and-braces; the toggle + the whole
    // navigator column are mode-gated below.
    setNavCollapsed(!isPaged);
  }, [isPaged, navUserSet, file?.content]);
  const toggleNav = useCallback(() => {
    setNavUserSet(true);
    setNavCollapsed((c) => !c);
  }, []);

  // Selecting a slide in the left navigator sets the selection to that slide
  // (no block; anchors page ops + the Design tab) AND scrolls the canvas to it.
  const [scrollToSlide, setScrollToSlide] = useState<{ index: number; nonce: number } | null>(null);
  const selectSlideFromNavigator = useCallback((index: number) => {
    setSelection({
      blockId: null,
      blockKind: null,
      slideIndex: index,
      pageIndex: null,
      slot: null,
      arrange: null,
      text: '',
    });
    setEditingBlockId(null);
    setScrollToSlide((s) => ({ index, nonce: (s?.nonce ?? 0) + 1 }));
    setMobilePane('canvas'); // on mobile, jump to the canvas to see the slide
  }, []);

  // ADR-455: the outline navigates — selecting a heading selects its BLOCK
  // (anchoring the Design tab) and scrolls the canvas to it (deck parity).
  const [scrollToBlock, setScrollToBlock] = useState<{ blockId: string; nonce: number } | null>(
    null,
  );
  const selectHeadingFromNavigator = useCallback((blockId: string) => {
    setSelection({
      blockId,
      blockKind: 'heading',
      slideIndex: null,
      pageIndex: null,
      slot: null,
      arrange: null,
      text: '',
    });
    setEditingBlockId(null);
    setScrollToBlock((s) => ({ blockId, nonce: (s?.nonce ?? 0) + 1 }));
    setMobilePane('canvas');
  }, []);

  // ── ADR-455: the file-verb completion (surface-bar ⋯) ────────────────────
  // Copy link — the member-facing deep link to this artifact (the workspace
  // is multi-member; distinct from the ADR-437 Share origin).
  const copyArtifactLink = useCallback(() => {
    if (!artifactPath) return;
    const url = `${window.location.origin}/desktop?studio.file=${encodeURIComponent(relPath(artifactPath))}`;
    void navigator.clipboard.writeText(url);
  }, [artifactPath]);
  // Duplicate — read the open artifact, write it at a -copy sibling through
  // the one mechanical door (never overwrite an existing copy), open the copy.
  const duplicateArtifact = useCallback(async () => {
    if (!artifactPath || !file?.content) return;
    const base = artifactPath.replace(/\.html$/, '');
    for (let i = 1; i <= 5; i++) {
      const target = i === 1 ? `${base}-copy.html` : `${base}-copy-${i}.html`;
      try {
        await api.workspace.getFile(target);
        continue; // exists — try the next suffix
      } catch {
        /* free — create here */
      }
      try {
        await api.studio.writeArtifact(
          target,
          file.content,
          null,
          `Studio: duplicate ${baseName(artifactPath)}`,
        );
        setParam({ file: relPath(target) });
      } catch (e) {
        setOpError(e instanceof Error ? e.message : 'Duplicate failed.');
      }
      return;
    }
    setOpError('Too many copies of this artifact already — rename one first.');
  }, [artifactPath, file, setParam]);

  // ADR-447 Phase 4 + ADR-453 D5: "+ Add here" in an empty slot, gated by the
  // slot's ROLE from the vocabulary. A flow slot takes a prose block directly
  // (the member edits it in place or asks the lane to fill it); a media slot
  // takes a CITED image — select the slot and open the Design tab's picker.
  const onAddHere = useCallback(
    (slot: string, slideIndex: number | null, pageIndex: number | null, arrange: string | null) => {
      const role = vocabulary?.arrangements?.[template]
        ?.find((a) => a.slug === arrange)
        ?.slots.find((s) => s.name === slot)?.role;
      if (role === 'media') {
        setSelection({ blockId: null, blockKind: null, slideIndex, pageIndex, slot, arrange, text: '' });
        setEditingBlockId(null);
        setRightTab('design');
        return;
      }
      insertProseInSlot(slot, slideIndex, pageIndex);
    },
    [vocabulary, template, insertProseInSlot],
  );

  // ── START STATE ─────────────────────────────────────────────────────────
  if (!artifactPath) {
    return (
      <StudioStart
        onOpen={(path) => setParam({ file: relPath(path) })}
        onRenameRequest={(path) => {
          setParam({ file: relPath(path) });
          setRenaming(true); // the crumb arms as the workbench mounts
        }}
      />
    );
  }

  // ── WORKBENCH ───────────────────────────────────────────────────────────
  // Desktop (md+): three columns — NAVIGATOR (left) · CANVAS (center, with the
  // Add/Arrange toolbar + zoom control over it) · bound CHAT LANE (right).
  // Mobile (< md): canvas-primary — one pane at a time (nav · canvas · chat)
  // switched by a bottom tab bar; the navigator and chat are drawers over the
  // canvas-first surface (ADR-447 mobile). Freddie's rail is suppressed here.
  const navActive = mobilePane === 'nav';
  const canvasActive = mobilePane === 'canvas';
  const chatActive = mobilePane === 'chat';
  return (
    <div className="relative flex h-full min-h-0 flex-col">
      <div className="flex min-h-0 flex-1">
        {/* Left — the per-type navigator (drawer on mobile). The max-% caps
            (here + the right column) are the anti-collapse guard: with a
            fourth fixed-width sibling beside the workbench (e.g. the steward
            rail when its ADR-454 chrome gate is on), fixed columns can exceed
            the window and crush the flex-1 canvas to 0 — verified live at
            ~960px. Percentages yield gracefully; wide screens are unchanged. */}
        {/* PAGED only: the navigator is container navigation (a slide strip),
            which only exists where the container IS the unit. A flow artifact's
            outline was a derived table of contents wearing a navigator's
            clothes — deleted with the mode split. */}
        {isPaged && (
          <div
            className={`w-full shrink-0 border-r border-border md:w-56 md:max-w-[22%] ${
              navCollapsed ? 'md:hidden' : 'md:flex'
            } ${navActive ? 'flex' : 'hidden'}`}
          >
            <StudioNavigator
              layout={template}
              html={file?.content ?? ''}
              artifactPath={artifactPath}
              selectedSlide={selection?.slideIndex ?? null}
              onSelectSlide={selectSlideFromNavigator}
              onSelectHeading={selectHeadingFromNavigator}
            />
          </div>
        )}

        {/* Center — the toolbar + zoom over the canvas (renders, edits in place). */}
        <div className={`min-w-0 flex-1 flex-col md:flex ${canvasActive ? 'flex' : 'hidden'}`}>
          <div className="flex items-center gap-1 border-b border-border">
            {/* The SELF-RENDERED locator (2026-07-14): the toolbar row carries
                the crumb, so the OS surface bar suppresses (useSelfLocatedSurface
                above) — one "you are here", and the ~28px OS band is reclaimed.
                Root "Studio" → back to the start state (the OS strip's old
                root-click). Shown on mobile too (the toolbar row is visible when
                the Canvas pane is active), so suppressing the OS strip never
                leaves the artifact unnamed. */}
            {/* The navigator toggle sits at the FAR LEFT, on the edge of the
                panel it governs — the macOS/VS Code placement. It was floating
                mid-row after the artifact name, where it read as a third
                crumb-adjacent action rather than as the left panel's handle: a
                control for a panel belongs on that panel's side, not in the
                middle of the row. PAGED only — with no navigator in flow mode,
                the toggle toggles nothing (ADR-455). */}
            {isPaged && (
              <button
                type="button"
                onClick={toggleNav}
                title={`${navCollapsed ? 'Show' : 'Hide'} the slide strip`}
                aria-label={`${navCollapsed ? 'Show' : 'Hide'} the slide strip`}
                className={`ml-2 hidden shrink-0 items-center gap-1 rounded p-1 text-[11px] transition-colors hover:bg-muted/40 md:inline-flex ${
                  navCollapsed ? 'text-muted-foreground/60' : 'text-muted-foreground'
                }`}
              >
                <PanelLeft className="h-3.5 w-3.5" />
              </button>
            )}
            <div className={`flex shrink-0 items-center gap-1 text-xs ${isPaged ? 'ml-1 md:ml-2' : 'ml-2'}`}>
              <button
                type="button"
                onClick={() => setParam({ file: null })}
                title="Back to Studio"
                className="text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
              >
                Studio
              </button>
              <span className="text-muted-foreground/40">/</span>
              {/* The name is renamed WHERE IT IS SHOWN (the Finder/macOS model)
                  — click it and type. It renames the MEANING FOLDER, which is
                  the artifact's actual name; the h1 and the crumb follow. The
                  Design tab's Rename row stays as the discoverable path for
                  members who look for a menu. */}
              {renaming ? (
                <input
                  autoFocus
                  defaultValue={artifactName(artifactPath)}
                  disabled={renameBusy}
                  onBlur={(e) => void commitRename(e.currentTarget.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      void commitRename(e.currentTarget.value);
                    } else if (e.key === 'Escape') {
                      e.preventDefault();
                      setRenaming(false);
                    }
                  }}
                  className="w-[24ch] rounded border border-indigo-400/60 bg-background px-1 py-0.5 text-xs font-medium outline-none disabled:opacity-50"
                  aria-label="Rename this artifact"
                />
              ) : (
                <button
                  type="button"
                  onClick={() => setRenaming(true)}
                  title={`${relPath(artifactPath)} — click to rename`}
                  className="max-w-[24ch] truncate rounded px-1 py-0.5 font-medium text-foreground/80 hover:bg-muted/50"
                >
                  {artifactName(artifactPath)}
                </button>
              )}
              <span className="mx-1 h-4 w-px shrink-0 bg-border/60" aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <StudioToolbar
                vocabulary={vocabulary}
                layout={template}
                isPaged={isPaged}
                onInsertBlock={handleInsertBlock}
                onInsertCited={handleInsertCited}
                onInsertGallery={handleInsertGallery}
                onAddArrangement={handleAddArrangement}
                onSeed={seedComposer}
              />
            </div>
            {/* Zoom — a VIEW control (doesn't touch the file). */}
            <div className="flex shrink-0 items-center gap-0.5 px-2">
              <button
                type="button"
                onClick={() => setZoom((z) => Math.max(0.25, Math.round((z - 0.1) * 100) / 100))}
                className="rounded px-1.5 py-0.5 text-sm text-muted-foreground hover:bg-muted/40"
                title="Zoom out"
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
                onClick={() => setZoom((z) => Math.min(2, Math.round((z + 0.1) * 100) / 100))}
                className="rounded px-1.5 py-0.5 text-sm text-muted-foreground hover:bg-muted/40"
                title="Zoom in"
              >
                +
              </button>
            </div>
          </div>
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
            /* The wrapper is the slash palette's positioning context — the
               iframe fills it, so frame coordinates map onto it directly. */
            <div ref={canvasWrapRef} className="relative flex min-h-0 flex-1">
              <StudioCanvas
                file={file}
                artifactPath={artifactPath}
                onPoint={onPoint}
                onPointClear={onPointClear}
                editingBlockId={editingBlockId}
                onEdit={onEdit}
                onEditExited={() => setEditingBlockId(null)}
                onEditEntered={(id) => {
                  setEditingBlockId(id);
                  lastCaretBlockId.current = id; // entering a block anchors inserts here
                }}
                onEnterBlock={onEnterBlock}
                onReorder={handleReorder}
                onRatio={handleRatio}
                onMeasure={(id, w) => handleMeasure(id, w)}
                onContextMenu={setCtxMenu}
                onKeyVerb={handleKeyVerb}
                onSplitBlock={handleSplitBlock}
                onMergeBlock={handleMergeBlock}
                onAddHere={onAddHere}
                onSlashOpen={onSlashOpen}
                onSlashFilter={onSlashFilter}
                onSlashClose={onSlashClose}
                onSlashMove={onSlashMove}
                onSlashEnter={onSlashEnter}
                onSlashTaken={onSlashTaken}
                slashTake={slashTake}
                scrollToSlide={scrollToSlide}
                scrollToBlock={scrollToBlock}
                zoom={zoom}
              />
              {slash && (
                <StudioSlashPalette
                  vocabulary={vocabulary}
                  filter={slash.filter}
                  left={slash.left}
                  top={slash.top}
                  highlight={slash.highlight}
                  onHighlight={onSlashHighlight}
                  onItemsChange={onSlashItemsChange}
                  onPick={onSlashPick}
                  onClose={onSlashClose}
                />
              )}
              {/* ADR-462: the canvas right-click menu. Fixed-positioned at the
                  page-mapped anchor, so it renders beside the canvas rather
                  than inside the iframe (chrome never enters the artifact). */}
              {ctxMenu && (
                <StudioBlockMenu
                  target={ctxMenu}
                  onClose={() => setCtxMenu(null)}
                  onCopy={menuCopy}
                  onPaste={menuPaste}
                  onDuplicate={() => handleBlockVerb('duplicate')}
                  onDelete={() => handleBlockVerb('delete')}
                  onTurnInto={menuOpenDesign}
                  onRearrange={menuOpenDesign}
                  onMoveUp={() => handleBlockVerb('up')}
                  onMoveDown={() => handleBlockVerb('down')}
                  onRewrite={menuRewrite}
                  onCheck={menuCheck}
                  onCopyLink={menuCopyBlockLink}
                  onHistory={menuHistory}
                />
              )}
            </div>
          )}
        </div>

        {/* Right — Chat | Design tabs (ADR-453 D4, the Canva model — never a
            fourth column). Drawer on mobile. */}
        <div
          className={`w-full shrink-0 flex-col border-l border-border md:flex md:w-[380px] md:max-w-[45%] ${
            chatActive ? 'flex' : 'hidden'
          }`}
        >
          <div className="flex shrink-0 border-b border-border">
            {(
              [
                ['chat', 'Chat'],
                ['design', 'Design'],
              ] as const
            ).map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                onClick={() => setRightTab(tab)}
                className={`flex-1 py-1.5 text-[11px] font-medium transition-colors ${
                  rightTab === tab
                    ? 'border-b-2 border-foreground text-foreground'
                    : 'border-b-2 border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          {/* The lane stays MOUNTED while the Design tab is up (CSS-hidden,
              never unmounted) — a streaming turn survives the tab switch. */}
          <div className={`min-h-0 flex-1 flex-col ${rightTab === 'chat' ? 'flex' : 'hidden'}`}>
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
                suggestions={
                  // ADR-452 D2: a derive-bound lane (the landing's Learn-from
                  // flow) leads with its one job; the template chips follow.
                  boundLane.derive_source
                    ? [
                        `Learn from ${baseName(boundLane.derive_source)} — build this ${template} from it.`,
                        ...(TEMPLATE_SUGGESTIONS[template] ?? TEMPLATE_SUGGESTIONS.document),
                      ]
                    : TEMPLATE_SUGGESTIONS[template] ?? TEMPLATE_SUGGESTIONS.document
                }
              />
            ) : (
              <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                {laneError ?? 'Preparing the authoring lane…'}
              </div>
            )}
          </div>
          {rightTab === 'design' && (
            <StudioDesignTab
              vocabulary={vocabulary}
              layout={template}
              html={file?.content ?? ''}
              selection={selection}
              onSetToken={handleSetToken}
              onApplyArrangement={handleApplyArrangement}
              onBlockVerb={handleBlockVerb}
              onPageVerb={handlePageVerb}
              onTurnInto={handleTurnInto}
              onAskAboutSelection={askAboutSelection}
              onApplyDesignSystem={handleApplyDesignSystem}
              onRemoveDesignSystem={handleRemoveDesignSystem}
              onAddTextInSlot={insertProseInSlot}
              onInsertImageInSlot={insertImageInSlot}
              onSetPageBackground={handleSetPageBackground}
              onRemovePageBackground={handleRemovePageBackground}
              fileVerbs={{
                copyLink: copyArtifactLink,
                duplicate: () => void duplicateArtifact(),
                // Rename focuses the CRUMB rather than opening the shared
                // leaf-rename modal: the artifact's name is its meaning folder,
                // and the crumb is where that name is shown. One rename path,
                // and the menu teaches where the name lives (the Finder model).
                rename: () => setRenaming(true),
                move: () =>
                  organizeVerbs.onMove({ path: artifactPath, name: baseName(artifactPath) }),
                trash: () =>
                  organizeVerbs.onDelete({ path: artifactPath, name: baseName(artifactPath) }),
              }}
            />
          )}
        </div>
      </div>

      {/* Mobile-only bottom tab bar (< md): one pane at a time. */}
      <nav className="flex shrink-0 border-t border-border md:hidden">
        {([
          ['nav', template === 'deck' ? 'Slides' : 'Outline'],
          ['canvas', 'Canvas'],
          ['chat', 'Chat'],
        ] as const).map(([pane, label]) => (
          <button
            key={pane}
            type="button"
            onClick={() => setMobilePane(pane)}
            className={`flex-1 py-2 text-xs font-medium transition-colors ${
              mobilePane === pane
                ? 'border-t-2 border-foreground text-foreground'
                : 'border-t-2 border-transparent text-muted-foreground'
            }`}
          >
            {label}
          </button>
        ))}
      </nav>

      {/* ADR-458 D3: the organize dialogs (rename/move/trash confirmations)
          stay mounted — the entrances moved to the Design tab's File section;
          the surface-bar menu is gone. */}
      {organizeModals}
    </div>
  );
}

// ── The start state — the Studio landing (ADR-452 D1) ────────────────────
// Create (templates) · Learn from a source · Recents with real thumbnails.
// No chat pre-artifact: the lane belongs to an OPEN artifact.

/** The landing's Learn-from targets (ADR-452 D2) — studio-shaped only.
 *  `recipe` names the kernel DERIVE_RECIPES row; `template` the artifact
 *  skeleton (null → the target is a folder, not a canvas → chat lane). */
const LEARN_TARGETS: Array<{
  recipe: string;
  template: 'document' | 'deck' | null;
  label: string;
  description: string;
}> = [
  {
    recipe: 'prd',
    template: 'document',
    label: 'Document',
    description: 'A grounded document (PRD-style) derived from the source.',
  },
  {
    recipe: 'deck',
    template: 'deck',
    label: 'Deck',
    description: 'Slides that argue the source’s claims, evidence cited.',
  },
  {
    recipe: 'design-system',
    template: null,
    label: 'Design system',
    description: 'Tokens-first CSS + manifest your artifacts can wear.',
  },
];

/** A real render of the artifact, scaled down (the ADR-447 navigator
 *  technique): sandboxed srcDoc iframe, display-only. */
function ArtifactThumb({ path }: { path: string }) {
  const [doc, setDoc] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    api.workspace
      .getFile(path)
      .then((f) => !cancelled && setDoc(f.content ?? null))
      .catch(() => !cancelled && setDoc(null));
    return () => {
      cancelled = true;
    };
  }, [path]);
  return (
    <div className="relative aspect-[16/10] overflow-hidden rounded-md border border-border bg-muted/30">
      {doc ? (
        <iframe
          sandbox=""
          srcDoc={doc}
          tabIndex={-1}
          aria-hidden
          title=""
          className="pointer-events-none absolute left-0 top-0 h-[400%] w-[400%] origin-top-left scale-[0.25] border-0 bg-white"
        />
      ) : (
        <div className="flex h-full items-center justify-center">
          <Palette className="h-5 w-5 text-muted-foreground/40" />
        </div>
      )}
    </div>
  );
}

function StudioStart({
  onOpen,
  onRenameRequest,
}: {
  onOpen: (path: string) => void;
  /** Open the artifact AND arm its crumb rename — the landing has no rename
   *  UI of its own, because the name is renamed where the name is shown. */
  onRenameRequest: (path: string) => void;
}) {
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  // Derived from the client's return type — never hand-restated, so a served
  // field (ADR-459's computed `name`/`kind`/`kind_label`) can't drift.
  const [recents, setRecents] = useState<
    Awaited<ReturnType<typeof api.studio.artifacts>>['artifacts']
  >([]);
  const [openPickerOn, setOpenPickerOn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRecents = useCallback(() => {
    api.studio
      .artifacts()
      .then((res) => setRecents(res.artifacts))
      .catch(() => {
        /* recents are a convenience — creation still works without them */
      });
  }, []);

  useEffect(() => {
    api.studio
      .templates()
      .then((res) => setTemplates(res.templates))
      .catch(() => setError('Could not load templates.'));
    loadRecents();
  }, [loadRecents]);

  // ── Organize a recent in place (rename / move / trash) — the SAME shared
  // implementation the Files surface and the open-artifact Design tab use
  // (useFileOrganizeVerbs). A ⋯ / right-click on a recent card reaches the same
  // three verbs against the same backend. After a mutation, reload the recents
  // (a rename re-titles the card; a trash drops it) — the recent is a pointer,
  // not the open artifact, so we never re-point a surface, just refresh.
  const { verbs: organizeVerbs, modals: organizeModals } = useFileOrganizeVerbs({
    onAfterMutate: () => loadRecents(),
  });
  // Copy link / Duplicate are surface-specific extras (ADR-455 extraItems).
  const copyRecentLink = useCallback((path: string) => {
    const url = `${window.location.origin}/desktop?studio.file=${encodeURIComponent(relPath(path))}`;
    void navigator.clipboard.writeText(url);
  }, []);
  const duplicateRecent = useCallback(
    async (path: string) => {
      try {
        const f = await api.workspace.getFile(path);
        const base = path.replace(/\.html$/, '');
        for (let i = 1; i <= 5; i++) {
          const target = i === 1 ? `${base}-copy.html` : `${base}-copy-${i}.html`;
          try {
            await api.workspace.getFile(target);
            continue; // exists — next suffix
          } catch {
            /* free */
          }
          await api.studio.writeArtifact(target, f.content ?? '', null, `Studio: duplicate ${baseName(path)}`);
          loadRecents();
          return;
        }
      } catch {
        /* best-effort — a failed duplicate leaves the recents untouched */
      }
    },
    [loadRecents],
  );

  // The shared right-click / kebab menu (ADR-400 Amendment 1), wired to the
  // organize verbs + the two Studio extras. `openMenu` fires on a card's
  // onContextMenu AND on the hover ⋯ button (both anchor at the click point).
  // Renaming a recent means what it means in the workbench: the artifact's NAME
  // (its meaning folder), never the leaf (a TYPE marker). The shared
  // leaf-rename modal is leaf-bound by contract — it would rename
  // `document.html` to `report.html` and leave the name untouched — and forking
  // it for one caller would give the Studio two rename UIs.
  //
  // So the landing OPENS the artifact and focuses the crumb, which is the one
  // rename affordance. The name is renamed where the name is shown.
  const renameRecent = useCallback(
    (path: string) => onRenameRequest(path),
    [onRenameRequest],
  );

  const { openMenu, menu: recentMenu } = useFileContextMenu(
    {
      onOpen: (t) => onOpen(t.path),
      onRename: (t) => renameRecent(t.path),
      onMove: (t) => organizeVerbs.onMove(t),
      onDelete: (t) => organizeVerbs.onDelete(t),
    },
    (t) => [
      { id: 'copy-link', label: 'Copy link', icon: <Link2 className="h-3.5 w-3.5 text-muted-foreground" />, onClick: () => copyRecentLink(t.path) },
      { id: 'duplicate', label: 'Duplicate', icon: <Copy className="h-3.5 w-3.5 text-muted-foreground" />, onClick: () => void duplicateRecent(t.path) },
    ],
  );

  // ── The two ways to begin (ADR-452 v2): start from scratch, or learn
  // from a source. Both are peers in ONE grid; both nest their details in a
  // focused modal — the landing shows choices and recents, never form fields.
  const [scratchTemplate, setScratchTemplate] = useState<TemplateInfo | null>(null);
  const [learnOpen, setLearnOpen] = useState(false);

  const { navigateToSurface } = useSurfacePreferences();
  // ADR-460 §4b — the landing only needs to know whether lanes RUN. It used to
  // also carry `model: d.models[0]?.id` so `learnFrom` could bind an engine;
  // that was the same array-index accident as the bound-lane create, in two
  // more places. The Agent resolves the engine server-side now.
  const [laneEnv, setLaneEnv] = useState<{ enabled: boolean } | null>(null);
  useEffect(() => {
    api.lanes
      .list()
      .then((d) => setLaneEnv({ enabled: d.enabled }))
      .catch(() => setLaneEnv({ enabled: false }));
  }, []);

  // Scratch creation — invoked by the name-it modal; throws so the modal
  // can show the failure inline.
  const createScratch = async (templateSlug: string, path: string) => {
    const res = await api.studio.createArtifact(path, templateSlug);
    onOpen(res.path);
  };

  // Learn-from creation (ADR-452 D2, source-first) — invoked by the flow
  // modal once BOTH source and target are chosen. A canvas target creates
  // the artifact skeleton + ONE lane carrying both bindings; the
  // design-system target (a folder, no canvas) routes to a chat lane.
  const learnFrom = async (
    source: { path: string; name: string },
    target: (typeof LEARN_TARGETS)[number],
  ) => {
    if (!laneEnv?.enabled) {
      throw new Error('Chat helpers aren’t enabled on this workspace.');
    }
    if (target.template) {
      const sourceSlug = slugify(source.name.replace(/\.[a-z0-9]+$/i, ''));
      const res = await api.studio.createArtifact(
        `operation/${sourceSlug}/${target.template}.html`,
        target.template,
      );
      await api.lanes.create({
        name: `Learn: ${source.name}`.slice(0, 60),
        // A canvas target IS an authoring lane (it carries `artifact_path`), so
        // it gets the same colleague the bound-lane create does.
        agent: 'designer',
        artifact_path: res.path,
        derive_recipe: target.recipe,
        derive_source: source.path,
      });
      setLearnOpen(false);
      onOpen(res.path);
    } else {
      const lane = await api.lanes.create({
        name: `Learn: ${source.name}`.slice(0, 60),
        // The design-system target has NO canvas — it lands in /chat as an
        // ordinary conversation, so it gets an ordinary colleague. Scout is the
        // fast reader, which is what "learn from this source" asks for.
        agent: 'scout',
        derive_recipe: target.recipe,
        derive_source: source.path,
      });
      setLearnOpen(false);
      navigateToSurface('chat', { lane: lane.id });
    }
  };

  const hasRecents = recents.length > 0;
  return (
    <div className="h-full overflow-y-auto p-6 sm:p-8">
      <div className="mx-auto w-full max-w-4xl space-y-6">
        {/* Header row — the title on the left, the ONE create entry on the
            right. The old 5-card grid collapsed into "+ New" (2026-07-14): the
            surface now leads with the member's own work, not a chooser. */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <div className="flex items-center gap-2">
              <Palette className="h-5 w-5 text-muted-foreground" />
              <h1 className="text-lg font-semibold">Studio</h1>
            </div>
            <p className="max-w-md text-sm text-muted-foreground">
              Pick a shape, name it, then describe what you want in plain words —
              it takes shape live, pulling in your files, images, and data as it
              goes.
            </p>
          </div>
          <div className="shrink-0">
            <StudioNewMenu
              templates={templates}
              learnEnabled={laneEnv?.enabled !== false}
              onPickTemplate={(t) => setScratchTemplate(t)}
              onPickLearn={() => setLearnOpen(true)}
            />
          </div>
        </div>

        {/* Recents — the emphasis. Real thumbnails, per-SHAPE icon + label,
            and a ⋯ / right-click menu per card (open · rename · duplicate ·
            move · trash).

            ADR-459: this list is a COMPOSITION (one operator act: reopen my
            work), so it reads like a Mac, not a workbench — the member's own
            name ("IR deck v3", titleized from the meaning folder they typed)
            over the served kind. No path, no `.html`: the format is the
            artifact's storage encoding, not its identity. The Files surface
            (the MIRROR) still shows the raw leaf, and so does the editor
            crumb — an app over one file names the file. */}
        {hasRecents ? (
          <div className="space-y-3">
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Continue where you left off
            </p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {recents.map((r) => {
                const shape = studioShapeStyle(r.kind);
                const ShapeIcon = shape.icon;
                // The organize verbs act on the FILE — they get the raw leaf
                // (Rename pre-fills the real name, the shared Files flow).
                const target = { path: r.path, name: baseName(r.path), isFile: true };
                return (
                  <div
                    key={r.path}
                    className="group relative rounded-lg border border-border p-2 transition-colors hover:bg-muted/20"
                    onContextMenu={(e) => openMenu(target, e)}
                  >
                    <button
                      type="button"
                      onClick={() => onOpen(r.path)}
                      className="block w-full text-left"
                    >
                      <ArtifactThumb path={r.path} />
                      <span className="mt-2 flex items-center gap-1.5">
                        <ShapeIcon className={`h-4 w-4 shrink-0 ${shape.color}`} />
                        <span className="min-w-0 truncate text-sm font-medium">
                          {r.name}
                        </span>
                      </span>
                      {/* The kind carries the accent — it's the answer to "what
                          IS this?", which the thumbnail alone can't give at a
                          glance (a deck and a page both read as "a page of
                          text" at 200px). Date stays quiet beside it. */}
                      <span className="mt-1 block truncate text-[11px]">
                        <span className={`font-medium ${shape.color}`}>{r.kind_label}</span>
                        {r.updated_at ? (
                          <span className="text-muted-foreground">
                            {` · ${new Date(r.updated_at).toLocaleDateString()}`}
                          </span>
                        ) : null}
                      </span>
                    </button>
                    {/* The ⋯ — appears on hover (desktop) / always on touch; opens
                        the SAME menu as right-click, anchored at the click point. */}
                    <button
                      type="button"
                      aria-label={`Actions for ${r.name}`}
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
            <p className="text-sm text-muted-foreground">
              Nothing here yet — hit <span className="font-medium text-foreground/80">New</span>{' '}
              to start your first document, deck, article, or page.
            </p>
          </div>
        )}

        <NewArtifactModal
          template={scratchTemplate}
          onClose={() => setScratchTemplate(null)}
          onCreate={createScratch}
        />

        <LearnFromFlowModal
          open={learnOpen}
          targets={LEARN_TARGETS}
          onClose={() => setLearnOpen(false)}
          onStart={learnFrom}
        />

        {/* Open… — the OS gesture. The member browses their work; they never
            type a raw workspace path (the same refusal ADR-400 Q2 made for
            Move: "move to shouldn't be a URL path input"). */}
        <div className="pt-1">
          <button
            type="button"
            onClick={() => setOpenPickerOn(true)}
            className="inline-flex items-center gap-1.5 rounded-md px-1.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
          >
            <FolderOpen className="h-3.5 w-3.5" />
            Open something else…
          </button>
        </div>

        {error && <p className="text-xs text-red-500">{error}</p>}
      </div>

      {/* The organize dialogs (rename/move/trash) + the shared context menu. */}
      {organizeModals}
      {recentMenu}
      <OpenArtifactModal
        open={openPickerOn}
        onClose={() => setOpenPickerOn(false)}
        onOpen={(p) => {
          setOpenPickerOn(false);
          onOpen(p);
        }}
      />
    </div>
  );
}
