# ADR-519 — The object hierarchy is four grains, and the pane speaks one grammar

> **Amended by [ADR-544](ADR-544-the-containment-law-slide-layout-area-block.md)
> (2026-08-10) for the paged media.** D1's middle rung — "Container" — was one word for
> two substrate concepts (`.cols`/`.col`, declared by the skin, and `data-slot`, declared
> by the arrangement), which is why one paragraph's breadcrumb read `slide 2 › columns ›
> main`: two structural rungs, neither a chosen word. ADR-544 collapses them into **Area**
> (a region typed by role) and renames the chain **Slide → Layout → Area → Block**, adding
> the invariant this ADR left implicit: **every block lives in exactly one Area**. Three of
> the eleven deck arrangements had a heading inside a region and six had it bare on the
> slide — the hierarchy was unstateable, not merely unnamed. **D2 is superseded in the deck
> medium**: under containment there is no layout-less container on a slide, so "Group ≡ a
> container with no layout declared" has nothing left to denote there. The pane spine (D3)
> and the set-is-state rule (D4.1) are unchanged.
>
> **Extended by [ADR-525](ADR-525-the-selection-carries-its-tier.md) (2026-08-06).** D1's
> closing scope sentence — *"document is Docs' housing (ADR-518) and outside this ADR"* —
> was true in canon and false in code: `StudioDesignTab` never received the app identity
> and composed block scope with no medium term, so a Docs paragraph rendered this ADR's
> pane spine in full (verb row, Layout, Width Hug|Fill, Align). ADR-525 splits the pane's
> block column by TIER so the exclusion this ADR declared is the one the surface obeys.
> The four grains and the spine ordering are unchanged.

- **Status**: **Accepted** (2026-08-05, operator-ratified — *"let's proceed per the
  assessment and recommended next steps direction on containers as stated"*). Prepared
  from the operator's directive: *"the hierarchy of html to slides needs a similar
  philosophy to Figma's sections, frames, groups … thus potentially revamp the
  properties work in full aligned to this."* Benchmark screenshots: Figma's Section /
  Frame / Group property panels. The §5 open questions resolved per recommendation:
  page identity YES (lands with Phase B, where addressing uniformity pays for it) ·
  ⌘-click deep select YES (Phase B) · Direction row CONTAINERS ONLY (Phase C).
- **Date**: 2026-08-05
- **Dimension**: Studio interaction model + Design tab. No schema change, no new
  primitive, no substrate-format change — the hierarchy this ADR names is the one
  ADR-511/516 already shipped; the work is completing it and making the pane speak it.
- **Amends / relates**:
  - **ADR-511** (extended, not amended) — D3's structural grain is *canonized as the
    hierarchy*; this ADR names the levels and closes the gaps D3 left implicit
    (multi-select wiring, container reachability, per-child alignment).
  - **ADR-516** (extended) — D1's "the page is a container" generalizes to **every grain
    has layout authority over its children through the one mechanism**; the allowlist
    grows direction and align-self rows.
  - **ADR-462 D3 / ADR-511 D7** (upheld) — still no shadow group object. This ADR
    *dissolves* the group question rather than adding the concept (D2 below).
  - **STUDIO.md** — the interaction matrix gains the hierarchy statement and the pane
    spine; the Phase-3 declared cells are absorbed into this ADR's phases.

---

## 1. Context — the benchmark, read precisely

Figma's inspector has one deep property worth importing and several we must refuse.

**The property worth importing is the *panel grammar*, not the node types.** Across
Section, Frame, and Group, Figma's right panel is one ordered spine — **Position
(with an alignment row) → Layout (flow, dimensions, clip) → Appearance → Fill →
Stroke → Effects → Export** — and each node type differs only in *which rows appear*,
never in ordering, vocabulary, or mechanism. A Section shows no rotation and no flow; a
Frame shows both; a Group shows position but empty paint sections. The user learns the
panel once.

**The node types themselves map onto what we already have** — because after ADR-511 the
substrate is conventional HTML/CSS, and Figma's model is (as the ADR-511 audit found of
Claude Design) plain CSS wearing chrome:

| Figma | yarnnn (shipped) | DOM anchor | Layout authority |
|---|---|---|---|
| Page (canvas) | **Artifact root** | `<html>` | document tokens (font/measure) |
| Frame as artboard / Section | **Page** — slide (deck) · band (web) | `STRUCTURAL_PAGE_SEL` | padding + vertical-align presets (ADR-516 D1/D3) |
| Frame, nested (auto-layout) | **Structural container** | `div[data-block-id]:not([data-block])` | padding/gap/align/justify/width (ADR-511 D4 + ADR-516 D4) |
| Group | **a container with no layout declared** — see D2 | same anchor | none until declared |
| Object (text/shape) | **Block** | `[data-block]` + id | tokens + measures |

The hierarchy the operator asked for — *slides → the master layout arrangement → groups
→ blocks* — is therefore already real, with one correction of terms: **"the master
layout arrangement" is not a node**. It is the page's own layout authority (its flex
properties + its container tree). Arrangements are starter templates that *produce* that
tree (ADR-511 D2); after application the tree is live structure, owned by the same
mechanism as everything else. There is no fourth persistent layer.

## 2. What the benchmark exposes as genuinely missing

The audit of HEAD (2026-08-05) against the benchmark:

1. **The pane has no spine.** Four scopes exist (document/page/container/block —
   `StudioDesignTab.tsx`) but each composes its rows ad-hoc: page leads with verbs,
   container with a media picker, block with typography; Layout sits at a different
   position in each; block scope has a Size section page scope lacks; container scope
   has no verb row at all (right-click only). The member re-learns the panel per scope —
   the exact failure Figma's spine avoids.
2. **The alignment row does not exist.** Figma's top Position row (align left/center/
   right · top/middle/bottom against the parent) has no equivalent at any grain. Our
   alignment verbs are all *parent-side* (`align-items`/`justify-content` move every
   child); there is no way to align *one* child within its parent (`align-self`), and no
   align/distribute over a multi-selection.
3. **Multi-selection is orphaned at the React boundary.** The canvas group is real
   (shift/⌘-click, group move, group resize, `yarnnn-geometry-many`) but
   `StudioCanvas.onGroup` is never passed by `StudioSurface` — the Design tab,
   breadcrumb, and navigator all see one selection. Figma's panel-over-multi-selection
   (the align/distribute home) is structurally impossible today.
4. **A covered container is unreachable by click.** The ladder's container/page rung
   lives in the pointable-miss branch (`projection.ts` click handler): only a click on
   the container's own padding selects it. Canon says "down is clicking the thing"
   (ADR-511 D3) — but a container fully tiled by children has no clickable "thing."
   Breadcrumb, Esc-walk, and the navigator tree are the only routes.
5. **Direction is implicit.** A container's flex-direction is auto-set (column, unless
   its children carry `.col`). The horizontal idiom exists only as the `.cols/.col`
   template class — a member cannot *turn* a container horizontal. Figma's Flow row
   (vertical/horizontal/wrap/grid) is the conventional control.
6. **Geometry is drag-only.** W/H read back numerically but X/Y do not; no numeric
   entry anywhere; "Positioned" is enterable only by drag. (Deliberately flow-first —
   ADR-511 D4 — but readback-without-entry is a half-affordance.)
7. Already declared, still owed (STUDIO.md Phase 3): snap/alignment guides, container
   drag-reorder, keyboard nudge rows.

## 3. Decisions

### D1 — The hierarchy is canon: four addressable grains, one law

**Artifact root → Page → Container (nestable) → Block.** Every grain is a real DOM
element (R1); every grain is addressable (identity or page-anchor); every grain with
children has **layout authority over them through the one mechanism**
(`setContainerLayout`, bounded presets, inline CSS); every grain's chrome, label, and
pane scope derive from the same anchors. Per medium: deck carries the full contract
(the only coordinate space); web carries it minus geometry (band-first, ADR-505 D3);
document is Docs' housing (ADR-518) and outside this ADR.

Normative restatement (one sentence): **structure owns layout downward; position is the
stage's marked exception; meaning stays themed** (ADR-516 D6 unchanged).

### D2 — "Group" is dissolved, not added: a group IS a layout-less container

Figma's Group — a transparent wrapper with position but no paint and no flow — is, in a
conventional substrate, *exactly* a `<div>` with identity and no declared layout. We
already have both halves:

- **Transient grouping** = the multi-selection (canvas group), now surfaced (D4).
- **Persistent grouping** = **Group as a verb**: wrap the multi-selection in a real
  `<div data-block-id>` — one authored revision, R1-compliant, the shape ADR-462/511
  always pointed to. **Ungroup** = unwrap (children splice up, wrapper deleted). Both
  are existing-op compositions (insert + move), not new primitives (ADR-462 D1).

No group node type, no shadow object, no special chrome: a wrapped group *is* a
container and immediately inherits selection, label ("group" from the label map), the
pane's container scope, and layout authority — Figma's "Group vs Frame" distinction
collapses into "container without vs with declared layout," which is the honest CSS
truth Figma itself hides.

**D2.1 — Re-arranging a slide dissolves its groups** (amended 2026-08-06, from the
Phase B/C audit; operator-decided). D2 was ratified without seeing a refusal already
written at `artifactOps.ts:719` (2026-07-24), which argued that no persisted group may
exist at all. The audit tested both of its claims:

- Its `carriedBlocksOf` objection — that a wrapper would hide its own children from
  every content-redistributing sweep — is **false**. That filter tests `data-block`; a
  group wrapper carries `data-block-id` alone, so it never trips it and the children
  stay visible. Verified by execution, not by reading.
- Its `applyArrangement` objection is **true**, and is resolved here rather than left
  implicit: `applyArrangement` ends in `page.replaceWith(el)`, so the old page is
  discarded wholesale and blocks survive only because they were re-parented into the
  new arrangement first. A group wrapper is destroyed with the page that held it.

The rule is therefore: **a group is durable until the arrangement is re-declared, and
re-arranging dissolves it.** This costs no op-layer change and no cleanup pass — a
wrapper can never be orphaned, because nothing of the old page survives. It is the same
yielding AUTHORING.md already names: a slot is DECLARED by the arrangement, a group is
AUTHORED ad hoc, and the ad-hoc structure yields when the declaration changes. **The
surface owes the member that sentence before the re-arrange** — a group vanishing
silently is the defect this decision must not produce. ✅ **The debt is paid (2026-08-06)**:
`countGroupsOnPage` feeds the arrangement galleries, which say *"ungroups 2 groups"* on
the thumb — the same home, and the same "say it where the choice is made" principle, as
ADR-466 D5's carried-content note. Where both apply the dissolve is named FIRST: content
lands on a new page, but a group is simply *gone*, so the less recoverable consequence
leads. A group is counted as D2 defines it — a container with identity, **no declared
layout**, actually holding blocks; a `data-slot` region is the arrangement's own
structure, not something the member authored.
*Group-survives-as-a-carried-unit*
was considered and refused: it would change the arrangement's carry semantics and open
slot-fitting for a multi-block wrapper, for a durability no member has asked for.

### D3 — The pane spine: one ordered grammar at every scope

The Design tab recomposes onto one spine; scopes differ only by which sections render:

| Section | document | page | container | block | mechanism |
|---|---|---|---|---|---|
| **Identity** — label/breadcrumb tail + verb row (dup/move/delete) | name + file verbs | ✅ (exists) | ✅ **NEW: verb row parity** (ops exist, today right-click-only) | ✅ (has ops via menu; row added) | existing ops |
| **Position** — In flow \| Positioned · X/Y readback+entry · align-self row | — | — | — | ✅ deck-staged only | measures + geometry op, two-clamp |
| **Layout** — direction · padding · gap · align · justify · width · (page: valign) | — | ✅ | ✅ | size Hug/Fill token | one op (ADR-516), allowlist grown (D5) |
| **Style** — typography ramp · tone/variant swatches · scrim/bg-pos | faces, measure, design system | tone, background | — | ✅ | tokens (meaning — D6 boundary untouched) |
| **Content** — turn-into · media picker · background citation | — | background | media-role picker | turn-into | existing |

Ordering is fixed; vocabulary is fixed; a scope never re-orders or renames a section.
The refusals hold verbatim: **no raw CSS pane, no Fill/Stroke/Effects/opacity/corner
radius as literals** (they are the skin's palette roles — tone/variant — or nothing),
**no rotation** (not in the substrate's grammar; a transform channel is a new ADR if
ever), **no clip toggle** (the slide clips by kernel rule).

### D4 — Selection completion: the multi-selection becomes a first-class scope

- `StudioSurface` finally passes `onGroup`; selection state grows
  `groupIds: string[]`. The pane gains a **multi scope**: Identity ("N objects") +
  **Align / Distribute rows** (against the shared parent, or the frame when positioned)
  + shared-token intersection. Writes land through `setGeometryMany` (positioned) or
  per-child `align-self` (in flow) — one revision, existing ops.
- **Group / Ungroup verbs** (D2) live in the multi scope and container scope
  respectively, and in the right-click menu.
- **Deep select**: ⌘-click selects the innermost *container* under the hit even when a
  block covers it (the Figma/conventional modifier), closing gap §2.4 without touching
  the default ladder. Esc-walk stays the inverse. Double-click stays text-entry
  (P10), never descend.
- Breadcrumb, navigator tree, and canvas chrome light multi-selection consistently
  (every member boxed, the shared parent named).

### D4.1 — The set is STATE, not a scope (amended 2026-08-06, operator-directed)

D4 above says *"the pane gains a **multi scope**"*. That is withdrawn. The affordances
it names — align/distribute, Group/Ungroup, consistent chrome — all stand; only their
**home** changes. Re-derived from first principles at the operator's instruction rather
than by matching the ADR-528 precedent:

**What is a selection for?** It answers *what does the next verb act on*. Two things
follow, and they are different things:

1. **A scope answers "what is this?"** The pane is an inspector, and every one of its
   sections is a property *of a subject*: Identity is a label, Position is a box, Layout
   is a container's own CSS, Style is the subject's tokens. A **set of N things has no
   label, no box, no tier, and no `data-block-id`.** Asking the inspector to describe a
   set forces it to answer a question the set does not have — which is exactly how the
   pane came to show "HEADING · Typography: Heading 2" over a six-block range (`d878242`).
2. **A set answers "how many does the verb take?"** That is a fact about the *gesture*,
   not about the subject. `setGeometryMany` already proves the point: it accepts a list
   and writes one revision, and it has existed since 2026-07-24 **with no scope at all**.
   The op layer never needed one.

**The runtime settled this before the ADR asked.** `group` rides *alongside* `cur`, and
the comment at [projection.ts:988-994](../../web/components/workspace/viewers/projection.ts#L988-L994)
states the rule outright: *"cur stays the primary (the block the box, handles and
Properties scope follow), and group is the additional members. That keeps the
one-selection rule intact — every existing reader of `__yarnnnSelected()` still gets
exactly one element, and only the move gesture consults the group."* A multi scope would
have contradicted the substrate that already ships.

**And a scope is now unbuildable without breaking rule 11.** After ADR-528 D2.1, scope
derives FROM the tier the runtime declares. A set has no single tier — select a heading
and a figure and there is no honest answer — so a sixth scope would have to either invent
a tier or bypass the derivation. Both are worse than not having one.

**The decision.** A multi-selection is **state carried beside the selection**
(`groupIds: string[]`), never a scope:

- Single-subject sections **withdraw over a set and say they have withdrawn**, exactly as
  they now do over a multi-block range. Silence and staleness are the two failure modes;
  saying so is the fix.
- **Align / distribute is a SECTION that appears when the set has more than one member** —
  it is the one control whose subject genuinely *is* the set, so it is the one thing that
  earns a mount there.
- The Identity heading names the **count**, never a stale label.
- Nothing about the tier derivation, the scope set, or rule 11 changes.

**Where D4 was right, and stays right:** the multi-selection must become first-class —
`onGroup` wired, chrome consistent, align/distribute reachable, Group/Ungroup available.
The audit's finding was that the set is orphaned at the React boundary, and that is real.
The correction is only that "first-class" means *visible state*, not *a sixth scope*.

**Refused with it:** no synthetic set-subject (a fake label/box/tier standing in for N
things) · no per-member pane fan-out (N inspectors is not an inspector) · no scope whose
tier is invented rather than declared.

**The chrome follows the same rule** (2026-08-06). The canvas already boxed every member
identically to the primary (`.yarnnn-grouped` wears the primary's own outline — the set
reads as one selection, which is the point). The breadcrumb did not: it named the
primary's ancestry while N objects were boxed — the same staleness the pane withdrew, one
surface over. Over a set the crumb climbs from the members' **shared parent** (the deepest
container enclosing every member, `sharedChain`) and its innermost rung is the **count**.
A set has no single innermost rung; that is what makes it a set. Where the members share
nothing below the page, the page *is* the shared parent and the chain says exactly that.
A set spanning pages draws no chain at all — no shared page, no ancestry to name.

### D5 — Layout completion: the allowlist grows three rows, no new mechanism

- **Direction**: `flex-direction` column \| row on containers — the explicit Flow
  control. `.cols/.col` demotes to "a horizontal container the templates ship"
  (inert-name discipline, ADR-511 D8: classes keep styling old artifacts; the control
  is the live mechanism).
- **Align-self**: start/center/end presets on a *child* within a flow parent — the
  per-child half of alignment (the alignment row's in-flow implementation).
- **Numeric geometry entry**: X/Y/W/H fields in block Position/Layout become editable
  within the served two-clamp bounds (ADR-461 unchanged — same clamps, keyboard instead
  of drag). Entry is the readback made honest, not a new channel.
- Already-declared Phase-3 items ride along unchanged in priority: snap/alignment
  guides on drag; container drag = reorder per medium.

### D6 — Refused (restated for this ADR's scope)

No shadow group object · no rotation · no raw paint (fill/stroke/opacity/radius/
effects) · no per-element free CSS · no positional anything on web · no container
measures (a container sizes by flow + Hug/Fill; D5's numeric entry is block-staged
only) · no Sections-above-pages layer (the navigator's page list is the sequence; a
deck is linear).

## 4. Phases

1. **Phase A — the spine** (pure FE recomposition, no new ops): STUDIO.md hierarchy
   statement + this ADR's matrix; `StudioDesignTab` recomposed onto D3's spine;
   container verb-row parity; X/Y readback.
2. **Phase B — selection completion**: onGroup wiring · multi scope · align/distribute
   · Group/Ungroup verbs · ⌘-click deep select · chrome/breadcrumb/navigator
   multi-select consistency.
3. **Phase C — layout completion**: direction row · align-self · numeric entry ·
   then the standing Phase-3 pair (snap guides, container drag-reorder).

Each phase lands with its gates re-cut in the same commit (the counting-gate lesson);
the STUDIO.md matrix is amended cell-by-cell as cells ship, never ahead of them.

## 5. Open questions — RESOLVED at ratification (2026-08-05, per recommendation)

1. **Page identity** — **YES, stamp at the seam.** ✅ **Implemented 2026-08-06.** Pages
   were index-addressed (no `data-block-id`); ADR-516 built a second resolver to cope.
   `normalizeStructure` grew a page pass: pages get identity on the artifact's next write
   (migration-by-use, the ADR-511 annotation pattern — no fleet sweep). One resolver,
   breadcrumb/ops/multi-select uniformity. The ADR-516 page-anchor resolver retires when
   the id path covers it (singular implementation — the anchor fallback survives only for
   not-yet-written artifacts, and `arrangedPageAt` now tries id first).

   **Why stamping a page cannot make it read as a container**: a page is a `<section>`,
   and every container selector in the system is `div[data-block-id]:not([data-block])`
   — div-qualified, enumerated and asserted by the gate rather than assumed. The one
   un-qualified JS test (`climbChain`) stops *at* the page element, so it never reaches
   it. The gate pins the div-qualification across every file that carries the selector,
   so a future un-qualified one is caught there rather than by a member selecting a slide
   as a box.
2. **⌘-click deep select** — **YES** (D4). Conventional, discoverable-by-habit for
   exactly the users who need it. Phase B.
3. **Direction row** — **CONTAINERS ONLY** until a horizontal-page need is evidenced.
   Phase C.
