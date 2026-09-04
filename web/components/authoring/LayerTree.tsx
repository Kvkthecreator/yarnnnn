'use client';

/**
 * LayerTree — the compositor's left rail (ADR-633 D4).
 *
 * The organ `PagedNavigator` is not. A deck's rail answers "which page"; an
 * artboard's rail answers "which layer, and at what depth". They are different
 * questions, so they are different components — ADR-633 D6 is explicit that
 * PagedNavigator keeps its single job rather than growing a second mode.
 *
 * ── WHY THIS EXISTS ────────────────────────────────────────────────────────
 * IMAGES' substrate has been a layer stack since ADR-472: an artboard is a
 * `<section class="slide" data-arrange="free">` whose blocks carry
 * `data-x`/`data-y`/`data-z`, and ADR-544 D3 re-grained those measures to
 * `artboard` so free position is an IMAGES-ONLY capability. `nudgeZ` has
 * written stacking order the whole time.
 *
 * What was missing was the VIEW. Depth was reachable only through a context
 * menu — on a surface whose entire purpose is composing overlapping objects.
 * In every compositor the operator has used (Figma, Illustrator, Photoshop,
 * Canva) the stack IS the left rail. This is that rail.
 *
 * ── THE TREE IS TWO LEVELS ─────────────────────────────────────────────────
 *     ▼ ▢ Square 1080×1080          ← artboard (a section.slide)
 *         ▣ WORK DIFFERENT   z:3    ← layers, TOP OF STACK FIRST
 *         ▣ subject cut-out  z:2
 *         ▣ gradient bg      z:1
 *     ▶ ▢ Story 1080×1920
 *
 * A file holds N artboards (the same ad at Square/Story/Wide). The substrate
 * already permits it — `STRUCTURAL_PAGE_SEL` matches repeatable `section.slide`
 * — so this is a chrome capability, not a substrate change.
 *
 * ── ORDER IS Z-DESCENDING ──────────────────────────────────────────────────
 * Top of stack first: the INVERSE of document order, and the convention every
 * compositor shares. A layer with no z sorts beneath those that have one (the
 * ADR-461 absence-default rule: a missing value degrades to natural behaviour,
 * never to zero), and layers that SHARE a z hold document order — a tie is a
 * legitimate authored state, not a defect to normalise.
 *
 * The z itself is read through `readMeasure`, the op module's one reader:
 * `setMeasure` writes `data-z=""` as a bare presence marker with the number in
 * `--yz`, so anything parsing the attribute reads a shape our own writer never
 * produces.
 *
 * ── WHAT THIS COMPONENT DOES NOT OWN ───────────────────────────────────────
 * Nothing about how an object BEHAVES. A drag hands the parent an ORDER — the
 * artboard's ids, top of stack first — and the parent writes it as a dense z
 * through `setGeometryMany`; this file never computes a depth (see
 * `commitDrop`). Selection is re-pointed by the parent, never fabricated here
 * (the canvas runtime is the only thing that can supply a complete
 * StudioSelection). This file is chrome — it decides what the member is SHOWN
 * and what it is CALLED, and nothing else (ADR-633 D1).
 *
 * Canonical reference: docs/adr/ADR-633-the-artboard-is-a-stack-of-layers.md
 */

import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, ChevronRight, Eye, EyeOff, Lock, Unlock } from 'lucide-react';
import { readMeasure } from './artifactOps';
import { STRUCTURAL_PAGE_SEL } from './structureLabels';
import { readStageSize } from './stageGeometry';

/** One layer — a positioned block on an artboard. */
export interface LayerNode {
  /** `data-block-id` — the address every op keys on. */
  id: string;
  /** `data-block` — the kind, for the icon and the fallback name. */
  kind: string;
  /** The member-facing name: the layer's own text, elided. Falls back to the
   *  kind's registry LABEL — never to the raw `data-block` slug, which is
   *  substrate vocabulary (ADR-544 D4: the chrome says the member's word). */
  name: string;
  /** Stacking order. `null` = unstamped; sorts beneath every stamped layer. */
  z: number | null;
  /** Presence-tokens (ADR-633 D5) — mirrored here so the row can render its
   *  state without a second DOM read per paint. */
  locked: boolean;
  hidden: boolean;
}

export interface ArtboardNode {
  /** Index in document order — the address `STRUCTURAL_PAGE_SEL` resolves. */
  index: number;
  /** The artboard's own name: its `data-title`, else its dimensions. An
   *  artboard is a FRAME, so its size is the honest default identity. */
  name: string;
  /** Real pixel dimensions (ADR-472 D3), for the subtitle. */
  w: number;
  h: number;
  layers: LayerNode[];
}

