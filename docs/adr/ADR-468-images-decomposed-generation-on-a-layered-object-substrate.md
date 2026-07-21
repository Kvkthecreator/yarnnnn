# ADR-468 — IMAGES: decomposed generation onto a layered object substrate

> **Status**: **Accepted direction** (2026-07-20, operator-ratified) — **D3 + D4 FULFILLED 2026-07-21 by [ADR-475](ADR-475-decomposed-generation.md)**: the decomposition workflow, the per-object cut-out contract, and `data-gen-*` provenance are built and on main (`82012cd`), together with render-to-raster (`9974c12`). The ADR-427 Ph2–3 gate lifted on 2026-07-20 and the build followed immediately. **The generation ENGINE remains a deliberate stub** (ADR-475 D6) — wiring a vendor (the standing default, Gemini, per §Preserves below) is a follow-on with its own key/cost/CHANGELOG discipline. What the first real ad taught is recorded in ADR-475 §5, not here.
> **D1 FULFILLED 2026-07-20 by [ADR-472](ADR-472-images-as-a-first-class-app.md)**: IMAGES is now a real app — surface `images`, route `/images`, its own dock icon, its own backend module (`api/services/images.py`), its own layouts registered with the shared machinery. ADR-471 had shipped the composition surface as a *Studio layout* ("canvas") with the extraction deferred; the operator hit that seam from the product side the same day and the carve landed immediately. ADR-472 also settles the housing question this ADR left implicit — the object layer is a SHARED kernel (`block-staged`), not forked per app — and adds dimensions-first creation (D3, real W×H) as the honest first decision for a raster artifact. **Still gated**: the generation half (§8), which waits on ADR-427 Ph2–3 (now Implemented) and lands as its own ADR per ADR-472 D6 — decomposed generation drives the object model, not the reverse.
> **Date**: 2026-07-20
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6 — a second authoring app/surface) with a **Substrate** spine (the object document is authored markup on the ledger) and a **Mechanism** consequence (rented generation decomposed into per-object calls).

**Extends**:
- [ADR-440](ADR-440-the-studio-the-first-authoring-app.md) — the second member of the authoring-app class. IMAGES reuses the artifact machinery wholesale: bound lane (D3), settle-then-cite + `data-ref`/`data-ref-rev` (D5), templates-as-skeletons (D4), the five verbs + `EditFile` patch-preference.
- [ADR-436](ADR-436-the-app-registry-frame-agnostic-renderers.md) — a new app id of the ratified row shape; the surface-owning-app pattern (ADR-451) routes its artifact type.
- [ADR-467](ADR-467-app-residency-and-the-cast.md) — the residency rule's first exercise: IMAGES arrives declaring its resident, and it is **Designer** (dual residency; no new agent).

**Preserves** (load-bearing, untouched):
- [ADR-417](ADR-417-render-service-retirement.md) — **generation is rented, not owned.** Every generative call in this app is a provider API call (the standing default: Gemini image generation, free-tier-friendly — the 2026-04 direction, still sound); yarnnn hosts no generation, matting, or rendering engine.
- [ADR-457](ADR-457-think-and-make-the-service-model.md) **P1 + D6** — *"No media promises before ADR-427 Phases 2–3."* The gate stands (§8). The MacWrite/MacPaint doctrine is this ADR's charter — IMAGES is the literal MacPaint seat, taken deliberately.
- [ADR-427](ADR-427-binary-native-substrate-and-the-storage-seam.md) — the storage seam; Phases 2–3 (binary + pins-as-GC-roots) are this app's substrate precondition for the generation half.
- [ADR-443](ADR-443-dom-is-the-model.md) / [ADR-446](ADR-446-direct-edit.md) / [ADR-453](ADR-453-the-property-layer.md) — DOM-is-the-model, edit-projection-write-source, tokens-not-pixels: the three Studio theses this app extends spatially.
- AGENT-TAXONOMY §4 — "a new output shape is a modality *inside* an agent, not an agent."

---

## 1. Context — what the name demands

