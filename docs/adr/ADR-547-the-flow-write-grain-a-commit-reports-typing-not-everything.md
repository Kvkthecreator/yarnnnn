# ADR-547: The flow write grain — a commit reports TYPING, not everything

> **Completed by construction, and its mechanism superseded, by
> [ADR-560](ADR-560-the-document-model-flow-editing-leaves-the-dom.md) (2026-08-12).** With one
> writer there is no granularity mismatch for a commit to lie about: the per-op declared
> grain becomes ONE flush chokepoint in `applyOp`, and D3's guard property is re-homed into
> the schema (preservation island — nothing the model does not understand can be dropped).
> The law's three claims are gated in structural form (`adr547_flow_write_grain.mjs`).

> **Status**: **Proposed** (2026-08-10) — found by driving a real document on prod
> during the ADR-546 click-pass. Two prior framings were **tested and refuted**
> before this one (§2), which is the reason this is a law and not a fourth patch.
> **Date**: 2026-08-10
> **Dimension**: **Substrate** (what a flow write is allowed to say) primary, with
> **Channel** consequences (whether a member's op survives their next keystroke).
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**:
> - **ADR-480 D1/D3** (the editing grain: on flow the block is an ANNOTATION, the
>   root is `contenteditable`, the browser owns selection/undo) — **its READ half
>   is upheld in full; its WRITE half is amended.** Making the root editable was
>   right; leaving the commit's write granularity at *the whole body* is what this
>   ADR re-cuts.
> - **ADR-524 D1/D2** (the patch channel — a block-local op patches one block into
>   the live document instead of swapping `srcdoc`) — **the mechanism this ADR
>   generalizes.** D2 exempted patchable ops from the defect; this ADR observes
>   that the exemption *was* the fix and extends its reach.
> - **ADR-540** (a retired document does not commit) — **upheld and scoped.** Its
>   `flowDead` fence stops a *stale teardown* commit. It cannot stop a *live,
>   correctly-based* commit, which is what §1 found.
> - **ADR-466 D7** (the courteous 409) — unchanged, and **explains why nothing
>   caught this**: there was no conflict to detect (§1.3).
> - **ADR-546 D4** (Tab steps the rung) — a new affordance that landed on this
>   defect. It works as a gesture and did not survive a reload (§4.2).
> - **ADR-511 D5** (`normalizeStructure` at the one serialize seam) — unchanged.
> - **ADR-254** (file-format discipline) — unchanged; no new file, no new format.

---

## 1. Context — a 200-OK write that silently reverts the member's op

Found by driving `operation/untitled-document-3/document.html` on **prod**, not by
a gate. The ADR-546 battery was 46/0 and the full FE battery 23/23 at the time.

### 1.1 The observation

On a Docs document, **every parent-side op renders correctly and then reverts on
the next ordinary keystroke commit**:

| act | pane says | canvas shows | survives reload |
|---|---|---|---|
| Turn into → Bulleted list | "Bulleted list" selected | still plain prose | **no** |
| pane INDENT → 2 | `2` selected | indented | **no** |
| Tab (ADR-546 D4) | INDENT `1`, clamps at 3 | indented | **no** |
| typing (`RUNGPROBE`) | — | typed text | **yes** |

Turn-into and the pane's INDENT button are **pre-existing affordances** — this
predates ADR-546. Typing surviving while every op reverts is the diagnostic.

### 1.2 The mechanism, from the wire

Two `POST /api/studio/artifacts/write`, **both HTTP 200**:

| req | `message` | `expected_head_version_id` | returned head | payload carries the op? |
|---|---|---|---|---|
| 554 | `Docs: set indent to 2` | `d1de5a61…` | `5c31e30f…` | **yes** — `data-indent="2"` on the block |
| 555 | `Docs: edit document` | `5c31e30f…` | `c3dfcad6…` | **no** — no `data-indent` on any block |

555 is `onFlowEdit` → `editFlowRegion`, the whole-body flow commit. It chains onto
554's head, so **CAS is satisfied and there is no 409**, and it replaces the entire
`<main>` with a faithful serialization of a DOM that never received the op.

The chain that produces it:

- `applyOp` (`StudioSurface.tsx`) calls
  `writeAndAdvance(compute, message, /*reload*/ false, /*patchBlockId*/ undefined)`.
- `reload: false` is correct and deliberate (ADR-466 P8 — pixels never wait, and a
  reload here flashed backwards). `patchBlockId: undefined` means **no patch is
  sent**.
- So the parent's `liveRef` / `localOverride` advance, and **the iframe DOM is
  never told**.
- The member's next keystroke fires `flowCommit` → `readSourceInner(root)`, which
  strips only transient chrome and serializes the live DOM **honestly** — a body
  without the op.

### 1.3 Why every existing guard passed

This is the part that makes it a law rather than a bug:

- **`flowDead` (ADR-540) fired correctly** — `retireFlowCommits()` is called for
  every non-patchable op, posted in a `useLayoutEffect` so it precedes the
  re-projection. It was not bypassed.
- **CAS passed** — 555's base *is* 554's result. Nothing was out of date.
- **The payload was not corrupt** — `readSourceInner` is the ONE serializer both
  commit paths use, and it reported exactly what the DOM held.

**The destructive write was live, correctly ordered, correctly based, and honest.**
No fence, version check or lock catches that, because nothing was stale.

### 1.4 The real fault: a granularity mismatch

| writer | writes at | knows an op landed? |
|---|---|---|
| the iframe (`contenteditable` root, ADR-480) | **the whole `<main>`** | **no** |
| the parent (`applyOp`) | a computed whole document | yes |

The iframe's only write granularity is *the entire body*. So any parent-side op
that does not reach the iframe DOM is erased by the next ordinary keystroke.
**Typing survived for exactly this reason** — typing is the one mutation the iframe
DOM originates.

### 1.5 Three signals that a decision was missing, not a guard

1. **ADR-524 already built the correct fix and scoped it narrowly.** The patch
   channel pushes a projected block into the live DOM and skips the caret host. D2
   exempted patchable ops from the problem; it did not ask what happens to the
   ops it left out.
2. **ADR-540 fenced one instance** (the stale-teardown gasp).
3. **`editFlowRegion`'s own annihilation guard defends only the extreme of this
   same failure.** Its docstring states *"the blast radius of a bad `newInner` is
   the entire artifact"*, and it refuses a commit that takes a document from having
   blocks to **zero** blocks. **Losing an attribute is the same bug at lower
   amplitude, and it was undefended.** Someone met this failure class and hardened
   only its catastrophic tail.

Three patches to one seam, plus a guard covering one amplitude of the same fault,
is the signature of a missing structural decision.

---

## 2. Two framings tested and refuted (recorded, so they are not re-proposed)

### 2.1 "A retire gap" — REFUTED

The first hypothesis was that ADR-540's fence was not reached for token/convert
ops, making this ADR-540's bug recurring. **False**: the call is unconditional for
non-patchable ops, and it runs in a layout effect specifically to beat the
teardown. Reading the guard before theorising would have closed this immediately.

### 2.2 "A checkout / locking problem" — REFUTED, and this is the load-bearing one

The operator asked directly whether this is a *checkout* concept the system never
accounted for. It is not, and the receipts separate the two cleanly.

A checkout/lock framing predicts the losing writer is **stale** — so you fence it,
version it, or lock it. The system already has all three, and **all three passed**
(§1.3). The commit was a *truthful witness* to a document that had simply never
been told about the op.

**A checkout discipline cannot catch a writer that is not out of date.** What it
would add is ceremony around a correctness property that is not the one being
violated. The violated property is *granularity*: the iframe is allowed to say
"here is the whole document" when the only thing it can honestly witness is
"here is what I typed."

---

## 3. Decisions

### D1 — A flow commit may only report what the browser originated

`flowCommit`'s whole-body payload is a report of **native editing** — typing,
native splits/merges, paste, `execCommand`. That is the only thing the iframe DOM
is a competent witness to, and ADR-480 D3 is precisely why (the browser owns
selection and restructuring on a continuous surface).

**A whole-body replace is therefore reserved for browser-originated restructuring.**
It is not a general write door, and it must never be the write that carries away a
parent-authored fact.

### D2 — A parent-side op on flow REACHES the live document

An op that changes a block — a token (`align`/`indent`), a `convertBlock`, a
`setTokenMany` over a span — patches its block(s) into the live iframe DOM through
the **existing** ADR-524 channel. No new mechanism: `applyOp` names the blocks it
touched, and `writeAndAdvance`'s existing `patchBlockId` path carries them.

This is rule 7 (a new affordance is an existing op reached through a new grain
before it is ever a new op): the patch channel was already the fix, applied to one
class of op. D2 extends its reach rather than inventing a second path.

**Consequence**: the iframe DOM and the parent agree after every op, so the next
`flowCommit` reports a body that already contains the op — and the revert cannot
occur, by construction rather than by fence.

### D3 — A commit never removes an annotation it cannot have authored

The **safety net**, and deliberately independent of D2 so that a future op which
forgets to declare its blocks cannot silently destroy substrate.

`editFlowRegion` refuses a commit that would **drop grammar/identity annotations**
(`data-block`, `data-block-id`) or **block-grain property tokens** the region
previously carried, when the incoming body shows no sign of having authored that
change. Native editing does not remove a `data-indent` from an untouched
paragraph; only a stale-or-uninformed snapshot does.

This generalizes the annihilation guard from **one amplitude** (all blocks gone)
to **the property it was always protecting** (a commit must not be a silent
deletion of authored substrate). The existing zero-blocks refusal is retained as
the extreme case of the same rule, not replaced by it.

> **Deliberately not symmetric.** The guard constrains only *removal*, never
> addition — a member's typing must always be free to add. And it judges by
> annotations, not by text: contenteditable legitimately rewrites text nodes.

### D4 — The write path is one door with a declared grain, not two doors

`writeAndAdvance`'s `patchBlockId` parameter becomes the **declared grain** of the
op rather than an optimization flag:

- `null` grain = *the document restructured* (insert/move/delete/split/merge, or a
  browser-originated commit) → whole-body write, re-projection as today;
- a block-id list = *these blocks changed* → whole-body write for durability
  (unchanged — the substrate is whole-file per ADR-528 §2) **plus** a patch so the
  live DOM converges.

Durability is untouched. What changes is that an op must **say what it touched**,
and the surface uses that to keep its two writers in agreement.

---

## 4. What this costs, stated

### 4.1 Every op must now name its blocks

D2/D4 mean an op that changes blocks and does not declare them is a latent
occurrence of §1. That is a real burden on future ops, and it is why **D3 exists
independently** — the guard catches the case the discipline misses. The gate
asserts both, so a new op cannot quietly re-open this.

### 4.2 ADR-546 D4 rode this defect

The Tab rung works as a gesture and did not survive a reload — verified on prod.
It is **not removed**: removing it fixes nothing and loses the gesture, and it
fails identically to its pre-existing neighbours (Turn into, the pane INDENT).
Recorded here so the ADR-546 click-pass result reads honestly: *D4's gesture was
verified; its persistence was not, and this ADR is why.*

### 4.3 The patch channel's caret rule now matters more

The runtime already refuses to patch the block holding a live caret (replacing an
element under a cursor drops it mid-word). Under D2 more ops flow through that
path, so that refusal carries more weight. It is correct as written — the caret
host's DOM already shows the op's result when the op came from typing — but an op
that changes a block the member is *actively editing* converges on the next
ordinary re-projection instead of instantly. Named, accepted, not hidden.

### 4.4 What is NOT changed

- **ADR-480's read half** — the root stays `contenteditable`; the browser keeps
  selection, undo and ⌘F. This ADR does not re-enclose flow blocks.
- **Whole-file durability** — one attributed CAS revision per op through the one
  write door. `data-block-id` still never crosses it (ADR-528 §2).
- **`reload: false`** — the override remains the canvas (ADR-466 P8). This ADR
  fixes the *iframe's* knowledge, not by reintroducing reloads.

---

## 5. Not decided here

- **Per-block attribution** — still whole-file (ADR-528 §2's separate bet).
- **Whether paged needs D3's guard.** Paged commits are per-block enclosures
  (ADR-480), so the whole-body blast radius does not exist there. Unexamined
  rather than ruled out.
- **A general "the two writers reconcile" protocol** (CRDT-shaped). Explicitly
  refused in spirit by ADR-406 (no keystroke CRDT); D2/D3 are the minimum that
  makes one-directional convergence honest.

---

## 6. Falsifiers

1. **If a parent-side op on flow can be reverted by a subsequent ordinary
   keystroke commit**, D2 failed. This is the defect's own shape and the primary
   gate.
2. **If a flow commit can remove a `data-block`, `data-block-id`, or a block-grain
   token the region previously carried**, D3 failed.
3. **If an op declares no blocks yet changes block attributes**, D4's grain is not
   being declared — the gate enumerates the op sites.
4. **If the zero-blocks annihilation refusal stops working**, D3 replaced the guard
   instead of generalizing it.
5. **If a block holding a live caret is patched out from under the member**, §4.3's
   rule was widened wrongly.
6. **If paged block editing changes behaviour at all**, the amendment leaked past
   flow (ADR-480 is per-medium).

---

## 7. Implementation phases

1. **D3, the guard first** — it is the safety net, it is independently valuable,
   and it makes the defect *loud* rather than silent even before D2 lands.
2. **D2/D4, the grain** — `applyOp` declares its blocks; `writeAndAdvance` patches
   them. Token, turn-into and span ops converge.
3. **The gate** — falsify each: strip the guard and watch a commit eat an
   attribute; drop the declared grain and watch the revert return.

**A browser click-pass gates this arc, not the battery.** The defect was invisible
to 23/23 FE + 46/0 gates and was found on prod by driving the doorway. The pass is:
apply a token op, **type a character**, hard-reload, and confirm the op is still
there.
