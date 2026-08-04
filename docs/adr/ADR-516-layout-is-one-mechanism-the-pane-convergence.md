# ADR-516 — Layout is one mechanism: the pane convergence, and the legible container

- **Status**: Accepted (2026-08-04, operator-directed — *"consolidation and streamlining of
  both code and documentation … even scoping in clean up of legacy, to avoid dual approach
  for future ambiguity"* — the follow-through on the ADR-511 audit's industry-alignment
  review)
- **Date**: 2026-08-04
- **Dimension**: Studio Design tab + artifact format + canvas chrome. No schema change,
  no new primitive.
- **Amends / supersedes**:
  - **ADR-453 (amended)** — the property-token registry loses its two page-grain LAYOUT
    rows (`valign`, `pad`). The token model itself is not retired: tokens remain the
    carrier for *meaning* (tone, variant, scrim, focus, typography). See D6 for the
    boundary.
  - **ADR-456 W1 `pad` / ADR-453 `valign` (superseded as tokens)** — both survive as
    kernel CSS for legacy artifacts (inert names, the ADR-511 D8 pattern) and as pane
    affordances re-cut onto the CSS mechanism.
  - **ADR-466 P9 (scoped)** — "only a BLOCK is measurable" was written when the coarser
    grains were slots and pages with no identity. It still governs *measures* (geometry
    ops). It stops governing *selection legibility*: a structural container earns the
    selection box (static variant), because ADR-511 made it a real selection subject.
  - **ADR-511 (extended)** — D4's container scope grows Width (Hug | Fill); Phase 3's
    "Hug/Fixed/Fill sizing idioms on containers" partially lands here, in the CSS
    mechanism rather than a new token row.

---

## Context

The 2026-08-02 click-pass and the industry-alignment review that followed it surfaced
three facts about the interaction layer:

1. **Two layout languages, one rung apart.** A selected *slide* offered Vertical align /
   Spacing as `data-*` property tokens interpreted by the baked kernel stylesheet; the
   *container* one level down offered Padding / Gap / Align / Justify as literal inline
   CSS (ADR-511 D4). Same member intent — "give this thing breathing room" — two
   mechanisms, two vocabularies, two failure modes. Industry-wise a slide *is* the
   outermost container; no reference tool speaks two layout languages by nesting depth.
2. **A selected container was illegible.** ADR-511 D3 made containers selection
   subjects, but the object chrome (box, handles, move band) is gated on `data-block`
   (ADR-466 P9), so selecting a container produced a 1px outline and a Design-tab flip —
   nearly invisible on a stage where every block answers with a full box. The operator's
   own first contact read as "can't grab it." The hover chrome *advertises* the
   container (outline + green label); the selection chrome went silent. The
   visible-but-inert clash, one level up.
3. **The conventional substrate argues for the CSS carrier.** After ADR-511, the
   artifact is plain HTML/CSS + three annotations. A layout property expressed as
   `data-pad="l"` needs the baked kernel to mean anything; the same property as
   `style="padding: 4.5rem 5.5rem"` means itself — to a browser, to an importer, and to
   the lane in its native tongue. Every layout property still riding a token is a
   decoder-ring dependency the substrate no longer needs.

## Decisions

### D1 — The page is a container: one layout mechanism across grains

Layout properties write **bounded inline-CSS presets** through the ONE op —
`setContainerLayout` — at every grain that has them. The op gains an **anchor resolver**:
id-addressed for containers (unchanged), page-anchored (`arrangedPageAt`) for pages,
which carry no `data-block-id` and are addressed by position everywhere else in the op
layer. One op, one allowlist, two resolvers — no second write path (ADR-462 D1 holds).

The property surface remains an **allowlist of enumerated presets** (never a raw CSS
pane — ADR-511 D7 stands). Page presets carry the medium's own values (a slide's
padding steps differ from a web band's); the values live in the same allowlist,
extended, not in a parallel table.

### D2 — `valign` and `pad` leave the token registry; their rules become inert names