The operator's naming rule is itself a decision: the app is called **IMAGES**, so everyone inside yarnnn will assume it is AI-native — **and therefore the app must be AI-native in full**, not a manual editor with a generate button. The question this ADR answers is what "AI-native image work" means when the substrate is an attributed commons, and the answer is *not* "call an image model and store the PNG." That is what every chat product does, and its output is an opaque flat raster: no provenance, no per-part edit, "make the background warmer" is a full re-roll.

The benchmark cut is **draw, not paint**. Photoshop's model is raster (pixels; edits destroy information; the document is opaque bytes). Canva/Illustrator's model is an **object model**: a z-ordered tree of named elements — text, shapes, image frames, groups — composed on a canvas. For yarnnn the object model is architecturally loaded, because an object tree can be **structured markup — which means the document IS the substrate**: every edit, human drag or AI instruction, is an attributed revision on the ledger, diffable, traceable, revertible. Canva's AI is bolted onto a proprietary doc. Ours is native because the doc is the thing the lane already knows how to edit.

## 2. D1 — The app is IMAGES; the name is the principle

`IMAGES` — surface `/images`, an authoring app of the ADR-440 class with its own direct-manipulation idioms (select · drag · resize · rotate · z-order · snap/align · group), distinct from Studio's block-document idioms (blocks in flow, caret, gutter). Per ADR-436, the app boundary is the surface + idioms; the machinery beneath is shared. The Keynote to Studio's Pages.

The principle the name carries: **no feature ships in IMAGES that breaks the object-model-as-substrate thesis.** A capability that only works on flattened pixels (and cannot be expressed as an object, a leaf, or a filter on one) is out of scope by default.

## 3. D2 — The document: a layered object tree in authored markup; raster only at the leaves

The IMAGES artifact is an HTML document (SVG primitives as leaf elements where vector shapes want them) of absolutely-positioned, z-ordered, **named** objects — ADR-443's DOM-is-the-model, extended spatially. Concretely:

- **Layers are elements.** Position/size/rotation/opacity/blend ride as the ADR-453 property layer — tokens-not-pixels; the workspace design system applies by construction (brand color/type on a canvas is a token reference, not a baked pixel).
- **Text is text.** Text layers are real text elements — never generated raster type. This is simultaneously the largest quality win (generated in-image type is notoriously broken), the editability win, and the brand win (text wears tokens).
- **Raster exists only at the leaves.** A photo, a generated subject, a textured background — each is a **cited asset** (`data-ref` + `data-ref-rev`, ADR-440 D5): an attributed file in the commons that the object tree references, never inline bytes.
- **Export is a projection.** The member ultimately needs a flat PNG/JPEG for the world; the flat image is **rendered from the tree at export, never a second source** (the ADR-456 md-is-a-projection rule, applied to pixels).

## 4. D3 — Decomposed generation IS the AI-native workflow

The operator's core mechanic, ratified: **one prompt does not generate one image — it generates a composition.** A member asks for "a launch ad: headline, hero shot of the product, warm background" and the bound lane runs the decomposition workflow, *explicit and named*:

1. **Decompose** — the prompt becomes a named layer plan (background · hero-product · headline · logo …). The plan is legible, member-visible work, not hidden orchestration: the object tree *is* the plan.
2. **Route each object by kind**:
   - text → native text objects (D2 — never raster),
   - backgrounds / shapes / gradients / washes → CSS/SVG where expressible; generated raster leaf where not,
   - subjects (product, person, illustration) → **generated cut-outs** (D4).
3. **Generate per object** — one rented call per raster leaf, not one call for the whole canvas.
4. **Compose** — the objects land as the layered document. The output *feels* like one image; it *lands* as individually selectable, resizable, regenerable objects.

The dividend is the moat's, not just the editor's: **"change the headline" is a text edit; "make the background warmer" is a filter-token or a one-leaf re-roll; the hero product survives both untouched.** Every step is an attributed revision; `trace` shows the composition's history per object.

## 5. D4 — The cut-out contract + generation provenance

