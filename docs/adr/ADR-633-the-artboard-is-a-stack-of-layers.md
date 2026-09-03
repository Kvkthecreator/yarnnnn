# ADR-633 — The artboard is a stack of layers: IMAGES takes its own chrome

- **Status**: Accepted
- **Date**: 2026-09-03
- **Supersedes**: nothing
- **Amends**: [ADR-472](ADR-472-images-as-a-first-class-app.md) D2 (the carve boundary is
  restated, not reversed) · [ADR-520](ADR-520-the-stage-view-and-the-adjustable-container.md)
  D4 (the navigator's scope becomes app-declared) · [ADR-544](ADR-544-the-containment-law-slide-layout-area-block.md)
  §4.3 (the artboard grain grows from a scope-discipline note into a property model)
- **Gate**: `api/test_adr633_the_artboard_is_layers.py`

---

## 1. Context — the pane wears another app's chrome

ADR-472 carved IMAGES out of Studio: its own route, its own backend package, its
own app registry row, dimensions-first creation. The carve was real and it held.
It stopped at the **backend and the housing**, and never reached the **chrome**.

The result, measured at `e380174`:

- `web/app/(authenticated)/images/page.tsx` is four functional lines:
  `<StudioSurface app={IMAGES_APP} />`.
- Of 17,644 lines in `web/components/authoring/`, **~88 are images-specific**
  (0.5%): an 8-line config object, an export-PNG prop gate, a fallback stage
  box, and the size-first creation modal.
- The string `layout === 'image'` appears **exactly once** in the entire
  frontend (`StudioDesignTab.tsx:1821`). There is no `isImages` variable.

None of that is drift. It is ADR-472 D2 working as designed — one implementation,
two consumers. The defect is narrower and it is a **vocabulary and organ** defect,
not a kernel one:

### 1.1 The pane calls one object by two wrong names

An IMAGES artboard is a `<section class="slide">` — the frame class IS the
staged grain (ADR-472 D2), and that inheritance is correct. But the chrome reads
the class literally:

| Site | Renders | For an artboard, says |
|---|---|---|
| `structureLabels.ts:117` | `cl?.contains('slide') → 'Slide'` | **"Slide"** |
| `structureLabels.ts:135` | `tag === 'SECTION' → 'Slide'` | **"Slide"** |
| `PagedNavigator.tsx:510` | `layout === 'deck' ? 'Slides' : 'Sections'` | **"Sections"** |

So the breadcrumb, the Esc-walk and the injected edit runtime call it a *Slide*,
while the left rail calls the same object a *Section*. Two wrong nouns for one
thing, neither of which is what it is. **No `'Artboard'` string exists anywhere
in the frontend.**

Note the shape of the second one: images is never *named*. It falls through
`layout === 'deck'` onto the **document** branch. Nobody chose that — it is an
unmade decision, not a decision to share.

### 1.2 The left rail is the wrong organ, correctly built

`PagedNavigator` is the **sequence** rail. ADR-520 D4 deliberately removed the
per-page structure tree from it: *"the navigator is the SEQUENCE — page cards,
reorder, multi-select — and nothing below the page grain."* That is the right
design for a deck, where the page IS the unit.

On an artboard the page is not the unit. The **layer** is. Mounted on `isPaged`,
a single-stage image file renders a one-card rail restating the canvas the member
is already looking at — noise where the compositor's primary navigation belongs.

### 1.3 The z-axis exists with no z-view

The substrate is already a layer stack. `stage.py` seeds
`<section class="slide" data-arrange="free">` with blocks carrying
`data-x`/`data-y`/`data-w` and `--yx`/`--yy`/`--yw`. ADR-544 D3 re-grained
`x`/`y`/`z` to `("artboard",)` — free position is an **IMAGES-only capability**,
gate-enforced. `nudgeZ` writes stacking order and the block menu offers Bring
forward / backward.

And yet **nowhere in the UI is a stacking order visible.** The member has a
z-axis reachable only through a context menu, on a surface whose entire purpose
is composing overlapping objects. In every compositor the operator has ever used
— Figma, Illustrator, Photoshop, Canva — the stack IS the left rail.

### 1.4 The property model is document-native to the bone

The block registry is heading · prose · callout · quote · checklist · list ·
divider · toggle · button · table · metrics · stat · comparison · timeline ·
person · chart · figure · gallery · logo-row. The tokens are size · align ·
indent · tone · variant · height · fit · ratio · scrim · font · measure · pagenum.

**There is not one layer-native property.** No opacity, no blend mode, no lock,
no hide. Even `figure` is a document's idea of a picture — *"a workspace image
CITED by reference, with a caption"*, wearing a `<figcaption>`.

Which is why the pane offers **TURN INTO → Quote / Checklist / Bulleted list**
on a block sitting on an advertisement.

---

## 2. First principles — what a compositor's chrome owes

Read from the conventions IMAGES actually competes with (Figma, Illustrator,
Canva), not from what Studio happens to have:

1. **The stack is the navigation.** A compositor's left rail is the object tree,
   ordered by depth, top-of-stack first. It is not a page list.
2. **Depth is a first-class, directly-manipulable axis.** Reordering is dragging
   in the tree, not a menu verb you must already know exists.
3. **A layer has properties a paragraph does not have** — opacity, blend, lock,
   visibility. These are what make composition *composition*.
4. **An artboard is a frame, not a page.** Multiple artboards coexist (the same
   ad at Square / Story / Wide), each a coordinate space, none a "page 2 of".
5. **Every object is addressable by name.** A member finds a buried layer through
   the tree, not by clicking through what is stacked on top of it.

Studio's chrome satisfies none of these, and **should not** — a deck is a
sequence of pages and its rail is right about that. The two apps need different
organs because they answer different questions.

---

## 3. Decisions

### D1 — The kernel stays shared; the chrome does not

This is the amendment to ADR-472 D2, stated so the next session cannot read this
ADR as a fork.

**Unchanged and explicitly still shared** — one implementation, two consumers:

- the `.slide` frame class as the staged grain's boundary
- the geometry measures (`x`/`y`/`z`/`w`/`h`) and their kernel CSS
- `artifactOps` (`setGeometry`, `setGeometryMany`, `nudgeZ`, `returnToFlow`)
- the selection algebra (`selection.ts`: `unify` / `scopeOf` / `arityOf`)
- `StudioSurface`, `StudioCanvas`, `SelectionGesture`, `blockRows`, the token
  and measure registries, `admits()`, the projection runtime
- `STRUCTURAL_PAGE_SEL` — one page selector, so indices always agree

**Newly app-scoped** — the chrome, which was never chosen to be shared:

- the left rail: a **sequence** rail (`PagedNavigator`) or a **layer tree**
  (`LayerTree`), never both
- the object noun (Slide vs Artboard) and the collection noun (Slides vs Layers)
- the inspector's artboard-grained sections

ADR-472 §3's four-layer table already predicted this: three of the four layers
diverge and **the middle one converges**. The middle layer is direct
manipulation of positioned objects. That is the kernel, and forking it would
re-create the exact failure §5 warned of — *artboards on which nothing can be
positioned*.

> **The one-line rule:** if it decides *how an object behaves*, it is kernel and
> stays shared. If it decides *what the member is shown and what it is called*,
> it is chrome and follows the app.

### D2 — The rail is DECLARED by the app, never derived from the layout

`AuthoringApp` grows one field:

```ts
objectModel: 'flow' | 'pages' | 'layers'
```

- `slides` → `'pages'` · `blogger` → `'flow'` · `images` → `'layers'`

The rail mount reads **this field**, never `layout === 'deck'`.

This is the decision that stops the defect recurring. §1.1's wrong noun exists
because the rail choice is a *derivation* — images fell through a deck ternary
onto a document branch. A derivation has a default; a declaration does not. The
precedent is ADR-518 D7, which retired per-site slug ternaries in favor of a
declared field for exactly this reason, and ADR-592, whose `stage` field was
**inert for five days** because `_implied_stage` back-derived it from the very
pair it replaced — a tautology. A declaration that nothing declares is not a
declaration.

**Obligation:** every app row declares `objectModel` explicitly. No fallback, no
implied value, no `?? 'pages'`. The gate asserts the population, not the shape.

### D3 — An artboard is an Artboard, everywhere the member can read it

The vocabulary is app-scoped and complete. `labelForElement` and the navigator
take the object noun from the app's model, not from the frame class:

| Grain | `pages` (slides) | `layers` (images) |
|---|---|---|
| the frame | Slide | **Artboard** |
| the collection | Slides | **Layers** |
| a block on it | Text / Image / … | **the layer's own name** |

`.slide` stays the class (D1 — it is the kernel's grain boundary). What changes
is that the chrome stops reading a *class name* as a *display word*.

This is ADR-544 D4's rule applied to the app it skipped: **the chrome says the
member's word, and never the substrate's.**

### D4 — The layer tree is two levels: artboard → layers

An IMAGES file holds **N artboards** (the same ad at Square / Story / Wide). The
substrate already permits it — `STRUCTURAL_PAGE_SEL` matches repeatable
`section.slide` — so this is a chrome capability, not a substrate change.

```
▼ ▢ Square 1080×1080
    ▣ WORK DIFFERENT      z:3
    ▣ subject cut-out     z:2
    ▣ gradient bg         z:1
▶ ▢ Story 1080×1920
```

- **Order is z-descending, top-of-stack first** — the compositor convention, and
  the inverse of document order. A layer with no `data-z` sorts by document
  order beneath those that have one (the absence-default rule: garbage degrades
  to natural behavior, never to zero).
- **Drag within an artboard restacks** — writes through the existing `nudgeZ` /
  `setGeometryMany`, one gesture, one revision. No new op.
- **The tree REPLACES `PagedNavigator` on `layers`.** Not beside it. A rail plus
  a tree is two answers to "where am I", which is the ADR-595 lesson (the desk
  is one surface).
- A layer's name is its text content, elided — or its block label when it has no
  text. A free-form authored string never becomes the display word (ADR-544 D4).

### D5 — Layer essentials become first-class properties

Four token rows at the `artboard` grain, plus position promoted out of the menu:

| Property | Kind | Why it is a token, not a measure |
|---|---|---|
| `opacity` | token | enumerated steps (100/75/50/25) — one kernel rule each |
| `blend` | token | a closed set (normal/multiply/screen/overlay) |
| `lock` | token | boolean-by-presence |
| `hide` | token | boolean-by-presence |

Each is a registry row + one kernel CSS rule, admitted through `admits()` — the
gate that **already fires** for `artboard` (`x`/`y`/`z` prove the path). No new
machinery.

`TURN INTO` is withdrawn at the `artboard` grain: converting a composed layer to
a bulleted list is a document act offered on a compositor surface.

**Deliberately NOT in this pass:** crop, mask, matte. Non-destructive raster ops
need a durable substrate model (CSS `clip-path` is a rendering trick, not an
authored fact) and they interact with the cut-out subjects `generate.py` already
produces. That is its own ADR, and pretending otherwise here would ship a
property whose value cannot survive a re-render.

### D6 — Deleted, not dual-run

Per the hooks discipline (ADR-472 D7 — the precedent this arc inherits):

- No `layout === 'deck'` ternary survives as the rail selector. The derivation is
  **deleted**, replaced by D2's declaration.
- `PagedNavigator` is **not** modified to grow a layer mode. It keeps its single
  job. A second mode inside it would be the dual approach wearing one filename.
- No `'Artboard'` alias beside `'Slide'` — the label ladder takes the app's noun
  and there is one source for it.

---

## 4. What this costs, stated

**Expressive loss:** none identified. Slides loses nothing (its rail and nouns
are unchanged); images loses `TURN INTO` at the artboard grain, which was never
a coherent offer there.

**The `.slide` tension stays.** An artboard is a `section.slide` called an
Artboard. That is a deliberate, documented inheritance (ADR-472 D2 / ADR-471 D-a)
and D1 keeps it: the class is a *kernel grain boundary*, the noun is *chrome*.
Renaming the class would fork the kernel to fix a display string — the
over-reach this ADR exists to refuse.

**Multi-artboard is chrome-only here.** Creating a second artboard, and
cross-artboard operations (resize-to-fit, copy a layer between boards) are NOT
decided by this ADR. The tree renders N artboards because the substrate already
holds them; authoring the second one is follow-on work.

**IMAGES is `stage: internal`** (ADR-488). This ships unadvertised. Re-unveiling
runs ADR-488 §3's checklist, unchanged by this ADR.

---

## 5. Falsifiers

The gate fails if:

1. **F1** — any app row omits `objectModel`, or the field is back-derived from
   `layout`/`slug` (the ADR-592 tautology).
2. **F2** — `labelForElement` returns "Slide" for an element on a `layers` app,
   or "Artboard" on a `pages` app.
3. **F3** — the position measures (`x`/`y`/`z`) leave the `artboard` grain, or
   are deleted (ADR-544 §4.3 — IMAGES breaks).
4. **F4** — a layer-essential token declares a grain wider than `artboard` (a
   deck block must not acquire opacity by a wide grain).
5. **F5** — `PagedNavigator` mounts on an app whose `objectModel` is `layers`,
   or `LayerTree` mounts on `pages`.
6. **F6** — `IMAGES_ARRANGEMENTS` declares Areas, or loses its seeded free
   position (ADR-544 §4.3, carried forward).
7. **F7** — the kernel CSS loses the `.slide [data-block][data-z]` rule, or any
   shared module in D1's list acquires an app conditional.

---

## 5a. Driven — what the first real run showed (2026-09-03)

Driven on a production artboard (`operation/untitled-image/image.html`, the
WORK DIFFERENT poster) through the Images chat pane, immediately after deploy.
Not a gate: a member's own file, a member's own prompt, no token named in the
ask.

**The chrome shipped and works.** The rail reads **LAYERS** with
`▼ Artboard 1  1080×1080` over nine named layers — D3 and D4 confirmed on a
real file rather than a fixture. (Drag-to-restack remains unexercised.)

**The craft loop closed.** The agent read a file and its reasoning carried
skill-only content the 242-byte description does not contain: the type must rest
"on solid protected ground, not in the gradient's fuzzy transition zone"
(step 4 — check the text's OWN region), "reads at thumbnail" twice as the
acceptance criterion (the quality bar's lead), and "3D lift against the photo
without a visible box" — refusing an anti-pattern it was never asked about.
It patched four layers across five revisions and NAMED the five it left alone.
Every reported coordinate landed (`headline-main` 58% → 66%, `scrim-grad`
45% → 35%).

**⭐ The evaluation lesson.** "Did it read the skill?" is a mechanism check, not
a craft check, and it predicts less than it appears to. The two questions that
carry signal:

1. **Did the skill change what the agent NOTICED?** Here, yes — it diagnosed
   *where the scrim arrives relative to where the type lands*, which is not
   obvious and is precisely what step 4 points at. Without the skill the
   plausible response is "bigger headline, add a shadow".
2. **Did it change what the agent REFUSED?** Also yes — the visible box. The
   negative half of a skill is the harder half to land, and it landed.

A skill is not a procedure the agent executes; it is **the set of questions the
agent asks before deciding**. All the actual judgment was the agent's.

**⭐⭐⭐ On the tokens: a first reading was WRONG, and the correction is the
more useful finding.**

The landed markup uses **zero** of the four new tokens. The first reading of
that (recorded here, then falsified against the substrate) was that the agent
"fell out of the grammar into raw CSS" because `opacity`'s three steps
(75/50/25) could not express the 62% and 32% its prose described — and that D5
had therefore mis-shaped a continuous property as an enumerable token.

**Driven against the actual bytes, that is not what happened.** In the artifact
BODY — everything the agent authored — there are **0** `opacity:` declarations,
**0** `mix-blend-mode:`, and **0** `data-opacity`/`data-blend`. Every one of the
8 `opacity:` rules in the file is OUR kernel CSS (the v20 retrofit, landed
correctly) or a pre-existing keyframe. What the agent actually wrote is **14
`rgba()` values**, and every one of them is a COLOUR: gradient stops on the
scrim (`rgba(10,8,5,0)` → `0.99`), a text colour on the body copy
(`rgba(250,248,245,0.62)`), a text-shadow on the headline.

**Colour-with-alpha and layer-opacity are different operations, and the agent
picked the right one.** `data-opacity` dims a whole layer including its
children; `rgba()` sets one channel of one colour. For a gradient scrim, rgba is
CORRECT and `data-opacity` cannot express it at all — a gradient's stops each
carry their own alpha. For dimming body copy against a headline, a colour is
also the better tool: it leaves the layer's own opacity free for a later
composition move. **The token was not reached for because the composition never
needed a whole-layer dim.**

So D5's shape is not falsified by this run — it is simply **unexercised**.
`opacity`, `blend`, `lock` and `hide` remain plausible; none has yet been driven.

**⭐⭐ The real lesson is about the evidence, not the grammar.** "Token count
is 0" read as a design defect, and the fix it implied (re-shape `opacity` as a
measure) would have been actively wrong: the posture teaches measures as
*"member-authored geometry… preserve them exactly"* and never tells the agent it
may SET one, while tokens get *"set them yourself when asked in plain words."*
Moving `opacity` to a measure would have moved it into the category the agent is
told to leave alone — converting an unexercised feature into an unreachable one.

⭐ **A zero is not a verdict.** It says nothing was used; it does not say why,
and the two candidate whys (the grammar could not express it · the composition
never needed it) imply opposite fixes. Read the bytes before re-shaping the
grammar. The same class as ADR-592's inert field and ADR-630's un-enforced
ceiling: an aggregate that looks like a finding until you ask what produced it.

**What IS still open on the grammar** — genuinely, and narrowly. `z` is a
measure with NO inspector control (written only by menu verbs and the tree's
drag), and the measure sections are hand-keyed by name (`m.key === 'w' || 'h'`,
`'x' || 'y'`), so a sixth measure needs a new section rather than registering.
`setMeasure`'s key guard is `^[a-z]{1,3}$`, which admits no long-named measure
at all. None of that is urgent, and none of it is what this run showed.

**Open, and NOT closed by this ADR:** `derived_from` does not cite the skill a
revision followed, and no mechanism would make it (the run cited the photo it
composed, which is content consumed — arguably the correct edge). ADR-630's
loop is open by construction. Whether craft-applied belongs on that edge at all
is a question for ADR-630, not this one.

## 6. The one-line statement

**IMAGES stops borrowing a document's rail and a deck's nouns: the artboard gets
the organ its medium has always implied — a stack of named layers, ordered by
depth, carrying the properties a layer has — while the object kernel it shares
with Studio stays exactly one implementation.**
