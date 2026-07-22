# ADR-475 — Decomposed generation: one prompt becomes a composition

> **Status**: **Implemented — ENGINE LIVE** (2026-07-21). The workflow, the seams, and render-to-raster are on main (`82012cd`, `9974c12`); the vendor commit landed the same day: **`GeminiBackend`** (direct httpx REST per ADR-076, no new SDK; default model `gemini-2.5-flash-image`, env-overridable via `IMAGES_GENERATION_MODEL`). Resolution is lazy + env-driven: `GEMINI_API_KEY` present → the rented driver; keyless or `IMAGES_GENERATION_ENGINE=stub` → the offline stub (gates stay green with no network). **Every rented leaf is metered**: one `execution_events` row per generated leaf (`slug=images-generate`, `cost_override_usd` — per-image figure, `IMAGES_GENERATION_COST_USD` default $0.08 = 2× list per the platform's standard rate; the free stub ledgers nothing). The cut-out is **prompt-engineered** (subject isolated on a plain white ground — asking image models for "transparent" yields painted checkerboards); true alpha **matting is the named follow-on**, a second rented step behind the same contract. Live-smoked: one real call returned a clean isolated subject (1MB PNG, magic verified). Gate `api/test_adr475_gemini_driver.py` 13/13 (EXECUTING — parse, cutout discipline, aspect mapping, failure shapes, env resolution, per-leaf ledger). Render env: `GEMINI_API_KEY` must be on the API service (human-verify — same var the ADR-408 router uses).
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

## 10. The first live smoke (2026-07-21) — what production taught that the gate could not

The gate was 50/50 green against a fake DB. Then the endpoint ran once on the operator's real workspace with the live Gemini engine, and **four things the gate structurally could not see** surfaced. Recorded here because each is a lesson about where this build's tests end.

### §11 — The privileged writes were using the member's client

Two writes require a service client, and both had the member's:

- **The ledger** — `execution_events` is service-role-only (RLS `42501`). Every other metering site (`lane_runner`, `settle`, `foreign_read`, `session_continuity`) already resolves `get_service_client()`; this module was the lone exception.
- **The leaf** — a binary revision uploads to the *private* `workspace-cas` bucket (ADR-427 D4), which refuses a member JWT with `403 new row violates row-level security policy`. Isolated by probing each surface separately: `workspace_files` and `workspace_blobs` both accept the member (they fail on NOT NULL, not policy). Only the bucket refuses — which is why the failure read as a substrate problem and was not one.

**Consequence:** Gemini generated the images successfully, both writes 403'd, the member saw `generated: 0` and a lighter composition with no error, and was billed **~$0.16 for images that were discarded with no ledger row.** `workspace=None` in the log was the telemetry fail-open catch swallowing the broken client, not a resolution bug.

**Fixed** (`2e4bce1`): `compose_stage` resolves its own service client, lazily (a pure text+CSS composition rents nothing and must not require service credentials to run — eager resolution broke the offline gate). The boundary lives *with* the privileged writes so a caller cannot hand in the wrong client. Both swallowed exceptions became ERRORs that name the money. The gate now records *which client* reached each write — the assertion surface it was missing.

### §12 — Two visual defects, both invisible until a real ad rendered

- **Dark on dark.** Designer opened the first brand ad with `background:#0A0A0F` and expected the text to cope; the artifact inherited the base layout's light-page `--ink:#1a1a1a`, and every text layer rendered `rgb(26,26,26)` — placed perfectly, unreadable. **Fixed** with a declared `data-ground="dark"` on the frame (the ADR-453 property-layer pattern: enumerable, pre-declarable, absence = light) whose value `_ground_of` derives from the full-bleed surface's *perceived luminance* (Rec. 601) when Designer doesn't state it, and always defers to an explicit declaration. Browser-verified: `rgb(26,26,26)` → `rgb(245,245,247)`.
- **The `h` floor is too blunt.** `_coerce` clamped `h` to a 10% minimum, copied from `w` without thinking. Designer's hairline divider and pill badge inflated to 63px slabs on a 628px stage. **A 1%-tall rule is legitimate; a 1%-wide column is not** — the axes honestly differ. The floor is the *kernel's* (`STUDIO_MEASURES["h"].min`, governing Studio decks too), so IMAGES **reads the bound from the kernel rather than forking it**, and lowering it was raised here as a kernel question rather than taken unilaterally in the images path: → *does a staged-frame block's height want a 1% floor where its width wants 10%?* The pill/divider case says yes.

  > **RESOLVED (2026-07-22):** `STUDIO_MEASURES["h"].min` lowered `10 → 1`. `w` stays at 10 (a 1%-wide column is illegible; a 1%-tall rule is not). One kernel value; the FE geometry clamp (`artifactOps.setGeometry`, clamps from the *served* spec) and the IMAGES `_coerce` bound both inherit it — no fork. Studio decks gain the same 1% height floor, which is correct: a hairline horizontal rule is as legitimate on a slide as on a stage. The residual risk (a member fat-fingering a block to near-invisibility) is mitigated by the inspector's own numeric affordances and by undo (⌘Z).

- **A bug I introduced, caught by re-running the real plan.** The `data-ground` edit accidentally fused the subject-prompt guard into an `else`, so a *surface with no ground token fell through the subject branch and was dropped* — and that empty result masked the luminance path (no surface to read → ground came back light). Replaying the exact 11-layer live plan surfaced both at once. This is the forcing-function discipline paying a second time: the unit gate was green; the real composition was not.

### §13 — Render-to-raster: the server path is REMOVED; export is client-side (decided 2026-07-22)

The server rasterizer (`POST /api/images/render`, `render.py`, the `RenderBackend` seam) returned **503** in production — the Render container has no headless browser, so it never once produced a PNG. Rather than install Chrome in the image or rent a screenshot API, the operator's call is that **export is client-side**: the member's browser rasterizes the stage it is already displaying. So the whole server path is **deleted**, not deferred — a broken feature removed beats a broken feature kept returning 503.

**The moat survives the deletion, which is why it is safe.** D5 argued render must be server-side so "this PNG is a derivation of revision X" is a *fact*, not a client's *claim*. But the provenance was always in the **composition**, not the export: `trace` walks the layered, attributed source; the flat PNG is a convenience artifact for the outside world (Instagram does not read our ledger). A client-side download therefore loses nothing the moat depends on. If a member ever wants the *export itself* recorded, the browser can POST the bytes back as a `revision_kind="derivation"` — the same write the server path did, sourced from the client — but that is opt-in, not required, and not built at launch.

**Built (2026-07-22): client-side PNG export, IMAGES only.** The premise that a rasterizer must run *inside* the sandboxed canvas iframe turned out false — the sandbox (`allow-scripts` only) is a boundary the parent cannot reach, but the parent does not need to reach it. Export re-projects the artifact into its OWN off-screen, un-sandboxed container (the exact technique `exportPrint` already uses for Print/PDF: `resolveArtifactHtml` resolves citations and strips executables, then the resolved body is mounted and rasterized). So there is no library inside the runtime and no security-boundary crossing.

The canvas-taint problem is solved without depending on bucket CORS: a cited raster binary resolves to a cross-origin Supabase *signed URL* (`projection.resolveOne`), and drawing a cross-origin image onto a canvas taints it. The export pass **re-fetches every such `<img>`/`background-image` as a blob and swaps it for a same-origin `data:` URI before rasterizing** — a `fetch()` carries the signed URL fine, and a data URI never taints. (SVG/CSV citations already resolve to data URIs upstream.) The rasterizer is `html-to-image` (`toPng`, `pixelRatio: 2` at the stage's `data-w`/`data-h`), dynamically imported so it stays out of the initial bundle. Files: `web/components/workspace/viewers/rasterExport.ts`, wired through `exportVerbs.exportPng` (present only when `app.slug === 'images'`).

Studio decks/documents keep Print/PDF only — a raster of a document is a fuzzier need than of a stage whose whole point is the raster. The **record-the-export-as-a-derivation** path (POST the bytes back as `revision_kind="derivation"`) stays the named opt-in follow-on: not built, because the composition is already the traceable source. The residual honest risk is **fidelity** on gradients / `object-fit` / webfonts — the standing Studio caveat that this pass is owed a human live-click smoke on a real generated ad. **ADR-472 D5's `RenderBackend` seam is withdrawn**; §7 step 6 of ADR-472 is reframed from server-derivation to client-export.

D4's "the raster is an attributed derivation" claim is **preserved in principle** (the composition remains the traceable source; the optional record-the-export path keeps the edge) and **withdrawn in mechanism** (no server rasterizer produces it).

## The one-line statement

**A brief decomposes into a named, legible layer plan — text as real text, washes as CSS that rents nothing, subjects as per-object rented cut-outs carrying their own generation provenance — landing as N+1 attributed revisions whose composition is the source and whose raster is a derivation that can be traced back to it; the engine is stubbed on purpose so the first real ad could drive the object model, and what it drove was the discovery that a positioned empty layer without a height measure is placed perfectly and paints nothing.**
