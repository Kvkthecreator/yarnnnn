'use client';

/**
 * StudioToolbar — the PAGE-grain toolbar (ADR-444 executing toolbar,
 * grain-realigned by ADR-453 D3; the page-verb PAIR per ADR-466 D5).
 *
 * Verbs, in operator words (paged layouts only — flow layouts insert at the
 * pointer and have no page unit):
 *  - New slide/section + — add a page from the arrangement GALLERY (derived
 *                          wireframe thumbnails, ADR-447 D7.1).
 *  - Re-arrange          — re-lay the CURRENT page (the PowerPoint pair). Since
 *                          2026-07-21 this is the ONE mount: the Properties
 *                          page-scope gallery was deleted as a full duplicate,
 *                          and the label follows the ACT, not the noun.
 *
 * `Media ▾` is DELETED (ADR-466 D4): the picker-backed kinds (Image / Table /
 * Gallery) now live in the located palette, which opens StudioCitablePicker at
 * the insertion point; Chart seeds the lane from the same palette. Insert is
 * located, with no exceptions — the AUTHORING.md named follow-on, executed.
 *
 * The selection chip is GONE (2026-07-15) — ADR-453 D3's "acknowledgment" was
 * the receipt for a selection-gated world that ADR-458 replaced with hover.
 * Every button EXECUTES a deterministic op through the one mechanical door.
 */

import { useEffect, useRef, useState } from 'react';
import { LayoutTemplate, Plus } from 'lucide-react';
import { ArrangementThumb } from './ArrangementThumb';

/** An arrangement (ADR-447) — the composition shape of a page/slide.
 *
 *  ADR-544 D2 — `slots` became `areas`: an AREA is the region grain, typed by
 *  a role from the closed set (heading | body | media | aside) with an optional
 *  `place` telling same-role siblings apart. The role is the Area's IDENTITY —
 *  the chrome labels from it (D4) and a re-lay maps by it (D6) — not the hint
 *  it was when only the media picker read it. */
export interface StudioArrangement {
  slug: string;
  label: string;
  description: string;
  grain: string;
  areas: Array<{ name: string; role: string; place?: string }>;
  fragment: string;
}

/** A property token family (ADR-453 D1) — tokens, not pixels.
 *  ADR-542 D1: WHERE (scope) and WHEN (grains) are two declared axes; the
 *  compound `applies` slugs are retired from the wire. */
export interface StudioToken {
  key: string;
  label: string;
  scope: string[];
  grains: string[];
  values: Array<{ value: string; label: string }>;
  description: string;
}

/** A MEASURE (ADR-461 D4) — the one continuous property. A token's values are
 *  enumerated and the kernel pre-declares a selector per value; a measure's are
 *  not, so the kernel pre-declares the MECHANISM (`width: var(--yw, auto)`) and
 *  the element carries the value. Bounded: free WITHIN its frame, never
 *  unbounded — which is why the grains are staged + media only (a slide has a
 *  frame; a page has only a viewport to guess at). */
export interface StudioMeasure {
  key: string;
  label: string;
  scope: string[];
  grains: string[];
  unit: string;
  min: number;
  max: number;
  css_var: string;
  description: string;
}

export interface StudioVocabulary {
  /** ADR-528 D5 — `apps` names which apps OFFER this kind; null = every app
   *  (the served default, carried by all but the two rows Docs does not
   *  offer). The surface filters ONCE at the vocabulary load site, so every
   *  consumer of this array already holds the app's own roster. */
  blocks: Array<{
    kind: string;
    label: string;
    description: string;
    /** ADR-539 D1 — DERIVED server-side from `cites`; a display facet only. */
    group: string;
    fragment: string;
    apps?: string[] | null;
    /** ADR-539 D1 — the behavior fields. The registry declares; every surface
     *  derives from these instead of keeping a hand-list (the audit found five
     *  spellings of the picker set and two kind lists doing this job). */
    tier: 'text' | 'object';
    convertible: boolean;
    cites: 'none' | 'source' | 'picture' | 'fragment';
  }>;
  /** ADR-539 D3 — the heading rung set, declared once in the kernel. The
   *  outline walk, the Typography ramp, and the turn-into levels all read
   *  this; the runtime's static copy is pinned to it by the parity gate. */
  heading_rungs: number[];
  layouts: Array<{ slug: string; label: string; description: string; mode: 'flow' | 'paged' }>;
  arrangements: Record<string, StudioArrangement[]>;
  tokens: StudioToken[];
  /** ADR-461 D4 — the measures: a property whose MECHANISM is enumerable but
   *  whose VALUE is not (the kernel pre-declares `var()`, the element carries
   *  the value). Served WITH its bound, so nothing downstream invents one. */
  measures: StudioMeasure[];
  media_kinds: string[];
  /** ADR-483 — every layout's scaffolded h1, served so the name-lift can tell a
   *  PLACEHOLDER title from an authored one. Not derivable from `layouts`: a
   *  deck/page scaffold is a thesis ("The headline promise."), not
   *  "Untitled ‹label›". The kernel names it; the FE never re-derives it. */
  placeholder_titles: string[];
  kernel_css_version: number;
  kernel_style_element: string;
  design_systems: Array<{ name: string; manifest_path: string; folder: string; css: string[] }>;
  /** ADR-487 D5 — the workspace-default system's manifest path (null = none):
   *  the house identity a NEW artifact is born wearing. */
  default_design_system: string | null;
}