The two page-grain layout rows are **deleted from `STUDIO_TOKENS`** — gone from the
served vocabulary, the Design tab's generic token rows, and the lane's grammar (an
ADR-306-shaped ablation: the lane already speaks `padding` and `justify-content`
natively; teaching it a private synonym was prompt tax).

Their kernel CSS rules (`[data-valign]`, `[data-pad]`) **remain** — the ADR-511 D8
ruling applies verbatim: existing artifacts carry the attributes and baked kernels that
read them; stripping would break live rendering. The attributes become **inert names**:
nothing writes them, nothing gates on them, CSS still honors them on the artifacts that
carry them.

**Convergence-by-use:** a layout write to an element strips *that element's* legacy
layout attributes (`data-valign`, `data-pad`) in the same revision — single element,
authored by the member acting on it, never a fleet sweep (ADR-209). Inline style would
win the cascade anyway; the strip keeps each element single-sourced.

### D3 — The pane's page scope speaks the same rows

The Design tab's page scope gains a LAYOUT section — the same preset-row component the
container scope uses — offering Padding (medium-appropriate presets) and Vertical align
(`justify-content`; the slide skin is already a flex column). Pressed-state reads the
element's inline style first, the legacy attribute as display-only fallback. Tone,
Columns, Background rows are untouched (see D6).

### D4 — Containers gain Width: Hug | Fill, in the CSS mechanism

The container scope's LAYOUT section grows a Width row: **Hug** (`width: fit-content`) |
**Fill** (`width: 100%`) | absence = the flow's own width. This is Phase 3's container
sizing idiom, landed as two more allowlist values rather than a new token row. `Fixed`
stays refused at this grain — a continuous value has no enumerable preset, and the
block-staged measure remains the one bounded exception (ADR-461 D3).

### D5 — A selected container is legible: the static box

`syncBox` extends to structural containers: a selected container wears the selection
box in a **container variant** — border only, **no handles, no move band, no move
cursor**. The chrome must not promise gestures the grain lacks (the ADR-466 "honest
about inertness" rule, applied at the new grain). Geometry ops stay measurable-gated
exactly as before; nothing here makes a container resizable or positionable.

### D6 — The boundary: geometry converges on CSS; meaning stays tokens

What converges and what stays, decided by one test — *does the value mean itself, or is
it themed/structural indirection?*

| Converges to inline CSS | Stays a token | Why it stays |
|---|---|---|
| padding (page + container) | `tone`, `variant` | themed via custom properties — the value is a *palette role*, resolved by the skin, never a literal |
| vertical align / justify | `scrim`, `bg-pos` | halves of the cited-background mechanism (ADR-456 W3), not free layout |
| gap, align, justify (container, ADR-511 D4) | `font`, `measure`, `pagenum` | document-grain, themed/structural |
| width Hug/Fill (container, D4) | `size`, `align` (block) | block-grain; same themed-ramp interactions (`.slide [data-size="fill"]` cap-beating); revisit only with evidence |
| | `ratio` | a stop over a sibling *pair* — the divider gesture's grammar; not a single-element property. Named holdout, not an oversight |

### D7 — Refusals restated

No raw CSS pane (bounded presets only). No container measures/positioning (a container
is flow structure; D5 is legibility, not geometry). No fleet migration (D2's strip is
per-element, at the member's own write). No new op.

## Consequences

- One layout language at every grain; exports read as ordinary HTML without the kernel
  decoder ring for layout; the lane's grammar shrinks.
- The registry's `page-deck` applies-value loses its last token; `applies` simplifies
  in practice without a contract change.
- Legacy `data-valign`/`data-pad` artifacts render unchanged forever; each element
  converges on its next layout touch.
- The operator's "can't grab it" resolves into: *selectable and visibly selected*
  (D5), *layout-editable in one language* (D1–D4), *not draggable* — the remaining
  Phase 3 items (container drag-reorder per medium, snap guides) stay declared in
  `docs/design/STUDIO.md`'s interaction matrix, which this ADR's companion rewrite
  makes the single contract surface.
