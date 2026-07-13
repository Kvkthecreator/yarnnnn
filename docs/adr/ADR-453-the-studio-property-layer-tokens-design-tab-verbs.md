# ADR-453 — The Studio property layer: tokens-not-pixels, the Design tab, and the grain-aligned verbs

> **Status**: **Accepted** (2026-07-13, operator-ratified — "proceed in full"). The operator, from
> the Figma inspector and then self-corrected to the Wix/Webflow family, named the missing
> in-document layer: interactive control of *where things sit and how they read* — position,
> layout, appearance — universal across document types, integrated into the member's clicks on the
> canvas (the double-click precedent). This ADR ships that layer the HTML-native way: **Figma's
> inspector ergonomics over CSS-native properties, never Figma's free-transform geometry** —
> property TOKENS (a third `data-*` annotation family), a scope-switching **Design tab** on the
> right column (Chat | Design), a grain-aligned verb realignment (Insert · New ‹slide|section› ·
> Re-arrange), and the arrangement registry promoted to the canvas's **interaction contract**
> (one row → six projections). Derivation: the 2026-07-13 in-document action-model discourse
> (recon of the shipped ADR-440/442/443/444/446/447/449/450/452 action inventory).

**Date**: 2026-07-13
**Dimension**: Substrate (Axiom 1 — the artifact carries its own property semantics as `data-*`
tokens + a marked kernel style element) + Channel (the Design tab, the verb realignment) +
Mechanism (every property edit is a deterministic, free, CAS-guarded mechanical revision).

**Amends**:
- **ADR-443** — the axiomatic model gains the property-token annotation family (`data-align`,
  `data-tone`, …) beside `data-template`/`data-arrange`/`data-slot`/`data-block`, and a second
  MARKED style element (`data-kernel`) joins ADR-449's `data-skin` in the head contract.
- **ADR-444** — the mechanical op set completes: `setToken`, delete/duplicate/move at block and
  page grain, and `applySkin`/`removeSkin` join the insert/edit/arrange ops. The toolbar verbs
  realign (below).
- **ADR-446 D6** — the deferred "style/geometry tweaks (the tweak-inspector, now properly
  block-grained)" ARRIVES, as tokens in the Design tab.
- **ADR-447** — D7.2's "no inspector column" is amended: the inspector returns as the right
  column's second TAB (not a fourth column) because the ratified scope grew to property editing;
  D7.1's derived wireframe thumbnails land (the New flyout + the Re-arrange gallery); D5's single
  "Arrange" operator word retires in favor of the grain-honest pair **New ‹slide|section›** /
  **Re-arrange**.
- **ADR-449 D5** — the design-system picker is homed: the Design tab's document scope (discovery
  served on the vocabulary; resolution via `GET /studio/design-systems/resolve`; apply through the
  one mechanical door, FE-side `applySkin` mirroring `apply_skin_to_html`).

**Preserves**: the DOM is the model / no shadow layer (ADR-443 R1) · grammar-not-schema (R4) ·
the ONE mechanical write door + CAS + free-no-LLM (ADR-444/396/406) · block ids preserved
(ADR-446) · citations-by-reference (ADR-440 D5) · the skin contract (ADR-449 — the `data-skin`
element outranks everything by cascade order and survives every switch) · no widget ABI · no
keystroke CRDT.

---

## D1 — Tokens, not pixels: the property layer

Studio adopts the **Wix/Webflow family**, not Figma's: the member composes *within* a layout
system the kernel + design system define; they do not author free geometry. Figma's panel
*contents* map to CSS-native equivalents, and those are what ship — as **property tokens**, a
third `data-*` annotation family interpreted by kernel CSS:

| Token | Grain | Values | CSS it drives |
|---|---|---|---|
| `data-align` | block | `start · center · end` | text-align + auto margins |
| `data-tone` | block + page | `accent · muted · inverse` | color/background via CSS custom properties |
| `data-height` | media block (figure/chart) | `s · m · l` | max-height presets |
| `data-fit` | media block | `cover · contain` | object-fit |
| `data-ratio` | page (≥2 flow slots) | `1-1 · 2-1 · 1-2` | column flex weights |
| `data-valign` | deck slide | `start · center · end` | slide justify-content |

Rules:
- **Absence is the default** — the default value is never written; clearing a token removes the
  attribute. Un-tokened artifacts stay valid (grammar not schema).
- **Tokens reference intent, never hex.** Appearance tokens resolve through CSS custom properties
  (`--accent`, `--muted`, `--ink`, `--paper`) — a design system (ADR-449) redefines the
  properties and every token restyles with it. Raw color pickers are REFUSED (the
  detached-style soup that would hollow out the skin contract).
