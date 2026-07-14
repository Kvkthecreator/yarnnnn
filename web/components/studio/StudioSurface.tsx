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

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Loader2, Palette, PanelLeft, Sparkles } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useSurfaceParam, useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { LearnFromFlowModal } from './LearnFromFlowModal';
import { NewArtifactModal, slugify } from './NewArtifactModal';
import { useFileLoad } from '@/components/workspace/useFileLoad';
import { useSurfaceActions, useWindowCrumb } from '@/contexts/BreadcrumbContext';
import { useFileOrganizeVerbs } from '@/hooks/useFileOrganizeVerbs';
import { LanePanel } from '@/components/chat-surface/LanePanel';
import { StudioCanvas, type PointerEvent2 } from './StudioCanvas';
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
  duplicatePage,
  editBlockText,
  galleryFragment,
  insertArrangement,
  insertBlock,
  insertBlockInSlot,
  moveBlock,
  movePage,
  removePageBackground,
  removeSkin,
  setPageBackground,
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

  // ADR-446 surface-bar action: a single ⋯ that opens the organize menu
  // ADR-458 D3: the surface bar is crumb-only — the "File actions" button is
  // deleted; the file verbs live in the Design tab's document scope (the one
  // settings home). Registering the empty set keeps the bar clean.
  useSurfaceActions('studio', []);

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

  // ── Organize the open artifact (ADR-446): Rename / Move to… / Move to Trash.
  // The SAME shared implementation the Files surface uses (useFileOrganizeVerbs)
  // — the artifact-as-file is organized from the app that opened it (the macOS
  // window-titlebar model), not only from the Files explorer. Optimistic: an
  // inbound record / machine-config 403s with the honest reason; an ordinary
  // artifact (or an uploaded file under inbound/uploads/) organizes cleanly.
  // After the mutation: rename/move → re-point the surface at the new path;
  // trash → the artifact is gone, so fall to the Studio START state.
  const { verbs: organizeVerbs, modals: organizeModals } = useFileOrganizeVerbs({
    onAfterMutate: (newPath) => {
      setParam({ file: newPath === null ? null : relPath(newPath) });
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

  // ADR-453 D4: the right column's two tabs — Chat (the bound lane) | Design
  // (the scope-switching inspector). The lane stays MOUNTED under either tab.
  const [rightTab, setRightTab] = useState<'chat' | 'design'>('chat');

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
    // ADR-458: the gutter's ⋮⋮ selects AND opens the Design tab (one home).
    if (p.design) setRightTab('design');
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
    () => ({
      blockId: selection?.blockId ?? null,
      slideIndex: selection?.slideIndex ?? null,
      pageIndex: selection?.pageIndex ?? null,
    }),
    [selection],
  );
  const kernelStyle = vocabulary?.kernel_style_element;

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
  // ADR-456 W1: N cited images land as ONE gallery block, one revision.
  const handleInsertGallery = useCallback(
    (paths: string[]) => {
      const base = vocabulary?.blocks.find((b) => b.kind === 'gallery')?.fragment;
      if (!base) return;
      const fragment = galleryFragment(base, paths.map(relPath));
      if (!fragment) return;
      void applyOp(
        (html) => insertBlock(html, fragment, anchor),
        `Studio: insert gallery (${paths.length} images)`,
      );
    },
    [applyOp, anchor, vocabulary],
  );
  const handleAddArrangement = useCallback(
    (fragment: string, label: string) =>
      applyOp(
        (html) => insertArrangement(html, fragment, anchor, kernelStyle),
        `Studio: add ${label}`,
      ),
    [applyOp, anchor, kernelStyle],
  );
  const handleApplyArrangement = useCallback(
    (fragment: string, label: string) =>
      applyOp(
        (html) => applyArrangement(html, fragment, anchor, kernelStyle),
        `Studio: change arrangement to ${label}`,
      ),
    [applyOp, anchor, kernelStyle],
  );

  // ── ADR-453: the property layer + the structural verbs (Design tab) ──────
  const handleSetToken = useCallback(
    (grain: 'block' | 'page' | 'document', key: string, value: string | null) =>
      applyOp(
        (html) => setToken(html, { grain, anchor }, key, value, kernelStyle),
        value == null ? `Studio: clear ${key}` : `Studio: set ${key} to ${value}`,
      ),
    [applyOp, anchor, kernelStyle],
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
      void applyOp(
        (html) => insertBlockInSlot(html, proseFragment, slot, slideIndex, pageIndex),
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
      if (!editBlockText(file.content, blockId, newInner)) return; // no-op — no revision, no error
      void applyOp((html) => editBlockText(html, blockId, newInner), `Studio: edit ${blockId} block`);
    },
    [applyOp, file],
  );

  // ── ADR-456 W2: slash-insert + turn-into ─────────────────────────────────
  // The edit runtime commits + exits on '/' in an empty context, then reports
  // the block's rect; the palette renders in the canvas wrapper (the iframe
  // fills it, so frame-viewport coordinates ≈ wrapper coordinates, clamped).
  const canvasWrapRef = useRef<HTMLDivElement>(null);
  const [slash, setSlash] = useState<{
    blockId: string;
    empty: boolean;
    left: number;
    top: number;
  } | null>(null);
  const onSlashOpen = useCallback(
    (blockId: string, empty: boolean, rect: { left: number; top: number; bottom: number }) => {
      const wrap = canvasWrapRef.current;
      const maxLeft = Math.max(8, (wrap?.clientWidth ?? 640) - 272);
      const maxTop = Math.max(8, (wrap?.clientHeight ?? 480) - 300);
      setSlash({
        blockId,
        empty,
        left: Math.max(8, Math.min(rect.left, maxLeft)),
        top: Math.max(8, Math.min(rect.bottom + 6, maxTop)),
      });
    },
    [],
  );
  const onSlashPick = useCallback(
    (kind: string, label: string, fragment: string) => {
      const s = slash;
      setSlash(null);
      if (!s) return;
      if (kind === 'chart') {
        seedComposer('Create an SVG chart at ./assets/chart.svg, cite it in the document, showing: ');
        return;
      }
      if (s.empty) {
        // An empty block CONVERTS in place — the Notion "empty line + /" gesture.
        void applyOp(
          (html) => convertBlock(html, s.blockId, kind, fragment),
          `Studio: turn block into ${label}`,
        );
      } else {
        void applyOp(
          (html) => insertBlock(html, fragment, { blockId: s.blockId }),
          `Studio: add ${label} block`,
        );
      }
    },
    [slash, applyOp, seedComposer],
  );
  // ADR-456 W3: the page background — a cited image on the page element.
  const handleSetPageBackground = useCallback(
    (path: string) =>
      applyOp(
        (html) => setPageBackground(html, anchor, relPath(path), kernelStyle),
        `Studio: set page background ${relPath(path)}`,
      ),
    [applyOp, anchor, kernelStyle],
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
  const [navCollapsed, setNavCollapsed] = useState(false);

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

        {/* Center — the toolbar + zoom over the canvas (renders, edits in place). */}
        <div className={`min-w-0 flex-1 flex-col md:flex ${canvasActive ? 'flex' : 'hidden'}`}>
          <div className="flex items-center gap-1 border-b border-border">
            {/* ADR-455: collapse/expand the navigator (desktop) — the outline
                earns its width or gets out of the way. */}
            <button
              type="button"
              onClick={() => setNavCollapsed((c) => !c)}
              title={`${navCollapsed ? 'Show' : 'Hide'} the ${template === 'deck' ? 'slide strip' : 'outline'}`}
              className={`ml-2 hidden shrink-0 rounded p-1 transition-colors hover:bg-muted/40 md:inline-flex ${
                navCollapsed ? 'text-muted-foreground/60' : 'text-muted-foreground'
              }`}
            >
              <PanelLeft className="h-3.5 w-3.5" />
            </button>
            <div className="min-w-0 flex-1">
              <StudioToolbar
                vocabulary={vocabulary}
                layout={template}
                selection={selection}
                onClearSelection={onPointClear}
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
                onEditEntered={(id) => setEditingBlockId(id)}
                onAddHere={onAddHere}
                onSlashOpen={onSlashOpen}
                scrollToSlide={scrollToSlide}
                scrollToBlock={scrollToBlock}
                zoom={zoom}
              />
              {slash && (
                <StudioSlashPalette
                  vocabulary={vocabulary}
                  left={slash.left}
                  top={slash.top}
                  onPick={onSlashPick}
                  onClose={() => setSlash(null)}
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
                rename: () =>
                  organizeVerbs.onRename({ path: artifactPath, name: baseName(artifactPath) }),
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

function StudioStart({ onOpen }: { onOpen: (path: string) => void }) {
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [recents, setRecents] = useState<
    Array<{ path: string; updated_at: string | null; summary: string | null }>
  >([]);
  const [existing, setExisting] = useState('');
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

  // ── The two ways to begin (ADR-452 v2): start from scratch, or learn
  // from a source. Both are peers in ONE grid; both nest their details in a
  // focused modal — the landing shows choices and recents, never form fields.
  const [scratchTemplate, setScratchTemplate] = useState<TemplateInfo | null>(null);
  const [learnOpen, setLearnOpen] = useState(false);

  const { navigateToSurface } = useSurfacePreferences();
  const [laneEnv, setLaneEnv] = useState<{ enabled: boolean; model: string } | null>(null);
  useEffect(() => {
    api.lanes
      .list()
      .then((d) => setLaneEnv({ enabled: d.enabled, model: d.models[0]?.id ?? '' }))
      .catch(() => setLaneEnv({ enabled: false, model: '' }));
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
    if (!laneEnv?.enabled || !laneEnv.model) {
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
        model: laneEnv.model,
        artifact_path: res.path,
        derive_recipe: target.recipe,
        derive_source: source.path,
      });
      setLearnOpen(false);
      onOpen(res.path);
    } else {
      const lane = await api.lanes.create({
        name: `Learn: ${source.name}`.slice(0, 60),
        model: laneEnv.model,
        derive_recipe: target.recipe,
        derive_source: source.path,
      });
      setLearnOpen(false);
      navigateToSurface('chat', { lane: lane.id });
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

        {/* ADR-452 v2 — ONE creation grid: the type cards and Learn-from are
            peers ("start from scratch, or learn from"); each nests its
            details in a focused modal. */}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {templates.map((t) => (
            <button
              key={t.slug}
              type="button"
              onClick={() => setScratchTemplate(t)}
              className="rounded-lg border border-border p-3 text-left transition-colors hover:bg-muted/20"
            >
              <p className="text-sm font-medium">{t.label}</p>
              <p className="mt-1 text-[11px] leading-snug text-muted-foreground">
                {t.description}
              </p>
            </button>
          ))}
          <button
            type="button"
            disabled={laneEnv?.enabled === false}
            onClick={() => setLearnOpen(true)}
            title={laneEnv?.enabled === false ? 'Chat helpers aren’t enabled on this workspace.' : undefined}
            className="rounded-lg border border-dashed border-border p-3 text-left transition-colors hover:bg-muted/20 disabled:opacity-40"
          >
            <p className="flex items-center gap-1 text-sm font-medium">
              <Sparkles className="h-3.5 w-3.5" /> Learn from
            </p>
            <p className="mt-1 text-[11px] leading-snug text-muted-foreground">
              Start from a file — yours or one you upload.
            </p>
          </button>
        </div>

        {recents.length > 0 && (
          <div className="space-y-2 border-t border-border pt-4">
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
              Continue where you left off
            </p>
            <div className="grid grid-cols-3 gap-2">
              {recents.slice(0, 6).map((r) => (
                <button
                  key={r.path}
                  type="button"
                  onClick={() => onOpen(r.path)}
                  className="group rounded-lg border border-border p-2 text-left transition-colors hover:bg-muted/20"
                >
                  <ArtifactThumb path={r.path} />
                  <span className="mt-1.5 block truncate text-xs font-medium">{baseName(r.path)}</span>
                  <span className="block truncate text-[10px] text-muted-foreground">
                    {r.updated_at
                      ? new Date(r.updated_at).toLocaleDateString()
                      : relPath(r.path)}
                  </span>
                </button>
              ))}
            </div>
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
