# The Studio drift ledger, and the deck question

**2026-07-15 · analysis, not canon.** Written at the operator's request: *"the conflation does seem to be taking place, so let's do the mapping and documentation clearly here so that even if we end up reverting on our decision post implementation and testing, we can continue down the thread accordingly. Thus, I'd suggest taking this opportunity to re-assess the approach from first principles by inferring what it is we were trying to achieve in the first place."*

This decides nothing. It records what the Studio was for, where the implementation left that, and what the deck question actually is — so that whichever way the geometry call goes, the thread is picked up from evidence rather than re-derived from memory.

Two operator asks are **held open** at the end of this doc and are not resolved here.

---

## 1. What the Studio was for

The Studio was **not** created to be an editor. It was created to answer a definitional question about the app format — `docs/analysis/the-authoring-app-claude-design-benchmark-2026-07-10.md:15`:

> "The open definitional question was: *what is an app users USE — an app that authors, not just renders — as a substrate object?*"

The operator accepted it with the trade named — same doc, `:9`:

> "build an **explicit first-party authoring app** — accepted with eyes open that it may be "the not-so-great Notion / not-so-great Claude Design" feature-wise, because the structural advantages (live filesystem references, image-swap-updates-everywhere, attributed provenance, workspace memory) are the bet."

And the *reason*, which is the sharpest sentence in the corpus (`:43`):

> "**The irony that names the bet:** the deck being authored *in* Claude Design argues that each AI giant is a sealed island and "the gap between the islands is the product" — while Claude Design's own artifact is a sealed island. Swap the yarnnn wordmark image tomorrow and every deck that baked it is stale. The authoring app's entire structural thesis is the negation of that: **the artifact is a projection over living substrate references.**"

**The Studio exists to prove an artifact can cite a living commons instead of sealing its assets inside itself.** The deck was the demo vehicle — the operator hit the sealed-island wall while authoring the yarnnn IR deck in Claude Design.

Three things follow that the current implementation does not reflect:

**(a) It was a probe, with the builder deferred behind it.** ADR-440:5 — *"probe first, builder second… The probe's residue is the app format the future S/W-engineer hire (ADR-382-shaped, deferred) builds into."*

**(b) The drift guard was written on day one.** ADR-440 D7 — *"does this feature force a definitional question about the app format, or is it just a better editor? The second kind is refused — **TextEdit, not Word**."*

**(c) The founding empirical finding was that direct manipulation was unnecessary** (`:41`):

> "**The finding that matters most:** Claude Design is *already* a chat-mutation editor. The operator authored an entire IR deck without direct manipulation being the primary tool. This is empirical proof that **chat-driven mutation is a complete authoring modality**… The benchmark does not pressure yarnnn's discipline; it **validates** it."

That finding was inverted 48 hours later (§3) and has never been re-examined.

---

## 2. Why blocks, and why the DOM is the model

ADR-443 R1's rationale (`:29`):

> "**R1 — No shadow content model. The DOM is the model.** … A shadow model would demote HTML to an export format (violating axiom 1), create a drifting second source of truth (violating Singular Implementation), and **orphan the revision chain**. This is the load-bearing correction; everything else follows from it."

All three harms are **substrate** harms, not UX harms. The third is the moat: a JSON block model breaks `trace`.

And blocks were never an editing primitive. They were an **attribution grain** (`:56`):

> "Posture v2 teaches block-grain patching… which aligns `trace` diffs to blocks, **the finest attribution grain in the benchmark class**."

D6's stated reason for their early arrival: *"because a gesture wants a block to aim at, blocks land before tweaks."* **Blocks were a provenance primitive later repurposed as an editing primitive.** That repurposing is upstream of the conflation this doc maps.

---

## 3. The drift ledger

| Original intent | Where it stands (2026-07-15) | The drift |
|---|---|---|
| A **probe** whose residue is the app format; the engineer hire builds into it (ADR-440:5) | 19 ADRs of editor depth; the hire still deferred (ADR-457 §10) | **The probe became the product.** The drift guard has refused nothing since ADR-446. |
| **"TextEdit, not Word"** (ADR-440 D7 — never withdrawn) | Inline format bar, slash-insert, turn-into, hover gutter, Design tab, arrangement gallery, theme panel | This is Word. The line was crossed by the operator's own 07-12 widening — but **the guard was never rewritten, and still says TextEdit.** |
| **Chat-driven mutation is a complete authoring modality** — empirically proven (benchmark §1) | Chat is the *judgment* path; mechanical is the default (ADR-444/446) | The founding finding was inverted within 48 hours. Never re-examined. |
| The bet is **structural** — living references, provenance under every slide (ADR-440:5) | Waves 1–3 are all composition chrome. **Publish / pins-at-publish is still deferred** (ADR-457 §10.5, gated behind ADR-427 Ph2–3) | **The moat feature is deferred; the parity features shipped.** The `data-ref-rev` pin — the whole categorical difference from Claude Design — has never been exercised at the boundary it was designed for. This is the sharpest drift in the corpus. |
| **AI derives, member refines** (ADR-452, ADR-457 D2) | Free-placement pressure is being weighed | The intended member *refines a derived artifact*. Free placement optimizes the path canon made secondary. |
| One object, format-agnostic (ADR-443) | `paged` vs `flow` mode seam added 2026-07-15; deck exemptions carved | **Two objects wearing one grammar** (§4). |