/** The canvas selection (ADR-444/446; the structural grain per ADR-511 D3):
 *  blockId + blockKind → a vocabulary BLOCK; blockId with NO blockKind → a
 *  structural CONTAINER (a column/columns/slot-div carrying identity but no
 *  vocabulary); otherwise a page grain when slideIndex/pageIndex is known.
 *  The ADR-453 slot grain is dissolved — a slot-div selects as a container. */
export interface StudioSelection {
  blockId: string | null;
  blockKind: string | null;
  slideIndex: number | null;
  pageIndex: number | null;
  slot: string | null;
  arrange: string | null;
  text: string;
  /** ADR-511 D3 — the operator-word name (slide, columns, column, heading…). */
  label?: string | null;
  /** ADR-522 D4 — the nearest heading at or above this block (flow only).
   *  Docs has no section unit, so this heading is what "this section" means:
   *  from here to the next heading. Null on paged media. */
  headingId?: string | null;
  headingText?: string | null;
  /** ADR-525 D1 — what KIND of thing this selection is, declared by the
   *  projection runtime (the one party that sees both the DOM and the medium).
   *
   *    text      — prose on flow. The caret speaks for it: no box, no unit
   *                verbs, no geometry. Still addressable (ADR-480).
   *    object    — a figure/table/chart/divider anywhere, and EVERY block on a
   *                paged medium (ADR-480 D1: there the block is an enclosure).
   *    structure — a container or page.
   *
   *  Read it; never re-derive it. Three surfaces derived their own answer and
   *  disagreed — the pane offered Move up/down on a Docs paragraph while the
   *  right-click menu refused it on the same block. */
  tier?: 'text' | 'object' | 'structure' | null;
}

/** ADR-466 D5 — the galleries forewarn instead of post-failing: a slotless
 *  arrangement applied to a page that holds content MOVES that content to a
 *  new content page (the handler's resolution). The note says so where the
 *  choice is made. Shared by the toolbar's Layout gallery and the Properties
 *  page scope's Re-arrange gallery. */
export function arrangementCarryNote(
  a: Pick<StudioArrangement, 'areas'>,
  carriedCount: number | null,
  pageNoun: string,
  /** ADR-519 D2.1 — does this page hold an authored GROUP? Re-arranging
   *  dissolves it, and the member is owed that sentence BEFORE the gesture. */
  groupCount?: number | null,
): string | null {
  const n = carriedCount ?? 0;
  const g = groupCount ?? 0;
  // ADR-519 D2.1 — the debt the dissolve rule carries. `applyArrangement` ends
  // in `page.replaceWith(el)`, so a group wrapper dies with the page that held
  // it: never orphaned, no cleanup pass, but also never announced. A group
  // vanishing silently is the defect the rule must not produce, and this is
  // where the choice is made — the same place ADR-466 D5 warns about carried
  // content, for the same reason.
  //
  // Ordered FIRST: a slotless arrangement moves content AND dissolves groups,
  // and the dissolve is the less recoverable of the two (content lands on a
  // new page; a group is gone). Say the surprising thing.
  if (g > 0) {
    const groups = g === 1 ? 'group' : 'groups';
    return n > 0 && a.areas.length === 0
      ? `ungroups ${g} ${groups} · content → new ${pageNoun}`
      : `ungroups ${g} ${groups}`;
  }
  if (n > 0 && a.areas.length === 0) {
    return `content → new ${pageNoun}`;
  }
  return null;
}

