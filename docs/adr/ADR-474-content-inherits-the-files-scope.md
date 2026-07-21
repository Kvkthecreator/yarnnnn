# ADR-474 — Content inherits the file's scope

> **Status**: Accepted 2026-07-21. Ratified by KVK.
> **Decides**: `workspace_blobs` gains a workspace owner; deletion of content is
> scoped exactly like modify and edit.
> **Resolves**: the A-vs-B question left open by
> [the GC sweep receipt](../evaluations/adr427-gc-sweep-executed-2026-07-20.md)
> and [retention from first principles](../analysis/retention-from-first-principles-reachability-not-deletion-2026-07-20.md).
> **Amends**: ADR-209 (the content layer gains a stated lifetime rule) ·
> ADR-427 (the storage seam gains a delete verb) · ADR-373 (blob scope follows
> the re-key) · ADR-407 (account-scope purge becomes complete).
> **Canonical home for the resulting model**:
> [`docs/architecture/authored-substrate.md`](../architecture/authored-substrate.md) §3.

---

## 1. Context

The substrate is three layers with three different lifetimes:

| Layer | Table | Lifetime rule |
|---|---|---|
| Namespace | `workspace_files` | the member curates (Trash, ADR-400) |
| Ledger | `workspace_file_versions` | immutable, retained (ADR-209) |
| Content | `workspace_blobs` | **had no rule at all** |

`workspace_blobs` was created ownerless — `(sha256, content, size_bytes,
created_at)` — so that identical content across workspaces would be stored
once. That single design choice has one structural consequence:

**`workspace_purge` cannot reach blobs.** It deletes `workspace_files` and
`workspace_file_versions` scoped by `user_id`; it mentions `workspace_blobs`
zero times, and it *cannot* mention them, because there is no column to scope
on. A member who deletes their workspace leaves their file content in the
table permanently.

On 2026-07-20 a GC sweep collected 34,393 unreferenced blobs. That was a mop.
It did not change the fact that purge is structurally blob-blind.

## 2. The decision

**Content is scoped to the workspace that wrote it, and deletion of content is
governed by the same grant that governs writing it.**

Two clauses, neither of which invents a new concept:

**D1 — Content inherits the file's scope.** A blob is the bytes of a file; a
file belongs to a workspace (ADR-373); therefore the blob belongs to that
workspace. `workspace_blobs` gains `workspace_id`. The ownerless design was not
a considered trade — it was a layer that never received the scoping the layer
above it already had.

