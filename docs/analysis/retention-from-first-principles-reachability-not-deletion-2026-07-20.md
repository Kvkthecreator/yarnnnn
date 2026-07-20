# Retention from first principles — reachability, not deletion

> **Status**: Discourse / axiomatic reframe. **No code written, no decision taken.**
> **Date**: 2026-07-20
> **Supersedes the framing of**: [Trash is not history](trash-is-not-history-scoping-the-lifecycle-fix-2026-07-20.md) — which asked "may we delete a row?" That was the wrong question.
> **Touches**: Axiom 1 (both clauses) · ADR-209 · ADR-373 · ADR-427 · DP7 · DP33
> **Method**: measured the live database first. Every number below is a query, not an estimate.

---

## 1. Measure before theorising

| Table | Rows | Size |
|---|---|---|
| `workspace_files` (the namespace) | 178 | 6.6 MB |
| `workspace_file_versions` (the ledger) | 657 | 13 MB |
| `workspace_blobs` (the content) | **34,814** | **51 MB** |

53 blobs per revision. Blobs are supposed to be *deduplicated* content, so the
ratio should run the other way.

```
blobs referenced by a revision        422
blobs total                        34,814
ORPHAN blobs (no revision)         34,392   ← 98.8% of rows, 98.0% of bytes
```

**34,392 blobs — 98% of all substrate content bytes — are referenced by
nothing.** No revision, no file, no path. They are unreachable from any query
the system can express, at N=5 workspaces.

The retention conversation has been about Trash. Trash governs 178 rows. The
actual retention problem is two orders of magnitude larger and sits somewhere
nobody was looking.

### Where they come from

Two producers, both structural:

**(a) `workspace_purge` cannot collect blobs — by construction.** It deletes
`workspace_files` and `workspace_file_versions` scoped by `user_id`, and
mentions `workspace_blobs` **zero times**. It cannot: the table is

```sql
workspace_blobs (sha256, content, size_bytes, created_at)
```

— **there is no owner column.** Blobs are globally shared by design, so no
per-user operation can ever reach them. Every workspace reset orphans every
blob it ever wrote. (Sampled orphans are `TrackUniverse` indicator writes and
Reviewer judgment logs from the alpha-trader era — workspaces since purged.)

**(b) `write_revision` is not atomic, and says so.** Its own docstring:

> *"the four-step sequence is not wrapped in a single transaction… a failure
> between step 3 and step 4 leaves a revision row without a head pointer"*

Step 1 (upsert blob) commits independently of step 3 (insert revision). Any
failure in between orphans a blob permanently. The docstring reasons about the
3→4 gap; the 1→3 gap has the same shape and no reconciliation.

### And the premise that justified the design does not hold

Blobs have no owner *because* they are shared across workspaces — identical
content reuses one blob. Measured:

| Workspaces sharing a blob | Blobs |
|---|---|
| 1 | 407 |
| 2 | 1 |
| 3 | 1 |
| 5 | 13 |

**15 of 422 referenced blobs are shared — 3.5%**, and those are almost certainly
identical scaffold seeds. The design traded *the ability to ever collect
content* for a 3.5% dedup win. That is a bad trade, and it was never stated as
one.

## 2. The axiom the system is actually missing

Axiom 1 has two clauses: **what persists lives in files**, and **every mutation
is attributed and retained**. Both are about *writing*. Neither says anything
about what happens to substrate that is no longer reachable — so nothing does.

The missing principle is not "when may we delete." It is:

> **Every byte in the substrate must be reachable from a named thing, or it
> must be collectable. Unreachable-and-uncollectable is a third state the
> substrate does not admit.**

This is not a new value — it is what Axiom 1 already implies. Retention means
*the record is preserved*, which presupposes the record is **findable**. 34,392
blobs that no query can reach are not retained; they are **leaked**. Retention
and leakage look identical on a disk-usage graph and are opposites in meaning.

**Reframe: the question is reachability, not deletion.**

- Deleting a reachable thing is a *policy* question (who may curate what).
- Keeping an unreachable thing is a *bug*. It preserves nothing, costs storage
  forever, and — because 98% of bytes are noise — actively degrades every
  operation over the substrate.

## 3. The three-layer model, and what each layer's rule must be

The substrate is three layers, and the previous discourse (mine included)
conflated them by discussing only the middle one.

| Layer | Table | What it is | Reachable from | Retention rule |
|---|---|---|---|---|
| **Namespace** | `workspace_files` | what is present in my workspace *now* | the member's tree | **the member curates** — Trash + empty is legitimate (the ledger holds the record) |
| **Ledger** | `workspace_file_versions` | what happened, who did it, when | `(workspace, path)` | **immutable, retained** — this is ADR-209's actual claim |
| **Content** | `workspace_blobs` | the bytes a revision points at | a revision's `blob_sha` | **reference-counted** — a blob lives exactly as long as some revision cites it |

Stated this way the answers fall out, and they are not the same answer:

