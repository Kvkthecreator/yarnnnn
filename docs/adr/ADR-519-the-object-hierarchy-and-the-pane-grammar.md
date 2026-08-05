# ADR-519 — The object hierarchy is four grains, and the pane speaks one grammar

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

1. **Page identity** — **YES, stamp at the seam.** Pages are index-addressed (no
   `data-block-id`); ADR-516 built a second resolver to cope. `normalizeStructure`
   grows a page pass: pages get identity on the artifact's next write
   (migration-by-use, the ADR-511 annotation pattern — no fleet sweep). One resolver,
   breadcrumb/ops/multi-select uniformity. Lands with **Phase B**, which is where
   addressing uniformity is consumed; the ADR-516 page-anchor resolver retires when the
   id path covers it (singular implementation — the anchor fallback survives only for
   not-yet-written artifacts).
2. **⌘-click deep select** — **YES** (D4). Conventional, discoverable-by-habit for
   exactly the users who need it. Phase B.
3. **Direction row** — **CONTAINERS ONLY** until a horizontal-page need is evidenced.
   Phase C.
