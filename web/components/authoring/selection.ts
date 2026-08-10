/**
 * selection.ts — the selection algebra (ADR-541 D1/D2).
 *
 * ONE home for the two questions every verb entrance kept answering for
 * itself (the 2026-08-09 audit found six derivation sites, five vocabularies,
 * and two set representations):
 *
 *   scopeOf — "what is the member looking at?"  (the pane scope)
 *   arityOf — "how many subjects does a verb take?"  (the gesture fact)
 *
 * ADR-519 D4.1 holds whole here: the SET is state, never a scope. `unify`
 * folds the two historical set states (flow's range-covered ids, paged's
 * ⇧-click ids) into one `set` with a `setKind` naming the gesture. No pane
 * section ever takes the set as its identity subject; `arityOf === 'many'`
 * is what a section consults to withdraw — or, per ADR-541 D3/D4, to act on
 * every covered block as ONE revision.
 *
 * These are pure functions. If you find yourself deriving scope or arity
 * anywhere else, you are re-opening the ADR-525 defect ("three surfaces,
 * three answers, one block") — move the derivation here instead.
 */

import type { StudioSelection } from './StudioToolbar';

export type PaneScope = 'document' | 'range' | 'object' | 'container' | 'page';
export type Arity = 'none' | 'one' | 'many';
export type SetKind = 'range' | 'objects' | null;

export interface UnifiedSelection {
  /** The primary — what was CLICKED (ADR-519 D4.1's `cur`). */
  primary: StudioSelection | null;
  /** The covered/collected block ids, in document order. Empty = no set. */
  set: string[];
  /** HOW the set was made: a drag over flow text, or ⇧-clicks on a stage. */
  setKind: SetKind;
}

/** Fold the two set states into one. A live range outranks a stale click's
 *  set memory — the `d878242` finding, one gesture earlier: what the member
 *  is looking at is the range. The two set kinds cannot coexist in one
 *  gesture (ranges are a flow fact, ⇧-click sets a paged fact). */
export function unify(
  primary: StudioSelection | null,
  rangeBlockIds: string[] | null | undefined,
  groupIds: string[] | null | undefined,
): UnifiedSelection {
  const range = rangeBlockIds ?? [];
  const group = groupIds ?? [];
  if (range.length > 0) return { primary, set: range, setKind: 'range' };
  if (group.length > 0) return { primary, set: group, setKind: 'objects' };
  return { primary, set: [], setKind: null };
}

/** The ADR-528 D2.1 ladder, extracted to the one shared home (ADR-541 D2).
 *
 *  `tier` is the RUNTIME's declared answer for the primary (ADR-525 D1),
 *  resolved by the caller (payload tier first, served-vocabulary fallback via
 *  kindTier) — this function never re-derives it from a kind list.
 *
 *  The range rung is checked FIRST and flow-only: a live range IS a selection
 *  on a continuous surface, and it outranks a stale click (the ADR-528
 *  unreachable-scope fix, now structural). */
export function scopeOf(
  u: UnifiedSelection,
  mode: 'flow' | 'paged',
  tier: 'text' | 'object' | 'structure' | null,
): PaneScope {
  if (u.setKind === 'range' && u.set.length > 0 && mode === 'flow') return 'range';
  const sel = u.primary;
  if (!sel) return 'document';
  if (sel.blockId && sel.blockKind) return tier === 'text' ? 'range' : 'object';
  if (sel.blockId) return 'container';
  if (sel.slideIndex != null || sel.pageIndex != null) return 'page';
  return 'document';
}

/** How many subjects does a verb take? The single-subject question, answered
 *  once (it used to be enforced through five mechanisms across ~14 guard
 *  sites with two notice strings). `one` covers both a clicked primary and a
 *  single-member set — one subject either way. */
export function arityOf(u: UnifiedSelection): Arity {
  if (u.set.length > 1) return 'many';
  if (u.primary != null || u.set.length === 1) return 'one';
  return 'none';
}

/** The one withdrawal sentence (ADR-541 D4): every single-subject section or
 *  menu row that withdraws over a set says WHY with the same words, derived
 *  from the set — never a second hand-written string. */
export function withdrawalNotice(u: UnifiedSelection): string {
  const n = u.set.length;
  return u.setKind === 'range'
    ? `Formatting applies to everything selected. Identity and single-block controls apply to one block at a time (${n} selected).`
    : `Align and distribute apply to everything selected. Identity, position, layout and style apply to one object at a time (${n} selected).`;
}

