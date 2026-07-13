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
  /** ADR-447 Phase 4 + ADR-453 D5: the member clicked "+ Add here" in an empty
   *  slot — the surface gates the add by the slot's ROLE (arrange + vocabulary
   *  lookup) and targets the page (slideIndex for decks, pageIndex otherwise). */
  onAddHere?: (
    slot: string,
    slideIndex: number | null,
    pageIndex: number | null,
    arrange: string | null,
  ) => void;
  /** ADR-447: scroll the canvas to this slide (the navigator selected it). A
   *  monotonic nonce forces the scroll even when re-selecting the same slide. */
  scrollToSlide?: { index: number; nonce: number } | null;
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
  onAddHere,
  scrollToSlide,
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
  }, [isDeck]);
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

  const commandEdit = useCallback(() => {
    const win = iframeRef.current?.contentWindow;
    if (!win) return;
    const id = editingRef.current;
    if (id) win.postMessage({ type: 'yarnnn-edit-enter', blockId: id }, '*');
    else win.postMessage({ type: 'yarnnn-edit-exit' }, '*');
    // Re-apply the current zoom on a fresh load (the runtime resets on reload).
    win.postMessage({ type: 'yarnnn-zoom', scale: zoomRef.current }, '*');
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
        });
      } else if (d.type === 'yarnnn-point-clear') {
        onPointClear?.();
      } else if (
        d.type === 'yarnnn-edit' &&
        typeof d.blockId === 'string' &&
        typeof d.newInner === 'string'
      ) {
        onEdit?.(d.blockId, d.newInner);
      } else if (d.type === 'yarnnn-edit-exited') {
        onEditExited?.();
      } else if (d.type === 'yarnnn-edit-entered' && typeof d.blockId === 'string') {
        onEditEntered?.(d.blockId);
      } else if (d.type === 'yarnnn-add-here' && typeof d.slot === 'string') {
        onAddHere?.(
          d.slot,
          typeof d.slideIndex === 'number' ? d.slideIndex : null,
          typeof d.pageIndex === 'number' ? d.pageIndex : null,
          typeof d.arrange === 'string' ? d.arrange : null,
        );
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [onPoint, onPointClear, onEdit, onEditExited, onEditEntered, onAddHere]);

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
