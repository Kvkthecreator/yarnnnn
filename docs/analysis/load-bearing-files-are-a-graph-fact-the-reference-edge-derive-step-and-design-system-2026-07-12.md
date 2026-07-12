# Load-Bearing Files Are a Graph Fact — the Reference Edge, the Derive Step, and the Design System

**Date**: 2026-07-12
**Hat**: A (system canon — the organizing axiom for "mission-critical" files, derived from ratified inputs).
**Status**: **Ratified direction** (operator, 2026-07-12 session). The buildable slice is [ADR-448](../adr/ADR-448-the-reference-edge-derived-from-on-the-ledger.md); the design-system convention is named-deferred until ADR-447 ratifies.
**Participants**: KVK (operator) + Claude (collaborator).

---

## 0. What this note decides (and what it does not)

**Decides:** what makes a file "mission-critical" in the substrate, and therefore
what "managed architecture" for such files is. The answer: **load-bearing-ness is
a graph position, not a file type and not a location** — a file matters because
other work was *made from it*. That is a relationship, and in this canon
relationships are **metadata on revisions, never namespace**. It follows that the
three things an operator wants from a "managed" design system or shared key
document — visibility, protection, version coupling — decompose onto three
mechanisms that already exist or are one column away. It also decides that the
"infer / learn from sources" feature is **not a new subsystem**: it is the derive
step the ledger has been reserving a slot for (`revision_kind='derivation'`,
ADR-423 §7), given an operator-facing verb.

**Does NOT decide:** the design-system consumption contract (the Skin layer
ADR-447 D1 explicitly carved out — deferred until ADR-447 ratifies); the
one-chain re-home of raw into the meaning-file's chain (ADR-423 §7 item 2, still
deferred); any change to the permission model (the powerbox, ADR-434, is
referenced, not re-opened).

**The ratified inputs it sits on** (not re-litigated):
- **The Files model** ([2026-07-08 note](the-files-model-directory-is-meaning-everything-else-is-metadata-2026-07-08.md) + ADR-384/424): a directory is meaning; permission,
  lifecycle, and provenance are metadata. Folders never gate.
- **ADR-434 (powerbox)**: permission is a per-object, per-principal grant — the
  object-granular gate exists; nothing here needs a namespace class.
- **ADR-423 (`revision_kind`)**: provenance rides the ledger; `'derivation'` is
  reserved, written by no live code; `derived_from` is a content-frontmatter
  convention; the second pass waits on "a deterministic derive step."
- **ADR-443/446 (Studio)**: an artifact cites workspace objects **by reference,
  never by copy** — `data-ref` (living path) + `data-ref-rev` (pin), with
  dangling-path fallback to the pin
  ([projection.ts](../../web/components/workspace/viewers/projection.ts)).
- **ADR-447 D1** (Proposed): the Studio's four layers — Layout / Arrangement /
  Block / **Skin**, with Skin ("design system") named out-of-scope, a separate
  decision. This note is that separate decision's ground.

## 1. The question, bare

Two questions arrived together and turned out to be one:

1. *A design system — or any "shared key document" — becomes mission-critical to
   downstream work: artifacts are created "based on it." Directories no longer
   gate (correctly). So where does its special-ness live? Is this axiomatic for
   some file types?*
2. *We want a feature that ingests a GitHub repo / PDF / PowerPoint / website
   and turns it into reusable context. What is it, and what is it called?*

The shared axis: both are about **files that other files were made from** — the
edge that runs from a derived thing back to its source. Question 1 asks what
rights and legibility that edge confers on the *source*; question 2 asks how the
edge gets *created* from outside material. Same primitive, two faces.

## 2. The axiom

**Nothing about a file's content or location makes it load-bearing. What makes
it load-bearing is that things were made from it — and that is a fact about the
graph, so it lives where graph facts live: on the revision, as metadata,
derived-never-declared (DP29).**

"Managed architecture" for such files then decomposes into three registers, each
with exactly one right mechanism — and none of them is a folder:

| Register | The operator's want | The mechanism | Status |
|---|---|---|---|
| **Legibility** | "show me what depends on this; warn me before I break it" | the reference edge, queryable — a dependents count in Files, a warning on delete | the edge exists only as content convention + artifact HTML; **ADR-448 makes it a ledger column** |
| **Protection** | "not everyone should write this" | a powerbox grant narrowing on exactly those objects (ADR-434) | **exists** — per-object, per-principal; no namespace class |
| **Version coupling** | "does downstream track my edits or freeze a version?" | the living-ref + pin model (`data-ref` / `data-ref-rev`) — track head by default, pin as the fallback | **exists** at block grain in Studio; the design system inherits it |

The counter-design this rejects: a `shared/` or `design-system/` *protected
folder class*. That is the §1 conflation of the Files-model note (permission
loaded onto location) re-imported one level up — the moment two design systems,
or one design system plus one unrelated shared doc, want different protection,
the folder class breaks and meaning loses. The operator reverted folder gating
for exactly this reason; the answer is not to sneak it back for "important"
files. Importance is *earned by references and shown by derivation* — never
declared by path.

## 3. The finding: the derive step already exists

