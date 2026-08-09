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