- **Cut-outs**: a subject leaf is generated *isolated* — the generation contract asks for the subject alone (transparent or chroma-solid ground), followed where needed by a **rented** matting/background-removal step. The specific provider chain is implementation (ADR-417 discipline: yarnnn hosts no matting engine); the contract — *subject leaves arrive as clean cut-outs that compose* — is the decision.
- **Provenance on the element**: every generated leaf carries its generation facts as attributes — the `data-ref` pattern's generation sibling (`data-gen-prompt`, `data-gen-model`, params). Per-object regeneration is thereby native and attributed: re-rolling a leaf is a new asset revision cited by the same object, with the prompt that made it on record.
- **Fallback is never a dead end**: when decomposition isn't warranted (or a model returns one flat result), the result still lands as an object leaf on the canvas — a one-layer composition that can be built on, never an opaque terminal output.

## 6. D5 — The resident is Designer; no new agent

The ADR-467 residency rule's first exercise: IMAGES declares `resident: designer`. Image-making is the same addressed operation — *make* — in a second modality (AGENT-TAXONOMY §4, Axis-1: modality lives inside the agent). Designer holds dual residency (Studio + IMAGES); the Designer hardening pass is thereby shaping the resident of two apps. A dedicated "image agent" would be the deck-agent error in new clothes, and is refused.

## 7. D6 — Scope guard: keep the core, skip the raster deep-end

Core photo operations ship as **leaf-object operations** — crop (frame geometry), adjust/filter (CSS filter tokens on the leaf), replace/regenerate (D4). The raster deep-end — pixel brushes, masks, healing, hand-matting — is **out of scope for v1** and re-enters, if ever, only under the D1 principle (expressible as object/leaf/filter) and demonstrated demand. Less Photoshop, deliberately: the app's bet is that decomposed generation + object editing covers the layman's real jobs (the Canva jobs) without a raster engine.

## 8. D7 — Gates, staging, and the capacity honesty

- **What is NOT gated**: the object core — canvas, text/shape layers, tokens, upload-based raster leaves (uploads already settle via the ADR-395 bucket path), composition, export projection. The document is *text substrate*.
- **What IS gated** (ADR-457 P1, unamended): the **generation half** and heavy raster — generated leaves write binary at scale into a substrate with no binary path and no GC (34,698 orphan blobs; deletes never reclaim). **ADR-427 Phases 2–3 (binary + pins-as-GC-roots) execute first, as one unit.** No media promises before it.
- **Staging**: ① ADR-467's code + the Designer hardening pass (the resident is shaped before its second app exists) → ② ADR-427 Ph2–3 → ③ IMAGES v1 (object core + upload leaves) → ④ the generation workflow (D3/D4). Steps ③/④ are pulled by dogfood demand (the operator's own decks/posts needing composed visuals is the honest wedge), not pushed by the roadmap.
- **Capacity, named honestly**: ADR-457 D6's two-front guard (chat shallow, Studio deep) becomes a **three-front** question. IMAGES is a Studio-scale editor investment; this ADR ratifies the *direction* so the arc stops re-deriving it, and deliberately does **not** start the build.

## 9. Falsifiers (so the bet is checkable)

1. **Decomposition quality**: if routine prompts produce layer plans members immediately flatten or fight (objects mis-cut, composition worse than a one-shot flat image), the D3 workflow is wrong — the fallback (D4, one-leaf landing) becomes the default and IMAGES degrades gracefully toward "generate + arrange," which must still be honest.
2. **Cut-out reliability**: if the rented matting chain cannot produce composable subjects at acceptable cost, D4's contract fails and subject-generation waits for providers that can (the object model loses nothing while waiting).
3. **Residency**: if bound-IMAGES turns show Designer's character failing the modality (make-language that fights spatial work), that is *posture* evidence for the Designer pass — not evidence for a new agent, until an irreducible addressed operation is named.

## The one-line statement

**IMAGES is yarnnn's second authoring app and its MacPaint seat, AI-native by construction rather than by button: one prompt decomposes into an explicit, named layer plan — text as real text, shapes as vectors, subjects as rented-generation cut-outs with per-object provenance — landing not as one opaque raster but as a layered object document on the attributed substrate, where every layer is selectable, editable, and regenerable alone; Designer is its resident (dual residency, no new agent), the object core rides the text substrate today, and the generation half waits — ratified, staged, and honest — behind ADR-427 Phases 2–3.**
