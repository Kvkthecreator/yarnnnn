# ADR-616 — The Update door is deleted; the re-arrange comes home

**Status**: Ratified + implemented 2026-08-28. Operator instruction: *"i want to completely delete the update button and its subfeatures. any absorption required. do so. streamlined and singular implementation discipline."*

**Supersedes**: [ADR-589](ADR-589-update-is-a-door-over-the-selection-matrix.md) in full (D1–D6). **Amends**: [ADR-586](ADR-586-one-insert-door-categories-galleries-contextual-update.md) D6 (the contextual-update half; the one-insert-door half stands).

**Related**: [ADR-612](ADR-612-the-judged-act-is-one-gesture-at-the-selection.md) / [ADR-613](ADR-613-the-judged-act-leaves-the-menus.md) (the judged act left the menus first — this is the mechanical half of the same motion) · [ADR-462](ADR-462-the-block-context-menu-and-the-metered-badge.md) D1 (a door is a second entrance, never a second write path) · [ADR-367](ADR-367-home-as-operating-cockpit.md) D3 (fast path vs dwell) · [ADR-479](ADR-479-placement-is-a-judgment.md) D1 (the arrangement plan is a judgment)

---

## 1. What the audit measured

The operator asked whether Update could be absorbed by Add, the sparkle and the
right-click menu. The measurement says: **almost**. Six of its seven rows are
already redundant; one is not, and it is the only reason the door still stood.

`StudioUpdateMenu` rendered **six act rows** across five rungs:

| Rung | Row | What it actually did |
|---|---|---|
| Artifact | Typography… | `onOpenPane('document')` |
| Artifact | Palette & design system… | `onOpenPane('document')` |
| Slide | **arrangement gallery** | **`handleApplyArrangement` — a real op** |
| Slide | Layout & background… | `onOpenPane('page')` |
| Block | Align, position & style… | `onOpenPane('object')` |
| Container | Layout & measures… | `onOpenPane('container')` |
| Text | Marks & turn into… | `onOpenPane('range')` |

And the mount discarded the argument:

```tsx
onOpenPane={(sc: PaneScope) => { void sc; setRightTab('design'); }}
```

**Five rungs of derivation, thrown away at the door.** `StudioDesignTab` derives
its own scope from the selection (`scopeOf(...)`, line 1417), so the ladder's
answer was never read by anything. Six rows, one action: *switch to Properties*.

### ADR-589's premise had expired

Its §1 defect was that *"the artifact's own typography, palette, and design
system … [are] reachable only from the Properties pane, never from the door
named Update."* That is now false **independently of this ADR**: with nothing
selected the Properties pane renders exactly those at `document` scope, and says
so (*"select a slide or a block on the canvas to shape it here"*). ADR-589 built
a second, more nameable door to a room that already had one — and then ADR-613
took the judged verbs out of it, leaving the ladder disambiguating targets for
acts that no longer needed disambiguating, because every surviving row led to
the same place.

**A door whose every row is the same row is not a door. It is a button.**

## 2. The one thing that was not redundant

`handleApplyArrangement` had **exactly one caller** in the codebase.

Add's `New slide` gallery renders the same `ArrangementThumb` over the same
vocabulary — and is a different verb: `onPick` → `insertArrangement` (*create a
new page*), against `onApplyArrangement` → *re-lay this page*, which
redistributes existing blocks by ADR-479 D1's placement judgment, moves content
a slotless arrangement cannot hold onto a following page, and dissolves group
wrappers. Same pixels, different act. A member could approximate it by adding a
slide and moving blocks by hand; that is a workaround producing a different
revision, not an equivalent.

The gallery reached Update by **two successive deletions** — out of the
Properties pane (2026-07-21, *"the toolbar button is the one home"*) and out of
the toolbar dropdown (ADR-589 D3, *"moved, not copied"*). Deleting the door
without re-homing it would have deleted slide re-arrangement from the product,
along with the only client caller of `planArrangement`,
`applyArrangementPlan` and `applyArrangementMovingContent`.

## 3. Decisions

### D1 — The Update door is deleted whole

