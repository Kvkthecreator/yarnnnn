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
import { ArrowLeft, Check, FileText, FolderOpen, Image as ImageIcon, Link2, Loader2, MoreHorizontal, Palette, PanelLeft, PanelRight, Plus, Presentation, Upload } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { useSurfaceParam, useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { slotIsColumn, usePaneLadder, usePaneSlot } from '@/lib/shell/pane-layout';
import { formatAiReference, relPath as relPathShared } from '@/lib/interop/fileHandle';
import { useCoarsePointer } from '@/hooks/useCoarsePointer';
import { useDeclareFocus, type SurfaceFocus } from '@/lib/shell/useSurfaceFocus';
import { LearnFromFlowModal } from './LearnFromFlowModal';
import { NewDesignSystemModal } from './NewDesignSystemModal';
import { NewArtifactModal, slugify } from './NewArtifactModal';
import { defaultDestinationFor } from './artifactNaming';
import { appForKind, registerKindApps } from '@/lib/file-types';
import { StudioNewMenu } from './StudioNewMenu';
import { studioShapeStyle } from './studioShapes';
import { STRUCTURAL_PAGE_SEL } from './structureLabels';
import { isColorValue, parseSkinVars } from './skinVars';
import { OpenArtifactModal } from './OpenArtifactModal';
import { FlowEditor, type FlowEditorHandle } from './FlowEditor';
import { readRegionInner, replaceRegionInner } from '@/lib/authoring/flow/roundtrip';
// ADR-529 D1 — the one share act, shared with Files and every file surface.
import { ShareDialog } from '@/components/workspace/ShareDialog';
import { useFileLoad } from '@/components/workspace/useFileLoad';
import {
  resolveArtifactHtml,
  projectBlock,
} from '@/components/workspace/viewers/projection';
import { useFileContextMenu } from '@/components/workspace/FileContextMenu';
import { useSelfLocatedSurface, useSurfaceActions, useWindowCrumb } from '@/contexts/BreadcrumbContext';
import { useFileOrganizeVerbs } from '@/hooks/useFileOrganizeVerbs';
import { LanePanel, type SeedTarget } from '@/components/chat-surface/LanePanel';
import { SelectionGesture } from '@/components/authoring/SelectionGesture';
import {
  StudioCanvas,
  type PointerEvent2,
  type RangeRung,
  type StudioContextTarget,
} from './StudioCanvas';
import { StudioBlockMenu } from './StudioBlockMenu';
import { StudioBlockInsertMenu } from './StudioBlockInsertMenu';
import { StudioCitablePicker } from './StudioCitablePicker';
import { StudioSlashPalette } from './StudioSlashPalette';
import {
  StudioToolbar,
  type StudioArrangement,
  type StudioSelection,
  type StudioVocabulary,
} from './StudioToolbar';
// ADR-539 D1 — kindTier reads the served tier (falling back to the runtime's
// pinned copy), so a parent-side reach and the pane consult one declaration.
import { StudioDesignTab, kindTier, type StructVerb } from './StudioDesignTab';
// ADR-541 D2 — the one selection algebra (the pane reads the same two).
import { arityOf, scopeOf, spanShapeOf, unify, type PaneScope, type SpanShape } from './selection';
import { StudioUpdateMenu } from './StudioUpdateMenu';
import type { LadderRung } from './updateLadder';
import { StudioShareExport } from './StudioShareExport';
import { PagedNavigator } from './PagedNavigator';
import { SelectionBreadcrumb } from './SelectionBreadcrumb';
import {
  applyArrangement,
  applyArrangementMovingContent,
  applyArrangementPlan,
  blocksForPlan,
  applySkin,
  countCarriedBlocks,
  countGroupsOnPage,
  convertBlock,
  convertBlocks,
  deleteBlock,
  deleteBlocks,
  deletePage,
  deletePages,
  duplicateBlock,
  duplicateBlocks,
  pasteBlock,
  duplicatePage,
  editBlockText,
  galleryFragment,
  insertArrangement,
  insertBlock,
  insertIntoContainer,
  mergeBlock,
  moveBlock,
  normalizeArtifact,
  nudgeZ,
  movePage,
  movePageTo,
  movePages,
  splitBlock,
  splitBlockAndInsert,
  removePageBackground,
  removeSkin,
  retrofitKernel,
  setContainerLayout,
  setGeometry,
  setGeometryMany,
  setMeasure,
  setPageBackground,
  setPosition,
  setToken,
  setTokenMany,
  type OpResult,
} from './artifactOps';

/**
 * One step of the member's own edit lineage (ADR-523 D1).
 *
 * The snapshot is the restore mechanism; the rest is what a bare string could
 * never carry. `structural` is the load-bearing field: a non-structural undo
 * does NOT reload the iframe — it advances the override and lets the canvas
 * re-project on content change, exactly the contract a text edit already uses.
 * That is what removes the blink from the common case (typing, formatting,
 * token changes) while leaving the structural path, which genuinely needs the
 * reload, untouched.
 */
interface HistoryEntry {
  /** The document BEFORE the op — what ⌘Z restores. */
  content: string;
  /** Operator-facing verb ("insert block", "type"), for coalescing + labels. */
  label: string;
  /** Did the DOM shape change? Gates the iframe reload on replay. */
  structural: boolean;
  /** What was selected when this happened — undo returns the member there. */
  selectionId: string | null;
  /** Capture time (ms) — the coalescing window's clock (ADR-523 D3). */
  at: number;
}

/** ADR-523 D2: the history's memory ceiling, in bytes of retained document. */
const HISTORY_BUDGET_BYTES = 24 * 1024 * 1024;
/** Entries kept regardless of the byte budget, so a huge document still undoes. */
const HISTORY_FLOOR = 20;
/**
 * ADR-523 D3: same-label text edits landing closer together than this fold into
 * the open entry. A pause longer than this opens a new one, so ⌘Z rewinds the
 * phrase the member paused after — the Google-Docs split between what gets
 * SAVED (one revision per burst) and what gets UNDONE (a checkpoint per pause).
 */
const TEXT_COALESCE_MS = 600;

interface LaneInfo {
  id: string;
  name: string;
  model: string;
  /** ADR-562 D5 — the resident this lane carries. The panel names the
   *  COLLEAGUE; the engine is a fact behind the name (ADR-460 D4). */
  agent?: string | null;
  artifact_path?: string | null;
  /** ADR-450/452 — the derive binding (a "Learn from" lane). */
  derive_recipe?: string | null;
  derive_source?: string | null;
  status: string;
}

/** The named colleagues the API serves (ADR-460 D4) — slug → display name.
 *  Studio DISCARDED this array until ADR-562: it created a lane pinning a
 *  resident, then rendered the engine label because it never read the roster
 *  back. The join is the whole fix. */
interface AgentInfo {
  slug: string;
  name: string;
}

interface TemplateInfo {
  slug: string;
  label: string;
  description: string;
}

/** Strip the /workspace/ prefix for display + comparison (ADR-587: one grammar). */
const relPath = relPathShared;

function baseName(p: string): string {
  const parts = p.split('/');
  return parts[parts.length - 1] || p;
}

/** The artifact's name from its PATH — the titleized meaning folder.
 *
 *  `operation/prd-for-yarnnn/document.html` → "Prd for yarnnn". The leaf is a
 *  TYPE marker (document/deck/article/page.html), not a name.
 *
 *  This is the FALLBACK half of `artifact_name` in services/authoring.py. It is
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
 *  ADR-469 lifted the name into `<title>` and made `services/authoring.py::
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
 *  Plain words, no model-speak: they teach what the authoring apps DO.
 *  (The `article` entry died with its type, ADR-505; `web` falls to the
 *  document set at the lookup until it earns its own.) */
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
};

/**
 * The authoring-surface app config (ADR-472 D1/D2, extended by ADR-518).
 *
 * Docs, Studio and IMAGES are three APPS over one shared authoring machinery:
 * the same bound lane, the same object layer, the same live render. What
 * differs is the surface slug (which param namespace the window manager
 * reads), the templates offered, and the app's own chrome. Parameterizing
 * beats forking 2,500 lines — the dual-approach smell the hooks discipline
 * forbids.
 */
export interface AuthoringApp {
  /** Surface slug — the param namespace (`docs.file` vs `studio.file`) AND
   *  the app identity the kernel's type→app association keys on (ADR-473 D2).
   *  Which shapes this app offers and which artifacts are its own are both
   *  DERIVED from that association — never listed here (ADR-473 D3). */
  slug: 'slides' | 'images';
  /** Operator-readable app name — the one fact the chrome shows (ADR-518 D7
   *  retired the per-site slug ternaries in favor of this declaration). */
  label: string;
  /** The landing's one-line invitation, in the app's own voice (ADR-518 D7 —
   *  a writing app invites writing; a layout app invites shaping). */
  tagline: string;
  /** The landing glyph — the same family the dock wears for this app
   *  (lib/shell/surface-icons), declared here so the landing never falls to
   *  another app's icon. */
  icon: LucideIcon;
  /** Dimensions-first creation (ADR-472 D3) — a raster artifact is born at a
   *  size. Not derivable from ownership, so it stays an app property. */
  dimensionsFirst?: boolean;
}

