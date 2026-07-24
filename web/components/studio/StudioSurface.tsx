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
import { formatRelativeTime, formatAbsolute } from '@/lib/formatting';
import { ArrowLeft, Copy, FileText, FolderOpen, Link2, Loader2, MoreHorizontal, Palette, PanelLeft, Plus, Upload } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { AUTHORING_APPS } from '@/lib/apps/authoring';
import { useSurfaceParam, useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { LearnFromFlowModal } from './LearnFromFlowModal';
import { NewDesignSystemModal } from './NewDesignSystemModal';
import { NewArtifactModal, slugify } from './NewArtifactModal';
import { registerKindApps } from '@/lib/file-types';
import { StudioNewMenu } from './StudioNewMenu';
import { studioShapeStyle } from './studioShapes';
import { OpenArtifactModal } from './OpenArtifactModal';
import { useFileLoad } from '@/components/workspace/useFileLoad';
import { resolveArtifactHtml } from '@/components/workspace/viewers/projection';
import { useFileContextMenu } from '@/components/workspace/FileContextMenu';
import { useSelfLocatedSurface, useSurfaceActions, useWindowCrumb } from '@/contexts/BreadcrumbContext';
import { useFileOrganizeVerbs } from '@/hooks/useFileOrganizeVerbs';
import { LanePanel } from '@/components/chat-surface/LanePanel';
import { StudioCanvas, type PointerEvent2, type StudioContextTarget } from './StudioCanvas';
import { StudioBlockMenu } from './StudioBlockMenu';
import { StudioCitablePicker, PICKER_KINDS } from './StudioCitablePicker';
import { StudioSlashPalette } from './StudioSlashPalette';
import {
  StudioToolbar,
  type StudioArrangement,
  type StudioSelection,
  type StudioVocabulary,
} from './StudioToolbar';
import { StudioDesignTab, type StructVerb } from './StudioDesignTab';
import { StudioShareExport } from './StudioShareExport';
import { StudioNavigator } from './StudioNavigator';
import {
  applyArrangement,
  applyArrangementMovingContent,
  applyArrangementPlan,
  blocksForPlan,
  applySkin,
  countCarriedBlocks,
  convertBlock,
  deleteBlock,
  deletePage,
  deletePages,
  duplicateBlock,
  pasteBlock,
  duplicatePage,
  editBlockText,
  editFlowRegion,
  galleryFragment,
  insertArrangement,
  insertBlock,
  insertBlockInSlot,
  mergeBlock,
  moveBlock,
  moveBlockTo,
  nudgeZ,
  movePage,
  movePageTo,
  movePages,
  splitBlock,
  splitBlockAndInsert,
  removePageBackground,
  removeSkin,
  retrofitKernel,
  setGeometry,
  setGeometryMany,
  setMeasure,
  setPageBackground,
  setPosition,
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

/** The artifact's name from its PATH — the titleized meaning folder.
 *
 *  `operation/prd-for-yarnnn/document.html` → "Prd for yarnnn". The leaf is a
 *  TYPE marker (document/deck/article/page.html), not a name.
 *
 *  This is the FALLBACK half of `artifact_name` in services/studio.py. It is
 *  lossy by construction — the path is an ASCII identity key (ADR-469), so a
 *  non-Latin name slugs away entirely (`sdㄴ` → `sd`, `한글 문서` → `untitled`).
 *  Never call it directly for a member-facing name; call `artifactNameOf`,
 *  which lifts the title first. */
function artifactNameFromPath(p: string): string {
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

/** The artifact's own `<title>`, exact. Mirrors `extract_title` (ADR-469 D1) —
 *  `set_artifact_title` writes the member's typed name here at creation and at
 *  every rename, for every layout, and nothing else may write it. */
function extractTitle(html: string): string | null {
  const m = /<title>([^<]*)<\/title>/.exec(html || '');
  if (!m) return null;
  // set_artifact_title escapes on the way in; unescape so the round-trip is
  // exact (`&amp;` → `&`), matching the Python's html_unescape.
  const el = typeof document !== 'undefined' ? document.createElement('textarea') : null;
  let text = m[1];
  if (el) {
    el.innerHTML = text;
    text = el.value;
  }
  return text.trim() || null;
}

/** The artifact's operator-facing NAME — LIFTED from the artifact, with the
 *  namespace as fallback. The FE half of ADR-469, completed by ADR-483.
 *
 *  ADR-469 lifted the name into `<title>` and made `services/studio.py::
 *  artifact_name` read it first — but the Studio workbench never migrated, so
 *  the crumb kept deriving from the folder slug alone. That is a LOSSY key: a
 *  member who named a document `sdㄴ` saw the crumb read "Sd", because the
 *  non-Latin character is dropped on the way into the path. The artifact's
 *  title said one thing and the crumb another — the exact "two names for one
 *  thing" ADR-469 set out to end, surviving at its last unmigrated caller.
 *
 *  Same two sources, same order, same placeholder guard as the server:
 *    1. the artifact's own `<title>`, unless it is still a scaffold
 *    2. the titleized meaning folder
 *  `placeholders` comes from the served vocabulary — never re-derived here,
 *  because a deck's scaffold h1 is a thesis, not "Untitled ‹label›". */
function artifactNameOf(p: string, html: string | undefined, placeholders: string[]): string {
  const lifted = extractTitle(html ?? '');
  if (lifted && !placeholders.includes(lifted)) return lifted;
  return artifactNameFromPath(p);
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

/**
 * The authoring-surface app config (ADR-472 D1/D2).
 *
 * Studio and IMAGES are two APPS over one shared authoring machinery: the same
 * bound lane, the same object layer, the same live render. What differs is the
 * surface slug (which param namespace the window manager reads), the templates
 * offered, and the app's own chrome. Parameterizing beats forking 2,500 lines
 * — the dual-approach smell the hooks discipline forbids.
 */
export interface AuthoringApp {
  /** Surface slug — the param namespace (`studio.file` vs `images.file`) AND
   *  the app identity the kernel's type→app association keys on (ADR-473 D2).
   *  Which shapes this app offers and which artifacts are its own are both
   *  DERIVED from that association — never listed here (ADR-473 D3). */
  slug: 'studio' | 'images';
  /** Dimensions-first creation (ADR-472 D3) — a raster artifact is born at a
   *  size. Not derivable from ownership, so it stays an app property. */
  dimensionsFirst?: boolean;
}

export const STUDIO_APP: AuthoringApp = { slug: 'studio' };
export const IMAGES_APP: AuthoringApp = { slug: 'images', dimensionsFirst: true };

export function StudioSurface({ app = STUDIO_APP }: { app?: AuthoringApp } = {}) {
  const { get: getParam, set: setParam } = useSurfaceParam(app.slug);
  const artifactParam = getParam('file');
  const artifactPath = artifactParam
    ? artifactParam.startsWith('/')
      ? artifactParam
      : `/workspace/${artifactParam}`
    : null;
  // DESIGN-SYSTEMS.md §6 — the THIRD render state: manage a design system.
  // Keyed on `studio.system=<manifest-path>`, sibling to `studio.file`. Not the
  // landing, not an artifact workbench.
  const systemParam = getParam('system');
  const systemPath = systemParam
    ? systemParam.startsWith('/')
      ? systemParam
      : `/workspace/${systemParam}`
    : null;

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
  useSurfaceActions(app.slug, []);
  // 2026-07-14 (operator ruling): in the WORKBENCH the toolbar row renders the
  // crumb itself (Studio · ‹artifact›), so the OS strip suppresses — one
  // locator, never two, and the ~28px band is reclaimed for the canvas. The
  // START state keeps the OS strip (it has no toolbar row of its own).
  useSelfLocatedSurface(app.slug, Boolean(artifactPath));

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
        // ADR-467 D1 — the app's declared RESIDENT (Studio→Designer), read
        // from the authoring-app registration rather than a string literal.
        // The lane stays the mind (ADR-440 D3); residency is the creation-time
        // default made legible, and a settle from here attributes to a person.
        agent: AUTHORING_APPS.studio.resident,
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

  // ADR-453 D4: the right column's two tabs — Properties (the scope-switching
  // inspector, 'design' slug) | Chat (the bound lane). The lane stays MOUNTED
  // under either tab. Default is Properties (the 2026-07-19 realignment): Make
  // is this surface's verb (ADR-457), so the artifact's inspector is the resting
  // state; the lane surfaces on demand (a lane seed / "ask about this" flips to
  // Chat — see the setRightTab('chat') calls below).
  const [rightTab, setRightTab] = useState<'chat' | 'design'>('design');

  // (The old F2 "last caret block" implicit-insert anchor is gone with
  // Media ▾ — every insert is now LOCATED: the palette's take handshake
  // carries the exact block, so there is no un-located insert left to anchor.)

  // ADR-446 D5: a click SELECTS (block → slot → page, the ADR-453 grain
  // ladder; anchors ops + gates edit mode). It NO LONGER auto-seeds the
  // composer — that produced the seed-append spam. The lane hears the
  // selection only on the explicit "Ask about this" affordance below.
  const onPoint = useCallback((p: PointerEvent2) => {
    // A click in the CANVAS dismisses the context menu. The menu's own
    // outside-click listener is on the PARENT window, but the canvas is a
    // sandboxed iframe — a click on the artifact fires inside the frame's
    // document, which the parent never hears, so the menu used to hang open
    // (operator, 2026-07-22). The runtime already posts a point on every
    // click; closing here is the signal that actually arrives.
    setCtxMenu(null);
    setSelection({
      blockId: p.blockId,
      blockKind: p.blockKind,
      slideIndex: p.slideIndex,
      pageIndex: p.pageIndex,
      slot: p.slot,
      arrange: p.arrange,
      text: p.text,
    });
    // ADR-458: the gutter's ⋮⋮ selects AND opens the Design tab (one home).
    if (p.design) setRightTab('design');
  }, []);
  const onPointClear = useCallback(() => {
    setCtxMenu(null); // same reason as onPoint — a click on empty canvas
    setSelection(null);
    setEditingBlockId(null);
  }, []);

  // ADR-446: which block is being edited in place (surface-held; the canvas
  // commands its iframe runtime). Selecting a different block exits the prior
  // edit (the runtime commits on the enter of the next).
  const [editingBlockId, setEditingBlockId] = useState<string | null>(null);

  // The explicit ask (replaces the auto-seed): the member chose to bring the
  // selection to the lane — one seed, on purpose, in operator words. Lives in
  // the right-click menu's AI group (relocated 2026-07-24 when the Properties
  // block-verb section was deleted); it flips back to Chat so the seed is seen.
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

  // ── The artifact's NAME (ADR-469's lift, completed FE-side by ADR-483) ────
  // ONE derivation for every surface that shows the name — the crumb, the
  // rename field's starting value, the export filename, the Move/Trash
  // confirmations. Computed here, below `file` + `vocabulary`, because the lift
  // needs both the content (the <title>) and the served placeholder set.
  //
  // Before the placeholders arrive the guard is empty, so a freshly-created
  // artifact reads its scaffold title ("Untitled document") for one beat rather
  // than the folder — the same words either way, and it self-corrects on the
  // vocabulary fetch. Nothing downstream re-derives.
  const artifactDisplayName = useMemo(
    () =>
      artifactPath
        ? artifactNameOf(artifactPath, file?.content, vocabulary?.placeholder_titles ?? [])
        : '',
    [artifactPath, file?.content, vocabulary?.placeholder_titles],
  );

  const commitRename = useCallback(
    async (next: string) => {
      if (!artifactPath || renameBusy) return;
      const trimmed = next.trim();
      // No change / cleared → just close. Never rename to nothing. Compared
      // against the LIFTED name (ADR-483): against the path-derived one, a
      // member who re-confirmed a non-Latin name would submit a "change" that
      // slugs to the identical key and 409s on a rename to itself.
      if (!trimmed || trimmed === artifactDisplayName) {
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
    [artifactPath, renameBusy, setParam, artifactDisplayName],
  );

  // ADR-442 D4: the Studio declares its surface chrome into the surface bar
  // instead of hand-rolling a header row. Identity = the crumb (the strip's
  // root-click fires the leaf onClick → back to the start state, which is
  // what "New / open…" did).
  useWindowCrumb(
    app.slug,
    artifactPath
      ? [
          {
            label: artifactDisplayName,
            kind: 'artifact',
            onClick: () => setParam({ file: null }),
          },
        ]
      : [],
  );

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
  // ADR-480: the RESOLVED mode — undefined until the registry answers. The
  // 'flow' default above is safe for CHROME (show less, flash nothing) but not
  // for the EDITING GRAIN: defaulting a deck to flow would put contenteditable
  // on its root for the first frames and let a whole-region write land against
  // a paged artifact. The canvas therefore receives the mode only once it is
  // genuinely known, and runs the per-block grammar until then.
  const resolvedMode: 'flow' | 'paged' | undefined =
    vocabulary?.layouts.find((l) => l.slug === template)?.mode;
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
        // ADR-473 D3: publish the served type→app association so path-only
        // callers (the Finder's open verb, the Open picker) route correctly.
        registerKindApps(v.layouts);
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
  // ADR-479 D1: a re-arrangement is planned by a judgment before it applies,
  // so the gallery can say it is thinking (the call is ~2-4s).
  const [planning, setPlanning] = useState(false);

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

  // ── Undo / redo (⌘Z / ⌘⇧Z) — a session-local stack of whole-op HTML
  // snapshots. Because the whole document IS one HTML string and block ids are
  // stable within it (artifactOps discipline: ids are never renumbered), a
  // prior state is reconstructed by swapping its string back in — no revision
  // round-trip, no tree diff. `writeAndAdvance` is the single door every op
  // passes through, so it is where snapshots are captured.
  //
  // Model (the ratified choices): whole ops one at a time (text edits already
  // batch to one op on blur); session-scoped, cleared on any FOREIGN write to
  // this file — you cannot undo across a conflict you did not make. An undo is
  // itself a normal op (a full-content replace back through the door), so it is
  // durable + CAS-safe like any other; the flag below just stops it re-pushing
  // its own snapshot and clearing the redo branch it is walking.
  const undoStack = useRef<string[]>([]);
  const redoStack = useRef<string[]>([]);
  const replaying = useRef(false);
  useEffect(() => {
    // A path change or foreign reload starts a fresh history — the same signal
    // that drops the override (below), for the same reason.
    undoStack.current = [];
    redoStack.current = [];
  }, [artifactPath, reloadKey]);

  const writeAndAdvance = useCallback(
    (
      compute: (liveHtml: string) => string | null,
      message: string,
      reload: boolean,
    ): Promise<boolean> => {
      if (!artifactPath) return Promise.resolve(false);
      // ── STAGE 1 — OPTIMISTIC, this tick (ADR-466 P8): pixels never wait for
      // the network. Compute against the live view NOW, paint the override
      // NOW; the durable write queues behind. Before this, the override was
      // set only after the API ack — every reorder/insert/re-arrange sat on a
      // full round-trip before the canvas moved ("performative slow"). The
      // revision is still the atom and the queue still serializes writes; the
      // only thing that changed is that durability stopped gating the pixels.
      const anchorHead = loadedFile?.head_version_id ?? null;
      const live = liveRef.current;
      const computed = compute(live?.content ?? '');
      if (computed == null) return Promise.resolve(false); // no-op against live state
      // Snapshot the PRE-mutation content for undo (a whole op = one entry).
      // Skipped while replaying: an undo/redo must not push its own before-state
      // (that would make ⌘Z a no-op toggle) — replaying manages the stacks
      // itself. A fresh forward edit invalidates the redo branch, as every
      // editor does. Cap the depth so a long session can't grow unbounded.
      if (!replaying.current && live) {
        undoStack.current.push(live.content);
        if (undoStack.current.length > 100) undoStack.current.shift();
        redoStack.current = [];
      }
      // ADR-453 D2: the kernel element retrofits on first touch, at the one
      // member write door. Byte-identical when current — never manufactures a
      // revision on its own.
      const html = retrofitKernel(computed, kernelStyleRef.current);
      // Advance the live CONTENT now (the next op computes off this); the HEAD
      // advances only on ack (the queued write below reads it fresh).
      liveRef.current = { content: html, head: live?.head ?? null };
      setLocalOverride((cur) => ({
        anchorHead,
        content: html,
        headVersionId: cur?.headVersionId ?? live?.head ?? '',
      }));
      if (reload) setReloadKey((k) => k + 1);

      // ── STAGE 2 — DURABILITY, queued: one attributed CAS revision. ──
      const run = async (): Promise<boolean> => {
        // The CAS base is the head the PREVIOUS queued write acked — read
        // inside the queue, never from a render closure.
        const baseHead = liveRef.current?.head ?? null;
        try {
          const res = await api.studio.writeArtifact(artifactPath, html, baseHead, message);
          liveRef.current = liveRef.current
            ? { ...liveRef.current, head: res.head_version_id }
            : { content: html, head: res.head_version_id };
          // Stamp the acked head WITHOUT clobbering a newer optimistic
          // content a queued-behind op may already have painted.
          setLocalOverride((cur) =>
            cur && cur.content === html
              ? { ...cur, headVersionId: res.head_version_id }
              : cur,
          );
          return true;
        } catch (e) {
          // Courteous 409 (ADR-466 D7): a conflict here means a genuinely
          // foreign write (the lane / another member) landed between our base
          // and now. The op is a COMPUTE over content — so fetch the
          // authoritative head and re-apply ONCE on top of it. Typed text and
          // structural intent survive (the member's edit re-lands over the
          // foreign change); only a second conflict, or an op that no longer
          // applies to the fresh content, falls back to the destructive
          // reload. The override keeps its ORIGINAL anchor (loadedFile never
          // refetched), so the merge guard stays valid and nothing flashes.
          const conflict =
            e instanceof APIError ? e.status === 409 : /409|conflict/i.test(String(e));
          if (conflict) {
            try {
              const fresh = await api.workspace.getFile(artifactPath);
              const recomputed = compute(fresh.content ?? '');
              if (recomputed != null) {
                const html2 = retrofitKernel(recomputed, kernelStyleRef.current);
                const res2 = await api.studio.writeArtifact(
                  artifactPath,
                  html2,
                  fresh.head_version_id ?? null,
                  message,
                );
                liveRef.current = { content: html2, head: res2.head_version_id };
                setLocalOverride({ anchorHead, content: html2, headVersionId: res2.head_version_id });
                if (reload) setReloadKey((k) => k + 1);
                return true;
              }
            } catch {
              /* the retry lost too — fall through to the honest reload */
            }
          }
          const detail =
            e instanceof APIError && e.data && typeof e.data === 'object'
              ? (e.data as { detail?: string }).detail
              : null;
          setOpError(
            detail ??
              (e instanceof Error ? e.message : 'The edit did not land — reloading.'),
          );
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

  // ⌘Z — restore the previous snapshot; ⌘⇧Z — re-apply the one just undone.
  // Both replay a captured HTML string through the ONE write door as a full
  // replace, so the restore is a normal CAS-safe revision and the canvas
  // re-projects (reload=true — the DOM shape may have changed). `replaying`
  // stops the door from pushing the replayed before-state back onto the stack.
  const handleUndo = useCallback(() => {
    const prev = undoStack.current.pop();
    if (prev == null) return; // nothing to undo — quiet no-op
    const current = liveRef.current?.content ?? '';
    redoStack.current.push(current);
    replaying.current = true;
    void writeAndAdvance(() => prev, 'Studio: undo', true).finally(() => {
      replaying.current = false;
    });
  }, [writeAndAdvance]);

  const handleRedo = useCallback(() => {
    const nextState = redoStack.current.pop();
    if (nextState == null) return;
    const current = liveRef.current?.content ?? '';
    undoStack.current.push(current);
    replaying.current = true;
    void writeAndAdvance(() => nextState, 'Studio: redo', true).finally(() => {
      replaying.current = false;
    });
  }, [writeAndAdvance]);

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
  const kernelStyle = vocabulary?.kernel_style_element;
  // Mirror into the ref the async write queue reads (see kernelStyleRef).
  useEffect(() => {
    kernelStyleRef.current = kernelStyle;
  }, [kernelStyle]);

  // The cited fragment builders (ADR-440 D5): the citation carries its PIN —
  // the cited file's head revision at the moment of citation. This used to be
  // the lane's job ("stamp it when you have the head revision id… otherwise
  // leave it empty") and so was never done: 0 populated pins across the live
  // workspace. A mechanical insert knows the rev; it stamps it.
  const citedFragment = useCallback(
    (kind: 'figure' | 'table', path: string, pin?: string | null): string | null => {
      const base = vocabulary?.blocks.find((b) => b.kind === kind)?.fragment;
      if (!base) return null;
      const rel = relPath(path);
      return base
        .replace(/data-ref="[^"]*"/, `data-ref="${rel}"`)
        .replace(/data-ref-rev="[^"]*"/, `data-ref-rev="${pin ?? ''}"`);
    },
    [vocabulary],
  );
  // ADR-456 W1: N cited images land as ONE gallery block, one revision. Pins
  // are keyed by the RELATIVE path the fragment will carry, so the lookup
  // inside galleryFragment matches what it stamps.
  const citedGalleryFragment = useCallback(
    (paths: string[], pins?: Record<string, string | null>): string | null => {
      const base = vocabulary?.blocks.find((b) => b.kind === 'gallery')?.fragment;
      if (!base) return null;
      const relPins: Record<string, string | null> = {};
      for (const p of paths) relPins[relPath(p)] = pins?.[p] ?? null;
      return galleryFragment(base, paths.map(relPath), relPins);
    },
    [vocabulary],
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
    async (a: Pick<StudioArrangement, 'fragment' | 'label' | 'slots' | 'slug'>) => {
      // ADR-479 D1 — the PLACEMENT is a judgment; this function is the
      // mechanism around it. Ask where each block belongs, then put it there.
      // A refusal (placements === null: router off, bad JSON, failed
      // validation) falls straight through to the mechanical ladder below —
      // ADR-468 D4, a re-arrangement must never dead-end.
      //
      // Below, unchanged, is that ladder (ADR-466 D5):
      //  · ROLE-AWARE distribution — the target's slot roles ride into the op,
      //    so media blocks seek media slots and flow content never fills one.
      //  · RESOLUTION instead of a dead-end — a slotless arrangement (title /
      //    section-header / closing / hero / cta) applied to a page that holds
      //    content moves that content to a NEW content page right after it
      //    (one compound revision; the galleries forewarn with an inline note).
      //    The old red banner ("has no place for this slide's content") remains
      //    only for the layout with no slotted arrangement at all.
      const slotRoles = Object.fromEntries(a.slots.map((s) => [s.name, s.role]));
      const pageNoun = template === 'deck' ? 'slide' : 'section';

      // The planned path. Only worth a metered call when there is content to
      // place AND somewhere to put it — an empty page or a slotless target is
      // pure mechanism, and paying a judgment for it would be waste.
      if (file?.content && a.slots.length > 0) {
        const blocks = blocksForPlan(file.content, anchor);
        if (blocks && blocks.length > 0) {
          setPlanning(true);
          try {
            const { placements } = await api.studio.planArrangement({
              blocks,
              slots: a.slots.map((s) => ({ name: s.name, role: s.role })),
              arrangement: a.slug,
            });
            if (placements) {
              return await applyOp(
                (html) => applyArrangementPlan(html, a.fragment, anchor, placements),
                `Studio: change arrangement to ${a.label}`,
              );
            }
          } catch {
            /* the planner is unreachable — the mechanical ladder still works */
          } finally {
            setPlanning(false);
          }
        }
      }

      if (file?.content && !applyArrangement(file.content, a.fragment, anchor, slotRoles)) {
        const set = vocabulary?.arrangements?.[template] ?? [];
        const receiver =
          set.find((x) => x.slug === 'content' && x.slots.length > 0) ??
          set.find((x) => x.slots.length > 0);
        if (receiver) {
          return applyOp(
            (html) => applyArrangementMovingContent(html, a.fragment, anchor, receiver.fragment),
            `Studio: change to ${a.label} — content moved to a new ${receiver.label.toLowerCase()} ${pageNoun}`,
          );
        }
        setOpError(
          `"${a.label}" has no place for this ${pageNoun}'s content — move or delete the blocks first.`,
        );
        return Promise.resolve();
      }
      return applyOp(
        (html) => applyArrangement(html, a.fragment, anchor, slotRoles),
        `Studio: change arrangement to ${a.label}`,
      );
    },
    [applyOp, anchor, file, vocabulary, template],
  );

  // ADR-466 D5 — the galleries forewarn: how many blocks would an arrangement
  // change on the anchored page carry? (null → no page anchored yet)
  const carriedCount = useMemo(
    () => (file?.content ? countCarriedBlocks(file.content, anchor) : null),
    [file, anchor],
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
  // ADR-466 P8: a bounding-box gesture landed — any mix of position (body
  // drag) and width (corner handle; a west handle on a positioned block moves
  // origin AND width together) as ONE geometry revision. The bound comes from
  // the KERNEL's served registry — the FE never invents one (setGeometry
  // clamps again at the write, so a bad message can't author an unbounded
  // value either).
  const geometrySpecs = useCallback(() => {
    const sx = vocabulary?.measures?.find((m) => m.key === 'x');
    const sy = vocabulary?.measures?.find((m) => m.key === 'y');
    const sw = vocabulary?.measures?.find((m) => m.key === 'w');
    const sh = vocabulary?.measures?.find((m) => m.key === 'h');
    const sz = vocabulary?.measures?.find((m) => m.key === 'z');
    if (!sx || !sy || !sw) return null;
    const spec = (s: NonNullable<typeof sx>) => ({
      cssVar: s.css_var,
      unit: s.unit,
      min: s.min,
      max: s.max,
    });
    // h and z are optional (ADR-466 P10 / ADR-471 D-d): a vocabulary served
    // before either token simply yields no spec, and those paths no-op.
    return {
      x: spec(sx),
      y: spec(sy),
      w: spec(sw),
      ...(sh ? { h: spec(sh) } : {}),
      ...(sz ? { z: spec(sz) } : {}),
    };
  }, [vocabulary]);
  // ADR-485 D3 — the served bounds, in the shape the projection bakes into the
  // pointer runtime. Same registry `geometrySpecs` reads: ONE source, two
  // consumers (the in-gesture preview clamp and the write clamp), so the box
  // the member releases on is the box that lands. useMemo, not a literal: this
  // is a projection input, and a fresh object every render would re-inject the
  // runtime and reload the frame on every keystroke.
  const measureBounds = useMemo(() => {
    const rows = vocabulary?.measures ?? [];
    if (!rows.length) return undefined;
    const out: Record<string, { min: number; max: number }> = {};
    rows.forEach((m) => {
      out[m.key] = { min: m.min, max: m.max };
    });
    return out;
  }, [vocabulary]);

  const handleGeometry = useCallback(
    (blockId: string, geo: { x?: number; y?: number; w?: number; h?: number }) => {
      const specs = geometrySpecs();
      if (!specs) return;
      // ADR-485 D3 — the receipt states what LANDED, not what was asked for.
      // These parts were built from the raw `geo`, while `setGeometry` clamps
      // to the served bound; a width dragged to 3% therefore wrote a revision
      // message reading "width 3%" over an artifact holding 10%. A receipt is
      // the one surface a member consults to learn what actually happened, so a
      // receipt that misstates the substrate is worse than the visual snap it
      // accompanies. Clamp first, describe second — one helper, same specs the
      // op uses, so the two can never drift apart again.
      const landed = (key: 'x' | 'y' | 'w' | 'h', v: number) => {
        const s = specs[key];
        return s ? Math.round(Math.max(s.min, Math.min(s.max, v))) : Math.round(v);
      };
      const parts = [
        geo.w != null ? `width ${landed('w', geo.w)}%` : null,
        geo.h != null ? `height ${landed('h', geo.h)}%` : null,
        geo.x != null && geo.y != null
          ? `at ${landed('x', geo.x)}%, ${landed('y', geo.y)}%`
          : geo.x != null
            ? `x ${landed('x', geo.x)}%`
            : null,
      ].filter(Boolean);
      void applyOp(
        (html) => setGeometry(html, blockId, geo, specs),
        `Studio: ${blockId} ${parts.join(' ') || 'geometry'}`,
      );
    },
    [applyOp, geometrySpecs],
  );
  // A GROUP drop (2026-07-24) — N blocks, ONE revision. The receipt names the
  // count rather than every id: a group of six would otherwise write a message
  // no one can read, and the ids are in the diff either way.
  const handleGeometryMany = useCallback(
    (moves: Array<{ blockId: string; geo: { x?: number; y?: number; w?: number; h?: number } }>) => {
      const specs = geometrySpecs();
      if (!specs || !moves.length) return;
      // ADR-485 D3 — the receipt states what LANDED. A group resize carries
      // w/h, a group move does not; calling both "moved" would misdescribe the
      // substrate on the one surface a member consults to learn what happened.
      const resized = moves.some((m) => m.geo.w != null || m.geo.h != null);
      void applyOp(
        (html) => setGeometryMany(html, moves, specs),
        `Studio: ${resized ? 'resized' : 'moved'} ${moves.length} blocks together`,
      );
    },
    [applyOp, geometrySpecs],
  );
  // ADR-485 follow-on — clear a single size measure (w or h) from the Properties
  // block scope. The DRAG is the primary authoring path for a measure; this is
  // the read-back's "reset to Auto" affordance, the same absence-default every
  // token offers. Routes through setMeasure(…, null), which strips both halves
  // (data-w + --yw) as one revision — never a second write path.
  const handleClearMeasure = useCallback(
    (key: 'w' | 'h') => {
      const id = selection?.blockId;
      const spec = geometrySpecs();
      const s = key === 'w' ? spec?.w : spec?.h;
      if (!id || !s) return;
      void applyOp(
        (html) => setMeasure(html, id, key, null, s),
        `Studio: clear ${id} ${key === 'w' ? 'width' : 'height'}`,
      );
    },
    [applyOp, selection, geometrySpecs],
  );
  // The escape hatch (Properties block scope): a positioned block returns to
  // the page's flow — both measures cleared, one revision.
  const handleReturnToFlow = useCallback(() => {
    const id = selection?.blockId;
    const specs = geometrySpecs();
    if (!id || !specs) return;
    void applyOp(
      (html) => setPosition(html, id, null, null, { x: specs.x, y: specs.y }),
      `Studio: return ${id} to flow`,
    );
  }, [applyOp, selection, geometrySpecs]);
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
    const url = `${window.location.origin}/desktop?${app.slug}.file=${encodeURIComponent(
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

  // ADR-480 D1/D3: a FLOW edit committed on the canvas (blur/idle). The member
  // wrote on ONE continuous surface, so the runtime reports the whole region's
  // source-mapped inner rather than one block's; `editFlowRegion` swaps it in
  // and runs normalize-on-write, which re-establishes data-block-id identity
  // after the native splits and merges the browser performed.
  //
  // Everything else is deliberately IDENTICAL to onEdit above — the same
  // mechanical door, the same invisible save (reload: false), the same silent
  // no-op guard. ADR-446's write contract is preserved exactly; only the size
  // of the region differs.
  const onFlowEdit = useCallback(
    (selector: string, newInner: string) => {
      if (!file?.content) return;
      if (!editFlowRegion(file.content, selector, newInner)) return; // no-op — no revision
      void writeAndAdvance(
        (liveHtml) => editFlowRegion(liveHtml, selector, newInner)?.html ?? null,
        'Studio: edit document',
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
  const lastSlashRef = useRef<{
    blockId: string;
    empty: boolean;
    filter: string;
    left: number;
    top: number;
  } | null>(null);
  useEffect(() => {
    if (slash)
      lastSlashRef.current = {
        blockId: slash.blockId,
        empty: slash.empty,
        filter: slash.filter,
        left: slash.left,
        top: slash.top,
      };
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
  const pendingPick = useRef<{
    kind: string;
    label: string;
    fragment: string;
    empty: boolean;
    left: number;
    top: number;
  } | null>(null);
  const [slashTake, setSlashTake] = useState<{ filterLen: number; nonce: number } | null>(null);
  const slashNonce = useRef(0);
  const onSlashPick = useCallback(
    (kind: string, label: string, fragment: string) => {
      // The ref, not the state: the close that races this pick has already
      // nulled `slash` (see lastSlashRef above).
      const s = slash ?? lastSlashRef.current;
      setSlash(null);
      if (!s) return;
      pendingPick.current = {
        kind,
        label,
        fragment,
        empty: s.empty,
        left: s.left,
        top: s.top,
      };
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
  // ADR-466 D4 — the located palette hosts the picker: picking Image / Table /
  // Gallery parks the located insertion context here and opens the cited-file
  // picker at the palette's own anchor. The pick then lands a CITED block where
  // the member was pointing (Media ▾ retired with this).
  const [citePicker, setCitePicker] = useState<{
    kind: 'figure' | 'table' | 'gallery';
    left: number;
    top: number;
    ctx: { blockId: string; beforeInner: string | null; afterInner: string | null; empty: boolean };
  } | null>(null);

  // Land a fragment at a LOCATED insertion context (the slash/gutter point):
  // an empty block is replaced (insert-after + delete — one revision; headings
  // are never deleted, they anchor pages); a mid-sentence point splits so the
  // sentence keeps its tail; otherwise the block lands after the anchor.
  const landAtLocatedPoint = useCallback(
    (
      fragment: string,
      label: string,
      ctx: { blockId: string; beforeInner: string | null; afterInner: string | null; empty: boolean },
    ) => {
      const { blockId, beforeInner, afterInner, empty } = ctx;
      if (empty) {
        void applyOp((html) => {
          const inserted = insertBlock(html, fragment, { blockId });
          if (!inserted) return null;
          const anchorKind = new DOMParser()
            .parseFromString(inserted.html, 'text/html')
            .querySelector(`[data-block-id="${CSS.escape(blockId)}"]`)
            ?.getAttribute('data-block');
          if (anchorKind === 'heading') return inserted;
          return deleteBlock(inserted.html, blockId) ?? inserted;
        }, `Studio: insert ${label}`);
        return;
      }
      if (beforeInner !== null && afterInner !== null && afterInner.trim() !== '') {
        void applyOp(
          (html) => splitBlockAndInsert(html, blockId, beforeInner, afterInner, fragment),
          `Studio: insert ${label}`,
        );
        return;
      }
      void applyOp((html) => insertBlock(html, fragment, { blockId }), `Studio: insert ${label}`);
    },
    [applyOp],
  );

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
      if (PICKER_KINDS.has(p.kind)) {
        setCitePicker({
          kind: p.kind as 'figure' | 'table' | 'gallery',
          left: p.left,
          top: p.top,
          ctx: { blockId, beforeInner, afterInner, empty: p.empty },
        });
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

  // The cited-file picker's terminals (ADR-466 D4): a pick builds the cited
  // fragment (pin stamped) and lands it at the parked located point.
  const onCitePickOne = useCallback(
    (path: string, pin: string | null) => {
      const cp = citePicker;
      setCitePicker(null);
      if (!cp) return;
      const kind = cp.kind === 'table' ? 'table' : 'figure';
      const fragment = citedFragment(kind, path, pin);
      if (!fragment) return;
      landAtLocatedPoint(
        fragment,
        `${kind === 'figure' ? 'image' : 'table'} ${relPath(path)}`,
        cp.ctx,
      );
    },
    [citePicker, citedFragment, landAtLocatedPoint],
  );
  const onCitePickGallery = useCallback(
    (paths: string[], pins: Record<string, string | null>) => {
      const cp = citePicker;
      setCitePicker(null);
      if (!cp) return;
      const fragment = citedGalleryFragment(paths, pins);
      if (!fragment) return;
      landAtLocatedPoint(fragment, `gallery (${paths.length} images)`, cp.ctx);
    },
    [citePicker, citedGalleryFragment, landAtLocatedPoint],
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
  const turnBlockInto = useCallback(
    (blockId: string, kind: string, label: string, fragment: string) => {
      void applyOp(
        (html) => convertBlock(html, blockId, kind, fragment),
        `Studio: turn block into ${label}`,
      );
    },
    [applyOp],
  );
  const handleTurnInto = useCallback(
    (kind: string, label: string, fragment: string) => {
      const blockId = selection?.blockId;
      if (!blockId) return;
      turnBlockInto(blockId, kind, label, fragment);
    },
    [turnBlockInto, selection],
  );
  // ADR-479 D5 — the menu's Turn into acts on the RIGHT-CLICKED block, which is
  // not necessarily the selected one (right-click selects, but the op must not
  // depend on that ordering). Same `convertBlock` op, explicit target.
  const menuTurnInto = useCallback(
    (kind: string, label: string, fragment: string) => {
      const blockId = ctxMenu?.blockId;
      if (!blockId) return;
      turnBlockInto(blockId, kind, label, fragment);
    },
    [turnBlockInto, ctxMenu],
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
  // The slide strip is RESIZABLE (drag its right divider). Width persists across
  // sessions so a member's chosen strip stays put. Clamped to a sane band so a
  // drag can neither hide the strip nor crush the canvas.
  const NAV_MIN = 140;
  const NAV_MAX = 520;
  const [navWidth, setNavWidth] = useState(224); // ~w-56, the prior fixed width
  useEffect(() => {
    const saved = Number(localStorage.getItem('studio.navWidth'));
    if (saved >= NAV_MIN && saved <= NAV_MAX) setNavWidth(saved);
  }, []);
  const startNavResize = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      const startX = e.clientX;
      const startW = navWidth;
      const onMove = (ev: PointerEvent) => {
        const w = Math.min(NAV_MAX, Math.max(NAV_MIN, startW + (ev.clientX - startX)));
        setNavWidth(w);
      };
      const onUp = () => {
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
        setNavWidth((w) => {
          localStorage.setItem('studio.navWidth', String(w));
          return w;
        });
      };
      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', onUp);
    },
    [navWidth],
  );
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
  const selectSlideFromNavigator = useCallback(
    (index: number) => {
      // A deck slide keys on slideIndex (section.slide); a page section keys on
      // pageIndex (PAGE_SEL) — the ops resolve different index spaces, so the
      // primary must land in the field the page grain uses. Deck sets both null
      // but slideIndex; page sets pageIndex (the `page` template has no .slide).
      const isDeck = template === 'deck';
      setSelection({
        blockId: null,
        blockKind: null,
        slideIndex: isDeck ? index : null,
        pageIndex: isDeck ? null : index,
        slot: null,
        arrange: null,
        text: '',
      });
      setEditingBlockId(null);
      setScrollToSlide((s) => ({ index, nonce: (s?.nonce ?? 0) + 1 }));
      setMobilePane('canvas'); // on mobile, jump to the canvas to see the slide
    },
    [template],
  );

  // Drag-to-reorder a slide in the navigator (PowerPoint). One mechanical
  // revision through the same write door as every op; the selection follows the
  // slide to its new index so the Design tab stays anchored to it.
  const reorderSlideFromNavigator = useCallback(
    (from: number, to: number) => {
      void applyOp((html) => movePageTo(html, from, to), `Studio: move slide ${from + 1} → ${to + 1}`);
      setSelection((sel) =>
        sel?.slideIndex === from ? { ...sel, slideIndex: to } : sel,
      );
      setScrollToSlide((s) => ({ index: to, nonce: (s?.nonce ?? 0) + 1 }));
    },
    [applyOp],
  );

  // Group reorder (multi-select drag) — move the selection to the drop gap as
  // ONE compound revision (paged-general: deck slides OR page sections).
  //
  // The primary selection MUST be re-anchored, exactly as the single-drag path
  // does. It is not "cleared by the canvas's own reflow": `selection.slideIndex`
  // is an INDEX, and after the group moves that same index names a DIFFERENT
  // page — so the canvas held a slide the member never dragged and the Design
  // tab scoped to it. `landsAt` is where the group's first page ends up; the
  // primary follows the group there and the canvas scrolls to it.
  const reorderPagesFromNavigator = useCallback(
    (indices: number[], to: number, landsAt: number) => {
      const noun = template === 'deck' ? 'slides' : 'sections';
      void applyOp(
        (html) => movePages(html, indices, to),
        `Studio: reorder ${indices.length} ${noun}`,
      );
      setSelection((sel) => {
        if (sel?.slideIndex == null) return sel;
        // The primary was one of the moved pages → it keeps its rank within the
        // group. If it was NOT (a stale primary), re-anchor to the group head
        // rather than leave it pointing at an unrelated page.
        const rank = indices.indexOf(sel.slideIndex);
        return { ...sel, slideIndex: rank >= 0 ? landsAt + rank : landsAt };
      });
      setScrollToSlide((s) => ({ index: landsAt, nonce: (s?.nonce ?? 0) + 1 }));
    },
    [applyOp, template],
  );

  // Multi-delete from the navigator — delete the selection as ONE compound
  // revision. The confirmation (for >1) lives in the navigator; this is the act.
  const deletePagesFromNavigator = useCallback(
    (indices: number[]) => {
      const noun = template === 'deck' ? 'slides' : 'sections';
      void applyOp(
        (html) => deletePages(html, indices),
        `Studio: delete ${indices.length} ${noun}`,
      );
      onPointClear();
    },
    [applyOp, template, onPointClear],
  );

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
    const url = `${window.location.origin}/desktop?${app.slug}.file=${encodeURIComponent(relPath(artifactPath))}`;
    void navigator.clipboard.writeText(url);
  }, [artifactPath]);
  // Share — mint a /s/{token} grant link for THIS artifact and copy it
  // (ADR-437 D4 / ADR-465). Unlike copyArtifactLink (the in-app member
  // deep-link), the recipient becomes a broad member of the commons on accept.
  // Throws on failure so the Properties tab's Share button surfaces the error.
  const shareArtifact = useCallback(async () => {
    if (!artifactPath) throw new Error('No artifact open');
    const res = await api.workspace.createShare(relPath(artifactPath));
    if (!res.share_link) throw new Error('No share link returned');
    // Clipboard may be denied in a non-secure context; the link still exists
    // (listed under Files/Shares), so a copy failure is not a share failure.
    try {
      await navigator.clipboard.writeText(res.share_link);
    } catch {
      /* link minted; copy denied — the caller still reports success */
    }
  }, [artifactPath]);

  // ── Export (ADR-466 D6) ────────────────────────────────────────────────
  // An export is a PROJECTION (ADR-417 — no owned render engine): the resolved
  // artifact plus a print stylesheet, handed to the browser's print-to-PDF. A
  // deck prints one slide per landscape page; a flow layout paginates. The
  // frame is NOT sandboxed (print needs contentWindow) — safe because the
  // projection has already stripped every artifact-authored executable.
  const exportPrint = useCallback(async () => {
    if (!file?.content || !artifactPath) return;
    const projected = await resolveArtifactHtml(file.content, artifactPath, {});
    const printCss =
      template === 'deck'
        ? `@media print {
             @page { size: 330mm 186mm; margin: 0; }
             body { margin: 0; background: #fff; }
             section.slide { break-after: page; page-break-after: always;
               width: 100% !important; margin: 0 !important; box-shadow: none !important; }
           }`
        : `@media print { @page { size: A4; margin: 18mm; } body { background: #fff; } }`;
    const html = projected.includes('</head>')
      ? projected.replace('</head>', `<style>${printCss}</style></head>`)
      : `<style>${printCss}</style>${projected}`;
    const frame = document.createElement('iframe');
    frame.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;';
    frame.srcdoc = html;
    frame.onload = () => {
      try {
        frame.contentWindow?.focus();
        frame.contentWindow?.print();
      } finally {
        // Long grace: the print dialog blocks in some browsers, not others.
        setTimeout(() => frame.remove(), 60_000);
      }
    };
    document.body.appendChild(frame);
  }, [file, artifactPath, template]);

  // ── Raster export (ADR-475 §13) — IMAGES only ───────────────────────────
  // The IMAGES stage's raster is the point of the app; a Studio deck/document
  // keeps Print/PDF (a raster of a document is a fuzzier need). The member's
  // browser rasterizes the projection it already shows; provenance stays in the
  // composition (`trace`), the PNG is the convenience artifact for the outside
  // world. Throws on failure so the Export tab's button surfaces the error.
  const exportPng = useCallback(async () => {
    if (!file?.content || !artifactPath) throw new Error('No artifact open');
    const { exportArtifactPng } = await import(
      '@/components/workspace/viewers/rasterExport'
    );
    await exportArtifactPng(file.content, artifactPath, artifactDisplayName);
  }, [file, artifactPath]);

  // The AI-native reference (the interop face, ADR-368/310): a handle any
  // connected LLM can use to reach this artifact through the yarnnn MCP
  // connector — complementing the /s/{token} membership link (ADR-465).
  const copyAiReference = useCallback(async () => {
    if (!artifactPath) throw new Error('No artifact open');
    const rel = relPath(artifactPath);
    const name = artifactDisplayName;
    await navigator.clipboard.writeText(
      `"${name}" — a yarnnn artifact at ${rel}. ` +
        `With the yarnnn connector (MCP), recall "${name}" to read it — ` +
        `trace shows who changed it and when.`,
    );
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

  // ── MANAGE STATE (DESIGN-SYSTEMS.md §6) ─────────────────────────────────
  // The third render state — a design system opened for management. Checked
  // BEFORE the landing so `studio.system` wins on its own. Step 1 is a minimal
  // panel (name · files · worn-by · Re-import); step 2 makes the dependents
  // openable and adds the theme panel + the token-editor slot.
  if (systemPath) {
    return (
      <StudioManage
        manifestPath={systemPath}
        onBack={() => setParam({ system: null })}
        onOpenArtifact={(path) => setParam({ system: null, file: relPath(path) })}
      />
    );
  }

  // ── START STATE ─────────────────────────────────────────────────────────
  if (!artifactPath) {
    return (
      <StudioStart
        onOpen={(path) => setParam({ file: relPath(path) })}
        onOpenSystem={(manifestPath) => setParam({ system: relPath(manifestPath) })}
        onRenameRequest={(path) => {
          setParam({ file: relPath(path) });
          setRenaming(true); // the crumb arms as the workbench mounts
        }}
        app={app}
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
            className={`relative shrink-0 flex-col border-r border-border max-md:!w-full ${
              navCollapsed ? 'md:hidden' : 'md:flex'
            } ${navActive ? 'flex w-full' : 'hidden'}`}
            style={{ width: navWidth }}
          >
            <StudioNavigator
              layout={template}
              isPaged={isPaged}
              html={file?.content ?? ''}
              artifactPath={artifactPath}
              selectedSlide={
                template === 'deck'
                  ? (selection?.slideIndex ?? null)
                  : (selection?.pageIndex ?? null)
              }
              onSelectSlide={selectSlideFromNavigator}
              onReorderSlide={reorderSlideFromNavigator}
              onReorderPages={reorderPagesFromNavigator}
              onDeletePages={deletePagesFromNavigator}
              onSelectHeading={selectHeadingFromNavigator}
            />
            {/* The resize divider — drag to set the strip width (persisted). A
                hair-wide hit target over the right border; md+ only (on mobile
                the strip is a full-pane view, nothing to resize against). */}
            <div
              onPointerDown={startNavResize}
              title="Drag to resize the slide strip"
              className="absolute right-0 top-0 z-10 hidden h-full w-1.5 translate-x-1/2 cursor-col-resize hover:bg-indigo-400/40 md:block"
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
                {/* ADR-482 D7: app-aware, matching the landing (:2762). The
                    workbench hardcoded the literal, so the IMAGES app read
                    "Images" on its landing and "Studio /…" once a stage was
                    open — the same app naming itself two ways. */}
                {app.slug === 'images' ? 'Images' : 'Studio'}
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
                  // SELECT, don't just focus (browser-tested 2026-07-20).
                  // `autoFocus` alone leaves the caret at the end, so a member
                  // typing into a freshly-created "Untitled document" got
                  // "Untitled documentMy name". That is the ADR-470 D1
                  // distinction failing in practice: an armed name is only an
                  // OFFER if typing REPLACES it. Finder selects the name on a
                  // new folder for exactly this reason.
                  onFocus={(e) => e.currentTarget.select()}
                  defaultValue={artifactDisplayName}
                  disabled={renameBusy}
                  onBlur={(e) => void commitRename(e.currentTarget.value)}
                  onKeyDown={(e) => {
                    // ADR-483 — an IME COMPOSITION owns Enter first. Typing
                    // Korean/Japanese/Chinese, the first Enter commits the
                    // SYLLABLE, not the field: `isComposing` is true and the
                    // buffer still holds a half-formed jamo. Without this guard
                    // the rename snatched that fragment and committed it —
                    // browser-observed as `sdㄴ`, which then slugged to `sd`
                    // (the non-Latin character drops on the way into the path
                    // key), so the crumb read "Sd" and the rename looked like
                    // it had silently done nothing. The member gets a second
                    // Enter once the syllable is assembled, which is exactly
                    // the interaction every native text field gives them.
                    if (e.nativeEvent.isComposing) return;
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
                  className="flex max-w-[26ch] items-center gap-1.5 truncate rounded px-1 py-0.5 font-medium text-foreground/80 hover:bg-muted/50"
                >
                  {/* ADR-482 D7: the document-type glyph. The registry already
                      existed (studioShapes) with three consumers — the landing
                      recents, the New menu, the Open picker — and the crumb,
                      the one place a member reads WHILE working, was the only
                      surface without it. `template` is the served slug, so an
                      unknown layout degrades to a neutral glyph rather than a
                      wrong one. Presentation only; the name stays the name. */}
                  {(() => {
                    const { icon: ShapeIcon, color } = studioShapeStyle(template);
                    return <ShapeIcon className={`h-3.5 w-3.5 shrink-0 ${color}`} aria-hidden />;
                  })()}
                  <span className="truncate">{artifactDisplayName}</span>
                </button>
              )}
              <span className="mx-1 h-4 w-px shrink-0 bg-border/60" aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <StudioToolbar
                vocabulary={vocabulary}
                layout={template}
                isPaged={isPaged}
                onAddArrangement={handleAddArrangement}
                onApplyArrangement={handleApplyArrangement}
                planning={planning}
                carriedCount={carriedCount}
                currentArrange={selection?.arrange ?? null}
                hasPageAnchor={
                  !!selection &&
                  (selection.blockId != null ||
                    selection.slideIndex != null ||
                    selection.pageIndex != null)
                }
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
            {/* The boundary acts (2026-07-24) — Share/Export left the
                Properties pane for the header, right of zoom: document-global
                verbs with their own anchored panels (the StudioToolbar popover
                grammar). The Properties sections are deleted, not mirrored. */}
            <StudioShareExport
              share={shareArtifact}
              print={() => void exportPrint()}
              copyAiRef={copyAiReference}
              exportPng={app.slug === 'images' ? exportPng : undefined}
            />
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
                selectedBlockId={selection?.blockId ?? null}
                onEdit={onEdit}
                mode={resolvedMode}
                measureBounds={measureBounds}
                onFlowEdit={onFlowEdit}
                onEditExited={() => setEditingBlockId(null)}
                onEditEntered={(id) => setEditingBlockId(id)}
                onEnterBlock={onEnterBlock}
                onReorder={handleReorder}
                onRatio={handleRatio}
                onGeometry={handleGeometry}
                onGeometryMany={handleGeometryMany}
                onContextMenu={setCtxMenu}
                onKeyVerb={handleKeyVerb}
                onUndo={handleUndo}
                onRedo={handleRedo}
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
              {/* ADR-466 D4: the cited-file picker the palette opens for the
                  picker-backed kinds — anchored at the palette's own point, so
                  the cited block lands where the member was pointing. */}
              {citePicker && (
                <StudioCitablePicker
                  kind={citePicker.kind}
                  left={citePicker.left}
                  top={citePicker.top}
                  onPickOne={onCitePickOne}
                  onPickGallery={onCitePickGallery}
                  onClose={() => setCitePicker(null)}
                />
              )}
              {/* ADR-462: the canvas right-click menu. Fixed-positioned at the
                  page-mapped anchor, so it renders beside the canvas rather
                  than inside the iframe (chrome never enters the artifact). */}
              {ctxMenu && (
                <StudioBlockMenu
                  target={ctxMenu}
                  // ADR-482 D5: the RESOLVED mode, same source the canvas reads
                  // — the menu withholds enclosure verbs until the registry
                  // answers rather than guessing them on.
                  mode={resolvedMode}
                  // ADR-482 D9: read at menu-open (the ctxMenu state change IS
                  // the render), so the ref's non-reactivity is not a problem —
                  // the clipboard cannot change while the menu is on screen.
                  hasClipboard={!!blockClip.current}
                  onClose={() => setCtxMenu(null)}
                  onCopy={menuCopy}
                  onPaste={menuPaste}
                  onDuplicate={() => handleBlockVerb('duplicate')}
                  onDelete={() => handleBlockVerb('delete')}
                  onTurnInto={menuTurnInto}
                  blocks={vocabulary?.blocks}
                  onMoveUp={() => handleBlockVerb('up')}
                  onMoveDown={() => handleBlockVerb('down')}
                  onBringForward={() => {
                    // ADR-471 D-d — z among positioned blocks; the spec comes
                    // SERVED (geometrySpecs), never invented FE-side.
                    const id = ctxMenu?.blockId;
                    const gz = geometrySpecs()?.z;
                    if (id && gz)
                      void applyOp((html) => nudgeZ(html, id, +1, gz), `Studio: bring ${id} forward`);
                  }}
                  onBringBackward={() => {
                    const id = ctxMenu?.blockId;
                    const gz = geometrySpecs()?.z;
                    if (id && gz)
                      void applyOp((html) => nudgeZ(html, id, -1, gz), `Studio: bring ${id} backward`);
                  }}
                  onRewrite={menuRewrite}
                  onCheck={menuCheck}
                  // The open question, relocated from the deleted Properties
                  // block-verb section (2026-07-24) — same seed, same flip to
                  // Chat; the menu is its only mount now.
                  onAsk={askAboutSelection}
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
                // ADR-453 D4 + the 2026-07-19 realignment: Make is the verb of
                // this surface (ADR-457) — the artifact is the object of work and
                // Properties is its resting inspector; Chat (the bound lane) is the
                // on-demand helper. Properties leads; the label reads Properties
                // (the scope-switching inspector + settings home, ADR-455/458), the
                // internal 'design' slug is unchanged (relabel-keep-slug).
                ['design', 'Properties'],
                ['chat', 'Chat'],
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
              onPageVerb={handlePageVerb}
              onTurnInto={handleTurnInto}
              onReturnToFlow={handleReturnToFlow}
              measures={vocabulary?.measures ?? []}
              onClearMeasure={handleClearMeasure}
              onApplyDesignSystem={handleApplyDesignSystem}
              onRemoveDesignSystem={handleRemoveDesignSystem}
              onAddTextInSlot={insertProseInSlot}
              onInsertImageInSlot={insertImageInSlot}
              onSetPageBackground={handleSetPageBackground}
              onRemovePageBackground={handleRemovePageBackground}
              fileVerbs={{
                copyLink: copyArtifactLink,
                duplicate: () => void duplicateArtifact(),
                move: () =>
                  organizeVerbs.onMove({ path: artifactPath, name: artifactDisplayName }),
                trash: () =>
                  organizeVerbs.onDelete({ path: artifactPath, name: artifactDisplayName }),
              }}
              // The File card renames IN PLACE (double-click the name) through
              // the SAME commit the crumb uses — one derivation (ADR-483), one
              // write path, two entry fields (the Finder: sidebar + Get Info).
              artifactName={artifactDisplayName}
              onRenameCommit={commitRename}
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
  onOpenSystem,
  onRenameRequest,
  app,
}: {
  onOpen: (path: string) => void;
  /** Open a design system's manage state (DESIGN-SYSTEMS.md §6 — the third
   *  render state, keyed on studio.system=). */
  onOpenSystem: (manifestPath: string) => void;
  /** Open the artifact AND arm its crumb rename — the landing has no rename
   *  UI of its own, because the name is renamed where the name is shown. */
  onRenameRequest: (path: string) => void;
  /** ADR-472: which app is landing — filters templates + names the surface. */
  app: AuthoringApp;
}) {
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  // Derived from the client's return type — never hand-restated, so a served
  // field (ADR-459's computed `name`/`kind`/`kind_label`) can't drift.
  const [recents, setRecents] = useState<
    Awaited<ReturnType<typeof api.studio.artifacts>>['artifacts']
  >([]);
  // DESIGN-SYSTEMS.md §6 — the workspace's design systems (first-order on the
  // landing). Fetched via the vocabulary (already carries `design_systems`);
  // worn-by counts are enriched per-system after the list lands.
  const [systems, setSystems] = useState<
    Awaited<ReturnType<typeof api.studio.vocabulary>>['design_systems']
  >([]);
  const [wornBy, setWornBy] = useState<Record<string, number>>({});
  const [openPickerOn, setOpenPickerOn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRecents = useCallback(() => {
    api.studio
      // ADR-473 D4: an app's landing shows the artifacts it OWNS. Scoped in
      // the QUERY, not sieved client-side — correct at 10,000 artifacts.
      .artifacts(app.slug)
      .then((res) => setRecents(res.artifacts))
      .catch(() => {
        /* recents are a convenience — creation still works without them */
      });
  }, [app.slug]);

  // DESIGN-SYSTEMS.md §6 — load the workspace's design systems + enrich each
  // with its worn-by count (the ADR-448 edge on the manifest). Best-effort:
  // the section just stays empty if discovery fails.
  const loadSystems = useCallback(() => {
    api.studio
      .vocabulary()
      .then((v) => {
        registerKindApps(v.layouts);  // ADR-473 D3 (see the workbench fetch)
        setSystems(v.design_systems);
        for (const s of v.design_systems) {
          api.documents
            .dependents(s.manifest_path)
            .then((d) => setWornBy((w) => ({ ...w, [s.manifest_path]: d.count })))
            .catch(() => {
              /* a missing count is shown as '—', never an error */
            });
        }
      })
      .catch(() => {
        /* design systems are additive — the rest of the landing still works */
      });
  }, []);

  useEffect(() => {
    api.studio
      .templates()
      // ADR-473 D3: ownership is SERVED (`t.app`), never restated here. This
      // replaces ADR-472's hardcoded slug lists — no FE file holds a list of
      // "which types are Studio's", so a program-shipped type routes with no
      // frontend deploy.
      .then((res) => setTemplates(res.templates.filter((t) => t.app === app.slug)))
      .catch(() => setError('Could not load templates.'));
    loadRecents();
    loadSystems();
  }, [loadRecents, loadSystems, app]);

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
    const url = `${window.location.origin}/desktop?${app.slug}.file=${encodeURIComponent(relPath(path))}`;
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
  // The DELIBERATE door's modal (ADR-470): open (true) = choose shape + name +
  // destination there. The IMMEDIATE door doesn't pass through here at all.
  const [namingOpen, setNamingOpen] = useState(false);
  const [learnOpen, setLearnOpen] = useState(false);
  // DESIGN-SYSTEMS.md §6 (the 2026-07-19 regroup) — creating a design system is
  // ONE intent through ONE dedicated modal (NewDesignSystemModal), not two
  // landing buttons routing to a blind file picker + the generic learn-from
  // flow. The modal owns the import-vs-derive choice + the source guardrails;
  // the section just opens it. On a successful import it refreshes the list;
  // derive navigates to the lane (see the handlers below).
  const [newSystemOpen, setNewSystemOpen] = useState(false);

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

  // ── The two doors into a new artifact (ADR-470) ────────────────────────
  // IMMEDIATE: New hands over the workbench. No name, no destination — the
  // server places it, the skeleton's "Untitled ‹kind›" stands, and the crumb
  // arms so the name is OFFERED. This is the door a doc processor gives you.
  const createUntitled = async (templateSlug: string) => {
    const res = await api.studio.createArtifact(templateSlug);
    onRenameRequest(res.path); // opens the workbench with the crumb armed
  };

  // DELIBERATE: the member arrived knowing ("IR deck v3, in clients/"). The
  // name-it modal owns this; it throws so the failure shows inline there.
  // `name` travels beside the slugified path so the <title> gets what they
  // actually typed (ADR-469).
  const createScratch = async (
    templateSlug: string,
    path: string,
    name?: string,
    dims?: { width: number; height: number },
  ) => {
    // ADR-472 D3: a stage is born at its real size; a document ignores dims.
    const res = await api.studio.createArtifact(templateSlug, { path, name, ...(dims ?? {}) });
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
      // Deliberate placement: a learn-from artifact is named after its SOURCE,
      // which is a real name the member chose (by picking that source) — so it
      // takes the named door, not the untitled one.
      const sourceName = source.name.replace(/\.[a-z0-9]+$/i, '');
      const res = await api.studio.createArtifact(target.template, {
        path: `operation/${slugify(sourceName)}/${target.template}.html`,
        name: sourceName,
      });
      await api.lanes.create({
        name: `Learn: ${source.name}`.slice(0, 60),
        // A canvas target IS an authoring lane (it carries `artifact_path`), so
        // it gets the app's same declared resident (ADR-467 D1).
        agent: AUTHORING_APPS.studio.resident,
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

  // DESIGN-SYSTEMS.md §6 — the two terminal actions the NewDesignSystemModal
  // calls. IMPORT writes the folder (the modal shows the receipt; we refresh the
  // list). DERIVE creates the design-system lane (same shape learnFrom uses for
  // the no-template target) and navigates to chat — the modal just closes.
  const importNewSystem = async (file: File) => {
    const r = await api.studio.importDesignSystem(file);
    loadSystems();
    return { name: r.name, written: r.written.length, warnings: r.warnings?.length ?? 0 };
  };
  const deriveNewSystem = async (source: { path: string; name: string }) => {
    const lane = await api.lanes.create({
      name: `Design system: ${source.name}`.slice(0, 60),
      agent: 'scout',
      derive_recipe: 'design-system',
      derive_source: source.path,
    });
    setNewSystemOpen(false);
    navigateToSurface('chat', { lane: lane.id });
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
              <h1 className="text-lg font-semibold">
                {app.slug === 'images' ? 'Images' : 'Studio'}
              </h1>
            </div>
            <p className="max-w-md text-sm text-muted-foreground">
              Pick a shape, name it, then describe what you want in plain words —
              it takes shape live, pulling in your files, images, and data as it
              goes.
            </p>
          </div>
          {/* The New / Open pair (the File-menu convention). Open browses an
              existing artifact; it belongs beside New, not below the Design
              systems section where it read as "…else besides design systems". */}
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setOpenPickerOn(true)}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60"
            >
              <FolderOpen className="h-3.5 w-3.5" />
              Open
            </button>
            <StudioNewMenu
              templates={templates}
              learnEnabled={laneEnv?.enabled !== false}
              onPickTemplate={(t) => void createUntitled(t.slug)}
              onPickNamed={() => setNamingOpen(true)}
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
                          <span className="text-muted-foreground" title={formatAbsolute(r.updated_at)}>
                            {` · ${formatRelativeTime(r.updated_at, { rollToDate: true })}`}
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

        {/* ── Design systems (DESIGN-SYSTEMS.md §6, first-order on the landing) ──
            The workspace's visual identity, worn by many artifacts. ONE
            `+ New design system` entry everywhere (empty + populated) → the ONE
            dedicated modal that owns import-vs-derive (the 2026-07-19 regroup —
            one intent, not two buttons; the modal explains the .zip and filters
            the derive source). A card opens the manage state. Job B (manage the
            identity); Job A (wear it) stays in the open-artifact Design tab. */}
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Design systems
            </p>
            {systems.length > 0 && (
              <button
                type="button"
                onClick={() => setNewSystemOpen(true)}
                className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
              >
                <Plus className="h-3 w-3" />
                New design system
              </button>
            )}
          </div>

          {systems.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border p-6">
              <p className="text-sm text-muted-foreground">
                No design system yet. Give your artifacts one look — import your
                brand’s export, or derive one from a style guide.
              </p>
              <button
                type="button"
                onClick={() => setNewSystemOpen(true)}
                className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60"
              >
                <Plus className="h-3.5 w-3.5" />
                New design system
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {systems.map((s) => (
                <button
                  key={s.manifest_path}
                  type="button"
                  onClick={() => onOpenSystem(s.manifest_path)}
                  className="group flex flex-col items-start rounded-lg border border-border p-3 text-left transition-colors hover:bg-muted/20"
                >
                  <span className="flex items-center gap-1.5">
                    <Palette className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 truncate text-sm font-medium">{s.name}</span>
                  </span>
                  <span className="mt-1 text-[11px] text-muted-foreground">
                    {wornBy[s.manifest_path] === undefined
                      ? '—'
                      : wornBy[s.manifest_path] === 0
                        ? 'Not worn yet'
                        : `Worn by ${wornBy[s.manifest_path]} ${wornBy[s.manifest_path] === 1 ? 'artifact' : 'artifacts'}`}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <NewArtifactModal
          templates={namingOpen ? templates : null}
          onClose={() => setNamingOpen(false)}
          onCreate={createScratch}
          dimensionsFirst={app.dimensionsFirst}
        />

        <LearnFromFlowModal
          open={learnOpen}
          targets={LEARN_TARGETS}
          onClose={() => setLearnOpen(false)}
          onStart={learnFrom}
        />

        <NewDesignSystemModal
          open={newSystemOpen}
          deriveEnabled={laneEnv?.enabled !== false}
          onClose={() => setNewSystemOpen(false)}
          onImport={importNewSystem}
          onDerive={deriveNewSystem}
        />

        {/* Open… is the OS gesture (browse an existing artifact, never a raw
            path — ADR-400 Q2). It now lives in the header's New/Open pair, not
            here below the Design systems section. */}

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
        appSlug={app.slug}
      />
    </div>
  );
}

// ── The manage state (DESIGN-SYSTEMS.md §6, the third render state) ──────────
// A design system opened for management: name · worn-by-N (the ADR-448 edge on
// the manifest) · its files (the flattened sources) · Re-import. NOT a canvas,
// NOT a modal — a dedicated panel, the deferred token-editor's future home.
//
// Step 1 (this): the panel + Re-import + the dependent COUNT. Step 2 makes the
// dependents an OPENABLE list, folds in the read-only theme panel (the §5
// widened vocabulary), and adds the token-editor slot. Named so the boundary
// is honest.
function StudioManage({
  manifestPath,
  onBack,
  onOpenArtifact,
}: {
  manifestPath: string;
  onBack: () => void;
  /** Open one of the artifacts that wear this system (step 2 makes the list
   *  clickable; step 1 wires the handler so the enrichment is drop-in). */
  onOpenArtifact: (path: string) => void;
}) {
  const [detail, setDetail] = useState<Awaited<
    ReturnType<typeof api.studio.resolveDesignSystem>
  > | null>(null);
  const [wornBy, setWornBy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reimporting, setReimporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    setError(null);
    api.studio
      .resolveDesignSystem(manifestPath)
      .then(setDetail)
      .catch(() => setError('This design system could not be read.'));
    // Worn-by: the ADR-448 reference edge, read outward from the manifest. The
    // backend returns {count: 0} on any failure, so this never throws.
    api.documents
      .dependents(manifestPath)
      .then((d) => setWornBy(d.count))
      .catch(() => setWornBy(null));
  }, [manifestPath]);

  useEffect(() => {
    load();
  }, [load]);

  // Re-import runs the SAME import against this folder (ADR-292 reapply shape) —
  // a refreshed export overwrites through the one door; the manifest path is
  // stable, so worn-by and citations survive.
  const reimport = async (file: File) => {
    setReimporting(true);
    setError(null);
    try {
      await api.studio.importDesignSystem(file, detail?.name);
      load(); // pick up the new sources/warnings
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Re-import failed.');
    } finally {
      setReimporting(false);
    }
  };

  const folder = manifestPath.replace(/\/_design\.yaml$/, '');
  const leafOf = (p: string) => p.slice(p.lastIndexOf('/') + 1);

  return (
    <div className="h-full overflow-y-auto p-6 sm:p-8">
      <div className="mx-auto w-full max-w-3xl space-y-6">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Design systems
        </button>

        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <div className="flex items-center gap-2">
              <Palette className="h-5 w-5 text-muted-foreground" />
              <h1 className="min-w-0 truncate text-lg font-semibold">
                {detail?.name ?? 'Design system'}
              </h1>
            </div>
            <p className="truncate text-[11px] text-muted-foreground">
              {folder.replace(/^\/workspace\//, '')}
            </p>
          </div>
          <div className="shrink-0">
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void reimport(f);
                e.target.value = '';
              }}
            />
            <button
              type="button"
              disabled={reimporting}
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60 disabled:opacity-50"
            >
              {reimporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
              Re-import
            </button>
          </div>
        </div>

        {error && <p className="text-xs text-red-500">{error}</p>}

        {/* Worn by — the ADR-448 reference edge. Step 2 makes this an openable
            list; step 1 shows the count (the payoff the citation contract was
            built for, surfaced at last). */}
        <div className="rounded-lg border border-border p-4">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Worn by
          </p>
          <p className="mt-1 text-sm">
            {wornBy === null ? (
              <span className="text-muted-foreground">—</span>
            ) : wornBy === 0 ? (
              <span className="text-muted-foreground">
                No artifacts wear this yet. Apply it from an artifact’s Design tab.
              </span>
            ) : (
              <button
                type="button"
                onClick={() => onOpenArtifact(folder)}
                className="text-foreground underline-offset-2 hover:underline"
                title="Open the artifacts that cite this design system (Files shows the full list)"
              >
                {wornBy} {wornBy === 1 ? 'artifact' : 'artifacts'}
              </button>
            )}
          </p>
        </div>

        {/* The files — the flattened sources the skin is composed from. */}
        <div className="rounded-lg border border-border p-4">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Files
          </p>
          {detail === null ? (
            <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading…
            </div>
          ) : detail.sources.length === 0 ? (
            <p className="mt-2 text-sm text-muted-foreground">No stylesheets found.</p>
          ) : (
            <ul className="mt-2 space-y-1">
              {detail.sources.map((s) => (
                <li key={s} className="flex items-center gap-2 text-sm">
                  <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span className="min-w-0 truncate">{leafOf(s)}</span>
                </li>
              ))}
            </ul>
          )}
          {detail && detail.warnings.length > 0 && (
            <ul className="mt-2 space-y-1 border-t border-border pt-2">
              {detail.warnings.map((w, i) => (
                <li key={i} className="text-[11px] text-amber-600">
                  {w}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* The theme panel + the token-editor slot are step 2 (they reuse the
            Design tab's skinVars parse + the shipped §5 Q4 PATCH permission). */}
      </div>
    </div>
  );
}
