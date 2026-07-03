# ADR-406: Stale-Parent Rejection — optimistic concurrency at the singular write path

**Status**: Implemented (2026-07-03) — migration 197 applied to prod (guard probe: duplicate-parent insert rejected live); gate `api/test_adr406_stale_parent.py` 22/22
**Date**: 2026-07-03
**Dimension**: Substrate (primary, Axiom 1) — integrity of the revision chain under concurrent principals
**Relates to**: ADR-209 (authored substrate — the parent-pointer chain this hardens), ADR-286 (single-writer-per-path — the semantic layer above), ADR-373 (multi-principal workspace — the condition that makes races real), ADR-405 (the witness dial — the conflict surface is a witness moment), ADR-400 (operator direct manipulation — the second live writer)
**Amends**: ADR-209 (write_revision gains an optional CAS precondition; the chain gains a DB-level linearity guarantee)

---

## 1. Context

`write_revision()` (ADR-209) reads the newest revision for a path *at write
time* and records it as the new revision's parent. The caller never states
which revision it *based its edit on* — so two principals editing from the
same head both succeed, and the second silently clobbers the first. The chain
faithfully records the order (attribution survives), but nothing ever
*detects* the conflict. Verified in prod discourse 2026-07-03: no CAS
anywhere on the write path.

Pre-ADR-400 this was theoretical — one operator, one steward whose writes
were proposal-gated. Now the operator manipulates files directly, foreign
LLMs write under grants, and ADR-404 makes human members the launch thesis.
Concurrent honest writers are the normal case, not the edge.

Canon already rejected the heavyweight answers: no merge/CRDT layer
(ADR-286, reaffirmed ADR-378 — semantic conflict is reconciled by the seat),
no locking. What is missing is the git-grade minimum: **a write based on a
stale parent is rejected, not absorbed.**

## 2. Decision

**D1 — `expected_parent_version_id` on `write_revision` (optional CAS).**
A caller that read the file before editing passes the head revision id it
read. If, at write time, the current head differs, the write raises
`StaleWriteError` carrying both revisions' attribution (who wrote the
intervening revision, when, with what message). Callers that don't pass the
precondition keep today's append semantics — mechanical appenders (capture
lane, ledgers, logs) are last-write-tolerant by design and MUST NOT adopt
the precondition.

**D2 — The HTTP conflict contract.** `PATCH /api/workspace/file` accepts
`expected_head_version_id`; on mismatch it returns **409** with
`{current_head: {id, authored_by, message, created_at}}`. `GET
/api/workspace/file` returns `head_version_id` so the editor holds its base.
The FE editor sends its base on save and surfaces the conflict with the
intervening author's attribution ("kvk moved past you 40s ago — reload &
reapply"). Resolution is revert-as-write (ADR-209 D7): reload, reapply, save
— never a hidden merge.

**D3 — DB-level linearity guard.** A partial UNIQUE index on
`workspace_file_versions(parent_version_id) WHERE parent_version_id IS NOT
NULL` makes the chain *structurally* linear: two truly concurrent writers
that both read head H cannot both insert a child of H — the loser gets a
unique violation, surfaced as the same `StaleWriteError`. This closes the
read-then-insert TOCTOU window that a Python-side check alone leaves open.
Prod verified clean before ratification (0 duplicate parents / 284
revisions), so the index builds without repair. The ADR-209 orphan-
reconciliation property (a revision inserted but head-pointer update lost →
next write parents on the orphan) is preserved — the orphan IS the newest
revision, so the next write's parent is unique.

**D4 — Which writers adopt the precondition.** Adopt: the operator file
editor (route layer, D2) and the `EditFile` primitive (it reads before
editing; it threads the head it read). Do not adopt: `WriteFile` in append
mode, capture/ledger/log writers, mirrors — appends want interleaving.
`WriteFile` in overwrite mode from chat MAY adopt later; deferred until a
real clobber is observed there (no speculative surface).

**D5 — No merge, ever, at this layer.** Reaffirms ADR-286/378: the substrate
detects and attributes conflicts; resolving them is judgment (a principal
reapplies, or the seat reconciles). A future three-way-merge helper would be
a *tool offered at the conflict surface*, never an automatic write.

## 3. Consequences

- A stale write becomes a visible witness moment (ADR-405) instead of silent
  data loss — the launch-blocking racing concern is closed by construction.
- The chain gains a hard invariant (linear history per path) the kernel can
  rely on: `parent_version_id` uniquely determines the successor.
- Zero behavior change for every existing caller until it opts in; the
  guard index only bites actual races.

## 4. Key files

`api/services/authored_substrate.py` (StaleWriteError + precondition +
unique-violation translation) · `supabase/migrations/197_adr406_linear_chain_guard.sql`
· `api/routes/workspace.py` (409 contract) · `api/services/primitives/workspace.py`
(EditFile threading) · `web` file editor save path · gate
`api/test_adr406_stale_parent.py`.