// DOCS_APP was DELETED by ADR-599 D5 with its app; the writing medium's
// future is a separate blogger-app arc.
export const STUDIO_APP: AuthoringApp = {
  // ADR-599 D4 — the full evolve: member-facing identity is Slides (slug,
  // label, route); the component tree keeps its internal Studio name (D6).
  slug: 'slides',
  label: 'Slides',
  tagline:
    'Name a deck, then describe what you want in plain words — it takes shape live, slide by slide, pulling in your files, images, and data as it goes.',
  // ADR-602 D4 — the PRESENTATION glyph, matching the launcher (`icon_key:
  // presentation`, kernel_surfaces). The landing had kept `Palette` from
  // before ADR-599 D4's icon pass, so the app wore two different faces
  // depending on where a member met it; `palette` is now Designer's glyph,
  // which would have read as the wrong being's mark on the Slides door.
  // (`Palette` the import STAYS — the design-system picker uses it, which is
  // a different noun and a correct use.)
  icon: Presentation,
};
export const IMAGES_APP: AuthoringApp = {
  slug: 'images',
  label: 'Images',
  tagline:
    'Pick a size, name it, then describe the image in plain words — it renders live on the canvas.',
  icon: ImageIcon,
  dimensionsFirst: true,
};

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
  // The NAMING table (every engine, retired included). `models` is the CHOOSER
  // and drops retired rows, so a bound lane pinned to one would name itself by
  // its RAW ID (ADR-559 D2 — one dict, two audiences).
  const [modelNames, setModelNames] = useState<Record<string, string>>({});
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  /** ADR-562 D6 — the served app registry (slug → its name for its resident). */
  const [apps, setApps] = useState<Array<{ slug: string; resident: string; name: string }>>([]);
  // ADR-602 — the BEINGS roster. `agents` is the HIRE roster and is empty by
  // ADR-599 (nobody is `offered`), so resolving a resident's name through it
  // always missed and fell through to the ENGINE label: the bound lane read
  // "Message Claude Sonnet 4.6…" when Editor was answering. A resident is not
  // a hire, so it was never going to be there.
  const [beings, setBeings] = useState<Array<{ slug: string; name: string }>>([]);
  const [lanes, setLanes] = useState<LaneInfo[]>([]);
  const [laneError, setLaneError] = useState<string | null>(null);

  const refreshLanes = useCallback(async () => {
    try {
      // Studio's lanes ARE the bound ones — they left the /chat list, not this one.
      const res = await api.lanes.list(true);
      setLanesEnabled(res.enabled);
      setModels(res.models);
      setModelNames(res.model_names ?? {});
      // ADR-562 D5 — keep the roster. Dropping it here is what made the panel
      // say "Claude Sonnet is working…" in a lane whose resident is Designer.
      setAgents((res.agents ?? []) as AgentInfo[]);
      setApps(res.apps ?? []);
      setBeings((res.beings ?? []) as Array<{ slug: string; name: string }>);
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
        // ADR-562 D3 — the surface names WHICH APP is asking; the RESIDENT is
        // resolved server-side from that app's own declaration
        // (`services/apps/*`). The client no longer holds the colleague fact —
        // it held it before and never read it back, so the panel rendered the
        // engine where a resident had been pinned.
        app: app.slug,
        artifact_path: artifactPath,
      })
      .then(() => refreshLanes())
      .catch(() => setLaneError('Could not create the authoring lane.'))
      .finally(() => setCreatingLane(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifactPath, lanesEnabled, boundLane]);

  // ── The artifact itself (the surface owns the load; canvas projects) ───
  // TWO signals, because "refetch the file" and "my edit history is no longer
  // valid" are different facts and only one of them is about authorship.
  //
  //   reloadKey  — refetch + drop the local override. Bumped by ANY reload:
  //                a foreign write, an own server-side write (retitle), a
  //                failed op, the member's explicit reload button.
  //   foreignKey — a write this member did NOT make landed on this file. Only
  //                THIS clears undo/redo, because a snapshot cannot be rebased
  //                onto someone else's change.
  //
  // Before the split, history hung off reloadKey, so an own retitle — which
  // touches no block content and invalidates nothing — silently threw away the
  // member's whole undo stack.
  const [reloadKey, setReloadKey] = useState(0);
  const [foreignKey, setForeignKey] = useState(0);
  // `error` is read, not discarded. useFileLoad deliberately separates a 404
  // ("no longer at this path") from a real load failure, and Studio was throwing
  // that distinction away: any 500 fell into the notFound branch and told the
  // member their artifact "does not exist yet" — the most alarming possible
  // reading of a transient server error, on a surface whose whole promise is
  // that the record is durable.
  const { file: loadedFile, loading, notFound, error: loadError } =
    useFileLoad(artifactPath ?? '', { reloadKey });

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
    // ADR-511 D5 — the load-side normalize: the working copy carries full
    // identity (bare content promoted, containers stamped) from the moment it
    // arrives, so the canvas can select what the ops can address. Nothing is
    // written here — the identities land in the substrate with the first real
    // write (migration-by-use). Idempotent on an already-annotated artifact.
    return loadedFile.content
      ? { ...loadedFile, content: normalizeArtifact(loadedFile.content) }
      : loadedFile;
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

  // A path change or ANY refetch drops the override — it can't shadow content
  // it did not descend from. This is the refetch signal's job and stays coupled
  // to reloadKey; only the HISTORY signal is separate (see foreignKey).
  useEffect(() => {
    setLocalOverride(null);
  }, [artifactPath, reloadKey]);

  const onArtifactWrite = useCallback(
    (writtenPath: string) => {
      if (!artifactPath) return;
      if (relPath(writtenPath) === relPath(artifactPath)) {
        // A FOREIGN write (the lane) genuinely changed the file — refetch AND
        // invalidate history: our snapshots predate a change we did not make.
        setReloadKey((k) => k + 1);
        setForeignKey((k) => k + 1);
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
  const [seed, setSeed] = useState<{ text: string; nonce: number; target?: SeedTarget } | null>(null);
  // ADR-579 D7 — a gesture door passes WHAT WAS CLICKED as a typed target
  // beside the editable intent text; the pane holds it as a chip and sends
  // it as the turn's `seed`. Ids and excerpts no longer flatten into the
  // member's composer prose.
  const seedComposer = useCallback(
    (text: string, target?: SeedTarget) =>
      setSeed((s) => ({ text, nonce: (s?.nonce ?? 0) + 1, target })),
    [],
  );
  // ── The selection (ADR-444; slot + page grains ADR-453): held by the
  // surface, it anchors the toolbar's deterministic ops, drives the Design
  // tab's scope, AND informs the lane (via a visible composer seed). ──
  const [selection, setSelection] = useState<StudioSelection | null>(null);
  /** ADR-528 — the blocks a live text RANGE intersects, when the member has
   *  one. Deliberately SEPARATE state from `selection`, not a field on it:
   *  `selection` answers "which block did you point at" (a click) and the
   *  range answers "what have you got selected right now" (a drag). They are
   *  different questions with different lifetimes, and collapsing them is what
   *  produced the defect — the pane read the click answer while the member was
   *  looking at a six-block range. Empty = no range. */
  const [rangeBlockIds, setRangeBlockIds] = useState<string[]>([]);
  /** ADR-546 D3 — the span's SHAPE, derived by `spanShapeOf` (selection.ts, the
   *  one home) from the rungs the runtime reports alongside the ids. Held here
   *  beside `rangeBlockIds` for the same reason the ids are: it is a fact about
   *  the live gesture, not a field on the click-derived `selection`. */
  const [rangeShape, setRangeShape] = useState<SpanShape | null>(null);
  const onRange = useCallback((ids: string[], rungs?: RangeRung[]) => {
    setRangeBlockIds(ids);
    // No rungs = an older projection still live in the iframe. Degrade to a
    // bare count rather than inventing a shape (the ADR-482 D3 direction:
    // withhold, never guess).
    setRangeShape(
      rungs && rungs.length === ids.length
        ? spanShapeOf(
            ids.map((blockId, i) => ({ blockId, rung: rungs[i], text: rungs[i].text ?? null })),
          )
        : null,
    );
  }, []);
  /** ADR-519 D4.1 — the blocks a ⇧-click SET holds, on a staged medium. The
   *  same shape and the same reasoning as `rangeBlockIds` above, for the same
   *  reason: a set answers "how many does the verb take", `selection` answers
   *  "what is the subject". They are different questions, so they are different
   *  state — a set is never a field on the selection and never a sixth scope.
   *
   *  The runtime already settled this (projection.ts: `group` rides ALONGSIDE
   *  `cur`, and `cur` stays the primary the box/handles/pane follow), so this
   *  is the parent half of a rule the substrate already keeps. The set's FIRST
   *  member is the primary — `__yarnnnGroup()` returns `[cur].concat(group)` —
   *  which is why `selection` stays valid and meaningful while a set is live.
   *  Length < 2 means "no set": one block is a selection, not a group. */
  const [groupIds, setGroupIds] = useState<string[]>([]);
  const onGroup = useCallback((ids: string[]) => setGroupIds(ids), []);

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
      const pageCount = doc.querySelectorAll(STRUCTURAL_PAGE_SEL).length;
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
      label: p.label ?? null,
      headingId: p.headingId ?? null,
      headingText: p.headingText ?? null,
    });
  }, []);
  const onPointClear = useCallback(() => {
    setCtxMenu(null); // same reason as onPoint — a click on empty canvas
    setSelection(null);
    setEditingBlockId(null);
    // ADR-519 D4.1 — a set cannot outlive the selection it rode alongside.
    // The runtime clears it at its own chokepoint and says so; this is the
    // parent-side backstop, because a STUCK set is uniquely bad: every
    // single-subject section withdraws, so the member loses every editing
    // affordance AND the gesture that would get them back.
    setGroupIds([]);
  }, []);

  // ADR-446: which block is being edited in place (surface-held; the canvas
  // commands its iframe runtime). Selecting a different block exits the prior
  // edit (the runtime commits on the enter of the next).
  const [editingBlockId, setEditingBlockId] = useState<string | null>(null);

  // ── The canvas context menu (ADR-462) ──────────────────────────────────
  // The runtime has already SELECTED the block under the cursor (D7), so this
  // holds only the anchor + the grain. Every row dispatches an op that already
  // exists — a second entrance, never a second write path (D1).
  const [ctxMenu, setCtxMenu] = useState<StudioContextTarget | null>(null);
  // ADR-586 D6 — which tier the mount opens expanded. Set ONLY by the
  // toolbar's contextual [Update]; a right-click opens collapsed (null).
  // The toolbar's contextual Update: synthesize the menu's target from the
  // live selection and mount the SAME menu the right-click renders — one
  // definition of the block acts, two mounts (the blockRows discipline).
  // Conservative DOM facts (positioned/framed false): the toolbar cannot see
  // the projected DOM, so the geometry rows simply don't render from this
  // mount; the right-click keeps the full answer.
  // ADR-589 — the Update DOOR replaces the old selection FORK (block →
  // block-acts menu, otherwise → a slide-arrangement gallery). That fork's
  // no-selection branch silently assumed the target was the page, which left
  // `document` scope — the artifact's own typography, palette and design
  // system — with no entrance anywhere in the door named Update.
  const [updateMenu, setUpdateMenu] = useState<{ x: number; y: number } | null>(null);
  const openUpdateDoor = useCallback((at: { x: number; y: number }) => {
    setUpdateMenu({ x: at.x, y: at.y });
  }, []);

  /** ADR-589 D1 — picking a rung RE-TARGETS. Setting selection IS the
   *  mechanism: StudioCanvas re-commands the runtime with
   *  `yarnnn-select-block` whenever `selectedBlockId` changes, so the canvas
   *  box follows without a second message. A document rung clears the
   *  selection, which is exactly what that scope means. */
  const retargetToRung = useCallback((rung: LadderRung) => {
    setEditingBlockId(null);
    if (rung.scope === 'document') {
      setSelection(null);
      return;
    }
    setSelection((prev) => ({
      blockId: rung.blockId,
      blockKind: rung.blockId && rung.blockId === prev?.blockId ? (prev?.blockKind ?? null) : null,
      slideIndex: prev?.slideIndex ?? null,
      pageIndex: prev?.pageIndex ?? null,
      slot: rung.blockId && rung.blockId === prev?.blockId ? (prev?.slot ?? null) : null,
      arrange: prev?.arrange ?? null,
      text: '',
      label: rung.label,
      tier: rung.scope === 'container' ? 'structure' : (prev?.tier ?? null),
    }));
  }, []);
  // Copy/paste is a BLOCK clipboard, not the OS text one: the unit is a block's
  // source HTML, so a paste can reconstruct it whole (kind + tokens + citations)
  // rather than smearing its text into another block. Session-scoped by design —
  // a cross-artifact block clipboard is a substrate question, not a menu one.
  const blockClip = useRef<string | null>(null);

  const template = useMemo(() => extractTemplate(file?.content ?? ''), [file]);
  const modelLabel = useMemo(
    () =>
      (boundLane?.model ? modelNames[boundLane.model] : undefined) ??
      models.find((m) => m.id === boundLane?.model)?.label ??
      boundLane?.model ??
      '',
    [models, modelNames, boundLane],
  );

  // ADR-562 D5 — WHO this lane is, for the member to read. The resident's name
  // ("Designer"), falling back to the engine label only when there is no
  // colleague to name (a pre-registry lane). The SAME chain ChatSurface has
  // always run; this surface simply never ran it, so a pinned resident was
  // invisible and the member read the engine instead.
  //
  // The engine is not hidden — it stays legible as the lane's own fact
  // (`modelLabel`, still shown beside the artifact). The rule is ADR-460 D4's:
  // identity leads, the technical fact rides behind it.
  const laneLabel = useMemo(() => {
    // ADR-602 D7 — resolve from THIS SURFACE's app first, then the lane's
    // derived resident. A pre-ADR-567 bound lane carries no `app` stamp
    // (ADR-597 D3 deliberately left ~35 of them alone), so the server's
    // derivation returns None and the composer fell back to the ENGINE —
    // "Message Claude Sonnet 4.6…" on a deck Editor was authoring. The
    // surface cannot be wrong about which app it IS, so it is the stronger
    // fact; the lane's stamp remains the fallback for anything else.
    const slug = apps.find((a) => a.slug === app.slug)?.resident || boundLane?.agent;
    if (slug) {
      // ADR-562 D6 — THIS app's name for its resident wins ("Writer" in Docs).
      // Read from the served registry, never a TS table: the declaration the
      // prompt uses is the declaration the glass shows, so the two cannot
      // disagree about who the member is talking to.
      const appName = apps.find((a) => a.slug === app.slug)?.name;
      if (appName) return appName;
      // The being's OWN name — served from the same registry the prompt reads.
      // Checked before `agents` because `agents` is the hire roster: a desk's
      // resident is never on it (ADR-598), which is why this fell through to
      // the engine label until ADR-602.
      const being = beings.find((b) => b.slug === slug)?.name;
      if (being) return being;
      const named = agents.find((a) => a.slug === slug)?.name;
      if (named) return named;
    }
    return modelLabel;
  }, [agents, apps, beings, app.slug, boundLane, modelLabel]);

  // ── The served kernel vocabulary (ADR-443 R4 + ADR-444 + ADR-447): blocks +
  // arrangements — the toolbar EXECUTES from it, the posture teaches from the
  // same source. One fetch per open. (Layouts are served too but the Studio no
  // longer switches type — ADR-447 deleted the format-switcher.) ──
  const [vocabulary, setVocabulary] = useState<StudioVocabulary | null>(null);
  /** The vocabulary fetch FAILED, as distinct from not having answered yet.
   *  Without this the two states are indistinguishable at the insert door, and
   *  the failed one renders as an empty menu that looks like a dead button. */
  const [vocabularyError, setVocabularyError] = useState(false);

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
  // services/authoring.py). `paged` (deck, page) = the CONTAINER is the unit, so
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

  // ── ADR-522: the focus declaration — what the member is looking at ──────
  //
  // D3: the VIEWPORT, distinct from the selection. On a staged deck the member
  // pages with PgUp/PgDn and selects nothing, so this is the only signal that
  // says which slide is on screen. The runtime already reported it; ADR-522
  // lifted it out of StudioCanvas's restore ref.
  const [viewportPage, setViewportPage] = useState<number | null>(null);
  const onScrollPos = useCallback((pos: { y: number; slide: number | null }) => {
    setViewportPage(pos.slide);
  }, []);

  // Compose the declaration. Precedence (D3): the SELECTION wins where it
  // exists — it is the finer, truer answer — and the viewport fills where it
  // doesn't. `document` scope means "this artifact, nothing finer", which is
  // the honest reading when the member has neither selected nor scrolled.
  const focus = useMemo<SurfaceFocus | null>(() => {
    if (!artifactPath) return null;
    const viewport = viewportPage != null ? { pageIndex: viewportPage } : null;
    const base = { app: app.slug, path: relPath(artifactPath), viewport };
    const s = selection;

    // Block grain — a vocabulary block.
    if (s?.blockId && s.blockKind) {
      // D4, flow only: name the SECTION the member is writing in — the nearest
      // heading at or above the caret. Docs has no section unit (flat sibling
      // headings, no wrapper), so the heading block IS the section, and "this
      // section" means from it to the next. On a paged medium the slide is
      // already the unit, so the heading adds nothing and we keep the block.
      if (layoutMode === 'flow' && s.headingId && s.headingId !== s.blockId) {
        return {
          ...base,
          scope: 'block' as const,
          id: s.headingId,
          pageIndex: null,
          label: 'heading',
          excerpt: s.headingText || null,
        };
      }
      return {
        ...base,
        scope: 'block' as const,
        id: s.blockId,
        pageIndex: s.slideIndex ?? s.pageIndex ?? null,
        label: s.label ?? s.blockKind,
        excerpt: s.text || null,
      };
    }
    // Container grain — identity but no vocabulary (ADR-511 D3).
    if (s?.blockId) {
      return {
        ...base,
        scope: 'container' as const,
        id: s.blockId,
        pageIndex: s.slideIndex ?? s.pageIndex ?? null,
        label: s.label ?? null,
        excerpt: s.text || null,
      };
    }
    // Page grain — a selected slide/section, or (D3) merely the one on screen.
    const pageIdx = s?.slideIndex ?? s?.pageIndex ?? viewportPage;
    if (pageIdx != null) {
      return {
        ...base,
        scope: 'page' as const,
        id: null,
        pageIndex: pageIdx,
        label: s?.label ?? (template === 'deck' ? 'slide' : 'section'),
        excerpt: s?.text || null,
      };
    }
    // Nothing finer than the artifact itself.
    return {
      ...base,
      scope: 'document' as const,
      id: null,
      pageIndex: null,
      label: template || null,
      excerpt: null,
    };
  }, [artifactPath, app.slug, selection, viewportPage, template, layoutMode]);

  useDeclareFocus(app.slug, focus);
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
        // ADR-528 D5 — scope the block roster to THIS app, once, here.
        //
        // At the CHOKEPOINT, never at the offering sites (rule 11 / ADR-484's
        // recorded fault: a rule guarded at two click sites left five other
        // routes inheriting nothing while its gate stayed green). There are
        // three offering surfaces today — the insert menu, the slash palette
        // and turn-into — plus lookup-by-kind callers that must keep resolving
        // fragments for kinds already IN the document. Filtering here gives
        // every offering surface the app's roster and leaves the lookups
        // alone, because a kind that is no longer offered still renders and
        // still edits (an inert name, ADR-511 D8).
        //
        // `apps: null` = every app (the served default). Absent for all but
        // the two rows Docs does not offer.
        const scoped: StudioVocabulary = {
          ...v,
          blocks: v.blocks.filter((b) => !b.apps || b.apps.includes(app.slug)),
        };
        if (live) {
          setVocabulary(scoped);
          setVocabularyError(false);
        }
      })
      .catch(() => {
        // NOT silent. "Toolbar menus stay empty" is exactly the state the
        // operator met as "Insert doesn't work": the vocabulary IS the block
        // list, so a failed fetch makes every insert door render nothing, and
        // the only thing left in the console was an unrelated Sentry beacon to
        // blame. A failure the member can SEE beats a failure they must guess.
        // `live` is respected so an unmounted surface never reports.
        if (live) setVocabularyError(true);
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

  // ADR-544 D5.1 — the runtime refuses a gesture the containment law forbids
  // (today: a ⇧-click building a set across two Areas). It must be SAID, not
  // silently swallowed: an affordance that does nothing is the defect ADR-544
  // keeps finding. The runtime posts a REASON code and never operator-facing
  // words — the surface owns the sentence, so there is one place to change it.
  const [refusal, setRefusal] = useState<string | null>(null);
  const handleRefused = useCallback((reason: string) => {
    setRefusal(
      reason === 'cross-area-set'
        ? 'Select objects from one area at a time — a set spanning two areas has no shared frame to align against.'
        : 'That is not available here.',
    );
  }, []);
  // The notice is transient: it answers a gesture, so it clears on the next one
  // rather than lingering as chrome the member must dismiss.
  useEffect(() => {
    if (!refusal) return;
    const t = setTimeout(() => setRefusal(null), 4000);
    return () => clearTimeout(t);
  }, [refusal]);

  // ── ADR-524 D1/D2 — the patch channel ────────────────────────────────────
  // A block-local op sends its projected block to the runtime instead of
  // swapping srcDoc. srcDoc is a WHOLE-DOCUMENT handoff: the browser discards
  // the live document and rebuilds it, destroying scroll/caret/selection/zoom,
  // which is why commandEdit exists to put all four back. A patch changes one
  // element in place, so there is nothing to restore.
  const [patch, setPatch] = useState<{
    /** ADR-547 D2/D4 — the blocks this op touched, projected. One for a
     *  block-local edit, N for a span op; they share ONE `appliedFor` because
     *  together they bring the live DOM to a single artifact state. */
    blocks: Array<{ blockId: string; html: string }>;
    nonce: number;
    /** The full artifact content this patch brings the live DOM in line with —
     *  the canvas skips its re-projection for exactly this string. */
    appliedFor: string;
  } | null>(null);
  const patchNonce = useRef(0);
  // D2: patchability is decided by the OP and defaults to NO. A wrong patch
  // leaves the canvas silently disagreeing with substrate; a redundant full
  // swap only blinks. So this is an allowlist of ops proven block-local, and a
  // new op is a full swap until someone deliberately adds it here.
  // ── ADR-560 D8: ADR-540's retire channel is DELETED ──────────────────
  // Flow no longer edits in an iframe, so there is no teardown gasp to
  // fence: the model (FlowEditor) is the one writer and re-parses external
  // writes itself. Paged never had a whole-body commit to retire.

  const sendPatch = useCallback(
    async (blockIds: string[], html: string) => {
      if (!artifactPath || blockIds.length === 0) return false;
      try {
        // ADR-547 D2 — project EVERY touched block. All-or-nothing: if any block
        // is unaddressable the caller falls back to the ordinary re-projection,
        // because a partial patch would leave the live DOM in a state no single
        // `appliedFor` describes — and `appliedFor` is what suppresses the
        // re-projection. A half-true claim there is worse than no claim.
        const projected: Array<{ blockId: string; html: string }> = [];
        for (const blockId of blockIds) {
          const one = await projectBlock(html, blockId, artifactPath);
          if (!one) return false; // block vanished / unaddressable → full swap
          projected.push({ blockId, html: one });
        }
        patchNonce.current += 1;
        setPatch({ blocks: projected, nonce: patchNonce.current, appliedFor: html });
        return true;
      } catch {
        return false; // projection failed → the caller falls back to a reload
      }
    },
    [artifactPath],
  );

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
  // Model (the ratified choices): session-scoped, cleared on any FOREIGN write
  // to this file — you cannot undo across a conflict you did not make (ADR-523
  // §2 takes that ceiling deliberately rather than paying for 35 hand-written
  // op inverses). An undo is itself a normal op (a full-content replace back
  // through the door), so it is durable + CAS-safe like any other; the depth
  // counter below just stops it re-pushing its own snapshot and clearing the
  // redo branch it is walking.
  //
  // ADR-523 D1: an entry is a LINEAGE RECORD, not a bare string. The snapshot
  // is still what makes restore correct, but a snapshot alone cannot say what
  // the member did or where they were — so undo could only ever be a blunt
  // whole-document swap that reloaded the iframe and dropped the selection.
  const undoStack = useRef<HistoryEntry[]>([]);
  const redoStack = useRef<HistoryEntry[]>([]);
  // ADR-523 D2: bounded by BYTES, not by a count. A 100-entry cap is meaningless
  // when one entry can be 40KB or 4MB — the old cap made memory proportional to
  // document size. Evict oldest-first, but always keep a floor of recent entries
  // so a huge document still has a usable history.
  const trimHistory = useCallback((stack: HistoryEntry[]) => {
    let bytes = 0;
    for (const e of stack) bytes += e.content.length;
    while (stack.length > HISTORY_FLOOR && bytes > HISTORY_BUDGET_BYTES) {
      const dropped = stack.shift();
      if (!dropped) break;
      bytes -= dropped.content.length;
    }
  }, []);
  // A COUNTER, not a boolean. A replay is async (the write queues), so a member
  // holding ⌘Z overlaps them: with a boolean, the FIRST replay's `.finally()`
  // cleared the flag while a later replay was still in flight, and the next
  // press was then read as a fresh forward edit — it pushed the replayed state
  // back onto the undo stack and CLEARED the redo branch. A fast undo run
  // corrupted its own history and redo died mid-sequence. Counting depth means
  // the flag is only clear once every replay has settled.
  const replayDepth = useRef(0);
  // Read the selection through a ref for the same reason as liveRef: the write
  // door is a stable callback and must not re-bind every time the member clicks
  // a different block, but it needs the selection as of THIS gesture.
  const selectionIdRef = useRef<string | null>(null);
  selectionIdRef.current = selection?.blockId ?? null;
  useEffect(() => {
    // A path change or a FOREIGN write starts a fresh history. Not every
    // reload: an own retitle refetches (reloadKey) but changes no block content,
    // so the stack it used to discard was still perfectly valid.
    undoStack.current = [];
    redoStack.current = [];
  }, [artifactPath, foreignKey]);

  const writeAndAdvance = useCallback(
    (
      compute: (liveHtml: string) => string | null,
      message: string,
      reload: boolean,
      /** THE OP'S DECLARED GRAIN (ADR-524 D2, widened by ADR-547 D4).
       *
       *  The block ids this op touched — one for a block-local edit, N for a span
       *  op (setTokenMany / convertBlocks over a range), empty/absent when the op
       *  RESTRUCTURED the document (insert/move/delete/split/merge) or the commit
       *  came from the browser itself.
       *
       *  Two things ride on it, and ADR-547 §1 is what happens when the second is
       *  forgotten:
       *   1. the patch channel (no srcDoc swap, nothing to restore); and
       *   2. **whether the live iframe DOM learns the op happened at all.** An op
       *      that declares nothing leaves the iframe holding a pre-op body, and
       *      the member's next keystroke commits that body back over the op — one
       *      200-OK write erasing another, with CAS satisfied and no conflict to
       *      detect (measured on prod: ADR-547 §1.2).
       *
       *  Ignored when `reload` is true: a re-projecting op hands the iframe a
       *  fresh document, so it cannot be holding a stale one. */
      patchBlockIds?: string[] | string | null,
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
      // Capture the PRE-mutation state as a lineage entry (ADR-523 D1).
      // Skipped while replaying: an undo/redo must not push its own before-state
      // (that would make ⌘Z a no-op toggle) — the replay manages the stacks
      // itself. A fresh forward edit invalidates the redo branch, as every
      // editor does.
      // ADR-560: NOT on flow — the model's own history is the one undo there
      // (⌘Z is a ProseMirror command; external writes re-enter as undoable
      // transactions), and this stack's only entrances were the iframe's ⌘Z
      // relays, which flow no longer mounts. Pushing here would hoard
      // whole-document snapshots nothing can ever pop.
      if (replayDepth.current === 0 && live && resolvedMode !== 'flow') {
        const now = Date.now();
        const prev = undoStack.current[undoStack.current.length - 1];
        // ADR-523 D3: COALESCE a fast run of same-label text edits into the
        // entry already open, so history checkpoints at the member's pauses
        // rather than at the write cadence. The write layer is untouched —
        // revisions still batch on blur/idle-2s (ADR-444); this only decides
        // how far ONE ⌘Z rewinds. Structural ops never coalesce: each is a
        // discrete act the member expects to undo on its own.
        const coalesce =
          prev != null &&
          !reload &&
          !prev.structural &&
          prev.label === message &&
          now - prev.at < TEXT_COALESCE_MS;
        if (coalesce) {
          // Keep the OLDER content (the true before-state of the burst) and
          // just extend the window — this is what makes ⌘Z rewind a phrase
          // instead of a keystroke, without ever losing the burst's origin.
          prev.at = now;
        } else {
          undoStack.current.push({
            content: live.content,
            label: message,
            structural: reload,
            selectionId: selectionIdRef.current,
            at: now,
          });
          trimHistory(undoStack.current);
        }
        redoStack.current = [];
      }
      // ADR-453 D2: the kernel element retrofits on first touch, at the one
      // member write door. Byte-identical when current — never manufactures a
      // revision on its own.
      const html = retrofitKernel(computed, kernelStyleRef.current);
      // ADR-540 — retire the CURRENT document's commits BEFORE the override
      // advances. Ordering is the whole fix: the override is what triggers the
      // re-projection whose teardown fires the stale beforeunload commit, so
      // the runtime has to be told first. A patchable op is exempt — it does
      // NOT re-project (that is the point of ADR-524's channel), so its
      // document stays live and must keep its right to commit the member's
      // in-flight typing.
      // Normalize the declared grain: one id, N ids, or none.
      const touched =
        patchBlockIds == null ? [] : typeof patchBlockIds === 'string' ? [patchBlockIds] : patchBlockIds;
      // ADR-540 — retire the CURRENT document's commits when it is about to be
      // torn down and replaced. An op that PATCHES keeps its document alive (and
      // therefore its right to commit in-flight typing), which is exactly why
      // ADR-547 D2 requires the patch to actually reach it.
      // Advance the live CONTENT now (the next op computes off this); the HEAD
      // advances only on ack (the queued write below reads it fresh).
      liveRef.current = { content: html, head: live?.head ?? null };
      setLocalOverride((cur) => ({
        anchorHead,
        content: html,
        headVersionId: cur?.headVersionId ?? live?.head ?? '',
      }));
      if (reload) setReloadKey((k) => k + 1);
      // ADR-524 D1/D2 — a block-local op patches instead of re-parsing. Fire
      // and forget: the projection is async, but the override above has ALREADY
      // advanced, so if the patch never lands the canvas still converges on the
      // next ordinary re-projection. A patch is an optimization over a correct
      // path, never the thing correctness depends on.
      if (!reload && touched.length > 0 && resolvedMode !== 'flow') void sendPatch(touched, html);

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
          // The op did NOT land and we are about to take authoritative content
          // from the server. Our snapshots describe a lineage that no longer
          // exists (an unresolved 409 means a foreign write won), so the
          // history is invalid here too — this is a foreign event, not a
          // routine refetch.
          setForeignKey((k) => k + 1);
          return false;
        }
      };
      // Chain, and keep the tail alive even if this link fails.
      const next = writeTail.current.then(run, run);
      writeTail.current = next.catch(() => false);
      return next;
    },
    [artifactPath, loadedFile, sendPatch, trimHistory, resolvedMode],
  );

  // ⌘Z — restore the previous state; ⌘⇧Z — re-apply the one just undone.
  // Both replay a captured document through the ONE write door as a full
  // replace, so the restore is a normal CAS-safe revision like any other op.
  // `replayDepth` stops the door from pushing the replayed before-state back
  // onto the stack.
  //
  // ADR-523 D1 — the reload is now CONDITIONAL on the entry's own `structural`
  // flag. Every undo used to pass reload=true, so reverting a typo re-parsed the
  // whole iframe, re-injected its runtimes and then restored scroll/caret/zoom
  // by postMessage — a visible blink on the most common undo there is. A
  // non-structural entry changed no DOM shape, so the canvas re-projects on the
  // content change alone, exactly as it already does for a text edit.
  //
  // The replayed entry carries the SELECTION the member had at capture, so undo
  // returns them to where the edit happened rather than leaving the canvas
  // pointing at whatever was selected when they pressed ⌘Z.
  const replay = useCallback(
    (entry: HistoryEntry, verb: 'undo' | 'redo', onto: HistoryEntry[]) => {
      const current = liveRef.current?.content ?? '';
      // The counterpart entry mirrors the one being replayed: same lineage
      // facts, so a redo blinks exactly as much (or as little) as its undo did.
      onto.push({
        content: current,
        label: entry.label,
        structural: entry.structural,
        selectionId: selectionIdRef.current,
        at: Date.now(),
      });
      trimHistory(onto);
      replayDepth.current += 1;
      void writeAndAdvance(
        () => entry.content,
        `${app.label}: ${verb}`,
        entry.structural,
      ).finally(() => {
        replayDepth.current -= 1;
      });
      // Restore the member's place. Two guards, both load-bearing:
      //   1. the block must still EXIST in the document being restored — a
      //      structural undo can remove the very block that was selected;
      //   2. we only ever RE-POINT an existing selection, never fabricate one.
      //      StudioSelection carries kind/slide/page/slot/arrange that only the
      //      canvas runtime can supply; synthesizing a partial here would put a
      //      malformed selection into the toolbar's hands. When there is no
      //      live selection the canvas re-points itself on re-projection.
      if (entry.selectionId && entry.content.includes(entry.selectionId)) {
        setSelection((sel) =>
          sel && sel.blockId !== entry.selectionId
            ? { ...sel, blockId: entry.selectionId }
            : sel,
        );
      }
    },
    [writeAndAdvance, app.label, trimHistory],
  );

  const handleUndo = useCallback(() => {
    const prev = undoStack.current.pop();
    if (prev == null) return; // nothing to undo — quiet no-op
    replay(prev, 'undo', redoStack.current);
  }, [replay]);

  const handleRedo = useCallback(() => {
    const nextState = redoStack.current.pop();
    if (nextState == null) return;
    replay(nextState, 'redo', undoStack.current);
  }, [replay]);

  // ADR-560 — the flow model's handle: the one flush chokepoint (see applyOp).
  const flowRef = useRef<FlowEditorHandle | null>(null);

  const applyOp = useCallback(
    async (
      compute: (html: string) => OpResult | null,
      message: string,
      /** ADR-547 D2/D4 — the blocks this op touched. An op that changes block
       *  attributes MUST name them, or the live iframe DOM never learns the op
       *  happened and the member's next keystroke commits it away (§1.2). Absent
       *  = the op restructured the document, which re-projects. */
      touchedBlockIds?: string[] | string | null,
    ) => {
      if (!artifactPath || !file?.content) return;
      setOpError(null);
      // ADR-560 — ONE writer means the op's base must include the member's
      // in-flight typing: flush the model BEFORE computing. This is ADR-547's
      // per-op "declare your blocks" discipline collapsed to one chokepoint;
      // the compute below re-runs against liveRef inside the write queue, so
      // it applies to the flushed content, and the editor re-parses the op's
      // own result synchronously — nothing for a later keystroke to revert.
      if (resolvedMode === 'flow') flowRef.current?.flush();
      // Guard against the CURRENT render so a genuine miss still reports; the
      // real computation re-runs against live state inside the write queue (an
      // op queued behind another must apply to the previous op's result).
      if (!compute(file.content)) {
        // The old copy said "select something in the document first" — naming a
        // cause that is largely UNREACHABLE (insertBlock never returns null for
        // a missing anchor; it falls through to the page and appends anyway,
        // the "never 'nowhere'" rule). The reachable causes are structural: a
        // fragment that would not parse, an anchor that no longer exists. So it
        // blamed the member for a failure that was ours and prescribed an
        // action that would not have helped.
        //
        // 49 call sites share this one guard, so the copy must not name a cause
        // it cannot know. It states WHAT happened and offers the one recovery
        // that always applies, instead of guessing WHY.
        setOpError('That change could not be applied. Reload and try again.');
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
        touchedBlockIds,
      );
    },
    [artifactPath, file, writeAndAdvance, resolvedMode],
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
    (
      kind: 'figure' | 'table' | 'chart' | 'component',
      path: string,
      pin?: string | null,
    ): string | null => {
      const base = vocabulary?.blocks.find((b) => b.kind === kind)?.fragment;
      if (!base) return null;
      const rel = relPath(path);
      return base
        .replace(/data-ref="[^"]*"/, `data-ref="${rel}"`)
        .replace(/data-ref-rev="[^"]*"/, `data-ref-rev="${pin ?? ''}"`);
    },
    [vocabulary],
  );
  // ADR-456 W1: N cited images land as ONE block, one revision. Pins are keyed
  // by the RELATIVE path the fragment will carry, so the lookup inside
  // galleryFragment matches what it stamps. ADR-581 D4 — two multi-pick kinds
  // now (gallery + logo-row), same figure-per-image construction, so the one
  // prototype-cloning builder serves both; the kind picks the base fragment.
  const citedMultiFragment = useCallback(
    (kind: 'gallery' | 'logo-row', paths: string[], pins?: Record<string, string | null>): string | null => {
      const base = vocabulary?.blocks.find((b) => b.kind === kind)?.fragment;
      if (!base) return null;
      const relPins: Record<string, string | null> = {};
      for (const p of paths) relPins[relPath(p)] = pins?.[p] ?? null;
      return galleryFragment(base, paths.map(relPath), relPins);
    },
    [vocabulary],
  );
  const handleAddArrangement = useCallback(
    (fragment: string, label: string) => {
      const p = applyOp(
        (html) => insertArrangement(html, fragment, anchor),
        `${app.label}: add ${label}`,
      );
      // ADR-520 D1 — the stage follows the new page (it lands after the
      // anchored page; unanchored it appends, which the restore keeps showing
      // only if the member was already on the tail — so name it explicitly).
      if (anchor.slideIndex != null || anchor.pageIndex != null) {
        const at = (anchor.slideIndex ?? anchor.pageIndex ?? 0) + 1;
        setScrollToSlide((s) => ({ index: at, nonce: (s?.nonce ?? 0) + 1 }));
      }
      return p;
    },
    [applyOp, anchor],
  );
  const handleApplyArrangement = useCallback(
    async (a: Pick<StudioArrangement, 'fragment' | 'label' | 'areas' | 'slug'>) => {
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
      const slotRoles = Object.fromEntries(a.areas.map((s) => [s.name, s.role]));
      const pageNoun = template === 'deck' ? 'slide' : 'section';

      // The planned path. Only worth a metered call when there is content to
      // place AND somewhere to put it — an empty page or a slotless target is
      // pure mechanism, and paying a judgment for it would be waste.
      if (file?.content && a.areas.length > 0) {
        const blocks = blocksForPlan(file.content, anchor);
        if (blocks && blocks.length > 0) {
          // The content BEFORE the preview touched anything. Both settle paths
          // compute from this, never from live state: the preview has already
          // advanced the override, so re-applying an arrangement on top of it
          // would arrange an arranged page.
          const preArrangeHtml = file.content;
          // ── ADR-524 D4 — preview mechanically, settle to the judgment ─────
          // ADR-466 P8 said pixels never wait for the network; the planner was
          // the one gesture still doing so, because a judgment (not a write)
          // sat in front of it. The member watched a spinner for 2-4s on a
          // VISUAL operation while the surface already held enough to show
          // them something: the mechanical ladder that is ALREADY this path's
          // fallback. So run it now, as pure view state, and settle to the
          // plan when it lands.
          //
          // The preview is NEVER written (ADR-209: no revision nobody
          // authored, and one gesture must not produce two). It paints the
          // override only; the write door is reached exactly once, below,
          // with whichever result settles.
          const previewed = applyArrangement(file.content, a.fragment, anchor, slotRoles);
          if (previewed) {
            setLocalOverride((cur) => ({
              anchorHead: loadedFile?.head_version_id ?? null,
              content: previewed.html,
              headVersionId: cur?.headVersionId ?? liveRef.current?.head ?? '',
            }));
          }
          setPlanning(true);
          try {
            const { placements } = await api.studio.planArrangement({
              blocks,
              areas: a.areas.map((s) => ({ name: s.name, role: s.role, place: s.place })),
              arrangement: a.slug,
            });
            if (placements) {
              // Settle to the judgment. `applyOp` computes from LIVE state
              // inside the write queue, and the preview advanced `liveRef` —
              // so compute the plan from the PRE-preview content instead, or
              // the arrangement would be applied twice.
              return await applyOp(
                () => applyArrangementPlan(preArrangeHtml, a.fragment, anchor, placements),
                `${app.label}: change arrangement to ${a.label}`,
              );
            }
          } catch {
            /* the planner is unreachable — the mechanical ladder still works */
          } finally {
            setPlanning(false);
          }
          // No plan (refused / unreachable / exhausted balance): the preview IS
          // the result — ADR-479's existing degraded path, now reached without
          // the member having waited to discover it. Land it as the one write.
          if (previewed) {
            return await applyOp(
              () => applyArrangement(preArrangeHtml, a.fragment, anchor, slotRoles),
              `${app.label}: change arrangement to ${a.label}`,
            );
          }
        }
      }

      if (file?.content && !applyArrangement(file.content, a.fragment, anchor, slotRoles)) {
        const set = vocabulary?.arrangements?.[template] ?? [];
        const receiver =
          set.find((x) => x.slug === 'content' && x.areas.length > 0) ??
          set.find((x) => x.areas.length > 0);
        if (receiver) {
          return applyOp(
            (html) => applyArrangementMovingContent(html, a.fragment, anchor, receiver.fragment),
            `${app.label}: change to ${a.label} — content moved to a new ${receiver.label.toLowerCase()} ${pageNoun}`,
          );
        }
        setOpError(
          `"${a.label}" has no place for this ${pageNoun}'s content — move or delete the blocks first.`,
        );
        return Promise.resolve();
      }
      return applyOp(
        (html) => applyArrangement(html, a.fragment, anchor, slotRoles),
        `${app.label}: change arrangement to ${a.label}`,
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
  // ADR-519 D2.1 — how many authored groups a re-arrange would dissolve. Paid
  // at the same seam and for the same reason as carriedCount: the galleries
  // say it where the choice is made, before the gesture, never after.
  const groupCount = useMemo(
    () => (file?.content ? countGroupsOnPage(file.content, anchor) : null),
    [file, anchor],
  );

  // ── ADR-453: the property layer + the structural verbs (Design tab) ──────
  const handleSetToken = useCallback(
    (grain: 'block' | 'page' | 'document', key: string, value: string | null) => {
      // ADR-541 D3 — a block-flow token (align/indent) over a live multi-block
      // range reaches EVERY covered block as one revision. Whether a token
      // spans is read off its SERVED grain, never a hardcoded key list (the
      // ADR-536 rule); box/media tokens keep their single anchor.
      const spans =
        grain === 'block' &&
        rangeBlockIds.length > 1 &&
        (vocabulary?.tokens.find((t) => t.key === key)?.grains ?? []).includes('flow');
      if (spans) {
        return applyOp(
          (html) => setTokenMany(html, rangeBlockIds, key, value),
          value == null
            ? `${app.label}: clear ${key} on ${rangeBlockIds.length} blocks`
            : `${app.label}: set ${key} to ${value} on ${rangeBlockIds.length} blocks`,
          // ADR-547 D2 — declare the span, so all N reach the live DOM.
          rangeBlockIds,
        );
      }
      return applyOp(
        (html) => setToken(html, { grain, anchor }, key, value),
        value == null ? `${app.label}: clear ${key}` : `${app.label}: set ${key} to ${value}`,
        // ADR-547 D2 — a BLOCK-grain token touches the anchored block, so it must
        // say so; page/document tokens live on the artifact root, which no flow
        // commit reports, so they declare nothing.
        grain === 'block' ? (anchor.blockId ?? null) : null,
      );
    },
    [applyOp, anchor, rangeBlockIds, vocabulary],
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
        value == null ? `${app.label}: even columns` : `${app.label}: columns ${value}`,
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

  /** ADR-544 D4 — the served kind→label map, threaded to every surface that
   *  names a block: the canvas runtime (via projection), the breadcrumb, and
   *  the pane. useMemo for the same reason as `measureBounds` directly above —
   *  it is a projection input, and a fresh object every render would re-inject
   *  the runtime and reload the frame on every keystroke. */
  const blockLabels = useMemo(() => {
    const rows = vocabulary?.blocks ?? [];
    if (!rows.length) return undefined;
    const out: Record<string, string> = {};
    rows.forEach((b) => {
      if (b.label) out[b.kind] = b.label;
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
        `${app.label}: ${blockId} ${parts.join(' ') || 'geometry'}`,
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
        `${app.label}: ${resized ? 'resized' : 'moved'} ${moves.length} blocks together`,
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
        `${app.label}: clear ${id} ${key === 'w' ? 'width' : 'height'}`,
      );
    },
    [applyOp, selection, geometrySpecs],
  );
  // ADR-520 D3 — numeric measure entry: the drag's keyboard twin. Same
  // id-addressed op, same served spec, same two-clamp (setMeasure clamps at
  // the write; the field clamps the input). Works on blocks AND staged
  // containers (ADR-511 D5 — the op never asked for a kind).
  const handleSetMeasureValue = useCallback(
    (key: 'w' | 'h' | 'x' | 'y', value: number) => {
      const id = selection?.blockId;
      const specs = geometrySpecs();
      const s = specs?.[key];
      if (!id || !s) return;
      void applyOp(
        (html) => setMeasure(html, id, key, value, s),
        `${app.label}: set ${id} ${key} ${Math.round(value)}${s.unit}`,
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
      `${app.label}: return ${id} to flow`,
    );
  }, [applyOp, selection, geometrySpecs]);
  // ADR-511 D4 + ADR-516 D1 — layout is ONE mechanism: bounded plain-CSS
  // presets on a selected structural container (id-addressed) OR on the
  // selected PAGE (anchor-addressed — the page is a container). One revision.
  const handleContainerLayout = useCallback(
    (layout: Record<string, string | null>) => {
      const id = selection?.blockId ?? null;
      const anchor = {
        blockId: null,
        slideIndex: selection?.slideIndex ?? null,
        pageIndex: selection?.pageIndex ?? null,
      };
      if (!id && anchor.slideIndex == null && anchor.pageIndex == null) return;
      void applyOp(
        (html) => setContainerLayout(html, id, layout, anchor),
        id
          ? `${app.label}: layout ${id} container`
          : `${app.label}: layout page ${anchor.slideIndex ?? anchor.pageIndex}`,
      );
    },
    [applyOp, selection],
  );
  const handleBlockVerb = useCallback(
    (verb: StructVerb) => {
      const id = selection?.blockId;
      if (!id) return;
      // ADR-541 D4 — a verb over MANY takes the set. When the ⇧-click set
      // holds more than one object AND the acting subject is a member of it,
      // delete/duplicate expand to the whole set as ONE revision (one ⌘Z).
      // The old behavior — ⌫ over five selected objects deleting one,
      // silently — was the data-loss-shaped defect the audit named. Move
      // up/down stay single-subject: document order gives a set no one
      // answer, so they act on the clicked block alone.
      // (Ranges never reach here: ⌫ in flow text is typing, and the runtime
      // only posts object-tier key verbs.)
      const set = groupIds.length > 1 && groupIds.includes(id) ? groupIds : null;
      if (verb === 'delete') {
        if (set) {
          void applyOp(
            (html) => deleteBlocks(html, set),
            `${app.label}: delete ${set.length} blocks`,
          );
        } else {
          void applyOp((html) => deleteBlock(html, id), `${app.label}: delete ${id} block`);
        }
        onPointClear();
      } else if (verb === 'duplicate') {
        if (set) {
          void applyOp(
            (html) => duplicateBlocks(html, set),
            `${app.label}: duplicate ${set.length} blocks`,
          );
        } else {
          void applyOp((html) => duplicateBlock(html, id), `${app.label}: duplicate ${id} block`);
        }
      } else {
        void applyOp((html) => moveBlock(html, id, verb), `${app.label}: move ${id} block ${verb}`);
      }
    },
    [applyOp, selection, groupIds, onPointClear],
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

  /** ADR-519 D4.1 — align / distribute over the ⇧-click SET. The one control
   *  whose subject genuinely IS the set, which is why it is the one thing the
   *  pane mounts over a multi-selection while every single-subject section
   *  withdraws.
   *
   *  Geometry is read from the SUBSTRATE (`data-x/y/w/h`, percentages of the
   *  frame — ADR-461's two-clamp measures), never from the DOM rects in the
   *  iframe: the substrate is what the op writes, so computing from anything
   *  else would align to one coordinate space and write in another. Members
   *  without geometry are SKIPPED, not defaulted to 0 — an in-flow block has no
   *  x/y, and inventing one would fling it to the frame's corner.
   *
   *  Writes through the existing `setGeometryMany`: one gesture, one revision,
   *  no new op (ADR-462 D1). */
  const setGeometryOf = useCallback(
    (
      compute: (
        boxes: Array<{ id: string; x: number; y: number; w: number; h: number }>,
      ) => Array<{ blockId: string; geo: { x?: number; y?: number } }>,
      describe: string,
    ) => {
      const specs = geometrySpecs();
      if (!specs || !file?.content || groupIds.length < 2) return;
      const doc = new DOMParser().parseFromString(file.content, 'text/html');
      const num = (el: Element, a: string) => {
        const v = el.getAttribute(a);
        if (v == null) return null;
        const n = parseFloat(v);
        return Number.isFinite(n) ? n : null;
      };
      const boxes = groupIds
        .map((id) => {
          const el = doc.querySelector(`[data-block-id="${CSS.escape(id)}"]`);
          if (!el) return null;
          const x = num(el, 'data-x');
          const y = num(el, 'data-y');
          if (x == null || y == null) return null; // in flow — not positionable
          return { id, x, y, w: num(el, 'data-w') ?? 0, h: num(el, 'data-h') ?? 0 };
        })
        .filter((b): b is { id: string; x: number; y: number; w: number; h: number } => !!b);
      if (boxes.length < 2) return; // nothing to align a set against
      const moves = compute(boxes);
      if (!moves.length) return;
      void applyOp(
        (html) => setGeometryMany(html, moves, specs),
        `${app.label}: ${describe} ${boxes.length} objects`,
      );
    },
    [file, groupIds, applyOp, geometrySpecs],
  );

  const handleAlignMany = useCallback(
    (edge: 'left' | 'hcenter' | 'right' | 'top' | 'vcenter' | 'bottom') => {
      // Align to the SET's own bounding box — the Figma/PowerPoint default, and
      // the only frame-independent answer (aligning to the slide would move the
      // whole set, which is a different intent the member did not express).
      setGeometryOf((boxes) => {
        const minX = Math.min(...boxes.map((b) => b.x));
        const maxR = Math.max(...boxes.map((b) => b.x + b.w));
        const minY = Math.min(...boxes.map((b) => b.y));
        const maxB = Math.max(...boxes.map((b) => b.y + b.h));
        return boxes.map((b) => {
          switch (edge) {
            case 'left':
              return { blockId: b.id, geo: { x: minX } };
            case 'right':
              return { blockId: b.id, geo: { x: maxR - b.w } };
            case 'hcenter':
              return { blockId: b.id, geo: { x: (minX + maxR) / 2 - b.w / 2 } };
            case 'top':
              return { blockId: b.id, geo: { y: minY } };
            case 'bottom':
              return { blockId: b.id, geo: { y: maxB - b.h } };
            default:
              return { blockId: b.id, geo: { y: (minY + maxB) / 2 - b.h / 2 } };
          }
        });
      }, `align ${edge}`);
    },
    [setGeometryOf],
  );

  const handleDistributeMany = useCallback(
    (axis: 'h' | 'v') => {
      // Even GAPS between edges, not even centres: the conventional reading, and
      // the one that looks right when the boxes differ in size. The two extremes
      // hold still and everything between them is re-spaced.
      setGeometryOf((boxes) => {
        if (boxes.length < 3) return []; // with two, their spacing IS the spacing
        const pos = (b: (typeof boxes)[number]) => (axis === 'h' ? b.x : b.y);
        const size = (b: (typeof boxes)[number]) => (axis === 'h' ? b.w : b.h);
        const sorted = [...boxes].sort((a, b) => pos(a) - pos(b));
        const first = sorted[0];
        const last = sorted[sorted.length - 1];
        const span = pos(last) + size(last) - pos(first);
        const totalSize = sorted.reduce((s, b) => s + size(b), 0);
        const gap = (span - totalSize) / (sorted.length - 1);
        let cursor = pos(first);
        return sorted.map((b) => {
          const at = cursor;
          cursor += size(b) + gap;
          return { blockId: b.id, geo: axis === 'h' ? { x: at } : { y: at } };
        });
      }, `distribute ${axis === 'h' ? 'horizontally' : 'vertically'}`);
    },
    [setGeometryOf],
  );

  const pasteAfter = useCallback(
    (after: string | null) => {
      const html = blockClip.current;
      if (!html) return;
      // Through the SAME door as every other insert — a fresh id is stamped so
      // a paste is a new block, never a second element wearing one address.
      void applyOp(
        (src) => pasteBlock(src, html, after),
        `${app.label}: paste block${after ? ` after ${after}` : ''}`,
      );
    },
    [applyOp],
  );

  const menuCopy = useCallback(() => copyBlock(ctxMenu?.blockId ?? null), [copyBlock, ctxMenu]);
  const menuPaste = useCallback(() => pasteAfter(ctxMenu?.blockId ?? null), [pasteAfter, ctxMenu]);

  // D10: the selected block's keyboard. Every verb already exists — the key is
  // a third entrance (after the menu and the Design tab), never a new op.
  const handleKeyVerb = useCallback(
    (verb: 'copy' | 'paste' | 'duplicate' | 'delete' | 'up' | 'down', blockId: string) => {
      if (verb === 'copy') return copyBlock(blockId);
      if (verb === 'paste') return pasteAfter(blockId);
      // ADR-541 D4 — the keyboard was the set-blind entrance: ⌫ over a five-
      // object ⇧-click set deleted ONE object, silently (the runtime keys off
      // its primary alone, correctly — the SET is parent state, so the parent
      // is where the verb widens). Delete/duplicate take the whole set as one
      // revision when the keyed block is a member of it.
      const set = groupIds.length > 1 && groupIds.includes(blockId) ? groupIds : null;
      if (verb === 'duplicate') {
        if (set) {
          void applyOp(
            (html) => duplicateBlocks(html, set),
            `${app.label}: duplicate ${set.length} blocks`,
          );
          return;
        }
        void applyOp((html) => duplicateBlock(html, blockId), `${app.label}: duplicate ${blockId} block`);
        return;
      }
      // ADR-526 D3 — ⌥↑/⌥↓, the structure-tier reorder door. The SAME moveBlock
      // the pane and menu call on paged media (one op, N entrances — ADR-511
      // D5), never a second write path.
      //
      // This branch is explicit and precedes the delete fallthrough on purpose:
      // the handler ends in an UNGUARDED deleteBlock, so a verb that reached
      // here without its own branch would silently delete the member's block.
      if (verb === 'up' || verb === 'down') {
        void applyOp((html) => moveBlock(html, blockId, verb), `${app.label}: move ${blockId} block ${verb}`);
        return;
      }
      if (set) {
        void applyOp((html) => deleteBlocks(html, set), `${app.label}: delete ${set.length} blocks`);
      } else {
        void applyOp((html) => deleteBlock(html, blockId), `${app.label}: delete ${blockId} block`);
      }
      onPointClear();
    },
    [copyBlock, pasteAfter, applyOp, groupIds, onPointClear],
  );

  // Turn into / Re-arrange have HOMES already (the Design tab's block + page
  // scopes). The menu row is a doorway to them, not a second implementation —
  // which is exactly ADR-462 D1, and why neither needs new logic here.

  // D6: both AI rows SEED and send nothing. The seeds differ only in how much
  // they pre-fill; the member finishes the sentence and presses enter.
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
        void applyOp((html) => deletePage(html, anchor), `${app.label}: delete ${noun}`);
        onPointClear();
      } else if (verb === 'duplicate') {
        void applyOp((html) => duplicatePage(html, anchor), `${app.label}: duplicate ${noun}`);
        // ADR-520 D1 — the stage follows the copy (it lands right after the
        // original; on the one-slide stage an unfollowed duplicate is
        // invisible feedback).
        const at = (anchor.slideIndex ?? anchor.pageIndex ?? 0) + 1;
        setScrollToSlide((s) => ({ index: at, nonce: (s?.nonce ?? 0) + 1 }));
      } else {
        void applyOp((html) => movePage(html, anchor, verb), `${app.label}: move ${noun} ${verb}`);
      }
    },
    [applyOp, anchor, template, onPointClear],
  );
  // The PAGE grain's keyboard — a third entrance to `deletePage`, never a
  // second implementation (the ADR-511 D5 shape the block verbs already use).
  //
  // The gap this closes: the click ladder's miss-branch and the Esc-walk both
  // SELECT a page, but the runtime's key handler returned early on the missing
  // block id, and the parent's only entrance to the page verb was the Design
  // tab. So a member who framed a slide and pressed Delete got silence — the
  // gesture the medium advertises, refused without a word.
  //
  // Takes the indices the runtime REPORTED rather than reading the ambient
  // anchor: the anchor is the same page today, but a verb that addresses "the
  // page the keystroke was about" must say so, not infer it from surrounding
  // state that another gesture could move first.
  const handlePageKeyVerb = useCallback(
    (verb: 'delete', slideIndex: number | null, pageIndex: number | null) => {
      if (verb !== 'delete') return;
      if (slideIndex == null && pageIndex == null) return;
      const noun = template === 'deck' ? 'slide' : 'section';
      void applyOp(
        (html) => deletePage(html, { blockId: null, slideIndex, pageIndex }),
        `${app.label}: delete ${noun}`,
      );
      onPointClear();
    },
    [applyOp, template, onPointClear],
  );
  // The design-system Apply/Remove (ADR-449 D5 homed): resolve the composed
  // MARKED skin element server-side, land it as ONE mechanical revision.
  const handleApplyDesignSystem = useCallback(
    async (manifestPath: string) => {
      const res = await api.studio.resolveDesignSystem(manifestPath);
      await applyOp(
        (html) => applySkin(html, res.skin_element),
        `${app.label}: apply design system ${res.name}`,
      );
    },
    [applyOp],
  );
  const handleRemoveDesignSystem = useCallback(
    () => void applyOp((html) => removeSkin(html), `${app.label}: remove design system`),
    [applyOp],
  );
  // Container-scoped adds (the Design tab's container scope + the role-gated
  // add-here) — ADR-511 Phase 2: addressed by IDENTITY, never by slot name.
  const insertProseInContainer = useCallback(
    (containerId: string, regionName: string | null) => {
      const proseFragment = vocabulary?.blocks.find((b) => b.kind === 'prose')?.fragment;
      if (!proseFragment) return;
      // "+ Add text" adds TEXT. The prose block's registry markup is
      // `<h2>Heading</h2><p>…</p>` — the right default for the palette (where
      // the member picked "Text" as a section unit) and the wrong one here:
      // clicking an empty region produced a heading nobody asked for. Strip
      // the heading for this gesture; the member can Turn into one at will.
      //
      // The registry is NOT changed — the lane and the palette share that
      // markup, and this is a property of the ADD GESTURE, not of the block.
      const bare = proseFragment.replace(/<h[1-6][^>]*>.*?<\/h[1-6]>/i, '');
      void applyOp(
        (html) => insertIntoContainer(html, bare, containerId),
        `${app.label}: add text to ${regionName ?? containerId}`,
      );
    },
    [applyOp, vocabulary],
  );
  const insertImageInContainer = useCallback(
    (path: string, containerId: string) => {
      const base = vocabulary?.blocks.find((b) => b.kind === 'figure')?.fragment;
      if (!base) return;
      const rel = relPath(path);
      const fragment = base.replace(/data-ref="[^"]*"/, `data-ref="${rel}"`);
      void applyOp(
        (html) => insertIntoContainer(html, fragment, containerId),
        `${app.label}: insert image ${rel}`,
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
      //
      // ADR-524 D2: reload:false was never enough on its own. The canvas re-
      // projects on every CONTENT change, so this "invisible" save still swapped
      // srcDoc and re-parsed the document a tick later. Naming the block makes
      // it patchable, which suppresses that re-projection. The runtime skips a
      // patch aimed at the block being edited, so a live caret is never
      // disturbed — the DOM there already shows what the member typed.
      void writeAndAdvance(
        (liveHtml) => editBlockText(liveHtml, blockId, newInner)?.html ?? null,
        `${app.label}: edit ${blockId} block`,
        false,
        blockId,
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
  // ADR-560 D1 — the flow commit is the MODEL's serialization (canonical,
  // idempotent, gate-held). The legacy editFlowRegion lane — the whole-body
  // iframe snapshot plus the two refusal guards — is deleted with the iframe
  // editing path (D8): with one writer there is nothing stale to refuse.
  const onFlowEdit = useCallback(
    (_selector: string, newInner: string) => {
      if (!file?.content) return;
      void writeAndAdvance(
        (liveHtml) => {
          const cur = readRegionInner(liveHtml);
          if (cur == null || cur === newInner) return null; // no-op — no revision
          return replaceRegionInner(liveHtml, newInner);
        },
        `${app.label}: edit document`,
        false,
      );
    },
    [file, writeAndAdvance, app.label],
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
        `${app.label}: add block`,
        false, // the override re-projects; onLoad re-commands the caret
      ).then((ok) => {
        if (ok && newId) {
          setEditingBlockId(newId); // caret into the new block once it projects
        }
      });
    },
    [file, vocabulary, writeAndAdvance],
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
        `${app.label}: split block`,
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
        `${app.label}: merge block`,
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
  // ── ADR-613 — the judged act's anchor, reported by the runtime ────────
  // The one thing Slides lacked: a selection RECT. `StudioSelection` carries
  // identity and never geometry, and every other iframe message carries a
  // pointer POINT (which ADR-612 D1 refuses) or nothing. The runtime posts the
  // visual box; StudioCanvas maps it to parent-page coordinates.
  const [selRect, setSelRect] = useState<{
    rect: {
      left: number; top: number; right: number; bottom: number;
      contentLeft: number; contentRight: number;
    };
    grain: string | null;
  } | null>(null);
  const onSelectionRect = useCallback(
    (
      rect: {
        left: number; top: number; right: number; bottom: number;
        contentLeft: number; contentRight: number;
      } | null,
      grain: string | null,
    ) => setSelRect(rect ? { rect, grain } : null),
    [],
  );

  // ── ADR-613 — the judged act, one gesture at the selection ────────────
  // The grain question this surface has and Text does not: a text RANGE inside
  // a block and the BLOCK itself are different targets, and ADR-612 D2's rule
  // is that whatever the chip names is what gets anchored. The runtime tells
  // us which it reported, so the noun and the anchor are decided together and
  // cannot drift — the member never gets a block rewritten when they meant
  // three words.
  const gestureTarget = useMemo(() => {
    if (!selRect || !selection) return null;
    const isRange = selRect.grain === 'range';
    const kind = selection.blockKind ?? 'content';
    return {
      noun: isRange ? 'the selection' : `the ${kind} block`,
      label: isRange ? 'selection' : kind,
      // A range is addressed by the block that holds it — the runtime has no
      // source offsets for HTML, so `block_id` IS this medium's address
      // (ADR-609 D2). The noun still says "the selection" because that is what
      // the member has, and the frame carries the excerpt to narrow it.
      blockId: selection.blockId ?? null,
    };
  }, [selRect, selection]);

  // ADR-612 D4 in THIS medium — the act says it is working, and cannot get
  // stuck saying so. Slides shipped the gesture without this, so a member who
  // clicked Rewrite and pressed Send watched the door sit there reading
  // "Rewrite" while a turn ran unseen; the Text half had already established
  // that vanishing (or silence) at the click makes the act feel like it went
  // nowhere. The click only ARMS — a seed is not a turn (the member may still
  // edit the intent, dismiss the chip, or never send) — and the lane's
  // `onSeededTurn` is what promotes armed → pending.
  const armedRewriteRef = useRef(false);
  const [pendingRewrite, setPendingRewrite] = useState(false);
  /** A gesture target is waiting in the composer (clicked, not yet sent) — the
   *  door withdraws while it is. Same rule as Text's, same reason: a second
   *  click appends to one composer rather than starting a second rewrite. */
  const [seedHeld, setSeedHeld] = useState(false);
  useEffect(() => {
    if (!pendingRewrite) return;
    // A turn that answers WITHOUT writing (a refusal, a question back, an
    // error) must not leave the door saying "Rewriting…" for the session. The
    // ceiling is generous on purpose: a stuck-state release, never a timeout
    // on the turn itself.
    const t = setTimeout(() => setPendingRewrite(false), 180_000);
    return () => clearTimeout(t);
  }, [pendingRewrite]);

  const rewriteSelection = useCallback(() => {
    if (!gestureTarget) return;
    armedRewriteRef.current = true;
    // No prefill — the chip names the target and the typed seed carries the
    // instruction; see the note at Text's `rewriteSelection`.
    seedComposer('', {
      verb: 'rewrite',
      path: artifactPath ? relPath(artifactPath) : null,
      blockId: gestureTarget.blockId,
      label: gestureTarget.label,
      excerpt: selection?.text || null,
      pageIndex: selection?.slideIndex ?? selection?.pageIndex ?? null,
      range: null,
    });
    setRightTab('chat');
  }, [gestureTarget, selection, seedComposer, artifactPath]);

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
  // ADR-527 D4 — the pane's entrance to the runtime's `applyFmt`. Same nonce
  // shape as slashTake, and for the same reason: pressing the same button
  // twice must fire twice. The runtime restores the member's last live range
  // before applying (the pane steals focus, so the selection is gone by the
  // time this arrives) and does nothing when there was never a range.
  const [fmtCmd, setFmtCmd] = useState<{
    op: string;
    value: string | null;
    nonce: number;
  } | null>(null);
  const fmtNonce = useRef(0);
  const handleFormat = useCallback((op: string, value?: string | null) => {
    fmtNonce.current += 1;
    setFmtCmd({ op, value: value ?? null, nonce: fmtNonce.current });
  }, []);
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
    // ADR-539 D2 — the kind is a served string and `cites` rides beside it,
    // derived from the vocabulary row at the set site. The old hardcoded
    // union + PICKER_KINDS/CSV_KINDS memberships (five spellings of one set,
    // per the audit) are deleted: a kind opens this picker iff its row
    // declares a citation, and the citable list follows the citation's kind.
    kind: string;
    cites: 'source' | 'picture' | 'fragment';
    left: number;
    top: number;
    ctx: { blockId: string; beforeInner: string | null; afterInner: string | null; empty: boolean };
  } | null>(null);

  /** ADR-539 D1 — what this kind CITES, read off the served row. */
  const kindCites = useCallback(
    (kind: string): 'none' | 'source' | 'picture' | 'fragment' =>
      vocabulary?.blocks.find((b) => b.kind === kind)?.cites ?? 'none',
    [vocabulary],
  );

  // Land a fragment at a LOCATED insertion context (the caret/slash point):
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
        }, `${app.label}: insert ${label}`);
        return;
      }
      if (beforeInner !== null && afterInner !== null && afterInner.trim() !== '') {
        void applyOp(
          (html) => splitBlockAndInsert(html, blockId, beforeInner, afterInner, fragment),
          `${app.label}: insert ${label}`,
        );
        return;
      }
      void applyOp((html) => insertBlock(html, fragment, { blockId }), `${app.label}: insert ${label}`);
    },
    [applyOp],
  );

  // ── The MOUSE insert route on `paged` (deck / web) ──────────────────────
  // '/' is gone on paged (see the runtime's FLOW-only gate), so this is the
  // block-grain insert there. Two mounts — the toolbar button (discovery) and
  // the right-click row (located) — open the SAME menu and land through the
  // SAME ops the palette uses. One write path, three doors.
  const [insertMenu, setInsertMenu] = useState<{
    x: number;
    y: number;
    // The target is resolved AT OPEN TIME and named in the menu, so the member
    // is never guessing where the block will go.
    slot: string | null;
    blockId: string | null;
    slideIndex: number | null;
    pageIndex: number | null;
    label: string;
  } | null>(null);

  // Resolve where a paged insert lands, most specific first:
  //   1. a selected BLOCK   → after it (the located answer)
  //   2. a selected SLOT    → into it
  //   3. otherwise          → append to the current page/slide
  // Never "nowhere": a member who clicks Insert without selecting anything gets
  // the block on the page they are looking at, which is what appending means on
  // a paged surface. Mirrors the toolbar door's own caret ladder (ADR-506 D1).
  const resolveInsertTarget = useCallback(() => {
    const sel = selection;
    // ADR-522 D3, applied here: the SELECTION wins where it exists, and the
    // VIEWPORT fills where it doesn't. On a staged deck the member pages with
    // the navigator and selects nothing, so the viewport is the only signal
    // that says which slide is on screen — the focus declaration has read it
    // this way since D3, and the Properties pane names "SLIDE 2" from it.
    //
    // Without this the ladder's last rung resolved to all-null, and all-null is
    // NOT "the current page": `arrangedPageAt` returns null for it, so
    // `insertBlock` fell through to `defaultFlow`, which is the LAST slide of
    // the deck. On slide 2 of 10 the block landed on slide 10 — while the menu,
    // reading `nth == null`, promised "Insert into this slide". The label and
    // the landing named two different places, and the label was the one the
    // member believed.
    const viewIndex = template === 'deck' ? viewportPage : null;
    const viewPageIndex = template === 'deck' ? null : viewportPage;
    const slideIndex = sel?.slideIndex ?? viewIndex ?? null;
    const pageIndex = sel?.pageIndex ?? viewPageIndex ?? null;
    if (sel?.blockId) {
      return {
        slot: null, blockId: sel.blockId, slideIndex, pageIndex,
        // The label carries its OWN preposition. The header states the target
        // verbatim, so a branch that reads "after the stat" must not be handed
        // to a fixed "into" prefix — that composed "into after the stat", the
        // ungrammatical header the ADR-586 click-pass found on every
        // block-selected open (both the popover and the bottom sheet).
        label: sel.blockKind ? `after the ${sel.blockKind}` : 'after the selected block',
      };
    }
    if (sel?.slot) {
      return { slot: sel.slot, blockId: null, slideIndex, pageIndex, label: `into ${sel.slot}` };
    }
    const nth = (slideIndex ?? pageIndex);
    // Same derivation the toolbar's New-‹noun› uses (deck speaks "slide",
    // web speaks "section") — the chrome must not call one page two names.
    const noun = template === 'deck' ? 'slide' : 'section';
    return {
      slot: null, blockId: null, slideIndex, pageIndex,
      label: nth == null ? `into this ${noun}` : `into ${noun} ${nth + 1}`,
    };
    // `viewportPage` is a DEPENDENCY, not a closed-over constant — the sibling
    // gate test_adr522_focus_is_threaded_not_closed_over.py exists because this
    // exact value was once captured stale.
  }, [selection, template, viewportPage]);

  const openInsertMenu = useCallback(
    (x: number, y: number) => {
      // A door that opens onto NOTHING is indistinguishable from a dead button.
      // The menu returns null on an empty roster (correctly — "a menu with no
      // acts is not a menu"), so when the roster is empty because the fetch
      // FAILED, say so here rather than letting the press look ignored.
      if (vocabularyError && !vocabulary?.blocks.length) {
        setOpError('Insert is unavailable — the block list could not be loaded. Reload to retry.');
        return;
      }
      setInsertMenu({ x, y, ...resolveInsertTarget() });
    },
    [resolveInsertTarget, vocabularyError, vocabulary],
  );

  // ADR-586 D1 — ONE door on every medium: the toolbar's [+ Add] opens the
  // category menu on flow and on paged alike (the medium orders the
  // categories inside it; the '/' remains flow's LOCATED gesture, untouched).
  // The old flow fork — the button typing the '/' through a runtime
  // round-trip — is DELETED with its slash-invoke plumbing: the door needs no
  // caret, so it cannot mis-fire while the registry is still answering.
  const onInsertPressed = useCallback(
    (at: { x: number; y: number }) => {
      openInsertMenu(at.x, at.y);
    },
    [openInsertMenu],
  );

  // The pick lands through the EXISTING ops — insertBlock for every anchor
  // (a container anchor appends INTO it, ADR-511 Phase 2). The picker-backed kinds
  // (figure/table/gallery) and chart route exactly as the palette routes them,
  // so a cited insert behaves identically whichever door opened it.
  //
  // ADR-579 D6.a — ONE landing for every located pick: the toolbar verb menus
  // AND the right-click New/Add tiers resolve a target and land here. One
  // write path under every door, whichever chrome opened it.
  const landInsertPick = useCallback(
    (
      t: { blockId: string | null; slideIndex: number | null; pageIndex: number | null },
      anchor: { x: number; y: number },
      kind: string,
      label: string,
      fragment: string,
    ) => {
      // (ADR-538 D2 — the `chart` branch that seeded "author an SVG chart at
      // ./assets/…" is DELETED. A chart cites DATA now. ADR-539 D2 — a kind
      // is picker-backed iff its served row declares a citation; no list.)
      const menuCites = kindCites(kind);
      if (menuCites !== 'none') {
        setCitePicker({
          kind,
          cites: menuCites,
          left: anchor.x,
          top: anchor.y,
          // An empty ctx blockId means "not a located caret pick" — the cite
          // terminal falls through to the same anchor rules used here.
          ctx: { blockId: t.blockId ?? '', beforeInner: null, afterInner: null, empty: false },
        });
        return;
      }
      // (ADR-511 Phase 2: the slot-name branch is gone — a selected container
      // is a blockId anchor, and insertBlock appends INTO a container anchor.)
      void applyOp(
        (html) =>
          insertBlock(html, fragment, {
            blockId: t.blockId,
            slideIndex: t.slideIndex,
            pageIndex: t.pageIndex,
          }),
        `${app.label}: add ${label} block`,
      );
    },
    [applyOp, kindCites],
  );
  const onInsertMenuPick = useCallback(
    (kind: string, label: string, fragment: string) => {
      const t = insertMenu;
      setInsertMenu(null);
      if (!t) return;
      landInsertPick(t, { x: t.x, y: t.y }, kind, label, fragment);
    },
    [insertMenu, landInsertPick],
  );
  // ADR-586 D7 — the library pick: the gallery item IS the cited file, so the
  // fragment is built here (pin stamped) and lands through insertBlock at the
  // menu's resolved target — never through the picker, and never a collapse
  // to another kind (the ADR-538 D2 lesson).
  const onInsertMenuLibrary = useCallback(
    (path: string, pin: string | null) => {
      const t = insertMenu;
      setInsertMenu(null);
      if (!t) return;
      const fragment = citedFragment('component', path, pin);
      if (!fragment) return;
      void applyOp(
        (html) =>
          insertBlock(html, fragment, {
            blockId: t.blockId,
            slideIndex: t.slideIndex,
            pageIndex: t.pageIndex,
          }),
        `${app.label}: add component ${relPath(path)}`,
      );
    },
    [insertMenu, citedFragment, applyOp],
  );
  // The right-click New/Add tiers (ADR-579 D6.a): the target resolves at PICK
  // time through the same ladder the menu door uses, anchored at the
  // right-click point (so a cited pick's picker opens where the member was
  // already pointing).
  const ctxInsertKind = useCallback(
    (kind: string, label: string, fragment: string) => {
      const m = ctxMenu;
      if (!m) return;
      landInsertPick(resolveInsertTarget(), { x: m.x, y: m.y }, kind, label, fragment);
    },
    [ctxMenu, landInsertPick, resolveInsertTarget],
  );

  const onSlashTaken = useCallback(
    (blockId: string, beforeInner: string | null, afterInner: string | null) => {
      const p = pendingPick.current;
      pendingPick.current = null;
      if (!p) return;
      // (ADR-538 D2 — the chart-seeds-an-SVG branch is deleted here too; the
      // slash route reaches the same CSV picker as the palette route.
      // ADR-539 D2 — picker-backed iff the served row declares a citation.)
      const slashCites = kindCites(p.kind);
      if (slashCites !== 'none') {
        setCitePicker({
          kind: p.kind,
          cites: slashCites,
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
          `${app.label}: turn block into ${p.label}`,
          // ADR-547 D2 — declared, like every other block-touching op. This site
          // was MISSED on the first pass and the gate caught it, which is the
          // whole reason F1 enumerates by the OP rather than by the handler name.
          blockId,
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
          `${app.label}: add ${p.label} block`,
        );
        return;
      }
      void applyOp(
        (html) => insertBlock(html, p.fragment, { blockId }),
        `${app.label}: add ${p.label} block`,
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
      // ADR-538 D2 — the cited single-file kinds each keep their OWN kind
      // (the collapse to table-or-figure would silently land the wrong block
      // wherever a member picked). ADR-583 adds `component` to the ladder.
      const kind: 'figure' | 'table' | 'chart' | 'component' =
        cp.kind === 'table'
          ? 'table'
          : cp.kind === 'chart'
            ? 'chart'
            : cp.kind === 'component'
              ? 'component'
              : 'figure';
      const fragment = citedFragment(kind, path, pin);
      if (!fragment) return;
      const noun = kind === 'figure' ? 'image' : kind;
      landAtLocatedPoint(fragment, `${noun} ${relPath(path)}`, cp.ctx);
    },
    [citePicker, citedFragment, landAtLocatedPoint],
  );
  const onCitePickGallery = useCallback(
    (paths: string[], pins: Record<string, string | null>) => {
      const cp = citePicker;
      setCitePicker(null);
      if (!cp) return;
      // ADR-581 D4 — the multi terminal keeps the picked KIND (the ADR-538 D2
      // lesson next door: a collapse would silently land a GALLERY wherever a
      // member picked Logo row).
      const kind: 'gallery' | 'logo-row' = cp.kind === 'logo-row' ? 'logo-row' : 'gallery';
      const fragment = citedMultiFragment(kind, paths, pins);
      if (!fragment) return;
      const noun = kind === 'logo-row' ? 'logo row' : 'gallery';
      landAtLocatedPoint(fragment, `${noun} (${paths.length} images)`, cp.ctx);
    },
    [citePicker, citedMultiFragment, landAtLocatedPoint],
  );
  // ADR-456 W3: the page background — a cited image on the page element.
  const handleSetPageBackground = useCallback(
    (path: string) =>
      applyOp(
        (html) => setPageBackground(html, anchor, relPath(path)),
        `${app.label}: set page background ${relPath(path)}`,
      ),
    [applyOp, anchor],
  );
  const handleRemovePageBackground = useCallback(
    () => applyOp((html) => removePageBackground(html, anchor), `${app.label}: remove page background`),
    [applyOp, anchor],
  );

  // Turn-into from the Design tab (same op, selection-anchored).
  const turnBlockInto = useCallback(
    (blockId: string, kind: string, label: string, fragment: string) => {
      void applyOp(
        (html) => convertBlock(html, blockId, kind, fragment),
        `${app.label}: turn block into ${label}`,
        // ADR-547 D2 — the converted block reaches the live DOM. `convertBlock`
        // REPLACES the element (a new tag), but the block's id survives the
        // conversion by contract, so the patch still addresses it.
        blockId,
      );
    },
    [applyOp],
  );
  // ADR-541 D3 — a turn-into over a live multi-block range converts EVERY
  // covered block, one revision (per-block legality per-block: citation
  // islands and same-shape no-ops are skipped inside convertBlocks). The span
  // is the subject even when nothing was clicked — the covered ids are the
  // range's own fact, not the primary's.
  const turnBlocksInto = useCallback(
    (blockIds: string[], kind: string, label: string, fragment: string) => {
      void applyOp(
        (html) => convertBlocks(html, blockIds, kind, fragment),
        `${app.label}: turn ${blockIds.length} blocks into ${label}`,
        // ADR-547 D2 — every converted block, declared. `convertBlocks` skips
        // citation islands and same-shape no-ops internally, and a block that did
        // not change simply patches to itself.
        blockIds,
      );
    },
    [applyOp, app.label],
  );
  const handleTurnInto = useCallback(
    (kind: string, label: string, fragment: string) => {
      if (rangeBlockIds.length > 1) {
        turnBlocksInto(rangeBlockIds, kind, label, fragment);
        return;
      }
      const blockId = selection?.blockId;
      if (!blockId) return;
      turnBlockInto(blockId, kind, label, fragment);
    },
    [turnBlockInto, turnBlocksInto, rangeBlockIds, selection],
  );
  // ADR-479 D5 — the menu's Turn into acts on the RIGHT-CLICKED block, which is
  // not necessarily the selected one (right-click selects, but the op must not
  // depend on that ordering). Same `convertBlock` op, explicit target.
  // ADR-541 D4 — unless a live range covers MORE than one block and the
  // right-clicked block is among them: then the menu's pick takes the span,
  // exactly as the pane's does (one derivation of "how many", two doors).
  const menuTurnInto = useCallback(
    (kind: string, label: string, fragment: string) => {
      const blockId = ctxMenu?.blockId;
      if (!blockId) return;
      if (rangeBlockIds.length > 1 && rangeBlockIds.includes(blockId)) {
        turnBlocksInto(rangeBlockIds, kind, label, fragment);
        return;
      }
      turnBlockInto(blockId, kind, label, fragment);
    },
    [turnBlockInto, turnBlocksInto, rangeBlockIds, ctxMenu],
  );

  // ADR-447: canvas view controls (view-only, never touch the file) + pane
  // switching at the narrow rungs (one pane at a time: nav · canvas · chat).
  const [zoom, setZoom] = useState(1);
  const [activePane, setActivePane] = useState<'nav' | 'canvas' | 'chat'>('canvas');

  // ── The collapse ladder (2026-08-12) ──────────────────────────────────────
  // The workbench measures ITS OWN container, not the window: a surface can be
  // narrow inside a roomy window (a 320px window on a 1440px monitor), and the
  // shell's viewport-wide `isMobile` cannot see that. `usePaneLadder` is the ONE
  // measured-container answer — Studio, Text, Desk and Chat all read it — and it
  // holds the ONE spelling of the
  // thresholds (lib/shell/surface-preferences.ts), which raw `md:` class strings
  // had been silently disagreeing with — measured live: at 820px the toolbar
  // painted 260px over the Properties column.
  // A CALLBACK ref, not an object ref: the workbench mounts on a LATER render
  // than this hook (the START state returns first), and an effect keyed on a
  // stable object ref runs once against a null node and never retries — the
  // rung then sits at its roomy default forever. See pane-layout.ts.
  const [setWorkbenchNode, wb] = usePaneLadder();
  const { threeColumn, sideIsOverlay, singlePane, fullLabels } = wb;
  // Pane state is per (surface, slot, workspace, user) — the id scopes the key.
  const { userId } = useSurfacePreferences();
  // Touch parity: a coarse pointer gets 44px targets (Apple/Google floor) while
  // desktop density is untouched. The CAPABILITY, not the width — a large tablet
  // has no mouse; a narrow desktop window still does (useCoarsePointer's own
  // distinction, which this surface previously ignored entirely).
  const coarsePointer = useCoarsePointer();


  // ADR-455: the navigator collapses (desktop) — a member reclaims the width
  // when the outline/strip isn't earning it.
  //
  // DEFAULT BY LAYOUT (operator ruling 2026-07-14): a DECK's slide strip is its
  // primary navigation (PowerPoint) → open by default. A DOCUMENT/ARTICLE
  // outline is a thin table-of-contents that doesn't earn its width for the
  // short-to-medium artifacts the Studio actually produces → COLLAPSED by
  // default. ADR-455 D4 resolving toward "gets out of the way" for documents
  // while the deck keeps its strip.
  //
  // Both chrome slots ride the ONE pane contract (`lib/shell/pane-layout.ts`):
  // show/hide + width + persistence, identical here, in Text and in Chat.
  //
  // The rail's RESTING answer depends on the medium, and is only knowable once
  // the artifact loads — `template` reads 'document' from the extract-fallback
  // before content arrives, so committing early would flash a deck's strip
  // closed→open. Handed to the slot as a MOVING default rather than written
  // after the fact: the slot follows it until the member chooses, and never
  // fights them afterwards. That replaces the old `navUserSet` latch, which held
  // the member's choice for the SESSION only — their next visit forgot it.
  const rail = usePaneSlot('studio', 'rail', userId, wb, {
    defaultShown: !!file?.content && isPaged,
  });
  // The side pane rests SHOWN: a member arriving at an artifact should see its
  // properties without hunting for them.
  const side = usePaneSlot('studio', 'side', userId, wb, { defaultShown: true });
  const navCollapsed = !rail.shown;
  const toggleNav = rail.toggle;
  const sideOpen = side.shown;
  // Escape withdraws the side pane while it is an OVERLAY — an overlay covers
  // the canvas and is therefore modal; a COLUMN is not, and Escape must not
  // reach across and close it (the member would have no idea what they hit).
  useEffect(() => {
    if (!sideIsOverlay || !sideOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') side.toggle();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [sideIsOverlay, sideOpen, side]);

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
      setActivePane('canvas'); // on mobile, jump to the canvas to see the slide
    },
    [template],
  );

  // Drag-to-reorder a slide in the navigator (PowerPoint). One mechanical
  // revision through the same write door as every op; the selection follows the
  // slide to its new index so the Design tab stays anchored to it.
  const reorderSlideFromNavigator = useCallback(
    (from: number, to: number) => {
      void applyOp((html) => movePageTo(html, from, to), `${app.label}: move slide ${from + 1} → ${to + 1}`);
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
        `${app.label}: reorder ${indices.length} ${noun}`,
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
        `${app.label}: delete ${indices.length} ${noun}`,
      );
      onPointClear();
    },
    [applyOp, template, onPointClear],
  );

  // ADR-455: a navigator pick selects a BLOCK (anchoring the Design tab)
  // and scrolls the canvas to it.
  const [scrollToBlock, setScrollToBlock] = useState<{ blockId: string; nonce: number } | null>(
    null,
  );

  // ADR-511 D3 — a structure-tree pick (container OR block) from the
  // navigator: same contract as the heading pick, generalized to any
  // addressable node. The canvas outline follows via selectedBlockId.
  const selectNodeFromNavigator = useCallback(
    (node: { blockId: string; label: string; kind: string | null }) => {
      setSelection({
        blockId: node.blockId,
        // The outline names a heading by its TAG (h1/h2/h3 — the level is the
        // kind there); the vocabulary's kind is `heading`. Normalize at the
        // seam so downstream readers see one vocabulary (the Typography ramp
        // gates on blockKind === 'heading').
        blockKind: node.kind && /^h[1-6]$/.test(node.kind) ? 'heading' : node.kind,
        slideIndex: null,
        pageIndex: null,
        slot: null,
        arrange: null,
        text: '',
        label: node.label,
        // ADR-526 D2 — a parent-side reach must declare the tier like every
        // other selection (ADR-525 D1), or the pane guesses for the frame
        // before the runtime's own point payload lands. Same rule as the
        // runtime's `tierOf`, reading the SAME exported kind list — never a
        // second copy of the rule. The outline passes a heading tag (h1/h2/h3),
        // which the ramp treats as `heading`; Contents passes real block kinds.
        tier: !node.kind
          ? 'structure'
          : layoutMode === 'flow' &&
              kindTier(
                vocabulary?.blocks,
                /^h[1-6]$/.test(node.kind) ? 'heading' : node.kind,
              ) === 'text'
            ? 'text'
            : 'object',
      });
      setEditingBlockId(null);
      setScrollToBlock((s) => ({ blockId: node.blockId, nonce: (s?.nonce ?? 0) + 1 }));
      setActivePane('canvas');
    },
    [],
  );

  // ── ADR-455: the file-verb completion (surface-bar ⋯) ────────────────────
  // Copy link — the member-facing deep link to this artifact (the workspace
  // is multi-member; distinct from the ADR-437 Share origin).
  const copyArtifactLink = useCallback(() => {
    if (!artifactPath) return;
    const url = `${window.location.origin}/desktop?${app.slug}.file=${encodeURIComponent(relPath(artifactPath))}`;
    void navigator.clipboard.writeText(url);
  }, [artifactPath]);
  // Share — OPENS THE SHARED DIALOG (ADR-529 D1). Studio no longer owns a
  // share implementation: its two-button popover is deleted (ADR-529 D4), and
  // the act it performed now lives in the one `ShareDialog` that every file
  // surface mounts. The header placement is unchanged — ADR-515 §2.0's
  // two-mount carve is correct and preserved (Share belongs beside Export as a
  // boundary act); what changes is that the header verb and the file-verb are
  // ONE component rather than two implementations of one idea.
  //
  // The dialog resolves the path itself, so no mode parameter crosses here —
  // the choice is made in the dialog, where the consequence is stated.
  const [shareTarget, setShareTarget] = useState<{ path: string; name: string } | null>(null);
  const shareArtifact = useCallback(() => {
    if (!artifactPath) return;
    setShareTarget({
      path: artifactPath,
      name: artifactPath.split('/').filter(Boolean).pop() || artifactPath,
    });
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

  // The AI-native reference (ADR-512 D5): the canonical yarnnn://workspace/…
  // handle any connected LLM resolves with the interop `open` verb (the
  // exact-version read) — complementing the /s/{token} membership link
  // (ADR-465). The handle is the kernel grammar; the sentence around it is
  // host guidance.
  const copyAiReference = useCallback(async () => {
    if (!artifactPath) throw new Error('No artifact open');
    await navigator.clipboard.writeText(
      formatAiReference(artifactPath, artifactDisplayName),
    );
  }, [artifactPath, artifactDisplayName]);
  // Duplicate — read the open artifact, write it at a -copy sibling through
  // the one mechanical door (never overwrite an existing copy), open the copy.
  // ADR-514 D1: the kernel owns duplicate. The pre-514 body lived here — a
  // browser-side `-copy` probe (TOCTOU-racy, capped at 5, `.html`-only) that
  // wrote no derived_from, leaving every duplicate an attribution orphan. The
  // shared verb resolves the name server-side and cites the source; the
  // surface's only job is to follow the copy (onAfterMutate re-points ?file).
  const duplicateArtifact = useCallback(() => {
    if (!artifactPath) return;
    organizeVerbs.onDuplicate({ path: artifactPath, name: artifactDisplayName });
  }, [artifactPath, artifactDisplayName, organizeVerbs]);

  // ADR-447 Phase 4, re-addressed by ADR-511 Phase 2: "+ Add" in an empty
  // region. The runtime carries the container's IDENTITY; the registry role
  // (looked up by the legacy names while they exist) routes media regions to
  // the Design tab's picker in container scope; everything else takes prose.
  const onAddHere = useCallback(
    (
      slot: string,
      slideIndex: number | null,
      pageIndex: number | null,
      arrange: string | null,
      containerId: string | null,
    ) => {
      if (!containerId) return; // an unaddressed region cannot take an op
      const role = vocabulary?.arrangements?.[template]
        ?.find((a) => a.slug === arrange)
        ?.areas.find((s) => s.name === slot)?.role;
      if (role === 'media') {
        setSelection({
          blockId: containerId,
          blockKind: null,
          slideIndex,
          pageIndex,
          slot,
          arrange,
          text: '',
          label: slot || 'group',
        });
        setEditingBlockId(null);
        setRightTab('design');
        return;
      }
      insertProseInContainer(containerId, slot || null);
    },
    [vocabulary, template, insertProseInContainer],
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
  // Four rungs of one width ladder (AUTHORING.md rule 15), measured off THIS
  // container rather than the window. Freddie's rail is suppressed here.
  //
  //   full        three columns — NAVIGATOR · CANVAS (toolbar + zoom) · SIDE
  //   condensed   three columns, verbs collapse to glyphs
  //   two-pane    canvas full-width; the SIDE pane becomes an overlay drawer
  //   single-pane one pane at a time (nav · canvas · chat), bottom tab bar
  //
  // `activePane` names which pane the tab bar has raised. It is read ONLY at
  // the single-pane rung — it was called `mobilePane`, a name that stopped
  // being true once the ladder gained a rung between phone and desktop.
  const navActive = activePane === 'nav';
  const canvasActive = activePane === 'canvas';
  const chatActive = activePane === 'chat';
  return (
    <div ref={setWorkbenchNode} className="relative flex h-full min-h-0 flex-col">
      {/* `relative` is LOAD-BEARING: the two-pane rung's side overlay + its
          scrim are `absolute inset-y-0 right-0` and must resolve against THIS
          row (the column band), not against a distant positioned ancestor. */}
      <div className="relative flex min-h-0 flex-1">
        {/* Left — the per-type navigator. A COLUMN at the three-column rungs; a
            full-width pane at the single-pane rung; withdrawn entirely at the
            two-pane rung, where the canvas needs the width more than the strip
            does (the ladder's rule: the canvas never yields).

            The strip's own width is member-set and persisted, but it is CLAMPED
            against the measured container below so a wide saved strip can never
            re-create the crush this ladder exists to prevent. */}
        {/* PAGED only: the navigator is container navigation (a slide strip),
            which only exists where the container IS the unit. A flow artifact's
            outline was a derived table of contents wearing a navigator's
            clothes — deleted with the mode split. */}
        {isPaged && (
          <div
            className={`relative shrink-0 flex-col border-r border-border ${
              threeColumn && !navCollapsed ? 'flex' : 'hidden'
            } ${singlePane && navActive ? '!flex w-full' : ''}`}
            // The slot clamps its own width against the measured container, so
            // a strip dragged to 520px on a wide monitor cannot carry that into
            // an 800px workbench and re-create the crush through member state.
            style={singlePane && navActive ? undefined : { width: rail.width }}
          >
            <PagedNavigator
              layout={template}
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
            />
            {/* The resize divider — drag to set the strip width (persisted). A
                hair-wide hit target over the right border. Only where the strip
                is a real COLUMN: at the single-pane rung it is a full-width pane
                with nothing to resize against, and a coarse pointer cannot hit a
                6px target anyway. */}
            {threeColumn && !coarsePointer && (
              <div
                onPointerDown={rail.startResize}
                role="separator"
                aria-orientation="vertical"
                title="Drag to resize the slide strip"
                className="absolute right-0 top-0 z-10 block h-full w-1.5 translate-x-1/2 cursor-col-resize hover:bg-primary/20 active:bg-primary/30"
              />
            )}
          </div>
        )}

        {/* Center — the toolbar + zoom over the canvas (renders, edits in place).
            THE CANVAS NEVER YIELDS: at every rung above single-pane this column
            is present and it is the last thing to lose width. */}
        <div
          className={`min-w-0 flex-1 flex-col ${
            !singlePane || canvasActive ? 'flex' : 'hidden'
          }`}
        >
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
            {isPaged && threeColumn && (
              <button
                type="button"
                onClick={toggleNav}
                title={`${navCollapsed ? 'Show' : 'Hide'} the slide strip`}
                aria-label={`${navCollapsed ? 'Show' : 'Hide'} the slide strip`}
                className={`ml-2 inline-flex shrink-0 items-center justify-center gap-1 rounded text-[11px] transition-colors hover:bg-muted/40 ${
                  coarsePointer ? 'h-11 w-11' : 'p-1'
                } ${navCollapsed ? 'text-muted-foreground/60' : 'text-muted-foreground'}`}
              >
                <PanelLeft className="h-3.5 w-3.5" />
              </button>
            )}
            <div className={`flex shrink-0 items-center gap-1 text-xs ${isPaged ? 'ml-1' : 'ml-2'}`}>
              <button
                type="button"
                onClick={() => setParam({ file: null })}
                title={`Back to ${app.label}`}
                className="text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
              >
                {/* ADR-482 D7: app-aware, matching the landing. The label is
                    the app's own declaration (ADR-518 D7) — no per-site slug
                    ternary to fall out of date when an app joins. */}
                {app.label}
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
                mode={resolvedMode}
                onInsert={onInsertPressed}
                // ADR-586 D6 — Update at the SELECTION'S grain: a selected
                // block opens the one block-acts menu (the same definition
                // the right-click renders), Update tier expanded.
                hasBlockSelection={!!selection?.blockId && !!selection?.blockKind}
                onUpdateBlock={openUpdateDoor}
                planning={planning}
                hasPageAnchor={
                  !!selection &&
                  (selection.blockId != null ||
                    selection.slideIndex != null ||
                    selection.pageIndex != null)
                }
                compact={!fullLabels}
                coarsePointer={coarsePointer}
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
                grammar). The Properties sections are deleted, not mirrored.
                ADR-529 D1: Share is now a trigger for the shared dialog — the
                popover it used to open is deleted; Export keeps its panel. */}
            <StudioShareExport
              share={shareArtifact}
              print={() => void exportPrint()}
              copyAiRef={copyAiReference}
              exportPng={app.slug === 'images' ? exportPng : undefined}
              compact={!fullLabels}
              coarsePointer={coarsePointer}
            />
            {/* The side pane's DOOR — at EVERY rung that has a side pane, not
                only where it is an overlay. Gating this on `sideIsOverlay` was
                the inversion: the overlay rung already dismisses on backdrop
                and Escape, while the COLUMN rung — the ordinary desktop — was
                the one with no way out, permanently spending 380px with no
                affordance to reclaim it. Hidden only at single-pane, where the
                bottom tab bar IS the switcher and a second control would be a
                second answer to one question. */}
            {!singlePane && (
              <button
                type="button"
                onClick={side.toggle}
                title={`${sideOpen ? 'Hide' : 'Show'} properties and chat`}
                aria-label={`${sideOpen ? 'Hide' : 'Show'} properties and chat`}
                aria-expanded={sideOpen}
                className={`mr-1 inline-flex shrink-0 items-center justify-center rounded border border-border text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground ${
                  coarsePointer ? 'h-11 w-11' : 'h-7 w-7'
                }`}
              >
                <PanelRight className="h-3.5 w-3.5" />
              </button>
            )}
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
          ) : loadError && !file ? (
            /* A real failure says so, and offers the retry — never "it doesn't
               exist", which reads as data loss. reloadKey is the same refetch
               the 409 path uses. */
            <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
              <p className="text-sm text-muted-foreground">
                Couldn’t load {relPath(artifactPath)}. The artifact is still there — the
                request failed.
              </p>
              <button
                type="button"
                onClick={() => setReloadKey((k) => k + 1)}
                className="rounded border border-border px-2.5 py-1 text-xs hover:bg-accent"
              >
                Try again
              </button>
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
              {/* ADR-560 D1/D4 — on flow the canvas IS the editor: the model
                  mounts in the parent (one writer, no iframe editing lane).
                  Gated on the vocabulary having LANDED: resolvedMode defaults
                  to 'flow' before it arrives, and mounting the model against
                  a deck-shaped document would canonicalize the wrong medium.
                  Paged (and the pre-vocabulary window) keeps StudioCanvas. */}
              {resolvedMode === 'flow' && vocabulary ? (
                <FlowEditor
                  ref={flowRef}
                  file={file}
                  artifactPath={artifactPath}
                  headingRungs={vocabulary.heading_rungs}
                  kinds={vocabulary.blocks.map((b) => b.kind)}
                  blockLabels={blockLabels}
                  zoom={zoom}
                  onPoint={onPoint}
                  onPointClear={onPointClear}
                  onRange={onRange}
                  selectedBlockId={selection?.blockId ?? null}
                  onFlowEdit={onFlowEdit}
                  onSlashOpen={onSlashOpen}
                  onSlashFilter={onSlashFilter}
                  onSlashClose={onSlashClose}
                  onSlashMove={onSlashMove}
                  onSlashEnter={onSlashEnter}
                  onSlashTaken={onSlashTaken}
                  slashTake={slashTake}
                  fmtCmd={fmtCmd}
                  scrollToBlock={scrollToBlock}
                  onScrollPos={onScrollPos}
                />
              ) : (
              <StudioCanvas
                file={file}
                artifactPath={artifactPath}
                onSelectionRect={onSelectionRect}
                onPoint={onPoint}
                onPointClear={onPointClear}
                onRange={onRange}
                editingBlockId={editingBlockId}
                selectedBlockId={selection?.blockId ?? null}
                onEdit={onEdit}
                mode={resolvedMode}
                measureBounds={measureBounds}
                blockLabels={blockLabels}
                onRefused={handleRefused}
                onEditExited={() => setEditingBlockId(null)}
                onEditEntered={(id) => setEditingBlockId(id)}
                onEnterBlock={onEnterBlock}
                onRatio={handleRatio}
                onGeometry={handleGeometry}
                onGeometryMany={handleGeometryMany}
                // ADR-519 D4.1 — the prop StudioCanvas has DECLARED and called
                // since 2026-07-24 while no parent passed it: the ⇧-click set
                // was built, moved and resized inside the iframe and then died
                // at the React boundary, so pane and chrome saw one block.
                onGroup={onGroup}
                onContextMenu={(t) => {
                  // A right-click opens COLLAPSED; only the toolbar's
                  // contextual Update pre-expands its tier (ADR-586 D6).
                  setCtxMenu(t);
                }}
                onKeyVerb={handleKeyVerb}
                onPageKeyVerb={handlePageKeyVerb}
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
                fmtCmd={fmtCmd}
                scrollToSlide={scrollToSlide}
                scrollToBlock={scrollToBlock}
                patch={patch}
                zoom={zoom}
                // ADR-520 D1 — a deck edits on the STAGE (one slide shown);
                // web stays a scroll (bands are a viewport medium, ADR-505).
                stage={template === 'deck'}
                onScrollPos={onScrollPos}
              />
              )}
              {/* AUTHORING.md Phase 3 §3 — the ancestor chain at the selection,
                  paged media only (flow's chain is caret → block → clear).
                  Selecting an ancestor rides the navigator's existing
                  selection paths — no new op, a new reach (rule 7). */}
              {/* ADR-544 D5.1 — the refusal, said where the gesture happened.
                  Transient (it answers a gesture, not a state) and it sits over
                  the canvas rather than in the pane, because the pane may be
                  closed and the member's attention is on the slide. */}
              {refusal && (
                <div
                  role="status"
                  className="pointer-events-none absolute bottom-3 left-1/2 z-30 -translate-x-1/2 rounded-md bg-foreground/90 px-3 py-1.5 text-[11px] leading-snug text-background shadow-lg"
                >
                  {refusal}
                </div>
              )}
              {isPaged && selection && (
                <SelectionBreadcrumb
                  html={file.content ?? ''}
                  layout={template}
                  selection={selection}
                  groupIds={groupIds}
                  blockLabels={blockLabels}
                  onSelectPage={selectSlideFromNavigator}
                  onSelectNode={selectNodeFromNavigator}
                />
              )}
              {/* ADR-613 — the judged act, at the thing it acts on. Yields to
                  every other floating door on this canvas: they all anchor off
                  the same surface, and two doors at one selection is a
                  collision, not a choice (the Text mount's rule). */}
              {/* `gestureTarget` (not `selRect` alone) is the condition: it
                  needs BOTH the rect and the selection, and `rewriteSelection`
                  early-returns without it. Keyed on the rect alone the door
                  rendered with a fallback label and did NOTHING when clicked —
                  a door that opens onto nothing. */}
              {/* ...and withdraws while a gesture is HELD: one gesture, one
                  target, one turn (see Text's mount for the defect). */}
              {!slash && !citePicker && !updateMenu && !ctxMenu && !seedHeld && gestureTarget && (
                <SelectionGesture
                  pending={pendingRewrite}
                  anchor={
                    selRect
                      ? {
                          // `...rect` carries contentLeft/contentRight too —
                          // the door hangs beside the ARTIFACT, never on the
                          // heading it is about to rewrite.
                          ...selRect.rect,
                          endLeft: selRect.rect.left,
                          endTop: selRect.rect.top,
                          endBottom: selRect.rect.bottom,
                        }
                      : null
                  }
                  label={gestureTarget.noun}
                  onClick={rewriteSelection}
                />
              )}
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
                  cites={citePicker.cites}
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
              {/* ADR-589 — the Update door. Rail = the selection ladder, pane =
                  that rung's acts. `document` is always the top rung, so the
                  artifact's typography/palette/design-system have an entrance
                  for the first time. */}
              {updateMenu && (
                <StudioUpdateMenu
                  x={updateMenu.x}
                  y={updateMenu.y}
                  selection={selection}
                  scope={scopeOf(
                    unify(selection, rangeBlockIds, groupIds),
                    resolvedMode === 'paged' ? 'paged' : 'flow',
                    selection?.tier ?? null,
                  )}
                  // The container rung comes from the SLOT the runtime already
                  // reports (ADR-511 D3's region). The surface holds no parsed
                  // DOM, and deriving a second chain here would be a second
                  // answer to what `climbChain` already answers in the pane.
                  ancestors={
                    selection?.slot && selection?.blockId
                      ? [{ blockId: selection.blockId, label: selection.slot }]
                      : []
                  }
                  mode={resolvedMode === 'paged' ? 'paged' : 'flow'}
                  pageNoun={template === 'deck' ? 'slide' : 'section'}
                  artifactLabel={artifactDisplayName}
                  setCount={unify(selection, rangeBlockIds, groupIds).set.length}
                  arrangements={vocabulary?.arrangements?.[template] ?? []}
                  currentArrange={selection?.arrange ?? null}
                  carriedCount={carriedCount}
                  groupCount={groupCount}
                  onApplyArrangement={handleApplyArrangement}
                  onRetarget={retargetToRung}
                  onOpenPane={(sc: PaneScope) => { void sc; setRightTab('design'); }}
                  onClose={() => setUpdateMenu(null)}
                />
              )}
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
                  headingRungs={vocabulary?.heading_rungs}
                  // ADR-541 D4 — the same arity the pane reads (unify →
                  // arityOf), scoped to this menu's own subject: the count
                  // applies only when the right-clicked block is IN the set.
                  setCount={(() => {
                    const u = unify(selection, rangeBlockIds, groupIds);
                    return arityOf(u) === 'many' && ctxMenu.blockId && u.set.includes(ctxMenu.blockId)
                      ? u.set.length
                      : 0;
                  })()}
                  onMoveUp={() => handleBlockVerb('up')}
                  onMoveDown={() => handleBlockVerb('down')}
                  onBringForward={() => {
                    // ADR-471 D-d — z among positioned blocks; the spec comes
                    // SERVED (geometrySpecs), never invented FE-side.
                    const id = ctxMenu?.blockId;
                    const gz = geometrySpecs()?.z;
                    if (id && gz)
                      void applyOp((html) => nudgeZ(html, id, +1, gz), `${app.label}: bring ${id} forward`);
                  }}
                  onBringBackward={() => {
                    const id = ctxMenu?.blockId;
                    const gz = geometrySpecs()?.z;
                    if (id && gz)
                      void applyOp((html) => nudgeZ(html, id, -1, gz), `${app.label}: bring ${id} backward`);
                  }}
                  onCopyLink={menuCopyBlockLink}
                  onHistory={menuHistory}
                  // The LOCATED half of the paged mouse insert route
                  // (ADR-579 D6.a): the New/Add tiers render the served
                  // vocabulary INLINE and land through the same ops as the
                  // toolbar doors — no hop to a second menu, and never
                  // another verb's rows under this verb's name.
                  onInsertKind={ctxInsertKind}
                />
              )}
              {/* The native block-insert menu — the MOUSE route on `paged`,
                  where '/' no longer exists. Two mounts open this one menu:
                  the toolbar's Insert (discovery) and the right-click row
                  (located). Both land through the same ops the flow palette
                  uses, so there is one write path under all three doors. */}
              {insertMenu && (
                <StudioBlockInsertMenu
                  vocabulary={vocabulary}
                  medium={resolvedMode ?? null}
                  x={insertMenu.x}
                  y={insertMenu.y}
                  targetLabel={insertMenu.label}
                  onPick={onInsertMenuPick}
                  // ADR-586 D7 — a library pick lands its citation DIRECTLY
                  // (the gallery item IS the file; no picker hop), through
                  // the same insertBlock landing every door uses.
                  onPickLibrary={onInsertMenuLibrary}
                  onClose={() => setInsertMenu(null)}
                  // ADR-586 D2 — the Slide category (the page grain, inside
                  // the one door; the ADR-579 D6.a shape kept).
                  pageSection={
                    resolvedMode === 'paged'
                      ? {
                          noun: template === 'deck' ? 'slide' : 'section',
                          arrangements: vocabulary?.arrangements?.[template] ?? [],
                          onPick: (fragment, label) => {
                            setInsertMenu(null);
                            handleAddArrangement(fragment, label);
                          },
                        }
                      : undefined
                  }
                />
              )}
            </div>
          )}
        </div>

        {/* Right — Chat | Design tabs (ADR-453 D4, the Canva model — never a
            fourth column).

            Three postures, one mount (never a duplicated pane — Singular
            Implementation): a real COLUMN at the three-column rungs; an OVERLAY
            drawer at the two-pane rung, where 368px of permanent column is width
            the canvas needs more (it slides over, dismisses on Escape or the
            scrim, and leaves the artifact full-width underneath); a full-width
            PANE at the single-pane rung, switched by the bottom tab bar. */}
        {sideIsOverlay && sideOpen && (
          <div
            role="presentation"
            onClick={side.toggle}
            className="absolute inset-0 z-20 bg-black/20"
          />
        )}
        {/* The side pane's resize divider — a column edge, so it exists only
            where the pane IS a column. An overlay is dismissed, not resized. */}
        {slotIsColumn(wb, side) && !coarsePointer && (
          <div
            onPointerDown={side.startResize}
            role="separator"
            aria-orientation="vertical"
            title="Drag to resize"
            className="w-1 shrink-0 cursor-col-resize bg-transparent transition-colors hover:bg-primary/20 active:bg-primary/30"
          />
        )}
        <div
          style={slotIsColumn(wb, side) ? { width: side.width } : undefined}
          className={`shrink-0 flex-col border-l border-border ${
            threeColumn
              ? `${sideOpen ? 'flex' : 'hidden'}`
              : sideIsOverlay
                ? `absolute inset-y-0 right-0 z-30 w-[min(380px,85%)] bg-background shadow-xl ${
                    sideOpen ? 'flex' : 'hidden'
                  }`
                : `w-full ${chatActive ? 'flex' : 'hidden'}`
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
                Lanes are not enabled on this deployment — the authoring chat
                needs the model router. The canvas still renders the artifact.
              </div>
            ) : boundLane ? (
              <LanePanel
                key={boundLane.id}
                laneId={boundLane.id}
                laneName={boundLane.name}
                modelLabel={modelLabel}
                // ADR-562 D5 — the member reads WHO ("Designer"), not the
                // engine. This surface created a lane pinning a resident and
                // then rendered `modelLabel`, so the pin was invisible.
                speakerLabel={laneLabel}
                onArtifactWrite={onArtifactWrite}
                composerSeed={seed}
                // ADR-612 D4 — only the lane knows a SEEDED turn actually went
                // up; the click cannot infer it (see armedRewriteRef above).
                onSeedHeld={setSeedHeld}
                onSeededTurn={(running) => {
                  if (running) {
                    if (!armedRewriteRef.current) return;
                    setPendingRewrite(true);
                    armedRewriteRef.current = false;
                  } else {
                    setPendingRewrite(false);
                  }
                }}
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
              onFormat={handleFormat}
              rangeBlockIds={rangeBlockIds}
              rangeShape={rangeShape}
              groupIds={groupIds}
              onAlignMany={handleAlignMany}
              onDistributeMany={handleDistributeMany}
              onPageVerb={handlePageVerb}
              // ADR-519 D3 — the spine's Identity verb row at container + block
              // scope: the SAME id-addressed handler the right-click menu and
              // the block keyboard use (one implementation, a third entrance).
              onElementVerb={handleBlockVerb}
              onTurnInto={handleTurnInto}
              onReturnToFlow={handleReturnToFlow}
              onContainerLayout={handleContainerLayout}
              measures={vocabulary?.measures ?? []}
              onClearMeasure={handleClearMeasure}
              onSetMeasure={handleSetMeasureValue}
              // ADR-520 D4 — the pane's structure affordances select through
              // the SAME reaches the breadcrumb uses (path/Contents → node;
              // the path's page segment → the navigator's page select).
              onSelectNode={selectNodeFromNavigator}
              onSelectPage={selectSlideFromNavigator}
              onApplyDesignSystem={handleApplyDesignSystem}
              onRemoveDesignSystem={handleRemoveDesignSystem}
              // ADR-487 D9 — the applied-system cue routes to the manage panel
              // (the third render state), the SAME param the landing card sets.
              onOpenSystem={(manifestPath) => setParam({ system: relPath(manifestPath) })}
              onInsertImageInSlot={insertImageInContainer}
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

      {/* The single-pane rung's bottom tab bar: one pane at a time.
          ADR-542 D5 — flow ships NO nav tab: its pane content has been
          isPaged-unmounted since ADR-520/526 (the outline's home is the
          Design pane, ADR-526 D2's operator ruling), so the "Outline" label
          was a dead doorway on Docs — a tab that opened onto nothing.

          `min-h-[44px]` is the touch floor (Apple/Google). It was 34px, one of
          27 sub-44px controls measured on this surface — and this one is the
          PRIMARY navigation on a phone, so it is the least affordable of them. */}
      {singlePane && (
        <nav className="flex shrink-0 border-t border-border">
          {([
            ...(resolvedMode === 'paged'
              ? ([['nav', template === 'deck' ? 'Slides' : 'Outline']] as const)
              : []),
            ['canvas', 'Canvas'],
            ['chat', 'Chat'],
          ] as ReadonlyArray<readonly [typeof activePane, string]>).map(([pane, label]) => (
            <button
              key={pane}
              type="button"
              onClick={() => setActivePane(pane)}
              className={`min-h-[44px] flex-1 py-2 text-xs font-medium transition-colors ${
                activePane === pane
                  ? 'border-t-2 border-foreground text-foreground'
                  : 'border-t-2 border-transparent text-muted-foreground'
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      )}

      {/* ADR-458 D3: the organize dialogs (rename/move/trash confirmations)
          stay mounted — the entrances moved to the Design tab's File section;
          the surface-bar menu is gone. */}
      {organizeModals}

      {/* ADR-529 D1: the SAME share dialog Files mounts. Studio's own
          two-button popover is deleted — one act, one component, every
          surface. */}
      <ShareDialog target={shareTarget} onClose={() => setShareTarget(null)} />
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
function ArtifactThumb({ path, fallbackIcon: FallbackIcon }: { path: string; fallbackIcon: LucideIcon }) {
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
          {/* The pre-preview fallback wears THIS app's glyph (ADR-518 D7),
              not Studio's palette on every app's recents. */}
          <FallbackIcon className="h-5 w-5 text-muted-foreground/40" />
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
  // ADR-487 D5 — the workspace default's manifest path (badged on its card).
  const [defaultSystem, setDefaultSystem] = useState<string | null>(null);
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
        setDefaultSystem(v.default_design_system ?? null);
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
  // ADR-514 D1: duplicate is the KERNEL's verb. The pre-514 body here read the
  // content into the browser, probed for a free `-copy` name (capped at 5), and
  // swallowed every error — and recorded no derived_from, so the copy had no
  // recorded origin. `organizeVerbs.onDuplicate` is the one shared path.
  const duplicateRecent = useCallback(
    (path: string) => {
      organizeVerbs.onDuplicate({ path, name: baseName(path) });
    },
    [organizeVerbs],
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
      // ADR-514 D1: Duplicate is a SHARED verb now, so it leaves the Studio
      // extras and joins the organize group (one menu, one ordering, every
      // surface). Copy link stays an extra — it is genuinely Studio-specific.
      onDuplicate: (t) => organizeVerbs.onDuplicate(t),
    },
    (t) => [
      { id: 'copy-link', label: 'Copy link', icon: <Link2 className="h-3.5 w-3.5 text-muted-foreground" />, onClick: () => copyRecentLink(t.path) },
    ],
  );

  // ── The two ways to begin (ADR-452 v2): start from scratch, or learn
  // from a source. Both are peers in ONE grid; both nest their details in a
  // focused modal — the landing shows choices and recents, never form fields.
  // The DELIBERATE door's modal (ADR-470): open (true) = choose shape + name +
  // destination there. The IMMEDIATE door doesn't pass through here at all.
  const [namingOpen, setNamingOpen] = useState(false);
  // Which shape the member picked in the New menu (ADR-549 D1). The dialog
  // opens ON that shape rather than resetting to the first template.
  const [namingTemplate, setNamingTemplate] = useState<string | null>(null);
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

  // ── ONE door into a new artifact (ADR-549 D1) ──────────────────────────
  // Every creation names its object. `createUntitled` — the row that created
  // immediately and asked nothing — is DELETED, along with the "Untitled
  // ‹kind›" identity and the crumb-arms-on-mount behaviour that existed only to
  // make an unnamed artifact nameable after the fact. Its cost was legible in
  // the substrate: `operation/asdfadsf/document.html`, permanent and
  // attributed, because nothing ever asked what it was.
  //
  // The modal owns creation; it throws so the failure shows inline there.
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
      // ADR-549 D4 — a derived artifact lands BESIDE ITS SOURCE.
      //
      // This used to hardcode `operation/${slug}` and never consult the
      // source's own location, so a brief derived from
      // `operation/ai-frontier/briefs/x.md` landed at the ROOT of Documents,
      // orphaned from the thing it was made from. The default is now the
      // source's folder — except for an arrival (`inbound/`), which is not a
      // home, so those still default to Documents.
      const sourceName = source.name.replace(/\.[a-z0-9]+$/i, '');
      const res = await api.studio.createArtifact(target.template, {
        path: `${defaultDestinationFor(source.path)}/${slugify(sourceName)}/${target.template}.html`,
        name: sourceName,
      });
      await api.lanes.create({
        name: `Learn: ${source.name}`.slice(0, 60),
        // A canvas target IS an authoring lane (it carries `artifact_path`), so
        // it gets THIS app's declared resident — resolved server-side from the
        // app's own module (ADR-562 D3, re-homing ADR-467 D1).
        app: app.slug,
        artifact_path: res.path,
        derive_recipe: target.recipe,
        derive_source: source.path,
      });
      setLearnOpen(false);
      onOpen(res.path);
    } else {
      const lane = await api.lanes.create({
        name: `Learn: ${source.name}`.slice(0, 60),
        // No canvas — it lands in /chat as an ordinary conversation. The
        // colleague comes from the RECIPE's own declaration (ADR-562 D4); the
        // `agent: 'scout'` literal that lived here was the same client-asserted
        // identity the app registry removed, surviving one rung down.
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
      // The colleague is the recipe's, declared server-side (ADR-562 D4).
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
              {/* The app's own glyph + invitation (ADR-518 D7) — declared on
                  the AuthoringApp, never another app's chrome. */}
              <app.icon className="h-5 w-5 text-muted-foreground" />
              <h1 className="text-lg font-semibold">
                {app.label}
              </h1>
            </div>
            <p className="max-w-md text-sm text-muted-foreground">
              {app.tagline}
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
              onPickTemplate={(t) => {
                // ADR-549 D1 — the shape choice opens the ONE dialog. The menu
                // picks what kind of thing, never how much you will be asked.
                setNamingTemplate(t.slug);
                setNamingOpen(true);
              }}
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
                      <ArtifactThumb path={r.path} fallbackIcon={app.icon} />
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
              {/* ADR-518: the offer derives from THIS app's served templates —
                  the hardcoded list had gone stale twice (article/page died in
                  ADR-505; the split made it cross-app). */}
              Nothing here yet — hit <span className="font-medium text-foreground/80">New</span>{' '}
              to start your first{' '}
              {templates && templates.length
                ? templates.map((t) => t.label.toLowerCase()).join(' or ')
                : 'artifact'}
              .
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
                  <span className="flex w-full items-center gap-1.5">
                    <Palette className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 truncate text-sm font-medium">{s.name}</span>
                    {defaultSystem === s.manifest_path && (
                      <span
                        className="ml-auto shrink-0 rounded-full border border-border px-1.5 py-px text-[9px] uppercase tracking-wide text-muted-foreground"
                        title="New artifacts are born wearing this design system"
                      >
                        Default
                      </span>
                    )}
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
          initialTemplate={namingTemplate}
          onClose={() => {
            setNamingOpen(false);
            setNamingTemplate(null);
          }}
          onCreate={createScratch}
          dimensionsFirst={app.dimensionsFirst}
        />

        <LearnFromFlowModal
          open={learnOpen}
          // ADR-518 via ADR-473 D3/D4: an app offers only derive targets whose
          // artifact type it OWNS, resolved through the served kind→app
          // association (never a hardcoded type list). Folder targets
          // (template: null → chat lane) are app-free and offered everywhere.
          targets={LEARN_TARGETS.filter(
            (t) => !t.template || appForKind(t.template) === app.slug,
          )}
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
// Step 2 (this, 2026-07-24): the dependents are an OPENABLE list, the
// read-only theme panel (the §5 widened vocabulary, kernel-consumed slots
// first — the SAME parse the Design tab runs, shared via skinVars.ts) is
// folded in, and the theme section is the named token-editor slot (step 3
// makes values editable against the shipped §5 Q4 PATCH permission).
function StudioManage({
  manifestPath,
  onBack,
  onOpenArtifact,
}: {
  manifestPath: string;
  onBack: () => void;
  /** Open one of the artifacts that wear this system. */
  onOpenArtifact: (path: string) => void;
}) {
  const [detail, setDetail] = useState<Awaited<
    ReturnType<typeof api.studio.resolveDesignSystem>
  > | null>(null);
  const [wornBy, setWornBy] = useState<Array<{ path: string }> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reimporting, setReimporting] = useState(false);
  // ADR-487 D5 — is THIS system the workspace default? (null = unknown/loading)
  const [isDefault, setIsDefault] = useState<boolean | null>(null);
  const [defaultBusy, setDefaultBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    setError(null);
    api.studio
      .resolveDesignSystem(manifestPath)
      .then(setDetail)
      .catch(() => setError('This design system could not be read.'));
    // Worn-by: the ADR-448 reference edge, read outward from the manifest —
    // the endpoint already returns the PATHS, not just the count. The backend
    // returns {dependents: []} on any failure, so this never throws.
    api.documents
      .dependents(manifestPath)
      .then((d) => setWornBy(d.dependents))
      .catch(() => setWornBy(null));
    // The default flag rides the vocabulary (the served workspace state).
    api.studio
      .vocabulary()
      .then((v) => setIsDefault(v.default_design_system === manifestPath))
      .catch(() => setIsDefault(null));
  }, [manifestPath]);

  // ADR-487 D5 — toggle the workspace default. An inheritance rule at
  // creation: new artifacts are born wearing it; nothing existing changes.
  const toggleDefault = async () => {
    if (isDefault === null) return;
    setDefaultBusy(true);
    setError(null);
    try {
      const r = await api.studio.setDefaultDesignSystem(isDefault ? null : manifestPath);
      setIsDefault(r.default_design_system === manifestPath);
    } catch {
      setError('Could not update the workspace default.');
    } finally {
      setDefaultBusy(false);
    }
  };

  // The theme — parsed from the RESOLVED skin element (what this system IS,
  // maps bridge included), not from any one artifact's copy of it.
  const themeVars = useMemo(() => {
    if (!detail) return [];
    const css =
      detail.skin_element.match(/<style[^>]*>([\s\S]*?)<\/style>/i)?.[1] ??
      detail.skin_element;
    return parseSkinVars(css, 24);
  }, [detail]);

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
          <div className="flex shrink-0 items-center gap-2">
            {/* ADR-487 D5 — the workspace default: new artifacts are born
                wearing it. Toggle; clearing returns to skin-less birth. */}
            <button
              type="button"
              disabled={defaultBusy || isDefault === null}
              onClick={() => void toggleDefault()}
              title={
                isDefault
                  ? 'New artifacts are born wearing this — click to clear'
                  : 'Make new artifacts wear this design system at creation'
              }
              className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm transition-colors disabled:opacity-50 ${
                isDefault
                  ? 'border-indigo-400 bg-indigo-50/60 text-indigo-900 dark:bg-indigo-950/40 dark:text-indigo-200'
                  : 'border-border text-foreground hover:bg-muted/60'
              }`}
            >
              {defaultBusy ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Check className={`h-3.5 w-3.5 ${isDefault ? '' : 'opacity-40'}`} />
              )}
              {isDefault ? 'Default' : 'Set as default'}
            </button>
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

        {/* Worn by — the ADR-448 reference edge, now the openable LIST (the
            payoff the citation contract was built for): each artifact whose
            HEAD cites this manifest, one click from its manage home. */}
        <div className="rounded-lg border border-border p-4">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Worn by{wornBy && wornBy.length > 0 ? ` · ${wornBy.length}` : ''}
          </p>
          {wornBy === null ? (
            <p className="mt-1 text-sm text-muted-foreground">—</p>
          ) : wornBy.length === 0 ? (
            <p className="mt-1 text-sm text-muted-foreground">
              No artifacts wear this yet. Apply it from an artifact’s Design tab.
            </p>
          ) : (
            <ul className="mt-2 space-y-1">
              {wornBy.map((d) => (
                <li key={d.path}>
                  <button
                    type="button"
                    onClick={() => onOpenArtifact(d.path)}
                    className="flex w-full min-w-0 items-center gap-2 rounded-md px-1.5 py-1 text-left text-sm transition-colors hover:bg-muted/60"
                    title={d.path.replace(/^\/workspace\//, '')}
                  >
                    <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 truncate">{leafOf(d.path)}</span>
                    <span className="ml-auto shrink-0 truncate text-[10px] text-muted-foreground">
                      {d.path.replace(/^\/workspace\//, '').split('/').slice(0, -1).join('/')}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
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

        {/* The theme — the resolved skin's custom properties, kernel-consumed
            vocabulary first (§5 Move 1; the shared skinVars parse). This
            section IS the token-editor slot: step 3 makes a row editable
            against the shipped §5 Q4 PATCH permission, once the var→owning-
            source design pass lands. Read-only until then, and says so. */}
        {themeVars.length > 0 && (
          <div className="rounded-lg border border-border p-4">
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Theme
            </p>
            <div className="mt-2 space-y-1">
              {themeVars.map((v) => (
                <div key={v.name} className="flex items-center gap-2">
                  {isColorValue(v.value) ? (
                    <span
                      className="h-3.5 w-3.5 shrink-0 rounded-sm border border-border"
                      style={{ background: v.value }}
                    />
                  ) : (
                    <span className="h-3.5 w-3.5 shrink-0" />
                  )}
                  <code className="text-[11px] text-muted-foreground">--{v.name}</code>
                  <span className="ml-auto truncate text-[11px]">{v.value}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 border-t border-border pt-2 text-[10px] text-muted-foreground">
              Read-only — the theme lives in its files. Change a value through
              the chat or a re-import; inline editing lands here.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
