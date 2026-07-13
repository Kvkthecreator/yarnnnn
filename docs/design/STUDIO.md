# STUDIO — the living design doc

> The Studio is yarnnn's first authoring app (ADR-440) governed by the axiomatic model (ADR-443). This doc is the FE-facing contract: the philosophy, the operations and their operator words, the vocabulary and layout registries, and the surface contract. Derivations live in the four probe analyses (`the-authoring-app-claude-design-benchmark` · `the-studio-surface-lane-and-reference-model` · `the-studio-content-and-the-reference-mechanics` · `the-studio-axiomatic-model-components-and-layouts`).

## Philosophy (operator-authored, 2026-07-12; ratified with refinements by ADR-443)

Studio is an **HTML-native, AI-native editing system** built from first principles — an axiomatic model for creating, editing, and transforming structured content, not an emulation of legacy desktop applications.

- **HTML-native** — HTML is the canonical source of truth, not an export format.
- **Component-native** — content is composed from reusable semantic blocks, not pages or proprietary formats.
- **Layout-native** — layout defines presentation and constraints, not the content model.
- **AI-native** — AI operates on blocks and document semantics, not raw text or binary files.
- **Format-agnostic** — documents, decks, articles, pages are different renderings of the same structured content.
- **Interoperable by design** — one artifact renders, transforms, and (later) exports across formats with structure and intent preserved.

**The refinements that make this hold** (ADR-443 D1): the DOM is the model — no shadow content layer (R1); layout is a binding inside the artifact and switching it is an authored revision (R2); blocks are owned, citations are borrowed (R3); one kernel vocabulary that teaches and never validates (R4); Studio authors one type — agnosticism is about renderings, not editors (R5).

## The four layers (the composition model)

An artifact is composed from four orthogonal layers. Each answers one question; each is a thin `data-*` annotation on real HTML (the DOM is the model, never a JSON tree):

| Layer | Answers | Annotation | Status |
|---|---|---|---|
| **Layout** | what *kind* of artifact | `data-template` (document/deck/article) | live (ADR-443) |
| **Arrangement** | *where content goes* on a page/section — grids, slots, overlays, sizings | `data-arrange` + `data-slot` | live (ADR-447) — per-type, page-grain shipped; section-band nesting is phase 2 |
| **Block** | what a content unit *is* | `data-block` + `data-block-id` | live (ADR-443/446) |
| **Skin** | how it *looks* (design system: palette/type/mood) | `<style data-skin="true" data-ref="…">` — marked + cited | live (ADR-449) |
| **Property tokens** | *placement + emphasis* of one block/page/artifact — align, tone, sizing presets, column ratio, typography, width | `data-align` / `data-tone` / `data-height` / `data-fit` / `data-ratio` / `data-valign` (block/page) + `data-font` / `data-measure` on the ROOT (document grain, ADR-455) | live (ADR-453/455) — tokens not pixels; styled by the marked `<style data-kernel="true">` element (v2), themed by the skin's custom properties; absence = default |

Arrangement is the composition layer PowerPoint's New-Slide flyout and Wix's section stacks both name: *Title Slide · Two Content · Comparison · Picture-with-Caption* (page grain) and drop-in *two-column / three-grid / image-overlay* bands (section grain), nested. It is orthogonal to blocks (what) and skin (how). See ADR-447.

## The seven operations × operator words (ADR-443 D2/D3)

The operations are internal vocabulary. **The chrome speaks the right column, always.**

| Operation | The chrome says | Where it lives |
|---|---|---|
| CREATE | **Create** / "New" | start state: layout picker + name + place |
| COMPOSE | **Insert** (blocks) · **New slide/section** (pages) | the toolbar (ADR-453 grain-aligned): Insert ▾ = block-grain palette; New ‹noun› ▾ = the page-grain arrangement GALLERY with derived wireframe thumbnails |
| TRANSFORM | **Edit** — double-click the block and type, or ask in plain words; **Re-arrange** / token controls for shape | in place on the canvas (ADR-446); the Design tab for arrangement + property tokens (ADR-453); the lane (chat) for judgment work |
| POINT | **Select** | the click-grain ladder (ADR-453 D5): click a block → its slot's padding → the page margin; slots outline + name themselves on hover; the selection anchors ops and drives the Design tab's scope |
| CITE | **Insert from workspace** | the Image/Table pickers; media slots take a cited image via the Design tab; `data-ref` under the hood |
| PROJECT | *(implicit)* — the canvas; later **Share/Publish** | the live canvas; publish deferred |
| TRACE | **History** | revision history / Files detail; block-grain lens later |

