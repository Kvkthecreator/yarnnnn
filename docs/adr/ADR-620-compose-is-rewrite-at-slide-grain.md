# ADR-620 — Compose is Rewrite at slide grain

**Status**: Ratified + implemented 2026-08-28.

**Operator framing**: *"the Add related details seem to only scaffold skeleton components. while that's fundamentally right, similar to rewrite, we could have AI related compose of said components, text media, data… what's the structural, UI and UX consideration to handle and accommodate this as first class feature."* Then, on housing: *"can we have a dedicated component… something that feels more first class and visual."*

**Builds on**: [ADR-612](ADR-612-the-judged-act-is-one-gesture-at-the-selection.md) §1 (the selection IS the target) · [ADR-613](ADR-613-the-judged-act-leaves-the-menus.md) (the gesture, in Slides) · [ADR-579](ADR-579-the-verb-grammar.md) D7 (the seed: a door names its target, typed) · [ADR-609](ADR-609-the-selection-is-an-address.md) D3 (hand over the address) · [ADR-479](ADR-479-placement-is-a-judgment.md) D1–D2 (a judgment that never emits markup, validated before it applies) · [ADR-544](ADR-544-the-containment-law-slide-layout-area-block.md) (every block lives in an Area) · [ADR-462](ADR-462-the-block-context-menu-and-the-metered-badge.md) D1 (a door is a second entrance, never a second write path)

---

## 1. What `+ Add` is, and what it is not

Every Add door — toolbar, slash, right-click, in-canvas — stamps a **registry
fragment**. The bytes are literal:

```html
<div data-block="stat" data-block-id="b17">
  <strong>42%</strong><span>label</span>
  <em class="delta">▲ 8% vs last quarter</em>
</div>
```

`42%` and `label` are what the member gets. The door's job is to find *Stat*
fast, from a closed catalog, deterministically — and at that job it is correct
and should not change.

What it cannot serve is an **intent**: *"make this slide argue we're cheaper
than the alternatives"* has no row in a catalog. A member with that ask does
not know the noun; they know the argument. Meanwhile Rewrite is judged,
metered, seeded, and receipted — and stops at the block.

**Add and Rewrite are different species today, and there is no principled
reason for the gap.** This closes it at the grain where the gap is felt: the
slide.

## 2. Why this is NOT the re-arrange, re-framed

The obvious move — re-label re-arrange as "modify" — does not survive
inspection, and the reason is worth recording so it is not re-proposed.

`applyArrangementPlan` moves existing nodes: `returnToFlow(b); target.appendChild(b)`.
The blocks are the *same DOM nodes*; their content is never read or
regenerated. The model returns `{block_id, area}` — a **permutation**. That is
exactly why it can promise total block coverage and never lose content
(ADR-479 D2), and why its refusal has somewhere to land: a deterministic
mechanical ladder exists.

Three consequences:

- **A modify has no mechanical floor.** `{placements: null}` means "use the
  ladder"; there is no ladder for "compose this slide", so the contract cannot
  be reused even if we wanted it.
