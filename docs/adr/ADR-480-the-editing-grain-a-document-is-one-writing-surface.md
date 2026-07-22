# ADR-480 — The editing grain: a document is one writing surface

- **Status**: **Accepted** (2026-07-22, operator-ratified through the editing-grain
  discourse — *"we've pinned the assumption that, because it's attribution-native, we need
  block level for document type. However, is this really the right way?"* → the premise was
  stress-tested against the substrate and **failed**; the re-carve was ratified with the
  performance claim explicitly withdrawn).
- **Date**: 2026-07-22
- **Dimension**: Channel (primary — how the member writes, per mode). No new substrate, no
  new write path, no schema, no migration.
- **Amends**:
  - **ADR-466 D1/P12** — the flow contract is deepened one layer. P12 ruled the flow-mode
    complaints "chrome-grain defects, not block-model defects" and reaffirmed the block
    model *as the attribution grain on every template*. The first half stands; **the second
    half was factually wrong about the substrate** (§2) and is corrected here. The mode-native
    thesis is not reversed — it is carried one notch deeper than P12 took it.
  - **ADR-446** — direct-edit's editing UNIT on `flow` layouts becomes the document root;
    the write-back contract (source-mapped, sanitized, debounced, one door) is preserved
    exactly.
  - **ADR-477 §1a** — "an empty block closes itself" becomes **paged-only**. On flow the
    browser owns it; the rule is not deleted, it is scoped.
  - **ADR-458 D4 / ADR-462 D1** — on flow layouts the **right-click menu leads** and the
    hover gutter recedes to insert-only. The tiered-redundancy principle (ADR-367 D3) is
    preserved; which tier *leads* changes on flow.
- **Preserves**: ADR-209 (the revision is the atom; one attributed write door) · ADR-443 R1
  (the DOM is the model — reinforced: the DOM is now *more* the model, not less) · ADR-443
  D2 (no eighth operation) · ADR-448 (the reference edge lifts from `data-ref`, untouched) ·
  ADR-406/286 (no CRDT, single-writer-per-path) · ADR-456 stop-lines (no second source
  format, no per-breakpoint editing) · ADR-461 D4 (a page has a viewport — no spatial keys
  on flow) · **ADR-466 D2 and all `paged` work in full** (deck · page · canvas · IMAGES are
  not touched by this ADR).

---

## 1. The friction, and why four passes did not resolve it

The operator has returned to the same complaint across ADR-462, ADR-466 P9, P10, P11, P12
and ADR-477 — each time about the *document* type, each time some variant of *"the mouse and
the selection fight me; it doesn't feel like writing."* Each pass diagnosed a chrome defect,
fixed it honestly, and reaffirmed the model. The complaint returned.

When a defect recurs across five passes under five different diagnoses, the defect is
usually not in any of the five places. It is in a premise all five share.

The shared premise, stated plainly and never once tested:

> **YARNNN is attribution-native; attribution needs block-level grain; therefore a document
> must be edited block by block.**

This ADR tests it.

## 2. The stress test — the premise is false

Four findings, each verifiable by `grep` at the commit that ratified this ADR.

**F1 — the ledger's grain is the FILE, not the block.**
`write_revision` (`api/services/authored_substrate.py:614`) takes `path`, `content`,
`authored_by`, `message`, `derived_from`. There is no block parameter, no block column, no
block index anywhere in the signature or the schema. One revision = one whole-file snapshot
against `(workspace_id, path)`.

**F2 — the moat's write door has never heard of blocks.**
`authored_substrate.py` contains the substring `data-block` **zero times**.

**F3 — `data-block` is contained entirely in the APP layer.** Every non-test production
occurrence in `api/` is in `services/studio.py` (the layout/block registry),
`routes/studio.py`, or `services/images/` (the IMAGES app, which shares the block grammar per
ADR-472). **Zero** occurrences in the substrate, the primitives, `permission.py`,
`revisions.py`, or the MCP face (`remember`/`recall`/`trace`). The assertion is a
*containment boundary*, not a file count: a new Studio/IMAGES module may legitimately speak
blocks; `authored_substrate.py` or `primitives/` doing so would mean this premise has
changed and the carve needs re-deriving. The gate enforces the boundary, not the count.

**F4 — citation rides `data-ref`, not `data-block`.**
The ADR-448 reference edge lifts `derived_from` from `_DATA_REF_RX = data-ref="([^"]+)"`
(`authored_substrate.py:245`). `derived_from` would survive the deletion of every
`data-block` attribute in the codebase.

