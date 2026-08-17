# ADR-518: Docs and Studio — the Writing App and the Layout App

> **⚠️ D5 SUPERSEDED by [ADR-574](ADR-574-the-prose-currency-leads-text-is-the-text-app-docs-pauses.md) (2026-08-17)**: the full unveil is **reversed — Docs is PAUSED** to `search-only` and leaves the default Dock (the ADR-488 "hidden, not unplugged" template). **D5's evidence is retired as INAPPLICABLE, not refuted**: the "9 of 18 live artifacts, and the only ones with real authored substance" count was taken over artifacts that are **100% test data**, so it never measured member behaviour and no adoption verdict is claimed. The pause rests on a different measurement entirely — a `document` artifact is **invisible through the interop face** (~24KB of inlined kernel CSS exceeds the 24,000-char MCP read cap before `<body>`; `open` returns `success: true` with zero authored content). **D1–D4, D6 and D7 are UNTOUCHED** — Docs still owns `document`, the machinery stays singular with N consumers, and the app stays registered and routable. Reopening is ADR-574 §5, and only as an outbound Publish surface (D4).

> **Status**: **Accepted** (2026-08-04) — operator-ratified ("let's proceed with this in full"), implementation delegated in full, unveil strategy delegated (decided at D5). Splits the authoring housing along the mode seam; preserves ADR-466's one-grammar ruling by *keeping* the substrate grammar and machinery singular, and giving the two editor families the two app housings they already were.
> **Date**: 2026-08-04
> **Dimension**: **Channel** (Axiom 6 — which app the operator is in) primary; nothing at the Substrate dimension changes (one artifact format, one write door, one revision atom).
> **Relates to**: ADR-472 (the IMAGES carve — the precedent this ADR re-runs), ADR-505 (the three-type set — unchanged, re-housed), ADR-473 (type→app declaration — the mechanism), ADR-440 (Studio the first authoring app — D2's act test re-cut), ADR-466 (one grammar, N native editors — the housings become honest), ADR-480 (editing binds to the medium), ADR-509 (the insert route follows the medium — falsifier 8 is this ADR's cut line), ADR-507 (the acts are open — the growth rule), ADR-467 (residency — Designer becomes triple-resident), ADR-486/488 (the unveil discipline), ADR-514 (Open With — the >1-handler mechanism this split rides).

---

## 1. Context — the operator named the thesis; the audit confirmed it

The operator (2026-08-04): *"there isn't actually one single OS-like program that has it together. it's either Word or PowerPoint, Slides or alike, Notion, etc."* — and asked for a full audit of the mode/document-type separation before deciding.

The audit (canon + code, at 529bc39) returned a stronger form of the thesis: **the split already exists everywhere except the housing.**

