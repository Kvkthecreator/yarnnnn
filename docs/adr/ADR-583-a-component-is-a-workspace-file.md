# ADR-583 — A component is a workspace file: the composed object joins the citation discipline

> **Status**: **Accepted** (2026-08-19). Operator-ruled after the ADR-581 D4 discourse:
> *"the law recut, your interpretation is correct… i think components as files is right
> (library). its conceptual approach should be thoroughly consistent to that of our
> existing csv and images handling. thus, single discipline approach that actually gives
> us the long standing persistent management. the carve shape… resides NOT as the
> separate app. thus, the existing add, new, update will need streamlined updating."*
>
> **Preserves**: [ADR-440](ADR-440-the-studio.md) D5 (citations: reference, never copy;
> pinned at insert) · [ADR-579](ADR-579-three-verbs-that-write-one-act-that-doesnt.md)
> (ADD = from the workspace; NEW = minted; the seam is WHO) ·
> [ADR-581](ADR-581-the-medium-regroup-deck-first-vocabulary.md) (family derives from
> `tier × cites`; the medium orders NEW) · [ADR-539](ADR-539-the-vocabulary-declares-behavior.md)
> D1 (a row declares its behavior; groups derive) · [ADR-562](ADR-562-the-app-owns-its-ai-configuration.md)
> (residency — no new agent; the compose act is a JOB on the designer) ·
> [ADR-417](ADR-417-generation-is-rented-not-owned.md) (unaffected: the lane AUTHORING
> markup is not an owned generation engine).
>
> **Supersedes in part**: [ADR-538](ADR-538-a-block-is-classified-by-what-it-cites.md)
> D3's answer to "can we scope these kinds of components in." D3 answered with a
> pre-drafted inline card (a registry row whose skeleton the kernel draws). This ADR
> keeps D3's *classification rule* — a block is what it cites — and moves the component
> to the side of that rule it always belonged on: a component CITES A FRAGMENT.
>
> **Dimensional classification** (Axiom 0): **Substrate** (a new citable file class +
> a citation kind) + **Channel** (the ADD door gains the library; the compose act joins
> the designer's job).

---

## 1. Context — the catalog was answering the wrong question

ADR-581 D4 grew the composed family with pre-drafted kinds (stat · comparison ·
timeline · person). Those serve the door that cannot generate — the member's CLICK,
which must land a fragment in the same frame as the gesture. But the operator's
Claude Design experience exposed the question the catalog cannot answer: *"when I
referred to my actual github repository connection, and screenshot the specific url
path and component, it seemed to reverse engineer the component."* No catalog would
ever have contained that component. Generation grounded on a referent is the
component capability; a catalog is a keyboard.

Meanwhile the system already holds the discipline the answer needs, twice over: a
table is not pasted rows — it is a CITED `.csv`, projected at render, pinned at
insert, current when the source changes. An image is not pasted bytes — it is a
CITED picture. The component was the one composed object still living as copied
markup. **The single discipline the operator ruled: a component is a workspace file,
managed like the CSVs and images beside it.**

## 2. Decisions

### D1 — The law recut: never a raw colour; geometry free

The token law's operative invariant is narrowed to what it always meant: **never a
raw colour, face, or radius — every themable property reaches the artifact through
the design-system slots (`var(--accent…)`, `var(--font-…)`, `var(--radius-…)`,
`var(--text-…)`), with fallbacks.** That invariant is what makes a skin swap re-theme
every document — the entire reason the colour picker is refused (ADR-449).

Bespoke **geometry** — flex, grid, padding, a component's own shape — was never that
rule's subject, and forbidding it is what forced every composed shape to be a
pre-declared kernel row. A component FILE carries its own scoped CSS: geometry free,
theme through the slots.

The placement/emphasis rule for ordinary blocks is untouched: on a block in an
artifact, the token IS the edit (align/tone/size…), and inline `style=""` stays
refused there. The bespoke CSS lives in the component file, not sprayed on blocks.

### D2 — The component file: `*.component.html`

A component is a workspace file whose name ends `.component.html` — self-describing,
listable by suffix (the `.csv` precedent), impossible to confuse with an artifact
(which is a full `<!doctype html>` document). Its contract:

- an HTML **fragment** with a single root element;
- MAY carry its own `<style>`, **scoped under its root** (selectors prefixed so
  nothing leaks into the citing artifact);
- colours/faces/radii/type sizes through the design-system slots with fallbacks
  (D1) — so the workspace's design system themes every instance by cascade;
- **no `<script>`** (the artifact law, enforced mechanically at projection);
- **no `data-block-id` inside** — identity belongs to the citing block; a fragment
  is content, not structure.

It is an ordinary text file on the substrate: authored via `write_revision`,
attributed, versioned, revertible, exported with the workspace. Meaning-placed like
everything else; `components/` under the operation region is the taught convention,
never a requirement.

### D3 — The `component` kind is re-cut: it cites a fragment

The ADR-538 D2 chart precedent, applied to the row next to it: the inline-card
`component` was a library object wearing a copied-skeleton label. The registry row
becomes:

```
cites: "fragment"        (a FOURTH citation value — data source · picture · fragment)
markup: <div data-block="component" data-ref="operation/components/….component.html"
             data-ref-kind="component" data-ref-rev="<head-rev-id>"></div>
```

- `GROUP_BY_CITES` gains `fragment → "component"` (a served display label).
- The ADR-581 family derivation needs **no change**: `cites ≠ none` → **cited** →
  the kind lands in **ADD** by construction — which is exactly the verb's meaning
  (ADD = from the workspace; the library is the workspace).
- `MEDIA_BLOCK_KINDS` is untouched (it derives from `cites == "picture"`).
- Existing inline-card markup in members' artifacts keeps rendering — the kernel's
  card CSS stays (ADR-511 D8: legacy renders, never migrates). What changes is what
  the door OFFERS: picking Component now opens the library picker.

### D4 — The projection inlines the fragment (the CSV rail, verbatim)

`resolveOne` gains a `component` branch beside `table`/`chart`: read the cited file,
**strip executables** (script/iframe/object/embed, `on*` handlers, `javascript:`
URLs — defense in depth; the canvas sandbox never runs script anyway), inline the
fragment into the citing block. The pinned fallback draws the component too (the
ADR-538 lesson: a dangling citation must not dump raw source). Reference, never
copy: change the component file and every citing artifact is current.

### D5 — The compose act is a JOB on the designer, not an app

The carve the operator named: composing a component — including **reverse-engineering
a referent** (a screenshot attached to the lane turn, a repo file through the
connector, an existing design) — is a posture-taught act of the Studio-bound lane's
resident. No new agent (ADR-562 residency), no new app, no new primitive: the lane
already has vision on attachments, `WriteFile`, and the substrate. The posture
teaches the contract (D2) and the act: author the file, then cite it. The ADR-579 D8
"from sources…" create door remains the phased front door for this act; this ADR
gives it the thing it will create.

### D6 — The verbs, streamlined; the catalog, capped

- **ADD** — cite from the workspace: images · CSVs · **components**. The picker
  gains the library list.
- **NEW** — mint content in place: prose kinds + the composed click-primitives
  (stat · comparison · timeline · person · button · metrics · divider). These are
  keycaps for the click door, NOT the component strategy: **the catalog is capped**
  — a new registry row now needs a click-door gap, never a "we need this component"
  need. That need is a component file.
- **UPDATE** on a cited component — already the law: never edit cited content inside
  the artifact; edit the SOURCE file, every instance follows.

## 3. What this deliberately does not do

- **No sub-file addressing** (ADR-528's finding stands): a component is cited whole.
- **No share-link resolution change**: the public share serves raw content today for
  every citation kind (tables included); components inherit that surface's existing
  behaviour and its eventual fix.
- **No component marketplace / cross-workspace anything**: a component is workspace
  substrate, reached like any file (grants, not species).

## 4. Gates

`api/test_adr583_component_library.py` (script-style): the enum + row declaration,
the family/ADD landing executed against the live registry, the citable endpoint's
suffix query, the projection branch + sanitizer + pinned fallback, the picker's
fragment branch, the posture anchors (law recut + contract), and falsifiers.
Amended: `test_adr538` §3 (the D3 supersession recorded), `test_adr581` (component
anchor moves composed → cited), `test_adr539` (the fourth cites value).
