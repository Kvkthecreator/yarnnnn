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

## The seven operations × operator words (ADR-443 D2/D3)

The operations are internal vocabulary. **The chrome speaks the right column, always.**

| Operation | The chrome says | Where it lives |
|---|---|---|
| CREATE | **Create** / "New" | start state: layout picker + name + place |
| COMPOSE | **Add** | the palette (Add block · Image · Table · Chart) |
| TRANSFORM | **Edit** — type in the block, or ask in plain words | in place on the canvas (block text, ADR-446); the lane (chat) for judgment work; later: tweak gestures |
| POINT | **Select** | click a block in the canvas; the selection anchors Add/Slide ops and gates edit mode (it feeds the chat only on "Ask about this") |
| CITE | **Insert from workspace** | the Image/Table pickers; `data-ref` under the hood |
| PROJECT | *(implicit)* — the canvas; later **Share/Publish** | the live canvas; publish deferred |
| TRACE | **History** | revision history / Files detail; block-grain lens later |

Plus **Change layout** (a TRANSFORM specialization worth its own verb in chrome): visible in the surface bar, always switchable, lands as an edit you can see in History.

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

A **template = layout × starter blocks** (assembled by `build_skeleton`). Layout is visible in the surface bar and switchable at any time; the switch preserves every block and its id, replaces skin + flow, updates `data-template`, and lands as an attributed revision.

## The surface contract

- **Start state**: layout picker (operator words + one-line descriptions) → name → meaning-placed path (`operation/…`, never an app-named root) → Create. Below: "Continue where you left off" (recent artifacts, clickable) + open-by-path fallback.
- **Workbench**: bound lane (left — the judgment path; teaching empty state + per-layout starter chips) · live canvas (right — sandboxed projection; **select-by-click, edit-in-place**) · outline rail. Identity + verbs live in the **surface bar** (ADR-442): the artifact crumb, Change layout.
- **Mutation is two-path, one door** (ADR-444 + ADR-446): the **lane** writes judgment edits (metered); the **member** writes mechanical edits (structural ops via the toolbar, and **block text typed in place on the canvas** — free). Both land through the one write door (`POST /studio/artifacts/write`, `authored_by="operator"`, CAS-guarded). The palette pickers and the "Ask about this" chip action prefill the lane's composer; nothing else is a write path. (ADR-236's *point* — one attributed door, no silent second path — is unbroken; its *letter* is amended to let the canvas edit.)
- **Direct editing maps to the source, never the projection** (ADR-446): the canvas renders a projection (citations resolved, executables stripped, runtime injected). A block edit emits `{data-block-id, new inner}`; the FE applies it to the artifact's SOURCE html, restores any cited object inside the block to its living-reference form (citations are `contentEditable=false` islands), sanitizes, and lands one debounced revision (blur / idle-2s). The revision is the atom — no keystroke-realtime CRDT, ever.
- **Canvas security posture**: the projection pass strips all artifact-authored executables and injects only the kernel pointer + edit runtime; the iframe is `sandbox="allow-scripts"` on an opaque origin; typed content is sanitized on write-back; on projection failure the canvas renders blank, never raw.

## What Studio is NOT (the standing refusals)

No shadow/JSON content model · no widget/plugin ABI (blocks are semantic HTML + skin, never embedded editors) · no *second* write path — in-place editing lands as debounced attributed revisions through the ONE write door (ADR-446), not a parallel one · **no keystroke-realtime CO-EDITING (CRDT)** — the revision is the atom, single-writer-per-path, no merge (ADR-406/286; "real time" means the manipulation feels immediate, not operational-transform co-editing) · no editing of viewer-owned formats (a PDF is citable, not Studio-editable) · no raster generation engine (rented at the boundary when demanded — ADR-417). The standing drift test (ADR-440 §7): *does this force a definitional question about the app format, or is it just a better editor?* — with the operator's 2026-07-12 widening on record: **direct text editing is in scope** (a webpage editor's in-place edit, committed as a revision).