- **Canon**: ADR-466's ruling is *"one shared substrate grammar, N mode-native editors over it"* — the editors are already plural; only the app is singular. ADR-480's axiom (*"editing binds to neither file nor structure — it binds to what the medium is"*) makes two media with two editing models two editors **by definition**. The STUDIO.md matrix shows it structurally: deck and web share interaction cells constantly ("✅ as deck"); `document` carries `—` (does not apply) in roughly half the contract.
- **Code**: the backend is registry-driven with essentially no medium branches; `artifactOps.ts` has zero `mode ===` conditionals; `StudioSurface.tsx` is ~90% shared machinery already parameterized by `AuthoringApp` (18 sites, serving Studio and IMAGES). The genuinely dual code is concentrated and cleanly gated (the paged-only runtimes, the navigator's two renderers).
- **Precedent**: ADR-472 ran exactly this carve once (IMAGES), and ADR-486 recorded its lesson as doctrine: *"an app developed inside an existing surface forces a carve later."* Applied to deck-vs-document, ADR-472 §3's four-layer test (input · geometry · object model · output) gives **three-of-four divergence — the same ratio that justified IMAGES**: a caret in a linear flow vs mouse-first objects/bands; no coordinate space vs frame/viewport; annotation-grain vs enclosure-grain blocks. What converges is the substrate — which is exactly what stays shared.

### 1a. The cut line is the mode seam, not Word-vs-PowerPoint

The operator's framing was Word-vs-PowerPoint; the evidence cuts **{document} vs {deck, web}**. `web` is `mode: "paged"` (same as deck); every `isPaged` chrome branch binds web to deck's interaction family; and ADR-509 falsifier 8 states it as gated canon: *"A `web` artifact behaves as `deck` does, not as `document` does."* The operator ratified this cut (2026-08-04): **web stays with deck.** The drift-ledger's §6 observation (deck wants Figma; web wants Wix) remains on the books as a possible *later* carve, taken only if it earns itself — this ADR does not pre-decide it.

## 2. First principles — the value test, answered head-on

`docs/analysis/the-commons-is-the-os-2026-07-09.md` §4 names "a deck editor" as the trap (*"this is how every workspace company dies"*), with the test: *does the app's value come from yarnnn having **built** it, or from yarnnn having **housed** it?*

The answer this ADR gives: **the split adds no editor capability at all.** Both apps are the same shipped machinery over the same substrate; what splits is the housing — which door, which recents, which default handler. The value remains entirely the housed half: attributed revisions, citations, trace, grants, the one write door. ADR-457 D6 (MacWrite/MacPaint — preserved by ADR-507) is the sanctioned frame, and it is telling that the doctrine's own analogy is a *pair* of apps split along precisely this line; the seam analysis' analogy ("the AppKit under Pages and Keynote") is likewise two document apps over one framework. First-party apps teach the platform's idioms; every capability they gain must decompose into kernel ABI + app behavior — and this ADR's entire diff is app-behavior rows over an unchanged ABI.

This also formally closes the drift-ledger's open debt: the ADR-443-era claim that *"a deck is a rendering of a document"* has been eroding since ADR-447 without being withdrawn. **It is withdrawn here.** Decks and documents are not one object composed differently; ADR-480 and ADR-505 already admitted this at the grain and type layers. The housing now says what the system already knows.

## 3. Decisions

### D1 — Two authoring apps over the writing/layout seam: Docs owns `document`; Studio keeps `deck` · `web`

- **Docs** — the writing app. Owns the `document` type (CAPTURE — flow, caret-first, the Notion contract). Route `/docs`, surface slug `docs`, param namespace `docs.file` / `docs.system`.
- **Studio** — the layout app. Keeps `deck` (PRESENT — staged frame, object-first) and `web` (PUBLISH — banded viewport, band-first). Route, slug, params unchanged.

The type set is **still ADR-505's three, one per medium** — no fourth type, nothing renamed, `data-template` values untouched, zero migration (type is derived from content at read time, ADR-473 D1). Only the `app` declaration on the `document` row changes, and the row moves house (D3).

### D2 — The grammar and machinery stay singular; the split is housing only (the anti-fork ruling)

Everything ADR-472 D2 classified as kernel stays one implementation with **three consumers**:

- One substrate format (conventional HTML + the three annotations, ADR-511 D1); one write door (`POST /studio/artifacts/write`); one revision atom (ADR-209).
- One block vocabulary, one token allowlist, one measure set, one kernel CSS, one `setContainerLayout` op (ADR-516 D1), one `normalizeStructure` seam (ADR-511 D5), one projection runtime (`projection.ts` — which also serves the Web Viewer and must never fork), one ops module, one shared surface component.
- The FE housing is **parameterization, not a fork**: `/docs` mounts the same `StudioSurface` with `DOCS_APP`, exactly as `/images` mounts it with `IMAGES_APP`. The `AuthoringApp` contract gains a declared `label`, retiring the hardcoded `app.slug === 'images' ? 'Images' : 'Studio'` ternaries.

The shared machinery keeps its current module homes (`services/studio.py`, `components/studio/*`). The full app-neutral rename ("the grammar extraction", images-implementation-plan P4 step 0) remains named-and-deferred: it is a pure rename with real churn, and this ADR's diff does not get simpler by paying it today. What this ADR does **not** permit is any *new* app-specific behavior landing in the shared modules — the extraction's forcing function only sharpens with a third consumer.

### D3 — The `document` row moves to its own module; registration maintains the scaffold-title set

The app boundary is the **module** (ADR-473 D2, as the `canvas` header comment already states): `api/services/docs.py` holds `DOCS_LAYOUTS` (the `document` row, verbatim, with `"app": "docs"`) and registers it into the shared resolver at import — the exact `services/images/stage.py` pattern. `routes/studio.py` imports it for the registration side-effect, beside `services.images`.

Two shared-machinery facts get honest in the same motion:

- `_SCAFFOLD_TITLES` derived from `STUDIO_LAYOUTS` only — it would lose "Untitled document" on the move, and it **already** misses IMAGES' scaffold today (a latent gap: an untitled stage's placeholder h1 is not recognized as placeholder). The set becomes registry-maintained: `register_layouts` extracts each incoming scaffold's title. One mechanism, every app covered.
- `build_skeleton`'s unknown-layout fallback (`STUDIO_LAYOUTS["document"]`) re-cuts to resolve through the registry — the kernel must not import an app, and after the move the bare subscript would be a KeyError.

### D4 — Naming: the writing app is **Docs**; Studio keeps the name and the layout media

Operator-ratified (2026-08-04): *"studio keeps the deck… while the documents just call it Docs."* Docs' surface title is "Docs"; its dock glyph is the text-document family (`file-text`). Deep links are conservative: `studio.file=<a document>` keeps working (params are owned and honored — present intent always wins), but the *default* open door for a `document` kind becomes Docs via the served `app` field and the runtime `KIND_TO_APP` map — no FE hardcoding, per ADR-473 D3. Open With continues to offer every claiming handler (ADR-514 D2.2).

### D5 — Unveil: full, day one (the delegated decision, taken here)

