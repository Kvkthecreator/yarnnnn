# Does a block have a size? — the geometry discourse

**2026-07-15 · discourse + the operator's ruling (§8). RATIFIED as [ADR-461](../adr/ADR-461-bounded-continuous-geometry-a-slide-has-a-frame.md) — read the ADR for the decisions; this doc is the evidence they rest on.** Opened at the operator's direction: re-open the geometry axiom **fully**, one thread, cut by seam rather than by layout label. Companion to [the drift ledger](the-studio-drift-ledger-and-the-deck-question-2026-07-15.md).

§§1–7 establish **what is actually true**, with mechanism-level receipts, so the decision is made against evidence rather than against a remembered argument. The headline: **the argument that killed this twice is a category error, and ADR-453 D7 contradicts it in its own parenthesis.** The objection that replaces it is real, coded, and enforced by a test — and it has an answer.

**§8 is the ruling: bounded-continuous on deck + media; enumerated tokens everywhere else; continuous-everywhere OPTED OUT, not refused** — with the conditions that would legitimately re-open it recorded, so reconsideration is evidence-driven rather than fatigue-driven.

---

## 0. Why this is one thread, not four

The operator asked whether to sequence deck / article / website separately from document. **The four labels are the wrong cut** — the ledger measured them at ~5% distinct (`document` vs `article` differ by `46rem` vs `42rem` and three selectors).

Two real seams exist underneath, and neither matches the label split:

| Seam | Cuts | Decides |
|---|---|---|
| **Responsive obligation** | **deck** \| article · page · document | whether geometry is *safe* |
| **What the unit is** (`mode`) | deck · page \| document · article | whether the container or the block is addressed |

Splitting the discourse by label would relitigate the same question four times, once per skin. **The question — *does a block have a size?* — is identical for a deck slide, a landing-page hero, and an image in a document.** So: one thread. The layout differences fall out as *consequences*.

The one thing that genuinely separates: the `page`/website layout ships looking like a document (inherits Georgia serif + `#fdfcfa` paper, overrides neither). That's a **design-system** problem, not a geometry one. Different discourse.

---

## 1. The claim under test

From ADR-456:60, glossing ADR-443 R1, and the reason free placement was refused:

> free geometry would be **"a shadow model in a costume"** — continuous coordinates amount to a JSON tree by another name, which orphans the revision chain, which is the moat.

If true, the discourse is unwinnable and should stop here. **It is not true.**

---

## 2. R1's predicate is "compiled from" — verified

`ADR-443:29`, verbatim:

> **R1 — No shadow content model. The DOM is the model.** Semantics live IN the HTML as thin `data-*` annotations; **there is no JSON block model that HTML is compiled from.** A shadow model would demote HTML to an export format (violating axiom 1), create a drifting second source of truth (violating Singular Implementation), and orphan the revision chain.

Read the three named harms. **Each one requires a second artifact to exist:**

- *"demote HTML to an **export format**"* — requires something HTML is exported *from*
- *"a **drifting second source of truth**"* — requires a *second* source to drift *against*
- *"orphan the revision chain"* — see §3

**The distinguishing predicate is "compiled from," not "structured."** R1 does not forbid structured data — R1 *mandates* it (`data-*` annotations). The entire shipped stack is structured data in attributes: `data-block`, `data-block-id`, `data-arrange`, `data-align`, `data-scrim`.

`style="width:761px"` is structured data in an attribute. **No second file. No compile step. No drift surface.** The HTML still *is* the source.

Note the tell: ADR-456:63 concedes markdown violates R1 *"not in letter but in structure."* The author of the "costume" line **admitted it wasn't a letter violation** and argued structure instead. That concession doesn't transfer: markdown-as-second-source genuinely is a second *source format* — that was D1's whole ruling. **An attribute on the one source file is not.**

---

## 3. The revision chain cannot see geometry — mechanism-level disproof

`api/services/authored_substrate.py:716`:

```python
sha = _sha256(content)
_upsert_blob(db_client, sha, content)
parent_version_id = _read_head_revision_id(db_client, user_id, path, workspace_id)
```

`:363` — `def _sha256(content: str) -> str: return sha256_bytes(content.encode("utf-8"))`

