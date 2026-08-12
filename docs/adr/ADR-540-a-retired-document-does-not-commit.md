# ADR-540: A retired document does not commit — the teardown write-back

> **The fence is DELETED by [ADR-560](ADR-560-the-document-model-flow-editing-leaves-the-dom.md) D8 (2026-08-12)** —
> not bypassed: the defect class lost its host. Flow no longer edits in an iframe, so there is
> no teardown gasp to fence; the model's teardown commit reports MODEL state, which cannot
> predate an op because ops flush the model first. The re-cut gate asserts the deletion is
> complete AND the replacement exists (`web/scripts/gates/adr540_flow_retire.mjs`).

> **Status**: **Accepted** (2026-08-09) — operator-directed ("fix the race now") after the defect was found in a browser click-pass of ADR-538.
> **Date**: 2026-08-09
> **Dimension**: **Channel** (Axiom 0 — how the surface talks to its canvas, and when the canvas may talk back). No Substrate change: no new file, no new write door, no revision semantics, no new op.
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**: ADR-524 (the patch channel — the mechanism whose *absence* on structural ops opened this window), ADR-480 D1 (the flow editing session — the commit this ADR retires), ADR-446 (the one write door), ADR-466 P8 (pixels never wait for the network — the optimistic override that triggers the teardown), ADR-538 (the click-pass that surfaced it), ADR-509/536 (the insert door this silently defeated).

---

## 1. Context — found by driving the doorway, not the room

ADR-538's gates were 59/59 and the build was clean. The click-pass on production
then found that **inserting a chart did nothing**: the block landed, and ~400ms
later the document was back to its previous state. No error, no console warning,
HTTP 200 on every request.

The instrumented message bus gave the shape immediately:

```
{taken: true}                 ← the slash pick lands
{hasChart: false, len: 313}   ← a flow-edit commit, carrying the PRE-insert DOM
{hasChart: false, len: 313}   ← and a second one
```

And the revision ledger showed the pattern in substrate, every time:

| t | message | result |
|---|---|---|
| 05:23:36.797 | `Docs: insert chart …commitments.csv` | block present ✅ |
| 05:23:37.324 | `Docs: edit document` | block **gone** ❌ |

**The defect is not ADR-538's.** `Table` — untouched by that ADR — is erased by
the identical pair (`Docs: insert table …` → `Docs: edit document`). Every cited
insert on the flow medium (chart · table · image · gallery) has been silently
reverted, past green gates, since the flow editing session and the optimistic
override have coexisted.

## 2. The mechanism

Three correct decisions compose into one wrong outcome:

1. **The optimistic override** (ADR-466 P8): a structural op computes against
   the parent's `live` content and advances `localOverride` *this tick*, so the
   pixels never wait for the network.
2. **The canvas re-projects on content change** (ADR-524 §1.1, measured there):
   `srcDoc` is a whole-document handoff, so the current iframe document is
   **discarded and rebuilt**.
3. **A pending flow edit must never be lost** (ADR-480 D1): so the runtime holds
   `window.addEventListener('beforeunload', flowCommit)` — a genuinely correct
   guard against losing typing to a tab close.

The teardown in (2) fires the guard in (3). `flowCommit()` reads the DOM of the
document being destroyed — which **predates the op from (1)** — and posts it as
`yarnnn-flow-edit`. The parent's `onFlowEdit` writes that stale region back
through the one door, over the block that just landed.

The guard is not wrong; it is **firing for the wrong reason**. It exists to
rescue a member's unsaved typing from an *unplanned* teardown. A re-projection
is a *planned* teardown in which the parent already holds the authoritative
result — there is nothing to rescue and everything to lose.

**Why the patch channel does not already cover this.** ADR-524 D2 made
patchability an allowlist that "defaults to NO", and a structural op is
explicitly not patchable ("a structural op is not patchable by definition").
That ruling is correct and this ADR does not touch it. But it means precisely
the ops that DO re-project are the ones with no patch to suppress the swap — so
the window this ADR closes is exactly the complement of ADR-524's coverage.

