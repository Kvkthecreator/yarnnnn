# ADR-475 — Decomposed generation: one prompt becomes a composition

> **Status**: **Implemented** (2026-07-21) — the workflow, the seams, and render-to-raster are on main (`82012cd`, `9974c12`). The generation engine is a **deliberate stub**; wiring a vendor is a follow-on with its own key/cost/CHANGELOG discipline (§8).
> **Date**: 2026-07-21
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Mechanism** (Axiom 5 — rented generation, decomposed per object) with a **Substrate** spine (the composition and its leaves are attributed revisions) and a **Channel** consequence (the raster is a derivation that stays in the system).

**Fulfills**:
- [ADR-468](ADR-468-images-decomposed-generation-on-a-layered-object-substrate.md) **D3 + D4** — the decomposition workflow and the cut-out/provenance contract. ADR-468 ratified the direction and staged the build behind ADR-427 Ph2–3; those shipped 2026-07-20, and this is the build.
- [ADR-472](ADR-472-images-as-a-first-class-app.md) **D4 + D5 + D6** — the composition→raster model, the `RenderBackend` seam, and the forcing-function discipline that shaped this ADR's *sequence*.

**Preserves** (load-bearing, untouched):
- [ADR-417](ADR-417-retire-the-render-service-generation-is-rented-not-owned.md) — **generation is rented, not owned.** Both engines here are driver seams; yarnnn hosts no generation or rendering service.
- [ADR-467](ADR-467-app-residency-and-the-cast.md) **D4** — the uniform lane surface. No `GenerateImage` verb was added (§4).
- [ADR-427](ADR-427-binary-native-substrate-and-the-storage-seam.md) — binary as Category-1 substrate; every generated leaf and every raster is a CAS-backed attributed revision.
- [ADR-456](ADR-456-the-studio-horizon-markdown-ruling-builder-grammar.md) — a projection is never a second source. Applied twice here (§5).
- [ADR-472](ADR-472-images-as-a-first-class-app.md) **D2** — the shared object layer. IMAGES consumes `block-staged`; it forks nothing.

---

## 1. Context

ADR-468 named decomposed generation as the reason IMAGES exists: *one prompt does not generate one image — it generates a composition.* It ratified the direction and deliberately did not start the build, gating the generation half on ADR-427 Phases 2–3. Those landed on 2026-07-20. ADR-472 then carved IMAGES into its own app and, in D6, set the discipline for this work:

> Decomposed generation drives the object model, not the reverse. Sequence: carve the housing → dimensions-first creation → **the first real generated ad** → let what it needed define the layer semantics.

This ADR records what that ad needed. It is written *after* the build, which is the point.

## 2. D1 — The workflow, as built

Four steps (ADR-468 D3), one act:

1. **Decompose** — a brief becomes a named layer plan. Two paths, one shape out: `plan_layers` (the resident's judgment) and `heuristic_plan` (deterministic, no model, no network). Everything downstream is blind to which ran.
2. **Route by kind** — three rules, ordered by cost: `text` → a real text block, never raster · `surface` → CSS/SVG where expressible, generated raster only where not · `subject` → a generated cut-out.
3. **Generate per object** — one rented call per raster leaf. The `GenerationBackend` interface is per-leaf on purpose: a driver that could only produce whole compositions cannot satisfy it.
4. **Compose** — the layers land as positioned blocks on the staged frame, carrying the shared object layer's measures.

Modules: `services/images/{stage,generate,decompose,compose,render}.py`. Endpoints: `POST /api/images/compose`, `POST /api/images/render`.

## 3. D2 — The object tree IS the plan (no plan format)

ADR-468 D3 requires the layer plan to be "legible, member-visible work, not hidden orchestration." That promise is kept **structurally**: decomposition returns layers, composition turns them into markup, and the markup is the only artifact. There is no plan document, nothing to keep in sync, and nothing to drift — the alternative was already ruled out by ADR-456 (a projection must never become a second source).

Concretely, `Layer` is an in-flight TypedDict between two function calls. It is never persisted, served, or round-tripped.

## 4. D3 — Composition is a server-side act, not a lane tool

ADR-467 D4 retired per-agent `tools` and made the lane surface uniform: every lane gets the same five verbs plus the shared extras, and per-agent reach is unrepresentable. A `GenerateImage` verb only Designer-in-IMAGES could meaningfully use would re-open that settlement one week after it closed.

**Decision: composition and rendering are HTTP acts on the app's own surface**, which is where ADR-472 D5 had already put rendering. The member invokes them; a lane can invoke them the same way; and the lane still edits the result with the five verbs it always had. No new primitive, no gate change, no allowlist variance.

## 5. D4 — What the first ad actually taught

This is the section ADR-472 D6 exists to produce. The first composed ad (`"a launch ad for our vitamin C serum: bright, clinical, confident"`, a 1200×628 Meta link ad) produced five correctly-placed layers, **two of which rendered as nothing.**

### The zero-height collapse

The kernel's measure rule is `height: var(--yh, auto)`. On an **absolutely-positioned, empty** element, `auto` computes to **zero**. A background `<div>` and a cut-out `<figure>` have no text to give them intrinsic height, so without an `h` measure they are placed perfectly and paint nothing. Browser-measured, both ways:

| layer | without `h` | with `h` |
|---|---|---|
| background | **756×0** | 756×396 |
| subject | **454×51** (the alt-text line) | 454×229 |

This is a property of **leaving the flow**, not a kernel defect: a block *in* flow gets height from content, and these have none. The fix is therefore in the plan, not the kernel.

**Ratified**: non-text layers carry `h`; text layers do not (their content is their height, and pinning it clips a wrapped headline). Enforced in three places — the heuristic geometry, the resident's prompt, and `_coerce`, which **backfills** it. The backfill is the load-bearing one: a prompt instruction is a request, and *a composition that silently renders nothing is the worst failure this app has, because it looks like it worked.*

### Two smaller findings, recorded honestly

- **A CSS surface is a `figure` block with no `img`.** The kernel's figure grammar assumes an image child; a wash stretches it. It composes correctly today (the `img` rules simply don't match), but the block-kind vocabulary may want a `surface` kind of its own. **Not taken here** — one ad is not enough evidence to add a kind, and D6's discipline cuts both ways.
- **The heuristic's copy is a literal echo of the brief.** Deliberate: a mechanical decomposition has no business inventing marketing prose, and an honest echo beats a plausible-sounding line the member did not ask for. The copy-writing is the resident's job, which is exactly the seam between `heuristic_plan` and `plan_layers`.