Plus the page verbs *(ADR-453)*: **New slide/section** (add a page from the gallery — the toolbar) and **Re-arrange** (re-lay THIS page — the Design tab's page scope), splitting the former mixed-grain "Arrange" menu by grain. A deck's page is a "slide", a document/article's a "section". Every act is a free, id-preserving, attributed reflow. Delete / Duplicate / Move up / Move down exist at both block and page grain (the Design tab's verb rows). *(There is no "Change layout" — the artifact's TYPE is fixed at creation; ADR-447 D7.5 deleted the type-switcher. Composition happens WITHIN the type.)*

## The block vocabulary (kernel-seeded — `services/studio.py`, served via `GET /studio/vocabulary`)

| Group | Kind | The chrome says |
|---|---|---|
| Content | `prose` | Text |
| Content | `callout` | Callout |
| Content | `quote` | Quote |
| Content | `checklist` | Checklist |
| Data | `table` | Table *(from a workspace CSV — cited)* |
| Data | `metrics` | Metrics |
| Data | `chart` | Chart *(authored SVG in `./assets/`)* |
| Media | `figure` | Image *(workspace image — cited)* |

Annotation spec: `data-block="<kind>"` + `data-block-id="<short-id>"` on top-level content units. Layout flow containers (slides, `<main>`, `<article>`) are structure, not blocks. Unannotated content stays valid — the vocabulary is grammar, not schema.

## The layouts (kernel-seeded)

| Slug | The chrome says | Flow |
|---|---|---|
| `document` | Document | continuous `<main>`, sections under headings |
| `deck` | Deck | `<section class="slide">` containers, one idea each |
| `article` | Article | `<article>` with header (title/subtitle/byline) + prose flow |

A **template = layout × [page arrangement] × starter blocks** (assembled by `build_skeleton`; since ADR-453 the skeleton also bakes the marked `<style data-kernel="true">` token stylesheet). The artifact's TYPE is fixed at creation (ADR-447 D7.5 — no in-artifact type switch); when the lane is asked to change layout it preserves every block and its id, replaces the UNMARKED skin + flow, updates `data-template`, and lands an attributed revision — the marked `data-kernel` and `data-skin` elements survive every switch.

## The arrangements *(live, ADR-447 — generalizes ADR-444's slide masters; the interaction contract per ADR-453 D5)*

**One registry row → six projections** (ADR-453): the markup fragment · the CSS · the derived wireframe thumbnail (New/Re-arrange galleries) · the canvas affordances (slot hover-outlines + names, `+ Add here`, the click-grain ladder) · the Design tab's page controls · the lane's posture grammar. Slot `role` is the interaction gate: `flow` slots take blocks (add-here inserts prose), `media` slots take a cited image (add-here opens the Design tab's picker), `heading` slots anchor. Adding an arrangement stays one registry row.

An **arrangement** says *where content goes* on a page or section: grids, slots, overlays, sizings. It is per-document-type and nested — page → section → slot → block:

- **Page arrangements** (whole canvas): deck → `title · content · two-column · quote` (live today as `STUDIO_CONTAINERS`), extended to `comparison · picture-with-caption · section-header` and to document/article page arrangements (`title+lede · hero`, `lead-image · pull-quote-aside`). The PowerPoint New-Slide grain.
- **Section arrangements** (drop-in bands, cross-type — phase 2): `two-column · three-grid · image-overlay · sidebar · full-bleed-band`. The Wix section-stack grain.

Annotation: `data-arrange="<slug>"` on the page/section element; `data-slot="main|left|right|media|…"` on its regions; blocks fill slots; slots may hold sub-arrangement bands (the recursion). Grid/overlay/sizing is CSS in the arrangement's skin fragment — HTML-native, no layout DSL, no JSON tree. Applying/switching an arrangement is the same free CAS-guarded reflow that moves blocks between slots today (`applySlideLayout`, generalized) — blocks move intact, ids preserved, heading blocks anchor rather than flow. Grammar not schema: an un-arranged artifact stays valid.

## The surface contract

- **Start state**: layout picker (operator words + one-line descriptions) → name → meaning-placed path (`operation/…`, never an app-named root) → Create. Below: "Continue where you left off" (recent artifacts, clickable) + open-by-path fallback.
- **Workbench** — three columns, three jobs (ADR-447; the right column split into two TABS by ADR-453): **navigator (left — a per-type navigator, COLLAPSIBLE via a toolbar toggle, ADR-455:** a slide strip of **visual previews** for a deck (each slide a scaled real render, PowerPoint/Preview.app style — clicking one scrolls the canvas to it), a **navigational outline** for a document/article — clicking a heading selects its block and scrolls the canvas to it (the Docs/Word nav-pane contract)) · **canvas (center — see + touch:** sandboxed projection; the **click-grain ladder** — a block, a slot's padding, a page's margin (slots outline + name themselves on hover); **double-click a block to edit its text in place**, empty slots show `+ Add here` (role-gated); a **zoom** view control (−/%/+) scales the render on screen without touching the file), with the **Insert · New ‹slide|section›** toolbar over it · **the right column — Chat | Design tabs (ADR-453 D4, the Canva model — never a fourth column):** Chat = the bound lane (the judgment path; teaching empty state + starter chips; stays MOUNTED under either tab so a streaming turn survives a switch); **Design = the scope-switching inspector** — document scope (typography Ag-chips + width tokens [ADR-455] + the design-system picker, ADR-449 D5 homed) / page scope (Re-arrange gallery + page tokens + Duplicate/Move/Delete) / slot scope (role-gated quick-add) / block scope (tokens + Ask about this + Duplicate/Move/Delete). The surface-bar `⋯` carries the file grain: Copy link · Duplicate · Rename · Move · Trash (ADR-446/455). Freddie's floating rail is suppressed on `studio` (like `/chat`), so the Studio's own chat owns the right edge. **On mobile (< md)** the three columns collapse to one pane at a time (Slides/Outline · Canvas · Chat) via a bottom tab bar — canvas-first. Identity lives in the **surface bar** (ADR-442): the artifact crumb. *(The type-switcher is deleted — see the refusals.)*
- **Mutation is two-path, one door** (ADR-444 + ADR-446): the **lane** writes judgment edits (metered); the **member** writes mechanical edits (structural ops via the toolbar, and **block text typed in place on the canvas** — free). Both land through the one write door (`POST /studio/artifacts/write`, `authored_by="operator"`, CAS-guarded). The palette pickers and the "Ask about this" chip action prefill the lane's composer; nothing else is a write path. (ADR-236's *point* — one attributed door, no silent second path — is unbroken; its *letter* is amended to let the canvas edit.)
- **Direct editing maps to the source, never the projection** (ADR-446): the canvas renders a projection (citations resolved, executables stripped, runtime injected). A block edit emits `{data-block-id, new inner}`; the FE applies it to the artifact's SOURCE html, restores any cited object inside the block to its living-reference form (citations are `contentEditable=false` islands), sanitizes, and lands one debounced revision (blur / idle-2s). The revision is the atom — no keystroke-realtime CRDT, ever.
- **Canvas security posture**: the projection pass strips all artifact-authored executables and injects only the kernel pointer + edit runtime; the iframe is `sandbox="allow-scripts"` on an opaque origin; typed content is sanitized on write-back; on projection failure the canvas renders blank, never raw.

## What Studio is NOT (the standing refusals)

No shadow/JSON content model · no widget/plugin ABI (blocks are semantic HTML + skin, never embedded editors) · no *second* write path — in-place editing lands as debounced attributed revisions through the ONE write door (ADR-446), not a parallel one · **no keystroke-realtime CO-EDITING (CRDT)** — the revision is the atom, single-writer-per-path, no merge (ADR-406/286; "real time" means the manipulation feels immediate, not operational-transform co-editing) · no editing of viewer-owned formats (a PDF is citable, not Studio-editable) · no raster generation engine (rented at the boundary when demanded — ADR-417). The standing drift test (ADR-440 §7): *does this force a definitional question about the app format, or is it just a better editor?* — with the operator's 2026-07-12 widening on record: **direct text editing is in scope** (a webpage editor's in-place edit, committed as a revision).
