# ADR-444 — The mechanical layer: an executing toolbar, slide masters, and the two write paths

> **Status**: **Accepted + Implemented** (2026-07-12, operator-corrected same-day as ADR-443). The operator's first-use verdict on the v1.1/443 toolbar was right: **prompt-prefill buttons were a timid half-implementation** ("quick prompt cheats"). This ADR ships what the benchmark class actually does — **selection-aware operations that EXECUTE**: Add inserts a real block at the canvas selection; picking an image inserts a cited figure block; a deck slide's layout is changed from a **container registry** (the slide-master grain). Deterministic member acts, no LLM, one attributed revision each.

**Date**: 2026-07-12
**Amends**: ADR-443 (D2's "TRANSFORM always via lane" splits into two write paths; the layout model gains the container grain) · ADR-440 v1.1 (the prefill strip is superseded; "Open in Files" removed from the bar — unnecessary chrome).
**Preserves**: mutation legibility (every act is an attributed revision); the canvas never edits (the TOOLBAR executes, through the write door); ADR-406 CAS; the powerbox; grammar-not-schema.

## D1 — Two write paths, one substrate

- **The judgment path** (unchanged): the bound lane — content, rewrites, restyles, artifact-level re-layout. Attributed `member:{id} via {model}`, metered.
- **The mechanical path** (new): deterministic structural operations — insert block, insert cited block, add slide, apply slide layout — computed in the FE (`web/components/studio/artifactOps.ts`, pure DOM transforms) and landed through **`POST /studio/artifacts/write`**: region-gated, `authored_by="operator"`, **CAS-guarded** (`expected_parent_version_id`; a stale base 409s and the canvas reloads — a lane write is never clobbered). Attributed to the member, free (no LLM — the ADR-396 mechanical class).
- ADR-443's seven operations stand; what changes is that **COMPOSE and structural TRANSFORM are mechanical by default, judgment on request.** Chart remains the one generative Add (authoring an SVG is judgment).

## D2 — The container grain (slide masters)

`STUDIO_CONTAINERS` joins the kernel registries: per-LAYOUT structural arrangements — deck ships `title · content · two-column · quote` — each a fragment with `data-container` identity and `data-slot` regions. **Apply-to-selected-slide is a deterministic reflow**: existing `[data-block]` elements move INTACT (ids preserved) into the new arrangement's first slot; other slots keep placeholders; the old slide is replaced. Document/article container rows arrive on demand with zero mechanism change. Served with the vocabulary (`GET /studio/vocabulary` now carries `fragment` payloads — the FE executes from the same source the posture teaches from).

## D3 — Selection is held state, and it anchors everything

The canvas selection (`{blockId, blockKind, slideIndex}` — the pointer runtime now reports the enclosing slide's index too, so title slides without blocks still anchor) is surface-held state shown as a **chip in the toolbar**: Add inserts after it, Slide ops target its slide, and the lane hears about it via the visible composer seed. Clear by clicking empty canvas or the chip.

## D4 — Posture note + the concurrency contract

The posture tells the lane that operator-authored structural revisions land between its turns: re-read before editing, treat current content as truth, never renumber ids it didn't create. The CAS door enforces the mirror-image: the member's op 409s if the lane wrote first. Two writers, one path each, no merge — ADR-406 discipline intact.

## Consequences

Positive: the toolbar is real software, not prompt sugar; structural edits are instant, free, and finely attributed ("Studio: add Callout block" / "Studio: change slide layout to Two column" in History); the slide-master registry gives layouts the second grain the operator asked for. Cost: `artifactOps.ts` (+~150 LOC pure functions), one endpoint, the toolbar rewrite. Risk: low — CAS prevents lost updates; ops are pure and reversible (revisions).

## The one-line statement

**Buttons execute: a selection-anchored, CAS-guarded mechanical write path lands deterministic structural operations (blocks, cited inserts, slides, slide-master reflows) as free operator-attributed revisions, while the lane keeps every judgment edit — two write paths, one attributed substrate, and the toolbar stops being a prompt cheat.**
