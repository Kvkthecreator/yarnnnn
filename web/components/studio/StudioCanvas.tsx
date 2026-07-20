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

import { useCallback, useEffect, useRef, useState } from 'react';
import type { WorkspaceFile } from '@/types';
import { resolveArtifactHtml } from '@/components/workspace/viewers/projection';

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
  /** ADR-458 — the hover gutter's ⋮⋮ asked for the Design tab (select AND
   *  flip the right column; the verbs' one home). */
  design?: boolean;
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
  /** ADR-446: the block currently being edited in place (null = none). The
   *  surface holds this state; the canvas commands the iframe runtime. */
  editingBlockId?: string | null;
  /** ADR-446: a block edit committed (blur/idle) — {blockId, newInner} mapped
   *  to the SOURCE (citation islands already restored). The surface lands it
   *  through the mechanical write door. */
  onEdit?: (blockId: string, newInner: string) => void;
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
  onReorder?: (blockId: string, beforeBlockId: string | null) => void;
  /** ADR-466 P8: a bounding-box gesture landed — any combination of position
   *  (x/y, a body drag) and width (w, a corner handle; a west handle on a
   *  positioned block moves origin AND width together), all as PERCENTS of
   *  the block's frame. The surface clamps from the kernel's served bound and
   *  lands setGeometry (ONE revision per gesture) through the one door. */
  onGeometry?: (blockId: string, geo: { x?: number; y?: number; w?: number }) => void;
  /** ADR-462 D7: the member right-clicked the canvas. The runtime has ALREADY
   *  selected the block under the cursor (right-click selects), so this only
   *  carries where to anchor + the grain the menu builds its rows from.
   *  `framed` is the runtime's answer to the ADR-461 D4 gate — only it can see
   *  the DOM, so it reports rather than letting the surface guess. */
  onContextMenu?: (m: StudioContextTarget) => void;
  /** ADR-462 D10: a keyboard verb on the SELECTED block. The canvas is a
   *  sandboxed iframe — keys land in its document or nowhere — so the runtime
   *  hears them and posts an existing verb out. Never a new op. */
  onKeyVerb?: (verb: 'copy' | 'paste' | 'duplicate' | 'delete', blockId: string) => void;
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
  /** ADR-447 Phase 4 + ADR-453 D5: the member clicked "+ Add here" in an empty
   *  slot — the surface gates the add by the slot's ROLE (arrange + vocabulary
   *  lookup) and targets the page (slideIndex for decks, pageIndex otherwise). */
  onAddHere?: (
    slot: string,
    slideIndex: number | null,
    pageIndex: number | null,
    arrange: string | null,
  ) => void;
  /** ADR-456 W2: the member typed '/' in an empty context — the runtime
   *  committed + exited the edit; the surface opens the block palette anchored
   *  at the block's rect (frame-viewport coordinates ≈ iframe-box pixels).
   *  `empty` = the whole block was empty (the palette converts it in place
   *  instead of inserting after it). */
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
  /** ADR-447: scroll the canvas to this slide (the navigator selected it). A
   *  monotonic nonce forces the scroll even when re-selecting the same slide. */
  scrollToSlide?: { index: number; nonce: number } | null;
  /** ADR-455: scroll the canvas to this heading block (the outline navigates). */
  scrollToBlock?: { blockId: string; nonce: number } | null;
  /** ADR-447: zoom the rendered document (a VIEW control — 1 = 100%). Never a
   *  file change; the artifact's real dimensions are untouched. */
  zoom?: number;
}

// A deck slide's natural landscape stage (ADR-447 D7.7) — the projection pins
// deck slides to this fixed box in the canvas so a narrow column can't collapse
// them (see DECK_STAGE_W in projection.ts). The canvas then AUTO-FITS: it scales
// the stage down so the 992px-wide slide fits the actual column width, and the
// operator's zoom rides on top of that fit. Documents/articles are fluid (no
// fixed stage), so they get no fit — their base is 1.
const DECK_STAGE_W = 992;