interface StudioToolbarProps {
  vocabulary: StudioVocabulary | null;
  /** The artifact's current layout slug — selects the arrangement set + noun. */
  layout: string;
  /** The layout's composition mode (kernel-named). `paged` gets the New-‹noun›
   *  gallery; `flow` has no page unit to offer.
   *
   *  ADR-506 D2 — TRI-STATE, not a boolean. `undefined` means the vocabulary
   *  has not landed yet, and the page-grain pair must render NOTHING rather
   *  than guess: a boolean derived with `?? 'flow'` cannot tell "this is a
   *  document" from "we don't know yet", so a deck's toolbar flashed empty and
   *  then grew two buttons. This is ADR-482 D3 (chrome waits for the mode)
   *  applied one level out, to the toolbar that D3 never reached. */
  mode: 'flow' | 'paged' | undefined;
  /** EXECUTE: open THE insert door (ADR-586 D1 — one [+ Add] on every medium;
   *  the ADR-579 verb split retired from the toolbar). Carries the button's
   *  own rect so the door drops from it. One list, one write path. */
  onInsert: (at: { x: number; y: number }) => void;
  /** ADR-586 D6 — a BLOCK is selected, so Update's contents are the block's
   *  acts. The surface opens the one block-acts menu (the same definition the
   *  right-click renders) at this point, Update tier expanded. */
  hasBlockSelection?: boolean;
  onUpdateBlock?: (at: { x: number; y: number }) => void;
  /** EXECUTE: add a new page (slide/section) from the gallery. */
  onAddArrangement: (fragment: string, label: string) => void;
  /** EXECUTE: re-lay the CURRENT page (ADR-466 D5 — the PowerPoint pair: Layout
   *  beside New slide; same gallery as the Properties page scope, two mounts). */
  onApplyArrangement: (a: StudioArrangement) => void;
  /** ADR-479 D1: a re-arrangement asks a judgment where each block belongs
   *  before it applies, so the button says it is thinking (~2-4s). */
  planning?: boolean;
  /** Blocks the anchored page would carry through an arrangement change —
   *  drives the carry note on slotless thumbs. */
  carriedCount: number | null;
  /** ADR-519 D2.1 — authored groups the anchored page holds. A re-arrange
   *  DISSOLVES them (`page.replaceWith`), so the gallery says so BEFORE the
   *  gesture, beside the carry note and for the same reason. */
  groupCount?: number | null;
  /** The anchored page's current arrangement slug (highlighted in Layout). */
  currentArrange: string | null;
  /** Whether a page can be resolved from the selection — Layout disables
   *  (with a teaching title) when nothing anchors it. */
  hasPageAnchor: boolean;
  /** COMPACT (2026-08-12): the verbs drop their text labels and keep their
   *  glyphs, so the row fits its box instead of escaping it.
   *
   *  This row cannot become a scroll container — the galleries below are
   *  `absolute top-full` and a scroll container's clipping context would cut
   *  them off (see the root's note). With overflow necessarily visible, the row
   *  had nowhere to put the excess and painted its buttons over the next column
   *  — measured at 820px: content needed 274px in a 16px box, 260px of
   *  overpaint. So the fix is to NEED less width, never to scroll. */
  compact?: boolean;
  /** Touch parity: 44px targets under a coarse pointer (the Apple/Google floor)
   *  while desktop keeps its density. The capability, not the width. */
  coarsePointer?: boolean;
}