**`write_revision` takes `content: str` and never parses it.** The chain is linked by `(user_id, path)` + a parent pointer. The only content-dependent step in the entire write door is `_resolve_derived_from` (`:712`), which lifts `derived_from:` frontmatter and `data-ref` citations — a `style` attribute is neither.

`api/services/primitives/revisions.py:326`:

```python
difflib.unified_diff(from_content.splitlines(keepends=True), to_content.splitlines(keepends=True), ...)
```

**Line-based `difflib` on an opaque string. No HTML parse anywhere.**

**There is no code path by which any attribute value can affect chain linkage.** "Orphan" is a real hazard *for its actual referent*: if HTML were compiled from JSON, the chain would track build output while authorship happened in the JSON — it would witness the compiler, not the human. **That hazard is created by the compile step, not by coordinate values.** Geometry written into the one source file is witnessed by the identical sha256 as any other edit.

**Drag a box:** `left:40px` → `left:80px` is a **one-line diff**. That is *smaller* than sanctioned ops — `Re-arrange` rewrites whole subtrees. If diff noise were the objection, `Re-arrange` would be the defendant.

---

## 4. `trace` joins by id, not by flow order — verified

The projection→source join, verbatim (`projection.ts:630`):

```js
el = document.querySelector('[data-block-id="' + (window.CSS && CSS.escape ? CSS.escape(blockId) : blockId) + '"]');
```

Grepped the runtime for index-based addressing in the attribution path: **the only `childNodes[…]` hit (`:1018`) is caret-position mapping inside a single block's clone** (`while (node !== editingEl)` — it never crosses a block boundary). Split/merge internals, not attribution.

**`querySelector('[data-block-id="…"]')` returns the element whether it is `position: static` or `position: absolute`.** An absolutely-positioned block that keeps its id and stays in the DOM is **invisible to the attribution path**. Nothing notices.

This is the deepest point in the discourse, and it connects to the ledger's finding that **blocks were an attribution grain repurposed as an editing grain**. The attribution grain does not care where the block sits. It never did.

---

## 5. D7's stated reason is responsiveness — and D7 pre-authorizes the thing it refuses

`ADR-453:187`, the entire clause:

> **number-field geometry (Studio edits intent discretely because responsive HTML, not fixed frames)**

**The stated reason is "responsive HTML, not fixed frames."** The words *moat*, *revision chain*, *shadow model*, and *orphan* do not appear.

And `ADR-453:185`, D7's own parenthesis:

> if true free-placement demand ever materializes it is a new *arrangement kind* with positioned slots — **an escape valve that doesn't break R1**

**D7 explicitly holds that positioned geometry is R1-compatible.** ADR-456:60's "shadow model in a costume" *contradicts the ADR it claims to rest on* — that phrase was ADR-456:63's argument about markdown-as-a-second-source-format, transplanted onto geometry-in-attributes. **That transplant is the category error.**

D7's framing elsewhere is a **taste** argument, honestly labelled: *"the member composes within a layout system… they do not author free geometry"* (`:53`) — Wix/Webflow vs Figma, a product-family choice. And `:217`: *"Figma's ergonomics arrive without ever importing Figma's geometry."*

### The concession already in the code

`api/services/studio.py:897-903` (re-annotated in `8bc5384`):

```
/* ... a deck slide is a fixed 16:9 stage, exempt.
   ... a slide has no responsive obligation (fixed stage, overflow:hidden), a page does.
   ... this one is a statement about what a slide IS. */
```

**A fixed 16:9 stage with `overflow:hidden` is exactly a fixed frame — the one thing D7's stated reason says Studio isn't.** D7's only stated reason does not apply to decks, *by the kernel's own reasoning*.

---

## 6. What the real objection is

Not the moat. **The enumerated-token invariant** — `api/test_adr453_property_layer.py:83`:

```python
all(f"[data-{key}=" in STUDIO_KERNEL_CSS for key in STUDIO_TOKENS)
```

Every token must be an attribute-selector match on a **pre-declarable** value. Kernel CSS is composed once (`compose_kernel_style_element`, `studio.py:926`) and shipped into the artifact; it cannot pre-write `[data-size="761"]`.

**This is a real, coded, tested constraint. It is the thing to beat — not the revision chain.**

### Claude Design's inspector, scored against it