- The registry is kernel-seeded (`STUDIO_TOKENS` in `services/studio.py`), served on
  `GET /studio/vocabulary`, and taught in the lane's posture — **one grammar for the Design tab's
  segmented controls and the lane's plain-words edits** (R4).

## D2 — The marked kernel style element (`data-kernel`) — the retrofit path

Token CSS (and any future arrangement CSS) must reach artifacts that are self-contained HTML,
including artifacts created before this ADR. The ADR-449 marked-element pattern generalizes:

```html
<style data-kernel="true" data-kernel-v="1"> …the kernel token/arrangement CSS… </style>
```

- **Baked** into new skeletons (`build_skeleton`).
- **Upserted** by the FE mechanical ops: any op that needs it (`setToken`, arrangement ops)
  ensures the element exists and is at the served version (`kernel_css_version` on the
  vocabulary), replacing an older one. Old artifacts retrofit on first touch, as one attributed
  revision.
- **Cascade order** in `<head>`: unmarked layout `<style>` < `data-kernel` < `data-skin` — the
  kernel styles tokens; the workspace's design system can still override everything.
- **Survives switches**: the ADR-449 rule ("replace the UNMARKED style only") now protects both
  marked elements. The lane's posture says so explicitly.

## D3 — The verb realignment: Insert · New ‹slide|section› · Re-arrange

The toolbar's "Add ▾ / Arrange ▾" mixed grains (Arrange held both "add a slide" and "change the
selected slide"). The realignment, in operator words:

- **Insert ▾** (block grain) — content units into the current flow/slot. The former Add, honestly
  named. Chart's ask-the-lane exception unchanged.
- **New slide ▾** (deck) / **New section ▾** (document, article) — the page-grain structural act,
  promoted to a first-class typed verb. Its flyout is the **arrangement gallery with derived
  wireframe thumbnails** (D7.1 lands here): the thumbnail is a structural mini-render derived
  from the row's `slots` + heading presence, never a hand-drawn asset — adding an arrangement
  stays one registry row. An article/document has no page boundary (both render as continuous
  flow); its structural unit is the *section band*. Pagination is a print/export-time concern,
  deferred with export (ADR-417).
- **Re-arrange** (page grain, selection-scoped) — change *this* page's arrangement. Moves out of
  the toolbar into the Design tab's page scope, with the same thumbnail gallery.

The toolbar keeps: Insert · New ‹noun› · zoom · a minimal selection chip (identity + clear —
the acknowledgment; the verbs live in the Design tab).

## D4 — The Design tab: the inspector returns as the right column's second tab

The right column becomes two tabs — **Chat | Design** (the Canva model; no fourth column). The
lane stays mounted (hidden, never unmounted — a streaming turn survives a tab switch). The Design
tab is a **scope-switching inspector** over the current selection:

| Selection | The Design tab shows |
|---|---|
| nothing | **Document scope** — the design-system picker (workspace design systems via ADR-449 discovery; the artifact's current `data-skin` ref; Apply/Remove as one mechanical revision) |
| a page (slide/section) | **Page scope** — the Re-arrange thumbnail gallery · page tokens (`tone`, `valign` on decks, `ratio` when the arrangement has ≥2 flow slots) · Duplicate / Move up / Move down / Delete |
| a slot | **Slot scope** — the slot's name + role · role-gated quick-add into it |
| a block | **Block scope** — block tokens (`align`, `tone`; media blocks add `height`, `fit`) · Ask about this (the one judgment bridge — seeds the lane and flips to the Chat tab) · Duplicate / Move up / Move down / Delete · the double-click-to-edit hint |

This single move homes the three orphans the recon surfaced: the ADR-449 picker (D5 handoff),
ADR-449 D6's pin-semantics UX (rides the Design tab's citation display, later), and ADR-446 D6's
tweak controls (they ARE the tokens). Current token values are parsed from the artifact SOURCE at
render (derived, never stored).

## D5 — The arrangement registry is the canvas's interaction contract

"Title with two sections / three sections" doesn't just render — the arrangement row drives the
whole interactive layer. **One row → six projections**: markup fragment · CSS · wireframe
thumbnail · canvas affordances (slot outlines, add points, legal targets) · the Design tab's
page controls · the lane's posture grammar. Slot `role` (already in the registry: `flow` /
`heading` / `media`) becomes the interaction gate:

- **Hover** — slots show a faint outline + their name on hover (the Wix section-hover); how the
  member *discovers* composition. Read-only, runtime CSS.
