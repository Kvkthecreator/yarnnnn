'use client';

/**
 * StudioCanvas — the Studio's artifact canvas (ADR-440 D2; pointing v1.1;
 * direct editing ADR-446).
 *
 * A MOUNT in the ADR-436 sense: it takes the loaded artifact, runs the
 * reference projection pass (citations become displayable content; every
 * artifact-authored executable is STRIPPED), injects the pointer + edit
 * runtimes, and renders in an iframe sandboxed to `allow-scripts` ONLY — an
 * opaque origin with no same-origin access, no credentials, no top-navigation.
 * The only scripts that run are ours (pointing + editing).
 *
 * The canvas now EDITS in place (ADR-446), but never a second write path: a
 * click selects a block (deixis — reports {blockId, blockKind, …}); entering
 * edit mode makes the block's text contentEditable; on blur/idle the runtime
 * maps the edit back to the artifact's SOURCE (citation islands restored to
 * their living-reference form) and reports {blockId, newInner} — the surface
 * lands it through the ONE mechanical write door (ADR-444) as a debounced,
 * operator-attributed, CAS-guarded revision.
 */

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { WorkspaceFile } from '@/types';
import { resolveArtifactHtml } from '@/components/workspace/viewers/projection';
import { readStageSize } from '@/components/authoring/stageGeometry';

/** ADR-462 D7: a right-click's report. The runtime has already selected the
 *  block under the cursor; this carries the anchor + the grain the menu builds
 *  its rows from. It is PointerEvent2's shape plus the two things only a
 *  right-click needs: where to draw, and whether a frame bounds the subject. */
export interface StudioContextTarget {
  x: number;
  y: number;
  tag: string | null;
  text: string;
  dataRef: string | null;
  blockId: string | null;
  blockKind: string | null;
  slideIndex: number | null;
  pageIndex: number | null;
  slot: string | null;
  arrange: string | null;
  /** ADR-461 D4's gate, answered by the only side that can see the DOM. Gates
   *  the geometry rows (Bring forward) — never guessed from the layout name. */
  framed: boolean;
  /** ADR-471 D-d: both x/y markers present — the positioned state. Gates the
   *  z verbs (Bring forward/backward order POSITIONED blocks). */
  positioned: boolean;
  /** ADR-525 D1 — the selection's tier, declared by the runtime. Gates the
   *  ENCLOSURE verbs (Duplicate/Delete) the same way `framed` gates geometry:
   *  the runtime is the only side that can see both the DOM and the medium. */
  tier?: 'text' | 'object' | 'structure' | null;
}

export interface PointerEvent2 {
  tag: string;
  text: string;
  dataRef: string | null;
  /** ADR-443 D6 — the enclosing block's address, when the hit is inside one. */
  blockId: string | null;
  blockKind: string | null;
  /** ADR-444 — the enclosing slide's index (deck layouts), for slide ops. */
  slideIndex: number | null;
  /** ADR-453 D5 — the page index (document order over `section.slide,
   *  [data-arrange]`), so document/article sections anchor page ops too. */
  pageIndex: number | null;
  /** ADR-453 D5 — the enclosing slot's name (a slot-padding click selects the
   *  SLOT when no block encloses the hit; blockId null + slot set = slot grain). */
  slot: string | null;
  /** ADR-453 D5 — the enclosing page's arrangement slug (role lookups). */
  arrange: string | null;
  /** ADR-511 D3 — the operator-word name of the selected thing (slide,
   *  columns, column, heading…), from the runtime's inlined label ladder.
   *  blockId set + blockKind null = a structural CONTAINER selection. */
  label?: string | null;
  /** ADR-522 D4 — the nearest heading at or above this block (flow only).
   *  Docs has no section unit (flat sibling headings, no wrapper), so this
   *  heading IS what "this section" resolves to: from here to the next one. */
  headingId?: string | null;
  headingText?: string | null;
  /** ADR-525 D1 — the selection's TIER, declared by the runtime (the one party
   *  that sees both the DOM and the medium): `text` on flow prose (the caret
   *  speaks for it), `object` for a figure/table/chart anywhere and for EVERY
   *  block on a paged medium, `structure` for a container/page. Read it; the
   *  pane and the menu both gate on this one field so they cannot disagree. */
  tier?: 'text' | 'object' | 'structure' | null;
}

/** ADR-546 D3 — one covered block's rung, as the runtime reports it. `text` is
 *  present on headings only (the span's potential lead needs a name; nothing
 *  else does). Interpreted ONLY by `spanShapeOf` in selection.ts. */
export interface RangeRung {
  heading: number | null;
  nesting: number;
  text?: string;
}

