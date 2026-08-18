/**
 * The properties-pane spine — ONE grammar, every authoring app.
 *
 * ADR-519 D3 fixed the order Studio's inspector speaks:
 *
 *     Identity → Position → Layout → Style → Content
 *
 * and gated it (`test_adr519_pane_spine.py`). That gate reads exactly two
 * files, both Studio's. Text grew its own pane beside it — its own heading
 * styles, its own section rhythm, its own order — and nothing could see the
 * divergence, because the rule lived in a docstring about one component.
 *
 * THE GENERALIZATION (2026-08-18). A pane opens by naming its SUBJECT, offers
 * what the member can CHANGE in one fixed order, and ends with what they can
 * only READ:
 *
 *     Identity → [Position → Layout → Text → Style → Content] → Readback
 *                └────────────── controls, ADR-519 order ──────────────┘
 *
 * Readback is the rung this generalization ADDS, and it is what let Text
 * conform without pretending to have sections it does not have. Studio's pane
 * is nearly all controls; Text's is nearly all facts (Length, Format, Last
 * edited). Asking Text to render Position/Layout would have been a fiction —
 * markdown has no box. Asking it to put its facts LAST is a real rule it can
 * actually satisfy, and it is the rule that makes the two panes read as one
 * product: the member's eye lands on the subject, walks the controls, and
 * finds the facts where facts always are.
 *
 * WHY A SECTION MAY BE ABSENT BUT NEVER MOVED. Absence is a property of the
 * grain — a range has no box, so no Position. Re-ordering is a property of
 * nothing; it is just drift. The member learns the panel once (ADR-519 D3's
 * own words), and that promise survives only if every surface spends the
 * member's learning the same way.
 *
 * This module is the SHARED implementation of that grammar: the rank order
 * and the two class strings. Both apps import them, so the rhythm cannot
 * drift by one app's edit — the failure mode a copied Tailwind string
 * guarantees eventually.
 */

/** The rungs, in the order a pane must render them. */
export const PANE_SPINE = [
  'identity',
  'position',
  'layout',
  'text',
  'style',
  'content',
  'readback',
] as const;

export type PaneRung = (typeof PANE_SPINE)[number];

/** The rungs a member can ACT on — everything between Identity and Readback. */
export const CONTROL_RUNGS: readonly PaneRung[] = [
  'position',
  'layout',
  'text',
  'style',
  'content',
];

/**
 * A rung's rank. Lower renders earlier. Use it to ASSERT an order (a gate, a
 * sort) rather than to build one by hand — a hand-kept second copy of this
 * sequence is the drift this module exists to prevent.
 */
export function rungRank(rung: PaneRung): number {
  return PANE_SPINE.indexOf(rung);
}

/**
 * True when `rungs` appear in spine order. Absences are FINE (a grain renders
 * only the sections it has); an inversion is not. Duplicates are fine too —
 * Studio legitimately mounts more than one Layout section at different scopes.
 */
export function isSpineOrdered(rungs: readonly PaneRung[]): boolean {
  let last = -1;
  for (const r of rungs) {
    const rank = rungRank(r);
    if (rank < last) return false;
    last = rank;
  }
  return true;
}

/**
 * The section heading. ONE string, both apps.
 *
 * Studio held this as a local `HEADING` const; Text inline-styled the same
 * declaration at four call sites. Identical pixels on the day it was written,
 * which is precisely why the divergence was invisible — nothing fails when
 * one of five copies is edited.
 */
export const PANE_HEADING =
  'text-[10px] font-medium uppercase tracking-wide text-muted-foreground';

/**
 * The section box. Studio separates its sections with a rule; Text used bare
 * vertical rhythm, which is the visible half of "these look like two
 * products". One box, both panes.
 */
export const PANE_SECTION = 'space-y-2 border-b border-border p-3';