/** Elide a layer's text to a name. A layer is named by what it SAYS — the
 *  convention in every compositor — so the first line of its content is the
 *  identity a member scans for. */
function layerName(el: Element, fallback: string): string {
  const text = (el.textContent ?? '').replace(/\s+/g, ' ').trim();
  if (!text) return fallback;
  return text.length > 32 ? `${text.slice(0, 31)}…` : text;
}

/**
 * Read the artboard/layer tree out of the artifact's own HTML.
 *
 * DERIVED at render, never stored — the ADR-453 D1 convention every token in
 * this app already follows. The HTML is the model (ADR-443/446); a parallel
 * tree kept in state would be a second source that drifts the moment an op
 * lands from the canvas, the AI hand, or another member's revision.
 */
export function readLayerTree(html: string, labelFor: (kind: string) => string): ArtboardNode[] {
  if (!html) return [];
  let doc: Document;
  try {
    doc = new DOMParser().parseFromString(html, 'text/html');
  } catch {
    return [];
  }
  const boards = Array.from(doc.querySelectorAll(STRUCTURAL_PAGE_SEL));
  // The stage box is a DOCUMENT-level fact today: `readStageSize` resolves the
  // artifact's `--stage-w`/`--stage-h` (ADR-472 D3), which every artboard in
  // the file shares. Per-artboard dimensions are what multi-size composition
  // eventually wants, and the shape below is ready for it — but inventing a
  // per-board reader here would be a SECOND size authority beside the one the
  // canvas, the navigator and the raster export all already agree on.
  const stage = readStageSize(doc, 'image');
  return boards.map((board, index) => {
    // Only DIRECT block children are layers. A block nested inside another
    // block (a figure's caption) is that block's business, not a peer in the
    // stack — the same containment the canvas already honours.
    const blocks = Array.from(board.querySelectorAll(':scope > [data-block]'));
    const layers: LayerNode[] = blocks
      .map((el) => {
        // Through the op module's ONE reader: `setMeasure` writes `data-z=""`
        // as a bare presence marker and puts the number in `--yz`, so parsing
        // the attribute read a shape our own writer never produces — every
        // layer an op had touched came back z=null and sank to the bottom of
        // the rail. `readMeasure` prefers the var and honours a valued legacy
        // attribute, so hand- and AI-authored markup reads the same.
        const z = readMeasure(el, 'z', '--yz');
        const kind = el.getAttribute('data-block') ?? 'block';
        return {
          id: el.getAttribute('data-block-id') ?? '',
          kind,
          name: layerName(el, labelFor(kind)),
          z,
          locked: el.getAttribute('data-lock') === 'on',
          hidden: el.getAttribute('data-hide') === 'on',
        };
      })
      .filter((l) => l.id !== '');
    // TOP OF STACK FIRST. An unstamped layer (z === null) sits beneath every
    // stamped one, and ties hold document order — `sort` is stable, and the
    // array is already in document order, so equal keys keep their sequence.
    layers.sort((a, b) => (b.z ?? -1) - (a.z ?? -1));
    return {
      index,
      name: board.getAttribute('data-title') || `Artboard ${index + 1}`,
      w: Math.round(stage.width),
      h: Math.round(stage.height),
      layers,
    };
  });
}

interface LayerTreeProps {
  /** The artifact's SOURCE html — the one model this tree derives from. */
  html: string;
  /** The kind → operator-facing label map (ADR-544 D4), from the served
   *  registry. Passed in rather than read here: the vocabulary is the
   *  surface's to fetch, and a rail that fetched its own would be a second
   *  reader of the same table. */
  labelFor: (kind: string) => string;
  /** The selected layer's block id, if the primary selection is a block. */
  selectedBlockId: string | null;
  /** The selected artboard index — drives which board is highlighted when the
   *  selection is the frame itself rather than a layer on it. */
  selectedArtboard: number | null;
  /** Select an artboard by index. Same contract as the navigator's
   *  `onSelectSlide`: the parent scrolls the canvas and re-anchors scope. */
  onSelectArtboard: (index: number) => void;
  /** Select a LAYER. The parent re-points the live selection at this block id
   *  — it never fabricates a StudioSelection (only the canvas runtime can
   *  supply kind/slide/slot/arrange). */
  onSelectLayer: (blockId: string, artboardIndex: number) => void;
  /** Restack: the artboard's layer ids in their NEW display order, top of
   *  stack first. The rail hands over the whole ORDER, never one layer's new
   *  depth — see `commitDrop` for why a per-layer z cannot express the move.
   *  One gesture, one revision, through the geometry op the canvas uses. */
  onRestack: (orderedIds: string[], artboardIndex: number) => void;
  /** Toggle a presence-token (ADR-633 D5). `null` clears it. */
  onToggleToken: (blockId: string, key: 'lock' | 'hide', value: 'on' | null) => void;
}