**Therefore**: blocks are a **Studio rendering-and-addressing convention inside HTML
content**. They are real and useful. They are **not** the attribution grain, and the
substrate does not require them at any grain. ADR-466 P12's claim that "blocks stay the
attribution/citation grain" is, as a statement about this substrate, false — and repeating it
is what made the operator's friction unresolvable, because it framed a chrome choice as a
constitutional constraint.

## 3. The axiom

> **Attribution binds to the file. Addressing binds to sub-file structure. Editing binds to
> neither — it binds to what the medium is.**

Three independent layers, fused in the shipped code because the block was believed
constitutionally required at all three. Unfused:

| Layer | Carrier | Grain | Required by |
|---|---|---|---|
| **Attribution** | `workspace_file_versions` row | the FILE (`workspace_id`, `path`) | ADR-209 — the moat |
| **Addressing** | `data-block-id`, `data-ref`, `data-gen-*` | a REGION of content | ADR-446 direct-edit, ADR-448 edges |
| **Editing** | the runtime's `contenteditable` root | **whatever the medium is** | nothing above — it is free |

The third row is the discovery: the editing grain was never derived from anything. It was
inherited from the deck, where it is correct, and applied to the document, where it is not.

## 4. Decisions

### D1 — On `flow` layouts, the editing root is the DOCUMENT, not the block

`document` and `article` (the two `mode: "flow"` layouts) place `contenteditable="true"` on
the **flow root** (`<main>` / `<article>`) — one continuous writing surface, entered once.

The member gets, natively and for free:

- cross-block drag-selection (a phrase spanning two paragraphs)
- `⌘A` selecting the document
- copy of a multi-paragraph span with structure intact
- `⌘F` find across the whole document
- native per-character undo *within* the field (ADR-477's `⌘Z` revert-as-write remains the
  outer layer)
- correct IME, accessibility, RTL and locale behavior — the browser's, not ours

**`paged` layouts are untouched.** Deck, page and canvas keep the ADR-466 object grammar
exactly: one block editable at a time, the bounding box, the eight handles, the border-band
move. A slide *is* a frame of objects; the object grammar is right there. This ADR only
denies that a document is one.

### D2 — Blocks persist in the markup as ANNOTATIONS, not enclosures

`data-block` and `data-block-id` stay in the serialized HTML on flow layouts. What changes is
the runtime's posture toward them:

- they are **no longer swapped in and out of `contenteditable`**
- they are **no longer click targets** that gate where the caret may go
- they **remain** addressable by id (AI direct-edit, `Ask about this`, turn-into, citation
  anchoring, the navigator outline)

The distinction is exactly *enclosure* → *annotation*: the same attribute, no longer acting
as a wall.

### D3 — Ids are PRESERVED through editing, not asserted before it (normalize-on-write)

This is the load-bearing mechanism and the one real risk (§7).

Native `contenteditable` will split, merge, duplicate and orphan `data-block-id`s as the
member types across boundaries. So on every commit, before the write door, a **normalize
pass** walks the flow root and re-establishes the invariant:

1. **Ids that survived on a recognizable block keep their id** — identity is preserved
   wherever the DOM still carries it.
2. **A duplicated id** (native split copied the attribute onto both halves) — the FIRST in
   document order keeps it; later ones are re-minted.
3. **A new top-level element with no id** gets a freshly minted id.
4. **A block whose id vanished entirely** is treated as new — it gets a new id rather than
   guessing at a resurrection.
5. **Citation islands (`data-ref`) are never re-minted or restructured** — they keep their
   identity unconditionally, and the ADR-448 edge lift is unaffected.

Addressability on flow becomes **reconstructed** rather than **enforced**. This is
deliberately and honestly weaker than the paged guarantee. It is priced in §7.

### D4 — The retired simulation is DELETED on flow, not disabled

The runtime currently hand-implements what native `contenteditable` does. On flow layouts
these paths are removed rather than flag-gated (Singular Implementation — no dual approach):

- `Enter` → `splitBlock` / `splitBlockAndInsert`
- `Backspace` at block start → `mergeBlock`
- `caretAtBlockStart` boundary detection and the cross-block ARROW traversal (`caretRect`,
  `adjacentTextBlock`) — the code whose own comment reads *"the document behaves as one
  continuous flow"*, i.e. a simulation of the browser
- the ADR-477 §1a empty-block-closes rule
- the one-gesture-two-ops race guards those paths required

**All of it survives for `paged`**, where blocks remain enclosures and the simulation is
still the correct mechanism. The ops themselves (`splitBlock`, `mergeBlock`) stay exported —
they are still reachable structurally.