### The 07-12 widening, in the operator's words

`ADR-446:7` — the pivot that inverted (c):

> "The operator's verdict: the seed-the-chat model is **"only partially right… we need to think closer to a webpage editor like Wix — select and edit ON SCREEN, IN REAL TIME."**"

But note the **scope the operator actually drew** (`the-studio-direct-edit-projection-to-source-2026-07-12.md:21`):

> "**The critical distinction the operator drew is modality, not architecture**: the member should *type in the document*, not describe the change to a chat that types for them. **Chat stays — for judgment work**… **Direct manipulation becomes the default for *direct* changes (fix a word, correct a heading).**"

**Typo-grain.** "Fix a word, correct a heading." The widening authorized direct *text* editing. Everything from the format bar to the Design tab has been built on a mandate that named two examples, both of them typos.

---

## 4. The conflation, measured

The four layouts are ~5% distinct. Measured against `api/services/studio.py`:

| | document | deck | article | page |
|---|---|---|---|---|
| **mode** | `flow` | `paged` | `flow` | `paged` |
| **own skin rules** | 4 | 9 | 6 | 6 |
| **inherited** | 24 shared + ~90 kernel | same | same | same |
| **only real novelty** | `max-width:46rem` | `aspect-ratio:16/9`, `.cols` | `max-width:42rem`, `.byline` | full-width bands |

`document` and `article` differ by **`46rem` vs `42rem`** and three header selectors. The `page` layout — the Wix answer — inherits Georgia serif and `#fdfcfa` paper and overrides neither, so a "landing page" ships looking like a document.

**The honest seam is `mode`, not the four labels.**

### The axiom that was quietly narrowed

ADR-443's format-agnostic axiom: *"documents, decks, articles, pages are different renderings of the same structured content."*

`STUDIO_LAYOUT_MODES` (added 2026-07-15) says otherwise — `STUDIO.md:29`:

> "**`paged`** (deck, page): the CONTAINER is the unit… **`flow`** (document, article): BLOCKS are the unit and they flow."

**Different units is not different renderings.** This is the system discovering, 19 ADRs in, that decks and documents are not one object composed differently. It was admitted at the chrome layer while the axiom stayed on the books.

And ADR-456 D7 narrowed the axiom rather than withdrawing it:

> "The "format-agnostic" axiom… **the axiom survives as block portability**… what D7.5 deleted was the *mechanical* type toggle. **Type change is a judgment act, not a view switch.**"

That is not format-agnosticism. That is format conversion with extra steps. **The axiom was reduced to a slogan while the machinery it justified — one object, one grammar, one block model — stayed.**

**Was the deck ever meant to be a document?** No — it was meant to be a *rendering* of one, which is a stronger claim, and that claim has been eroding since ADR-447 without ever being formally withdrawn.

---

## 5. The two bugs (fixed 2026-07-15, commit 8bc5384)

Both were visible in one screenshot of a two-column slide, and both are evidence for §4.

**The columns stacked.** The kernel carved out `[data-arrange]:not(.slide) .cols`, reasoning that decks keep their own `.slide .cols`. True of the deck skin as of ADR-444; false of every deck created before it, because **the layout skin is baked once at `build_skeleton` and never versioned or retrofitted** (only `style[data-kernel]` is). Live receipt: of three decks in the workspace, `yarrnnnn-decl` has no `.slide .cols` in its baked skin.

`artifactOps.ts:359` predicted this class in its own comment — *"becomes a real defect the first time a version CHANGES or REMOVES a rule an old artifact depends on, and the failure is silent."* The carve-out was that removal.

**The invariant, now gated:** *a kernel rule may not be predicated on the presence of a skin rule.* The skin is frozen at creation; the kernel is not.

**Identical thumbnails.** `ArrangementThumb` derived its wireframe from three signals that are identical for `two-column` and `comparison`. Fixed to read each column's own heading.

**Why they belong in this ledger:** both are inheritance seams. The `.cols` bug exists because a deck's columns are the *document's* column mechanism wearing a slide's clothes; the thumbnail bug exists because a wireframe derived from flow-slots can't see what makes two slide arrangements different. Neither would exist if the deck's composition model were its own.

---

## 6. The deck question

### What was already decided, twice, by the operator

**ADR-453:9** — the operator reached for free geometry and withdrew it:

> "The operator, **from the Figma inspector and then self-corrected to the Wix/Webflow family**, named the missing in-document layer."

**ADR-453 D1:**

> "Studio adopts the **Wix/Webflow family, not Figma's**: the member composes *within* a layout system… **they do not author free geometry.**"