Docs ships `launcher_tier: primary`, `default_pinned: True`, with a dock-reseed generation (the ADR-486/488 pattern: un-curated docks converge to the new default; authored docks are never rewritten). Rationale against the ADR-488 precedent (hidden pre-beta): the unveil bar is *"an app unveils only when its distinctive capability works"* (ADR-486 D7) — Docs' distinctive capability is the flow editor, which is **the shipped, most-exercised medium in the system** (the ADR-505 audit: 9 of 18 live artifacts, and the only ones with real authored substance). There is no missing core loop; hiding it would hide working capability behind ceremony. Studio's tier and pin are untouched.

### D6 — Residency: Designer becomes triple-resident

`AUTHORING_APPS` gains `docs: { resident: 'designer' }` (ADR-467 D3 already establishes multi-residency: *"one agent may hold multiple residencies"*). No new agent ships with this ADR. Whether the writing app eventually earns a writing-postured resident is a separate, demand-gated decision — the seat is the app's to declare, and today's honest declaration is the resident that already carries the authoring lane.

### D7 — Legacy is deleted, never dual-run (the hooks discipline)

- The `document` row is **moved**, not copied: deleted from `STUDIO_LAYOUTS` the commit it lands in `DOCS_LAYOUTS`. `STUDIO_TEMPLATES` (derived) auto-drops it; `all_templates()` (registry-derived) auto-carries it.
- The FE app-label ternaries are deleted in favor of the declared `label` (one fact, one home).
- Dead `STUDIO_LAYOUTS` imports in `routes/studio.py` (three sites that only ever used `resolve_layout`) are removed rather than widened.
- No compatibility alias, no `document` row "just in case," no second create door: Docs' create picker offers `document`; Studio's offers `deck` · `web` — both derived from the one `app` declaration (`kinds_for_app`), never restated.

## 4. What this amends (the canon delta)

| Canon | Change |
|---|---|
| ADR-440 D2 | The DP29 act test re-cuts per medium: Docs ↔ *write a document*; Studio ↔ *lay out an artifact*. The drift guard (D7) transfers to both apps unchanged. |
| ADR-443 R5 | "Studio authors one type" clarified to its original meaning (format-agnosticism ≠ editing PDFs), now per app: each authoring app authors artifacts of its own registered types. R4's "one vocabulary, one home" stands — the home is the kernel module, not an app. |
| ADR-451 D1 / ADR-473 D2 | The `.html`-claiming surface apps become two; the `app` field's value set gains `docs`. Mechanically pre-authorized ("the Nth app costs one field"). |
| ADR-466 §1/§7 | Restated: one substrate grammar, N mode-native editors — **in two app housings**. Nothing in its interaction contracts changes. |
| ADR-505 D1 | The three-type table gains its housing column: document→Docs; deck·web→Studio. The type set itself is untouched. |
| ADR-507 D1 | The Make act's app list: `docs` · `studio` · `images`. |
| ADR-467 D1/D3 | `AUTHORING_APPS` gains the `docs` row; Designer triple-resident. |
| GLOSSARY (Make row) · STUDIO.md (header, registries) · GitBook (`apps/studio.md` rewrite — already stale at four types — + `apps/docs.md`) | Updated with this ADR. |

Preserved untouched: ADR-209 · ADR-443 R1/D2 (DOM is the model; seven ops closed) · ADR-462 D1 · ADR-480 · ADR-505 D2/D3 · ADR-509 · ADR-511 · ADR-516 · ADR-436 (window = surface; the mount owns the frame) · ADR-427/448 provenance.

## 5. The carve boundary

**(a) Document-type declaration → MOVES to Docs.** `STUDIO_LAYOUTS["document"]` → `services/docs.py::DOCS_LAYOUTS` (verbatim row, `app: "docs"`).

**(b) Shared machinery → stays kernel, three consumers.** Everything in D2's list. No file forks; no behavior change; the existing studio gates prove it (they assert behavior, and behavior is unchanged).

**(c) Generic dispatch → a row appears, mechanisms untouched.** `APP_SURFACES` + `SurfaceRegistry` + surface-icons + `SURFACE_PARAM_KEYS`/ephemeral + `DEFAULT_KEPT_SURFACES` + one dock-reseed generation + one `kernel_surfaces` row + one route file (`/docs/page.tsx`, the `/images` shape) + one `AUTHORING_APPS` row. Recents, creation scoping, Open-by-format, and Open With all follow from the served `app` field with zero new filters.

## 6. Consequences

- **The apps' names become true.** "Open Docs to write; open Studio to lay out" — the operator's Word/PowerPoint instinct, delivered on the seam the system actually has.
- **The one-app assumptions die in canon rather than drifting.** ADR-440's act test, ADR-466's phrasing, and the create picker's "three types in one door" all stop being quietly false-in-spirit.
- **The deck/web question stays open honestly.** If web later earns Wix-grain divergence, it carves from Studio the same way — the third run of a now twice-proven pattern.
- **The extraction debt is named, not paid.** Shared grammar in Studio-named homes now has three consumers; any fourth consumer or first app-specific pressure in a shared module triggers the app-neutral rename (D2).

## 7. The one-line statement

**The substrate grammar stays one; the editors were always two; this ADR gives them the two doors they already were — Docs, where you write, and Studio, where you lay out — over the same attributed record.**
