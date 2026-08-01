# ADR-511 — The conventional substrate: selection derives from structure, not from annotation

- **Status**: **Accepted; Phases 1–2 Implemented** (2026-08-01, operator-directed — *"a hard
  streamlining towards the claude design benchmark … i'd like to delegate the details to
  you in full"* — closing the 2026-08-01 click-grain audit, five rounds, receipts in the
  audit trail below. Phase 2 same day, with the D8 amendment discovered during it.)
- **Date**: 2026-08-01
- **Dimension**: Studio interaction model + artifact format. No schema change, no
  migration, no new primitive — every new affordance is an existing op reached through a
  new grain (ADR-462 D1 holds).
- **Amends / supersedes**:
  - **ADR-443 D4 (amended, one sentence)** — *"Layout flow containers … are structure,
    not vocabulary blocks"* becomes **"structure is addressable, never a vocabulary
    block."** Containers stay out of the block vocabulary; they stop being invisible to
    selection. R1 (*the DOM is the model*) is not amended — it is finally honored in
    full: half the model was un-pointable.
  - **ADR-453 D5 (superseded)** — "the arrangement registry is the canvas's interaction
    contract" loses its premise. The **DOM tree** is the interaction contract; the
    registry demotes to a starter-template catalog (D2 below). The click-grain ladder
    D5 defined (block → slot → page) is replaced by the structural grain (D3 below).
  - **ADR-462 D3 refusal row (clarified, still refused)** — "Group / Frame selection —
    No — a container in a shadow tree" refused a **synthetic editor-side group object**
    (the Figma model). That refusal stands. Selecting a **real DOM container** was never
    the thing refused; this ADR makes them selectable. Persistent grouping, if ever
    requested, is wrap-in-a-real-`<div>` — a revision, R1-compliant, not a shadow layer.
  - **ADR-480 D3 (scoped)** — "ids preserved through editing, not asserted before it"
    was flow-editing reasoning. It holds for the editing session; it does not forbid
    identity minting at the artifact **boundary** (open/import/write — D5 below), which
    is where the annotation-gated-editability failure class is closed.
  - **ADR-466 P10** stands (first click selects on staged frames); this ADR extends the
    same object grammar upward to containers.

---

## Context — the five-round audit (2026-08-01)

1. **The ladder has no container rung.** block → slot → page (ADR-453 D5,
   `projection.ts` click handler). `div.cols` / `div.col` carry no `data-*`: invisible
   to hover, click, menus, Design tab. Shipped arrangement templates contain **bare
   `<p>` elements nobody can select or edit** (`studio.py` `two-column`,
   `picture-with-caption`) — on paged, promotion never runs (`normalizeBlockIds` is
   flow-only, edit-triggered, one level deep).
2. **Visible-but-inert clash.** The frame reference (`.yarnnn-frame`) draws and *names*
   the slot every time a block inside it is selected, while the inert pass makes that
   same slot unclickable on single-slot pages. The chrome asserts a container the click
   model denies.
3. **Overlap is unmediated.** Drag → `data-x`/`data-y` → `position:absolute` (kernel
   rule) → block exits flow; siblings reflow under it; no collision, no guides; the
   return-to-flow escape hatch is buried in Design-tab block scope.
