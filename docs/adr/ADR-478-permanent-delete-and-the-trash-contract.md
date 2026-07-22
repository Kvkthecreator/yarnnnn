# ADR-478 — Permanent delete, and the Trash contract

> **Status**: Accepted 2026-07-21. Ratified by KVK.
> **Decides**: Trash gains a permanent-delete gesture; no retention timer; the
> ledger is never deleted; the gesture is owner-grade and dependency-checked.
> **Sequenced after**: [ADR-474](ADR-474-content-inherits-the-files-scope.md)
> (content got an owner) + [ADR-476](ADR-476-purge-is-workspace-scoped.md)
> (purge got the right scope) — both prerequisites, because "permanently delete"
> could not mean anything complete while the layer beneath it leaked.
> **Amends**: ADR-400 Q3 (the no-hard-delete position, reversed with reasons) ·
> ADR-329 (the delete verb gains a second, terminal step).
> **Preserves**: ADR-209 (the ledger is immutable) · ADR-448 (the reference
> edge) · ADR-405 (the witness dial) · Axiom 1 second clause.
> **Derivation**: [Trash and lifecycle — what "removal" means](../analysis/trash-and-lifecycle-what-removal-means-2026-07-21.md)

---

## 1. Context

Delete has been trash-not-erase since ADR-329: it writes a `lifecycle='archived'`
revision, the row survives, restore is symmetric. ADR-400 Q3 deliberately
declined a hard-delete, on the reading that ADR-209's retain-everything applied
to the namespace as well as the ledger.

Two things have changed:

1. **Deletion can now be complete.** Before ADR-474, content had no owner and
   `workspace_purge` could not reach it; "permanently delete" would have left
   the bytes in `workspace_blobs` forever. Before ADR-476, the scope predicate
   was wrong in a shared workspace. Both are fixed, so a terminal delete can now
   remove what it claims to.
2. **The measured population is three files** (14 KB, one day old). Whatever we
   decide is not driven by accumulation — this is a question about *meaning*,
   not volume. (Contrast the content layer: 34,393 orphan blobs, 98% of
   substrate bytes. *That* was a leak. This is not.)

## 2. The decision

**D1 — Permanent delete exists, as an operator gesture.** Two forms: "Delete
Permanently" on a single trashed file, and "Empty Trash" over all of them. Both
require explicit confirmation. This reverses ADR-400 Q3.

**D2 — No retention timer. Ever, by default.** Trash holds until someone empties
it.

The prevailing conventions diverge, and the divergence *is* the decision:

| | macOS Trash | Google Drive | S3 / GCS |
|---|---|---|---|
| Auto-delete after N days | **No** — opt-in, 30d, off by default | **Yes** — 30 days, mandatory | Configurable lifecycle rules |
| Manual empty | Yes | Yes | Yes |
| Who decides | The user | The vendor | The admin |

**We inherit macOS, and not by taste.** A 30-day timer is *the system deleting a
member's work with nobody witnessing it* — precisely what ADR-405's witness dial
says the system does not do, and what Axiom 1's retention clause resists. Google
can default-destroy because Drive is a consumer product with vendor-set policy;
yarnnn's canon puts that decision with the operator. If a timer is ever wanted it
ships as an **opt-in setting**, which is the macOS answer, not the Drive one.

**D3 — Permanent delete removes the deleted path's row, chain, and content. It
preserves the ledger's INTEGRITY, not the deleted path's rows.** The semantic is
**unrecoverable, not unremembered** — and the two words are in tension, so the
resolution has to be stated exactly rather than waved at.

The tension: "permanent" demands the file cannot be resurrected; "the ledger is
immutable" (ADR-209) resists deleting revisions. If we keep the chain, restore
can rebuild the file from it — so it is not permanent. If we drop the chain,
`trace` on that path returns nothing — so is the ledger still immutable?

**Resolution: what ADR-209 protects is that the ledger never LIES, not that every
byte of every path lives forever.** A permanently-deleted path returning "no
history" is honest — the file does not exist. A path returning a restorable chain
for a file the operator terminally deleted would be the lie. So:

- **The deleted path's chain goes.** A surviving chain is a resurrection vector;
  keeping it would make "permanent" false. This is the one place a member act
  removes revisions, and it is bounded to exactly the path being destroyed.
- **No OTHER path's revisions are touched.** `trace` on every surviving file
  stays complete and true. This is the immutability that matters.
- **No live citation is orphaned.** D5 refuses the delete if any live file's HEAD
  cites the path (`derived_from`), so nothing downstream loses its source. There
  is no FK from `workspace_file_versions` to `workspace_files` (verified), so the
  mechanics are a plain scoped delete of the path's rows — no cascade risk.