interface StudioCanvasProps {
  /** The loaded artifact (the surface owns the fetch + reload cadence). */
  file: WorkspaceFile;
  /** Absolute workspace path — the base for relative citation resolution. */
  artifactPath: string;
  /** Pointing (v1.1): the member clicked an element in the canvas. */
  onPoint?: (p: PointerEvent2) => void;
  /** The member clicked empty space — selection cleared. */
  onPointClear?: () => void;
  /** ADR-528 — the blocks a live text range intersects (empty = collapsed).
   *  The pane needs this because a RANGE is not a click: its scope must
   *  follow the selection, not the last block the member clicked into. */
  /** ADR-546 D3 — the covered blocks AND each one's rung, so the parent can
   *  derive the span's SHAPE (a heading + what is under it is a subtree, not N
   *  peers). The rungs ride the same message: one gesture, one report. */
  onRange?: (blockIds: string[], rungs?: RangeRung[]) => void;
  /** ADR-446: the block currently being edited in place (null = none). The
   *  surface holds this state; the canvas commands the iframe runtime. */
  editingBlockId?: string | null;
  /** ADR-466 P9: the block currently SELECTED (the surface's grain-ladder
   *  state). Every optimistic op swaps srcdoc, which resets the runtime's own
   *  selection — the load handler re-commands it by id so the bounding box
   *  survives a write (the editingBlockId pattern, applied to selection). */
  selectedBlockId?: string | null;
  /** ADR-446: a block edit committed (blur/idle) — {blockId, newInner} mapped
   *  to the SOURCE (citation islands already restored). The surface lands it
   *  through the mechanical write door. */
  onEdit?: (blockId: string, newInner: string) => void;
  /** ADR-480 D1: the layout's composition mode, read from the served registry.
   *  `flow` puts contenteditable on the document root (one continuous writing
   *  surface); `paged` keeps the per-block enclosure grammar. The runtime never
   *  learns a layout SLUG — it reads only this mode (ADR-222). */
  mode?: 'flow' | 'paged';
  /** ADR-485 D3: the SERVED measure bounds, keyed by measure key — the same
   *  registry the write-side clamp reads (`vocabulary.measures`). The gesture
   *  clamps its PREVIEW with these, so the box the member releases on is the
   *  box that lands. The runtime invents no bound (ADR-461 D4). */
  measureBounds?: Record<string, { min: number; max: number }>;
  /** ADR-544 D4 — the served kind→label map. The runtime's chrome (frame label,
   *  hover badge, selection payload) says the registry's word, never the
   *  substrate's `data-block` attribute. Same projection-input discipline as
   *  `measureBounds`: memoized upstream, or the frame reloads every render. */
  blockLabels?: Record<string, string>;
  /** ADR-544 D5.1 — the runtime refused a gesture (today: a ⇧-click that would
   *  build a set spanning two Areas). The surface says why; the runtime never
   *  writes operator-facing words. */
  onRefused?: (reason: string) => void;
  /** ADR-446: the block left edit mode via a member blur — the surface clears
   *  its editingBlockId so it doesn't re-enter on the post-commit reload. */
  onEditExited?: () => void;
  /** ADR-447 Phase 4: the member DOUBLE-CLICKED a block — the runtime entered
   *  edit mode itself; the surface syncs its editingBlockId to match. */
  onEditEntered?: (blockId: string) => void;
  /** F2: the member pressed ENTER at a block's end — insert a fresh empty prose
   *  block after `afterBlockId` and move the caret in ("writing is adding"). */
  onEnterBlock?: (afterBlockId: string) => void;
  /** F1: the member DRAGGED a block via the ⋮⋮ handle — move it before
   *  `beforeBlockId` (null = end of its parent). Lands one reorder revision. */
  /** ADR-466 P8: a bounding-box gesture landed — any combination of position
   *  (x/y, a body drag) and width (w, a corner handle; a west handle on a
   *  positioned block moves origin AND width together), all as PERCENTS of
   *  the block's frame. The surface clamps from the kernel's served bound and
   *  lands setGeometry (ONE revision per gesture) through the one door. */
  onGeometry?: (blockId: string, geo: { x?: number; y?: number; w?: number; h?: number }) => void;
  /** A GROUP drop — every member's landed position, folded into one revision. */
  onGeometryMany?: (
    moves: Array<{ blockId: string; geo: { x?: number; y?: number; w?: number; h?: number } }>,
  ) => void;
  /** The group's membership changed (shift/⌘-click) — a transient selection. */
  onGroup?: (blockIds: string[]) => void;
  /** ADR-462 D7: the member right-clicked the canvas. The runtime has ALREADY
   *  selected the block under the cursor (right-click selects), so this only
   *  carries where to anchor + the grain the menu builds its rows from.
   *  `framed` is the runtime's answer to the ADR-461 D4 gate — only it can see
   *  the DOM, so it reports rather than letting the surface guess. */
  onContextMenu?: (m: StudioContextTarget) => void;
  /** ADR-462 D10: a keyboard verb on the SELECTED block. The canvas is a
   *  sandboxed iframe — keys land in its document or nowhere — so the runtime
   *  hears them and posts an existing verb out. Never a new op. */
  onKeyVerb?: (verb: 'copy' | 'paste' | 'duplicate' | 'delete' | 'up' | 'down', blockId: string) => void;
  /** ⌘Z / ⌘⇧Z from the runtime (fired only when no text caret is live — see
   *  projection.ts). The parent owns the snapshot stack; these just ask. */
  onUndo?: () => void;
  onRedo?: () => void;
  /** ADR-461 D3: the member dragged the column divider to a STOP. `value` is
   *  the ratio token's value, or null for the even default (which is written
   *  by CLEARING the attribute — 1-1 is the absence, not a third value). */
  onRatio?: (pageIndex: number, value: string | null) => void;
  /** F6: the member pressed ENTER mid-block — the runtime split it optimistically
   *  in-frame; land the source split (blockId keeps beforeInner, newId gets
   *  afterInner) as a background revision with NO reload. */
  onSplitBlock?: (blockId: string, newId: string, beforeInner: string, afterInner: string) => void;
  /** F6: the member pressed BACKSPACE at a block start — the runtime merged it
   *  into the previous block optimistically; land the source merge (no reload). */
  onMergeBlock?: (blockId: string, prevBlockId: string, mergedInner: string) => void;
  /** ADR-447 Phase 4, re-addressed by ADR-511 Phase 2: the member clicked
   *  "+ Add" in an empty region — `containerId` is the op address (identity);
   *  slot/arrange ride along as legacy names for the registry ROLE lookup. */
  onAddHere?: (
    slot: string,
    slideIndex: number | null,
    pageIndex: number | null,
    arrange: string | null,
    containerId: string | null,
  ) => void;
  /** ADR-456 W2: the member typed '/' in an empty context — the runtime
   *  committed + exited the edit; the surface opens the block palette anchored
   *  at the block's rect (frame-viewport coordinates ≈ iframe-box pixels).
   *  `empty` = the whole block was empty (the palette converts it in place
   *  instead of inserting after it). */
  /** ADR-613 — the selection's VISUAL box, mapped into PARENT-page coordinates
   *  so a parent-side door can anchor to it. `null` means nothing is selected.
   *  The runtime reports iframe-viewport coordinates (the `clientX/Y` space),
   *  so this offsets by the iframe's page position with NO zoom multiply — the
   *  same mapping the context-menu bridge below explains at length. */
  onSelectionRect?: (
    rect: { left: number; top: number; right: number; bottom: number } | null,
    grain: string | null,
  ) => void;
  onSlashOpen?: (
    blockId: string,
    empty: boolean,
    rect: { left: number; top: number; bottom: number; width: number },
  ) => void;
  /** The '/' filter is typed INTO the document (the caret never leaves), so the
   *  runtime reports the run after it — the palette's input is a mirror. */
  onSlashFilter?: (filter: string) => void;
  /** The caret left the run, the '/' was deleted, or the content was clicked.
   *  The palette's own document-mousedown cannot hear a click in this frame. */
  onSlashClose?: () => void;
  /** ↑/↓ while the palette is open — the document has the caret, so the runtime
   *  intercepts the key and the surface moves the highlight. */
  onSlashMove?: (delta: number) => void;
  /** Enter while the palette is open — pick the highlighted row. */
  onSlashEnter?: () => void;
  /** A pick was taken: the runtime removed the '/'+filter run and returns the
   *  halves around it (null when the caret sat inside a citation island). */
  onSlashTaken?: (
    blockId: string,
    beforeInner: string | null,
    afterInner: string | null,
  ) => void;
  /** Commands the runtime to consume the '/'+filter run (a pick landed). The
   *  nonce fires the same take twice when the member repeats the gesture. Only
   *  the runtime knows which text node holds the run, so it does the deleting
   *  and answers with onSlashTaken. */
  slashTake?: { filterLen: number; nonce: number } | null;
  /** ADR-506 D1: the toolbar's Insert. Asks the runtime to TYPE the '/' at a
   *  resolved caret — the button is a door to the one insert gesture, not a
   *  second mechanism (ADR-505 D4). The runtime answers with the ordinary
   *  onSlashOpen, so everything downstream is unchanged. Nonce for repeats. */
  /** ADR-527 D4 — a RANGE format op driven from the pane. Nonce-carrying so
   *  the same button fires twice; the runtime restores the last live range
   *  before applying, because the pane's click destroyed the selection. */
  fmtCmd?: { op: string; value: string | null; nonce: number } | null;
  /** ADR-447: scroll the canvas to this slide (the navigator selected it). A
   *  monotonic nonce forces the scroll even when re-selecting the same slide. */
  scrollToSlide?: { index: number; nonce: number } | null;
  /** ADR-455: scroll the canvas to this heading block (the outline navigates). */
  scrollToBlock?: { blockId: string; nonce: number } | null;
  /** ADR-524 D1 — a projected block to swap in place, instead of re-parsing the
   *  whole document. The nonce re-fires an identical patch.
   *
   *  `appliedFor` is the FULL artifact content this patch brings the live DOM
   *  into agreement with. The canvas uses it to skip the re-projection that
   *  would otherwise swap srcDoc for the same change one tick later — without
   *  it the patch is pointless, since srcDoc is re-fed on every content change.
   *  It is the patch's own claim about what it achieved, so a patch that fails
   *  to send simply leaves the ordinary re-projection in charge. */
  /** ADR-547 D2/D4 — the blocks an op touched, projected and ready for the live
   *  DOM. Was a single `blockId`; a span op (setTokenMany / convertBlocks over a
   *  range) touches N, and N patches share ONE `appliedFor` because they bring the
   *  live DOM to one artifact state together. */
  patch?: { blocks: Array<{ blockId: string; html: string }>; nonce: number; appliedFor: string } | null;
  /** ADR-447: zoom the rendered document (a VIEW control — 1 = 100%). Never a
   *  file change; the artifact's real dimensions are untouched. */
  zoom?: number;
  /** ADR-520 D1: the STAGE VIEW — a deck shows one slide at a time. The
   *  runtime owns WHICH slide (transient view state, restored through the
   *  existing scroll-pos/restore channel); this only turns the mode on. */
  stage?: boolean;
  /** ADR-522 D3: what is ON SCREEN, reported by the runtime on every scroll
   *  settle. Distinct from the selection — on a staged deck the member pages
   *  with PgUp/PgDn and nothing is selected, so this is the ONLY signal that
   *  says which slide they are looking at. The payload already existed (it
   *  drives the post-reload position restore below); this lifts it out of the
   *  ref so the surface can declare it as focus. */
  onScrollPos?: (pos: { y: number; slide: number | null }) => void;
}

