# ADR-485 — The frame a percent is a percent of

- **Status**: Accepted + **Implemented** (2026-07-23). Gates: `api/test_adr485_measure_frame.py` (static shape) + `web/scripts/gates/adr485_measure_frame.mjs` (EXECUTING, with falsifiers).
- **Dimension**: Substrate (primary — the value's meaning) + Channel (the gesture that authors it)
- **Supersedes**: nothing
- **Amends**: ADR-461 D3/D4 (the bound is unchanged; what the bound is a bound *of* becomes explicit) · ADR-466 D2 (`returnToFlow`'s clear-grain is widened to match `setGeometry`'s write-grain)
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

## 7. The one-line statement

**A percent is meaningless until you say what it is a percent of. The gesture measured the border box, CSS resolved the content box, and the carry never re-asked — three answers to a question nobody had written down. Name the rectangle once, clamp from the served bound, and report what landed.**