**D2 — Deletion inherits write permission.** No new permission model. Whoever
may write a file may delete its content: the same `principal_grants` consult,
the same path-derived authority (ADR-320's `access(2)` shape), the same
powerbox (ADR-434). "Delete" is not a distinct capability requiring its own
rules; it is the terminal case of "modify."

**D3 — Sharing is a grant, never a byte coincidence.** Content-addressing is a
*storage* optimization and must never be an *authorization* fact. Two
workspaces holding identical bytes is a coincidence of content; it is not a
relationship between them, and it must never cause one to reach the other's
data. This is the cloud-provider model: GCS and S3 do not make two projects
co-own an object because the bytes match — each has its own object, and sharing
is an explicit IAM/ACL grant layered on top.

Applied here: if workspace A shares a file with B, that is an explicit grant on
the **file**, resolved through the existing permission layer
(`principal_grants` · ADR-434 powerbox · ADR-437 shared-artifact wedge), which
then reads A's content. B never acquires ownership of A's blob. Sharing lives
at the grant layer, not the storage layer.

**Dedup therefore becomes optional and invisible.** With ownership explicit,
identical bytes *may* later be stored once physically with N owner rows and a
refcount — a placement detail beneath the ownership layer, transparent to
permissions. Not built here (87 KB at N=14 does not justify it). The point of
the composite key is that the schema no longer *forecloses* it, and no longer
*requires* it to stand in for authorization.

### Why not the alternative

The ownerless design was justified by cross-workspace dedup. The accurate
criticism is not that dedup is worth too little — it is that **dedup was doing
authorization work it had no business doing.** Measured on live data
(2026-07-21, 14 workspaces, 461 referenced blobs):

- **15 blobs are shared across workspaces — 3.2% of referenced bytes (87 KB of
  2.7 MB).**
- **Every one of them is a kernel scaffold seed**, `system:`-authored, at one
  identical path: `MANDATE.md`, `IDENTITY.md`, `PRECEDENT.md`,
  `_autonomy.yaml`, `_budget.yaml`, `_workspace_guide.md`, `_playbook.md`,
  `principles.md`, `reflection.md`, `notes.md`, `style.md`,
  `_principles.yaml`, `AGENT.md`.
- **Zero member content is shared.** No blob spans two different paths.

So dedup is not saving member content from duplication — it is saving 87 KB of
genesis boilerplate that the kernel regenerates deterministically anyway. The
design traded *the ability to ever delete content* for that. Stated plainly,
the trade does not survive.

## 3. What this makes true

1. **Purge becomes complete.** A workspace deletion reaches every byte it
   created — rows *and* storage objects.
2. **Deletion rights become expressible.** Under ADR-373 multi-principal, "this
   member's content" is now a query. It was not before.
3. **Reachability becomes checkable per workspace**, not only globally.
4. **The content layer gets a stated lifetime rule**, closing the gap ADR-209
   left: it is precisely right about the ledger and silent about the layer
   beneath it.

## 4. Prerequisite: the storage seam needs a delete verb

ADR-427 Phases 2–3 moved binaries to the `workspace-cas` bucket. Today
`StorageBackend` exposes `has_blob`, `open_read_stream`, `open_write_stream`,
and `mint_serving_url` — **and no delete.**

This is a hard prerequisite, not a follow-on. A purge that deletes blob rows
without deleting bucket objects strands those objects unreachably: the row was
the only thing that knew the `storage_key`. Applied naively, blob ownership
would make the binary leak *worse* than the text leak it fixes.

`StorageBackend.delete_blob(sha)` lands first, driver-side, so physical
placement stays the driver's business (ADR-427 D2c).

## 5. Scope boundaries

**In scope**: the composite key + FK, the backfill, the delete verb, purge
reaching content, and the doc cascade.

**Adjacent, deliberately separate**:

- **`write_revision`'s 1→3 gap.** Blob-upsert commits independently of
  revision-insert, so a failure between them orphans a blob. Real, but this ADR
  demotes it from "the leak" to "a small correctness fix" — with ownership, an
  orphan is at least *reachable and collectable*, which is the property that
  was missing. Measured: 18 blobs written in the 19 hours after the sweep, zero
  orphaned. The 34,393 were almost certainly historical workspace purges, not
  an ongoing drip. **Falsifier**: if orphans appear during normal operation
  after this lands, the gap fires more often than measured and deserves its own
  fix.
- **Trash / lifecycle** (`archived` enforced per-reader rather than at the
  substrate). A namespace-layer question, sequenced *after* this deliberately:
  "empty my trash" can only mean something complete once the layer beneath it
  has an owner. See
  [the lifecycle audit](../analysis/file-lifecycle-audit-what-trash-actually-does-2026-07-20.md).
- **Scheduled GC.** With ownership + a complete purge, a recurring sweep becomes
  optional hygiene rather than the mechanism deletion depends on. Not built
  here; the reachability invariant (§7) is what would justify it later.

## 6. Migration

469 blobs, 14 workspaces, 718 revisions — small enough to verify exhaustively
rather than sample.

- **Backfill is derivable exactly**: every blob's owner is the workspace of the
  revision(s) citing it. All 718 revisions carry a non-NULL `workspace_id`
  (verified), so there is no unresolvable row.
- **The 13 shared kernel seeds split per workspace.** Each owning workspace gets
  its own row with the same sha. This is the last cross-workspace coupling in
  the substrate and removing it costs 87 KB.
- **Unreferenced blobs** (8 at time of writing, all inside the 24h safety
  window) have no citing revision and therefore no derivable owner. They are
  collected by the same rule that would collect them under any GC: nothing
  references them.
- `sha256` stops being the sole primary key; the identity becomes
  `(workspace_id, sha256)`.
- **The FK follows the key.** `workspace_file_versions_blob_sha_fkey` is
  re-pointed from `(blob_sha) → (sha256)` to
  `(workspace_id, blob_sha) → (workspace_id, sha256)`. No column is added to
  the ledger: `workspace_file_versions.workspace_id` already exists and is
  non-NULL on all 718 rows (verified). The composite FK is what makes
  cross-workspace blob reference *structurally impossible* rather than merely
  discouraged.
- **Read-path verification is by execution, not grep.** PostgREST resolves
  embedded joins (`workspace_blobs(content)`) through the FK; changing it
  changes how those resolve. Every embedded-join reader is exercised by calling
  it. (The ADR-472 postmortem — green gates, function-scoped import, prod 500 —
  is the precedent for why source-presence is not evidence of runtime health.)

## 7. The invariant this establishes

> **Every blob is owned by exactly one workspace, and every byte a workspace
> created is reachable from that workspace — or collectable by it.**

Checkable in one query, and therefore assertable in CI rather than hoped for.

## 8. Falsifiers

This decision is wrong if any of these turn out to hold:

1. **Cross-workspace dedup is load-bearing at scale.** If member content (not
   kernel seeds) is substantially shared across workspaces at N≫14, per-workspace
   storage becomes a real cost. Today: zero member content is shared. Re-measure
   before assuming this stays true.
2. **The kernel does not re-seed genesis files deterministically.** The
   per-workspace split assumes splitting a shared seed changes nothing. If some
   genesis path depends on blob identity across workspaces, the split would
   alter behavior across 14 live workspaces.
3. **Deletion completeness is not actually required.** If "content lingers until
   a sweep" is an acceptable answer to a member's deletion request, option A
   (recurring GC, blobs stay ownerless) is cheaper and this ADR is
   over-engineering. This is a compliance judgment, and it was made
   deliberately: the operator's position is that deletion scope is no different
   from the existing write scope.

## 9. The one-line statement

**A blob is the bytes of a file, and a file belongs to a workspace — so content
inherits the file's scope, and deleting content is governed by the same grant
that governs writing it; the ownerless content layer was not a considered trade
but a missing rule, and it cost the ability to honour a deletion.**
