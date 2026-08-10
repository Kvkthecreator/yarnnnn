# ADR-544: The containment law — every block lives in an Area, and position is a place in the hierarchy

> **Status**: **Accepted** (2026-08-10, operator-ratified — *"ratify. please
> proceed in full with the prior mentioned discipline on streamlining, with
> clean up, doc and code in singular style"*; implementation delegated).
> Drafted from the operator's hierarchy audit of a live deck
> (`operation/ir-deck-v3/deck.html`). The containment half is operator-decided
> ("the containment law should follow and not allow free flowing placements");
> the vocabulary half is operator-decided for three of four grains, with `Area`
> chosen for the region grain and the role set accepted provisionally ("will be
> updated downstream").
> **Date**: 2026-08-10
> **Dimension**: **Substrate** (what a slide's structure IS) primary, with
> **Channel** consequences (what a click selects, what a drag means) that are
> the reason the substrate change is worth making.
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**:
> - **ADR-511 D3** (the conventional substrate; the structural grain) — extended.
>   This ADR names the grains D3 left as "structure vs content".
> - **ADR-519 D1** (four addressable grains, one law) — **amended**. Its
>   `Artifact root → Page → Container → Block` chain is re-cut: the middle rung
>   was one word for two substrate concepts (`.cols`/`.col` and `data-slot`).
> - **ADR-519 D2** (Group is a layout-less container) — **superseded in the deck
>   medium**. Under containment there is no layout-less container on a slide.
> - **ADR-461 D3 / ADR-466 D2** (bounded position; the "honest remainder") —
>   **retired for decks**, retained for IMAGES (§4.3).
> - **ADR-472 D2** (`block-staged` — the shared staged-frame grain) — narrowed
>   to its IMAGES consumer.
> - **ADR-541 D1/D2** (the selection algebra) — extended, not re-cut: `scopeOf`
>   gains an Area rung and loses the free-floating case.
> - **ADR-526 D1 + AUTHORING.md rule 12** (a Docs "section" is the span between
>   headings; **no `<section>` wrapper**) — **upheld, and the reason this ADR
>   does not use the word "section"** (§3.1).
> - **ADR-254** (file-format discipline) — unchanged; no new file, no new format.

---

## 1. Context — a hierarchy the surface cannot speak

The 2026-08-10 audit drove a live deck through the doorway rather than the
gates. Three findings, each a different layer of one fault.

### 1.1 The containment story is different in every arrangement

The eleven deck arrangements in `api/services/authoring.py` do not agree on
where a heading lives:

| arrangement | heading | content regions |
|---|---|---|
| `title` | **inside** `div[data-slot="heading"]` | — |
| `section-header` | **inside** `div[data-slot="heading"]` | — |
| `closing` | **inside** `div[data-slot="heading"]` | — |
| `content` | **outside** every slot — a bare `<h2>` child of `.slide` | `main` |
| `two-column` | **outside** — bare `<h2>`, then `.cols` | `main`, `side` |
| `comparison` | h2 **outside**; the h3s **inside** `.col`s that carry NO slot | `left`, `right` |
| `picture-with-caption` | **outside** | `media`, `caption` |
| `agenda` | **outside** | `main` |
| `big-number` | kicker **outside** | `main` |
| `full-bleed` | — | `media` |
| `quote` | — | `main` |

A block is therefore sometimes in a named region, sometimes a direct child of
the slide, and sometimes in a `.col` that is not a region at all. **There is no
invariant** — `data-slot` is optional, free-form, and authored by the LLM
(`authoring.py` §"Arrangements": *"give its content regions data-slot"*).

### 1.2 The middle rung is two concepts wearing one word

ADR-519 D1 named the chain `root → Page → Container → Block`. In the substrate
"Container" is two different things:

- **`.cols` / `.col`** — a grid, declared by the **skin's** CSS.
- **`data-slot="name"`** — a named region, declared by the **arrangement**.

They are sometimes the same element (`<div class="col" data-slot="main">`),
sometimes nested (`.cols` > `.col[data-slot]`), sometimes only one is present
(`comparison`'s `.col` has no slot; `content`'s slot has no `.col`). Both carry
`data-block-id` after `normalizeStructure`, so both appear in the breadcrumb —
which is why a member selecting one paragraph reads
**`slide 2 › columns › main`**: two structural rungs, neither of them a word
anyone chose for an operator.

### 1.3 Position silently ejects a block from the structure

Dragging a block writes `data-x`/`data-y`, clamped 0–95% **of the slide**
(`authoring.py` measure registry). The registry states the consequence plainly:

> *"A positioned block **exits the slot contract** (the ADR-461 honest
> remainder) and re-enters flow when an arrangement re-lays the page."*

So a drag is not a move within the layout — it is an **escape from it**. There
is no snapping, no region-awareness, no re-parenting. The operator's report is
the predicted behavior, met: *"when i select a header and move it around a
slide, it doesn't seem to have any logic and just ends up floating anywhere,
overlapping."*

### 1.4 Why these are one fault, not three

Each is the same shape: **a model that is coherent one layer above where the
member's finger lands.** The substrate is honest CSS; the canon is consistent;
and neither reaches the click. §1.1 makes the hierarchy unstateable, §1.2 makes
it unsayable, §1.3 makes it escapable. Fixing any one alone leaves the other
two producing the same confusion through a different door.

### 1.5 The co-authoring argument (the operator's, and the decisive one)

Free placement is not merely untidy — it is **the thing an LLM revision cannot
reason about**. A positioned block belongs to no region, so a later AI pass can
only preserve coordinates it does not understand or clobber them. Containment
is what makes a slide *re-describable*: "the body area of slide 2" is a
durable address across a human edit, an AI revision, and a layout change;
`--yx: 34%` is not. **The determinism that containment buys is the whole
co-authoring premise** (FOUNDATIONS: the substrate is authored and attributed;
a fact with no home cannot be re-authored honestly).

---

## 2. The vocabulary decision

### 2.1 Why not "Section"

The operator proposed *slide / layouts / sections / objects*. Three of four are
adopted verbatim. **"Section" is refused because it is already load-bearing in
two other places:**

1. **AUTHORING.md rule 12 / ADR-526 D1** — in Docs, *"a 'section' is the span
   from one heading to the next. There is no `<section>` wrapper and no section
   node."* This is a **standing refusal** with named reopening evidence.
2. `<section>` is the **HTML tag of the slide itself** (`<section class="slide">`).

Using "section" for a within-slide region puts one word on three referents —
the precise drift this ADR exists to end.

**"Object" is likewise refused**: it is already a selection **tier** in
`scopeOf` (`text | object | structure`). A grain named `object` and a tier named
`object` would collide at the one derivation home ADR-541 built.

### 2.2 Why not typing Areas by content ("title / subtitle / body")

Considered and refused. Naming a region by *what it contains* duplicates what
the block already declares (a heading block knows it is a heading) and breaks
under the operator's own examples: "multiple subtitles" makes the name stop
identifying anything, and "2-column body" needs two regions with one name. The
Figma benchmark the operator invoked argues the other way — a frame is named by
its **place in the composition**, not by its contents.

### 2.3 D0 — The four grains, named once

```
Slide      the frame — one coordinate space, one canvas          (operator's word)
  Layout   the named arrangement the slide wears ("Two column")  (operator's word)
    Area   a region of the layout, typed by ROLE                 (operator-chosen)
      Block  an object in an Area: heading, text, image, chart   (unchanged)
```

Every user-facing surface — pane header, breadcrumb, canvas badge, navigator,
menus, and the LLM-facing grammar — uses these four words and no others for
deck structure. `.cols` / `.col` / `slot` / `container` / `prose` / `main` /
`side` never appear in operator-facing text.

**The layout gallery already speaks this way** and is the evidence the
vocabulary is right: "Title slide · Content · Two column · Comparison" are
Layout names, and they are the one part of the surface that reads naturally
today.

---

## 3. Decisions

### D1 — Containment is total: every block lives in exactly one Area

On a deck slide, **no block is a direct child of the slide**. Every arrangement
declares Areas; every block sits in one. The eleven fragments in §1.1 are re-cut
so the heading of `content` / `two-column` / `comparison` / `picture-with-caption`
/ `agenda` / `big-number` lives in a declared heading Area, exactly as `title` /
`section-header` / `closing` already do.

**The invariant is checkable and MUST be gated**: on a deck slide, every
`[data-block]` has an Area ancestor within its slide. A fragment that violates
it is a defect, not a variant.

### D2 — An Area is one substrate concept, typed by role

The `.cols`/`.col` vs `data-slot` split (§1.2) collapses: **an Area is the
region element, and the grid is a layout property of its parent** — the ADR-516
"one mechanism" rule, which already owns direction/gap/align. A `.col` that
holds blocks IS an Area and carries the region marker; a `.cols` wrapper is the
parent Area's declared layout, not a rung of its own.

Consequence: the breadcrumb loses a rung. `slide 2 › columns › main` becomes
`Slide 2 › Body (left)` — one structural step, because there is one structural
concept.

An Area carries a **role** from a closed set — `heading | body | media | aside`
— and a **place** for disambiguation among same-role siblings. The role is the
Area's identity; the authored name is retained as data but is **never a display
word** (§D4). *Accepted provisionally per the operator: the role set is expected
to be revised downstream, and this ADR fixes the mechanism, not the final
enumeration.*

The `role` field **already exists** on every slot row (`{"name": "main", "role":
"flow"}`) and is read today only by the media picker. This ADR promotes it from
a behavioral hint to the Area's identity — the vocabulary was already half-built.

### D3 — Position is a place in the hierarchy, never a coordinate (decks)

A block's position IS *its Area + its order within that Area*. There is no
free placement on a deck slide.

- **Drag** = re-parent and/or reorder — it moves a block **between and within
  Areas**, and can never leave one.
- `x` / `y` / `z` are **retired for the deck medium**. The block-level geometry
  a slide keeps is size within its Area (the existing `w`/`h` measures).
- **IMAGES keeps free positioning in full** (§4.3) — its stage is a composition
  surface where overlap is the point, and `services/images/stage.py` seeds
  `data-x`/`data-y` deliberately. `block-staged` narrows to that one consumer.

### D4 — The chrome says the four words, and never the substrate's

`labelForElement` (`structureLabels.ts`) stops returning raw substrate strings
for deck structure:

- a raw `data-slot` value is **never** a display label (today: `if (slot) return
  slot`) — the Area's role + place produce the label;
- `.cols`/`.col` never produce `columns`/`column` — they are not a grain (D2);
- a block's label comes from the **registry's human label**, not its
  `data-block` attribute.

**The registry label already exists and is already correct**: `"prose": {"label":
"Text"}`. It is served to the FE and consumed *only* by the insert and Turn-into
menus, while the pane header, breadcrumb, and canvas badges read
`selection.label` — stamped from the raw attribute. The same object is
**"Text" in the menu you insert it from and "PROSE" in the pane that describes
it.** This is a mis-wire to an existing source of truth, and D4 closes it by
routing every label through one derivation.

### D5 — Selection follows containment

`scopeOf` (ADR-541 D2 — still the one derivation home) is re-cut onto D0's
grains: `document | slide | area | block | range`. Consequences:

- **Click** selects the Block. **⌘-click** descends; **Esc** walks out — the
  ladder is unchanged in gesture, re-pointed at the new grains.
- **A set is homogeneous in grain and shares one parent Area.** This makes the
  cross-container range from the audit (a drag from `main` into `side`)
  **structurally illegal** rather than undefined-and-unreported.
- **Open question carried into implementation, not resolved here**: sibling-only
  forbids selecting two blocks in *different* Areas to align them — a
  legitimate gesture in the Figma benchmark. Align/distribute is ADR-519 D4's
  one set-subject section. The implementation MUST test this case before the
  sibling rule is locked; if it holds, align/distribute needs an explicit
  carve-out stated here as an amendment.

### D6 — Layout change maps Area → Area by role

`applyArrangement` maps blocks by **role**, deterministically: heading→heading,
body→body, media→media, with place breaking same-role ties and overflow landing
in the primary body Area. It currently name-matches with a positional fallback
(`artifactOps.ts`), which is fragile *because names are free-form* — the same
root cause as §1.1.

This rung is upstream (it defines what an Area re-lay *means*) and lands here;
the remainder of re-arrange semantics stays downstream, per §5.

### D7 — Existing decks are healed, not grandfathered

Decks in the wild carry positioned blocks and slot-less headings. `applyArrangement`
already clears `x`/`y`, so re-arranging heals a slide today. That is not enough
to rely on: **a one-time migration re-homes slot-less blocks into role-typed
Areas and clears deck `x`/`y`.** A block whose Area cannot be inferred lands in
the slide's primary body Area — never dropped, never left un-homed.

---

## 4. What this costs, stated

### 4.1 Expressive loss, named honestly

Free placement **is** expressive, and D3 removes it from decks. A member who
wants a block at an arbitrary point on a slide can no longer have it. This is
accepted deliberately: the operator's determinism argument (§1.5) values a
re-describable slide over an arbitrarily-composed one, **for the deck medium
specifically**. The escape hatch is real and named: IMAGES is the composition
surface, and it keeps free placement in full.

### 4.2 Migration risk

D7 rewrites existing decks. A heal that mis-infers an Area moves a block
somewhere the member did not put it. Mitigations: the primary-body fallback is
never a drop; every heal is an ordinary attributed revision (`write_revision`),
so it is visible in history and revertible per file.

### 4.3 Scope discipline — IMAGES is untouched

`x`/`y`/`z` and the `staged` grain are **not deleted**. `services/images/`
depends on them structurally (`stage.py` seeds `data-x`/`data-y` on its
scaffolds; `generate.py` reads the `--yx/--yy/--yw/--yh` vars). The retirement
is deck-scoped. A sweep that deletes the measures outright breaks IMAGES and is
the predictable over-reach of this ADR.

### 4.4 Amendment cost

ADR-519 D1's four-grain chain and D2's layout-less container are re-cut for
decks; AUTHORING.md's interaction matrix, the pane spine table, and the label
rule all move. Canon must land **in the same commit** as the code, per the
project's doc-first discipline.

---

## 5. Not decided here

- **The remainder of re-arrange semantics** (what survives beyond the Area
  mapping; group dissolution) — downstream, and now decidable because D2/D6
  define what a region is.
- **The final role enumeration** — provisional per the operator.
- **Web/Docs media** — this ADR is deck-scoped. Web bands and Docs flow are
  governed by ADR-505 D3 and ADR-526 respectively and are untouched.
- **The paged-range defect's guard**, if it is wanted *before* this lands: D5
  makes it illegal by construction, but a standalone `user-select` refusal can
  be pulled forward independently if the bleeding should stop first.

---

## 6. Falsifiers

1. **If any deck fragment ships a `[data-block]` without an Area ancestor**, D1
   failed — the invariant is gated, so this is a gate failure, not a review
   finding.
2. **If any operator-facing string renders `slot`, `col`, `cols`, `container`,
   or a raw `data-block` value** for deck structure after this ships, D4 failed
   as a chokepoint — move the derivation, never add a second (the ADR-541 D2
   rule, inherited).
3. **If a drag can place a deck block outside every Area**, D3 failed.
4. **If a layout change moves a block to an Area of a different role** (with a
   compatible role available), D6's mapping is not deterministic.
5. **If IMAGES loses free positioning**, §4.3's scope discipline was violated by
   the implementation.
6. **If align/distribute across Areas proves necessary** (D5's carried
   question), the sibling-only rule needs an explicit carve-out — that is an
   amendment to record, not a silent widening.

---

## 7. Implementation phases

Sequenced so each phase is independently verifiable, substrate before surface:

1. **Areas in the substrate** — re-cut the eleven deck fragments (D1), collapse
   `.col`/`data-slot` to one Area concept with roles (D2), plus the invariant
   gate (F1).
2. **The heal** (D7) — migration for decks in the wild; receipts per file.
3. **Position** (D3) — drag becomes re-parent + reorder; deck `x`/`y`/`z`
   retired, IMAGES verified untouched (F5).
4. **Vocabulary** (D4) — one label derivation; the `PROSE`→`Text` mis-wire and
   the raw-slot leak close together.
5. **Selection** (D5) — `scopeOf` onto the new grains; the align/distribute
   question tested before the sibling rule locks.
6. **Layout mapping** (D6) + canon (AUTHORING.md, ADR-519 amendment banners,
   GLOSSARY entries for Slide/Layout/Area/Block).

**A browser click-pass gates this arc, not the gate battery.** The defects in
§1 were all invisible to green gates — they were found by driving the doorway.