ADR-423 §7 deferred the second pass "until a deterministic derive step exists."
Recon (2026-07-12) shows **it already does** — it just wasn't recognized as the
trigger:

- **ADR-395's upload pipeline is a live mechanical derive**: a human upload
  lands its raw blob at `inbound/uploads/{principal}/{slug}.{ext}` and the
  `ExtractTextFromBlob` primitive writes a co-located `.extracted.md` projection
  that **cites the raw via `derived_from`**
  ([documents.py::process_document](../../api/services/documents.py),
  [extract_text_from_blob.py](../../api/services/primitives/extract_text_from_blob.py)).
  Deterministic, zero-LLM, in-request. It cites via frontmatter because the
  column's consumer hadn't arrived; and the raw write predates/escaped ADR-423
  D3's tagging (it carries no `revision_kind='observation'` — a live gap against
  D3's own discipline "a write into `inbound/` is `'observation'`").
- **Studio artifacts carry reference edges in content**: every citation is a
  `data-ref` path in the artifact HTML — machine-written, deterministic,
  extractable at write time.
- **The seat's derive acts** (MCP `remember` → derived understanding) still cite
  via the same frontmatter convention, prompt-instructed.

So three independent producers of the same edge exist, all writing it as
*content*, none as *ledger*. The consumers that need it as ledger arrived this
week: the Files dependents question ("what was made from this?"), the delete
warning, `trace`'s reverse walk (today an `ilike '%derived_from%'` content scan
— the brittlest proxy left), and the design-system convention. That is the
ADR-423 §7 condition satisfied from both sides — **ADR-448 promotes
`derived_from` to a column** and completes the intake tagging.

## 4. "Learn from" is the derive step's operator-facing face

The ingest-a-source feature, mapped onto canon, is nothing new:

1. **Intake** — the source arrives as a retained, attributed raw
   (`revision_kind='observation'`): a PDF/PPT via the existing upload lane, a
   URL via a one-shot fetch, a repo via a fetched archive (follow-on). This is
   DP32's `retain`, already built for uploads.
2. **Derive** — an agent reads the raw and authors reusable meaning-files that
   **cite it** (`derived_from` → `revision_kind='derivation'`). The judgment of
   *what* to derive is LLM work; the *citation mechanics* are code — the
   `WriteFile` primitive carries the edge, the ledger records it. This is DP32's
   `cite`, made structural.

Do **not** build it as a standalone "Knowledge Acquisition" subsystem — that
names the mechanism, imports enterprise vocabulary, and would stand up a second
intake beside the ledger the system already has. One feature, two faces, over
the existing chain. A one-shot "learn from this repo" is an *addressed*
intake+derive; a standing watch (ADR-335 Sources) is the recurring flavor —
same ledger, different pulse.

**The operator-facing verb is "Learn from."** It is the word the product's own
copy already uses ("agents learn from feedback"), it is verb-shaped and
layman-legible — the same discipline that picked Documents/Downloads over
`operation/`/`inbound/`. Internally the act is *derive*; the schema value was
already named.

## 5. The design system, then

With the edge structural and the derive step live, "managed architecture for a
design system" needs **no new kernel concept**:

- **A meaning-folder** — an operator/AI-named peer home (e.g. `design-system/`),
  kind-① namespace, nothing special about its path. An exported design system
  (tokens, styles, components, guidelines, a manifest) drops in as-is — and its
  shape is already consumption-contract shaped: *a folder an agent reads at
  generation time*.
- **A consumption contract** — the Skin layer ADR-447 deferred: the Studio's
  posture reads the referenced design system when authoring; the artifact
  records which one via the same reference mechanic (a document-grain
  `data-ref`-family annotation, living ref + pin). This is the ADR-436
  LaunchServices flavor applied to skin: the artifact declares what it uses, the
  workspace resolves it. **Deferred until ADR-447 ratifies** — both touch the
  four-layer table.
- **Reference edges** make it legible (dependents badge, delete warning);
  **powerbox grants** make it protectable — both metadata, both optional, both
  now real.

The same answer covers every future "shared key document" — a glossary a
program's outputs cite, a brand voice file, a canonical dataset. No file-type
registry, no protected-folder class: the file becomes visibly load-bearing the
moment work derives from it, and the system can warn, badge, and gate on that
fact because the ledger carries it.

## 6. Sequencing

1. **[ADR-448, now]** The reference edge — `derived_from` as a ledger column;
   the lift at the single write path (frontmatter + artifact `data-ref`);
   intake tagging completed (upload raw = `observation`, projection = first
   `derivation` writer); readers read-both; dependents query + Files delete
   warning; `WriteFile` carries the edge as a parameter with posture guidance.
2. **[with 448]** "Learn from" as posture + parameter (the derive step's
   chat-addressable face); the FE affordance (a Files-surface "Learn from this"
   that seeds the chat) follows when a Files→chat seed mechanism exists.
3. **[post-ADR-447]** The design-system convention: the Skin consumption
   contract + document-grain reference. Its own ADR.
4. **[still deferred]** ADR-423 §7 item 2 (one-chain re-home of raw into the
   meaning-file's chain, the ADR-286→384 D4 single-writer relaxation) — not
   needed by any of the above.
