# ADR-461 — Bounded-continuous geometry: a slide has a frame, a page has a viewport

- **Status**: Accepted (2026-07-15) — D1–D3 Implemented-ready (no code in this commit; §8 sequences them)
- **Dimension**: Channel (primary — how the member shapes) + Substrate (the value axis, no new storage)
- **Supersedes**: nothing
- **Amends**: ADR-453 D7 (the "never raw geometry" refusal is scoped, and its stated reason is honoured rather than overridden) · ADR-453 D1 ("tokens reference intent, never hex" gains a bounded exception) · ADR-456 D4 (the Wix answer is completed, not reversed)
- **Preserves**: ADR-443 R1 (the DOM is the model) · ADR-209 (every mutation attributed) · ADR-440 D7 (direct manipulation is a gesture-composer, never a second write path) · ADR-456 D3 (per-breakpoint editing stays refused) · the enumerated-token invariant for every layout that reflows
- **Derivation**: [the drift ledger](../analysis/the-studio-drift-ledger-and-the-deck-question-2026-07-15.md) · [the geometry discourse](../analysis/does-a-block-have-a-size-the-geometry-discourse-2026-07-15.md)

---

## 1. The question

*Does a block have a size?*

The operator, from Claude Design's inspector (`Width 761px / Height 246px`, `Hug | Fixed | Fill`, `Position: Inline | Absolute`) and the Wix builder: **on-screen resizing, click-and-drag, real-time — obtainable within the html-native approach?**

It had been refused twice. Both refusals rested on an argument that does not survive inspection.

## 2. The argument that was standing in the way, and why it fell

The stated blocker (ADR-456:60, glossing ADR-443 R1): free geometry would be *"a shadow model in a costume"* — coordinates are a JSON tree by another name, which orphans the revision chain, which is the moat.

**This is a category error, disproven at the mechanism:**

- **R1's predicate is "compiled from."** ADR-443:29 forbids *"a JSON block model that HTML **is compiled from**"*. Its three named harms — HTML demoted to an *export format*, a *drifting second* source, an orphaned chain — **each require a second artifact to exist**. R1 does not forbid structured data; it *mandates* it (`data-*`). An attribute on the one source file has no second file, no compile step, no drift surface.
- **The chain cannot see geometry.** `write_revision` takes `content: str` and `sha256`s it (`authored_substrate.py:716`, `:363`); it never parses HTML. `DiffRevisions` is `difflib.unified_diff` on `splitlines()` (`revisions.py:326`). **No code path lets an attribute value affect chain linkage.** A dragged box is a one-line diff — *smaller* than `Re-arrange`, which rewrites subtrees.
- **`trace` joins by id, not by order.** `querySelector('[data-block-id="…"]')` (`projection.ts:630`). The only index-based addressing in the runtime is caret mapping *inside one block's clone* (`:1018`, scoped `while (node !== editingEl)`). **An absolutely-positioned block that keeps its id is invisible to the attribution path.** Blocks were an *attribution* grain (ADR-443:56 — "the finest attribution grain in the benchmark class"); that grain never cared where the block sits.
- **ADR-453 D7 already ruled this.** Its own parenthesis (`:185`): positioned slots are *"an escape valve that **doesn't break R1**"*. ADR-456's "costume" line was ADR-456:63's argument about **markdown as a second source format**, transplanted onto geometry-in-attributes. The transplant is the error.

**The moat was never the objection.**

## 3. What the real objection is

**The enumerated-token invariant** — `test_adr453_property_layer.py:83`:

```python
all(f"[data-{key}=" in STUDIO_KERNEL_CSS for key in STUDIO_TOKENS)
```

Kernel CSS is composed once (`compose_kernel_style_element`) and shipped *into* the artifact, so it must **pre-declare every selector it will ever match**. `[data-size="761"]` cannot be pre-written. This is real, coded, and tested — and it is what ADR-453:187's *"number-field geometry"* actually names.

And D7's **stated reason** is not the moat either. Verbatim (`:187`):

> number-field geometry (Studio edits intent discretely **because responsive HTML, not fixed frames**)

## 4. The seam

D7's reason is *sound* — and it has a boundary the kernel already drew. `studio.py:899-903`:

> a deck slide is a fixed 16:9 stage, exempt. … **a slide has no responsive obligation (fixed stage, overflow:hidden), a page does.** … this one is a statement about what a slide IS.

**A fixed 16:9 stage with `overflow: hidden` is exactly a fixed frame — the one thing D7's stated reason says Studio isn't.** D7's only stated reason does not reach the deck.

**The seam is responsive obligation, not the layout's name.** Note where that puts things, against the label intuition: **`page` (the website layout) sits with `document`, not with `deck`.** A landing page reflows; a slide does not.

## 5. Decisions

### D1 — Hug / Fill / Inline are tokens. Now, with no exception.

`Hug` (`width: fit-content`), `Fill` (`width: 100%`), `Position: Inline` (`position: static`, the absence-default) are **enumerated values**. They satisfy `test_adr453_property_layer.py:83` unchanged, with direct precedent in `fit: {cover, contain}`.

**Three of the five things in the inspector need no amendment to anything.** They ship as registry rows.

### D2 — Direct manipulation is a gesture over the existing ops. Not a new write path.

Click / drag / drop / resize are **gestures**, and ADR-440 D7 already sanctions them: *"Direct manipulation, when it comes, is a **gesture-composer** — never a second write path."*

