# ADR-443 — The Studio axiomatic model: blocks, layouts, and the seven operations

> **Amended by ADR-453** (2026-07-13): the model gains the **property-token annotation family**
> (`data-align`/`data-tone`/`data-height`/`data-fit`/`data-ratio`/`data-valign` — tokens, not
> pixels) and a second MARKED head element, `<style data-kernel="true">` (versioned kernel token
> CSS, self-retrofitting), joining ADR-449's `data-skin` in the switch-survival rule.

> **Amended by ADR-456** (2026-07-14): (1) **the markdown ruling** — R1 is upheld against a
> dual-source proposal: HTML stays the sole canonical source; markdown is an interchange
> *projection* (import at creation, export at the boundary), never a second source format.
> (2) The launch vocabulary grows by registry rows (D4's growth clause exercised): `divider` ·
> `toggle` · `button` · `gallery`. (3) The "format-agnostic" axiom is reconciled with ADR-447
> D7.5: the axiom survives as **block portability** — type change is a lane-performed judgment
> act (blocks + ids preserved); what D7.5 deleted was the mechanical type toggle.

> **Status**: **Accepted** (2026-07-12, operator-ratified; full-scope implementation delegated same-day). Ratifies the operator's six-axiom design philosophy for the Studio (HTML-native · component-native · layout-native · AI-native · format-agnostic · interoperable) **with the R1–R5 refinements** from the part-4 analysis, closes the universal feature set at **seven operations**, and flips the build sequence: the block/layout model lands **before** v1.2 tweak-gestures. Derivation: `docs/analysis/the-studio-axiomatic-model-components-and-layouts-2026-07-12.md` (part 4 of the probe series). Living design doc: `docs/design/STUDIO.md`.

**Date**: 2026-07-12
**Dimension**: Substrate (Axiom 1 — the artifact carries its own semantics) + Channel (Axiom 6 — the palette, switcher, pointing) + Mechanism (the lane transforms; nothing else writes)

**Extends**: ADR-440 (the Studio; this ADR upgrades D4 templates + D5 references + v1.1 pointing), ADR-441 (projection lives in the renderer layer), ADR-442 (surface-bar actions carry the switcher), ADR-177 (the section-kind vocabulary — absorbed), ADR-245 (L2/L3 content-shape rendering — the FE ancestor of block kinds).

---

## D1 — The six axioms, ratified with five refinements

The manifesto is canon, subject to:

- **R1 — No shadow content model. The DOM is the model.** Semantics live IN the HTML as thin `data-*` annotations; there is no JSON block model that HTML is compiled from. A shadow model would demote HTML to an export format (violating axiom 1), create a drifting second source of truth (violating Singular Implementation), and orphan the revision chain. This is the load-bearing correction; everything else follows from it.
- **R2 — Layout is a binding inside the artifact; switching is an authored transformation.** `data-template` + the artifact's `<style>` skin ARE the layout. Switching preserves the block sequence, replaces skin + flow structure, and lands as an attributed revision (lane-performed). Never a view toggle — the rendering IS the file.
- **R3 — Blocks are owned; citations are borrowed.** A `data-block` element is artifact-owned content the lane edits in place; a `data-ref` element is a commons object projected read-only (ADR-440 D5 unchanged; the OpenDoc guard unchanged). A block may contain citations.
- **R4 — One vocabulary, kernel-seeded, one home; grammar not schema.** The block vocabulary unifies the compose section-kinds (ADR-177), the L3 affordance ancestry (ADR-245), and the reference model into ONE registry in `services/studio.py`, served to the FE (`GET /studio/vocabulary`). It TEACHES (posture grammar + palette) and never VALIDATES — unknown blocks render as generic content; the trace witnesses, nothing polices.
- **R5 — Scope guard: Studio authors one type.** Format-agnosticism means one artifact renders as document/deck/article/page and later projects across the boundary (publish, exports as rented capabilities). It does NOT mean Studio edits PDFs or other viewer types (ADR-436's registry owns rendering those).

## D2 — The seven operations (the closed universal feature set)

**CREATE · COMPOSE · TRANSFORM · POINT · CITE · PROJECT · TRACE.** Every present and future Studio capability is one of these, parameterized by (layout, vocabulary). Tweak-gestures (v1.2) are TRANSFORM with a gesture composing the patch; publish is PROJECT at the boundary plus CITE's pins. Any proposal introducing an eighth operation is presumptively drift and must argue against this decision.

## D3 — The operator-word rule (the surfacing principle)

**The seven operations are internal vocabulary; the chrome speaks operator words.** The FE never surfaces "compose/transform/project/deixis" — it says **Create · Add · Edit (through the chat) · Select · Insert from workspace · Change layout · History**. The mapping is fixed in `docs/design/STUDIO.md` and is the contract for every future affordance: model-language in code and canon, human language in chrome. (The macOS rule: users never see the word "syscall.")

## D4 — The block annotation spec

- `data-block="<kind>"` on each top-level content unit; `data-block-id="<short-id>"` stamped by the author (skeleton stamps starters; the posture teaches the lane to stamp new blocks and PRESERVE existing ids).
- Layout flow containers (a deck's `<section class="slide">`, a document's `<main>`, an article's `<article>`) are structure, not vocabulary blocks; blocks live inside them.
- An artifact with zero annotations remains valid (grammar, not schema).
- Launch vocabulary (8 kinds, three groups): **Content** `prose · callout · quote · checklist` · **Data** `table · metrics · chart` · **Media** `figure`. Growth = a row in the registry, never a new mechanism.

## D5 — Layouts as first-class kernel data + the switcher

`STUDIO_LAYOUTS` registry: `{slug, label, description, skin (CSS), flow (grammar prose), starters (block kinds)}` for `document · deck · article`. **A template = layout × starter blocks** — the three hardcoded skeletons are DELETED and assembled from the registry (`build_skeleton`). FE: creation picker renders layouts; an open artifact gets a **"Change layout" surface-bar action** (ADR-442 contract, button-shaped) opening a picker whose selection seeds the lane's re-layout transformation (R2). Deterministic mechanical re-skin is a permissible later optimization; the act's shape (revision) is fixed now.

## D6 — Block-grain pointing

The pointer runtime (projection `pointer` mode) reports `{blockId, blockKind}` alongside `{tag, text, dataRef}` by walking to the nearest `[data-block]` ancestor; selection outlines the block. The seed speaks operator words ("Selected the callout block…"). Posture v2 teaches block-grain patching (patch within block boundaries; address blocks by id) — which aligns `trace` diffs to blocks, the finest attribution grain in the benchmark class.

## D7 — Scope: ships now / stays deferred

**Ships (this ADR)**: the unified vocabulary + layout registries and skeleton assembly (BE) · posture v2 (block grammar + id discipline + layout-switch grammar) · `GET /studio/vocabulary` · the palette rendered from the served vocabulary (operator-word groups; Image/Table pickers + Chart ask preserved as the citation-backed kinds) · the Change-layout bar action + picker · block-grain pointing.
**Deferred, unchanged from ADR-440 D7**: v1.2 tweak-gestures (now properly sequenced AFTER blocks) · publish/pin-at-publish/exports · desktop tile · third-party components (a widget ABI is refused outright — components are semantic HTML + skin, never embedded editors) · the engineer-agent hire.

## Consequences

- **Positive**: the universal feature set is closed and named; the palette/switcher/pointing all read from one kernel registry; tweaks and trace gain block grain for free; the manifesto's ambition ("object-processing system") is grounded without a second content model or a widget platform.
- **Cost**: `services/studio.py` refactors (skeletons → assembly); posture grows moderately; one new endpoint; FE palette + switcher + pointer payload.
- **Risk**: low — additive annotations (unannotated artifacts stay valid), API shapes preserved (`STUDIO_TEMPLATES` derives from layouts), no schema/migration.

## The one-line statement

**The DOM is the model: blocks are semantic HTML the artifact owns, citations are commons objects it borrows, layout is a switchable binding whose change is an authored revision, one kernel-seeded vocabulary teaches without validating, the whole feature set closes at seven operations surfaced only in operator words — and because a gesture wants a block to aim at, blocks land before tweaks.**