- The **ledger** is what ADR-209 protects. Nothing here should ever be deleted
  by a member act. (Workspace purge is a different thing — an account-level
  erasure, ADR-407 account scope.)
- The **namespace** is a *view* the member curates. ADR-400 Q3 protected it as
  if it were the ledger, which is the conflation the prior note identified.
- The **content** layer has *no rule at all today*, which is why it leaks.
  Its rule is the classical one and needs no invention: **a blob is live iff
  referenced.** GC, not policy.

**DP33 again**: each layer's lifetime is data on that layer, not a property
inherited from a neighbour. The bug is that content's lifetime was implicitly
assumed to equal the ledger's, and nothing enforced it.

## 4. What "future-proof and scalable" actually requires

Four properties, each falsifiable:

1. **Reachability is total.** Every blob is referenced, or collected. A
   standing invariant, checkable in one query — *"orphan blobs = 0"* — and
   therefore a CI/monitoring assertion, not a hope.
2. **Every layer has a stated lifetime rule** (§3's table). No layer inherits
   another's by assumption.
3. **Deletion at any layer is expressible and bounded.** Purge must be able to
   reach every byte it created — which today it structurally cannot. This is a
   **compliance** matter too: a member exercising deletion rights leaves their
   content in `workspace_blobs` forever, because the table has no owner column.
   That is not a scaling nicety; it is a correctness and legal exposure.
4. **The invariant survives the binary future.** ADR-427 Phase 2/3 moves large
   content out of Postgres. A GC that only understands `content TEXT` will
   leak storage objects the same way — worse, because they are bigger. **The
   reachability rule must be defined at the seam, not at the column.**

### On (3): the owner column question

Giving blobs an owner conflicts with cross-workspace dedup. The measurement
says dedup is worth 3.5%. Three options, and the discourse should choose
explicitly rather than inherit:

- **A — reference-counted GC, blobs stay ownerless.** Sweep `workspace_blobs`
  for rows no revision cites. Preserves dedup; requires a sweeper; a purge's
  blobs are collected on the next sweep rather than synchronously.
- **B — blobs get a workspace, dedup only within a workspace.** Purge becomes
  complete and synchronous; deletion rights become expressible per-member.
  Costs the 3.5% and a migration.
- **C — both.** Owner for reachability + deletion rights; GC for the
  write_revision leak that an owner column does not fix.

My reading: **C, sequenced as A-then-B.** A is additive, reversible, and stops
the bleeding immediately without a migration. B is the correctness fix for
deletion rights and should follow once A proves the invariant holds. (A alone
leaves ADR-373's multi-principal deletion story incomplete; B alone still leaks
via the write_revision 1→3 gap.)

## 5. What this changes about the Trash question

It does not answer it — it **de-couples** it. The prior note argued a member may
empty their trash because the ledger holds the record. That argument survives
intact and is now *more* clearly correct, because §3 separates the three
lifetimes explicitly.

But it is now visibly the *smallest* of the three retention questions:

- namespace curation: **178 rows**, a product decision, genuinely the operator's;
- ledger immutability: settled, ADR-209, no change proposed;
- content reachability: **34,392 orphans, 98% of bytes**, a bug with a
  classical solution.

The honest sequencing is content first. A retention ADR written today that only
addressed Trash would ratify a policy for 2% of the problem.

## 6. Open questions for the operator

1. **A, B, or C** in §4 — and if C, is A-then-B the right order?
2. **Is the 34,392-orphan backlog collected, or left?** Collecting is safe by
   construction (nothing references them) but irreversible. Leaving them is
   also defensible while GC is proven. Recommendation: ship the invariant
   check first, observe it, then collect — the backlog is 51MB, not urgent.
3. **Does GC run as a scheduled sweep, or at write time?** A sweep is simpler
   and matches the removed-reaper precedent; write-time refcounting is exact
   but touches the hot path.
4. **Should `write_revision`'s 1→3 gap be closed directly** (write the blob
   only after the revision insert succeeds, or reconcile), independent of GC?

## 7. What I am not claiming

- Not claiming the orphans are causing a live problem. 51MB at N=5 is not an
  outage. The claim is that the *rate* is structural (~1,500/day sampled) and
  the mechanism has no ceiling — it is a leak, and leaks are diagnosed by
  mechanism, not by current size.
- Not claiming blobs should definitely get an owner. §4 lays out the trade with
  the measurement that makes it decidable; the choice is the operator's.
- Not claiming ADR-209 was wrong. It is precisely right about the ledger. It
  simply never stated a rule for the layer beneath it, and nothing else did
  either.
- Not claiming this is only about storage. The sharper consequence is
  **deletion rights**: today a purge cannot reach a member's content.

## 8. The one-line statement

**Retention is not "keep everything" — it is "everything kept is reachable";
and by that standard 98% of what this substrate stores is not retained but
leaked, because the ledger's immutability was silently assumed to govern a
content layer that has no rule of its own.**