A drag that lands as an attributed revision through the one write door **is what the seven ops already do**. This needs no new mechanism and no eighth operation (ADR-443 D2). A gesture composes an existing op; it does not become one.

### D3 — Bounded-continuous geometry, where a frame exists

Free values are admitted **only where there is a frame to be bounded by**:

- **the deck** — a slide's own 16:9 stage
- **media blocks** — an image's intrinsic ratio (`figure`, `gallery`, `full-bleed`, `picture-with-caption`)

**Everywhere else — `article`, `page`, `document` — keeps enumerated tokens.** D7's reason is undefeated there, and per-breakpoint editing is already refused (ADR-456 D3): a positioned hero on a page has no answer at 40rem.

**The mechanism** — the token model gains one axis: **a property whose *mechanism* is enumerable but whose *value* is not.** The kernel pre-declares the rule via `var()`; the element carries the value. This is the shape `data-ref` already uses: the kernel declares the mechanism, the element carries the referent. The invariant at `:83` is preserved in substance — every selector remains pre-declared.

**The honest remainder, named:** `position: absolute` removes an element from flow, so a positioned block **exits the `data-arrange` slot contract** (`[data-arrange] .cols`). It stays attributed and traced; it stops participating in the arrangement's layout. That is a layout-contract cost, not a moat cost, and it is the price.

### D4 — Continuous-everywhere is OPTED OUT, not refused

Recorded so reconsideration is evidence-driven rather than fatigue-driven.

**Why the boundary is future-proof rather than merely cautious:** bounded-continuous and continuous-everywhere are **different features, not the same feature at two scales**. *Bounded* means the frame is what makes the value meaningful — `left: 40px` inside a fixed 16:9 stage is a determinate fact; `left: 40px` on a band that reflows at 40rem is a guess about a viewport. Continuous-everywhere is not more of the first; it is **the removal of the bound**, applied to layouts that have no frame *because* they reflow.

So the boundary does work rather than holding a place, and the decision is reversible both ways: insufficient → the extension arrives with a receipt; wrong → the blast radius is deck and media, the two surfaces that already opted out of responsiveness.

**The cost, paid deliberately:** two sizing models is real. *"It depends which layout you're in"* is a worse explanation than one rule. It is paid because the alternative breaks `article`/`page` at 40rem with per-breakpoint editing refused.

**How the pressure to widen will arrive** — not as *"we want free geometry everywhere"* but as **"why can a deck do this and a page can't?"** A consistency complaint. It will read as a bug report; it is the boundary working. The answer: **a slide has a frame; a page has a viewport.** Unanswered, the model widens by attrition — one reasonable request at a time, none individually wrong.

**What legitimately re-opens it** (any one):
1. **Per-breakpoint editing gets un-refused** (ADR-456 D3 reversed) — free placement plus authored breakpoints is coherent; this dissolves the objection entirely.
2. **A `page` artifact demonstrably needs placement no arrangement can express** — the instance in hand, not *"Wix does it."*
3. **The two-model seam confuses more in use than the reflow breakage it prevents** — measurable; currently a prediction on both sides.

Absent one of those, widening is drift with a good story.

## 6. What this does NOT do

- **Does not touch `article` / `page` / `document`.** They keep enumerated tokens.
- **Does not un-refuse per-breakpoint editing** (ADR-456 D3 stands — it is the *reason* the decision is bounded).
- **Does not add an eighth operation.** Gestures compose existing ops (D2).
- **Does not introduce a coordinate model, a JSON tree, or a second source.** §2.
- **Does not ship rotation, effects/shadows, or raw per-block color** — the rest of D7's refusals stand untouched.
- **Does not make the deck a canvas.** It makes a block's size and position expressible where a frame bounds them. The deck remains blocks in a stage, not shapes on an artboard.

## 7. Falsifiers

1. `Hug` / `Fill` / `Inline` render with no change to `test_adr453_property_layer.py:83`.
2. A drag lands as exactly one attributed revision through the existing write door — no new op, no second write path.
3. A geometry edit produces a one-line diff in `DiffRevisions`, and `trace` still resolves the block by id.
4. A positioned block keeps its `data-block-id` and remains addressable by every existing op.
5. `grep` shows no continuous value admitted on `article` / `page` / `document`.
6. Kernel CSS still pre-declares every selector it matches (the `:83` invariant holds in substance).

## 8. Sequence

| # | Step | Amends canon? |
|---|---|---|
| 1 | `Hug` / `Fill` / `Inline` as registry rows | **No** — D1 |
| 2 | Gesture layer (drag/resize handles) over existing ops | **No** — D2, ADR-440 D7 pre-authorizes |
| 3 | Discrete stops + 9-position | **No** — ADR-453 D7's pre-authorized text (`:176`, `:183`) |
| 4 | Bounded-continuous via `var()` on deck + media | **Yes** — D3; amends ADR-453 D7/D1 |

Steps 1–3 need **no permission from any ADR** and cover most of the observed inspector. Step 4 is the only amendment — and it is bounded by D4.

## 9. The one-line statement

**The revision chain is `sha256` over a string and `difflib` over lines; `trace` joins by `data-block-id`. Neither can see a coordinate — so the moat was never the objection. The objection is that kernel CSS must pre-declare its selectors, and the answer is that a mechanism can be pre-declared while its value rides in the element. Free values where there is a frame to be bounded by; enumerated tokens where there is only a viewport to guess at. A slide has a frame. A page has a viewport. That difference is the whole ruling.**