const ROW =
  'group flex w-full items-center gap-1.5 rounded px-1.5 py-1 text-left text-xs transition-colors';

export function LayerTree({
  html,
  labelFor,
  selectedBlockId,
  selectedArtboard,
  onSelectArtboard,
  onSelectLayer,
  onRestack,
  onToggleToken,
}: LayerTreeProps) {
  const boards = useMemo(() => readLayerTree(html, labelFor), [html, labelFor]);
  // Collapsed artboards, by index. Every board starts OPEN: a compositor's
  // rail shows the stack, and a member who opens a one-artboard file to a
  // collapsed row would see an empty rail where the layers are the point.
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());
  // Drag-to-restack: the layer being dragged, and the gap it would land in
  // (an index into the DISPLAYED, z-descending order).
  const [drag, setDrag] = useState<{ board: number; id: string } | null>(null);
  const [dropAt, setDropAt] = useState<number | null>(null);
  const dragBoardRef = useRef<number | null>(null);

  useEffect(() => {
    // A board that disappears (deleted, or the file swapped) must not keep a
    // stale collapse flag — the next board to take that index would inherit it.
    setCollapsed((c) => {
      const next = new Set<number>();
      c.forEach((i) => {
        if (i < boards.length) next.add(i);
      });
      return next.size === c.size ? c : next;
    });
  }, [boards.length]);

  const toggleCollapse = useCallback((index: number) => {
    setCollapsed((c) => {
      const next = new Set(c);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }, []);

  /** Drop the dragged layer into display-gap `gap` on its own artboard.
   *
   *  ⭐ THE RAIL HANDS OVER AN ORDER, NEVER A DEPTH. The first cut computed one
   *  layer's new z arithmetically (`top - 1 - target`), which is only correct
   *  when the stack's z values are a dense, unique `N-1 … 0` permutation.
   *  Nothing makes them so: an agent authors z by INTENT (background 1, scrim
   *  2, type 5), and the one production artboard carries 5 distinct values
   *  across 10 layers with 7 of them tied. Against real bytes that arithmetic
   *  dropped a layer in the wrong slot and inflated z toward the registry
   *  ceiling until writes clamped and the rail stopped moving at all.
   *
   *  A tie is not a defect to repair — two layers CAN share a depth, and
   *  document order breaks it (the stable sort above). But a member dragging a
   *  row is stating a total order, and the only faithful way to record one is
   *  to write it: renumber the artboard densely, top of stack first. Ties
   *  collapse because the member just resolved them, not because we normalised
   *  behind their back.
   *
   *  This component's whole job at the seam is turning the drop into that
   *  ORDER; the WRITE — one revision, clamped from the served spec — is the
   *  shared op's. */
  const commitDrop = useCallback(
    (board: ArtboardNode, gap: number) => {
      if (!drag) return;
      const from = board.layers.findIndex((l) => l.id === drag.id);
      if (from < 0 || gap === from || gap === from + 1) return; // no-op
      const ids = board.layers.map((l) => l.id);
      const [moved] = ids.splice(from, 1);
      // Removing the dragged row shifts every later gap left by one.
      ids.splice(gap > from ? gap - 1 : gap, 0, moved);
      onRestack(ids, board.index);
      setDrag(null);
      setDropAt(null);
    },
    [drag, onRestack],
  );

  if (boards.length === 0) {
    return (
      <div className="flex h-full w-full flex-col p-2">
        <p className="px-1 pb-2 pt-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          Layers
        </p>
        <p className="px-1 text-xs text-muted-foreground">No artboards yet.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full flex-col overflow-y-auto p-2">
      <div className="flex items-center justify-between gap-2 px-1 pb-2 pt-1">
        <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          Layers
        </p>
      </div>
      <ul className="flex flex-col gap-0.5">
        {boards.map((board) => {
          const isOpen = !collapsed.has(board.index);
          const boardSelected = selectedArtboard === board.index && !selectedBlockId;
          return (
            <li key={board.index}>
              {/* The ARTBOARD row — the frame, named by its size (ADR-633 D3:
                  an artboard is an Artboard, never a Slide). */}
              <div
                className={`${ROW} ${
                  boardSelected ? 'bg-accent text-accent-foreground' : 'hover:bg-muted'
                }`}
              >
                <button
                  type="button"
                  aria-label={isOpen ? `Collapse ${board.name}` : `Expand ${board.name}`}
                  className="shrink-0 rounded p-0.5 hover:bg-background/60"
                  onClick={() => toggleCollapse(board.index)}
                >
                  {isOpen ? (
                    <ChevronDown className="h-3 w-3" />
                  ) : (
                    <ChevronRight className="h-3 w-3" />
                  )}
                </button>
                <button
                  type="button"
                  className="flex min-w-0 flex-1 items-baseline gap-1.5 text-left"
                  onClick={() => onSelectArtboard(board.index)}
                >
                  <span className="truncate font-medium">{board.name}</span>
                  {board.w > 0 && board.h > 0 && (
                    <span className="shrink-0 text-[10px] text-muted-foreground">
                      {board.w}×{board.h}
                    </span>
                  )}
                </button>
              </div>
              {isOpen && (
                <ul className="ml-4 flex flex-col gap-0.5 border-l border-border pl-1.5">
                  {board.layers.length === 0 && (
                    <li className="px-1.5 py-1 text-[11px] text-muted-foreground">
                      No layers yet.
                    </li>
                  )}
                  {board.layers.map((layer, i) => {
                    const isSel = selectedBlockId === layer.id;
                    const dropping =
                      drag?.board === board.index && dropAt === i && drag.id !== layer.id;
                    return (
                      <li
                        key={layer.id}
                        draggable
                        onDragStart={() => {
                          setDrag({ board: board.index, id: layer.id });
                          dragBoardRef.current = board.index;
                        }}
                        onDragEnd={() => {
                          setDrag(null);
                          setDropAt(null);
                        }}
                        onDragOver={(e) => {
                          // Restacking is WITHIN one artboard. Cross-board
                          // moves are a different act (they change which frame
                          // owns the layer) and are not decided by ADR-633.
                          if (dragBoardRef.current !== board.index) return;
                          e.preventDefault();
                          const r = e.currentTarget.getBoundingClientRect();
                          setDropAt(e.clientY < r.top + r.height / 2 ? i : i + 1);
                        }}
                        onDrop={(e) => {
                          if (dragBoardRef.current !== board.index) return;
                          e.preventDefault();
                          if (dropAt !== null) commitDrop(board, dropAt);
                        }}
                        className={dropping ? 'border-t-2 border-primary' : undefined}
                      >
                        <div
                          className={`${ROW} ${
                            isSel ? 'bg-accent text-accent-foreground' : 'hover:bg-muted'
                          } ${layer.hidden ? 'opacity-50' : ''}`}
                        >
                          <button
                            type="button"
                            className="flex min-w-0 flex-1 items-center gap-1.5 text-left"
                            onClick={() => onSelectLayer(layer.id, board.index)}
                          >
                            <span className="truncate">{layer.name}</span>
                          </button>
                          {/* Lock + hide live ON THE ROW, not in a menu — they
                              are the two properties a member toggles while
                              scanning the stack, which is why every compositor
                              puts them here. */}
                          <button
                            type="button"
                            aria-label={layer.hidden ? `Show ${layer.name}` : `Hide ${layer.name}`}
                            className={`shrink-0 rounded p-0.5 hover:bg-background/60 ${
                              layer.hidden ? '' : 'opacity-0 group-hover:opacity-100'
                            }`}
                            onClick={() =>
                              onToggleToken(layer.id, 'hide', layer.hidden ? null : 'on')
                            }
                          >
                            {layer.hidden ? (
                              <EyeOff className="h-3 w-3" />
                            ) : (
                              <Eye className="h-3 w-3" />
                            )}
                          </button>
                          <button
                            type="button"
                            aria-label={layer.locked ? `Unlock ${layer.name}` : `Lock ${layer.name}`}
                            className={`shrink-0 rounded p-0.5 hover:bg-background/60 ${
                              layer.locked ? '' : 'opacity-0 group-hover:opacity-100'
                            }`}
                            onClick={() =>
                              onToggleToken(layer.id, 'lock', layer.locked ? null : 'on')
                            }
                          >
                            {layer.locked ? (
                              <Lock className="h-3 w-3" />
                            ) : (
                              <Unlock className="h-3 w-3" />
                            )}
                          </button>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default memo(LayerTree);
