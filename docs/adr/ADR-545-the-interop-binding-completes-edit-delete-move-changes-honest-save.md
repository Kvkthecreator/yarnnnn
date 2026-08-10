# ADR-545: The interop binding completes — edit · delete · move, a change feed, and the honest save

> **Status**: **Accepted** (2026-08-10) — operator-ratified ("aligned can you
> streamline our implementation thus in full to this"), from the external
> assessment digested the same day. Implemented in the same pass.
> **Date**: 2026-08-10
> **Dimension**: **Channel** (the MCP binding of the kernel contract) primary;
> one **Substrate-read** consequence (D5 — the searchable surface).
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**: ADR-543 (the file-native re-cut this completes), ADR-512 D3
> (the kernel verb contract), ADR-337 (EditFile / DeleteFile / MoveFile — the
> kernel verbs bound here), ADR-209 D7 (revert-as-write — why delete/move are
> safe to expose), ADR-406 (the CAS these verbs ride), ADR-325 (embed spend
> discipline — deliberately unchanged by D5), ADR-533 §13 (manifest caching —
> the reconnect step applies again).

---

## 1. Context — the assessment was right, and mostly about bindings

An external principal's assessment of the surface (2026-08-10) named four
structural gaps: nothing deletes or moves ("the tree only grows — an agent can
create but never tidy"), writes are whole-file only ("truncation stops being
dangerous [with patch] — the content it never saw was never in the payload"),
no change feed ("coordination requires polling, and polling isn't supported"),
and `list` doesn't paginate. A fifth finding arrived separately: search could
not see `_playbook.md` — "config and guide files are exactly what an arriving
agent needs most."

The audit of those claims found the ADR-543 lesson recurring: **three of the
four "missing verbs" already exist in the kernel** (ADR-337's `EditFile` /
`DeleteFile` / `MoveFile`, with attributed tombstones and the ADR-406 CAS) and
were simply never bound at the MCP surface; the change feed is a filter the
internal `ListFiles` already takes (`since`, ADR-209 Phase 3). The search
blindness turned out to be larger than underscores: the unscoped
QueryKnowledge sweep post-filters to a pre-re-founding **allow-list** of roots
(`operation/`, `uploads/`, `inbound/uploads/`), so every meaning-named folder
the re-founding made first-class (`deals/…`, a root-level guide) is invisible
to search — even to free BM25.

The remaining named gap — a status/scratch taxonomy — is NOT a missing verb;
it is an ontology question (DP33: a category belongs in data, not namespace)
and is deliberately deferred to its own ADR (§6).

## 2. D1 — `edit`: the anchored write (binds `EditFile`)

A ninth… rather: a new verb `edit(reference, old, new, replace_all=false,
message=None)` binds ADR-337's `EditFile`. The **anchor is the precondition**:
`old` must match the current content exactly and uniquely (unless
`replace_all`), so the verb carries no `base_revision` — a stale view fails
loudly as `no_match`/`not_unique`, never guesses, and the kernel's internal
head-read CAS closes the apply-window race (ADR-406 D4). Content the client
never read is never in the payload, which **removes the truncated-read
data-loss class structurally** for targeted changes, and two principals
editing different regions of one file stop colliding needlessly.

## 3. D2 — `delete` + `move`: the tidy verbs (bind `DeleteFile` / `MoveFile`)

The tree stops being grow-only. Both are **view changes, not information
loss** (ADR-337/209 D7): an attributed tombstone revision records who and why;
the chain (including content at deletion) is retained; restore is
revert-as-write. `move` refuses to overwrite an existing destination
(explicit intent = `delete` first). The governance lock-set and the ADR-307
gate apply unchanged — the same `CALLER_WRITE_POLICY["mcp"]` boundary that
governs `save`.

## 4. D3 — the change feed: `list` gains `since` (+ honest pagination)

`list(reference?, since?, limit?, offset?)`. `since` (ISO timestamp) filters
to files whose HEAD revision landed after the mark — "what moved since I was
last here" becomes one call instead of enumerate-and-diff-by-hand. `limit`
(≤500) + `offset` page the subtree in path order; `truncated` keeps meaning
"there is more" and now also carries `next_offset`. This is the asynchronous
multi-principal coordination primitive the assessment found most
conspicuously absent, and it is a filter the substrate already answered.

## 5. D4 — the honest save: the truncation guard

`open` caps content (`truncated: true` beyond `OPEN_CONTENT_CAP`); `save`
overwrites whole. Nothing stopped a client from reading half a file and
saving the visible half back over the whole. The guard is deterministic: a
`save` over an existing file **larger than the open cap** is refused with
`error: "large_file_overwrite"` unless the caller passes
`confirm_full_replace=true` — the message points at `edit` (the right tool
for targeted changes to a file you could not fully read). Wholesale rewrites
of large files remain possible; they now require stated intent instead of
silent luck. Belt and suspenders with D1: `edit` removes the class, the guard
catches the remaining whole-file path.

## 6. D5 — the searchable surface flips to a deny-list

`is_searchable_root` becomes: **everything in the commons is searchable
except machine/runtime substrate** (`governance/`, `system/`). The
re-founding made meaning folders first-class; the search sweep now agrees.
Two disciplines deliberately unchanged: **embed spend** (ADR-325's paid
semantic path keeps its allow-list — searchable ≠ embeddable; free BM25
carries the widened surface), and the **powerbox read gate** (reach is still
the grant's, enforced at the DB — this ADR widens relevance, not permission).

## 7. What is named and NOT taken

- **Status / scratch-vs-real** — an ontology decision (DP33: status is data,
  never a namespace); deserves its own ADR with the meaning-folder axioms on
  the table.
- **Range/region patches** beyond the anchor form; **cursor pagination**
  beyond offset; a **push change feed** (the pull `since` is the honest v1).

## 8. Consequences

- The roster grows to nine: `open · list · search · save · edit · delete ·
  move · history · share` — every content verb of the kernel contract now
  bound (ADR-512 D3's "list" gap closed by ADR-543; the write-side gaps close
  here). The ADR-533 D2 roster gate + D4 rendering-story gate extend to the
  three new verbs (all three text-only by declaration).
- Stale-manifest hosts need the reconnect step again (ADR-533 §13;
  CONNECTING.md).
- Identity discipline carries over: `edit`/`delete`/`move` stamp
  `author_identity_uuid` for human-traceable species exactly as `save` does
  (the 2026-08-10 identity pass).
