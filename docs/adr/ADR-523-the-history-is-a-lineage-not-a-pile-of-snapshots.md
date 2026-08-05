# ADR-523: The history is a lineage, not a pile of snapshots — undo/redo at the grain the member edited

> **Status**: **Accepted + Implemented** (2026-08-06). Derived from an audit of the Studio/Docs
> client-state model, asked for directly: *"is there a better way of handling client side
> and performance… and then, make undo and redo not just one command but more like other
> more web based interactive systems? figma, google docs."* The audit found the refresh
> model already sound (optimistic-first, CAS-anchored, serialized) and the **history** model
> to be the real ceiling. Operator-ratified in scope and sequence.
> **Date**: 2026-08-06
> **Dimension**: **Channel** (what the member's session holds about their own edits).
> Nothing at the Substrate dimension changes — no new file, no new write door, no revision
> semantics. History is transient session state, never authored.
> **Relates to**: ADR-444 (the one mechanical write door this ADR keeps singular),
> ADR-466 P8 (optimistic-first painting — the pattern this ADR extends to undo),
> ADR-466 D7 (the courteous 409 — the conflict path whose history consequence this ADR
> names), ADR-480 D1 (the flow caret, and the native contentEditable stack this ADR
> deliberately does not fight), ADR-482 D2 (the caret-live guard for text keys),
> ADR-518 (the Docs/Studio housing split — one implementation, so this lands on both).

---

## 1. Context — three defects, one root

The Studio/Docs client model was audited end to end. Two of the three findings are already
fixed (commit `b65c910`, landed ahead of this ADR because they were contained and the
repair did not depend on the design below). The third is what this ADR decides.

**What is NOT broken, and should be said plainly.** The refresh model is good. Writes paint
optimistically in the same tick and queue durability behind (`StudioSurface.tsx`, ADR-466
P8); the write tail serializes so two ops from one gesture cannot collide on one CAS head; a
local override is anchored to the head it forked from and survives a whole typing session
without a refetch; a 409 re-computes the op over fresh content rather than dropping the
member's edit. Text edits deliberately do not reload the iframe, to protect the caret. None
of that needs re-litigating, and this ADR changes none of it.

**Finding 1 — rapid undo corrupted its own history.** `replaying` was a boolean guarding an
*async* replay. Holding ⌘Z overlaps replays; the first `.finally()` cleared the flag while a
later replay was still in flight, so the next press was read as a fresh forward edit — it
pushed the replayed state back onto the undo stack and cleared the redo branch. Multi-level
undo degraded exactly when used fastest. **Fixed in `b65c910`** (depth counter).

**Finding 2 — an own retitle discarded the history.** `reloadKey` did three unrelated jobs:
refetch, drop the override, clear undo/redo. A retitle touches no block content but bumped
it, silently destroying a valid stack. **Fixed in `b65c910`** (`foreignKey` split out).

**Finding 3 — the model itself: history is a pile of whole-document snapshots.** This is the
root, and the reason ⌘Z "feels like one command."

```
undoStack: string[]   // up to 100 × the ENTIRE document HTML
```

Four consequences follow directly from that one line:

- **Memory is O(document × 100).** A large deck holds a hundred copies of itself.
- **Every undo reloads the iframe.** A replay goes through the write door with
  `reload: true`, so the canvas re-projects, re-parses, re-injects its runtimes, then
  restores scroll/caret/selection/zoom by postMessage. Google Docs' undo does not blink;
  ours re-mounts the document.
- **The grain is the whole op.** A keystroke burst commits as one op on blur or idle-2s, so
  ⌘Z after typing a paragraph deletes *the entire paragraph*. This is the reported symptom.
- **Any foreign write clears everything**, because a snapshot cannot be rebased onto a
  change someone else made.

The last point is the structural one. **Figma and Google Docs do not store snapshots; they
store invertible operations**, which can be transformed against a concurrent edit. The
existing code comment — *"you cannot undo across a conflict you did not make"* — is an
honest statement of the snapshot model's ceiling, not a law of editing.

## 2. The constraint that shapes the decision

The obvious move is "make every op return its inverse." **The audit rejects it**, on
evidence rather than taste.

`artifactOps.ts` exports ~35 ops (`insertBlock`, `deleteBlock`, `moveBlock`, `splitBlock`,
`mergeBlock`, `applyArrangement`, `movePages`, `setGeometry`, …). Every one has the same
shape:

```ts
(html: string, …args) => { html, landedId } | null
```

They are **whole-document string transforms**, not structured mutations over a tree. There
is no operation object to invert — the op *is* a function from document to document, and the
information needed to undo it (what was deleted, where it sat, what the prior geometry was)
is discarded the moment the new string is produced.

So hand-writing 35 inverses means 35 new hand-maintained code paths, each a place where an
inverse can silently disagree with its forward op, and each needing to stay correct as the
ops evolve. That is a large surface for a benefit — cross-conflict rebasing — that the
product does not yet need: today's collaboration model already reloads authoritatively on a
foreign write, and no member has two people typing in one artifact as the common case.

**The cost is real and the payoff is speculative. We do not take it.**

## 3. Decision

### D1 — The history entry is a lineage record, not a bare snapshot

An entry keeps the snapshot (it is what makes restore correct and cheap to reason about) and
adds the facts a snapshot alone cannot carry:

```ts
interface HistoryEntry {
  content: string;          // the pre-op document
  label: string;            // "insert block", "type" — what the member did
  structural: boolean;      // did the DOM SHAPE change?
  selectionId: string | null; // what was selected when it happened
  at: number;               // for coalescing
}
```

`structural` is the load-bearing addition. **A non-structural undo does not reload the
iframe** — it advances the override and lets the canvas re-project on content change, the
same contract a text edit already uses. That removes the blink from the common case
(typing, formatting, token changes) without touching the structural path, which genuinely
needs the reload.

`selectionId` restores *where the member was*, not just what the document said. Undo that
returns the caret to the edit it reverted is most of what makes Docs' undo feel continuous.

### D2 — Bounded by bytes, not by count

Replace the flat 100-entry cap with a byte budget (≈24MB) evicted oldest-first, with a floor
of 20 entries retained regardless. A 100-entry cap is meaningless when an entry can be 40KB
or 4MB. This makes the memory cost bounded and predictable instead of proportional to
document size.

### D3 — Text undo gets a finer grain than text *writes*

This is the Google Docs split, and it is the direct answer to "not just one command."

The revision remains the atom: writes still coalesce on blur/idle-2s (ADR-444 unchanged, no
new write door, no revision-per-keystroke). But **history checkpoints at a finer grain than
the write**: within a typing burst the surface records a checkpoint when the member pauses
(~600ms) or crosses a sentence boundary, coalescing anything faster into the current entry.

⌘Z then rewinds *a phrase*, not a paragraph — while the substrate still sees one clean
revision per burst.

**Scope limit, stated because it is easy to get wrong.** On flow (Docs), a live caret
deliberately yields ⌘Z to the browser's native contentEditable stack (`projection.ts`, per
ADR-482 D2 / ADR-480 D1) — which already rewinds keystroke by keystroke, *better* than any
stack we could keep. D3 governs the surface-level stack the member reaches **after** the
caret leaves, and the block-grain (Studio) editor. It must not steal ⌘Z from a live caret;
that trap is named in the existing code and stays respected.