- **Click grains** — block (a pointable inside a block) → slot (a slot's empty padding) → page
  (the page margin). The pointer payload gains `slot` + `arrange`; this un-defers D7.3's drill in
  its minimal honest form, because slots now *do* something.
- **Role-gated add** — "+ Add here" (and the slot scope's quick-add) dispatches by the slot's
  role looked up from the vocabulary: `flow` → a prose block (as today), `media` → the image
  picker. New arrangements make the media role real: deck **picture-with-caption** (media +
  caption slots) and **section-header** (a `data-tone="inverse"` divider — the first shipped
  token use), article **lead-image**.

## D6 — Mechanical completion: the missing editor verbs

`artifactOps` completes with pure transforms through the one door, all free, all CAS-guarded, all
id-preserving: `setToken` (set/clear + kernel-element upsert) · `deleteBlock` · `duplicateBlock`
(fresh ids) · `moveBlock(up|down)` · `deletePage` · `duplicatePage` (fresh ids) ·
`movePage(up|down)` · `applySkin`/`removeSkin` (FE mirror of `apply_skin_to_html`). A member no
longer needs a metered judgment turn to remove a block — the ADR-444 two-path carve is restored.

## D7 — Scope: v1 ships / fast-follows / refusals

**v1 (this ADR's implementation)**: D1–D6 — the token registry + kernel element + vocabulary
extension + design-system serving + posture · the verb realignment with wireframe thumbnails ·
the Design tab (all four scopes) · hover outlines + slot-grain selection + role-gated add · the
three new arrangements · the mechanical verb completion · the gate.

**Fast-follows (each its own commit, independently gate-able)**:
- **In-frame block drag** between slots — the D7.4 unlock: dragging an *existing* block never
  crosses the iframe boundary (the whole pointer gesture runs inside the runtime; the parent
  receives only the committed `{blockId, targetSlot, targetIndex}`). Parent→frame drag (new block
  from the toolbar) stays deferred; click-to-insert covers it.
- **Snap-handle resize** — column-divider and media-corner handles that step through token stops
  (`2-1` → `1-1` → `1-2`), never free pixels.
- **Undo + History** — surface-bar `⋯` gains History (mounts `RevisionHistoryPanel`); Undo =
  revert-as-write (ADR-406): write the prior revision's content back through the door as a new
  attributed revision.
- Navigator management (slide-card context menu → the D6 page verbs; clickable outline) ·
  smarter slot-mapping on Re-arrange (by role + order) · pin-semantics UX (ADR-449 D6).

**Refusals (named so they never re-litigate)**: free X/Y + rotation for flow content (the
sanctioned equivalent of overlay positioning is a 9-position token on overlay-type arrangements,
when those ship; if true free-placement demand ever materializes it is a new *arrangement kind*
with positioned slots — an escape valve that doesn't break R1) · raw per-block color/fill/stroke
pickers (tokens through the skin contract, or nothing) · effects/shadows (skin's job) · an export
panel (ADR-417 — rented at the boundary) · number-field geometry (Studio edits intent discretely
because responsive HTML, not fixed frames).

## Consequences

- **Positive**: the member gets Wix-class in-document control — properties, structure verbs,
  design systems — with zero new write machinery (every act is one deterministic revision through
  the existing door); the three orphaned handoffs (449 picker, 449 pin UX, 446 tweaks) get a real
  home; the arrangement registry becomes the single source the whole interactive layer derives
  from (adding an arrangement stays one row); the lane and the controls speak one grammar; old
  artifacts retrofit themselves on first touch via the marked kernel element.
- **Cost**: a real FE lift (Design tab, thumbnails, runtime grains) though the backend is small
  (one registry, one endpoint, posture prose); the posture grows one section (envelope-dilution
  checked: short, listed, plain).
- **Risk**: low-moderate — tokens are additive attributes (un-tokened artifacts unchanged; CSS
  self-gates); the runtime changes extend the established postMessage bridge without new write
  paths; the one place to get right is the kernel-element upsert (versioned, idempotent,
  regex-anchored on the marked attribute — the proven ADR-449 pattern).

## The one-line statement

**Studio's in-document control ships the HTML-native way: property tokens (a third `data-*`
family — align/tone/height/fit/ratio/valign) interpreted by a marked, versioned, self-retrofitting
kernel style element and themeable by the design system's custom properties; the verbs realign to
their grains (Insert a block · New slide/section from a thumbnail gallery · Re-arrange this page);
the inspector returns as the right column's Design tab, scope-switching over
document/page/slot/block and homing the design-system picker; and the arrangement registry becomes
the canvas's interaction contract — slots outline on hover, select on click, and gate what can
land in them by role — so a member composes within the system directly, every act one free,
attributed, CAS-guarded revision through the one mechanical door, and Figma's ergonomics arrive
without ever importing Figma's geometry.**