// ═══════════════════════════════════════════════════════════════════════════
// ADR-546 — THE RUNG. Depth on a document, derived here and nowhere else.
// ═══════════════════════════════════════════════════════════════════════════

/** ADR-546 D2 — one block's rung: how subordinate this block is.
 *
 *  `heading` is the block's own heading level when it IS a heading; `nesting` is
 *  its depth inside a list (0 = the list's own top level, or not in a list).
 *  Both are the SAME statement in two spellings (D1), which is why they share a
 *  declared set and one type.
 *
 *  **No new identity.** A rung is a PROPERTY of a block, never a grain that
 *  holds blocks: `normalizeStructure` is untouched and an `<li>` never carries
 *  `data-block-id` (D2's refusal — the addressable-item alternative is Notion's
 *  and would move the attribution floor, which ADR-528 §2 measured as
 *  whole-FILE). What changed is that the nesting rung became READABLE: before
 *  ADR-546 it was `ul ul` in the DOM and nothing in the model. */
export interface Rung {
  /** The heading level (1..N) when this block is a heading; null otherwise. */
  heading: number | null;
  /** Nesting steps below the containing list's top level. 0 when not nested. */
  nesting: number;
}

/** The rung's single number — what "how deep is this" means for sorting,
 *  indenting an outline row, or comparing two blocks. A heading's rung is its
 *  level; a non-heading's is its nesting depth. */
export function rungDepthOf(r: Rung): number {
  return r.heading ?? r.nesting;
}

/** ADR-546 D3 — THE SPAN'S SHAPE. A range is not a bag of N peers.
 *
 *  A selection covering a heading and the six paragraphs beneath it is a
 *  SUBTREE: one thing the member can name. Before this, `formatSegments` was
 *  flat by construction (*"Top-level blocks only"*), so the rung relation the
 *  outline already computed was discarded at the one place a span's subjects are
 *  derived — which is why multi-block selection had no honest description and
 *  the pane could only count ("7 blocks selected").
 *
 *  `lead` is the shallowest-rung block when it comes FIRST — the span's head.
 *  A span that does not open on its shallowest block has no single head (the
 *  member dragged into the middle of a section), and that is reported honestly
 *  as `lead: null` rather than guessed. */
export interface SpanShape {
  /** How many blocks the span covers. */
  count: number;
  /** The heading that heads this span, when it opens on one. */
  lead: { blockId: string; text: string; rung: number } | null;
  /** Blocks under the lead — count - 1 when there is a lead. */
  under: number;
}

/** Derive a span's shape from its covered blocks, in document order.
 *
 *  Pure, and the ONE derivation (ADR-541 D2's rule): the pane, the menu and the
 *  lane read this. Deriving it again anywhere re-opens the "three surfaces,
 *  three answers" defect ADR-525 closed. */
export function spanShapeOf(
  blocks: Array<{ blockId: string; rung: Rung; text?: string | null }>,
): SpanShape {
  if (blocks.length === 0) return { count: 0, lead: null, under: 0 };
  const first = blocks[0];
  // The span heads on a heading only if that heading is strictly shallower than
  // everything after it — otherwise the member's selection starts mid-section
  // and naming one block its head would be a guess.
  const heads =
    first.rung.heading != null &&
    blocks
      .slice(1)
      .every((b) => rungDepthOf(b.rung) > rungDepthOf(first.rung) || b.rung.heading == null);
  return heads
    ? {
        count: blocks.length,
        lead: {
          blockId: first.blockId,
          text: (first.text ?? '').trim(),
          rung: first.rung.heading!,
        },
        under: blocks.length - 1,
      }
    : { count: blocks.length, lead: null, under: 0 };
}

/** ADR-546 D3 — the span's own sentence, derived from its shape.
 *
 *  One home for the words, beside `withdrawalNotice` and for the same reason: a
 *  second hand-written string is how two surfaces start describing one selection
 *  differently. A shapeless span still gets a truthful count. */
export function spanLabel(s: SpanShape): string {
  if (s.count === 0) return 'Selection';
  if (s.count === 1) return '1 block selected';
  if (s.lead) {
    const name = s.lead.text || 'this heading';
    return `${name} and the ${s.under} block${s.under === 1 ? '' : 's'} under it`;
  }
  return `${s.count} blocks selected`;
}
