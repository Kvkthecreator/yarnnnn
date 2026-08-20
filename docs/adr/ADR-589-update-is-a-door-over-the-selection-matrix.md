# ADR-589 — Update is a door over the selection matrix

**Status**: Implemented (2026-08-20, `d4f2645`)
**Supersedes**: nothing. **Completes** [ADR-586](ADR-586-one-insert-door-categories-galleries-contextual-update.md) D6, which decided the contents follow the selection grain and shipped two of the five grains it named.
**Related**: [ADR-519](ADR-519-the-object-hierarchy-and-the-pane-grammar.md) D4.1 (the set is STATE, not a scope — inherited whole, see D4) · [ADR-541](ADR-541-the-selection-algebra-a-ranges-subjects-are-its-covered-blocks.md) (`scopeOf`/`arityOf` — the ladder this reads) · [ADR-506](ADR-506-the-insert-door.md) D3 (ordering never subsetting) · [ADR-462](ADR-462-the-block-context-menu-and-the-metered-badge.md) D1 (a door is a second entrance, never a second write path) · [ADR-367](ADR-367-home-as-operating-cockpit.md) D3 (fast path vs dwell)

---

## 1. The observation

The operator, looking at the built door: *"the main buttons in the center pane
only has slides, but really it should be a mimic, of course re-interpreted, of
the Add architecture."*

They are right, and the code says why. **Add** is a two-pane door whose left
rail is a DERIVED partition (`categorizeBlockRows` over the live registry) and
whose right pane is that partition's gallery. **Update** is not a door at all —
it is a fork on selection state:

- a block is selected → jump to the block-acts menu;
- nothing is selected → one flat gallery of slide arrangements, titled
  "CHANGE THIS SLIDE TO".

The second branch is the defect the screenshot shows: **with nothing selected,
Update ASSUMES the target is the slide.** The artifact's own typography, its
palette, and its design system are `document`-scope acts that already exist and
work — reachable only from the Properties pane, never from the door named
Update.

## 2. What is actually selectable, and what each admits

This is not a new taxonomy. `scopeOf(unified, mode, tier)` (ADR-541 D2) already
resolves every selection to one of five scopes, crossed with `arityOf` and two
modifiers. The acts already exist; four of the cells simply have no entrance.

| Selected | Scope | Admits (all already implemented) | Entrance today |
|---|---|---|---|
| nothing | `document` | artifact identity · **face/type tokens** · **palette** · **design system** · outline | ❌ door shows *slides* |
| a slide / page | `page` | **re-arrange** · layout rows · background · page verbs · colour tokens | ⚠️ re-arrange only |
| a group / slot | `container` | layout rows · measures · slot image · container verbs | ❌ |
| a block | `object` | align · position · layout · measures · tone · verbs · turn-into · **Rewrite** ⦿ | ✅ block-acts menu |
| a text range | `range` | marks · text tokens · turn-into | ❌ |
| many blocks | + `many` | align/distribute; single-subject rows **withdraw with the one stated reason** (ADR-541 D4) | ❌ |
| a **cited** block | `object` + cited | *edit source · swap citation · refresh pin* | ❌ **and unbuilt** |

## 3. Decisions

### D1 — Update is a two-pane door; the rail is the SELECTION LADDER

Same geometry as Add, same flyout mechanics, one re-interpretation: Add's rail
answers *what kind of thing do I want*, Update's answers *which of the nested
things under my cursor am I shaping*. Both rails are **derived, never
hand-listed** — Add from the registry, Update from `scopeOf` + `climbChain`.

The rail is the ancestor ladder (`Artifact › Slide 2 › Area › Stat`). Picking a
rung RE-TARGETS the selection and the right pane shows that rung's acts. This is
the correct axis because for Update the target is the hard part and the act set
is fully determined once the target is known — the inverse of Add, where the
target is implicit and the catalog is long.

### D2 — The ladder is never subset (ADR-506 D3, applied one level up)

Every rung renders on every open. Rungs above the current selection are live
(clicking one re-targets upward — this is how `document` becomes reachable with
a block selected). A rung that does not exist for this medium or selection
renders **greyed with its reason** ("select text first"), never hidden: a door
whose shape changes on every click cannot be learned, and hiding reads as a bug
(the ADR-559 lesson about unavailable engines, same principle).

