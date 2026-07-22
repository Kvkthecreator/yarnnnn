# ADR-481 — The flow chrome rebuild: a blank document is a blank page

- **Status**: **Accepted** (2026-07-22, operator-ratified through the flow-chrome discourse —
  *"a lot of our front end scaffold on document type was predicated on the legacy, Notion-like
  benchmark and block type… now that's simply out of date and goes against our recent
  implementation"* → from-scratch for the flow CHROME, derived from ADR-480's axiom rather
  than inherited from Notion. Q1 answered by the operator (drop arrangements from flow);
  Q2/Q3 delegated and decided here).
- **Date**: 2026-07-22
- **Dimension**: Channel (primary — what the member sees and reaches for on a flowing
  document). No new substrate, no new write path, no schema, no migration.
- **Amends**:
  - **ADR-447** — page arrangements become **`paged`-only**. The registry keeps arrangement
    rows for `deck`/`page`; `document`/`article` serve none. The arrangement grammar is
    unchanged where a page-grain unit actually exists.
  - **ADR-453 D5** — the click-grain ladder loses the **slot** and **page** grains on flow
    (ADR-466 P4 declined to do this on the grounds that a document's `[data-arrange]` band
    was the only re-arrangeable unit; with flow arrangements gone that reason is gone too).
  - **ADR-458** — the hover gutter is **flow chrome no longer**. It was built for a document;
    ADR-480 made a document one continuous surface, and this ADR completes the consequence.
  - **ADR-480 D5** — shipped half. D5 said "on flow, right-click LEADS; the gutter recedes to
    insert". The keyboard simulation was gated; the VISUAL chrome was not. This is the other
    half, and it goes further than "recede": on flow the gutter is **gone**.
- **Preserves**: ADR-480 (the axiom and the whole editing carve) · ADR-443 R1 (the DOM is the
  model) · ADR-443 D2 (no eighth operation — this ADR only REMOVES) · ADR-448 (`data-ref`
  citations and the reference edge, untouched) · ADR-446 (the write contract) · ADR-466 D1/D2
  and **all `paged` work in full** (deck · page · canvas · IMAGES are not touched) · ADR-455
  (the navigator outline — verified already correct, see D4).

---

## 1. The finding: the surface never got rebuilt

ADR-480 moved the editing grain — `contenteditable` to the flow root, blocks demoted from
enclosures to annotations. It did not touch the chrome drawn *around* those blocks, and the
operator's first click pass showed exactly what that leaves: a document whose substrate is
continuous and whose surface is still narrating a block structure nobody is thinking in.

Three defects, all visible in one screenshot of a real document:

1. **A floating gutter (`+` / `⋮⋮`) parked in an empty vertical gap**, attached to nothing.
2. **A dead vertical void** in the middle of the document.
3. **Per-block hover outlines** boxing prose as the pointer travels over text whose click
   means *place the caret*.

The gutter and the outlines are ADR-480 D5 shipped half — I gated the keyboard simulation and
left the visual chrome. The void has a different and more interesting cause (§2).

The deeper reading, which the operator supplied: the flow chrome as a whole is **inherited
from the Notion benchmark**, back when a block genuinely was an enclosure. Every piece of it
answers a question — *insert where? select what? which region is this?* — that a continuous
writing surface does not ask.

## 2. The void, and what the substrate says about arrangements

The `document` scaffold shipped `<section data-arrange="title-lede">` wrapping an empty
`<div data-slot="main">`. A **slot is a paged concept** — a PowerPoint placeholder, a Wix band
region. In a flowing document it renders as a dead gap wearing an `+ Add here` affordance and
a gutter attached to it. **A blank document should be a blank page, not a form with empty
fields.**

Measured against the live substrate before deciding (4 flow artifacts, all of them):

| artifact | body `data-arrange` | body `data-slot` | body blocks |
|---|---|---|---|
| `prd-for-yarnnn/document.html` | 2 | 2 | 19 |
| `flow1-real-name/document.html` | 1 | 1 | 6 |
| `untitled-document/document.html` | 1 | 1 | 4 |
| `test-article/article.html` | 1 | 1 | 4 |

**Every arrangement in every live flow artifact is the scaffold's own** (`title-lede` on
documents, `section` on the article). **Zero were authored by a member.** The population is
4 artifacts. There is no installed base of flow arrangements to protect, because nobody ever
made one — the feature existed and was never used, which is the strongest possible evidence
that a flowing document has no page-grain unit.

The PRD is the clincher. Its FIRST `title-lede` section is **already dissolved** — native
editing (ADR-480) unwrapped it, and what remains is a bare `<p class="lede">` that lost its
`data-block-id`. That bare paragraph, sitting where a section used to be, IS the void in the
screenshot. The substrate was already telling us arrangements don't belong on flow; the
surface hadn't heard.

## 3. Decisions

### D1 — Flow layouts serve NO arrangements; the scaffolds go flat

`document` and `article` scaffolds become flat: `h1`, lede, `h2`, prose. No `data-arrange`,
no `data-slot`. `STUDIO_ARRANGEMENTS` serves no rows for the two flow layouts, so the
New/Re-arrange galleries have nothing to offer and the toolbar's arrangement affordances are
absent by derivation rather than by a flag.