The operator's reference: `Width 761px / Height 246px`, `Hug | Fixed | Fill`, `Position: Inline | Absolute`.

| Inspector | CSS | Expressible today? | Why |
|---|---|---|---|
| **Hug** | `width: fit-content` | **YES, trivially** | A one-value token. Same shape as `pagenum: {on}`. One kernel rule. |
| **Fill** | `width: 100%` | **YES, trivially** | Direct precedent: `fit: {cover, contain}` (`studio.py:698`) is this pattern for media. |
| **Position: Inline** | `position: static` | **YES** | The absence-default — every token already works this way (*"absence = center"*, `:754`). |
| **Position: Absolute** | `position: absolute` | **PARTLY** | The boolean is expressible; absolute is only *meaningful* with coordinates → lands on Fixed. D7's sanctioned form: *"a 9-position token"* (`:183`). |
| **Fixed (761px)** | `width: 761px` | **NO** | The value is **continuous**. This — and only this — is what `:187`'s "number-field geometry" names. |

**Three of five are expressible today with zero architectural change.** `Fixed` is the sole genuine conflict — and it conflicts with the token invariant, **not** with R1 and **not** with the chain.

And D7 already sanctions the discretized form (`:176`): *"snap-handle resize… step through token stops (`2-1` → `1-1` → `1-2`), **never free pixels**."*

### The one genuine (C) remainder

`position: absolute` removes an element from flow, so it **exits the `data-arrange` slot contract** (`[data-arrange] .cols { display: flex }`, `studio.py:822`). The block stays attributed and traced; it stops participating in the arrangement's layout.

That is a **layout-contract** cost, not a moat cost. It is the honest price, and it should be named in whatever ships.

---

## 7. Where that leaves the question

**The moat argument is dead** — not unsupported, but *contradicted by D7's own parenthesis* and disproven at the mechanism (`sha256(content)`; `difflib` on lines; `querySelector` by id).

**Three positions are now live**, in ascending cost:

**(1) Block properties as tokens — buy it now, no argument needed.**
`Hug` / `Fill` / `Inline` are one-value tokens with direct precedent (`fit: {cover, contain}`). They need no ADR amendment, no new mechanism, and they satisfy the token invariant. **This is free and it is most of what the inspector shows.**

**(2) Discrete sizing + 9-position placement — inside D7's own valve.**
Snap-stops and positioned-slot arrangements are *pre-authorized text*. Arguing here means arguing with D7's words, not against them. Deck-scoped, this is fully coherent today.

**(3) Continuous geometry (`Fixed: 761px`) — the only real fight.**
The opponent is `test_adr453_property_layer.py:83`, and the argument would have to be: *kernel CSS cannot pre-declare continuous values, therefore the value must ride in the element* (an inline `style` or a CSS custom property). That is R1-safe and chain-safe — §2, §3 settle it — but it **widens the token model from "enumerated values" to "enumerated values + bounded continuous properties."**

The honest case for (3) is **the deck and media**: a fixed 16:9 stage has no responsive obligation (the kernel says so), and an image has intrinsic dimensions the flow can only crop or letterbox. The honest case *against* is that once continuous values are in the model, the discipline that produced tokens-not-pixels has no second line of defence — **"tokens reference intent, never hex" (D1) is the same sentence in a different suit.**

---

## 8. The ruling (operator, 2026-07-15)

> **Bounded-continuous, deck + media only.** Continuous-everywhere is **opted out, not refused** — recorded here as reconsiderable downstream.

### What was decided

Free values are admitted **where there is a frame to be bounded by**:

- **the deck** — a slide's own 16:9 stage (`aspect-ratio: 16/9` + `overflow: hidden`, which the kernel already calls *"a statement about what a slide IS"*, `studio.py:901`)
- **media blocks** — an image's intrinsic ratio (`figure`, `gallery`, `full-bleed`, `picture-with-caption`)

Everything else — `article`, `page`, `document` — keeps **enumerated tokens**. D7's stated reason (*"responsive HTML, not fixed frames"*) is undefeated there, and per-breakpoint editing is already refused (ADR-456 D3). A positioned hero on a page has no answer at 40rem.

**The seam is responsive obligation, not the layout's name.** That is why "website" sits with `document` here and not with `deck`, despite the label intuition that groups them.

