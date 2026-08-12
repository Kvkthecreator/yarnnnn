# ADR-560: The document model — flow editing gets a model, and the DOM becomes a view

> **Status**: **Accepted + Implemented** (2026-08-12 — phases 1-4 of §6 landed the same
> day: `f5950df` model + parity gate · `68201bd` FlowEditor + wiring · `a8d9bda`
> in-model identity (found by the operator's first live drive — this arc's own
> click-pass discipline, honest to form) · `290257c` the D8 deletion, −848 lines.
> Phase 5, the full prod click-pass, is OWED.)
> (Original ratification: 2026-08-12, operator-delegated — *"based on your own
> first principle assessment … resolve this in full such that any legacy, wrong
> approaches are cleaned-up, alongside the documentation and codebase to be
> streamlined"*). Drafted from the 2026-08-12 Docs audit (two full code-mapping
> passes + the ADR-511…547 defect ledger; receipts in §1).
> **Date**: 2026-08-12
> **Dimension**: **Channel** (how the flow medium is edited) primary, with a
> **Substrate non-change stated as a decision** (D6): the file format, the write
> door, whole-file attribution and CAS are untouched.
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**:
> - **ADR-443 R1** ("the DOM is the model; there is no parallel tree") —
>   **retired for the flow medium** (D1). Upheld for paged, where the block is
>   an enclosure and the model claim was never load-bearing in the same way.
> - **ADR-480** (the editing grain) — its *per-medium* axiom is upheld and is
>   the reason this ADR is flow-scoped. Its flow mechanism (contenteditable on
>   the root, browser owns everything) is superseded by D1/D4.
> - **ADR-524 D6** ("no virtual DOM / no diffing library in the iframe") —
>   **superseded with the measurement it asked for** (§2.2). The refusal was
>   correct for a patch channel; it is not a law against a document model.
> - **ADR-547** (the flow write grain) — **completed by construction**: with one
>   writer there is no granularity mismatch for a commit to lie about. Its D3
>   guard property ("a commit never removes an annotation it cannot have
>   authored") is re-homed into the schema (D3 below).
> - **ADR-540** (a retired document does not commit) — the defect class
>   (teardown gasp commits from a dying iframe) ceases to exist on flow; the
>   fence is deleted with the iframe editing path.
> - **ADR-528** (a range is not a block) — upheld in full: blocks stay the
>   document's units, `document | range | object` stays the scope set, and §2's
>   receipt (the substrate never sees block identity) is what makes D6 free.
> - **ADR-546** (the rung law) — upheld; `FLOW_RUNGS` becomes a schema input.
> - **ADR-521** (the flow benchmark) — upheld; D3's per-segment formatting
>   semantics are re-expressed as transactions, not re-derived.
> - **ADR-518 D2** (one machinery, no per-app forks) — see §2.3: this forks the
>   flow *editing runtime*, which was always a per-medium branch, and none of
>   the shared machinery (write door, registry, tokens, selection algebra,
>   revision atom).

---

## 1. Context — the audit's finding, in one page

The 2026-08-12 audit (operator-directed: *"why does Docs still feel fundamentally
broken?"*) mapped the full pipeline and the ADR ledger. The load-bearing facts:

1. **There is no document model anywhere in the system.** The server stores an
   opaque HTML string and validates path shape + non-emptiness
   (`routes/studio.py:651-684`); the parent holds string copies; the editable
   DOM lives in an opaque-origin iframe the parent cannot read. One document's
   content is live in **nine places** during editing, reconciled by discipline.
2. **Two writers, one document, no shared state.** The iframe's only write
   granularity is the whole `<main>` (a 2s-debounced snapshot); the parent
   computes ops over its own copy. ADR-540 and ADR-547 are both this seam
   failing — silent op reverts past green gates, two HTTP-200 writes, CAS
   satisfied, found only by driving prod.
3. **Every defense is a veto.** `flowDead`, the annihilation guard, the
   annotation-removal guard all drop the member's commit entirely. Nothing
   merges, because there is nothing to merge *in*.
4. **The editing engine is ~3,650 lines of ES5 inside template literals**
   (`POINTER_SCRIPT` / `EDIT_SCRIPT` / `OBJECT_SCRIPT` in `projection.ts`) —
   untyped, unlintable, untestable, driven over ~30 string-typed postMessage
   verbs, with script injection *order* as the dependency mechanism.
5. **The block grammar is declared four times in three languages** (TS DOM
   predicates, ES5-in-a-string hand-lists, Python regex, the Python registry),
   pinned by parity gates. Two hand-lists disagree at HEAD
   (`PASTE_KEEP_INTERNAL` vs the `GUARDED_ANNOTATIONS` predicate).
6. **16 of the 21 ADRs in the 511–547 arc exist to reconcile the block grammar
   with a contenteditable surface.** Five silent-data-loss defects shipped past
   green batteries in eight days; each was found by the operator personally,
   because the opaque-origin iframe defeats every machine driver (CDP, a11y,
   synthesized keys) — the QA loop for this surface *is* the operator.

The operator's metaphor at delegation: multiple attempts and a variety of
approaches diluted into dual approaches and wrong implementation. §1.5's
receipt agrees: the system has been re-deriving the internals of a document
editor piecewise — a selection algebra (541), declared op grains + a patch
channel (524/547 D4), a normalize seam (511 D5), a schema-shaped registry
(539/542), refusal guards where a schema would make the states unrepresentable
— each piece hand-rolled at the moment its absence produced a prod defect.

## 2. The three questions that decide this

### 2.1 Are blocks or the "Google Docs" mechanics the fault? — No.

ADR-528 answered this and the audit re-confirms it: Google Docs is itself
block-structured (a list of styled paragraphs); Notion-scope vocabulary with
continuous-surface mechanics (ADR-521 D1) is the right product target and is
**unchanged by this ADR**. The fault is one layer down, in what holds the
document *while it is being edited*.

### 2.2 Why is a dependency right now when ADR-524 D6 refused one?

ADR-524 D6 refused "a virtual DOM / diffing library in the iframe" as "a
dependency and a class of subtle bugs bought to solve a problem D2 already
bounds." That was correct *for the patch channel*: a render-path optimization
must not grow a second rendering architecture. This is a different question —
not how to move pixels, but **what a document IS between keystrokes** — and the
measurement D6 implicitly asked for now exists: the bounded problem was not
bounded (three more data-loss laws in six days), and the in-house alternative
is measured at ~3,650 untyped lines plus four grammar declarations plus a
per-op discipline whose own ADR (547 §4.1) predicts it will be forgotten.

**ProseMirror is adopted** (`prosemirror-model/state/view/transform/commands/
keymap/history/inputrules/schema-list`; `prosemirror-tables` was evaluated and
DROPPED at implementation — the served `table` kind is a cited CSV projection,
an island, never an authored grid). Chosen over Lexical for exactly the properties this substrate needs:
schema-first (the schema can be *generated from the served vocabulary*),
deterministic DOM↔model round-trip via declarative `parseDOM`/`toDOM`, a
transaction/step log (the shape per-span attribution needs — §D7), and no
framework coupling. The "block-first was tried five times and failed"
record (ADR-521 §2) does not count against this: those five were hand-rolled
per-block *enclosures on the same DOM-as-model substrate* — evidence against
hand-rolling, not against a model.

### 2.3 Why this is not the fork ADR-518/546 refused

ADR-546 §2.3 refused a Docs app fork because every defect was shared machinery
*failing to branch*, and a fork duplicates machinery without fixing the missing
branch. That analysis stands. What changes here is a layer that was **always
per-medium**: ADR-480 already split the editing grain by mode (enclosure vs
annotation), and the flow editing runtime (enterFlow, flowCommit, the flow
branches of EDIT_SCRIPT) was already flow-only code. D1 replaces that per-medium
branch with a better one. The shared machinery — the write door, the revision
atom, CAS, the registry, the token grammar, `selection.ts`, the projection as
the *render* path, the pane — stays one implementation with N consumers.

## 3. Decisions

### D1 — On flow, the document model is the source of truth; the DOM is a view

ADR-443 R1 is retired **for the flow medium**. A Docs document being edited is
a typed ProseMirror document; every mutation — typing, paste, an op from the
pane, a turn-into, a Tab — is a **transaction** against that model. The
rendered DOM is a projection of the model, maintained by the editor view.
There is exactly **one writer**, so ADR-547's law holds by construction: a
commit reports the model, and the model was party to every change.

Paged (Studio decks, IMAGES stages) is untouched — the enclosure grain,
per-block commits, the patch channel and the projection runtime all stand
there, per ADR-480's per-medium axiom.

### D2 — The schema is GENERATED from the served vocabulary

The flow schema's node set is derived from `STUDIO_BLOCKS` (the app-scoped
flow roster) and `FLOW_RUNGS`; its mark set from the kernel's span vocabulary
(`strong/em/s/code/a`, `data-mark`, `data-highlight`); its attribute law from
the `GUARDED_ANNOTATIONS` predicate (every `data-*` except the runtime's own
scaffolding round-trips as an attr). The registry finally gains an **executing
reader** — the ADR-539 shadow-registry fault closes for flow, and the paste
allowlists are **deleted**: the schema *is* the paste policy (unknown structure
parses to the preservation node, executable content cannot enter the model).

### D3 — Nothing the model does not understand is ever dropped

The schema carries a **preservation node**: any block-level element it does not
recognize round-trips verbatim (outerHTML as an atom — selectable, movable,
deletable, not internally editable), and unknown inline wrappers round-trip as
a generic wrap mark. This is ADR-547 D3's guard property re-homed from a
veto to a **structural invariant**: a save cannot remove an annotation it
cannot have authored, because unrecognized substrate is carried opaquely, not
re-derived. Legacy kinds Docs no longer offers (callout, toggle — ADR-528 D5's
inert names) remain editable as generic containers, preserving 528 D5's
promise that their prose stays editable.

### D4 — Flow editing happens in the parent document

The editor mounts in the parent (no editing iframe). The kernel CSS + layout
skin + design system are scoped into the editor host (one generated wrapper,
same Python emitters). The sandboxed opaque-origin iframe **remains the render
path** for read-only/share/preview surfaces — its security contract (ADR-446)
was always about *rendering possibly-foreign artifacts*, and editing one's own
document never needed it. Citation islands (`data-ref`) render as node views
through the same parent-side resolution the projection already uses; they stay
atoms (ADR-446 D3 unchanged: the source form is the substrate form).

Consequences taken deliberately:
- postMessage stops being the editing ABI on flow; the pane/toolbar/palette
  talk to the model through calls and one selection-derivation, not ~30 string
  verbs.
- ADR-524's patch channel no longer has a flow consumer (paged keeps it).
- ADR-522's focus declaration and ADR-525's tier stay as contracts; their flow
  producers move from the runtime to the editor's selection plugin, derived in
  `selection.ts` terms (ADR-541 D2 — still the one home).

### D5 — The op surface is re-expressed, not re-invented

Turn-into, block tokens (`align`/`indent`/`tone`), Tab-steps-the-rung
(ADR-546 D4), the format tier's per-segment semantics (ADR-521 D3 — the Word
rule, heading bold exemption), slash, insert/delete/duplicate on objects — all
keep their ADR-ratified semantics, implemented as commands dispatching
transactions. Document-grain tokens (`font`/`measure`) and head/root concerns
stay on the existing artifact-shell path: the model owns `<main>`'s interior;
the shell wraps it.

