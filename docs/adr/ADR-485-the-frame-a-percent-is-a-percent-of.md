# ADR-485 — The frame a percent is a percent of

- **Status**: Accepted + **Implemented** (2026-07-23; **D6** 2026-08-17; **D7** 2026-08-19). Gates: `api/test_adr485_measure_frame.py` (static shape) + `web/scripts/gates/adr485_measure_frame.mjs` (EXECUTING, with falsifiers).
- **Dimension**: Substrate (primary — the value's meaning) + Channel (the gesture that authors it)
- **Supersedes**: nothing
- **Amends**: ADR-472 D2 (the shared object layer is made actually shared — deck stage and IMAGES stage now agree on stage padding) · ADR-461 D3/D4 (the bound is unchanged; what the bound is a bound *of* becomes explicit) · ADR-466 D2 (`returnToFlow`'s clear-grain is widened to match `setGeometry`'s write-grain)
- **Preserves**: ADR-461 D4's aperture (deck + media only; `article`/`page`/`document` keep enumerated tokens) · ADR-443 R1 (the DOM is the model) · ADR-440 D7 (a gesture composes an existing op) · ADR-209 (every mutation attributed) · the enumerated-token invariant
- **Derivation**: the studio round-trip audit, 2026-07-23 (headless-Chrome receipts + a 16-artifact live corpus)

---

## 1. The question

The operator, on a deck slide: *a block resized smaller than its created width will not go back out to full width. Was it built to block growing, or is this post-creation handling?*

Neither. **A percent was being committed as a fraction of one rectangle and applied by CSS against a different one.**

## 2. What was actually happening

`resizeEnd` commits `msg.w = round(br.width / fr.width * 100)` where `fr = frame.getBoundingClientRect()` — the **border box**. The kernel applies `.slide [data-w] { width: var(--yw) }`, and a percentage width on a child resolves against its containing block's **content box**. `.slide` carries `padding: 3.5rem 4rem` under a global `box-sizing: border-box`, so the two rectangles differ by the padding.

Every drag therefore committed a number smaller than the one the member drew, and each correction lost the same fraction again. Executed in headless Chrome on a 992×558 slide:

```
width   100 → 87 → 76 → 66 → 57 → 50     one drag-to-fill loses 112.3px
height  100 → 80                          loses 89.2px
```

Height is worse because vertical padding is a larger fraction of 558px than horizontal padding is of 992px — so a corner drag also distorted the aspect ratio.

**The live corpus is the corroboration.** Across all 16 production artifacts there are six authored widths — 58, 60, 68, 70, 70, 78 — and **none above 78%**. If a member could reach the frame edge, some value would sit near 100. The three values on padded artifacts (58/60/68) sit on the predicted decay curve; the three on zero-padding IMAGES stages (70/70/78) sit higher. **The defect discriminates on exactly the variable the mechanism names**, which is what separates it from a plausible story.

## 3. Why every gate was green

All 25 Studio gates are static-source assertions. `test_adr461_geometry.py` has 47 checks and asserts, correctly, that the committed value is *"a PERCENT OF THE FRAME, not a pixel"*.

It never asks **which rectangle the frame is**. Nothing did. `measurableFrame` guessed it in the runtime, CSS resolved it from the containing block, and `returnToFlow` never reconsidered it on a carry — three independent answers to a question the system never wrote down.

That is the general lesson, and it is the same one ADR-482 recorded: *every check short of completing the gesture passed.* A round-trip invariant — read-back equals write — is invisible to a grep by construction.

## 4. Decisions

### D1 — The frame's rectangle is named once, at the runtime, per axis-class

A new `frameRects(frame)` helper returns both rectangles the CSS box model actually uses:

- **content box** — what `width:%` / `height:%` resolve against
- **padding box** — what `left:%` / `top:%` resolve against on an absolutely-positioned child

`resizeMove`, `resizeEnd`, `moveMove` and `moveEnd` all read from it. Preview and commit consume the same numbers, so what the member releases on is what lands.

The bound is untouched: a measure is still free **within** its frame and never unbounded. ADR-461 D4's aperture is untouched: deck + media only. This ADR does not widen anything — it makes the existing bound refer to the rectangle it always claimed to refer to.

**`x`/`y` were already correct** and are left alone in substance. `left:%` resolves against the padding box, and a `.slide` carries no left/right border, so padding box == border box horizontally. Verified in Chrome with a synthetic 10px border to disambiguate the three candidate formulas. They now read the same helper for one reason only: so the trailing-edge clamp (`xMax = 100 − wPct`) compares two percentages of the *same* rectangle, which it previously did not.

### D2 — The clear-grain matches the write-grain

`setGeometry` writes `x, y, w, h, z` as one geometry unit. `returnToFlow` cleared **two of the five**.

So a re-arrange carried a block into a `flex: 1` column while `--yw: 60%` survived — the same stored value silently re-based against a narrower rectangle. Chrome receipt: **595.2px before, 247.2px after** (−58.5%), with height collapsing 223.2px → 18.0px because a `flex-start` column has no definite height for `40%` to resolve against. No gesture involved; one click.

`returnToFlow` now clears the whole geometry unit — `w`, `h`, `z` alongside `x`, `y`. The arrangement's slots are about to lay the block out; a width that was a percent of the slide is not a width that means anything in a column. This is the honest completion of ADR-466 D2's stated intent ("its measures are cleared as it is carried"), which the implementation applied to only one axis pair.

### D3 — A clamp reads the served bound; a receipt reports what landed

Two separate lies, one root:

- The in-gesture preview floored **both** axes at a hardcoded `1`, while the kernel serves `w.min = 10` and `h.min = 1`. Drag width to 3%, watch the preview honour 3%, release, and the block renders at 10% — wider than the box the member let go of. The shared literal happened to equal one of the two bounds, which is why the asymmetry hid.
- The revision message was built from the **unclamped** value, so history recorded *"width 3%"* while the artifact stored `10%`. **A receipt that misstates the substrate is worse than a visual snap** — it is the one surface a member consults to find out what actually happened.

The runtime now receives the served bounds (interpolated into the pointer script at build time, the same way every other kernel constant reaches it) and clamps per key. The receipt is built after the clamp, from the value that landed.

### D4 — The positioned test reads both attributes

The kernel rule is `.slide [data-block][data-x][data-y]` — both required. The Design tab gated "Return to flow" on `hasAttribute('data-x')` alone, so a block with `data-x` and no `data-y` (writable by a lane, since the posture teaches the attributes as prose) offered an affordance for a state it was not in, and clicking it landed a revision that changed nothing visible.

### D6 — The origin travels with the box (amendment, 2026-08-17)

**The operator, on the same surface, one layer over:** *"I feel like I'm grabbing within the green selected, but then I can't width out to it."*

D1 named the **denominator** — `width:%` resolves against the frame's content box — and fixed every caller to divide by it. It never named the **ORIGIN**, and half a rectangle is not a rectangle. The east and south drags measured a delta from the **block's own edge** and divided it by the **frame's content width**:

```js
pct = ((e.clientX - br.left) / f.contentW) * 100   // two rectangles, one fraction
```

For a block laid out flush at the content-left the two agree, which is why D1's round-trip proof passed and why the executing gate stayed green over this for as long as it has existed. For a block **inset** from it — every flow block in a padded container, any block a `.col` gap offsets — they do not. Dragging to the frame's true right edge yields `(contentRight − blockLeft)/contentW`, short by exactly the inset. `maxPct = 100` never bound, **because the value never got there.** The member ran out of green before they ran out of percent.

The west branch was already frame-relative (D1 rewrote it); the east/south branches were the ones D1 did not visit. `frameRects` now returns `contentLeft`/`contentTop` beside `contentW`/`contentH`, so the origin is named once, where the box it belongs to is named.

**And the overlay drew a third rectangle.** `showFrame` painted `frame.getBoundingClientRect()` — the **border** box — while every percent resolves against the content box. The green outline was therefore *larger than the addressable area*, by exactly the frame's padding: the member aimed at green, the clamp stopped them short of it, and **the affordance and the constraint were two different rectangles.** This was `frameRects`' fifth reader and the only one that bypassed it. It now paints the content box, so reaching the green edge and committing `100` are the same act.

**The lesson, which is D1's own generalized:** D1 said *name the rectangle once*. It named the rectangle's **size** once and left its **position** to four call sites. A denominator without its origin is half an answer, and the half that was missing is the half the member's hand touches.

**The legacy duplicate, deleted.** `projection.ts` declared its own `DECK_STAGE_W = 992` and pinned `.slide` to it with `!important` in `pointer` mode — a VIEWER-baked width overriding the DOCUMENT's own `--stage-w`. `stageGeometry.ts`'s docstring already claimed this triple-copy was removed; the canvas copy was still live, so a deck authored at any other stage size (IMAGES seeds its own W×H per ADR-472 D3) rendered at 992 in the editor while `readStageSize` read the true value for the fit math — **the two disagreed by construction**, which is the exact split `stageGeometry.ts` exists to end. It now reads the same `var(--stage-w, …)` chain `PagedNavigator` converged on, with the shared fallback constant imported rather than restated. Third reader of one constant, not third copy of one number.

### D7 — The stage carries no padding; the container does (amendment, 2026-08-19)

**The operator, looking at the green frame D6 had just made honest:** *"is there a reason the slide selection in green is not the full slide? … think in terms of a simple PowerPoint or Google Slide. Is that content box needed?"*

**No. It was never needed, and keeping it left D1's central promise unkept.**

D1 named the rectangle once *per axis-class* — content box for `w`/`h`, padding box for `x`/`y` — and called `x`/`y` "already correct." Both halves are true in isolation, and together they mean **a deck slide has two frames**. On the 992×558 stage:

| measure | resolves against | rectangle |
|---|---|---|
| `x` / `y` (`position:absolute; left:%`) | padding box | **992 × 558** |
| `w` / `h` (`width:%`) | content box | **864 × 446** |

A block at `x=0%, w=100%` spans 0→864px, leaving **128px of slide unreachable on the right**. `x=100%` is the slide's true right edge, fully off-stage. The green overlay can draw only one rectangle, so after D6 it is honest for `w`/`h` and wrong for `x`/`y` — **the same defect D6 was written to end, one axis-class over.** D6's own closing sentence ("the rectangle the member aims at must be the rectangle the math uses") cannot be satisfied while there are two.

**The fix is not more geometry. It is deleting the cause.** `padding: 3.5rem 4rem` sat on `.slide` — a *stage*. Padding is a property of a text container; it is not a property of a coordinate system. Applied to the stage it silently amputated 13% of width and 20% of height from the space `x`/`y`/`w`/`h` address, and no value at any percent could name the missing band.

**The codebase had already voted, twice, and disagreed with itself:**

- `.slide[data-arrange="full-bleed"] { padding: 0 }` — a one-off cancellation, because full-bleed is *unrepresentable* while the stage is padded.
- `services/apps/images/stage.py` — `padding: 0`, carrying the comment *"Padding 0 so a positioned block's percent-of-frame is a percent of the visible stage."* The IMAGES stage, built later and against the same shared object layer, independently reached this decision and wrote down this exact reasoning.

ADR-472 D2 declares deck-slide and IMAGES-stage **one shared object layer**. They disagreed on the single property that defines the coordinate system. That — not the overlay's size — is the defect this amendment closes.

**The padding moves one level in, to the container that always existed.** Every deck arrangement opens with a `data-area` wrapper; the inset relocates onto it. Consequences:

- **One rectangle.** content box == padding box == border box == the stage. `x`, `y`, `w`, `h` resolve against the same thing. `frameRects` keeps both accessors and they now return identical numbers — the helper stays honest, its distinction simply stops being load-bearing.
- **The green frame is the slide.** What the member expected when they asked.
- **`w=100%` means full-bleed** — a background band, an edge-to-edge photo — previously unrepresentable at any value.
- **Nothing stored changes.** No document is rewritten. A block laid out in flow is inset by its container exactly as before; the only blocks that move are ones carrying `x`/`y`, and they move *because their frame became the whole stage*, which is the correction.

**Why this does not make decks uglier.** The margin is not removed, it is re-homed — the default authored deck renders identically. Typographic measure was never the stage's job and is unaffected: `.slide h1 { max-width: 34rem }` and `.slide p { max-width: 36rem }` still cap text width independently of the frame, which is the correct mechanism (measure belongs to type, not to the coordinate system). PowerPoint, Keynote, Google Slides and Figma all pad the *placeholder* and never the slide, for this reason.

**Deleted, not deprecated** (no future ambiguity): the `full-bleed` padding override becomes the general case and is removed; `DECK_STAGE_CSS`'s padding-dependent commentary goes with it. One rule, one rectangle, no exception list.

### D5 — What this does NOT do

- **Does not widen ADR-461 D4.** No continuous value reaches `article`/`page`/`document`. The three re-opening conditions in ADR-461 §D4 are untouched and none is claimed.
- **Does not change any bound.** `w ∈ [10,100]`, `h ∈ [1,100]`, `x`/`y ∈ [0,95]`, `z ∈ [0,20]` — all unchanged, all still served by the kernel and never invented downstream.
- **Does not add an operation.** Gestures still compose `setGeometry` (ADR-440 D7).
- **Does not touch the write door, the revision chain, or attribution.**
- **Does not fix `STAGE_DEFAULT_W`** — `projection.ts` exports it with a comment promising a `data-w → --stage-w` retrofit that does not exist, and it has zero importers. Deleted here as dead code rather than implemented, because no live stage needs it (every stage carries the mapping inline on its root at creation). If a stage ever loses its root `style`, that is the ADR that should build it, with the instance in hand.

## 5. The audit's negative results, recorded

Four suspected defects did not survive execution. Recording them so they are not re-investigated:

- **`parse ∘ serialize` idempotence** — fixpoint **16/16** across the live corpus. Ops do not drift artifacts. All 16 are source-*unstable* on first parse (a newline after `<html …>` absorbed, the trailing newline moving inside `</html>`) but that is a one-time normalization that does not compound.
- **Entity re-encoding as a two-writer divergence** — the mechanism is real (a bare `&` becomes `&amp;` on first parse; verified) but fixpoint holds in all seven cases tested, and there are **zero bare ampersands across all 16 artifacts**. Latent-theoretical.
- **Spurious no-op revisions** — zero consecutive same-blob writes on any `.html` path. The one 8-revisions/1-blob outlier is a scratch path reused by four create→rename cycles, where a `MoveFile` legitimately records a revision.
- **The enumerated-token invariant** and **`mode` vs `flow`** — both verified clean by execution.

## 6. Falsifiers

1. A drag-to-fill on a padded slide commits `100`, and the block does not move on release.
2. Repeating that drag five times leaves the value at `100` (no monotonic decay).
3. A re-arrange that carries a measured block leaves it with no `w`/`h`/`z`.
4. A width drag below 10% previews at 10%, not 1%, and the revision message reads `10%`.
5. Restoring the border-box denominator makes the executing gate red (the gate ships this falsifier).
6. `grep` shows no continuous value admitted on `article`/`page`/`document`.
7. **(D6)** A block **inset** from its frame's content-left reaches `100%` on an east drag. Restoring the block-relative origin caps it at `100 − inset%` and makes the executing gate red — verified by editing the shipped source, not only by arithmetic (the gate ships the arithmetic falsifier; the source edit was run once by hand and the check failed as predicted).
8. **(D6)** The green frame outline and the addressable area are the same rectangle: `showFrame` reads `frameRects`, and no raw `frame.getBoundingClientRect()` survives in it.
9. **(D6)** No `DECK_STAGE_W` literal survives in `projection.ts`; the deck stage rule reads `var(--stage-w, …)`.
10. **(D7)** The deck stage and the IMAGES stage carry the SAME stage padding (zero). A non-zero `padding` on `.slide` in the deck skin makes the gate red.
11. **(D7)** `frameRects` returns `contentW === padW` and `contentH === padH` on a deck slide: one rectangle, so `x` and `w` are percents of the same thing.
12. **(D7)** A block at `x=0%, w=100%` covers the stage edge to edge — full-bleed is expressible.
13. **(D7)** No `data-arrange`-scoped padding override survives in the kernel; the general case needs no exception.

## 7. The one-line statement

**A percent is meaningless until you say what it is a percent of. The gesture measured the border box, CSS resolved the content box, and the carry never re-asked — three answers to a question nobody had written down. Name the rectangle once, clamp from the served bound, and report what landed.**

**And there must be only ONE rectangle (D7).** Naming it per axis-class still left two, so half the coordinate system was unreachable at every percent. The cause was padding on a *stage* — a text container's property applied to a coordinate system. Move it to the container and the distinction dissolves: the affordance, the constraint and the math become the same rectangle, and full-bleed becomes sayable.

**And a rectangle is a size AND an origin (D6).** Naming only the size left the origin to four call sites, so the drag that could not reach the edge survived the ADR written to fix the drag that could not reach the edge. **The rectangle the member aims at must be the rectangle the math uses** — when the affordance and the constraint disagree, the member is right and the code is wrong.
