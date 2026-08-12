# ADR-554 — A derivation follows its source, and hides by its edge

> **Status**: Implemented (2026-08-12). A correctness fix, ratified as canon because it moves an anchor two other rules lean on.
> **Amends**: [ADR-395](ADR-395-model-consumable-projection-and-upload-intake-conformance.md) Piece B (the projection's hiding rule — lane-anchored → edge-anchored)
> **Preserves**: ADR-395's whole intake shape (retain raw · derive projection · cite by `derived_from`) · ADR-422 D2 (uploads are organizable) · ADR-337 D3 (MoveFile is one attributed op)
> **Derivation**: the 2026-08-12 arrival/move audit, Phase 1

---

## 1. The defect

An upload writes **two** rows: the raw blob, and a co-located `.extracted.md`
projection carrying `derived_from: <raw path>`. The projection is plumbing —
searchable text for recall — so the Files surface hides it and the member sees
one file, their PDF.

`MoveFile` moves **one row**. So the blessed workflow — upload, then move it
somewhere meaningful — did this:

```
raw        : inbound/uploads/operator/q3-report.pdf
projection : inbound/uploads/operator/q3-report.extracted.md   (hidden)

after moving the raw to operation/fundraising/q3-report.pdf:
  projection stays at inbound/uploads/operator/q3-report.extracted.md
  still hidden : True
  derived_from : points at a path with no live file
```

**The file's searchable text silently detached from the file, stayed invisible,
and cited a dead path.** Nothing surfaced it: no error, no orphan view, and the
hiding rule that made it invisible was the same rule that made it correct
before the move.

This is a consequence of two decisions that were each right alone — ADR-422 D2
making uploads organizable, and ADR-395 anchoring the hiding rule to the intake
lane. It is the seam-between-correct-modules shape again.

## 2. Decisions

### D1 — The projection travels with its raw

`MoveFile` carries the `.extracted.md` sibling, and **re-points its
`derived_from` at the raw's new path in the same act**. A citation that survives
the move is the entire point; leaving it stale would trade an invisible orphan
for a visible liar.

It lands in the **primitive**, not in the route, because that is the one seam
every mover already goes through — the Files route, the tree drag, an agent's
`MoveFile`. A caller cannot forget the sibling.

Costs one indexed read on every move (the sibling lookup), and returns early
when there is nothing to carry — the overwhelmingly common case.

### D2 — The hiding rule anchors on the EDGE, not the lane

`is_upload_projection` required the `inbound/uploads/` prefix **and** the
`.extracted.md` suffix. ADR-395's docstring argued for that pairing
deliberately, and its reasoning was sound: the suffix **alone** would hide a
member's own `notes.extracted.md` anywhere in the workspace.

But the lane anchor is false the moment the raw moves. Under D1 the projection
follows its raw into a meaning folder, where a lane-anchored rule stops hiding
it — and the member sees exactly the raw+extracted pair the rule exists to
prevent.

**A projection is plumbing because it is DERIVED FROM a sibling raw, not
because of where it happens to sit.** The narrowness ADR-395 wanted is
preserved and improved: a member's own `notes.extracted.md` is visible because
it cites nothing, rather than because of its address.

The edge is read from whichever evidence the caller already has:

| form | for | cost |
|---|---|---|
| `siblings` | a caller enumerating a folder (the tree, recents) | free — the raws are already in the result set |
| `content` | a caller holding bodies (the uploads listing) | free — that query already selects `content` |
| neither | any older caller | the lane rule still answers (pre-move, unchanged) |

**The sibling form was chosen over a content fetch after measuring.** An
earlier draft of this ADR asserted "the listing already selects `content`" —
true of the uploads listing, **false** of the tree and recents. Pulling full
file bodies into a tree query to hide a sibling would have been a real cost for
a cosmetic rule; the path-pair answers the same question from data already in
hand.

`.md` is excluded from the sibling test: a projection's raw is a non-text
upload by construction (a pure-text upload produces no projection at all), so
a member's `notes.md` can never turn their `notes.extracted.md` into plumbing.

## 3. What is deliberately not built

- **No backfill.** Existing stranded projections stay where they are. They are
  attributed substrate; a sweep that relocates files nobody asked about is the
  disposal ADR-549 §2 refused. They surface normally once their raw is moved
  again, and are harmless where they sit.
- **No orphan report.** Worth considering if stranding is found elsewhere; not
  earned by one instance.
- **No general "derivations follow their source" rule.** This ADR moves the
  upload projection only. `derived_from` is a wide edge (ADR-448) — an artifact
  derived from a source is *not* plumbing and must never be dragged around by
  its source's move. The narrowness is the point.

## 4. Falsifiers

1. Move an upload out of `inbound/uploads/`; its `.extracted.md` is at the new
   location, and its `derived_from` resolves to a live file.
2. That moved projection is **not** listed in the tree, recents, or the uploads
   view.
3. A member's own `notes.md` + `notes.extracted.md` pair both stay visible.
4. A `.extracted.md` whose raw was deleted becomes visible (nothing to hide
   behind).
5. Moving an ordinary file with no projection performs no extra write.

## 5. The one-line statement

**A derived projection follows the file it describes and hides because of the
edge that makes it a derivation — not because of the folder it was born in.**