- **The planner is machinery, not the desk's voice.** It resolves the
  **Designer** being deliberately (`studio_arrangement_plan.py`: "arrangement
  planning is MACHINERY that happens to plan layout, not the desk's voice").
  A member-facing act on a slide is the desk's voice — Slides' resident, the
  **Editor** (ADR-602 D1).
- **A gallery is a catalog gesture; this is an intent gesture.** Different
  doors regardless of what sits underneath.

What IS reused is the **discipline**, not the premise — and it is reused by
going through the lane rather than beside it (D2).

## 3. Decisions

### D1 — Compose is a fourth seed verb, at slide grain

`SeedTarget.verb` gains `compose`. It is Rewrite's sibling: same sparkle, same
composer, same stamp, same receipt. They differ only in grain and in what the
model returns.

| | Rewrite | Compose |
|---|---|---|
| grain | block | slide (page) |
| address | `block_id` of the block | `block_id` of the PAGE + `page_index` |
| the colleague writes | one block's prose | the slide's blocks, in place |
| removal | n/a | only with the member's permission (D3) |

The page has carried a `data-block-id` since ADR-519, so the address already
exists. `seedTargetNoun` already rendered a slide grain — though on a proxy that
compose invalidates (§5).

### D2 — The colleague writes it, through the ONE write path

A first cut of this built a `/studio/compose/plan` endpoint, a validator, and
an `applyComposePlan` op — a typed edit list the FE would materialize. **All
three were deleted before shipping**, and the reason is worth recording because
the design was seductive: it mirrored ADR-479's re-arrange planner exactly.

It was a second way to author the same substrate. The lane ALREADY has what
Compose needs — `EditFile` with `anchor`, the block grammar taught in the
posture (`blocks_grammar`), the artifact read fresh each turn, and one
attributed write. A parallel plan/validate/apply stack beside it would have been
the second write path ADR-462 D1 forbids, with a second vocabulary to keep in
sync and a second place for the containment law to be enforced.

So Compose is Rewrite's machinery, unchanged: the door seeds, the member sends,
the colleague reads the slide and edits it in place. ADR-544's containment law
holds for the same reason it holds for every other lane write — the posture
teaches it and `normalizeStructure` enforces it at the serialize seam.

**What the frame adds** is the instruction: compose this slide's actual words,
in the deck's voice, replacing the scaffold placeholders — plus D3's permission.

### D3 — Removal is a member's PERMISSION, not the colleague's judgment

Deleting a block destroys the member's own words, so the choice is theirs. The
chip carries a two-state control and the choice rides the seed to the frame:

- **Fill in what's missing** (default) — *"add and rewrite, but do not delete
  blocks that are already there."*
- **Replace what's there** — *"you may REMOVE blocks that no longer belong."*

Default-additive because the destructive reading must be **chosen**, and
because "fill this empty slide" is the case that motivated the feature.

Stated in BOTH directions deliberately: an absent instruction is not a
prohibition, and a colleague told nothing about removal will infer its own
license from the word "compose".

### D4 — The housing is the composer chip, NOT a modal

The operator asked for something first-class and visual. That is right, and a
modal is the wrong way to give it:

- **A modal hides the slide.** The member would describe an object they can no
  longer see, and the result would land behind a dismissed dialog. ADR-606's
  finding was the opposite direction: the pane must see what the member sees.
- **A modal has no transcript.** A composed slide is judged and metered; it
  belongs in the lane as an attributed, revertible, walkable turn. A modal
  either omits it (the substrate loses the record) or writes a turn nobody
  typed (the system talks to itself).
- **The seed ARMS, it does not send** (ADR-612 D4). A modal implies
  commit-on-confirm and would lose "edit the intent, dismiss it, or never send".

The DOOR itself is the Properties pane's page scope, not a floating sparkle:
the runtime reports a selection rect for blocks and ranges, never for a
page, so a floating door would have to invent geometry it is not given. The
pane is the dwell surface (ADR-367 D3), already beside the canvas, already
holding this slide's identity and contents — and it covers nothing.

The chip then **grows a body** rather than a new surface being introduced: it
names the target, lists the slide's current blocks by kind, and carries the D3
control. Send with an empty box is legitimate — it means *use your judgment* —
which is the zero-typing fast path for a fresh slide.

### D5 — Add is untouched

`+ Add` remains the catalog of things that exist. This ADR adds no row to it,
no "AI" variant beside it, and no second door. Two doors differing by a
modifier is the shape ADR-616 and ADR-619 have just deleted twice.

## 4. What this does NOT change

- **Rewrite stays block-grained.** Two verbs, two grains, one discipline.
- **The re-arrange is untouched** — it keeps its gallery, its planner and its
  Designer resident (§2).
- **No new write path**; no new door mechanism; no new menu tier.

## 5. Verification

`api/test_adr620_compose_at_slide_grain.py`. Defends: `compose` is a real verb
end to end (FE union → `seedToWire` → `LaneSeed` → the frame's gesture line);
the permission is rendered in BOTH directions; the page grain reads "slide N"
in the chip AND the frame, from the label rather than the absence of a block
id; there is exactly ONE seed producer and no compose-specific write path; and
`+ Add` gained no AI row.

**The `_seed_line` noun was a latent defect this ADR surfaced.** It read
`page is not None and not bid` — "no block id" standing in for "page grain",
true only because pre-620 nothing at page grain carried an id. A composed slide
carries the page's own id (stamped since ADR-519), so the proxy would have
called it *"the slide block"*. Both the frame and the chip now read the LABEL,
which names the grain directly, and the gate pins them together — they must
read identically before and after Send.
