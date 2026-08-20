/**
 * updateLadder — the Update door's rail, DERIVED (ADR-589 D1/D2).
 *
 * Add's rail partitions "what kind of thing do I want" (categorizeBlockRows
 * over the live registry). Update's answers a different question — "which of
 * the nested things under my cursor am I shaping" — because for Update the
 * TARGET is the hard part and the act set is fully determined once the target
 * is known. That is the re-interpretation ADR-589 D1 names: same two-pane
 * geometry, a rail derived from the SELECTION rather than the catalog.
 *
 * The ladder is never subset (D2, ADR-506 D3 one level up): every rung renders
 * on every open. A rung that does not apply to this medium or selection comes
 * back with a `reason` and renders greyed — hiding it would make the door's
 * shape change on every click, which cannot be learned, and reads as a bug.
 *
 * `document` is therefore ALWAYS present and ALWAYS reachable. That single
 * consequence is the fix: today the no-selection door shows a slide gallery, so
 * the artifact's own typography/palette/design-system have no entrance at all.
 *
 * Arity adds NO rung (D4, inherited whole from ADR-519 D4.1 — "the set is
 * STATE, not a scope"). A set shows its shared ancestry and the pane withdraws
 * its single-subject rows.
 *
 * PURE — no DOM, no React. The DOM walk that finds container ancestors is
 * `climbChain` (SelectionBreadcrumb); this module turns a selection plus that
 * walk's result into the rail the door renders.
 */

import type { PaneScope } from './selection';
import type { StudioSelection } from './StudioToolbar';

/** One rung of the rail. */
export interface LadderRung {
  /** The pane scope this rung targets — the SAME five `scopeOf` resolves. */
  scope: PaneScope;
  /** Stable key for React and for re-targeting (container rungs carry an id). */
  key: string;
  /** Operator-word label: "Artifact", "Slide 2", "Columns", "Stat". */
  label: string;
  /** The block id to select when this rung is picked; null = page/document. */
  blockId: string | null;
  /** For a page rung: which page to target. */
  pageIndex: number | null;
  /** True for the rung the current selection resolves to. */
  current: boolean;
  /** Set when the rung cannot be entered right now — rendered greyed WITH this
   *  sentence, never filtered (D2). */
  reason?: string;
}

/** A container ancestor, already walked out of the DOM by `climbChain`. */
export interface LadderAncestor {
  blockId: string;
  label: string;
}

export interface LadderInput {
  selection: StudioSelection | null;
  /** `scopeOf(...)` for the current selection — read, never re-derived. */
  scope: PaneScope;
  /** Container ancestors between the page and the selected block, outermost
   *  first (the `climbChain` order). Empty on flow, or when the block sits
   *  directly on the page. */
  ancestors: LadderAncestor[];
  mode: 'flow' | 'paged';
  /** "slide" on a deck, "section" on a web layout. */
  pageNoun: string;
  /** Artifact display name for the top rung's title. */
  artifactLabel: string;
  /** Size of the current set; >1 means single-subject rows withdraw. */
  setCount: number;
}

/** Title-case the medium's page noun for a rung label ("slide" → "Slide 2"). */
function pageLabel(noun: string, index: number | null): string {
  const n = noun.charAt(0).toUpperCase() + noun.slice(1);
  return index == null ? n : `${n} ${index + 1}`;
}

/**
 * Build the rail. Always returns the full ladder, current-marked, with
 * unreachable rungs carrying their reason.
 *
 * Order is OUTSIDE-IN (artifact → page → containers → block → range), which is
 * the containment order the breadcrumb already reads in and the order a member
 * narrows by.
 */
export function buildLadder(input: LadderInput): LadderRung[] {
  const { selection, scope, ancestors, mode, pageNoun, artifactLabel, setCount } = input;
  const sel = selection;
  const rungs: LadderRung[] = [];

  // ── The artifact. Always present, always reachable — the D2 consequence.
  rungs.push({
    scope: 'document',
    key: 'document',
    label: artifactLabel || 'Artifact',
    blockId: null,
    pageIndex: null,
    current: scope === 'document',
  });

  // ── The page. Paged media only: flow has no page unit (ADR-522 D4), so the
  //    rung is stated-and-greyed rather than silently missing.
  const pageIndex = sel?.slideIndex ?? sel?.pageIndex ?? null;
  if (mode === 'paged') {
    rungs.push({
      scope: 'page',
      key: 'page',
      label: pageLabel(pageNoun, pageIndex),
      blockId: null,
      pageIndex,
      current: scope === 'page',
    });
  } else {
    rungs.push({
      scope: 'page',
      key: 'page',
      label: pageLabel(pageNoun, null),
      blockId: null,
      pageIndex: null,
      current: false,
      reason: 'This document flows — it has no pages to shape.',
    });
  }

  // ── The container ancestors, outermost first. Each is a real rung: a group
  //    or slot has its own layout, measures and verbs (`container` scope).
  for (const a of ancestors) {
    rungs.push({
      scope: 'container',
      key: `container:${a.blockId}`,
      label: a.label,
      blockId: a.blockId,
      pageIndex,
      current: scope === 'container' && sel?.blockId === a.blockId,
    });
  }

  // ── The block itself.
  if (sel?.blockId && sel.blockKind) {
    rungs.push({
      scope: 'object',
      key: `object:${sel.blockId}`,
      label: sel.label || sel.blockKind,
      blockId: sel.blockId,
      pageIndex,
      current: scope === 'object',
    });
  } else {
    rungs.push({
      scope: 'object',
      key: 'object',
      label: 'Block',
      blockId: null,
      pageIndex,
      current: false,
      reason: 'Select a block on the canvas to shape it.',
    });
  }

  // ── A text range. Its acts (marks, text tokens, turn-into) need a live
  //    range; the rung says so rather than vanishing.
  rungs.push({
    scope: 'range',
    key: 'range',
    label: 'Text',
    blockId: sel?.blockId ?? null,
    pageIndex,
    current: scope === 'range',
    ...(scope === 'range' ? {} : { reason: 'Select text inside a block to format it.' }),
  });

  // A set never adds a rung (D4 / ADR-519 D4.1). It is visible in the door as
  // the pane's withdrawal sentence, and the ancestry above is the shared one.
  void setCount;

  return rungs;
}

/** The rung the door should open on: the current one, else the deepest
 *  reachable. With no selection that resolves to the ARTIFACT — the D3 empty
 *  case, and the reason the old door's slide-gallery default was wrong. */
export function initialRung(rungs: LadderRung[]): LadderRung | null {
  return rungs.find((r) => r.current) ?? rungs.find((r) => !r.reason) ?? null;
}