### Why this is the future-proof line, not merely the cautious one

The load-bearing point, and the reason this isn't "start small and widen later":

**Bounded-continuous and continuous-everywhere are different features, not the same feature at two scales.** *Bounded* means the frame is what makes the value meaningful — `left: 40px` inside a fixed 16:9 stage is a determinate fact; `left: 40px` on a band that reflows at 40rem is a guess about a viewport. Continuous-everywhere isn't more of the first; it is the **removal of the bound**, applied to layouts that have no frame *because* they reflow.

So the boundary is doing real work, not holding a place. Which makes the decision reversible in both directions:

- if bounded proves **insufficient**, the extension arrives with a receipt instead of a prediction
- if bounded proves **wrong**, the blast radius is the deck and media — the two surfaces that already opted out of responsiveness, so nothing that reflows was ever at risk

### The cost, recorded honestly

**Two sizing models is a real cost.** A member will hit the seam, and *"it depends which layout you're in"* is a worse explanation than one rule. This is paid deliberately: the alternative breaks `article`/`page` at 40rem with per-breakpoint editing already refused. It is a trade, not a free lunch.

### The pressure to widen — how it will actually arrive

**Not** as *"we want free geometry everywhere."* It will arrive as **"why can a deck do this and a page can't?"** — a *consistency* complaint, which feels like a bug report and is in fact the boundary working correctly.

The answer, for whoever fields it: **because a slide has a frame and a page has a viewport.** The deck's geometry is bounded by something real and fixed; the page's would be bounded by a guess about a screen nobody has measured. The consistency is the seam, and the seam is the feature.

If this is not answered in advance, the model gets widened **by attrition** — one reasonable-sounding request at a time, none of them individually wrong.

### What would legitimately re-open continuous-everywhere

Recorded so the reconsideration is evidence-driven rather than fatigue-driven. Any ONE of:

1. **Per-breakpoint editing gets un-refused** (ADR-456 D3 reversed). Free placement plus authored breakpoints is coherent; free placement without them is not. This is the big one — it dissolves the entire objection.
2. **A `page` artifact demonstrably needs placement no arrangement can express**, with the specific instance in hand. Not "Wix does it" — the artifact that failed.
3. **The two-model seam produces more confusion in use than the reflow breakage it prevents.** That is measurable, and it is currently a prediction on both sides.

Absent one of those, widening is drift with a good story.

---

## 9. Sequence

Ascending cost; each step is independently shippable, and the earlier ones may make the later ones unnecessary.

| # | Step | Argument needed |
|---|---|---|
| 1 | **`Hug` / `Fill` / `Inline` as tokens** | **None.** One-value tokens, direct precedent (`fit: {cover, contain}`). Three of the five things in the inspector, free. |
| 2 | **Click / drag / drop / resize as GESTURES** | **None.** ADR-440 D7 already sanctions it: *"Direct manipulation, when it comes, is a **gesture-composer** — never a second write path."* A drag landing as an attributed revision is what the seven ops already do. |
| 3 | **Discrete stops + 9-position** | **None** — D7's pre-authorized text (`:176`, `:183`). Arguing *with* D7's words. |
| 4 | **Bounded-continuous (deck + media)** | **An ADR.** Amends ADR-453 D7 + D1. The token model gains one axis: a property whose *mechanism* is enumerable but whose *value* is not — carried by a CSS custom property (kernel pre-declares `var()`, the element carries the value), the same shape `data-ref` already uses. |

Note steps 1–3 need **no permission from any ADR** and cover most of the observed inspector. Step 4 is the only one that amends canon.

---

## 10. The one-line statement

**The revision chain is `sha256` over a string and `difflib` over lines; `trace` joins by `data-block-id`. Neither can see a coordinate. R1 forbids a model HTML is *compiled from*, and an attribute on the one source file is not that — which is why D7's own parenthesis says positioned slots "doesn't break R1." The moat was never the objection. The objection is that kernel CSS must pre-declare its selectors — and the answer is that a mechanism can be pre-declared while its value rides in the element. So: free values where there is a frame to be bounded by (the deck's 16:9 stage, a media block's ratio); enumerated tokens where there is only a viewport to guess at. A slide has a frame; a page has a viewport. That difference is the whole ruling.**
