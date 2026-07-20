# IMAGES — the build scoping (post-Designer-pass, post-ADR-466-object-layer)

> **Status**: Scoping discourse (2026-07-20). ADR-468 ratified the *direction*; this doc scopes the *build* against the codebase as it stands today — which moved under the ADR within days of its drafting. One recommendation + three operator questions at the end.
> **Companions**: [ADR-468](../adr/ADR-468-images-decomposed-generation-on-a-layered-object-substrate.md) (the direction) · [ADR-467](../adr/ADR-467-app-residency-and-the-cast.md) (residency; Designer is the resident-on-arrival) · [ADR-427](../adr/ADR-427-binary-native-substrate-and-the-storage-seam.md) (the substrate gate) · [ADR-466](../adr/ADR-466-the-mode-native-carve-one-grammar-n-native-editors.md) (the object layer that changed this scoping) · the Designer click pass (`docs/evaluations/2026-07-20-designer-click-pass/`).

## 1. What changed since ADR-468 was drafted — the scoping's headline

ADR-468 assumed the object core (layers, positioning, direct manipulation) was IMAGES-side work to build. **The ADR-466 arc landed most of it, inside Studio, the same week:**

- **Positioned objects exist.** P5: a block you can pick up and place inside its frame — `data-x/y` + `--yx/--yy` measures (kernel v10), member-authored geometry the lane must preserve (and the Designer click pass *observed* being preserved under a live edit).
- **The manipulation chrome exists.** P8: a PowerPoint/Fabric-grammar bounding box, drag grip, resize handles, optimistic pixels ("pixels never wait for the network").
- **Raster-at-leaves exists in the grammar.** `figure`/`gallery`/`chart` blocks already carry `<img data-ref="…" data-ref-rev="…">`; hero backgrounds cite via `data-ref-kind="background"`. The ADR-468 D2 leaf model is not a design — it is the shipped convention.
- **The frame for N editors exists.** ADR-466's thesis is literally "one grammar, N native editors" — deck is already the object-first editor. A canvas is the *next mode-native editor*, not a new machinery.

**Consequence: the IMAGES *object core* is a small delta, not a workstream.** The genuinely unbuilt halves are (a) the binary substrate (ADR-427 Ph2–3 + GC) and (b) the generation workflow (decompose → per-object rented calls → cut-outs → provenance). The scoping below reflects that inversion.

## 2. The four workstreams

### WS-A — The canvas mode (small; unblocked today)

A `canvas` layout in the shared grammar (`build_skeleton` family): **one fixed-aspect stage where every block is positioned** — the deck slide's positioned-state generalized to "everything is an object," aspect selectable (1:1 · 16:9 · 4:5 · story), no flow. Blocks are the existing kinds (heading, figure, shape-ish SVG leaf, callout); arrangement = free (the stage IS the arrangement); tokens + design-system skin apply as today. Upload-based raster leaves ride the existing `figure` + ADR-395 path. The ADR-466 object chrome works on it because it works on positioned blocks, not on decks.

