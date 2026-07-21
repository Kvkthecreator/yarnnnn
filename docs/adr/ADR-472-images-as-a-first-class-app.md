# ADR-472: IMAGES as a First-Class App — the Housing Carve and the Composition→Raster Model

> **Status**: **Accepted** (2026-07-20) — operator-ratified with implementation delegated in full. Supersedes [ADR-471](ADR-471-the-canvas-layout.md)'s housing decision (canvas as a Studio layout); preserves ADR-471's object-layer inheritance thesis by *promoting* it to a shared kernel rather than discarding it.
> **Date**: 2026-07-20
> **Dimension**: **Channel** (Axiom 6 — which app the operator is in) primary; **Substrate** (Axiom 1 — the composition/raster relationship) secondary.
> **Relates to**: ADR-468 (IMAGES named as the 2nd authoring app — this fulfills D1), ADR-471 (canvas Phase 1, housing superseded), ADR-436 (the app registry / LaunchServices), ADR-440 (app + bound lane), ADR-427 (binary as a Category-1 revision — the render target), ADR-448 (`derived_from` — the raster's provenance), ADR-417 (generation is rented, not owned — §6 engages this), ADR-467 (residency — Designer is dual-resident), ADR-466/461 (the object layer being extracted).

---

## 1. Context — the operator saw the seam

IMAGES Phase 1 (ADR-471) shipped the canvas as the **fifth layout inside Studio** — an artboard that is literally `<section class="slide">`, chosen so the ADR-466 object layer (bounding box, drag, resize, z-order) came for free. That was the right call to ship P1 quickly, and the ADR named the extraction as deferred to P4 step 0.

The operator hit it earlier than P4, from the product side (2026-07-20, on a live canvas at `?studio.file=operation/untitled-canvas/canvas.html`):

> "i thought images was a different APP altogether, right now i see canvas as a document type (at least in flow or front end surfacing), and thus my expected flow was that it was a parallel surface, with its own docker and launcher icons and redirects to and also pure to that backend as well."

And, separately, on the build-up:

> "if we take the canva and fabric js like considerations, we need to start with dimensions or layouts, than, we should have a prompt customization of multiple layered objects that reverse engineers what if you imagine a marketing ad would need, like product hero, background, copy (multiple), etc."

Both observations are correct and are confirmed by the code. The nesting is not merely a front-end surfacing artifact — it is structural at every layer (§2).

## 2. The receipts — what "nested" actually means today

| Layer | State | Evidence |
|---|---|---|
| Backend | `canvas` is the 5th key of `STUDIO_LAYOUTS` | `api/services/studio.py:335-378` |
| Surface registry | one `studio` slug, route `/studio`; **no `images` surface** | `api/services/kernel_surfaces.py:261,269` |
| Dock / launcher | no IMAGES icon — it is unreachable except through Studio | (absence) |
| App registry | 7 rows, **all passive viewers**; no authoring app is registered at all | `web/lib/file-types/apps.tsx` |
| Artboard identity | the artboard IS a deck slide (`class="slide"`) | `api/services/studio.py:373`, ADR-471 D-a |
| Geometry | canvas positioning rides the grain **`block-deck`** — there is no `block-canvas` | `api/services/studio.py:940-993, 994-1000` |
| Dimensions | aspect is an enumerated **slug** (`wide`/`portrait`/`story`), not a dimension | `api/services/studio.py:864-882` |

The last two rows are the load-bearing findings. They are why this ADR is a *carve plus a kernel extraction*, not a file move (§5).

## 3. First principles — what distinguishes IMAGES from Studio

The decisive question is not "canvas vs document." It is **what is the artifact, and what does the system own?**

- **Studio's artifact is the file.** A `.html` deck or doc *is* the deliverable — printed, shared, opened. The HTML is authoritative (ADR-456: markdown is a projection, never a second source).
- **IMAGES' artifact is a rendered raster.** A marketing ad ends life as a 1080×1080 PNG in an ad platform, a DM, a post. **Nobody consumes the HTML.**

That difference cascades through all four layers of the authoring loop:

| Layer | Studio | IMAGES |
|---|---|---|
| Input | a caret, one block at a time | **a prompt emitting N placed objects at once** |
| Geometry | flow, with position as an override | **a bounded coordinate space; dimensions first** |
| Object model | blocks in a document | **layers on a stage** |
| Output | the file is the artifact | **a derived raster; the composition is the source** |

Three of the four diverge. What genuinely converges is the *middle* — direct manipulation of objects. That is exactly the boundary the carve must cut along (§5).

### 3a. The relationship IMAGES needs, which Studio does not have

If the deliverable is a raster, the composition is a **source** and the PNG is a **derivation**. yarnnn already owns that relationship precisely:

- `derived_from` on the ledger (ADR-448) — the reference edge
- `revision_kind='derivation'` (ADR-423)
- **binary as a first-class Category-1 revision** (ADR-427 Phases 2–3, Implemented 2026-07-20)

Studio has no concept of "export produces a new attributed substrate object" — its export is `Print / PDF…`, a browser affordance that *leaves* the system. IMAGES' central act is the thing Studio's model structurally lacks: **composition → rendered raster → attributed revision → citable, traceable, re-derivable.** ADR-427 is therefore not merely IMAGES' unblocker; it is IMAGES' foundation.

## 4. Decisions

### D1 — IMAGES is a first-class app with its own housing, front and back

A parallel surface, not a Studio layout:

- **Surface**: `slug: images`, `route: /images`, `launcher_tier: primary`, its own dock icon (ADR-297 surface registry).
- **Backend**: `api/services/images.py` (the composition kernel: stages, layers, scaffolds, the render contract) + `api/routes/images.py`. Studio's modules stop knowing the word `canvas`.
- **App registry**: IMAGES registers as an authoring app (ADR-436 row shape), alongside Studio.
- **Residency**: Designer is dual-resident (Studio + IMAGES), per ADR-467/468.

The name is load-bearing: it was named IMAGES because the point is image *generation*. The housing must match the artifact.

### D2 — The object layer is EXTRACTED to a shared kernel, never forked, never left behind

**This is the decision the coupling audit forced.** Canvas's whole positioning capability (`x`/`y`/`z`/`w`/`h`) is delivered under a grain literally named **`block-deck`**, with the `.slide` frame class as its boundary. A grep-for-`canvas` extraction would move the layout, the arrangement, and the aspect token, and leave IMAGES with artboards on which **nothing can be positioned**.

Therefore:

- The staged-frame object layer (frame class, geometry measures, the kernel CSS position/size/stack rules, the auto-fit) becomes a **shared kernel both apps consume** — `api/services/staged_frame.py` on the backend, and the existing shared `projection.ts` runtime on the FE.
- The grain is **renamed `block-deck` → `block-staged`** (Singular Implementation: one true name; `block-deck` is deleted, not aliased). ADR-471 D-a already *redefined* the string to mean "a block on a staged frame" while keeping the misleading name for FE compat — this ADR pays that debt rather than exporting it into a second app.
- Studio keeps consuming the kernel for `deck`. IMAGES consumes it for stages. **One implementation, two consumers.**

### D3 — Dimensions are first-class and REAL; the aspect slug token is deleted

Creation in IMAGES begins with the stage's dimensions (the Canva/Fabric model), not with a heading that later acquires a ratio. Concretely: a new image is born as a **W×H stage in pixels** (with named presets — Square 1080×1080, Story 1080×1920, Wide 1600×900, Ad 1200×628, plus custom).

The ADR-471 `aspect` token (`wide`/`portrait`/`story` slugs, scoped `document-canvas`) is **deleted, not carried over**. It existed because ADR-461's token gate requires every token value be enumerable — a real dimension is a continuous typed value, which that grammar structurally cannot express. Dimensions live on the stage as data, not as a property token. This removes the dual approach rather than porting it.

### D4 — The composition is the source; the raster is an attributed derivation

Rendering is a **first-class act that writes substrate**, not an export that leaves:

`render(composition) → PNG bytes → write_revision(content_bytes=…, revision_kind='derivation', derived_from=[composition_path])`

Every rendered image is thereby content-addressed, attributed, traceable (`trace` shows which composition and which revision produced it), and re-derivable. This is the differentiator no design tool has, and it is the reason ADR-427 had to land first.

### D5 — Rendering is SERVER-SIDE, and this narrows ADR-417 without reversing it

ADR-417 retired the render service on the principle **"generation is rented, not owned."** Client-side rasterization (DOM→PNG in the browser) would ship faster and keep 417 untouched, but it makes the raster's provenance weak: the bytes are produced on an unattested client, and "this PNG is a derivation of that composition at that revision" becomes a claim rather than a fact.

**Decision: render server-side, and hold ADR-417's principle by renting the engine.** The renderer is a *rented capability* behind a driver seam (the ADR-427 `StorageBackend` precedent), not a yarnnn-owned rendering service:

- The seam is `api/services/images/render.py::RenderBackend` — `render(html, width, height) -> bytes`.
- Driver 1 is a **rented headless-browser API**; a self-hosted driver is a config swap, never a code change.
- yarnnn hosts no rendering engine. 417's principle survives; only its blanket "no server-side raster" consequence is narrowed, and it is narrowed *because* provenance is the moat.

**Scope honesty:** the driver is a seam + contract in this ADR. Wiring a specific vendor is a follow-on with its own key/cost/CHANGELOG discipline — the seam ships now so the substrate shape is right.

> **Correction (2026-07-21, [ADR-475](ADR-475-decomposed-generation.md))**: the paragraph above described `api/services/images/render.py::RenderBackend` in the present tense, but this ADR shipped no such file — D5 was a *specification*, not an implementation. The seam exists as described **since ADR-475** (`9974c12`), at that exact path. The first driver invokes a headless browser the platform already has, which holds ADR-417 in the sense that matters (nothing hosted, nothing operated); a hosted-API driver remains a config swap. Recorded rather than silently fixed, because an ADR that reads as shipped when it is not is the failure mode this correction exists to catch.

### D6 — Decomposed generation drives the object model, not the reverse

The object model must NOT be designed in the abstract and then have generation fitted to it. The forcing-function discipline (ADR-427 §10.5: *you cannot design the type system, grant granularity, or range API in the abstract*) applies here directly.

Sequence: **carve the housing → dimensions-first creation → the first real generated ad → let what it needed define the layer semantics.** A prompt like *"skincare ad, product hero on gradient, headline + subhead + CTA"* must emit N independently-addressable, placed layers; what that concretely requires (cut-out subjects, background/foreground roles, editable copy runs, `data-gen-*` provenance per ADR-468) is settled by building it, then ratified in the IMAGES P3 ADR.

> **Discharged 2026-07-21 by [ADR-475](ADR-475-decomposed-generation.md)** — and it paid immediately. The first ad composed five layers, placed all five correctly, and **rendered two of them as nothing**: a positioned, empty element resolves `height: auto` to zero, so the background and the cut-out were invisible (browser-measured: `756×0` vs `756×396`). That is precisely the class of fact an abstractly-designed object model would have shipped. See ADR-475 §5.

### D7 — Legacy is deleted, never dual-run (the hooks discipline)

No compatibility shim, no aliased grain, no canvas row left in `STUDIO_LAYOUTS` "just in case":

- `STUDIO_LAYOUTS["canvas"]`, `STUDIO_ARRANGEMENTS["canvas"]`, and the `aspect` token are **removed** from Studio.
- `block-deck` is **renamed**, not aliased.
- Duplicated stage-width constants (`CANVAS_STAGE_W`/`DECK_STAGE_W` exist twice — `projection.ts` exports them, `StudioCanvas.tsx` re-declares local copies) are **collapsed to one import**; the audit flagged that a split copy would let fit and render drift with no test catching it.
- `POST /api/studio/artifacts {template:"canvas"}` cleanly rejects (the unknown-layout path already refuses rather than 500ing).
- **Existing canvas artifacts**: the opaque-slug contract (ADR-459 D3) means an already-created canvas keeps its slug and still round-trips. They are migrated to IMAGES stages by a one-shot; any straggler degrades to the document posture rather than crashing. No dual renderer is kept alive to serve them.

## 5. The carve boundary (derived from the coupling audit)

Three categories, from the full audit of every `canvas` coupling:

**(a) Canvas-only → MOVES to IMAGES.** `STUDIO_LAYOUTS["canvas"]` (`studio.py:335-378`) · `STUDIO_ARRANGEMENTS["canvas"]` (`:688-702`) · the `aspect` token (`:864-882`, then deleted per D3) · `CANVAS_STAGE_CSS`/`CANVAS_STAGE_W` (`projection.ts:300-308`) · `isCanvasTpl` (`StudioCanvas.tsx:231`) · the aspect-picker clause (`StudioDesignTab.tsx:356-358`) · `api/test_adr471_canvas.py` (whole file) · the ADR-471 block inside `test_adr466_mode_native.py:251-280`.

**(b) Shared object layer → EXTRACTED to a kernel, consumed by both.** The `.slide` frame class as the grain boundary (`studio.py:949-953`) · the `x`/`y`/`z`/`w`/`h` measures under `block-deck`→`block-staged` (`:940-993`) · `MEASURE_GRAINS` (`:994-1000`) · the kernel CSS `.slide [data-w]`/`[data-h]`/`[data-z]` rules (`:1089-1098, :1204`) · the staged-frame posture prose (`:1494-1499`) · the `isStaged` auto-fit + `effectiveZoom` (`StudioCanvas.tsx:228-262`) · `artifactOps.setGeometry` · the z-order verbs in `StudioBlockMenu`.

**(c) Generic dispatch → the canvas entry is removed, mechanism untouched.** `STUDIO_TEMPLATES` (derived, auto-drops) · `/api/studio/layouts` serializer · the create endpoint's layout lookup · `describe_artifact_kind` · `StudioSurface`'s mode-derived chrome (which is *why* canvas needed almost no FE code, and why its removal is nearly free).

**Explicitly untouched — the word `canvas` is triple-overloaded** and only the doc-type sense moves: `LayoutMode='canvas'|'desktop'` (ADR-358 shell posture), `StudioCanvas.tsx`-as-viewport (the iframe surface for *every* layout), the Files-page Finder background (`CanvasContextMenu`), `ShaderCanvas`, and `mobilePane:'canvas'`.

## 6. Consequences

- **The name becomes true.** IMAGES is an app you launch, not a document you happen to create — matching both the operator's mental model and ADR-468 D1.
- **Studio gets simpler.** It sheds a layout whose grammar never fit it, and its geometry grain finally carries an honest name.
- **The moat extends to visual work.** Every rendered image is an attributed derivation of a cited composition — `trace` works on an ad, not just on a document. This is what ADR-427 bought.
- **The Fabric-class ceiling is unblocked.** Marquee select, snapping, multi-select transforms, cut-out subjects want a scene-graph runtime that would fight Studio's contentEditable DOM-is-the-model (ADR-443/446). In its own app, IMAGES can take that path without destabilizing Studio.
- **Cost paid now, not later.** Five couplings today is a days-scale carve. After decomposed generation and a real dimension model land *inside* Studio, it is a rewrite.

## 7. Sequencing

1. **The kernel extraction** — `block-deck`→`block-staged`, staged-frame module, collapse duplicated stage constants. Studio-only change; gates prove deck is byte-identical.
2. **The housing** — `api/services/images.py` + routes + surface slug + route + dock icon + app-registry row; `canvas` deleted from Studio (D7).
3. **Dimensions-first creation** (D3) — real W×H stages + presets; the aspect token deleted.
4. **The migration one-shot** — existing canvas artifacts → IMAGES stages.
5. **Decomposed generation** (D6) — its own ADR, driven by the first real generated ad.
6. **Render-to-raster** (D4/D5) — the `RenderBackend` seam + the derivation write. ✅ **Shipped 2026-07-21** (ADR-475 D5, `9974c12`): `POST /api/images/render` writes the PNG with `revision_kind="derivation"` + `derived_from=[stage]`, verified end-to-end against real Chrome at the stage's authored 1200×628.

## 8. The one-line statement

**IMAGES stops being a document type inside a text editor and becomes what its name always said it was — an app whose artifact is a rendered raster, whose composition is an attributed source, and whose object layer is a kernel it shares with Studio rather than borrows from it.**
