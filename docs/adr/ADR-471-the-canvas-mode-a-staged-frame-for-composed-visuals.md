# ADR-471 — The canvas mode: a staged frame for composed visuals

> **⚠️ HOUSING SUPERSEDED by [ADR-472](ADR-472-images-as-a-first-class-app.md)** (2026-07-20, same day). The canvas shipped here as a **fifth Studio layout**, deliberately Studio-quiet, with the extraction deferred to IMAGES P4. The operator hit the seam earlier, from the product side — it read as a document type, not the app its name promised — and the carve landed immediately: the doc type left `STUDIO_LAYOUTS` for `services/images.py`, gained its own surface / route / dock icon, and `data-template="canvas"` became `data-template="image"`. **D-c (the `aspect` slug token) is DELETED**, not moved: a stage now carries real W×H pixels (ADR-472 D3), because a token's values must be enumerable and a dimension is continuous.
> **What this ADR got RIGHT and ADR-472 preserved**: **D-a — the artboard inherits the object layer rather than rebuilding it** (`class="slide"`, the frame class as the grain's boundary). ADR-472 D2 *promotes* that inheritance to a shared kernel consumed by both apps (and renames the grain `block-deck` → `block-staged`, paying the naming debt D-a knowingly took on). The coupling audit confirmed this was load-bearing: a naive extraction would have shipped IMAGES with artboards on which nothing could be positioned. This ADR's click-pass-earned posture assertions survive intact in `api/test_adr472_images.py` (which supersedes `test_adr471_canvas.py`).
>
> **Status**: **Accepted + Implemented** (2026-07-20, one arc, C1–C6: layout `510e86a` · z `f6b67a1` · web chrome `85602d1` · posture `b976739` · click pass `7605f1e`). Gates: adr466 39/39 · adr471_canvas 5/5 · adr461/462/chrome/layout/retrofit/drag/save/citation all green · `next build` clean. The click-pass confirm ran **11/11** live at the real authoring profile (`docs/evaluations/2026-07-20-canvas-click-pass/`). Next per the implementation plan: Phase 2 — ADR-427 Ph2–3 + GC, as its own dedicated arc.
> **Date**: 2026-07-20
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Substrate** (a new layout in the artifact grammar) with a **Channel** consequence (the staged editor mode) and a **Mechanism** note (the object layer generalizes, no new machinery).

**Extends**: [ADR-466](ADR-466-the-mode-native-carve-one-grammar-n-native-editors.md) (one grammar, N native editors — canvas is the next mode-native editor over the shipped object layer) · [ADR-468](ADR-468-images-decomposed-generation-on-a-layered-object-substrate.md) (the IMAGES direction; this is its WS-A) · [ADR-461](ADR-461-geometry.md)/[ADR-453](ADR-453-the-property-layer.md) (measures + tokens).
**Amends**: **ADR-468 §8's step order** — the canvas mode (object core) ships *quietly inside Studio* first, making no AI-native promise; `/images` unveils only when decomposed generation works (the D1 name-rule kept by construction). Ratified in the 2026-07-20 scoping discourse.
**Preserves**: ADR-457 P1 (no media promises before ADR-427 Ph2–3 — a canvas with text/shape/upload-cited leaves makes none); the kernel/skin cascade (ADR-453); the ADR-440 D5 citation model.

## Context

ADR-468 scoped an object-layered canvas as IMAGES-side work. The ADR-466 arc landed the object layer inside Studio the same week: positioned blocks (`data-x/y` + `--yx/--yy`), the manipulation chrome (bounding box, drag, resize), and — decisively — gates that key on the **DOM frame** (`positionable = closest('.slide')`, `projection.ts:2111-2113`), not the deck template. The kernel position rule is likewise `.slide`-scoped (`studio.py:998-1000`). A canvas whose artboard carries the `.slide` class therefore inherits the entire object layer. This ADR names the five decisions that make that inheritance deliberate rather than accidental.

## D-a — The artboard IS a `.slide`

The canvas layout's page element is `<section class="slide" data-arrange="free">` under `data-template="canvas"`. One stage concept, one frame class: the kernel position/size selectors, the chrome's positionable/measurable gates, and the empty-slot affordances all activate with zero new selectors. A parallel "canvas frame" class + duplicate selectors would be a Singular-Implementation violation for no gain.

**Corollary — the measure grain is redefined, not widened.** `block-deck`'s meaning becomes "a block on a **staged frame** (the `.slide` class — a deck slide or a canvas artboard)". The string stays (FE matches unbroken); the comment and the gate's falsifier update. No `block-canvas` grain: the frame class IS the grain's boundary, and two names for one boundary is drift waiting to happen.

## D-b — Canvas is `mode: "paged"`; pages are ARTBOARDS

The navigator strip, the New-‹noun› gallery, and nav behavior all derive from the served `mode` (ADR-466's seam). Canvas takes `paged` and names its unit **artboard** — multi-artboard canvases (Canva's pages) arrive free of new machinery.

## D-c — Aspect is a root token

`data-aspect` on the artifact root — absence = square (default by omission, the align lesson) · `wide` (16:9) · `portrait` (4:5) · `story` (9:16) — mapped to `--stage-aspect` by enumerated selectors in the **canvas skin** (the marker-attribute + custom-property split the measures already use). Values are **slugs, not ratio strings**: the ADR-461 gate's rule (every token value enumerable; typed/continuous values belong to a measure) bit on `"16:9"` during implementation, correctly, and the values conformed. The artboard reads `aspect-ratio: var(--stage-aspect, 1/1)`. Deck keeps its hardcoded 16:9 — that ratio is deck's identity, not a preference. Served through the existing token registry with grain `document-canvas` (the `document-flow`/`document-deck` layout-scoped precedent), so the Design-tab picker appears only on a canvas with zero new FE control code.

## D-d — Z earns its token

A new measure `z` (`data-z` marker + `--yz` value, integer 0–20): `.slide [data-block][data-z] { z-index: var(--yz, auto); }` beside the position rule; `STUDIO_KERNEL_CSS_VERSION` → 11 so the retrofit lights it up everywhere (positioned deck blocks included). `StudioBlockMenu`'s own comment ("z-order arrives with a token, if it ever earns one") is the pre-written justification — overlapping composed visuals are the earning. Bring forward/backward become honest verbs on positioned blocks; on a non-positioned block `z-index` is inert by CSS, which is the fallback philosophy working (a garbage measure degrades to natural behavior, never breakage).

## D-e — Everything-positioned is a CONVENTION, not an enforcement

The canvas posture instructs the lane to position every block; the scaffold starts positioned to teach by example; the member's chrome positions by drag. A flow block on a canvas degrades gracefully via the kernel's `var(…, auto)` fallback. No validation machinery — the grammar teaches, it never rejects (the shipped block-grammar's own rule).

## What this deliberately does not do

No generation (ADR-427 Ph2–3 then WS-C); no `/images` surface (WS-D, unveil-gated); no raster deep-end (ADR-468 D6); no new chrome primitives (the object layer is inherited, and where it falls short the finding routes through a click pass, not speculation).

## The one-line statement

**Canvas is the next mode-native editor over the grammar Studio already ships: its artboard is a `.slide` (so the object layer is inherited, not rebuilt), its pages are artboards, its aspect is a root token, z finally earns its measure, and everything-positioned is taught by posture and scaffold rather than enforced — a composed-visuals mode that lands quietly in Studio while the substrate and generation arcs earn the IMAGES name.**
