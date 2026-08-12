# ADR-524: The canvas is patched, not rebuilt — and a judgment shows its work early

> **D6's no-dependency refusal superseded, and the flow consumer removed, by
> [ADR-560](ADR-560-the-document-model-flow-editing-leaves-the-dom.md) (2026-08-12)** — with the
> measurement D6 implicitly asked for (§2.2 there). The patch channel itself stands, as the
> PAGED render path; flow no longer renders in the iframe while editing.

> **Status**: **Accepted + Implemented** (2026-08-06). Derived from an operator report of the symptom,
> not of a cause: *"whenever I request a slide re-arrange, or make slight changes in the
> details of a slide or doc, it seems to create either refresh or lag."* The audit found
> **two different causes wearing one symptom**, and the operator's own decomposition — the
> two handling paths plus "the loading mechanism… while loading, for user experience" — is
> the shape this ADR takes. Operator-ratified in scope and sequence.
> **Date**: 2026-08-06
> **Dimension**: **Channel** (how the surface talks to its canvas, and what it shows while
> a judgment thinks). No Substrate change: no new file, no new write door, no revision
> semantics, no new op. The patch is a render-path message; the preview is view state.
> **Relates to**: ADR-466 P8 (pixels never wait for the network — the principle this ADR
> finishes applying), ADR-479 (re-arrange as planned judgment — whose model call this ADR
> examines and *keeps*), ADR-446 D3 (the citation-island stamp a patch must not bypass),
> ADR-480 D3 / ADR-511 D5 (the normalize seam), ADR-481 D5 (flow flattening at projection),
> ADR-523 (the `structural` distinction this ADR generalizes past undo),
> ADR-518 D2 (one implementation — Docs and Studio both inherit this).

---

## 1. Context — one symptom, two causes, and a third thing that is neither

### 1.1 The canvas is replaced wholesale on every content change

`StudioCanvas` renders the artifact as `srcDoc={projected}`. `srcDoc` is a **whole-document
handoff**: any change to that string makes the browser discard the current document and
build a new one — re-parse the HTML, re-run every injected runtime, rebuild the DOM. The
member's scroll position, caret, selection and zoom are destroyed with it, which is why the
code that follows exists at all: `commandEdit` messages the fresh runtime to put all four
back (`yarnnn-edit-enter`, `yarnnn-select-block`, `yarnnn-zoom`, `yarnnn-restore-scroll`,
`yarnnn-flow-caret`).

That restore machinery is careful and it works. But it is **compensation for demolition** —
and the demolition is the thing the member perceives as a refresh.

**The `reload` flag was never what caused this, and that correction is the finding.** Tracing
it: `applyOp` already passes `reload: false` (a prior fix — the reload was worse than
redundant, nulling the override and flashing the pre-edit content back), and ADR-523 D1 made
undo conditional too. So the reload flag is *already* off for essentially every member op.
Yet the canvas still rebuilds — because `StudioCanvas` re-projects on **`file.content`
change**, unconditionally, and feeds the result to `srcDoc`:

```
content changes → resolveArtifactHtml(...) → setProjected(html) → srcDoc swap → full re-parse
```

`reloadKey` was only ever one of several ways to reach that line. **Every content change
re-parses the document — including a plain text edit that passes `reload: false`.** The
"invisible save" comment on the text path describes an intent the render path does not
honour: the write is invisible, the *re-projection* is not.

That is why narrowing the reload flag (ADR-523 D1) improved undo but did not remove the
symptom the operator reports on ordinary edits. The flag was never the mechanism.

**The fundamental correction is to stop replacing a document in order to change a block.**

### 1.2 The re-arrange wait is a judgment, and it is not fat

`handleApplyArrangement` awaits `api.studio.planArrangement` before applying — a model call,
`~2-4s` by the code's own comment. It is tempting to call this the performance bug and
route around it.

**The audit says no, and the first draft of this ADR was wrong about it.** ADR-479 replaced
a mechanical ladder (figure→media slot, name match, first-flow-slot, else refuse) *on
purpose*, because every rung "stands in for a question none of them asks — given this
content and this target layout, where does each piece belong?" The model is judging
**meaning**: keeping a stat with the sentence that frames it, keeping a figure with its
caption, balancing columns. A "skip the model when placement is unambiguous" gate would
route precisely the interesting pages to the dumb path and make re-arranges *faster and
worse*.

The call is already lean: one request, `max_tokens=1500`, skipped entirely when the page has
no content or the target has no slots, validated for total coverage, and already falling
back to the mechanical ladder when the router is cold or the balance is exhausted.

**There is no meaningful latency to remove. So the problem is not the wait — it is that the
member stares at a spinner during it.**

### 1.3 Which makes the third side a real side

The operator named it: *"maybe thus this is three sides, the two actual handling and then the
loading mechanism or while loading for user experience."* That decomposition is correct and
this ADR adopts it. `planning` is currently a boolean that renders a thinking state; for a
2-4s wait on a **visual** operation, showing nothing of the result is the weakest thing the
surface could do with information it already has.

## 2. Decision

### D1 — A patch channel: change a block without rebuilding the document

Add one inbound runtime verb, alongside the existing `yarnnn-*` command vocabulary:

```
{ type: 'yarnnn-patch', blockId: string, html: string }
```