- **The record that it existed and was removed** survives as the operator's own
  terminal `archived` revision attribution in the surrounding narrative /
  activity, and in whatever cited it before (nothing, by D5). What we do not
  keep is a *replayable copy* of a file the operator chose to destroy.

So after a permanent delete: the path is gone, its bytes are gone (blobs no other
path cites — §D3a), its chain is gone, and every *other* file's history is
untouched and honest. This is the "shred one document, the filing system's
integrity is intact" shape — not the S3 delete-marker shape, which keeps a
tombstone precisely because S3 has no separate immutable ledger to carry the
fact.

**D3a — content is reference-counted at the revision level.** A blob is deleted
only when no OTHER path's revision still cites it. 21 blobs live are shared across
paths (identical bytes — kernel seeds, empty files, copied artifacts); deleting a
blob a live path still points at would strand that file. The check runs AFTER the
chain delete, against the true remaining graph, through the ADR-474 storage seam
(row + bucket object, last-owner-only).

**D4 — Permanent delete is owner-grade in a shared workspace.** It destroys
shared content, which ADR-476 D2 established is not a member-grade act. It reuses
`has_workspace_clear_authority` — owner-default plus the extensible
`workspace:clear` grant scope. No new permission concept.

*Named cost*: a member cannot empty trash in a shared workspace, including for
files they authored themselves. That is a real ergonomic loss. It is accepted
because the alternative — one member irreversibly destroying another's work with
no witness — is the asymmetry ADR-476 just closed one layer up. Trash *listing*
and *restore* stay ordinary organize-scope acts (`operator_can_organize`),
unchanged.

**D5 — A cited file cannot be permanently deleted.** If any live file's HEAD
cites the path through `derived_from` (ADR-448), the delete is refused and names
the dependents. This is the reference edge doing real work: the graph already
answers "what was made from this?", and permanently destroying a source that
live work cites would silently break provenance.

`authored_substrate.list_dependents` is the existing helper and already has the
right semantics — it excludes archived dependents, so a trashed file citing
another trashed file does not block. Trashing (reversible) stays unblocked; only
the terminal step checks.

## 3. What this does NOT change

- **Trash itself.** Archive/list/restore are unchanged and stay reversible.
- **The ledger.** No revision is ever deleted by this ADR.
- **The `archived` visibility convention.** Left as-is deliberately — see §5.
- **Purge (L1/L2).** A workspace purge already removes everything including
  archived rows; it is lifecycle-blind and correctly so.

## 4. Why no reaper, restated as a falsifier

The strongest argument *for* a timer is that trash accumulates unboundedly. The
data says it does not: 3 files, 14 KB, one day old, in a workspace with 201
active files.

**Falsifier**: if archived files grow to a meaningful fraction of the workspace
(say >10% of rows, or a member complains about clutter), the decision should be
revisited — as an **opt-in setting first**, and only as a default if the
population argues for it across multiple workspaces. Building the reaper now
would be answering ADR-474's question (a real leak) at the wrong layer.

## 5. Deliberately deferred: the central visibility helper

The lifecycle audit's third gap — `archived` enforced per-caller rather than at
the substrate — is **not** addressed here. Five hand-copied filters exist and the
search RPCs now carry it in SQL.

A single global predicate would be *wrong*: enumerating readers (tree, recents,
search) must exclude archived, while exact-path readers must not — Trash itself
lists archived rows and restore reads their content. The narrower fix (one
helper for the enumerate-case) is a tidiness argument, not a correctness one,
and it is orthogonal to this ADR. Deferred with that reasoning stated rather than
bundled in.

## 6. Falsifiers

1. **Members need to empty their own trash.** If D4's owner-gate proves too
   coarse in practice, the fix is a narrower grant scope (e.g. delete-own), not
   removing the gate.
2. **The ledger should go too.** If an operator needs a true forget-everything
   for compliance (GDPR erasure of a specific document's history), D3 is
   insufficient and that is a *different* verb with its own ADR — erasure is not
   deletion, and it must reckon with ADR-209 head-on rather than by extension.
3. **The dependency check is too strict.** If refusing to delete a cited file
   blocks legitimate cleanup, the alternative is to warn-and-proceed. Chosen
   strict because a broken citation graph is silent, and silence is what the
   reference edge exists to prevent.

## 7. The one-line statement

**Permanent delete means unrecoverable, not unremembered: the file and its bytes
go, the ledger keeps the fact that they existed and who removed them — and no
timer ever does it on the operator's behalf, because a system that destroys work
nobody witnessed is the one thing this architecture keeps saying it will not be.**
