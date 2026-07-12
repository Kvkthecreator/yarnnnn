# The Studio axiomatic model — components, layouts, and the seven operations

*The operator's six axioms survive first-principles cross-analysis against the existing native — five hold outright, one needs a load-bearing correction (there is NO shadow content model: the DOM is the model). The component vocabulary the manifesto asks for already exists in three scattered places (compose section-kinds, the L3 library, the reference model) and wants unification, not invention. The universal feature set reduces to seven format-agnostic operations, every one already grounded in shipped machinery.*

> **Status**: Analysis (2026-07-12). Doc-first, receipts-backed. Part 4 of the authoring-app probe (parts 1–3: the Claude Design benchmark · surface/lane/reference design · content + reference mechanics; ADR-440 v1 + v1.1 shipped; ADR-441 mounts + ADR-442 chrome landed). Feeds the component/layout ADR and the FE architecture.
> **Authors**: KVK (the manifesto + the two lacks), Claude (cross-analysis).
> **Hat**: A. Vocabulary: artifact, block, citation, layout, skin, vocabulary, projection, lane, mount, surface bar.
> **Sequence decision this doc argues**: the component/layout model lands BEFORE v1.2 tweak-gestures — tweaks want block boundaries to operate on.

---

## 0. The operator's proposal (2026-07-12, verbatim in substance)

A six-axiom design philosophy: **HTML-native** (HTML is the canonical source of truth, not an export format) · **Component-native** (content composed from reusable semantic objects, not pages/slides) · **Layout-native** (layout defines presentation + constraints, not the content model) · **AI-native** (AI operates on components and semantics, not raw text) · **Format-agnostic** (documents/presentations/websites/reports = different renderings of the same structured content) · **Interoperable by design**. Studio as an **object-processing system**, not a word processor.

Plus two concrete lacks felt while using Claude Design:
1. **Explicit layout selection and management** — the layout choice (word-processing vs deck vs article) should be first-class, visible, and switchable; it sets the tone for the whole experience.
2. **Component grounding** — since it's HTML, editing should be grounded in components "like page design," with a **library of preset components**.

## 1. Cross-analysis — each axiom against the existing native

| Axiom | Existing native (receipts) | Verdict |
|---|---|---|
| **HTML-native** | ADR-440 D4/D5: the artifact IS one self-contained `.html` file in the attributed FS; compose is HTML-native (`engine.py`, ADR-417); the Web Viewer + canvas render it directly | ✅ **holds — already canon** |
| **Component-native** | THREE existing roots, never unified: (a) the compose **section-kind vocabulary** — `narrative · callout · checklist · metric-cards · entity-grid · comparison-table · status-matrix · data-table · timeline` (`engine.py:38-40`, ADR-177); (b) the **ADR-245 L3 library** (`web/components/library/registry.tsx` — structured affordances keyed by content shape); (c) the **reference model** — `data-ref` citations are already semantic objects projected live (ADR-440 D5) | ✅ **holds — by unification, not invention** (§3) |
| **Layout-native** | Layout modes exist (`document \| presentation \| dashboard`, `engine.py:5`) + `data-template` on the artifact root (ADR-440 D4); templates currently FIX layout at creation | 🟡 **holds with an upgrade**: layout becomes a switchable BINDING (§4.2), which the operator's lack #1 demands |
| **AI-native** | The posture already teaches template grammar + outline + patch-preference (ADR-440 D3); pointing reports `{tag, text, dataRef}` (v1.1) | ✅ **holds — and sharpens**: block-grain patching + block-grain pointing (§4.3) |
| **Format-agnostic** | One artifact, N layout modes (part 1 §2 finding: "slides/docs/pages = layout modes of ONE HTML object"); boundary projections deferred with publish/export | 🟡 **holds with a scope guard**: agnostic across *authored renderings*, NOT "Studio edits every file type" (§2 R5) |
| **Interoperable by design** | ESSENCE v15: plain HTML in an attributed, portable FS; the MCP face; substrate-portability invariant (ADR-328) | ✅ **holds — it's the moat itself** |

## 2. The refinements — where first principles bite