**ADR-456 §1** is this exact ask, in these words:

> "**deck + article** should stay html-native but move toward **Squarespace/Wix builder capability**"

Answered with flow **bands** (`page`), not a canvas. The reasoning that matters (ADR-456:60, on the markdown ruling but structurally identical): a second model is *"a shadow model in a costume."* Free geometry needs continuous x/y/w/h/z — a coordinate model — which is a JSON tree by another name, which orphans the revision chain, which is the moat.

**The canvas was refused by the moat, not by taste.**

### The pre-authorized escape valve

ADR-453 D7 — *"Refusals (named so they never re-litigate)"* — already names the exit:

> "**free X/Y + rotation for flow content** (… **if true free-placement demand ever materializes it is a new *arrangement kind* with positioned slots — an escape valve that doesn't break R1**) · … **number-field geometry (Studio edits intent discretely because responsive HTML, not fixed frames)**"

Note the scope: *"for flow content."* Not categorical. And the valve delivers **discrete** placement (a 9-position token; snap handles stepping `2-1` → `1-1` → `1-2`), not Figma.

### The one argument that does not apply to the deck

The load-bearing objection is **not** R1 — absolute positioning is perfectly good DOM. It is **responsiveness**: free placement + ADR-456 D3's refusal of per-breakpoint editing = artifacts that break on mobile.

That argument is sound for `article` and `page`. **It does not apply to the deck.** The deck is already a fixed frame — `aspect-ratio: 16/9`, `overflow: hidden`, and the kernel CSS *explicitly exempts it* from responsive stacking (retained and re-annotated in 8bc5384). **A slide has no responsive obligation.**

So: **the deck is the only layout where a canvas is coherent under existing canon — and it is coherent precisely because it opted out of being a webpage.**

The corollary, which the "deck + article + website should all be Wix-like" framing hides: **the deck wants Figma (fixed stage, direct manipulation); article and page want Wix (bands, reflow). Those are different products.** Conflating them is what produced the flow-committed deck.

### Held open — the operator's two live objections (2026-07-15)

Neither is resolved here. Both are recorded so the thread survives.

**(i) "I want to question the twice calls once more."** The refusals at ADR-453 D1/D7 were made against **Figma's free x/y**. That may be the wrong strawman. Claude Design's inspector — which the operator cites as having *"updated towards re-sizing on screen, real time"* — shows `Width 761px / Height 246px`, `Hug | Fixed | Fill`, `Position: Inline | Absolute`. **That is constrained geometry with an explicit inline/absolute switch, not free placement.** `Hug/Fixed/Fill` is CSS-native (it *is* `fit-content` / fixed / `1fr`) and arguably expressible as tokens with values — which would not require a coordinate model and would not orphan the revision chain. **Whether ADR-453 D7's "never raw geometry" forbids Hug/Fixed/Fill, or only forbids continuous x/y, is undecided and is the actual question.**

**(ii) Image/media screens must be accommodated.** Media blocks (`figure`, `gallery`, `chart`, `full-bleed`, `picture-with-caption`) are the strongest case for resize — an image has intrinsic dimensions the flow can only crop or letterbox. ADR-453 D7 already anticipates *"media-corner handles that step through token stops"*. Any resize decision lands here first.

---

## 7. If we go forward — the shape

Not a recommendation to build. The shape a proposal would have to take to be coherent with canon:

1. **Placement enters as an arrangement kind with positioned slots** (ADR-453 D7's own valve), not as a third `STUDIO_LAYOUT_MODE`. Adding `mode: "canvas"` is the drift-flagged move; `data-arrange="free"` with `slots: [{name, role: "free"}]` is pre-authorized.
2. **Deck-only.** `article`/`page` keep bands — the responsive argument stands there and is undefeated.
3. **The geometry question is fought explicitly or not at all.** Discrete stops (D7's offer) need no new argument. Hug/Fixed/Fill needs ADR-453 D7 amended with the distinction in §6(i). Continuous x/y needs the moat argument answered, and no answer is currently on the table.
4. **ADR-443 D2 closes the op set at seven** — *"any proposal introducing an eighth operation is presumptively drift and must argue against this decision."* Placement is arguably TRANSFORM; that must be argued, not assumed.
5. **The prior question the ledger raises**: before adding the largest "just a better editor" feature yet, the drift guard says to ship the thing the Studio was *for* — publish / pins-at-publish, the proof that an artifact cites a living commons. It is deferred behind ADR-427 Ph2–3. **A canvas would be parity work; the pin is the bet.**

---

## 8. The one-line statement

**The Studio was built to prove an artifact can cite a living commons; it has become a competent editor that has not yet shipped the citation's payoff. The deck was never meant to be a document — it was meant to be a rendering of one, and that claim has been eroding, unwithdrawn, since ADR-447. The deck is the one layout where a canvas is coherent, because it is the one that already opted out of being a webpage. Whether "no raw geometry" forbids Hug/Fixed/Fill or only free x/y is the live question, and it is open.**