`StudioUpdateMenu.tsx` and `updateLadder.ts` are removed; so are the toolbar
button, `onUpdateBlock`, `openUpdateDoor`, `retargetToRung`, the `updateMenu`
state and its four suppression clauses. Not shrunk to one row — **deleted**. A
door kept alive for a single act it does not name is the "second spelling
waiting to happen" ADR-613 D2 removed the `meter` discriminator to avoid.

`PaneScope` and `selection.ts` **survive**: the Properties pane derives its own
scope from them and always did. What dies is the ladder that re-derived an
answer nobody read.

### D2 — Re-arrange comes home to the pane's `page` scope

The gallery returns to `StudioDesignTab`'s `page` scope — where it lived until
2026-07-21 — directly above the existing `Layout` section, whose language it
already speaks.

This **reverses ADR-589 D3 deliberately**, and the July rationale for its
removal does not survive the reversal: it was deleted then because it
*"duplicated the toolbar's Re-arrange gallery in full, and two mounts of the
same act is exactly the redundancy DP29 names."* With the toolbar gallery gone
there is no duplication — **the pane is the one home**, which is the same
sentence the July note wrote, now pointing the other way.

The carry-note (`arrangementCarryNote`) rides with it, unchanged: a member is
owed *"content → new slide"* and *"ungroups N groups"* **before** the gesture
(ADR-466 D5 / ADR-519 D2.1). It moves; it is not re-derived.

### D3 — This is dwell, and that is the honest reading

ADR-367 D3 splits fast-path from dwell. Re-arranging a slide is **not** a fast
path: it is a considered act with a forewarned cost, an LLM placement round-trip
and a visible "Refining…" state. It belongs in the pane a member is already
dwelling in, next to that page's Layout and Background — not behind a toolbar
button that opens a two-pane door to reach one gallery.

The affordance genuinely lost is the rail's **`document` rung** — the only
*labelled* route to artifact scope from a live selection. Artifact scope stays
reachable (click empty canvas; `onPointClear`), and the pane names what to do
there. A labelled route to a place already reachable does not justify five
rungs, six rows and two modules.

### D4 — The sparkle's margin is measured against the CANVAS, not the window

Found in the same pass and fixed with it, because deleting Update **widens the
sparkle's availability**: it was suppressed while the door was open
(`!updateMenu`), and that clause dies here.

`SelectionGesture` chose the right margin on `right + DOOR_W < window.innerWidth`
— the viewport, where it meant *the canvas column*. With the Properties pane
open, the space to the right of a deck's letterboxed stage belongs to the pane,
so a `position: fixed` door hung over it.

This is the **outer** half of the defect `5abdce9` fixed on the inside: that
commit taught the runtime to report the artifact's CONTENT box, because
measuring against the iframe *"put the door past the canvas, on top of the
properties pane."* Both halves are now measured against something real — the
content bound within, the canvas bound without. The caller passes the column's
right edge; with none declared the door falls back to the viewport exactly as
before.

## 4. What this does NOT change

- **No new write path** (ADR-462 D1). The gallery calls the same
  `handleApplyArrangement`; only its mount moved.
- **Add is untouched.** Its `New slide` gallery keeps `insertArrangement` — a
  different verb, correctly in the insert door.
- **The right-click menu is untouched here.** Its clean-up is sequenced next, at
  the operator's direction, and is a separate scope.
- **ADR-613's deletions stay deleted.** The second-menu route, the `Ask` tier
  and the `meter` discriminator do not return; the gates that pin them are
  re-anchored, never relaxed.

## 5. Verification

`api/test_adr616_update_door_deleted.py`. Defends: both modules are gone and
un-imported; no toolbar button and no `updateMenu` state survives; the gallery
has **exactly one** render home and it is the pane; `handleApplyArrangement`
still reaches it; the carry-note moved rather than being re-derived; the
sparkle's margin reads a canvas bound; and — the one that would have caught the
original defect — **no surviving row discards a scope it was handed**.

`api/test_adr589_update_matrix.py` is **deleted with its subject**. Its two
dependent assertions elsewhere are re-anchored, not dropped:
`test_adr586_one_door.py` and `test_adr612_judged_gesture.py` each read
`StudioUpdateMenu.tsx` to prove the second-menu route stayed deleted — a file
read that would pass *vacuously* once the file is gone. Both now assert the
absence directly.
