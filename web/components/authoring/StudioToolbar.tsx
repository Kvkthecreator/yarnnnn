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
import { Plus } from 'lucide-react';

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
  /* ADR-616 D1 — `hasBlockSelection`, `onUpdateBlock`, `planning` and
     `hasPageAnchor` are DELETED with the Update button. Each existed only to
     dress or gate it; the re-arrange they described now states its own carry
     note and its own "Refining…" beside the gallery in the Properties pane,
     where the act lives (D2). The orphaned doc-comments they had accumulated
     went with them. */
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
  const rootRef = useRef<HTMLDivElement>(null);
  // The trigger cluster (buttons + their panels) — the click-away boundary.
  // Deliberately NOT rootRef, which spans the row's full flex-1 width.
  const menuRef = useRef<HTMLDivElement>(null);

  // The toolbar's own click-away/Escape effect is DELETED with the layout
  // panel (ADR-589 D3): this component no longer owns a panel to dismiss.
  // The one door it opens carries its own dismissal, including the iframe
  // bridge (`yarnnn-canvas-press`) this effect existed to handle —
  // StudioBlockInsertMenu listens for it. (Update was the second door until
  // ADR-616 D1 deleted it; Add is the only one this toolbar opens now.)


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

      {/* UPDATE is DELETED (ADR-616 D1). Six of its seven rows were one
          action — `onOpenPane`, whose scope argument the mount discarded — and
          the seventh, the re-arrange gallery, went home to the Properties
          pane's page scope (D2), taking `planning`/"Refining…" with it. The
          ladder that disambiguated targets outlived the acts needing
          disambiguation: ADR-613 took the judged verbs out, and every row left
          led to the same place. A door whose every row is the same row is a
          button, and this one no longer named the act it carried. */}

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

      {/* The Layout gallery left this toolbar in ADR-589 D3 and left the
          Update door in ADR-616 D2. It is now in the Properties pane's PAGE
          scope — the one home, which is the same sentence the 2026-07-21 note
          wrote when it removed the pane's copy, now pointing the other way
          because the toolbar copy is what no longer exists.
          `arrangementCarryNote` went with it: a helper follows its one
          consumer, and leaving it exported from here would be a second home
          for a function with no caller in this file. */}

      {/* The standalone Insert button is DELETED (ADR-579 D6): its two
          halves re-homed under the verb doors above — the from-the-workspace
          kinds behind Add, the thin-air kinds behind New. The door history
          (ADR-506 D1/D4, ADR-482 §7) lives with those buttons now. */}

      </div>
    </div>
  );
}