`document` is therefore ALWAYS the top rung, and always reachable. That single
consequence fixes §1's defect.

### D3 — Selection-shaped, not slide-shaped: the empty case

With no selection the door opens on the `document` rung — the artifact's own
acts — not on a slide gallery. Re-arrange remains exactly where it belongs: the
`page` rung, reached by selecting a page or clicking that rung. The current
behaviour is not "a sensible default"; it is one grain silently standing in for
all five.

### D4 — Arity is INHERITED as a modifier, not re-decided here

**ADR-519 D4.1 already settled this** ("the set is STATE, not a scope",
operator-directed, re-derived from first principles): a scope answers *what is
this?* and a set of N things has no label, no box, no tier and no
`data-block-id`; arity answers *how many does the verb take?*, which is a fact
about the gesture. This ADR adds nothing to that and must not re-open it.

Applied to the door: **a set gets no rung.** The rail shows the shared ancestry
(`sharedChain`, ADR-519 D4.1) and the PANE withdraws its single-subject rows
with `withdrawalNotice()` — the one sentence, already written (ADR-541). A
"many" rung would make arity look like a place, which is precisely the error
D4.1 withdrew.

### D5 — One implementation: the door is an entrance, the pane is the dwell

Per ADR-462 D1 and ADR-367 D3, this duplication is deliberate and already
ratified for right-click. The door carries the acts a member reaches for at
speed; the Properties pane keeps the full set including rare tokens and numeric
fields. **Both call the same ops.** No act may exist only in the door.

### D6 — The cited cell is named and SEQUENCED, not silently dropped

`edit source · swap citation · refresh pin` (ADR-586 D6's citation clause) are
the only acts in the matrix that do not exist anywhere — the other four cells
need an entrance, not an op. They need real surface: routing to the cited file
in its owning app, the citable picker, and a revision-bump that re-points
`data-ref-rev` at head. **Out of scope here, owed and named** — the door ships
over the five working scopes, and the cited rung shows its acts when they exist.

## 4. What this does NOT change

- **ASK is untouched** — it never writes and stays its own tier (ADR-586 D6).
- **The meter badge stays the only spelling** of mechanical-vs-metered
  (ADR-462 D4 / ADR-579 D3). Fusing mechanical and judged acts in one door is
  the operator's ratified ruling; the badge is the seam.
- **No new write path** (ADR-462 D1). Every rung's acts call the ops the
  Properties pane already calls.
- **Narrow screens** keep the ADR-586 D5 housing and the inline tiers.

## 5. Verification

`api/test_adr589_update_matrix.py` — **26/26** at `d4f2645`. Defends: the rail is
DERIVED (`updateLadder.ts`, pure — no DOM, no React, so it is assertable); the
`document` rung is pushed UNCONDITIONALLY (asserted by position, before any
branch in the brace-bounded builder); unreachable rungs carry a reason and the
rail maps the ladder WHOLE; no rung is built from the set; every act routes to
an op the pane also calls; and the moved gallery has exactly one render home.

Five checks falsified one at a time against real breaks: a conditional document
rung · a filtered rail · a re-copied toolbar gallery · the restored
disabled-gating · the object rung ceasing to route.

**As-built note.** The container rung derives from the SLOT the runtime already
reports (ADR-511 D3's region), not from a second DOM walk: the surface holds no
parsed document, and `climbChain` already answers ancestry in the pane. One
container rung today; a deeper chain needs the runtime to report one, not a
second derivation here.

**Deleted with the fork** (singular implementation, never left latent): the
toolbar's layout panel + its `open` state; its click-away/Escape effect (it
existed to dismiss a panel this component no longer owns — both doors carry
their own dismissal, including the iframe `yarnnn-canvas-press` bridge); the
orphaned `ArrangementThumb` import and the `currentArrange` / `carriedCount` /
`groupCount` / `onApplyArrangement` / `onAddArrangement` props with their
call-site arguments. `arrangementCarryNote` stays exported for its one consumer.

**Owed**: the cited cell (D6) · an operator click-pass of the door.