## 6. D5 — The raster is a derivation, not an export

`POST /api/images/render` writes the PNG as a first-class revision carrying `revision_kind="derivation"` ([ADR-423](ADR-423-revision-kind-the-observation-derivation-flag.md)) and `derived_from=[stage_path]` ([ADR-448](ADR-448-the-reference-edge-derived-from-on-the-ledger.md)). So `trace` walks an exported ad back to the composition and the revision that produced it, and `list_dependents` knows the ad was made from the stage.

This is the claim no design tool can make: in every one of them, export is a dead end. **Rendering is server-side** (ADR-472 D5) because bytes produced on an unattested client make the derivation a *claim* rather than a *fact* — provenance is the moat, so the raster is produced where it can be attested.

The engine is rented: `RenderBackend`, first driver a headless browser the platform already has (nothing hosted, nothing operated, gone after each render). A hosted-API driver is a config swap.

**Citations resolve to data URIs before rasterizing** — `data-ref` values are substrate keys, not URLs, and the renderer holds no session. That projection is never written back (ADR-456, applied a second time).

## 7. D6 — The engine is stubbed, deliberately

The default `GenerationBackend` is `StubBackend`: deterministic, offline, free, emitting a real PNG whose hue derives from the prompt. It is **not pretending to be an image model** — a placeholder that looked generated would make the first ad's reading dishonest; one that looks like a placeholder keeps attention on the composition.

Three reasons this is the right default *for this commit*:
1. D6 says the ad must drive the object model; a vendor's prompt-engineering would contaminate that reading.
2. The gate asserts composition shape without a billable call.
3. Determinism makes the CAS dedup property observable.

**The standing default when a vendor is wired remains Gemini image generation** (ADR-468 §Preserves; `google-genai` is already vendored). Swapping the driver changes the bytes at the leaves and nothing else about the composition.

## 8. Falsifiers

1. **Decomposition quality** — if routine briefs produce layer plans members immediately flatten, D3's workflow is wrong and the one-leaf fallback (ADR-468 D4) becomes the default. *Not yet testable: the stub cannot produce a good ad, only a correctly-composed one.*
2. **The `h` rule generalizes** — if a real resident-authored plan wants a content-sized non-text layer (a shape that hugs its SVG), the backfill is too blunt and the rule needs a third state. One ad is one data point.
3. **Per-object economics** — if N rented calls per composition costs materially more than one flat generation for comparable output, D3's per-object routing is an expensive principle and the surface/text rules (which rent nothing) are doing the real work.

## 9. What is NOT decided here

- **The vendor.** No key, no cost model, no CHANGELOG entry. Its own commit.
- **The role vocabulary.** `KNOWN_ROLES` is a vocabulary, not an enum — an unrecognized role composes fine. D6 says the set falls out of real ads; five layers from one ad is not that evidence.
- **A `surface` block kind.** §5 records the pressure; the change waits for more than one instance.
- **Per-object regeneration UX.** The substrate supports it today (the prompt is on the leaf, the leaf is its own revision chain). The affordance is FE work, unscoped.

## The one-line statement

**A brief decomposes into a named, legible layer plan — text as real text, washes as CSS that rents nothing, subjects as per-object rented cut-outs carrying their own generation provenance — landing as N+1 attributed revisions whose composition is the source and whose raster is a derivation that can be traced back to it; the engine is stubbed on purpose so the first real ad could drive the object model, and what it drove was the discovery that a positioned empty layer without a height measure is placed perfectly and paints nothing.**