This kills the void, the `+ Add here`, and the slot chrome in one move, because all three key
off structures that no longer exist.

Arrangements remain first-class on `deck` and `page`, where a page-grain unit genuinely is the
composition unit. **If two columns are ever wanted inside a document, that is a BLOCK KIND**
(one registry row, flowing with the text), not a page arrangement — a different and much
smaller thing, and explicitly not built here.

### D2 — On flow, the caret IS the insertion point; the gutter is deleted

The gutter existed to answer *"insert **here**"* — meaningful when blocks were enclosures with
gaps between them, meaningless when the caret is already the location. An affordance that
points at a place is answering a question the medium does not ask.

So on flow the gutter is **deleted, not hidden** (Singular Implementation — the `paged` path
keeps it in full). Insert on flow is:

- **`/` at the caret** — already built (ADR-456 W2), works mid-sentence, needs no anchor;
- **right-click** — already built (ADR-462), carries turn-into and the structural verbs.

Nothing new is built. This is a REMOVAL, which is the honest shape given both entrances
already exist and both are better suited to a continuous surface than chrome in the margin.

**One addition, for cold-start discoverability**: an empty flow document shows a single dim
hint (`Type / for blocks, or just start writing`) that disappears on the first keystroke. The
Notion/Craft convention — one line, no persistent chrome, CSS-only (`:empty`-driven, no
script, never serialized).

### D3 — The hover cue retires on flow; the caret is the cue

`[data-block]:hover` outlines retire on flow layouts. On a continuous writing surface the
I-beam and the caret already say everything the member needs about where a click lands;
boxing prose as the pointer travels re-asserts an enclosure that ADR-480 dissolved.

Slot/page hover chrome retires with the structures it decorated (D1). **Selection chrome for
non-text blocks stays** — a figure, table, chart or gallery is still an object, still
right-clickable, still addressable; clicking one still selects it. What goes is the box that
followed the pointer across *prose*.

### D4 — The navigator is UNCHANGED (verified, not assumed)

`extractOutline` (`StudioNavigator.tsx`) walks `h1, h2` and resolves `data-block-id`. It never
reads `data-arrange` or `data-slot`, so it survives D1 untouched, and a heading outline is
exactly the Word/Docs nav-pane contract.

Recorded as a decision because it was an open question, and because the answer is a good sign
for ADR-480's axiom: **the navigator was already mode-native.** No work.

### D5 — Legacy artifacts: leave the substrate alone, flatten at PROJECTION

Existing flow artifacts carry scaffold arrangements (§2). Three options were weighed:

- a **migration** that rewrites live substrate — rejected: it manufactures revisions on
  member content to fix a chrome problem, and ADR-209 attribution should never carry a write
  nobody made;
- **leave them and stop authoring new ones** — rejected: the 4 live documents keep their void
  forever, which is the exact defect this ADR exists to remove;
- **flatten at projection time** — adopted.

On a `flow` layout the projection pass unwraps `[data-arrange]` sections, lifting their
children in document order into the flow root. **The SOURCE is untouched** — no revision, no
attribution churn — and the member sees a flat document immediately. Because ADR-480's flow
writes serialize what the member edited, a legacy artifact **flattens permanently on its next
edit**, naturally and attributed to the member who actually typed. Migration by use, not by
sweep.

Blocks, ids, citations and `data-ref` pins are all preserved by the lift — it re-parents,
never rewrites. `paged` projections are untouched.

### D6 — What is NOT rebuilt

The block model, the write door, attribution, `derived_from`, the registries' serving
contract, the format bar, the slash palette, the right-click menu, the Design tab, the
navigator, and every `paged` surface. "From scratch" scopes to the **flow chrome** — the
inherited Notion affordances — not to Studio.

## 4. Falsifiers

1. A fresh `document` and `article` scaffold contain no `data-arrange` and no `data-slot`.
2. `GET /studio/vocabulary` serves zero arrangements for `document` and `article`, and its
   existing rows for `deck`/`page` are unchanged.
3. The gutter script is not injected on a flow projection; it is injected on a paged one.
4. A flow projection carries no `[data-block]:hover` outline rule; a paged one does.
5. A legacy artifact whose source has `data-arrange` projects with none, and every
   `data-block-id` and `data-ref` present in the source is still present in the projection.
6. The empty-state hint is CSS-only and never appears in serialized source.
7. Every `paged` gate still passes: bounding box, handles, navigator strip, add-here, slots.

## 5. The honest costs

- **Two-column inside a document is gone** until someone builds it as a block kind. Nobody
  ever used it (§2), so the cost is prospective, not incurred.
- **A legacy artifact renders differently from its source** until its next edit. That is the
  price of refusing to manufacture revisions, and it is bounded: the projection is a view,
  the source is the record, and the two converge on first write.
- **Non-text object selection on flow is now the only selection chrome**, so a member who
  wants to act on a *prose* block reaches for right-click rather than a hover box. That is
  D2's ruling, and it is a real change in muscle memory for anyone who learned the gutter.

## 6. The one-line statement

**A flowing document has no page-grain unit, no slot to fill and no place to point at — so it
gets no arrangements, no gutter and no hover boxes: the caret is the insertion point, `/` and
right-click are the verbs, and a blank document is finally a blank page.**