export function StudioCanvas({
  file,
  artifactPath,
  onPoint,
  onPointClear,
  editingBlockId,
  onEdit,
  onEditExited,
  onEditEntered,
  onEnterBlock,
  onReorder,
  onRatio,
  onGeometry,
  onContextMenu,
  onKeyVerb,
  onSplitBlock,
  onMergeBlock,
  onAddHere,
  onSlashOpen,
  onSlashFilter,
  onSlashClose,
  onSlashMove,
  onSlashEnter,
  onSlashTaken,
  scrollToSlide,
  slashTake,
  scrollToBlock,
  zoom = 1,
}: StudioCanvasProps) {
  const [projected, setProjected] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Is this a deck? (the projection pins deck slides to a fixed stage.) The root
  // carries data-template="deck"; a cheap string test avoids re-parsing.
  const isDeck = file.content?.includes('data-template="deck"') ?? false;

  // The auto-fit scale: for a deck, shrink the 992px stage to the column width
  // (never enlarge past 1); for fluid layouts, 1. Measured off the iframe's own
  // width via ResizeObserver so it tracks the column (chat drawer, DevTools,
  // window resize). The operator's `zoom` multiplies this base.
  const [fitScale, setFitScale] = useState(1);
  useEffect(() => {
    const frame = iframeRef.current;
    if (!frame || !isDeck) {
      setFitScale(1);
      return;
    }
    const measure = () => {
      const w = frame.clientWidth;
      if (w > 0) setFitScale(Math.min(1, w / DECK_STAGE_W));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(frame);
    return () => ro.disconnect();
    // `projected` is a dependency, not decoration: on first mount the content
    // has not loaded, so isDeck is false and this effect settles fitScale=1 and
    // never re-runs — iframeRef is a ref, so the frame appearing re-renders
    // nothing. A deck then rendered its 992px stage 1:1 inside a ~370px column
    // (chat + DevTools open) and the member saw a slide's blank left margin: a
    // "broken" white canvas that was really an unfitted one. Re-running once the
    // projection lands measures the frame that now exists.
  }, [isDeck, projected]);
  const effectiveZoom = fitScale * zoom;

  // Re-project on CONTENT change (not on file-object identity — useFileLoad
  // returns a fresh object on every reload even when content is byte-identical,
  // which would needlessly reload the iframe and flash it blank).
  const content = file.content;
  useEffect(() => {
    let cancelled = false;
    if (content == null) {
      setProjected(null);
      return;
    }
    // ADR-446: `edit: true` stamps citation islands + injects the edit runtime
    // (harmless when nothing is being edited; the runtime idles until the
    // parent commands enter). One render mode keeps the projection stable
    // across select→edit→select without reloading the frame.
    resolveArtifactHtml(content, artifactPath, { pointer: true, edit: true })
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
  }, [content, artifactPath]);

  // Command the iframe's edit runtime when the surface's editing state changes
  // AND on every fresh load (a reload after a commit reinjects the runtime; it
  // idles until told to enter). A ref carries the latest editing block so the
  // load handler re-posts the current state without re-binding.
  const editingRef = useRef<string | null>(editingBlockId ?? null);
  editingRef.current = editingBlockId ?? null;
  const zoomRef = useRef(effectiveZoom);
  zoomRef.current = effectiveZoom;

  // The latest position the runtime reported (opaque origin — the parent can't
  // read scrollTop, so the runtime posts it). Restored after a structural reload
  // so the canvas doesn't jump to the top (the invisible-save follow-on: text
  // edits no longer reload at all; the reloads that DO remain — structural ops,
  // foreign/AI writes — preserve the position). The runtime owns the anchoring
  // UNIT: `slide` (deck) is zoom-independent and survives a re-arrange; `y`
  // (fluid document) is the pixel fallback. We hand back BOTH; the runtime
  // prefers the slide.
  const scrollPosRef = useRef<{ y: number; slide: number | null }>({ y: 0, slide: null });

  const commandEdit = useCallback(() => {
    const win = iframeRef.current?.contentWindow;
    if (!win) return;
    const id = editingRef.current;
    if (id) win.postMessage({ type: 'yarnnn-edit-enter', blockId: id }, '*');
    else win.postMessage({ type: 'yarnnn-edit-exit' }, '*');
    // Re-apply the current zoom on a fresh load (the runtime resets on reload).
    win.postMessage({ type: 'yarnnn-zoom', scale: zoomRef.current }, '*');
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

  // On zoom change (operator zoom OR auto-fit rescale), command it (no reload
  // needed — view-only).
  useEffect(() => {
    iframeRef.current?.contentWindow?.postMessage({ type: 'yarnnn-zoom', scale: effectiveZoom }, '*');
  }, [effectiveZoom]);

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

  // ADR-455: when the outline selects a heading, scroll the canvas to it.
  useEffect(() => {
    const win = iframeRef.current?.contentWindow;
    if (!win || !scrollToBlock) return;
    win.postMessage({ type: 'yarnnn-scroll-to-block', blockId: scrollToBlock.blockId }, '*');
  }, [scrollToBlock]);

  useEffect(() => {
    const handler = (e: MessageEvent) => {
      const d = e.data;
      if (!d || typeof d !== 'object') return;
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
          design: d.design === true,
        });
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
      } else if (d.type === 'yarnnn-edit-exited') {
        onEditExited?.();
      } else if (d.type === 'yarnnn-edit-entered' && typeof d.blockId === 'string') {
        onEditEntered?.(d.blockId);
      } else if (d.type === 'yarnnn-enter-block' && typeof d.afterBlockId === 'string') {
        onEnterBlock?.(d.afterBlockId);
      } else if (d.type === 'yarnnn-reorder' && typeof d.blockId === 'string') {
        onReorder?.(d.blockId, typeof d.beforeBlockId === 'string' ? d.beforeBlockId : null);
      } else if (d.type === 'yarnnn-geometry' && typeof d.blockId === 'string') {
        onGeometry?.(d.blockId, {
          x: typeof d.x === 'number' ? d.x : undefined,
          y: typeof d.y === 'number' ? d.y : undefined,
          w: typeof d.w === 'number' ? d.w : undefined,
        });
      } else if (d.type === 'yarnnn-key-verb' && typeof d.blockId === 'string') {
        onKeyVerb?.(d.verb as 'copy' | 'paste' | 'duplicate' | 'delete', d.blockId);
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
        );
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
  }, [onPoint, onPointClear, onEdit, onEditExited, onEditEntered, onEnterBlock, onReorder, onSplitBlock, onMergeBlock, onAddHere, onSlashOpen, onSlashFilter, onSlashClose, onSlashMove, onSlashEnter, onSlashTaken]);

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