This is the deeper argument for the whole ADR: **we delete a hand-rolled text editor and use
the browser's**, retiring a class of recurring boundary defect rather than patching its next
instance.

### D5 — On flow, right-click LEADS; the gutter recedes to insert

Format changes (turn-into, duplicate, move, delete) reach for the **right-click menu**
(already built — ADR-462, `StudioBlockMenu`) and the **inline format bar** (already built —
ADR-456 W2). The hover gutter stays for **insert** (`+` / slash) and loses its role as the
primary structural affordance on flow.

ADR-367 D3 tiered redundancy is preserved: the Design tab remains the dwell. What changes is
which tier leads on flow — the fast path is now the menu that appears where the pointer
already is, rather than chrome in the margin.

### D6 — Pagination is REFUSED (a standing refusal, recorded)

Word-style page breaks on flow layouts are refused. Pagination is a **print** abstraction;
Studio is HTML-native by axiom (ADR-417 — no owned render engine), responsive by kernel CSS,
and ADR-456's stop-lines already refuse per-breakpoint editing. Deciding where text breaks
across a fixed page is that refusal in another costume.

The two legitimate wants beneath the ask are already served: **print fidelity** by the
ADR-466 D6 print-projection, and the **felt boundedness** of a page by `max-width` + margin +
paper-ground styling (a token question, not a model question). Notion, Linear and Craft all
refuse pagination for the same reason; Google Docs paginates because it targets paper, and
shipped "pageless" as the escape.

### D7 — Performance is explicitly NOT a justification

Measured before drafting, and recorded so no later reader infers a win that was never
claimed: the current path is already good — writes post per-block `newInner`
(`projection.ts:922`), debounce at blur/idle-2s, and ADR-466 P8 made them optimistic (pixels
never wait on the API).

Second-order effects roughly cancel: typing no longer runs `syncBox` per `input` on flow
(better); the normalize pass walks the DOM per commit and the payload widens from one block's
inner to a document region (worse). **Net: a wash.** This ADR is justified on capability and
code-structure grounds alone.

## 5. What this ADR does NOT do

- Does not touch `paged` layouts in any respect (deck · page · canvas · IMAGES).
- Does not touch the substrate, the write door, attribution, `derived_from`, the registries,
  or any schema. **No migration.**
- Does not remove `data-block` from serialized markup.
- Does not add a second write path, a JSON content model, or a CRDT.
- Does not build pagination (D6 refuses it), markdown export (ADR-456 W4), or band nesting.

## 6. Falsifiers

1. `data-block` / `data-block-id` still appear in every flow artifact's serialized HTML after
   a full edit session — annotation, not deletion.
2. Every flow edit still lands as exactly ONE attributed revision through `POST
   /studio/artifacts/write`; no new write path appears.
3. After a native split of a block into two, both halves carry **distinct, non-empty**
   `data-block-id`s, and the first retains the original id.
4. A block containing `data-ref` survives an edit session with its citation intact and its
   `derived_from` edge unchanged.
5. `grep` shows no `contenteditable` swapping per block on a `flow` layout — the root owns it.
6. Deck/page/canvas gates pass unchanged: the object grammar, the bounding box, the eight
   handles, split/merge and the empty-block rule all still work on `paged`.
7. A document with N blocks supports a single selection spanning blocks 1→N (`⌘A`), and
   copying it yields structured HTML.

## 7. The honest costs

- **AI direct-edit precision on flow degrades** from exact-enclosure to reconstructed
  annotation. Targeting "block b7" is exact when b7 is a wall; it is approximate when b7 is a
  reconstructed region. Decks — where precise object targeting matters most — are unaffected.
- **Normalize-on-write is where the risk concentrates.** Falsifier 3 is its gate. A
  pathological editing sequence could still churn ids; churn costs *addressing stability*
  (an AI edit aimed at a stale id misses), never *content* and never *attribution* — the
  revision chain is by path.
- **Arrangement bands inside flow documents** (`data-arrange`) remain islands within the
  editable root; their slot semantics are unchanged but they are now edited through the same
  continuous surface.
- **It amends a one-day-old reaffirmation.** ADR-466 P12's chrome fixes are kept in full;
  only its claim about the substrate is corrected.

## 8. The one-line statement

**Attribution binds to the file, addressing to structure, editing to the medium — so a deck
is edited as objects in a frame, and a document is edited as what it is: one continuous
writing surface, with blocks riding along as annotations rather than standing as walls.**