### D4 — `foreignKey` is the only history invalidator

Ratifying what `b65c910` implemented: refetch (`reloadKey`) and history-invalidation
(`foreignKey`) are different facts. Only a write this member did **not** make clears the
stack — the lane's foreign-write path, and the unresolved 409 that falls through to the
destructive reload. Own retitles, own successful ops, and the manual reload button preserve
history.

### D5 — Not now, and why

- **No CRDT, no OT.** ADR-373 already refused CRDT for the substrate; the same reasoning
  holds at the session layer.
- **No cross-conflict rebasing** (§2).
- **No persisted history.** Session-scoped. The durable record is the revision trail, which
  already exists and is attributed; history is a convenience over the live session.
- **No new dependency.** No diff library enters `web/` for this.

## 4. Consequences

**Better.** ⌘Z rewinds at the grain the member typed, not the grain the system saved.
Non-structural undo stops blinking the canvas. Memory is bounded by bytes. Undo restores
selection. Both Docs and Studio get all of it from one implementation (ADR-518).

**Unchanged.** The write door, the revision atom, CAS, the optimistic paint, the 409
recovery, the caret guard.

**Accepted cost.** History still dies on a foreign write. That is the snapshot model's
ceiling and we are choosing to live at it (§2) until two-people-in-one-artifact is a real
workload rather than an anticipated one. When it is, this ADR is what gets superseded, and
D1's entry shape is deliberately the place where an `inverse` field would land.

**Verification.** `next build` from an isolated worktree (`pnpm` is not on PATH; the
main-tree build races next-dev). The interaction claims — no blink on non-structural undo,
phrase-grain rewind, caret restore — are **click-pass claims and are not verified by a
build**. The opaque-origin iframe defeats CDP, so that pass is human-only; it is owed, and
until it is run this ADR's UX assertions stand as reasoned, not receipted.