**R1 — THE correction: there is no shadow content model. The DOM is the model.**
The manifesto's phrasing ("structured content... rendered into HTML") admits a reading where content lives in a structured model (JSON blocks, à la Notion/ProseMirror) and HTML is a render target. That reading is **refused**: it contradicts axiom 1 (HTML would become an export format), violates Singular Implementation (two sources of truth that drift — the OpenDoc/compound-document failure, again), and forfeits the substrate properties we already have (the revision chain versions the artifact; a shadow model would need its own). The resolution: **semantics live IN the HTML** — components are semantic markup annotated with `data-block` attributes; layout is a demarcated skin inside the same file. Structure is not something HTML is compiled *from*; it is something HTML *carries*.

**R2 — Layout is a binding inside the artifact; switching it is an authored transformation.**
Because there is no shadow model, "different renderings of the same structured content" cannot mean view-time re-layout of a neutral model. It means: the artifact carries `data-template` + a skin (its `<style>` layer) + a block sequence; **switching layout preserves the block sequence and replaces the skin + flow structure** — performed by the lane, landing as an attributed revision. The rendering IS the file; a layout switch is an act, witnessed in `trace`, revertible like any act. (A view-time *preview* of another layout is a permissible later affordance; *committing* it is always a revision.)

**R3 — Two object grains: blocks are owned, citations are borrowed.**
The component model unifies with the ADR-440 reference model along one line: a **block** (`data-block`) is content the artifact owns — editable in place by the lane; a **citation** (`data-ref`) is a commons object the artifact borrows — projected read-only, never embedded-edited (the OpenDoc guard, unchanged). A block may *contain* citations (a figure block holding a cited image). Every element in an artifact is one of: block content, citation projection, or skin.