Effort class: the smallest of the four. Reuses skeleton machinery, measures, chrome, tokens, `data-ref` model. New: the layout entry + its arrangement grammar + a `z`-order measure (the one object property decks haven't needed yet — `data-z`/`--yz`, same kernel-v10 shape).

### WS-B — The binary substrate (ADR-427 Ph2–3 + GC; the critical path)

Per the ADR's own sequencing (§10), executed as one unit per ADR-457 P1:

- **Ph2 — binary as Category-1**: `write_revision` accepts a binary stream; parent-pointers + attribution + ADR-406 linearity for binary; `blob_sha` authoritative; `content_url` becomes a minted response field; `content_type` derived-never-stored; **the 52-site `.content`-reader classification pass + ratchet** (the ADR's own correction E — the real risk surface; a binary row's `content` is empty and 30+ files read it).
- **Ph3 — media intake + serving**: conformance-DAG check replaces the upload cap + stored-MIME gate; range-read/resumable-write implementation; per-request LFS-batch URLs. Gate: a real image uploads, versions, streams, serves.
- **GC**: pins-as-GC-roots (`data-ref`/`data-ref-rev` + derived_from edges as the root set), deletes reclaim, the 34,698 orphan blobs swept. Named by ADR-457 P1 as part of this unit.

Effort class: the largest and riskiest (the reader-classification pass touches 30+ files). Nothing else on this page unblocks generation without it. **It is also not IMAGES-specific** — it unblocks media in chat attachments-as-substrate, uploads at scale, and the ADR-457 D7 P1 debt generally.

### WS-C — The generation workflow (gated on WS-B; the app's soul)

The ADR-468 D3/D4 contract made concrete:

- **A `GenerateImage` primitive** — a rented provider call (default per prior direction: Gemini image, free-tier-friendly) whose *result settles as an attributed asset file* (`assets/` beside the artifact, `member:{id} via {model}`) and returns the path for citation. It is a producer verb (WriteFile-class, commons-internal — not an outward write; the ADR-463 cliff is untouched). Under ADR-467's uniformity discipline, if it joins the lane surface it joins *uniformly* — every colleague can make an image; character decides who does it well. Metered like any judgment call.
- **The cut-out contract**: subject generations request isolated subjects; a rented matting step where the provider can't deliver transparency. Provider chain = implementation, chosen at build time against reliability/cost (falsifier 2 of ADR-468 §9).
- **Provenance**: `data-gen-prompt`/`data-gen-model` (+ params) on the citing element; re-roll = new asset revision, same object.
- **The decomposition discipline** lives in the *canvas job posture* (WS-A's posture section, extended): one prompt → named layer plan → route by kind (text→text, shape→SVG/CSS, subject→cut-out leaf) → compose. The Designer click pass gives confidence the posture layer steers reliably (one line moved observed behavior from invent to recall); the decompose discipline is the same mechanism with a bigger job.

### WS-D — The /images surface (thin; ships when the name is earned)

The surface shell: route `/images`, the canvas-mode editor full-frame, `AUTHORING_APPS.images = { resident: 'designer' }` (the ADR-467 declaration's second row), LaunchServices routing for image-led artifacts (ADR-451 pattern). Thin *because* WS-A/C carry the substance — the surface is presentation + entry points (New canvas · from-prompt · from-upload).

## 3. The sequencing recommendation (one honest change to ADR-468 §8)

ADR-468 §8 staged: 427 → IMAGES v1 (object core + uploads) → generation. With WS-A now small, a cleaner order **preserves D1 (the name demands AI-native in full) structurally**:

1. **WS-A now** — the canvas layout ships *quietly inside Studio* (a layout, like deck/document/article). It makes no AI-native promise: Studio's name carries decks and documents; a canvas layout is just composition. It validates the object grammar with real use while the substrate work runs.
2. **WS-B next** — ADR-427 Ph2–3 + GC, the critical path, started as its own arc (it is bigger than everything else combined and serves the whole OS, not just IMAGES).
3. **WS-C** — generation on the landed substrate; the canvas posture gains the decompose section; `GenerateImage` + cut-outs + provenance.
4. **WS-D last** — **/images opens only when decomposed generation works.** The app named IMAGES never exists in a non-AI-native state; the D1 promise is kept by construction rather than by roadmap discipline.

This inverts nothing ratified — it moves the *surface unveil* after the *soul*, which D1 arguably already demanded, and it was un-seeable before ADR-466 shrank WS-A.

## 4. Designer considerations (the resident, post-pass)

- **Character: no change.** The pass just hardened it; the grounding line (recall-before-inventing on settled territory) applies verbatim to canvas work — brand colors, product naming, positioning in a marketing visual are exactly "settled territory."
- **The job posture is where IMAGES lands.** As with Studio (thin character + rich job overlay, all disciplines observed holding), the canvas mode ships a job posture: stage grammar, object routing, measure/z discipline, citation + generation provenance, decompose-then-compose. The click-pass harness (`docs/evaluations/2026-07-20-designer-click-pass/harness_bound_turn.py`) adapts directly as the canvas pass's step-4 instrument — run it against the canvas skeleton before and after the posture lands (the worksheet procedure, third application).
- **Dual residency arrives with WS-D**: `images → designer`, one declaration row, per ADR-467.

## 5. Open questions (operator's to rule)

1. **The unveil rule (§3)**: agree that /images opens only when generation works, with the canvas layout shipping quietly in Studio first? (My recommendation; it re-orders ADR-468 §8's ③/④ and would be recorded as an amendment note on the ADR.)
2. **WS-B start**: is ADR-427 Ph2–3 + GC the next *arc* after WS-A (it is the critical path for IMAGES *and* the standing ADR-457 D7 P1 debt)? It is the one workstream that needs dedicated sessions rather than riding alongside.
3. **`GenerateImage` uniformity**: when WS-C lands, does image generation join the lane surface uniformly (every colleague can generate; character differentiates — the ADR-467 D4 discipline applied to a producer verb), or bound-canvas-only? (Uniform is my lean; decide at WS-C, flagged now so the ADR that lands the primitive argues it explicitly.)

## 6. One-line statement

**ADR-466 quietly built most of IMAGES' object core inside Studio, so the scoping inverts: a small canvas mode ships now in shared machinery, the real arcs are the binary substrate (ADR-427 Ph2–3 + GC, the critical path) and the decomposed-generation workflow on top of it, and the /images surface — Designer resident, one declaration row — unveils last, so the app named IMAGES is AI-native from its first pixel.**