### D6 — The substrate does not change

One write door, whole-file HTML, one attributed CAS revision per commit
(idle/blur-debounced, as today), whole-file attribution. `data-block-id` still
never crosses the write door as a substrate concept (ADR-528 §2). Serialization
is deterministic from the model — same annotated HTML dialect, same
`normalizeStructure` invariants expressed at parse time (rung clamp, id
discipline, promotion). Existing documents are read honestly and converge on
their next authored write (ADR-209 migration-by-use; ADR-546 D7's shape).

### D7 — The transaction log is the named path to per-span attribution

Not implemented here. ADR-528 §7 and ADR-546 §5 deferred per-block/per-span
attribution because the architecture could not see edits; a transaction-based
model is the missing prerequisite. Recorded so the bet has an address: when
attribution-inside-a-document is picked up, it starts from the step log, not
from a DOM diff.

### D8 — What is DELETED (singular implementation, CLAUDE.md §2)

On flow, with no dual path left behind: `enterFlow`/`flowCommit` and the flow
branches of `EDIT_SCRIPT`; the whole-body `yarnnn-flow-edit` commit lane and
`editFlowRegion`'s flow-only guards (annihilation + annotation-removal — their
property now holds by construction per D3); the `flowDead`/`yarnnn-flow-retire`
fence (ADR-540 — the defect class has no host); the flow consumers of the
patch channel; the flow caret/selection restore machinery
(`yarnnn-flow-caret`, `lastLiveRange` for fmt-ops); the paste allowlists
(`PASTE_ALLOW`/`PASTE_DROP`/`PASTE_KEEP_INTERNAL`) and `richPaste`;
`execCommand` on flow (the format ops, the Tab indent lane). Gates that pinned
these spellings are re-cut with intent preserved, never deleted.