The runtime replaces that block's element in place and leaves the rest of the document
untouched. Nothing is re-parsed, so **nothing needs restoring** — scroll, caret, selection
and zoom are never destroyed in the first place, and the restore round-trip disappears for
patched ops rather than being re-run faster.

The parent sends a patch instead of swapping `srcDoc` when, and only when, the change is
**block-local** (§D2). Otherwise it swaps `srcDoc` exactly as today. Full replacement
remains the fallback for everything, so correctness never depends on the patch path being
exhaustive.

### D2 — Patchability is decided by the op, and defaults to NO

An op is patchable only if it changes the content of **one existing block** and changes
neither the document's structure nor any other block:

| Patchable | Not patchable (full `srcDoc` swap) |
|---|---|
| `editBlockText` (block text commit) | insert / delete / duplicate / move / split / merge |
| `convertBlock` when the block keeps its id and position | re-arrange, page ops, skin/design-system apply |
| token / measure / geometry on one block | anything touching `<head>`, kernel style, or slide count |
| | flow-region edits (the root *is* the editable unit — ADR-480 D1) |

The default is **not patchable**. A new op is a full swap until someone deliberately proves
it block-local, because the failure mode of a wrong patch (a canvas silently disagreeing
with substrate) is far worse than the failure mode of a redundant reload (a blink).

### D3 — A patch is projected, never raw

This is the constraint that makes D1 safe, and it is not optional.

`resolveArtifactHtml` does real work on its way to the canvas: it stamps citation islands
with `data-src-html` **before** resolution (ADR-446 D3 — the source form is otherwise
unrecoverable at commit time), resolves every `data-ref` (async, over the network), flattens
legacy arrangements on flow (ADR-481 D5), and stamps operator-word labels on paged
containers (ADR-511 D3). The iframe is sandboxed `allow-scripts` with an opaque origin
precisely because the projection pass is what strips artifact-authored executables — a raw
patch would be an XSS lane straight into a script-enabled frame.

So the patch payload is produced by **the same projection pass, scoped to one block**
(`projectBlock`), never by hand-assembling markup parent-side. One projection
implementation, two entrances — the ADR-518 D2 discipline applied to the render path.

### D4 — The re-arrange previews mechanically, then settles to the judgment

Apply the **mechanical** placement immediately (the ladder that already exists as the
fallback), so the page visibly re-arranges in the same tick. Mark it provisional while the
plan is in flight. When the plan lands, settle to it.

This is ADR-466 P8 applied to a judgment instead of a write: *pixels never wait for the
network.* The member sees the layout change at once and watch it refine, rather than
watching a spinner and then a jump.

Two constraints, both load-bearing:

- **The preview is never written.** Only the settled result goes through the write door, as
  one revision. The provisional state is view state — it must not manufacture a revision
  nobody authored (ADR-209), and it must not produce two revisions for one gesture.
- **The preview must be visibly provisional.** A member who cannot tell a draft from a
  result will act on the draft. The gallery already has the `planning` signal; it moves onto
  the canvas rather than being replaced.

If the plan is refused, unreachable, or the balance is exhausted, the mechanical preview
**is** the result — which is exactly ADR-479's existing degraded path, now reached without
the member having waited to discover it.

### D5 — The planner's model call is kept, and the reason is recorded

Ratifying §1.2: no gate, no heuristic skip, no "unambiguous" fast path. ADR-479's judgment
stands. This decision is written down explicitly so that a future reader who finds the
`~2-4s` comment optimizes the *loading experience* (D4) rather than deleting the judgment —
the mistake this ADR's own first draft made.

### D6 — Refusals

- **No virtual DOM / no diffing library in the iframe.** The patch is id-addressed and
  block-scoped; a general tree-diff is a dependency and a class of subtle bugs bought to
  solve a problem D2 already bounds.
- **No same-origin iframe.** The opaque origin is a security boundary (ADR-446), not an
  inconvenience. Patching works within it because the channel is `postMessage`.
- **No incremental projection cache.** Projection is not currently cached and this ADR does
  not add one; `projectBlock` re-projects one block on demand.
- **No change to the write path.** One door, CAS-guarded, revision-as-atom (ADR-444).

## 3. Consequences

**Better.** A text commit, a token change and a one-block turn-into stop re-parsing the
document — no blink, no scroll jump, no caret restore round-trip, on the ops the member
performs most. A re-arrange shows its result immediately instead of after a 2-4s spinner,
and a degraded plan degrades visibly rather than silently late.

**Unchanged.** The write door, the revision atom, CAS, the sandbox, the projection's
security guarantees, ADR-479's judgment.

**Accepted cost.** Two render paths (patch and full swap) instead of one. This is a genuine
complexity increase and D2's default-to-NO is the discipline that keeps it honest: the patch
path is a narrow, enumerated optimization over a fallback that always works, not a second
rendering architecture. The moment a patch and a full swap could disagree about what the
document says, the patch is wrong and D2's table is what gets narrowed.

**Verification.** `next build` from an isolated worktree. **The interaction claims — no
blink on a patched edit, immediate re-arrange preview, provisional-then-settled — are
click-pass claims that a build cannot prove**, and the canvas's opaque origin defeats CDP,
so that pass is human-only. It is owed, and the packet ships with the implementation.