4. **The benchmark (Claude Design) is conventional HTML/CSS**, not an invention:
   breadcrumb = real ancestor chain; Hug/Fixed/Fill = `fit-content`/px/`stretch`;
   Inline/Absolute = the `position` property made visible and reversible; Contents
   layout = the parent's own CSS aligning children. Its one structural weakness is the
   edit loop (*"edit the preview; we will describe changes to Claude to apply on
   exit"*) — a shadow-model preview + lossy NL round-trip. Ours writes attributed
   revisions; we match the inspector, never the loop.
5. **Annotation-gated editability is the failure class, not a bug.** A model where
   editability requires proprietary annotations makes all unannotated HTML (imports,
   agent output, reference files) second-class **by construction**. And every
   proprietary grammar concept is prompt-tax under ADR-306's ablation ratchets — the
   lane speaks HTML/CSS from pretraining; the conventional substrate is the co-author's
   native tongue.

## Decisions

### D1 — The annotation set: two content annotations + one grammar annotation

The artifact format is **conventional HTML/CSS** plus:

| Annotation | Carries | Why nothing conventional can express it |
|---|---|---|
| `data-block-id` | **Identity** — on vocabulary blocks AND structural containers | The join key for trace, History, Copy-link, citations, and every op's address. The two rows no reference product can ship (ADR-462). |
| `data-ref` | **Provenance** — the citation island boundary | Owned vs. borrowed content (ADR-443 R3, unchanged). |
| `data-block="<kind>"` | **Grammar** — vocabulary blocks only, never containers | The palette / turn-into / token-applicability register. Kinds shadow semantic HTML wherever HTML has the element; the attribute earns its place only where HTML doesn't (callout, metrics, chart). |

Everything else is scaffolding and dissolves on the D6 schedule: `data-arrange` and
`data-slot` cease to be **interaction** concepts now (Phase 1), and their remaining
functional readers are re-cut structurally in Phase 2 — after which the attributes
survive only as **inert names** (see D8: skins style them, labels read them, nothing
gates on them). `data-slot-inert` is deleted outright — no phase, no reader survives.

`data-*` is the HTML-sanctioned extension mechanism: the annotations export cleanly,
every platform ignores them gracefully, and an importer that doesn't understand them
loses nothing. This is the portability posture ADR-510 ships at the workspace level,
applied to the artifact format.

### D2 — Arrangements demote to starter templates

`STUDIO_ARRANGEMENTS` stops being a runtime ontology and becomes what such things are in
every conventional tool: a **catalog of starter markup**. Applying one is an authored
transformation (ADR-443 R2, unchanged). What changes: the result is **live, editable
structure** — selectable containers whose layout is CSS the member (and the lane) can
edit — not a frozen master only replaceable wholesale. "Re-arrange" survives as the
apply-a-template verb; it stops being the only layout verb.

### D3 — The structural grain: the DOM tree is the selection model

The click ladder is replaced by the **structural grain**:

- **Click** selects the innermost *addressable* element under the hit — a vocabulary
  block when one encloses it (unchanged: text-first, click-to-caret on flow, ADR-466
  P10 on staged), else the nearest **structural container** (a column, a columns row, a
  slot-div — any element the D5 normalization stamped with identity), else the page.
- **Esc walks up the real ancestor chain**: editing → block → container → … → page →
  clear. This generalizes the existing Esc (caret → block-select) into the conventional
  hierarchy walk (Figma/Framer). There is no drill-*down* gesture to learn; down is
  just clicking the thing.
- **The hover cue and the selection cue light whatever the click would select** — the
  cue must agree with the grain (the 2026-07-21 rule, kept).
- **Operator words are a render-time label map, not a file concept.** The file says
  `<section>`/`<div>`/`<h2>`; the chrome says *slide / columns / column / heading* —
  `frameLabel()` generalized into one exported map, used by the canvas chrome, the
  Design tab, the navigator, and the menus. The chrome never says "div" (ADR-443 D3
  holds; Claude Design's `group (div)` breadcrumb is the counterexample we refuse).
- **Selection bottoms out at the block grammar.** Text nodes, `<br>`, inline spans are
  never selection subjects — the attribution floor (D1) is the selection floor. Claude
  Design's `group (br)` tree row is what an unbounded tree looks like; ours is bounded
  by what can carry identity.

### D4 — Layout is editable CSS; positioned state is legible

- **Container scope** (Design tab, new): a selected container exposes its layout as
  plain CSS through the existing bounded-token mechanism — padding, gap, alignment,
  direction — written as inline styles by an id-addressed op (`setContainerLayout`).
  Served specs + the two-clamp rule (ADR-461/485) apply unchanged. **No raw CSS pane**:
  the property surface is bounded even though the substrate is conventional.
- **Position: Inline / Absolute** becomes an explicit, visible, reversible control in
  block scope. The existing machinery is the implementation (`setPosition`,
  `handleReturnToFlow` — the escape hatch stops being buried). The canvas marks an
  out-of-flow block (a corner glyph on its selection box) so absolute is a *deliberate,
  visible exception*, flow the default — the benchmark's one deep lesson.
- Snap/alignment guides against siblings and the frame during drag are **Phase 3**
  (declared, not shipped here).

### D5 — Identity at the boundary: unannotated HTML becomes native

`normalizeBlockIds` generalizes to **`normalizeStructure`** and runs at the write seam
for **every** mode (flow AND paged), at **every depth** (not `region.children`):

- Bare text elements (`<p>`, `<div>` with text, headings, lists, tables, figures,
  blockquotes) are promoted into the block grammar with tag-derived kinds.
- **Structural containers** (elements between page and block that hold blocks) are
  stamped with `data-block-id` — identity without vocabulary (D1). This is what makes
  them addressable by the existing ops: `deleteBlock` / `duplicateBlock` / `moveBlock` /
  `setMeasure` already resolve by id and now work on containers with **zero op-side
  change**.
- Citation islands (`data-ref`) are never touched (ADR-480 D3's preservation discipline
  holds *within* the boundary).
- Existing ids are preserved; duplicates re-minted first-wins (unchanged).

An artifact opened with unannotated content gets one normalization pass folded into its
**first write** (migration-by-use, the ADR-427/480 pattern — no fleet migration, no
write-on-open).

### D6 — The dissolution schedule (Singular Implementation, phased honestly)

- **Phase 1 (this ADR ships it)**: the structural grain (D3) · Esc-walk ·
  `data-slot-inert` pass **deleted** · `slotIsRegion` **deleted** (the Design tab's
  slot scope collapses into container scope) · `normalizeStructure` (D5) ·
  container scope + `setContainerLayout` (D4) · Inline/Absolute legibility (D4) ·
  the navigator grows the structure tree (pages → containers → blocks, label-mapped,
  seeded from the existing slides+headings navigator) · the label map exported as the
  one vocabulary seam.
- **Phase 2 (Implemented 2026-08-01, as amended by D8)**: every remaining
  **interaction/op reader** of `data-arrange`/`data-slot` re-cut structurally — the ONE
  page selector (`STRUCTURAL_PAGE_SEL` in `structureLabels.ts`: a page is a deck slide
  or a top-level body/main/article section, imported or inlined at all five consumer
  sites so indices always agree) · insert targeting (a selected CONTAINER anchor is
  appended INTO; unanchored inserts land in the page's first LEAF container —
  `firstLeafContainer`, position not name) · `insertBlockInSlot` → `insertIntoContainer`
  (id-addressed, same address as every other op; the add-here runtime carries the
  container's identity) · the empty-region "+ Add" placeholder targets any empty leaf
  container structurally (imported HTML included) · the multicol fallback counts
  `.col` children · `measurableFrame` resolves the nearest identity-carrying container.
  Attribute REMOVAL did not ship — see D8.
- **Phase 3 (declared)**: drag snap/alignment guides; Hug/Fixed/Fill sizing idioms on
  containers.

Phase boundaries exist because ~30 gate files pin the current model's source text; each
phase lands with its gates re-cut in the same commit, never with a silently weakened
gate (the counting-gate lesson).

### D7 — What is explicitly refused

- **No shadow group object** (ADR-462's refusal, clarified and kept).
- **No raw CSS pane** — bounded property surface over a conventional substrate.
- **No preview-then-describe edit loop** — the benchmark's seam is its weakness; ours
  writes attributed revisions at block grain.
- **No DOM-inspector depth** — selection floor = attribution floor (D3).
- **No new primitive, no eighth operation** — every affordance here is POINT or
  TRANSFORM parameterized by a new grain.

### D8 — Legacy names are INERT BYTES, not stripped (the Phase-2 amendment)

D6's original Phase-2 clause ("attributes removed from templates and strippable at the
write seam") is **amended against evidence found during implementation**:

- **The web skin styles `section[data-arrange]`** (padding, per-arrangement band rules —
  `studio.py`), and every existing artifact carries a **baked copy** of that skin.
  Stripping the attribute breaks rendering on live artifacts; re-cutting skins forks
  styling between old markup + old skin and new markup + new skin.
- **The flow flatten pass keys on `[data-arrange]`** to unwrap legacy flow scaffolds. A
  seam-side strip that runs before projection would disarm the pass and resurrect the
  dead-void rendering it exists to fix.
- Region NAMES (`data-slot="side"`) feed the operator-word label map and the registry
  role lookup — deleting them would fork the naming carrier for zero interaction gain.

The ruling: **singular LOGIC, tolerant DATA.** After Phase 2 the attributes have zero
interaction/op readers — the readers that remain are (a) CSS in skins, (b) the label
map's name source, (c) registry template-application metadata (`applyArrangement`
mapping content by declared role — template logic, the same class as the galleries),
and (d) the legacy flow-flatten (self-retiring by use). `data-*` naming is conventional
HTML; an attribute nothing gates on is a name, not a model. D1's annotation thesis is
restated precisely: two annotations carry SEMANTICS nothing conventional can express
(identity, provenance); `data-block` carries grammar; everything else is inert naming.

## Consequences

- Imported/agent-authored/reference HTML is **editable by definition** — the promotion
  prerequisite disappears as a class. The bare-`<p>` defects in shipped templates
  become selectable blocks on first write.
- The visible-but-inert clash dissolves: what the frame chrome names, the member can
  select.
- The prompt layer sheds proprietary-grammar tax on the D6 schedule (slot/arrangement
  posture prose retires with Phase 2), per ADR-306's ablation discipline.
- `docs/design/STUDIO.md` carries the interaction-contract rewrite; ADR-LEDGER gains
  this entry; the three amended/superseded ADRs carry banners.