## 3. Decisions

### D1 — A document whose content has been superseded is RETIRED, and a retired document does not commit

The runtime gains one flag (`flowDead`). `flowCommit()` returns early when it is
set. The flag is set once and never cleared: the successor document is a fresh
runtime with its own flag, so there is no lifecycle to manage and no way to
"un-retire" a DOM whose content is already historical.

### D2 — The parent declares the retirement, because only the parent knows

The runtime cannot detect this on its own: from inside the iframe, a teardown
caused by a structural op is indistinguishable from a tab close. The fact lives
with the parent (it applied the op), so the parent states it —
`yarnnn-flow-retire`, one message, no payload.

### D3 — Ordering is the fix, and it is enforced by `useLayoutEffect`

The retire must reach the runtime **before** the override advances, because the
override is what triggers the re-projection whose teardown fires the stale
commit. Two orderings carry this:

- In `writeAndAdvance`, `retireFlowCommits()` is called **before**
  `setLocalOverride`.
- In `StudioCanvas`, the sender is a **`useLayoutEffect`** — the same React
  commit carries both `flowRetire` and the new `content`, and a passive effect
  would race the projection effect that re-feeds `srcDoc`. Layout effects run
  before paint and before passive effects, so the runtime is always told before
  it is destroyed.

Posting into a document that is already gone is harmless, so there is no
cleanup and no failure mode in the late case.

### D4 — A patchable op is EXEMPT

`if (!patchBlockId) retireFlowCommits()`. A patched op does **not** re-project
(that is the whole point of ADR-524's channel), so its document stays live and
must keep its right to commit the member's in-flight typing. Retiring there
would trade this defect for a worse one: silently dropping keystrokes.

## 4. What this amends

| Canon | Change |
|---|---|
| ADR-480 D1 | The flow session's `beforeunload` commit gains one precondition: the document must not be retired. The debounce, the source-mapping and the paste sanitizer are untouched. |
| ADR-524 D2 | Untouched and re-affirmed. The patch allowlist stays "defaults to NO"; D4 here reads that ruling rather than widening it. |
| ADR-466 P8 | Untouched. The optimistic override still advances first; this only silences a stale reporter downstream of it. |
| AUTHORING.md §The one write path | Gains the retirement precondition as a normative rule. |

## 5. Consequences

**Positive.** Cited inserts persist on flow — the ADR-509 insert door, the
ADR-538 chart, the ADR-536 list kinds and every `figure`/`gallery` citation
stop being silently reverted on Docs. The class of defect ("a planned teardown
fires an unplanned-teardown guard") is named, so the next runtime guard that
wants to survive a re-projection has a precedent to read.

**Costs, stated.** The runtime now has a state the parent can set, which is a
small widening of the parent→runtime protocol; D1's never-cleared flag is what
keeps that from becoming a lifecycle. If a future op re-projects *without*
going through `writeAndAdvance`, it will reopen this window — the gate below
pins the call site for that reason.

**Not claimed.** This ADR does not make structural ops patchable, does not
change what a revision is, and does not touch the paged medium (which has no
flow session and never had this window).

## 6. Falsifiers

1. **The retirement must be reachable.** If `retireFlowCommits` is ever removed
   from `writeAndAdvance`, or moved *after* `setLocalOverride`, the window
   reopens. Gate-pinned by call-site order, not by the symbol's existence.
2. **The exemption must hold.** If a patchable op starts retiring, in-flight
   typing will be dropped on ordinary text edits — the opposite defect. Pinned.
3. **If a cited insert is ever again observed reverting on flow**, D1's premise
   (that the stale commit is the only writer-back) is incomplete and a second
   source must be found rather than a second flag added.

## 7. The one-line statement

**A document whose content has already been superseded has nothing true left to
say — so the parent retires it before tearing it down, and its last gasp stops
overwriting the block that replaced it.**