**R4 — One component vocabulary, kernel-seeded, one home.**
The three existing roots (compose section-kinds, L3 library, template grammars) converge into ONE vocabulary with the APPS-table pattern (ADR-436): code-seeded kernel constants whose shape admits growth. Housed in `services/studio.py` (the app's program half, per D6) and **served** to the FE — one source, two consumers: the posture composes each block-kind's grammar from it; the FE palette renders from it. No FE-side duplicate table.
**Vocabulary as grammar, not schema**: the vocabulary *teaches* (posture + palette); it never *validates*. A lane that authors an unknown block produces generic content, not an error — the trace witnesses, nothing polices. A validation gate would put the kernel in a schema-fight with every model that authors here.

**R5 — Scope guard: Studio authors ONE type; agnosticism is about renderings, not editors.**
"Universal feature set across all supported file types" must not drift into "Studio edits PDFs." The ADR-436 viewer registry owns *rendering* of the 9 kinds; the Studio *authors* HTML artifacts whose layouts cover document/deck/article/page — and later *projects* them across the boundary (publish → served page; export → PDF/pptx as rented boundary capabilities, ADR-417 discipline). A PDF in the workspace is citable and viewable; it is not Studio-editable. This is macOS-faithful: Pages doesn't edit PDFs either; it exports them.

## 3. The axiomatic feature model — seven format-agnostic operations

Every capability the Studio has or will have reduces to seven operations. Format-specific behavior is these operations *parameterized by* (layout, vocabulary) — never new operations.

| # | Operation | What it is | Existing grounding | Gap |
|---|---|---|---|---|
| 1 | **CREATE** | new artifact = layout choice + starter block sequence | template picker + skeletons (ADR-440 D4) | templates refactor to layout × starter-blocks (§4.2) |
| 2 | **COMPOSE** | insert / remove / reorder blocks from the vocabulary | insert menu (v1.1, prompt-composers) | palette generalizes over the unified vocabulary (§4.4) |
| 3 | **TRANSFORM** | rewrite a block's content · restyle the skin · re-layout the artifact | lane patches (`EditFile`, posture-taught) | block-grain patch targets (§4.3); the layout switcher (§4.2) |
| 4 | **POINT** | select a block or citation — deixis, context for the next act | pointing v1.1 (`{tag, text, dataRef}`) | upgrade payload to `{blockId, kind}` (§4.3) |
| 5 | **CITE** | borrow a commons object; settle-then-cite; pin semantics | the reference model (ADR-440 D5, shipped; projection in `viewers/projection.ts` post-ADR-441) | none — done |
| 6 | **PROJECT** | render the artifact: canvas, other mounts, later publish/export | canvas + WebViewer projection (ADR-441: all mounts inherit) | publish/export stay deferred (minted cap / rented engines) |
| 7 | **TRACE** | who changed what, when — per artifact, eventually per block | revision chain (ADR-209); patch-preference already narrows diffs | block-grain trace *lens* (derived from diffs — no schema change) |

Direct-manipulation (v1.2 tweaks) is not an eighth operation — a tweak is TRANSFORM with a gesture composing the patch. Publish is not an eighth — it is PROJECT at the boundary plus CITE's pin semantics. The model is closed.

## 4. The FE architecture this implies

**4.1 The block annotation spec.** Components are semantic HTML annotated minimally:
- `data-block="<kind>"` — the vocabulary kind (callout, metric-cards, figure, quote, hero, …).
- `data-block-id="<short-id>"` — a stable, lane-stamped id (posture-taught convention, like `data-ref-rev`), giving POINT/TRANSFORM/TRACE a durable address that survives text edits.
- Interior markup stays plain semantic HTML — the annotation layer is thin; an artifact with zero annotations is still valid (grammar, not schema).

**4.2 The layout registry + switcher.** Layouts become first-class kernel data beside the vocabulary: `{slug, label, skin (CSS), flow rules (prose)}` in `services/studio.py`. A **template = layout × starter block sequence** (the current three templates decompose accordingly). FE: the creation picker keys on layouts; an open artifact gets a **layout switcher in the surface bar** (ADR-442 `useSurfaceActions` — actions are data; "View as: Document · Deck · Article") that seeds/executes the lane's re-layout transformation. The lack #1 affordance: layout is always visible, always changeable, and changing it is an honest act.

**4.3 Pointing v2 + block-grain patching.** The pointer runtime reports `data-block-id` + kind when present (falls back to today's tag/text). The posture teaches: patch WITHIN block boundaries; address blocks by id. Consequence: `trace` diffs align to blocks — "the hero block changed" instead of "the file churned" — the finest attribution grain any editor in the benchmark class has.

**4.4 The palette.** `StudioInsertMenu` generalizes into the component palette, rendered from the served vocabulary (grouped: content blocks · data blocks · citations), still prompt-composers until the tweak layer lands deterministic insertion. Suggestions re-key by layout (already true by template).

**4.5 What the manifesto's philosophy section becomes.** On ratification, the six axioms + refinements R1–R5 become the Studio ADR's principles section, and a `docs/design/STUDIO.md` carries the living design doc (per-surface contract style, like `docs/design/WORKSPACE.md`).

## 5. The sequence change — recommended

Insert the component/layout model **before** v1.2 tweak-gestures. Reason: a tweak needs a target, and the honest target is a block, not a div — building gestures first would aim them at soup and rebuild them after. Phasing:

- **Phase A — vocabulary + annotation** (mostly additive): unify the vocabulary in `studio.py`; serve it; skeletons emit `data-block`; posture teaches block grammar + id-stamping; palette renders from the vocabulary.
- **Phase B — layout as binding**: layout registry; template = layout × starters; the surface-bar layout switcher (lane-performed transformation).
- **Phase C — block-grain pointing** (pointer payload upgrade + posture).
- **Then v1.2 tweaks** ride block boundaries; **block-grain trace lens** any time after A.

## 6. Drift-guard check + what this is NOT

Every piece above forces a definitional question (the block address, the layout binding, the vocabulary home, the grammar-not-schema rule) — none is editor-feature polish, so the probe discipline holds. Explicitly NOT in this model: a shadow/JSON content model (R1) · a widget/plugin ABI (components are semantic HTML + skin, never embedded editors — the OpenDoc guard) · third-party components (App(principal) territory, deferred) · WYSIWYG text editing (mutation stays single-path) · Studio-edits-every-format (R5) · a validation gate on the vocabulary (grammar, not schema).

## 7. The one-line statement

**The manifesto holds with one correction — the DOM is the model, there is no shadow content layer — after which everything else falls into place from what already exists: components unify three shipped vocabularies into one kernel-seeded grammar (taught, never enforced), layout becomes a visible switchable binding whose change is an authored revision, blocks are owned while citations stay borrowed, and the whole universal feature set closes at seven operations (create · compose · transform · point · cite · project · trace) — so the sequence flips: the block/layout model lands before tweak-gestures, because a gesture wants a block to aim at.**