export function StudioToolbar({
  vocabulary,
  layout,
  mode,
  onInsert,
  hasBlockSelection = false,
  onUpdateBlock,
  onAddArrangement,
  onApplyArrangement,
  planning,
  carriedCount,
  groupCount,
  currentArrange,
  hasPageAnchor,
  compact = false,
  coarsePointer = false,
}: StudioToolbarProps) {
  // ADR-506 D2: the AFFIRMATIVE test (the ADR-482 D3 idiom). An unresolved mode
  // renders no page-grain chrome rather than guessing `flow` — `mode === 'paged'`
  // is false for both "document" and "not yet known", and only the first of
  // those is a claim.
  const isPaged = mode === 'paged';
  // ADR-447/453: a deck's page is a "slide"; a document/article's is a
  // "section" — the operator word follows the layout.
  const pageNoun = layout === 'deck' ? 'slide' : 'section';
  const [open, setOpen] = useState<null | 'layout'>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  // The trigger cluster (buttons + their panels) — the click-away boundary.
  // Deliberately NOT rootRef, which spans the row's full flex-1 width.
  const menuRef = useRef<HTMLDivElement>(null);

  // Click-away + Escape. Two things this must get right, both learned the hard
  // way (2026-07-15):
  //
  // 1. The listener anchors on `menuRef` (the trigger + its panel), NOT on the
  //    whole toolbar row. `rootRef` is `flex-1`, so it spans the wide empty
  //    stretch between the crumb and the zoom — clicking that apparently-blank
  //    toolbar counted as "inside" and the panel never closed.
  // 2. The canvas is an IFRAME: a mousedown on the document never reaches this
  //    listener (the same boundary StudioSlashPalette documents). The canvas
  //    bridges its in-frame presses out as `yarnnn-canvas-press`, so clicking
  //    the artifact — the most natural "click outside" — closes the panel too.
  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(null);
    const onDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    const onFrame = (e: MessageEvent) => {
      if ((e.data as { type?: string } | null)?.type === 'yarnnn-canvas-press') close();
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    window.addEventListener('message', onFrame);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('message', onFrame);
    };
  }, [open]);

  const arrangements = vocabulary?.arrangements?.[layout] ?? [];

  // shrink-0 + whitespace-nowrap: a flex child is shrinkable BY DEFAULT, so
  // when the row ran out of width (the chat panel open on a narrow viewport)
  // these triggers compressed below their text and the label wrapped mid-button
  // — "New / — / slide" stacked three lines tall, buckling the row. A control's
  // label is its meaning: it never wraps. The row scrolls instead (see the root).
  const btn =
    'inline-flex shrink-0 items-center justify-center gap-1 whitespace-nowrap rounded-md border border-border text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-40 ' +
    (coarsePointer ? 'min-h-[44px] ' : '') +
    (compact ? (coarsePointer ? 'w-11 px-0' : 'h-7 w-8 px-0') : 'px-2 py-1');
  // Anchored to the TRIGGER CLUSTER (menuRef), not the row: `left-2` against a
  // flex-1 row put both panels at the row's left edge regardless of which button
  // opened them. `z-30` matches the sibling Studio popovers (StudioNewMenu,
  // StudioSlashPalette) — `z-20` lost to them.
  const panel =
    'absolute left-0 top-full z-30 mt-1 max-h-72 w-80 overflow-y-auto rounded-md border border-border bg-background p-1 shadow-md';

  return (
    // NOTE: this row must NOT become a scroll container (`overflow-x-auto`) —
    // the dropdown panels are positioned `absolute top-full`, so any overflow
    // clipping would cut them off below the row.
    //
    // That constraint is real, and until 2026-08-12 it was ALSO the bug: with
    // overflow necessarily visible, `min-w-0` let the row yield to nothing while
    // its contents kept their intrinsic width, so the buttons rendered OUTSIDE
    // the box and painted over the next column (measured at 820px: clientW 16,
    // scrollW 274, 260px of overpaint onto Properties). The comment described
    // the tradeoff without preventing it.
    //
    // The fix is upstream of this row: `compact` makes the cluster NEED less
    // width (glyph-only verbs) at the ladder's narrow rungs, so it never has
    // excess to place. `min-w-0` stays — it is still what lets the row yield
    // gracefully to the zoom cluster — but it can no longer yield below what the
    // content occupies, because the content shrinks first.
    <div ref={rootRef} className="relative flex min-w-0 items-center gap-1 border-b border-border px-2 py-1.5">
      <div ref={menuRef} className="relative flex min-w-0 items-center gap-1">
      {/* ── ONE INSERT DOOR (ADR-586 D1, operator-locked) ──────────────────
          [+ Add] [Update] replace the ADR-579 triad: provenance stopped
          being a door decision (it survives as pick behavior + the library's
          "shared" marker). The door's top tier is intent CATEGORIES
          (Slide · Components · Text · Media · Data), each a nested gallery —
          the depth the operator pointed at (PowerPoint's SmartArt shape).
          579's laws survive the re-house: one grouping module, one landing,
          named target, the WHO/meter seam. */}
      <button
        type="button"
        className={btn}
        onClick={(e) => {
          setOpen(null);
          const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
          onInsert({ x: r.left, y: r.bottom + 4 });
        }}
        title={
          isPaged
            ? `Add — a ${pageNoun}, component, text, media, or data — into the selected spot or this ${pageNoun}`
            : 'Add — a component, text, media, or data — after the selection, or at the end'
        }
        aria-label={compact ? 'Add' : undefined}
      >
        <Plus className="h-3 w-3" />
        {!compact && ' Add'}
      </button>

      {/* UPDATE — it exists; change it — AT THE SELECTION'S GRAIN (ADR-586
          D6): a selected BLOCK opens the one block-acts menu (the same
          definition the right-click renders — one definition, two mounts),
          Update tier expanded; otherwise the page-grain door (re-arrange —
          the judgment, plan validation, and Refining… state unchanged,
          ADR-479/524 D4). This is the door where mechanical change and
          metered judgment FUSE; the meter badge inside is the only spelling
          of that distinction (ADR-579 D3 surviving the re-house). */}
      {(hasBlockSelection || (isPaged && arrangements.length > 0)) && (
        <button
          type="button"
          className={btn}
          disabled={!!planning || (!hasBlockSelection && !hasPageAnchor)}
          title={
            hasBlockSelection
              ? 'Update the selected block — move, turn into, rewrite'
              : hasPageAnchor
                ? `Update this ${pageNoun} — re-arrange its layout`
                : `Select a block or a ${pageNoun} first — click it on the canvas or in the strip`
          }
          aria-label={compact ? 'Update' : undefined}
          onClick={(e) => {
            if (hasBlockSelection && onUpdateBlock) {
              setOpen(null);
              const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
              onUpdateBlock({ x: r.left, y: r.bottom + 4 });
              return;
            }
            setOpen(open === 'layout' ? null : 'layout');
          }}
        >
          {/* ADR-524 D4: the page has ALREADY re-arranged mechanically by the
              time this shows — the judgment is refining that placement, not
              producing the first one. Compact keeps the SPINNING state legible
              without the word: the glyph pulses. */}
          <LayoutTemplate className={`h-3 w-3 ${compact && planning ? 'animate-pulse' : ''}`} />
          {!compact && (planning ? 'Refining…' : 'Update')}
        </button>
      )}

      {/* The selection chip is DELETED (2026-07-15). ADR-453 D3 gave it one
          job — "the acknowledgment" — for a world where every affordance was
          selection-gated (ADR-458 §1: "click → toolbar chip + Design tab"), so
          the chip was the receipt proving the click landed. ADR-458 moved the
          entrance to HOVER, and the receipt lost its errand: there is no longer
          a gated act it unlocks. (That hover layer is itself deleted now —
          ADR-505 D4 — which only deepens the reason.)

          What remained was a third rendering of one fact — the navigator
          already rings the slide indigo, the canvas already marks it, and the
          Design tab already flips to page scope. Its ✕ was the only live
          affordance, and clicking the canvas margin already clears the same
          selection through the same handler (the ADR-453 grain ladder).

          The STATE (`selection`) is untouched and still load-bearing: it
          anchors every op and scopes the Design tab. Only its third display
          is gone. */}

      {/* The New-panel dropdown is DELETED (ADR-579 D6.a): the New-‹noun›
          gallery now renders INSIDE the New menu (StudioBlockInsertMenu
          pageSection), so New is one door with two grains — never a dropdown
          hopping to a second menu. */}

      {/* The Layout gallery — re-lay the current page (ADR-466 D5). Slotless
          thumbs carry the amber note: applying one moves this page's content
          to a new content page (the handler's resolution), never a dead-end. */}
      {open === 'layout' && (
        <div className={panel}>
          <p className="px-2 pb-1 pt-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Change this {pageNoun} to
          </p>
          <div className="grid grid-cols-2 gap-1.5 p-1">
            {arrangements.map((a) => {
              const note = arrangementCarryNote(a, carriedCount, pageNoun, groupCount);
              const current = currentArrange === a.slug;
              return (
                <button
                  key={a.slug}
                  type="button"
                  title={
                    note
                      ? `${a.description} — this ${pageNoun}'s content moves to a new content ${pageNoun} after it.`
                      : a.description
                  }
                  onClick={() => {
                    onApplyArrangement(a);
                    setOpen(null);
                  }}
                  className={`flex flex-col gap-1 rounded-md border p-1.5 text-left hover:bg-muted/20 ${
                    current ? 'border-indigo-400' : 'border-transparent hover:border-border'
                  }`}
                >
                  <ArrangementThumb areas={a.areas} fragment={a.fragment} />
                  <span className="truncate text-[11px]">{a.label}</span>
                  {note && (
                    <span className="truncate text-[9px] leading-tight text-amber-600 dark:text-amber-500">
                      {note}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* The standalone Insert button is DELETED (ADR-579 D6): its two
          halves re-homed under the verb doors above — the from-the-workspace
          kinds behind Add, the thin-air kinds behind New. The door history
          (ADR-506 D1/D4, ADR-482 §7) lives with those buttons now. */}

      </div>
    </div>
  );
}