## 4. What this costs, stated

- **A dependency family** (~9 ProseMirror packages). The trade is measured in
  §1/§2.2. Pinned versions; no framework coupling.
- **Two undo domains during the arc**: content undo is the model's history;
  shell ops (document tokens, rename) stay on the surface's write-labeled
  stack. Their domains are disjoint by D5; unifying them is owed, not hidden.
- **Table editing changes engine** (`prosemirror-tables` semantics rather than
  browser-native contenteditable table behavior).
- **The parent page now hosts artifact-derived CSS** (scoped). The scoping
  wrapper is generated by the same kernel emitters; a leak is a gate-able
  defect (selector prefix discipline), not a security boundary change — member
  documents were always member-authored; *foreign* artifacts still render only
  in the sandbox.
- **A large deletion re-cuts many gates** — each re-cut preserves the gated
  intent (the ADR-528 §8 discipline).

## 5. Falsifiers

1. **If a parent-side op on flow can be reverted or dropped by a subsequent
   keystroke commit**, D1 failed (one writer was not one writer).
2. **If any block-level substrate an existing document carries does not
   round-trip byte-stably through open→no-edit→save** (beyond the declared
   normalizations: rung clamp, id minting, promotion), D3 failed.
3. **If a second grammar declaration for flow survives** (a paste hand-list, a
   runtime kind list, a regex parser feeding the editor), D2 failed.
4. **If the flow editing path still reaches `execCommand`, `flowCommit`, or a
   whole-body postMessage commit**, D8 was not executed.
5. **If a foreign/shared artifact renders outside the sandboxed iframe**, D4
   was widened wrongly — the sandbox retirement is for *editing one's own
   flow document* only.
6. **If paged behavior changes at all**, the amendment leaked past its medium.

## 6. Implementation phases (each gated before the next)

1. **The schema + serializer** — generated from the vocabulary; round-trip
   parity gate over real fixture documents (F2, F3).
2. **The editor host** — parent-mounted, scoped kernel CSS, citation node
   views, idle/blur-debounced CAS save through the one door (F1).
3. **Chrome integration** — selection payload from the model (via
   `selection.ts`), ops as commands, slash/format-bar/outline wired (F1, F4).
4. **The deletion** — D8 executed; gates re-cut (F4, F6).
5. **The click-pass** — this arc's canon (ADR-546 §7, ADR-547 §7): the battery
   cannot prove an editing surface; the pass drives typing, turn-into,
   Tab-rung, token ops, paste, undo, reload-persistence on prod.