// A staged layout's box is a property of the FILE (components/authoring/
// stageGeometry.ts) — it rides the artifact as --stage-w/--stage-h. This
// canvas's only geometric job is to AUTO-FIT: scale the stage down so it fits
// the actual column width, with the operator's zoom riding on top. It SCALES,
// never RESIZES — a deck must look the same here as it does shared, exported,
// or on a tablet. Documents/web are fluid (no fixed stage), so they get no fit.

export function StudioCanvas({
  file,
  artifactPath,
  onPoint,
  onPointClear,
  onRange,
  editingBlockId,
  selectedBlockId,
  onEdit,
  mode,
  measureBounds,
  blockLabels,
  onRefused,
  onEditExited,
  onEditEntered,
  onEnterBlock,
  onRatio,
  onGeometry,
  onGeometryMany,
  onGroup,
  onContextMenu,
  onKeyVerb,
  onUndo,
  onRedo,
  onSplitBlock,
  onMergeBlock,
  onAddHere,
  onSelectionRect,
  onSlashOpen,
  onSlashFilter,
  onSlashClose,
  onSlashMove,
  onSlashEnter,
  onSlashTaken,
  scrollToSlide,
  slashTake,
  fmtCmd,
  scrollToBlock,
  patch,
    zoom = 1,
  stage = false,
  onScrollPos,
}: StudioCanvasProps) {
  const [projected, setProjected] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Is this a STAGED layout? (the projection pins deck slides / canvas
  // artboards to a fixed stage — ADR-471 D-a shares the frame.) The root
  // carries data-template; cheap string tests avoid re-parsing.
  const isDeck = file.content?.includes('data-template="deck"') ?? false;
  // `image` (not `canvas`): ADR-472 D1/D7 moved the artboard out of Studio and
  // renamed the slug, and the migration rewrote every live artifact. This test
  // still read `canvas`, so IMAGES stages matched nothing and got NO auto-fit —
  // a 1080px stage rendered 1:1 in a ~370px column, the same unfitted
  // blank-margin defect ADR-447 D7.7 described for decks.
  const isImageTpl = file.content?.includes('data-template="image"') ?? false;
  const isStaged = isDeck || isImageTpl;

  // The auto-fit scale: for a deck, shrink the 992px stage to the column width
  // (never enlarge past 1); for fluid layouts, 1. Measured off the iframe's own
  // width via ResizeObserver so it tracks the column (chat drawer, DevTools,
  // window resize). The operator's `zoom` multiplies this base.
  const [fitScale, setFitScale] = useState(1);
  useEffect(() => {
    const frame = iframeRef.current;
    if (!frame || !isStaged) {
      setFitScale(1);
      return;
    }
    // The stage's WIDTH is read from the projected document, never restated
    // here: the file owns its geometry, and a second copy in the viewer is how
    // the editor and every other consumer drifted apart in the first place.
    const measure = () => {
      const w = frame.clientWidth;
      if (w <= 0) return;
      const { width: stageW } = readStageSize(
        frame.contentDocument,
        isDeck ? 'deck' : 'image',
      );
      if (stageW > 0) setFitScale(Math.min(1, w / stageW));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(frame);
    return () => ro.disconnect();
    // `projected` is a dependency, not decoration: on first mount the content
    // has not loaded, so isStaged is false and this effect settles fitScale=1
    // and never re-runs — iframeRef is a ref, so the frame appearing re-renders
    // nothing. A deck then rendered its 992px stage 1:1 inside a ~370px column
    // (chat + DevTools open) and the member saw a slide's blank left margin: a
    // "broken" white canvas that was really an unfitted one. Re-running once the
    // projection lands measures the frame that now exists.
  }, [isStaged, isDeck, projected]);
  const effectiveZoom = fitScale * zoom;

  // Re-project on CONTENT change (not on file-object identity — useFileLoad
  // returns a fresh object on every reload even when content is byte-identical,
  // which would needlessly reload the iframe and flash it blank).
  const content = file.content;
  // ADR-524 D1 — the content a PATCH already applied to the live DOM. Re-
  // projecting for it would swap srcDoc and re-parse the document, which is
  // precisely the demolition the patch exists to avoid: the effect below would
  // undo the optimization on the very next tick, because `content` changed.
  //
  // This is why the patch had to reach into the projection effect and not just
  // add a message: `reload` was never the mechanism (applyOp has passed
  // reload:false for a long time). srcDoc is re-fed on EVERY content change,
  // including a plain text edit, so a patch that does not also suppress the
  // re-projection buys nothing at all.
  const patchedContentRef = useRef<string | null>(null);
  if (patch && patch.appliedFor != null) patchedContentRef.current = patch.appliedFor;
  useEffect(() => {
    let cancelled = false;
    if (content == null) {
      setProjected(null);
      return;
    }
    if (content === patchedContentRef.current) {
      // The live DOM already shows this exact content — the patch put it there.
      // Nothing to do; the next NON-patched change re-projects normally.
      return;
    }
    // ADR-446: `edit: true` stamps citation islands + injects the edit runtime
    // (harmless when nothing is being edited; the runtime idles until the
    // parent commands enter). One render mode keeps the projection stable
    // across select→edit→select without reloading the frame.
    resolveArtifactHtml(content, artifactPath, { pointer: true, edit: true, mode, measureBounds, blockLabels })
      .then((html) => !cancelled && setProjected(html))
      // NEVER fall back to raw content: the iframe allows scripts, and only
      // the projection pass strips artifact-authored executables. A blank
      // canvas beats an unstripped one — but leave a breadcrumb, because a
      // silent catch here renders as an undiagnosable white canvas.
      .catch((e) => {
        console.error('[STUDIO] projection failed — canvas blanked:', e);
        if (!cancelled) setProjected('');
      });
    return () => {
      cancelled = true;
    };
    // ADR-480: `mode` is a projection input (it stamps data-yarnnn-mode), so it
    // must re-project when the served vocabulary lands — the surface defaults to
    // 'flow' until then, and a deck would otherwise keep the flow runtime.
    // ADR-485 D3: `measureBounds` is a projection input for the same reason —
    // it is baked into the injected script, so a vocabulary that lands after
    // the first projection must re-inject or the gesture keeps the fallback.
  }, [content, artifactPath, mode, measureBounds, blockLabels]);

  // Command the iframe's edit runtime when the surface's editing state changes
  // AND on every fresh load (a reload after a commit reinjects the runtime; it
  // idles until told to enter). A ref carries the latest editing block so the
  // load handler re-posts the current state without re-binding.
  const editingRef = useRef<string | null>(editingBlockId ?? null);
  editingRef.current = editingBlockId ?? null;
  const selectedRef = useRef<string | null>(selectedBlockId ?? null);
  selectedRef.current = selectedBlockId ?? null;
  const zoomRef = useRef(effectiveZoom);
  zoomRef.current = effectiveZoom;
  const stageRef = useRef(stage);
  stageRef.current = stage;

  // The latest position the runtime reported (opaque origin — the parent can't
  // read scrollTop, so the runtime posts it). Restored after a structural reload
  // so the canvas doesn't jump to the top (the invisible-save follow-on: text
  // edits no longer reload at all; the reloads that DO remain — structural ops,
  // foreign/AI writes — preserve the position). The runtime owns the anchoring
  // UNIT: `slide` (deck) is zoom-independent and survives a re-arrange; `y`
  // (fluid document) is the pixel fallback. We hand back BOTH; the runtime
  // prefers the slide.
  const scrollPosRef = useRef<{ y: number; slide: number | null }>({ y: 0, slide: null });
  // ADR-522 D3: the surface's viewport listener, held by ref so the message
  // handler below stays stably bound (see the call site).
  const onScrollPosRef = useRef(onScrollPos);
  onScrollPosRef.current = onScrollPos;


  const commandEdit = useCallback(() => {
    const win = iframeRef.current?.contentWindow;
    if (!win) return;
    const id = editingRef.current;
    if (id) win.postMessage({ type: 'yarnnn-edit-enter', blockId: id }, '*');
    else win.postMessage({ type: 'yarnnn-edit-exit' }, '*');
    // ADR-466 P9: restore the SELECTION too — a fresh load (optimistic-op
    // re-projection, foreign write) reset the runtime's state, so the bounding
    // box vanished the moment any gesture committed.
    if (!id && selectedRef.current) {
      win.postMessage({ type: 'yarnnn-select-block', blockId: selectedRef.current }, '*');
    }
    // Re-apply the current zoom on a fresh load (the runtime resets on reload).
    win.postMessage({ type: 'yarnnn-zoom', scale: zoomRef.current }, '*');
    // ADR-520 D1: re-enable the stage view BEFORE the position restore — the
    // restore's slide index is what re-shows the remembered stage.
    win.postMessage({ type: 'yarnnn-view-mode', stage: stageRef.current }, '*');
    // Restore the pre-reload position (a no-op at slide 0 / y=0 / first load).
    const pos = scrollPosRef.current;
    if (pos.slide != null || pos.y > 0) {
      win.postMessage({ type: 'yarnnn-restore-scroll', y: pos.y, slide: pos.slide }, '*');
    }
  }, []);

  // On editing-state change, command immediately (the runtime is already live).
  useEffect(() => {
    commandEdit();
  }, [editingBlockId, commandEdit]);

  // ADR-516 D5 — a PARENT-side selection (the navigator's structure tree, the
  // Design tab) reaches the LIVE runtime too, not only the reload-restore
  // above (ADR-466 P9's `yarnnn-select-block` fired solely on fresh load, so a
  // tree click switched the pane scope while the canvas drew nothing — the
  // selection was real and invisible, on blocks and containers alike).
  useEffect(() => {
    if (!selectedBlockId || editingRef.current) return;
    const win = iframeRef.current?.contentWindow;
    if (win) win.postMessage({ type: 'yarnnn-select-block', blockId: selectedBlockId }, '*');
  }, [selectedBlockId]);

  // On zoom change (operator zoom OR auto-fit rescale), command it (no reload
  // needed — view-only).
  useEffect(() => {
    iframeRef.current?.contentWindow?.postMessage({ type: 'yarnnn-zoom', scale: effectiveZoom }, '*');
  }, [effectiveZoom]);

  // ADR-520 D1: stage mode follows the template (deck ↔ on). View-only.
  useEffect(() => {
    iframeRef.current?.contentWindow?.postMessage({ type: 'yarnnn-view-mode', stage }, '*');
  }, [stage]);

  // ADR-447: when the navigator selects a slide, scroll the canvas to it (the
  // nonce re-fires even on re-selecting the same slide).
  useEffect(() => {
    const win = iframeRef.current?.contentWindow;
    if (!win || !scrollToSlide) return;
    win.postMessage({ type: 'yarnnn-scroll-to-slide', index: scrollToSlide.index }, '*');
  }, [scrollToSlide]);

  // A slash pick landed: tell the runtime to consume the '/'+filter run and
  // report the halves around it (only it can see which text node holds them).
  useEffect(() => {
    const win = iframeRef.current?.contentWindow;
    if (!win || !slashTake) return;
    win.postMessage({ type: 'yarnnn-slash-take', filterLen: slashTake.filterLen }, '*');
  }, [slashTake]);


  // ADR-527 D4 — the pane's format op reaches the edit runtime.
  useEffect(() => {
    const win = iframeRef.current?.contentWindow;
    if (!win || !fmtCmd) return;
    win.postMessage({ type: 'yarnnn-fmt-op', op: fmtCmd.op, value: fmtCmd.value }, '*');
  }, [fmtCmd]);

  // ADR-455: when the outline selects a heading, scroll the canvas to it.
  useEffect(() => {
    const win = iframeRef.current?.contentWindow;
    if (!win || !scrollToBlock) return;
    win.postMessage({ type: 'yarnnn-scroll-to-block', blockId: scrollToBlock.blockId }, '*');
  }, [scrollToBlock]);

  // ADR-524 D1 — the patch channel. A block-local op sends its projected block
  // here instead of swapping srcDoc, so the document is never re-parsed and the
  // member's scroll/caret/selection/zoom survive untouched.
  //
  // `patch` carries a nonce like the other command props, so re-patching the
  // same block with the same html still fires. The projection happens in the
  // SURFACE (it is async and needs the artifact path); this only forwards.
  useEffect(() => {
    const win = iframeRef.current?.contentWindow;
    if (!win || !patch) return;
    // ADR-547 D2 — one message per touched block. The runtime's verb is already
    // per-block (it replaces one element and skips the caret host), so N blocks
    // is N ordinary patches rather than a new bulk verb — rule 7, an existing op
    // reached through a wider grain.
    for (const b of patch.blocks) {
      win.postMessage({ type: 'yarnnn-patch', blockId: b.blockId, html: b.html }, '*');
    }
  }, [patch]);

  useEffect(() => {
    const handler = (e: MessageEvent) => {
      const d = e.data;
      if (!d || typeof d !== 'object') return;
      // The member is interacting INSIDE the frame — so a caret we restore after
      // a re-projection is one they had, not one we invented (see commandEdit).
      // Any in-frame message proves the focus; the point/slash ones additionally
      // name the block worth landing in.
      if (typeof d.type === 'string' && d.type.startsWith('yarnnn-')) {
      }
      if (d.type === 'yarnnn-point' && typeof d.tag === 'string') {
        onPoint?.({
          tag: d.tag,
          text: typeof d.text === 'string' ? d.text : '',
          dataRef: typeof d.dataRef === 'string' ? d.dataRef : null,
          blockId: typeof d.blockId === 'string' ? d.blockId : null,
          blockKind: typeof d.blockKind === 'string' ? d.blockKind : null,
          slideIndex: typeof d.slideIndex === 'number' ? d.slideIndex : null,
          pageIndex: typeof d.pageIndex === 'number' ? d.pageIndex : null,
          slot: typeof d.slot === 'string' ? d.slot : null,
          arrange: typeof d.arrange === 'string' ? d.arrange : null,
          label: typeof d.label === 'string' ? d.label : null,
          // ADR-522 D4 — the enclosing heading on flow ("this section").
          headingId: typeof d.headingId === 'string' ? d.headingId : null,
          headingText: typeof d.headingText === 'string' ? d.headingText : null,
          // ADR-525 D1 — the selection's tier, as the runtime declared it.
          tier:
            d.tier === 'text' || d.tier === 'object' || d.tier === 'structure'
              ? d.tier
              : null,
        });
      } else if (d.type === 'yarnnn-range' && Array.isArray(d.blockIds)) {
        // ADR-528 — the blocks a live text RANGE intersects. Distinct from
        // onPoint, which reports a CLICK: a drag across six blocks never
        // fired onPoint again, so the pane kept describing the block that
        // was clicked into. Empty array = the range collapsed.
        onRange?.(
          (d.blockIds as unknown[]).filter((x): x is string => typeof x === 'string'),
          // ADR-546 D3 — parallel to blockIds by construction (the runtime pushes
          // both in one loop). Absent from an older projection still live in the
          // iframe, which the parent handles by falling back to a bare count.
          Array.isArray(d.rungs) ? (d.rungs as RangeRung[]) : undefined,
        );
      } else if (d.type === 'yarnnn-point-clear') {
        onPointClear?.();
      } else if (
        d.type === 'yarnnn-edit' &&
        typeof d.blockId === 'string' &&
        typeof d.newInner === 'string'
      ) {
        onEdit?.(d.blockId, d.newInner);
      } else if (d.type === 'yarnnn-scroll-pos' && typeof d.y === 'number') {
        // Keep the latest position so a structural reload can restore it — the
        // slide index (deck) alongside the pixel y (fluid fallback).
        scrollPosRef.current = {
          y: d.y,
          slide: typeof d.slide === 'number' ? d.slide : null,
        };
        // ADR-522 D3: the same reading, surfaced. The ref above is RESTORE
        // state (it survives a reload); this is the live viewport the surface
        // declares as focus. One payload, two consumers.
        //
        // Through a ref, NOT the dependency array below: this fires on every
        // scroll settle, and mounts pass an inline callback — listing it as a
        // dep would tear down and re-bind the whole message listener on each
        // report.
        onScrollPosRef.current?.(scrollPosRef.current);
      } else if (d.type === 'yarnnn-edit-exited') {
        onEditExited?.();
      } else if (d.type === 'yarnnn-edit-entered' && typeof d.blockId === 'string') {
        onEditEntered?.(d.blockId);
      } else if (d.type === 'yarnnn-enter-block' && typeof d.afterBlockId === 'string') {
        onEnterBlock?.(d.afterBlockId);
      } else if (d.type === 'yarnnn-geometry' && typeof d.blockId === 'string') {
        onGeometry?.(d.blockId, {
          x: typeof d.x === 'number' ? d.x : undefined,
          y: typeof d.y === 'number' ? d.y : undefined,
          w: typeof d.w === 'number' ? d.w : undefined,
          h: typeof d.h === 'number' ? d.h : undefined,
        });
      } else if (d.type === 'yarnnn-geometry-many' && Array.isArray(d.moves)) {
        // A group drop or group resize — ONE act, so it lands as ONE revision
        // (the runtime batches; the parent must not re-split it into N writes).
        const moves = (d.moves as Array<Record<string, unknown>>)
          .filter((m) => typeof m.blockId === 'string')
          .map((m) => ({
            blockId: m.blockId as string,
            geo: {
              x: typeof m.x === 'number' ? m.x : undefined,
              y: typeof m.y === 'number' ? m.y : undefined,
              // A group RESIZE carries size too; a group MOVE omits both, and
              // setGeometry preserves an axis it is not given.
              w: typeof m.w === 'number' ? m.w : undefined,
              h: typeof m.h === 'number' ? m.h : undefined,
            },
          }));
        if (moves.length) onGeometryMany?.(moves);
      } else if (d.type === 'yarnnn-refused' && typeof d.reason === 'string') {
        // ADR-544 D5.1 — the runtime refused an illegal gesture. It must SAY so:
        // a gesture that silently does nothing is the inert affordance this ADR
        // keeps finding. The parent owns the words (one notice, ADR-541 D4).
        onRefused?.(d.reason as string);
      } else if (d.type === 'yarnnn-group' && Array.isArray(d.blockIds)) {
        onGroup?.((d.blockIds as unknown[]).filter((b): b is string => typeof b === 'string'));
      } else if (d.type === 'yarnnn-key-verb' && typeof d.blockId === 'string') {
        onKeyVerb?.(d.verb as 'copy' | 'paste' | 'duplicate' | 'delete' | 'up' | 'down', d.blockId);
      } else if (d.type === 'yarnnn-undo') {
        onUndo?.();
      } else if (d.type === 'yarnnn-redo') {
        onRedo?.();
      } else if (d.type === 'yarnnn-context-menu' && typeof d.x === 'number') {
        // The runtime reports the pointer's iframe-VIEWPORT coordinates
        // (e.clientX/Y). The menu draws in the parent page, so we offset by the
        // iframe element's page position. NO zoom multiply: the canvas zooms the
        // artifact via `body.style.zoom`, which rescales the document's LAYOUT
        // but not the iframe element's own viewport — a pointer's clientX stays
        // in [0, iframeWidth] at every zoom. Multiplying by the zoom put the
        // menu at ~37% of the offset on a deck (whose auto-fit zoom is ~0.37),
        // landing it up-left of the cursor. d.x already IS the iframe-box pixel.
        const r = iframeRef.current?.getBoundingClientRect();
        onContextMenu?.({
          ...(d as unknown as StudioContextTarget),
          x: (r?.left ?? 0) + (d.x as number),
          y: (r?.top ?? 0) + (d.y as number),
        });
      } else if (d.type === 'yarnnn-ratio' && typeof d.pageIndex === 'number') {
        // ADR-461 D3: the column divider dropped on a STOP. It carries the
        // token's value (or null = the even default), never a width — the
        // gesture composes setToken, it is not a second write path.
        onRatio?.(d.pageIndex, typeof d.value === 'string' ? d.value : null);
      } else if (
        d.type === 'yarnnn-split-block' &&
        typeof d.blockId === 'string' &&
        typeof d.newId === 'string'
      ) {
        onSplitBlock?.(d.blockId, d.newId, String(d.beforeInner ?? ''), String(d.afterInner ?? ''));
      } else if (
        d.type === 'yarnnn-merge-block' &&
        typeof d.blockId === 'string' &&
        typeof d.prevBlockId === 'string'
      ) {
        onMergeBlock?.(d.blockId, d.prevBlockId, String(d.mergedInner ?? ''));
      } else if (d.type === 'yarnnn-add-here' && typeof d.slot === 'string') {
        onAddHere?.(
          d.slot,
          typeof d.slideIndex === 'number' ? d.slideIndex : null,
          typeof d.pageIndex === 'number' ? d.pageIndex : null,
          typeof d.arrange === 'string' ? d.arrange : null,
          typeof d.containerId === 'string' && d.containerId ? d.containerId : null,
        );
      } else if (d.type === 'yarnnn-selection-rect') {
        if (!d.rect || typeof d.rect !== 'object') {
          onSelectionRect?.(null, null);
        } else {
          const f = iframeRef.current?.getBoundingClientRect();
          const r = d.rect as Record<string, number>;
          onSelectionRect?.(
            {
              left: (f?.left ?? 0) + (Number(r.left) || 0),
              top: (f?.top ?? 0) + (Number(r.top) || 0),
              right: (f?.left ?? 0) + (Number(r.right) || 0),
              bottom: (f?.top ?? 0) + (Number(r.bottom) || 0),
            },
            typeof d.grain === 'string' ? d.grain : null,
          );
        }
      } else if (
        d.type === 'yarnnn-slash-open' &&
        typeof d.blockId === 'string' &&
        d.rect &&
        typeof d.rect === 'object'
      ) {
        onSlashOpen?.(d.blockId, !!d.empty, {
          left: Number(d.rect.left) || 0,
          top: Number(d.rect.top) || 0,
          bottom: Number(d.rect.bottom) || 0,
          width: Number(d.rect.width) || 0,
        });
      } else if (d.type === 'yarnnn-slash-filter' && typeof d.filter === 'string') {
        onSlashFilter?.(d.filter);
      } else if (d.type === 'yarnnn-slash-close') {
        onSlashClose?.();
      } else if (d.type === 'yarnnn-slash-move' && typeof d.delta === 'number') {
        onSlashMove?.(d.delta);
      } else if (d.type === 'yarnnn-slash-enter') {
        onSlashEnter?.();
      } else if (d.type === 'yarnnn-slash-taken' && typeof d.blockId === 'string') {
        onSlashTaken?.(
          d.blockId,
          typeof d.beforeInner === 'string' ? d.beforeInner : null,
          typeof d.afterInner === 'string' ? d.afterInner : null,
        );
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [onPoint, onPointClear, onRange, onEdit, onEditExited, onEditEntered, onEnterBlock, onSplitBlock, onMergeBlock, onAddHere, onSelectionRect, onSlashOpen, onSlashFilter, onSlashClose, onSlashMove, onSlashEnter, onSlashTaken, onKeyVerb, onGeometry, onGeometryMany, onGroup, onRatio, onContextMenu, onUndo, onRedo]);

  return (
    <iframe
      ref={iframeRef}
      title={artifactPath}
      srcDoc={projected ?? ''}
      sandbox="allow-scripts"
      // Re-command edit state once the fresh document's runtime is live —
      // closes the race where a state-change postMessage beats iframe parse.
      onLoad={commandEdit}
      className="flex-1 w-full h-full border-0 bg-white"
    />
  );
}
