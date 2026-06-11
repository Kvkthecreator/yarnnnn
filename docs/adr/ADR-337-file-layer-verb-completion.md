# ADR-337 — File-Layer Verb Completion: the Working-Tree Half of the Repo Analogy

> **Status**: Implemented (2026-06-11)
> **Date**: 2026-06-11
> **Authors**: KVK, Claude
> **Dimensional classification**: **Mechanism** (Axiom 5 — the primitive vocabulary) + **Substrate** (Axiom 1 — what the verbs mutate) + **Identity** (Axiom 2 — who maintains the working tree)

## Companion canon

- FOUNDATIONS Axiom 1 (Substrate; every write attributed and retained) + Axiom 5 (Mechanism; primitives are its vocabulary)
- ADR-209 — Authored Substrate (revision chain; D7 revert-as-write; **extended by this ADR**: the verb set gains delete/move; the chain's retention guarantee is what makes them safe)
- ADR-168 — Primitive Matrix naming reform (`*File` family naming; this ADR continues the convention)
- ADR-307 — Unified Permission Taxonomy (the new verbs are consequential, gate-owned, path-addressed)
- ADR-275 — housekeeping cadence is Reviewer-authored (the cadence slot this ADR finally gives verbs to)
- ADR-319 — Stewardship of Intent against Ground Truth (the posture, one altitude down: stewardship of the *medium* the intent lives in)
- 2026-06-11 alpha substrate audit + write-integrity fix (`f1ef557`) — the evidence trail

## Context — the audit finding

The 2026-06-11 alpha substrate audit traced three pathology classes across the alpha
workspaces (0-byte deliverables, dead `context/` trees, permanent litter) and the
holistic follow-up audit found their common root: **the Claude Code analogy that canon
repeatedly invokes was implemented faithfully at the cognitive altitude (memory,
compaction, skills, sub-agents, hooks, permission gating — each with an explicit ADR)
and only half-implemented at the substrate-verb altitude.**

Claude Code operating on a repo has `Read, Write, Edit, Glob, Grep, rm, mv, git
log/show/diff/revert`. YARNNN's file layer had `ReadFile, WriteFile(overwrite|append),
ListFiles, SearchFiles(BM25), ListRevisions, ReadRevision, DiffRevisions` — read-side
complete (richer than bare git), write-side **create/overwrite/append only**. No
surgical edit. No delete. No move. The absence was never decided: ADR-209 D10
explicitly scoped out branching + replication but is silent on delete/move; no ADR
ever proposed or rejected an edit primitive (verified by exhaustive sweep, 2026-06-11).

The pathologies map 1:1 onto the missing verbs:

1. **0-byte truncation wipes** ← no `EditFile`. Every change to an 18KB
   `principles.md` or a growing `judgment_log.md` was a whole-file rewrite — the
   exact write shape that collided with the output-token ceiling and produced the
   truncated empty writes fixed in `f1ef557`. The `max_tokens` fix treats the
   symptom; whole-file-rewrite-as-only-verb is the exposure.
2. **Litter is permanent** ← no `DeleteFile`. Pollution could only be buried, never
   removed — by anyone except a developer with psql.
3. **Migration residue + `conflict-backups/`** ← no `MoveFile` + overwrite-only
   writes. The `context/`→`operation/` re-root was a hand-rolled mass `git mv`.
4. **Wiped-file recovery was dev-only** ← revert-as-write (ADR-209 D7) is composable
   from `ReadRevision` + `WriteFile`, but nothing senses the need or names the duty.

The sharpest form of the posture gap: this repo's own execution discipline #1 —
*"Singular Implementation: delete legacy code when replacing"* — is enforced on the
system's developers but was structurally impossible for the system's agent. ADR-319
ratified stewardship-with-urgency over the *intent*; the agent had no verbs to steward
the *medium*.

## The naming question, settled

Should the verbs adopt bash/Claude Code names (`Edit`, `rm`, `mv`, `Bash`)? **No.**
The decision rule this ADR ratifies:

> **Names and safety semantics are YARNNN's (the primitive matrix is our syscall
> ABI); parameter contracts follow Claude Code's tool shapes wherever a trained
> model prior exists (the competence is borrowed).**

Rationale, in force-ranked order:

1. **The names carry semantics bash would lie about.** YARNNN's delete removes the
   live view while the revision chain retains every byte; `rm` signals irreversible
   destruction. YARNNN's writes are attributed commits, not byte streams. The
   descriptive names ARE the safety model, for both the LLM and the operator.
2. **ADR-168's `*File` family naming is standing canon.** `EditFile` / `DeleteFile` /
   `MoveFile` are its zero-churn continuation.
3. **The ABI is multi-vendor** (ADR-310/311 interop). Bash names bias every foreign
   caller toward POSIX expectations (flags, globs, pipes) that don't exist here.
4. **Operator legibility** (Derived Principle 12): primitive names leak into feed
   narration, revision messages, and the proposals queue. `DeleteFile` is
   self-explanatory to a layman; `rm` is jargon.
5. **No `Bash`.** Bash is arbitrary compute, not a verb. Its absence is the one
   deliberate, defensible divergence from Claude Code: the ADR-307 gating model works
   because every mutation passes through a typed, classifiable verb. (It is also why
   missing verbs hurt so much here — there is no shell escape hatch — which argues
   for completing the verb set, not adding the hatch.)

Where literal alignment pays: **input schemas.** Claude models carry heavy trained
priors on Claude Code's exact tool contracts. `EditFile(path, old_string, new_string,
replace_all)` is literally the Claude Code `Edit` shape — uniqueness-of-match,
include-surrounding-context disambiguation, prefer-small-surgical-edits all transfer
for free. A novel patch shape (line numbers, ranges, diffs) would forfeit that prior
and buy a fresh failure-mode discovery process.

## Decisions

### D1 — `EditFile`: surgical in-place replacement (the Claude Code `Edit` contract)

`EditFile(path, old_string, new_string, replace_all=false, scope, authored_by?,
message?)`. Reads the current file, replaces `old_string` with `new_string`, writes
the result through the Authored Substrate (one new revision, attributed).

Contract (mirrors Claude Code `Edit` exactly — borrowed prior):
- `old_string` must exist in the file → else `old_string_not_found`.
- Without `replace_all`, `old_string` must be **unique** → else
  `old_string_not_unique` (the model already knows to add surrounding context).
- `old_string == new_string` → `no_change` error.
- The resulting content must be non-empty → else `empty_content_blocked` (the
  `f1ef557` write-integrity guard applies uniformly; emptying a file is `DeleteFile`'s
  job, by intent, not an edit side-effect).
- Permission: consequential, **path-addressed gate-queueable** (joins `WriteFile` in
  `_PATH_ADDRESSED_QUEUEABLE` — governance locks DENY, bounded/manual QUEUE).

This verb retires the largest residual exposure of the 0-byte class: appending one
entry to `judgment_log.md` or fixing one threshold in `principles.md` no longer
regenerates the whole file through the output-token ceiling.

### D2 — `DeleteFile`: remove from the live view; the chain retains everything

`DeleteFile(path, scope, authored_by?, message?)`. Two-step, both attributed:

1. **Tombstone revision** — a `workspace_file_versions` row is inserted with the
   file's *current* blob (no new blob), `message` prefixed `DeleteFile:`. The chain
   records who deleted, when, why, and what the content was at deletion.
2. **Live-row removal** — the `workspace_files` row is deleted (the operation
   ADR-209's code comments already sanction for system callers; this ADR exposes it
   as an attributed primitive).

Restore is the already-canonical ADR-209 D7 revert-as-write: `ReadRevision` →
`WriteFile` (revision primitives query the chain, not the live row — they survive
deletion). Deleting a file is a **view change, not information loss**.

Errors: `file_not_found`. Permission: consequential, path-addressed (governance locks
DENY — the Reviewer cannot delete `governance/`, `constitution/` etc. under the same
`DEFAULT_REVIEWER_WRITE_LOCKS` that protect them from overwrite).

### D3 — `MoveFile`: relocation as one attributed operation

`MoveFile(path, new_path, scope, authored_by?, message?)`. Composition of D1's write
and D2's delete, as a single primitive call:

1. Revision at `new_path` with the current content (`message`: `MoveFile: from
   {path}`). Destination must not already exist → `destination_exists` (refuse
   silent overwrite; an intentional replace is `DeleteFile` then `MoveFile`).
2. Tombstone + live-row removal at `path` (`message`: `MoveFile: to {new_path}`).

The permission gate checks **both** paths against governance locks (the gate's
path-resolution helper generalizes from one path key to the verb's declared path
keys). The `context/`→`operation/` class of migration becomes a sequence of normal,
attributed operations instead of bespoke dev scripts + conflict backups.

### D4 — `SearchFiles` gains exact match (the grep half)

`SearchFiles(query, match="semantic"|"exact", scope, path_prefix?)`. Default
`semantic` is the existing BM25 path, unchanged. `exact` does case-insensitive
substring match over content (and path), returning matched paths with a snippet
around the first occurrence — the verb today's audit needed raw SQL for ("find every
file containing `context/`"). Stays `read_only` (never gates).

### D5 — Registry placement + the tool-count canary

All three verbs land in `CHAT_PRIMITIVES`, `HEADLESS_PRIMITIVES`, and
`REVIEWER_PRIMITIVES`. The Reviewer placement is deliberate despite the 2026-05-25
canary evidence (one added tool → ~74% output collapse): that canary added a
**novel-surface communication tool** (`platform_email_send_to_operator`) that changed
the judgment posture; these are **same-family file verbs** alongside the existing
`ReadFile`/`WriteFile` — low conceptual novelty, tight one-line descriptions. The
Reviewer is also the verb's primary customer: ADR-275's housekeeping cadence runs as
Reviewer wakes, and hygiene without delete/move is a duty without hands.
**Commitment**: the standing alpha soak (perception-field liveness instrument)
watches post-deploy Reviewer output volume; a collapse fingerprint reverts the
Reviewer placement (chat + headless keep the verbs regardless).

### D6 — What stays out, by decision

- **`cp`** — no demonstrated need; demand-pull discipline (ADR-225 lesson).
- **`Bash`** — capability, not verb; deliberate divergence (see naming section).
- **MCP exposure** — foreign LLM callers (`yarnnn:mcp`) do NOT get
  `EditFile`/`DeleteFile`/`MoveFile`; the interop surface stays read + `WriteFile`
  per ADR-311. A foreign caller that needs restructuring asks the operator.
- **A `Glob` tool** — `ListFiles` + `SearchFiles(match="exact")` cover the territory.
- **Branching / replication** — remain out of scope per ADR-209 D10.

### D7 — Stewardship posture (the duty the verbs serve)

The verbs exist so substrate hygiene can be **internalized** instead of dev-applied.
Three layers, per Axiom 5's determinism-to-judgment spectrum:

1. **Kernel guarantees** (deterministic): write-integrity guards (`f1ef557`),
   governance locks, the empty-content gate.
2. **Mechanical sensing** (deterministic, deferred to demand): topology conformance
   (any live file outside `_workspace_guide.md`'s declared roots is residue by
   definition), 0-byte anomalies. Named here; shipped when the housekeeping cadence
   first wants a sensor (ADR-305 discipline — no dead substrate ahead of a reader).
3. **Reviewer judgment**: what is litter vs. load-bearing — decided at the
   Reviewer's own ADR-275-authored housekeeping cadence, executed with these verbs,
   attributed in the chain, gated by ADR-307.

The discipline cuts both ways: **developers do not hand-clean the working set**
(that is the agent's stewardship), and **the agent does not clean defect litter**
(that is a kernel bug to fix at the guard layer).

## Consequences

- The repo-analogy verb table in `primitives-matrix.md` becomes explicit (one
  mapping table: `EditFile ≈ Edit`, `DeleteFile ≈ rm` (view-only), `MoveFile ≈ mv`,
  `SearchFiles(exact) ≈ grep -F`) so future sessions don't re-litigate.
- `_PATH_ADDRESSED_QUEUEABLE` grows from `{WriteFile}` to `{WriteFile, EditFile,
  DeleteFile, MoveFile}`; the ADR-307 gate test's exact-set assertion updates in the
  same commit (ratified contract change).
- Tool counts: chat 28→31, headless 26→29, Reviewer 21→24 (+ ReturnVerdict).
- `workspace_files` deletion stops being a psql-only operation; every deletion is
  attributed in the revision chain from now on.

## Key files

`api/services/authored_substrate.py` (delete-with-tombstone helper),
`api/services/primitives/workspace.py` (3 tool defs + handlers + `_apply_edit` pure
function + exact-match branch + gate path-keys helper),
`api/services/primitives/registry.py` (3 lists + HANDLERS),
`api/services/primitives/permission.py` (queueable + path-addressed sets, multi-path
lock check), `docs/architecture/primitives-matrix.md` (rows + analogy table +
counts), `api/prompts/CHANGELOG.md`, `api/test_adr337_file_verbs.py` (gate),
`api/test_adr307_permission_taxonomy.py` (exact-set assertion updated).
